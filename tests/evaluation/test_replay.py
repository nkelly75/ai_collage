import asyncio
import json
from pathlib import Path

import pytest

from ai_collage.agent.requests import RequestLog
from ai_collage.agent.files import digest
from ai_collage.agent.conversation import Conversation
from ai_collage.engine.models import CollageError
from ai_collage.engine.projects import read_json
from ai_collage.evaluation.replay import ReplayReport, replay
from ai_collage.cli.replay import main

from ..helpers import REPO, layout_data
from ..agent.test_agent import FakeModel, asyncio_wakeup_pair, intent, photo_name, photo_reference, reply, turns


@pytest.fixture
def scenario(tmp_path, sources):
    path = tmp_path / "sequence.json"
    data = {
        "name": "offline-replay",
        "images": [str(source) for source in sources],
        "canvas": {"width": 100, "height": 100},
        "messages": [
            {"name": "initial", "prompt": "Make a collage."},
            {"name": "edit", "prompt": "Change the background.", "reopen_before": True},
        ],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, data


def execute(store, path, model, **options):
    return asyncio.run(replay(store, "demo", path, client=model, **options))


@pytest.mark.parametrize("generation", ["high", "low"])
@pytest.mark.parametrize("interpretation", ["high", "low"])
def test_reasoning_candidate_is_fixed_on_resume_and_verified_offline(
    store, scenario, generation, interpretation,
):
    from ai_collage.evaluation.assess import assess

    path, _ = scenario
    model = FakeModel(*turns(reply(), reply()))
    options = dict(generation_reasoning=generation, interpretation_reasoning=interpretation)
    first = execute(store, path, model, **options)
    assert first.generation_reasoning == generation
    assert first.interpretation_reasoning == interpretation
    captured = (store.project_dir("demo") / "replay" / "report.json").read_bytes()
    for field in options:
        changed = {**options, field: "high" if options[field] == "low" else "low"}
        with pytest.raises(CollageError, match="reasoning changed"):
            execute(store, path, model, resume=True, **changed)
    if generation == "high" or interpretation == "low":
        with pytest.raises(CollageError, match="reasoning changed"):
            execute(store, path, model, resume=True)
    assert len(model.contexts) == 2
    assert (store.project_dir("demo") / "replay" / "report.json").read_bytes() == captured
    report = execute(store, path, model, resume=True, **options)
    assert report.next_step == 2 and assess(store, "demo").passed
    request_path = store.project_dir("demo") / "conversation" / "requests" / "attempt-0001.json"
    data = read_json(request_path)
    data["reasoning_effort"] = "high" if interpretation == "low" else "low"
    request_path.write_text(json.dumps(data), encoding="utf-8")
    assert not assess(store, "demo").passed


@pytest.mark.parametrize("interpretation", ["high", "low"])
def test_timeout_retry_preserves_original_answer_and_auditable_task(store, scenario, interpretation):
    from ai_collage.agent.requests import StageTimeout
    from ai_collage.evaluation.assess import assess

    path, _ = scenario
    options = dict(interpretation_reasoning=interpretation, generation_reasoning="low")
    model = FakeModel(
        intent("question", question="Which photo?"),
        "{}", intent("fresh"), StageTimeout("offline timeout"),
        intent("resume"), reply(),
        intent("edit", source="current"), reply(),
    )
    assert execute(store, path, model, **options).executions[-1].status == "question"
    failed = execute(store, path, model, resume=True, answer="2", answer_origin="user", **options)
    assert failed.executions[-1].status == "failed"
    resumed = execute(store, path, model, resume=True, retry=True, remaining=True, **options)
    assert resumed.next_step == 2
    assert resumed.executions[2].answer == "2"
    assert model.contexts[5]["original_task"] == "Make a collage."
    assert model.contexts[5]["active_task"]["answers"] == ["2"]
    attempts = RequestLog(store, "demo").attempts()
    assert [a.reasoning_effort for a in attempts] == [
        interpretation, interpretation, interpretation, "low",
        interpretation, "low", interpretation, "low",
    ]
    assert assess(store, "demo").passed


@pytest.mark.parametrize("naming_first", [False, True])
def test_naming_receipt_pauses_replay_until_explicit_approval_without_changing_baseline(
    store, scenario, naming_first,
):
    from ai_collage.evaluation.assess import assess

    path, data = scenario
    naming_prompt = "Photo 2 is breakfast"
    messages = [
        {"name": "name-photo", "prompt": naming_prompt},
        {"name": "initial", "prompt": "Make a collage.", "reopen_before": True},
    ]
    naming = intent("remember", name_updates=[photo_name("breakfast", 2, naming_prompt)])
    if not naming_first:
        messages.reverse()
    original = "Photo 1 is breakfast"
    data["messages"] = [{"name": "original-name", "prompt": original}, *messages]
    path.write_text(json.dumps(data), encoding="utf-8")
    execute(store, path, FakeModel(intent("remember", name_updates=[photo_name("  breakfast  ", 1, original)])))
    if not naming_first:
        first = execute(store, path, FakeModel(intent("fresh"), reply()), resume=True)
        assert first.next_step == 2
    paused = execute(store, path, FakeModel(naming), resume=True)
    gate = paused.executions[-1]
    assert gate.status == "name_confirmation" and paused.next_step == (1 if naming_first else 2)
    assert gate.attempts == 1 and gate.receipt_event == gate.event_id
    pending = Conversation(store, "demo")
    assert pending.state.photo_names[0].photo_id == 1
    assert pending.state.baseline == (None if naming_first else "P001")
    assessment = assess(store, "demo")
    assert not assessment.complete and assessment.cases[-1].status == "not_assessed"
    assert not assessment.cases[-1].errors
    with pytest.raises(CollageError, match="paused"):
        execute(store, path, FakeModel(), resume=True)
    responses = [intent("names", decision="approve", receipt_event=gate.event_id)]
    if naming_first:
        responses.extend([intent("fresh"), reply()])
    client = FakeModel(*responses)
    report = execute(
        store, path, client, resume=True, remaining=True,
        answer="Yes, remember those", answer_origin="user",
    )
    acknowledged = next(item for item in report.executions if item.name_decision == "approve")
    assert report.next_step == 3 and acknowledged.attempts == 1
    assert acknowledged.proposal_id is None and acknowledged.source is None
    assert acknowledged.intent is None and acknowledged.preview_path is None
    assert acknowledged.changes == [] and "breakfast = photo 2" in acknowledged.acknowledgement
    assert acknowledged.name_decision == "approve" and acknowledged.receipt_event == gate.event_id
    assert acknowledged.answers_execution == (2 if naming_first else 3)
    conversation = Conversation(store, "demo")
    assert conversation.state.baseline == "P001" and conversation.state.photo_names[0].photo_id == 2
    assert len(list((conversation.root / "proposals").iterdir())) == 1
    assert assess(store, "demo").passed
    assert [item.name for item in conversation.state.photo_names] == ["breakfast"]
    if naming_first:
        assert client.contexts[1]["photo_names"][0]["name"] == "breakfast"


def test_rejected_naming_replay_records_a_discarded_task_without_a_proposal(store, scenario):
    from ai_collage.evaluation.assess import assess

    path, data = scenario
    prompt = "Photo 2 is breakfast; move breakfast higher"
    original = "Photo 1 is breakfast"
    data["messages"] = [
        {"name": "original", "prompt": original}, {"name": "teach-and-edit", "prompt": prompt},
    ]
    path.write_text(json.dumps(data), encoding="utf-8")
    execute(store, path, FakeModel(intent("remember", name_updates=[photo_name("breakfast", 1, original)])))
    paused = execute(store, path, FakeModel(intent(
        "fresh", references=[photo_reference("breakfast", 2)],
        name_updates=[photo_name("breakfast", 2, "Photo 2 is breakfast")],
    )), resume=True)
    gate = paused.executions[-1]
    report = execute(
        store, path, FakeModel(intent("names", decision="reject", receipt_event=gate.event_id)),
        resume=True, answer="No, that's not right", answer_origin="user",
    )
    result = report.executions[-1]
    assert report.next_step == 2 and result.status == "acknowledgement"
    assert result.name_decision == "reject" and result.attempts == 1
    assert "not applied" in result.acknowledgement
    conversation = Conversation(store, "demo")
    assert conversation.state.photo_names[0].photo_id == 1 and conversation.state.baseline is None
    assert assess(store, "demo").passed


def test_confirmed_teaching_with_exact_return_assesses_as_selection_not_generation(store, scenario):
    from ai_collage.evaluation.assess import assess

    path, data = scenario
    original = "Photo 1 is castle"
    data["messages"].insert(0, {"name": "original", "prompt": original})
    prompt = "Photo 2 is castle; return to P001"
    data["messages"].append({"name": "teach-and-return", "prompt": prompt})
    path.write_text(json.dumps(data), encoding="utf-8")
    paused = execute(store, path, FakeModel(
        intent("remember", name_updates=[photo_name("castle", 1, original)]),
        *turns(reply(), reply()),
        intent("select", proposal_id="P001", navigation={"kind": "id", "text": "P001"},
               name_updates=[photo_name("castle", 2, "Photo 2 is castle")]),
    ), remaining=True)
    gate = paused.executions[-1]
    report = execute(
        store, path, FakeModel(intent("names", decision="approve", receipt_event=gate.event_id)),
        resume=True, answer="Yes, remember those", answer_origin="user",
    )
    result = report.executions[-1]
    assert result.status == "selection" and result.proposal_id == "P001"
    assert result.name_decision == "approve" and result.attempts == 1
    assert Conversation(store, "demo").state.baseline == "P001"
    assert assess(store, "demo").passed


def test_stepwise_resume_allows_only_future_edits_and_captures_evidence(store, scenario, tmp_path):
    path, data = scenario
    changed = layout_data()
    changed["canvas"]["background"] = "#202020"
    model = FakeModel(*turns(reply(), reply(changed)))
    first = execute(store, path, model)
    assert first.next_step == 1 and len(model.contexts) == 2
    root = store.project_dir("demo") / "replay"
    original = {
        item: item.read_bytes()
        for item in (root / "steps" / "0001").iterdir()
    }
    preview = Path(first.executions[0].preview_path)
    preview_bytes = preview.read_bytes()
    path = path.rename(tmp_path / "renamed-sequence.json")
    data["messages"][1]["prompt"] = "Use a dark grey background; leave everything else alone."
    path.write_text(json.dumps(data), encoding="utf-8")
    resumed = execute(store, path, model, resume=True, remaining=True)
    assert resumed.next_step == 2 and len(model.contexts) == 4
    result = resumed.executions[-1]
    assert result.reopened and result.status == "proposal"
    assert result.attempts == 2 and result.validation_corrections == 0
    assert [change.field for change in result.changes] == ["recipe.canvas.background"]
    assert read_json(Path(result.contexts[0]))["user_request"] == data["messages"][1]["prompt"]
    assert model.contexts[3]["editing_baseline"] == read_json(
        Path(first.executions[0].proposal_path)
    )["recipe"]
    assert all(item.read_bytes() == raw for item, raw in original.items())
    assert preview.read_bytes() == preview_bytes
    assert read_json(root / "steps" / "0001" / "sequence.json")["messages"][1]["prompt"] != (
        data["messages"][1]["prompt"]
    )
    assert ReplayReport.model_validate(read_json(root / "report.json")) == resumed
    assert store.load("demo").current_version is None
    assert Conversation(store, "demo").state.accepted_proposal is None
    assert execute(store, path, model, resume=True).next_step == 2
    assert len(model.contexts) == 4


def test_remaining_reopens_at_the_declared_message(store, scenario, monkeypatch):
    path, _ = scenario
    requests = RequestLog(store, "demo")
    opened = []

    class ObservedConversation(Conversation):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            opened.append(self.state.baseline)

    monkeypatch.setattr("ai_collage.evaluation.replay.Conversation", ObservedConversation)
    result = execute(store, path, FakeModel(*turns(reply(), reply())), remaining=True)
    assert opened == [None, "P001"]
    assert result.next_step == 2 and len(requests.attempts()) == 4


def test_failure_stops_batch_and_requires_explicit_retry(store, scenario):
    path, _ = scenario
    model = FakeModel(*turns(reply()), CollageError("Service stopped"),
                      intent("edit", source="current"), reply())
    result = execute(store, path, model, remaining=True)
    assert result.next_step == 1 and len(model.contexts) == 3
    assert result.executions[-1].status == "failed"
    assert "Service stopped" in result.executions[-1].error
    failure_path = store.project_dir("demo") / "replay" / "steps" / "0002" / "result.json"
    failure = failure_path.read_bytes()
    with pytest.raises(CollageError, match="explicit"):
        execute(store, path, model, resume=True)
    result = execute(store, path, model, resume=True, retry=True)
    assert result.next_step == 2 and len(model.contexts) == 5
    assert failure_path.read_bytes() == failure
    assert len(result.executions) == 3 and result.executions[1].status == "failed"


def test_pre_dispatch_failure_is_preserved_without_spending_an_attempt(store, scenario):
    path, _ = scenario
    requests = RequestLog(store, "demo")

    class AuthenticationFailure:
        async def complete(self, context, requests, purpose):
            raise CollageError("Authentication unavailable")

    report = execute(store, path, AuthenticationFailure(), remaining=True)
    assert report.next_step == 0
    assert report.executions[0].attempts == 0
    assert len(report.executions[0].contexts) == 1
    assert requests.attempts() == []
    assert Conversation(store, "demo").history()[-1].attempt is None
    with pytest.raises(CollageError, match="explicit"):
        execute(store, path, FakeModel(reply()), resume=True)


@pytest.mark.parametrize("failed", [False, True])
def test_context_capture_retains_provider_side_size_trimming(store, scenario, failed):
    path, _ = scenario

    class TrimmedModel(FakeModel):
        async def complete(self, context, requests, purpose):
            context["history"] = []
            context["history_omitted"] += 1
            return await super().complete(context, requests, purpose)

    model = TrimmedModel(CollageError("essential context too large")) if failed else TrimmedModel(*turns(reply()))
    report = execute(store, path, model)
    for captured, actual in zip(report.executions[0].contexts, model.contexts, strict=True):
        assert read_json(Path(captured)) == actual
        assert actual["history_omitted"] == 1
    assert report.executions[0].status == ("failed" if failed else "proposal")


def test_question_stops_without_advancing_or_answering(store, scenario):
    path, _ = scenario
    model = FakeModel(intent("question", question="Which photo?"), reply())
    report = execute(store, path, model, remaining=True)
    assert report.next_step == 0 and len(model.contexts) == 1
    assert report.executions[0].question == "Which photo?"
    assert report.executions[0].status == "question"
    with pytest.raises(CollageError, match="question"):
        execute(store, path, model, resume=True, retry=True)
    assert len(model.contexts) == 1


def test_validation_corrections_capture_each_context(store, scenario):
    path, _ = scenario
    report = execute(store, path, FakeModel("not JSON", intent("fresh"), reply()))
    result = report.executions[0]
    assert result.status == "proposal" and result.attempts == 3
    assert result.validation_corrections == 1 and len(result.contexts) == 3
    assert read_json(Path(result.contexts[0]))["validation_feedback"] is None
    assert read_json(Path(result.contexts[1]))["validation_feedback"]


def test_question_matching_a_proposal_id_is_not_treated_as_a_proposal(store, scenario):
    path, _ = scenario
    report = execute(
        store, path,
        FakeModel(*turns(reply()), intent("question", question="P001")), remaining=True,
    )
    assert report.next_step == 1
    assert report.executions[-1].status == "question"
    assert report.executions[-1].proposal_id is None


def test_instructions_changing_during_correction_stop_before_another_call(store, scenario, monkeypatch):
    path, _ = scenario
    requests = RequestLog(store, "demo")

    class ChangedInstructions(FakeModel):
        async def complete(self, context, requests, purpose):
            response = await super().complete(context, requests, purpose)
            monkeypatch.setattr("ai_collage.evaluation.replay.instruction_bundle", lambda: "Changed instructions")
            return response

    model = ChangedInstructions("not JSON", reply())
    report = execute(store, path, model)
    assert report.executions[0].status == "failed"
    assert "Instructions changed" in report.executions[0].error
    assert len(model.contexts) == 1 and len(requests.attempts()) == 1


def test_four_invalid_responses_stop_the_batch_before_the_next_message(store, scenario):
    path, _ = scenario
    requests = RequestLog(store, "demo")
    model = FakeModel(intent("fresh"), *["not JSON"] * 3, reply())
    report = execute(store, path, model, remaining=True)
    assert report.next_step == 0 and len(model.contexts) == 4
    assert len(report.executions) == 1
    assert report.executions[0].status == "failed"
    assert "correction failed" in report.executions[0].error
    assert len(requests.attempts()) == 4


def test_four_message_batch_cannot_make_more_than_sixteen_calls(store, scenario):
    path, data = scenario
    data["messages"].extend([
        {"name": "third", "prompt": "Keep the layout."},
        {"name": "fourth", "prompt": "Keep the layout."},
    ])
    path.write_text(json.dumps(data), encoding="utf-8")
    model = FakeModel(*[
        response for index in range(4)
        for response in (
            intent("fresh") if index == 0 else intent("edit", source="current"), "{}", "{}", reply(),
        )
    ], reply())
    report = execute(store, path, model, remaining=True)
    assert report.next_step == 4 and len(model.contexts) == 16
    assert [result.attempts for result in report.executions] == [4] * 4
    assert [result.validation_corrections for result in report.executions] == [2] * 4
    assert len(RequestLog(store, "demo").attempts()) == 16
    assert not (store.owner_dir / "agent-runs").exists()
    execute(store, path, model, resume=True, remaining=True)
    assert len(model.contexts) == 16


@pytest.mark.parametrize("version", [1, 5, 6, 7])
def test_legacy_replay_version_is_rejected_without_rewriting(store, scenario, version):
    path, _ = scenario
    model = FakeModel(*turns(reply(), reply()))
    execute(store, path, model)
    root = store.project_dir("demo") / "replay"
    original = (root / "steps" / "0001" / "result.json").read_bytes()
    report = read_json(root / "report.json")
    report["record_version"] = version
    (root / "report.json").write_text(json.dumps(report), encoding="utf-8")
    from pydantic import ValidationError
    with pytest.raises(ValidationError, match="record_version"):
        execute(store, path, model, resume=True)
    assert (root / "steps" / "0001" / "result.json").read_bytes() == original
    assert not (store.owner_dir / "agent-runs").exists()


@pytest.mark.parametrize("field", ["generation_reasoning", "interpretation_reasoning"])
def test_replay_candidates_are_required_without_defaulting(store, scenario, field):
    from pydantic import ValidationError

    path, _ = scenario
    execute(store, path, FakeModel(*turns(reply())))
    report_path = store.project_dir("demo") / "replay" / "report.json"
    data = read_json(report_path)
    del data[field]
    report_path.write_text(json.dumps(data), encoding="utf-8")
    before = report_path.read_bytes()
    with pytest.raises(ValidationError, match=field):
        execute(store, path, FakeModel(), resume=True)
    assert report_path.read_bytes() == before


@pytest.mark.parametrize("change", ["prompt", "canvas", "source", "instructions", "conversation"])
def test_resume_rejects_changed_execution_identity(store, scenario, monkeypatch, change):
    path, data = scenario
    model = FakeModel(*turns(reply(), reply()))
    execute(store, path, model)
    if change == "prompt":
        data["messages"][0]["prompt"] = "A changed attempted message"
    elif change == "canvas":
        data["canvas"]["width"] = 120
    elif change == "source":
        data["images"].reverse()
    elif change == "instructions":
        monkeypatch.setattr("ai_collage.evaluation.replay.instruction_bundle", lambda: "Changed instructions")
    else:
        conversation = Conversation(store, "demo")
        conversation.controls(conversation.state.controls.model_copy(update={"cropping": True}))
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CollageError, match="changed"):
        execute(store, path, model, resume=True)
    assert len(model.contexts) == 2


def test_interrupted_step_cannot_be_blindly_replayed(store, scenario):
    path, _ = scenario
    requests = RequestLog(store, "demo")
    with pytest.raises(RuntimeError, match="interrupted"):
        execute(store, path, FakeModel(RuntimeError("interrupted")))
    report_path = store.project_dir("demo") / "replay" / "report.json"
    report = ReplayReport.model_validate(read_json(report_path))
    assert report.executions[0].status == "pending"
    with pytest.raises(CollageError, match="Interrupted"):
        execute(store, path, FakeModel(reply()), resume=True, retry=True)
    assert len(requests.attempts()) == 1


def test_inconsistent_cursor_cannot_skip_a_message(store, scenario):
    path, _ = scenario
    model = FakeModel(*turns(reply(), reply()))
    execute(store, path, model)
    report_path = store.project_dir("demo") / "replay" / "report.json"
    report = read_json(report_path)
    report["next_step"] = 2
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(CollageError, match="cursor"):
        execute(store, path, model, resume=True)
    assert len(model.contexts) == 2


def test_existing_project_is_not_overwritten(store, sources, scenario):
    path, _ = scenario
    store.create("demo", sources)
    metadata = store.project_dir("demo") / "project.json"
    before = digest(metadata.read_bytes())
    requests = RequestLog(store, "demo")
    with pytest.raises(CollageError, match="already exists"):
        execute(store, path, FakeModel(reply()))
    assert digest(metadata.read_bytes()) == before and not requests.attempts()


def test_check_validates_shipped_sequences_without_creating_data(tmp_path, capsys, monkeypatch):
    def forbidden():
        raise AssertionError("Offline check must not initialize a model")

    monkeypatch.setattr("ai_collage.evaluation.replay.FoundryModel", forbidden)
    for filename, name in (
        ("01_dark_portrait_adjustments.json", "checkpoint-a"),
        ("02_landscape_staggered_adjustments.json", "landscape-staggered"),
        ("03_named_photo_adjustments.json", "named-photo-adjustments"),
        ("04_exact_proposal_return.json", "exact-proposal-return"),
        ("05_clarification_continuation.json", "clarification-continuation"),
    ):
        sequence = REPO / "examples" / "sequences" / filename
        assert main(["--sequence", str(sequence), "--check", "--data-dir", str(tmp_path / "unused")]) == 0
        captured = json.loads(capsys.readouterr().out)
        assert len(captured["sources"]) == 4
        assert captured["sequence"]["name"] == name
    assert not (tmp_path / "unused").exists()


def test_invalid_sequence_fails_before_creating_a_project(store, scenario):
    path, data = scenario
    data["messages"][1]["name"] = "initial"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        execute(store, path, FakeModel(reply()))
    assert not store.project_dir("demo").exists()
    with pytest.raises(SystemExit) as exc:
        main(["--sequence", str(path)])
    assert exc.value.code == 2


@pytest.mark.parametrize("response,code", [
    (reply(), 0),
    (intent("question", question="Which photo?"), 1),
    (CollageError("Service failed"), 1),
])
def test_cli_runs_one_step_and_reports_stop_status(store, scenario, monkeypatch, capsys, response, code):
    path, _ = scenario
    responses = turns(response) if isinstance(response, str) and "schema_version" in response else [response]
    model = FakeModel(*responses)
    monkeypatch.setattr("ai_collage.evaluation.replay.FoundryModel", lambda: model)
    assert main([
        "--sequence", str(path), "--data-dir", str(store.data_dir),
        "--project", "demo",
    ]) == code
    report = json.loads(capsys.readouterr().out)
    assert len(report["executions"]) == 1
    assert report["generation_reasoning"] == "low"
    assert report["interpretation_reasoning"] == "high"


def test_cli_independent_reasoning_overrides_are_captured(store, scenario, monkeypatch, capsys):
    path, _ = scenario
    model = FakeModel(*turns(reply()))
    monkeypatch.setattr("ai_collage.evaluation.replay.FoundryModel", lambda: model)
    assert main([
        "--sequence", str(path), "--data-dir", str(store.data_dir), "--project", "demo",
        "--generation-reasoning", "high", "--interpretation-reasoning", "low",
    ]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["generation_reasoning"] == "high"
    assert report["interpretation_reasoning"] == "low"
    assert [a.reasoning_effort for a in RequestLog(store, "demo").attempts()] == ["low", "high"]


def test_recorded_clarification_continues_script_and_assesses_as_assisted(store, scenario):
    from ai_collage.evaluation.assess import assess

    path, data = scenario
    model = FakeModel(
        intent("question", question="Which photo should stand out?"),
        intent("fresh"), reply(),
        intent("edit", source="current"), reply(),
    )
    first = execute(store, path, model, remaining=True)
    root = store.project_dir("demo") / "replay"
    original = (root / "steps" / "0001" / "result.json").read_bytes()
    resumed = execute(
        store, path, model, resume=True, remaining=True,
        answer="Photo 2", answer_origin="copilot",
    )
    assert resumed.next_step == 2 and len(model.contexts) == 5
    assert [entry.status for entry in resumed.executions] == ["question", "proposal", "proposal"]
    answered = resumed.executions[1]
    assert answered.answer == "Photo 2" and answered.answer_origin == "copilot"
    assert answered.answers_execution == 1 and answered.prompt == data["messages"][0]["prompt"]
    assert read_json(Path(answered.contexts[0]))["user_request"] == "Photo 2"
    assert (root / "steps" / "0001" / "result.json").read_bytes() == original
    report = assess(store, "demo")
    assert report.passed and report.clarification_assisted
    resumed_again = execute(store, path, model, resume=True)
    assert resumed_again.next_step == 2 and len(model.contexts) == 5


def test_answer_failure_can_be_explicitly_retried_without_resetting_outer_cap(store, scenario, tmp_path):
    from ai_collage.agent.requests import call_budget
    from ai_collage.evaluation.assess import assess

    path, _ = scenario
    budget = tmp_path / "budget.json"
    model = FakeModel(
        intent("question", question="Which photo?"),
        CollageError("Connection failed"),
        *turns(reply(), reply()),
    )
    with call_budget(budget, 6):
        execute(store, path, model)
    with call_budget(budget, 6):
        failed = execute(store, path, model, resume=True, answer="Photo 2", answer_origin="user")
    assert failed.executions[-1].status == "failed"
    with call_budget(budget, 6):
        result = execute(store, path, model, resume=True, retry=True, remaining=True)
    assert result.next_step == 2
    assert read_json(budget)["used"] == 6
    assert result.executions[2].answer == "Photo 2"
    assert result.executions[2].answers_execution == 1
    assert assess(store, "demo").passed
    with call_budget(budget, 6):
        with pytest.raises(CollageError, match="exhausted"):
            RequestLog(store, "another-project").reserve("must not dispatch", 10)


def test_clarification_limit_blocks_third_answer_without_calls(store, scenario):
    path, _ = scenario
    model = FakeModel(*(intent("question", question="Which one?") for _ in range(3)))
    execute(store, path, model)
    for answer in ("Photo 1", "The first photo"):
        execute(store, path, model, resume=True, answer=answer, answer_origin="copilot")
    with pytest.raises(CollageError, match="Two clarification answers"):
        execute(store, path, model, resume=True, answer="Photo 1 again", answer_origin="copilot")
    assert len(model.contexts) == len(RequestLog(store, "demo").attempts()) == 3


def test_selection_fresh_and_older_source_edits_are_not_linearized(store, scenario):
    from ai_collage.evaluation.assess import assess

    path, data = scenario
    data["messages"].extend([
        {"name": "return", "prompt": "Go back to first"},
        {"name": "compound", "prompt": "Go back to second and change the background"},
        {"name": "fresh", "prompt": "Start over"},
    ])
    path.write_text(json.dumps(data), encoding="utf-8")
    changed = layout_data()
    changed["canvas"]["background"] = "#202020"
    model = FakeModel(
        *turns(reply(), reply(changed)),
        intent("select", proposal_id="P001", navigation={"kind": "ordinal", "text": "first"}),
        intent("edit", source="P002", navigation={"kind": "ordinal", "text": "second"}),
        reply(), intent("fresh"), reply(),
    )
    report = execute(store, path, model, remaining=True)
    assert report.next_step == 5
    selection, compound, fresh = report.executions[2:]
    assert selection.status == "selection" and selection.changes == [] and selection.attempts == 1
    assert compound.baseline_before == "P001" and compound.source.proposal_id == "P002"
    assert [change.field for change in compound.changes] == ["recipe.canvas.background"]
    assert fresh.source is None and fresh.changes == []
    assert assess(store, "demo").passed
    assert len(list((store.project_dir("demo") / "conversation" / "proposals").iterdir())) == 4


def test_return_confirmation_resume_preserves_exact_selection_and_assesses_offline(store, scenario):
    from ai_collage.evaluation.assess import assess

    path, data = scenario
    data["messages"].append({"name": "return", "prompt": "Return to the first one"})
    path.write_text(json.dumps(data), encoding="utf-8")
    evidence = {"kind": "ordinal", "text": "first"}
    model = FakeModel(
        *turns(reply(), reply()),
        intent("question", question="Do you mean P001?",
               return_confirmation={"proposal_id": "P001", "action": "select", "evidence": evidence}),
    )
    pending = execute(store, path, model, remaining=True)
    assert pending.next_step == 2 and pending.executions[-1].status == "question"
    model = FakeModel(intent("select", proposal_id="P001", navigation=evidence))
    result = execute(store, path, model, resume=True, answer="Yes", answer_origin="copilot")
    assert result.next_step == 3 and result.executions[-1].status == "selection"
    assert result.executions[-1].changes == [] and len(model.contexts) == 1
    assert assess(store, "demo").passed


def test_only_intent_prompt_change_also_blocks_resume(store, scenario, monkeypatch):
    from ai_collage.agent import provider as agent_provider

    path, _ = scenario
    model = FakeModel(*turns(reply()))
    execute(store, path, model)
    original = agent_provider.instructions
    monkeypatch.setattr(
        agent_provider, "instructions",
        lambda stage="generation": original(stage) + (" changed" if stage == "interpretation" else ""),
    )
    with pytest.raises(CollageError, match="instructions changed"):
        execute(store, path, model, resume=True)
    assert len(model.contexts) == 2


def test_shipped_landscape_sequence_runs_all_four_messages_with_controlled_two_stage_responses(store):
    import copy
    pytest.importorskip("agent_framework")
    import httpx
    from openai import AsyncOpenAI
    from ai_collage.agent.provider import ENDPOINT, guarded_transport, run_agent
    from ai_collage.evaluation.assess import assess
    from ..agent.test_agent import response_envelope

    path = REPO / "examples" / "sequences" / "02_landscape_staggered_adjustments.json"
    initial = {
        "schema_version": 3,
        "canvas": {"width": 1600, "height": 900, "background": "#EEEEEE"},
        "layers": [
            {"photo_id": number, "mode": "whole",
             "box": {"center_x": x, "center_y": y, "width": width}, "corner_radius_px": 8}
            for number, x, y, width in (
                (1, 0.14, 0.18, 0.13), (2, 0.18, 0.5, 0.13),
                (3, 0.72, 0.5, 0.4), (4, 0.2, 0.82, 0.13),
            )
        ],
    }
    swapped = copy.deepcopy(initial)
    for axis in ("center_x", "center_y"):
        swapped["layers"][0]["box"][axis], swapped["layers"][3]["box"][axis] = (
            initial["layers"][3]["box"][axis], initial["layers"][0]["box"][axis],
        )
    smaller = copy.deepcopy(swapped)
    smaller["layers"][1]["box"].update(center_x=0.4, width=0.1)
    square = copy.deepcopy(smaller)
    square["layers"][2]["corner_radius_px"] = 0
    responses = iter(turns(*(reply(value) for value in (initial, swapped, smaller, square))))

    class TransportModel:
        def __init__(self):
            self.contexts = []

        async def complete(self, context, requests, purpose):
            self.contexts.append(context)

            async def handler(request):
                return httpx.Response(200, json=response_envelope(next(responses)))

            gate = guarded_transport(requests, purpose, httpx.MockTransport(handler))
            async with AsyncOpenAI(
                base_url=ENDPOINT, api_key="offline-not-a-real-credential", max_retries=0,
                http_client=httpx.AsyncClient(transport=gate),
            ) as sdk:
                return await run_agent(context, sdk, requests)

    model = TransportModel()
    report = execute(store, path, model, remaining=True)
    assert report.next_step == 4 and len(model.contexts) == 8
    assert all(result.attempts == 2 and result.validation_corrections == 0 for result in report.executions)
    assert all(attempt.input_bound <= 50_000 for attempt in RequestLog(store, "demo").attempts())
    assert assess(store, "demo").passed
