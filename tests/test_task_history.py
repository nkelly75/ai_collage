import asyncio
import copy
import json

import pytest

from ai_collage.conversation import Conversation
from ai_collage.agent_models import NavigationEvidence
from ai_collage.models import CollageError, InputLayout
from ai_collage.projects import read_json
from ai_collage.task_history import (
    RecipeChange, change_matches, navigation_target, recipe_changes, undo_target,
)

from .helpers import layout_data
from .test_agent import (
    FakeModel, agent_project, ask, asyncio_wakeup_pair, intent, reply,
)


def bordered(width=1):
    data = layout_data()
    for layer in data["layers"]:
        layer["border"] = {"width_px": width, "color": "#FFFFFF"}
    return data


def navigation(kind, text, **fields):
    return {"kind": kind, "text": text, **fields}


def confirm(conversation, requests, target, evidence, *, action="select", prompt=None):
    model = FakeModel(intent(
        "question", question=f"Do you mean {target}?",
        return_confirmation={"proposal_id": target, "action": action, "evidence": evidence},
    ))
    result = asyncio.run(conversation.request(prompt or evidence["text"], model, requests))
    assert result.kind == "question"
    return model


def test_photo_keyed_differences_do_not_turn_stacking_into_spurious_photo_edits():
    before = InputLayout.model_validate(bordered())
    changed = bordered()
    changed["layers"].reverse()
    changed["layers"][0]["border"]["width_px"] = 2
    fields = [change.field for change in recipe_changes(before, InputLayout.model_validate(changed))]
    assert fields == ["recipe.photos.2.border.width_px", "recipe.stacking"]


@pytest.mark.parametrize("text,field,before,after", [
    ("before photo 2 became smaller", "recipe.photos.2.border.width_px", 3, 1),
    ("before photo 2 moved higher", "recipe.photos.2.box.center_y", 0.3, 0.4),
    ("before photo 2 moved left", "recipe.photos.2.box.center_x", 0.3, 0.4),
])
def test_descriptive_evidence_does_not_confuse_fields_or_reverse_direction(text, field, before, after):
    assert not change_matches(text, RecipeChange(field=field, before=before, after=after), [])


def test_ordinal_evidence_cannot_be_a_fragment_of_an_unrelated_word():
    with pytest.raises(CollageError, match="absent"):
        navigation_target(
            NavigationEvidence(kind="ordinal", text="first"),
            "Firstly, make a different arrangement", [], None, [], set(),
        )


def test_old_descriptive_task_retrieval_and_exact_return_beyond_windows(agent_project, monkeypatch):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply(bordered()))
    thickened = bordered(3)
    ask(conversation, requests, reply(thickened), prompt="Thicken the borders")
    task = conversation.tasks()[-1]
    for number in range(18):
        data = copy.deepcopy(thickened)
        data["canvas"]["background"] = f"#{number + 16:02X}2020"
        ask(conversation, requests, reply(data), prompt=f"Background variation {number}")
    prompt = "Go back to before thicker borders"
    context = conversation.context(prompt)
    assert len(context["history"]) == 3 and len(context["compact_tasks"]) == 12
    assert task.task_id in {record["task_id"] for record in context["compact_tasks"]}
    assert context["compact_tasks_omitted"] == 5
    assert context == conversation.context(prompt)
    before = {path: path.read_bytes() for path in (conversation.root / "proposals").rglob("*")
              if path.is_file()}

    def forbidden(*args):
        raise AssertionError("Exact selection must not render or accept")

    monkeypatch.setattr("ai_collage.conversation.render_layout", forbidden)
    monkeypatch.setattr(conversation.store, "accept_recipe", forbidden)
    model = FakeModel(intent("select", proposal_id=first, navigation=navigation(
        "before", "before thicker borders", task_id=task.task_id,
        field="recipe.photos.1.border.width_px",
    )))
    result = asyncio.run(conversation.request(prompt, model, requests))
    assert result.kind == "selection" and result.proposal_id == first
    assert len(model.contexts) == 1
    assert before == {path: path.read_bytes() for path in before}
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.baseline == first and resumed.state.expected_version is None


def test_undo_uses_source_ancestry_skips_noops_and_retains_fresh_predecessor(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    smaller = layout_data()
    smaller["layers"][1]["box"]["width"] = 0.18
    second, _ = ask(conversation, requests, reply(smaller))
    third, _ = ask(conversation, requests, reply(smaller))
    assert not conversation.tasks()[-1].changed
    assert undo_target(conversation.tasks(), conversation._current_source(), 1) == first
    fresh = copy.deepcopy(smaller)
    fresh["canvas"]["background"] = "#202020"
    fourth, _ = ask(conversation, requests, reply(fresh), action=intent("fresh"))
    assert conversation.proposal(fourth).parent is None
    assert undo_target(conversation.tasks(), conversation._current_source(), 1) == third
    assert undo_target(conversation.tasks(), conversation._current_source(), 2) == first
    assert conversation.context("Undo the last two edits")["navigation_lookup"]["proposal_id"] == first
    model = FakeModel(intent("select", proposal_id=first, navigation=navigation(
        "undo", "Undo the last two edits", steps=2,
    )))
    asyncio.run(conversation.request("Undo the last two edits", model, requests))
    branch, _ = ask(conversation, requests, reply(fresh))
    assert conversation.proposal(branch).parent == first
    assert undo_target(conversation.tasks(), conversation._current_source(), 1) == first
    retry, _ = ask(conversation, requests, reply(smaller), action=intent("retry", proposal_id=branch))
    assert conversation.proposal(retry).parent == first
    assert undo_target(conversation.tasks(), conversation._current_source(), 1) == first
    assert second not in {record.proposal_id for record in conversation.tasks()[-2:]}


def test_fresh_composition_retry_does_not_count_rejected_arrangement(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    fresh = layout_data()
    fresh["canvas"]["background"] = "#202020"
    rejected, _ = ask(conversation, requests, reply(fresh), action=intent("fresh"))
    alternative = layout_data()
    alternative["canvas"]["background"] = "#303030"
    ask(conversation, requests, reply(alternative), action=intent("retry", proposal_id=rejected))
    assert undo_target(conversation.tasks(), conversation._current_source(), 1) == first


def test_clarifications_form_one_task_and_keep_all_answers_essential(agent_project):
    conversation, requests = agent_project
    original = "Make one photo stand out"
    ask(conversation, requests, action=intent("question", question="Which photo?"), prompt=original)
    ask(conversation, requests, action=intent("question", question="How should it stand out?"),
        prompt="Photo 2")
    resumed = Conversation(conversation.store, "demo")
    _, model = ask(resumed, requests, reply(), prompt="Make it larger")
    records = resumed.tasks()
    assert len(records) == 1 and len(records[0].events) == 4
    assert records[0].request == original and records[0].outcome == "proposal"
    assert model.contexts[-1]["active_task"] == {
        "request": original, "answers": ["Photo 2", "Make it larger"],
    }
    assert len(resumed.context("Next")["history"]) == 1


@pytest.mark.parametrize("compound", [False, True])
def test_confirmation_survives_restart_and_keeps_exact_action_and_edit_task(agent_project, compound):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    changed = layout_data()
    changed["canvas"]["background"] = "#202020"
    latest, _ = ask(conversation, requests, reply(changed))
    prompt = f"Go back to {first}" + (" and make photo 2 smaller" if compound else "")
    evidence = navigation("id", first)
    confirm(conversation, requests, first, evidence,
            action="edit" if compound else "select", prompt=prompt)
    resumed = Conversation(conversation.store, "demo")
    action = intent(
        "edit", source=first, navigation=evidence,
    ) if compound else intent("select", proposal_id=first, navigation=evidence)
    model = FakeModel(action, reply(changed))
    result = asyncio.run(resumed.request("Yes please", model, requests))
    assert result.kind == ("proposal" if compound else "selection")
    if compound:
        assert model.contexts[-1]["original_task"] == prompt
        assert model.contexts[-1]["editing_baseline"] == resumed.proposal(first).recipe.model_dump(mode="json")
        assert resumed.proposal(result.proposal_id).parent == first
    else:
        assert result.proposal_id == first and len(model.contexts) == 1
    assert latest != resumed.state.baseline


def test_rejected_or_superseded_confirmation_never_silently_selects(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    changed = layout_data()
    changed["canvas"]["background"] = "#202020"
    latest, _ = ask(conversation, requests, reply(changed))
    evidence = navigation("id", first)
    confirm(conversation, requests, first, evidence, prompt=f"Return to {first}")
    model = FakeModel(
        intent("select", proposal_id=first, navigation=evidence),
        intent("question", question="Which proposal did you mean?"),
    )
    result = asyncio.run(conversation.request("No", model, requests))
    assert result.kind == "question" and conversation.state.baseline == latest
    model = FakeModel(intent("edit", source="current", continues_task=False), reply(changed))
    asyncio.run(conversation.request("Change the background instead", model, requests))
    assert conversation.proposal(conversation.state.baseline).intent.task_request == "Change the background instead"
    last = conversation.history()[-1]
    assert last.task_id != 5
    assert conversation.context("Yes")["pending_question"] is None


def test_ambiguous_changes_need_confirmation_and_retrieved_task_is_pinned(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply(bordered()))
    second, _ = ask(conversation, requests, reply(bordered(2)), prompt="Thicken borders")
    task = conversation.tasks()[-1]
    ask(conversation, requests, reply(bordered(3)), prompt="Thicken borders again")
    prompt = "Go back to before we thickened the borders"
    evidence = navigation("before", "before we thickened the borders",
                          task_id=task.task_id, field="recipe.photos.1.border.width_px")
    model = FakeModel(
        intent("select", proposal_id=first, navigation=evidence),
        intent("question", question=f"Do you mean {first}, before the first border increase?",
               return_confirmation={"proposal_id": first, "action": "select", "evidence": evidence}),
    )
    result = asyncio.run(conversation.request(prompt, model, requests))
    assert result.kind == "question"
    resumed = Conversation(conversation.store, "demo")
    context = resumed.context("Yes")
    assert context["required_tasks"][0]["task_id"] == task.task_id
    assert second != resumed.state.baseline
    model = FakeModel(intent("select", proposal_id=first, navigation=evidence))
    assert asyncio.run(resumed.request("Yes", model, requests)).proposal_id == first


@pytest.mark.parametrize("evidence,target", [
    (navigation("undo", "Undo the last two edits", steps=1), "P001"),
    (navigation("ordinal", "second"), "P001"),
    (navigation("before", "before thicker borders", task_id=1,
                field="recipe.photos.1.border.width_px"), "P001"),
])
def test_forged_destination_evidence_cannot_mutate_baseline(agent_project, evidence, target):
    conversation, requests = agent_project
    ask(conversation, requests, reply())
    latest, _ = ask(conversation, requests, reply())
    model = FakeModel(
        intent("select", proposal_id=target, navigation=evidence),
        intent("question", question="Which saved proposal do you mean?"),
    )
    result = asyncio.run(conversation.request(evidence["text"], model, requests))
    assert result.kind == "question" and conversation.state.baseline == latest
    assert len(model.contexts) == 2


def test_pure_return_cannot_be_regenerated_and_failed_compound_preserves_baseline(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    changed = layout_data()
    changed["canvas"]["background"] = "#202020"
    latest, _ = ask(conversation, requests, reply(changed))
    model = FakeModel(intent("edit", source=first), intent("select", proposal_id=first))
    result = asyncio.run(conversation.request(f"Return to {first}", model, requests))
    assert result.kind == "selection" and len(model.contexts) == 2
    ask(conversation, requests, action=intent("select", proposal_id=latest))
    model = FakeModel(intent("edit", source=first), CollageError("Simulated service failure"))
    with pytest.raises(CollageError, match="Simulated service failure"):
        asyncio.run(conversation.request(f"Return to {first} and resize photo 2", model, requests))
    assert conversation.state.baseline == latest
    assert conversation.tasks()[-1].outcome == "error"
    assert not conversation.tasks()[-1].changed


def test_grouping_evidence_is_verified_on_restart_without_a_trusted_cache(agent_project):
    conversation, requests = agent_project
    ask(conversation, requests, reply())
    path = conversation.root / "events" / "000002.json"
    data = read_json(path)
    data["baseline_before"] = {"proposal_id": "P999", "accepted_version": None}
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CollageError, match="baseline evidence"):
        Conversation(conversation.store, "demo")


def test_unknown_or_root_undo_reports_missing_history(agent_project):
    conversation, requests = agent_project
    ask(conversation, requests, reply())
    context = conversation.context("Undo the last two edits")
    assert "error" in context["navigation_lookup"]
    assert "proposal_id" not in context["navigation_lookup"]
    with pytest.raises(CollageError, match="beyond"):
        undo_target(conversation.tasks(), conversation._current_source(), 2)


def test_descriptive_return_can_find_a_change_on_an_abandoned_branch(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply(bordered()))
    old_branch, _ = ask(conversation, requests, reply(bordered(3)), prompt="Thicken borders")
    task = conversation.tasks()[-1]
    ask(conversation, requests, action=intent("select", proposal_id=first))
    changed = bordered()
    changed["canvas"]["background"] = "#202020"
    ask(conversation, requests, reply(changed))
    model = FakeModel(intent("select", proposal_id=old_branch, navigation=navigation(
        "after", "after we thickened the borders",
        task_id=task.task_id, field="recipe.photos.1.border.width_px",
    )))
    result = asyncio.run(conversation.request("Go back to after we thickened the borders", model, requests))
    assert result.proposal_id == old_branch and len(model.contexts) == 1


@pytest.mark.parametrize("qualifier", ["on this branch", "the last time"])
def test_explicit_branch_or_last_change_avoids_unnecessary_confirmation(agent_project, qualifier):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply(bordered()))
    ask(conversation, requests, reply(bordered(3)), prompt="Thicken borders")
    ask(conversation, requests, action=intent("select", proposal_id=first))
    target, _ = ask(conversation, requests, reply(bordered(2)), prompt="Thicken borders")
    task = conversation.tasks()[-1]
    prompt = f"Go back to after we thickened borders {qualifier}"
    model = FakeModel(intent("select", proposal_id=target, navigation=navigation(
        "after", prompt, task_id=task.task_id, field="recipe.photos.1.border.width_px",
    )))
    assert asyncio.run(conversation.request(prompt, model, requests)).proposal_id == target
    assert len(model.contexts) == 1


def test_working_baseline_cannot_be_changed_without_a_navigation_event(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    ask(conversation, requests, reply())
    state = read_json(conversation.state_path)
    state["baseline"] = first
    conversation.state_path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(CollageError, match="recorded navigation"):
        Conversation(conversation.store, "demo")
