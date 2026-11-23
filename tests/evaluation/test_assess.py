import asyncio
import copy
import json
from pathlib import Path

import pytest

from ai_collage.evaluation.assess import assess, dark_portrait_errors
from ai_collage.cli.assess import main
from ai_collage.engine.projects import read_json
from ai_collage.evaluation.replay import replay
from ai_collage.engine.models import CollageError

from ..helpers import REPO, layout_data, photo_file
from ..agent.test_agent import FakeModel, agent_project, asyncio_wakeup_pair, intent, photo_name, photo_reference, reply, turns
from .test_replay import execute, scenario


@pytest.fixture
def saved_replay(store, scenario):
    path, _ = scenario
    execute(store, path, FakeModel(*turns(reply(), reply())), remaining=True)
    return store.project_dir("demo")


@pytest.fixture
def dark_replay(store, tmp_path, sources):
    def create(*, border_color="#FFFFFF", unrelated_edit=False):
        images = [*sources, photo_file(tmp_path / "three.png"), photo_file(
            tmp_path / "four.png", (20, 40), "green",
        )]
        sequence = read_json(REPO / "examples" / "sequences" / "01_dark_portrait_adjustments.json")
        sequence["images"] = [str(path) for path in images]
        path = tmp_path / "dark.json"
        path.write_text(json.dumps(sequence), encoding="utf-8")
        initial = {
            "schema_version": 3,
            "canvas": {"width": 1200, "height": 1800, "background": "#282828"},
            "layers": [
                {
                    "photo_id": number,
                    "mode": "whole",
                    "box": {"center_x": x, "center_y": y, "width": width},
                    "border": {"width_px": 1, "color": border_color},
                    "corner_radius_px": 1,
                    "rotation_degrees": 1,
                }
                for number, x, y, width in (
                    (1, 0.25, 0.25, 0.3), (2, 0.75, 0.3, 0.12),
                    (3, 0.25, 0.7, 0.3), (4, 0.75, 0.7, 0.3),
                )
            ],
        }
        resized = copy.deepcopy(initial)
        resized["layers"][1]["box"]["width"] = 0.1
        if unrelated_edit:
            resized["layers"][0]["corner_radius_px"] = 2
        borderless = copy.deepcopy(resized)
        for layer in borderless["layers"]:
            layer["border"] = None
        straight = copy.deepcopy(borderless)
        for layer in straight["layers"]:
            layer["rotation_degrees"] = 0
        asyncio.run(replay(
            store, "dark", path, remaining=True,
            client=FakeModel(*turns(*(reply(data) for data in (initial, resized, borderless, straight)))),
        ))
        return store.project_dir("dark")
    return create


@pytest.mark.parametrize("border_color", ["#FFFFFF", "#F5F5F5", "#F0F0F0", "#F0FAFF"])
def test_dark_portrait_profile_checks_saved_results(dark_replay, store, border_color):
    dark_replay(border_color=border_color)
    report = assess(store, "dark", profile="dark-portrait-adjustments")
    assert report.complete and report.passed and not report.errors
    assert [case.status for case in report.cases] == ["passed"] * 4
    assert store.load("dark").current_version is None


def test_dark_portrait_checks_preserve_exact_unrelated_fields(agent_project):
    from ai_collage.engine.geometry import resolve_layout
    from ai_collage.engine.models import InputLayout

    conversation, _ = agent_project
    photos = conversation.store.load("demo").photos

    def resolve(value):
        return resolve_layout(InputLayout.model_validate(value), photos, 1)

    data = layout_data()
    data["canvas"]["background"] = "#282828"
    data["layers"][0]["box"]["width"] = 0.4
    data["layers"][0]["box"].update(center_x=0.3, center_y=0.3)
    for layer in data["layers"]:
        layer.update(border={"width_px": 1, "color": "#FFFFFF"}, corner_radius_px=1, rotation_degrees=1)
    initial = resolve(data)
    assert dark_portrait_errors(0, initial, None) == []
    smaller = copy.deepcopy(data)
    smaller["layers"][1]["box"]["width"] = 0.18
    resized = resolve(smaller)
    assert dark_portrait_errors(1, resized, initial) == []
    shifted = copy.deepcopy(smaller)
    shifted["layers"][1]["box"]["center_x"] += 0.0001
    assert "Unrelated" in " ".join(dark_portrait_errors(1, resolve(shifted), initial))
    changed = copy.deepcopy(smaller)
    changed["layers"][0]["corner_radius_px"] = 2
    assert "Unrelated" in " ".join(dark_portrait_errors(1, resolve(changed), initial))
    for layer in smaller["layers"]:
        layer["border"] = None
    borderless = resolve(smaller)
    assert dark_portrait_errors(2, borderless, resized) == []
    for layer in smaller["layers"]:
        layer["rotation_degrees"] = 0
    straight = resolve(smaller)
    assert dark_portrait_errors(3, straight, borderless) == []
    smaller["layers"].reverse()
    assert "stacking" in " ".join(dark_portrait_errors(3, resolve(smaller), borderless))


@pytest.mark.parametrize("options,case,expected", [
    ({"border_color": "#FFFEEE"}, 0, "subtle-style"),
    ({"border_color": "#EFF0F0"}, 0, "subtle-style"),
    ({"border_color": "#F0EFF0"}, 0, "subtle-style"),
    ({"border_color": "#F0F0EF"}, 0, "subtle-style"),
    ({"unrelated_edit": True}, 1, "Unrelated"),
])
def test_profile_checks_style_and_edits_without_affecting_integrity(
    dark_replay, store, options, case, expected,
):
    dark_replay(**options)
    assert assess(store, "dark").passed
    report = assess(store, "dark", profile="dark-portrait-adjustments")
    assert report.complete and not report.passed
    assert expected in " ".join(report.cases[case].errors)


@pytest.mark.parametrize("fault,question_references", [
    (None, True), (None, False),
    ("wrong-target", True), ("wrong-size", True), ("centre", True), ("snapshot", True),
])
def test_photo_identity_profile_checks_every_saved_transition(
    store, tmp_path, sources, fault, question_references,
):
    from ai_collage.agent.files import save

    sequence = read_json(REPO / "examples" / "sequences" / "06_photo_identity_memory.json")
    sequence["images"] = [str(path) for path in [
        *sources, photo_file(tmp_path / "three.png"), photo_file(tmp_path / "four.png"),
    ]]
    path = tmp_path / "memory.json"
    path.write_text(json.dumps(sequence), encoding="utf-8")
    messages = sequence["messages"]
    initial = {
        "schema_version": 3, "canvas": {"width": 1200, "height": 1800, "background": "#FFFFFF"},
        "layers": [
            {"photo_id": number, "mode": "whole",
             "box": {"center_x": x, "center_y": y, "width": 0.24}}
            for number, x, y in ((1, 0.25, 0.25), (2, 0.75, 0.25), (3, 0.25, 0.75), (4, 0.75, 0.75))
        ],
    }
    breakfast = copy.deepcopy(initial)
    breakfast["layers"][1]["box"]["width"] *= 0.9
    favourite = copy.deepcopy(breakfast)
    favourite["layers"][0 if fault == "wrong-target" else 3]["box"]["width"] *= (
        0.8 if fault == "wrong-size" else 0.9
    )
    if fault == "centre":
        favourite["layers"][3]["box"]["center_x"] += 0.01
    final = copy.deepcopy(favourite)
    final["layers"][1]["box"]["width"] *= 0.9

    def question():
        return intent("question", question="Which photo is breakfast?",
                      references=[photo_reference("breakfast", None)] if question_references else [])

    def resize(step, name, number):
        return intent("edit", source="current", references=[photo_reference(name, number)],
                      name_updates=[photo_name(name, number, messages[step]["prompt"])] if name == "breakfast" else [])

    paused = execute(store, path, FakeModel(intent("fresh"), reply(initial), question()), remaining=True)
    assert paused.next_step == 1 and not paused.executions[-1].memory_after
    paused = execute(store, path, FakeModel(
        resize(1, "breakfast", 2), reply(breakfast), intent("list_names"),
        intent("remember", name_updates=[photo_name("favourite", 1, messages[3]["prompt"])]),
        intent("remember", name_updates=[photo_name("favourite", 4, messages[4]["prompt"])]),
    ), resume=True, answer="Photo 2", answer_origin="copilot", remaining=True)
    gate = paused.executions[-1]
    assert gate.status == "name_confirmation"
    paused = execute(store, path, FakeModel(
        intent("names", decision="approve", receipt_event=gate.event_id),
        resize(5, "favourite", 4), reply(favourite),
        intent("forget", name_updates=[photo_name("breakfast", None, messages[6]["prompt"])]),
        intent("list_names"), question(),
    ), resume=True, answer="Yes", answer_origin="copilot", remaining=True)
    assert paused.next_step == 8
    assert {item.name: item.photo_id for item in paused.executions[-1].memory_after} == {
        "breakfast": None, "favourite": 4,
    }
    report = execute(store, path, FakeModel(
        resize(8, "breakfast", 2), reply(final), intent("list_names"),
    ), resume=True, answer="Photo 2", answer_origin="copilot", remaining=True)
    assert report.next_step == 10 and assess(store, "demo").passed
    if fault == "snapshot":
        report.executions[3].memory_after = []
        root = store.project_dir("demo") / "replay"
        save(root / "report.json", report)
        save(root / "steps" / "0004" / "result.json", report.executions[3])
        assert not assess(store, "demo").passed
    assessment = assess(store, "demo", profile="photo-identity-memory")
    assert assessment.complete and assessment.passed == (fault is None)
    if fault is not None:
        assert any(case.errors for case in assessment.cases)
    assert store.load("demo").current_version is None


@pytest.mark.parametrize("fault", [
    "missing-question", "other-step", "other-task", "not-a-question", "no-answer",
    "wrong-answer-link", "pre-answer-memory", "pre-answer-layout",
])
def test_photo_identity_gate_rejects_missing_provenance_and_premature_changes(agent_project, fault):
    from ai_collage.agent.models import Exchange, PhotoName, ResolvedIntent
    from ai_collage.engine.geometry import resolve_layout
    from ai_collage.engine.models import InputLayout
    from ai_collage.evaluation.assess import identity_memory_errors
    from ai_collage.evaluation.replay import StepResult, authored_changes

    conversation, _ = agent_project
    photos = conversation.store.load("demo").photos
    initial = layout_data()
    smaller = copy.deepcopy(initial)
    smaller["layers"][1]["box"]["width"] *= 0.9
    prompt = "Make breakfast 10% smaller."
    learned = PhotoName(name="breakfast", photo_id=2, event_id=4, quote=prompt)
    question = Exchange(
        prompt=prompt, response=intent("question", question="Which numbered photo?"),
        outcome="question", stage="interpretation", parent="P001", run_id=None, task_id=3,
    )
    pending = StepResult(
        step=1, name="learn-breakfast", prompt=prompt, reopened=False,
        status="question", event_id=3, usage_before={},
    )
    result = StepResult(
        step=1, name="learn-breakfast", prompt=prompt, reopened=False, status="proposal",
        event_id=5, answer="Photo 2", answer_origin="copilot", answers_execution=1,
        usage_before={}, memory_after=[learned],
        intent=ResolvedIntent(
            action="edit", source={"proposal_id": "P001"}, task_turn=3, task_request=prompt,
            references=[{"text": "breakfast", "photo_id": 2}],
        ),
    )
    event = Exchange(
        prompt="Photo 2", outcome="proposal", stage="generation",
        parent="P001", run_id=None, task_id=3,
    )
    earlier = [] if fault == "missing-question" else [pending]
    if fault == "other-step":
        pending.step = 8
    elif fault == "other-task":
        question = question.model_copy(update={"task_id": 9})
    elif fault == "not-a-question":
        question = question.model_copy(update={"outcome": "intent"})
    elif fault == "no-answer":
        result.answer = None
    elif fault == "wrong-answer-link":
        result.answers_execution = 2
    elif fault == "pre-answer-memory":
        pending.memory_after = [learned]
    elif fault == "pre-answer-layout":
        pending.changes = authored_changes(initial, smaller)
    waiting = fault.startswith("pre-answer")
    errors = identity_memory_errors(
        pending if waiting else result, earlier,
        resolve_layout(InputLayout.model_validate(smaller), photos, 1),
        resolve_layout(InputLayout.model_validate(initial), photos, 1),
        {3: question, 5: event},
    )
    assert (
        "Question/receipt changed memory or the collage before an answer."
        if waiting else "Breakfast identity was used without the required preceding question."
    ) in errors


def test_wrong_profile_fails_explicitly(saved_replay, store):
    report = assess(store, "demo", profile="dark-portrait-adjustments")
    assert not report.passed
    assert "four named steps" in " ".join(report.errors)


def test_captured_instructions_use_the_same_text_hash_on_windows_and_unix(saved_replay, store):
    path = saved_replay / "replay" / "instructions.md"
    text = path.read_text(encoding="utf-8")
    for ending in ("\n", "\r\n"):
        path.write_bytes(text.replace("\n", ending).encode("utf-8"))
        assert assess(store, "demo").passed


def test_reopening_must_match_the_recorded_message(saved_replay, store):
    path = saved_replay / "replay" / "report.json"
    data = read_json(path)
    data["executions"][1]["reopened"] = False
    path.write_text(json.dumps(data), encoding="utf-8")
    path = saved_replay / "replay" / "steps" / "0002" / "result.json"
    data = read_json(path)
    data["reopened"] = False
    path.write_text(json.dumps(data), encoding="utf-8")
    report = assess(store, "demo")
    assert not report.passed and "message" in " ".join(report.cases[1].errors)


def test_cli_is_read_only_except_append_only_assessments(saved_replay, store, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("Assessment must not initialize a conversation/model/request log or accept.")

    monkeypatch.setattr("ai_collage.agent.conversation.Conversation.__init__", forbidden)
    monkeypatch.setattr("ai_collage.agent.conversation.Conversation.accept", forbidden)
    monkeypatch.setattr("ai_collage.agent.provider.FoundryModel.complete", forbidden)
    monkeypatch.setattr("ai_collage.agent.requests.RequestLog.__init__", forbidden)
    (saved_replay / "conversation" / "acceptance.json").write_text("{}", encoding="utf-8")
    original = {
        path: path.read_bytes()
        for path in store.data_dir.rglob("*") if path.is_file()
    }
    args = ["--data-dir", str(store.data_dir), "--project", "demo"]
    assert main(args) == 0
    first = json.loads(capsys.readouterr().out)
    first_path = Path(first["report_path"])
    first_bytes = first_path.read_bytes()
    assert first["profile"] == "integrity" and first["passed"]
    assert main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert Path(second["report_path"]).name == "0002.json"
    assert first_path.read_bytes() == first_bytes
    assert first["replay_sha256"] == second["replay_sha256"]
    assert all(path.read_bytes() == raw for path, raw in original.items())


@pytest.mark.parametrize("artifact", [
    "preview", "geometry", "instructions", "instructions-encoding", "source",
    "step-result", "cursor", "message",
])
def test_corrupt_evidence_is_not_reported_as_passing(saved_replay, store, artifact):
    root = saved_replay
    proposal = root / "conversation" / "proposals" / "P001"
    if artifact == "preview":
        (proposal / "preview.png").write_bytes(b"changed")
    elif artifact == "instructions":
        (root / "replay" / "instructions.md").write_text("changed", encoding="utf-8")
    elif artifact == "instructions-encoding":
        (root / "replay" / "instructions.md").write_bytes(b"\xff")
    elif artifact == "source":
        project = store.load("demo")
        store.photo_paths(project)[1].write_bytes(b"changed")
    else:
        if artifact == "geometry":
            path = proposal / "proposal.json"
            data = read_json(path)
            data["geometry"][0]["box_pixels"]["x"] += 1
        elif artifact == "step-result":
            path = root / "replay" / "steps" / "0001" / "result.json"
            data = read_json(path)
            data["attempts"] += 1
        else:
            path = root / "replay" / "report.json"
            data = read_json(path)
            if artifact == "cursor":
                data["next_step"] = 1
            else:
                data["executions"][0]["step"] = 100
        path.write_text(json.dumps(data), encoding="utf-8")
    report = assess(store, "demo")
    assert not report.passed
    assert report.errors or any(case.errors for case in report.cases)


@pytest.mark.parametrize("outcome", ["partial", "question", "failed", "pending"])
def test_incomplete_replays_do_not_pass(store, scenario, outcome):
    path, _ = scenario
    responses = {
        "partial": reply(),
        "question": intent("question", question="Which photo?"),
        "failed": CollageError("Service stopped"),
        "pending": RuntimeError("interrupted"),
    }
    if outcome == "pending":
        with pytest.raises(RuntimeError, match="interrupted"):
            execute(store, path, FakeModel(responses[outcome]))
    else:
        execute(store, path, FakeModel(*(
            turns(responses[outcome]) if outcome == "partial" else [responses[outcome]]
        )))
    report = assess(store, "demo")
    assert not report.complete and not report.passed
    assert "incomplete" in " ".join(report.errors)
    assert report.cases[0].status == ("passed" if outcome == "partial" else "not_assessed")


def test_retry_history_is_preserved_in_an_eventually_passing_assessment(store, scenario):
    path, _ = scenario
    model = FakeModel(CollageError("Service stopped"), *turns(reply(), reply()))
    execute(store, path, model)
    execute(store, path, model, resume=True, retry=True, remaining=True)
    report = assess(store, "demo")
    assert report.complete and report.passed
    assert [case.recorded_outcome for case in report.cases] == ["failed", "proposal", "proposal"]
    assert [case.status for case in report.cases] == ["not_assessed", "passed", "passed"]


def test_cli_writes_a_failed_assessment_and_returns_nonzero(saved_replay, store, capsys):
    assert main([
        "--data-dir", str(store.data_dir), "--project", "demo",
        "--profile", "dark-portrait-adjustments",
    ]) == 1
    report = json.loads(capsys.readouterr().out)
    assert not report["passed"] and Path(report["report_path"]).is_file()


@pytest.mark.parametrize("artifact", ["stage", "request-purpose", "source-differences"])
def test_current_stage_and_source_evidence_must_be_truthful(saved_replay, store, artifact):
    root = saved_replay / "replay"
    if artifact == "stage":
        path = root / "steps" / "0001" / "context-0001.json"
        data = read_json(path)
        data["stage"] = "generation"
        path.write_text(json.dumps(data), encoding="utf-8")
    elif artifact == "request-purpose":
        path = saved_replay / "conversation" / "requests" / "attempt-0002.json"
        data = read_json(path)
        data["purpose"] = "demo: interpretation"
        path.write_text(json.dumps(data), encoding="utf-8")
    else:
        path = root / "report.json"
        data = read_json(path)
        data["executions"][1]["changes"] = [
            {"field": "recipe.canvas.background", "before": "#FFFFFF", "after": "#000000"},
        ]
        path.write_text(json.dumps(data), encoding="utf-8")
        (root / "steps" / "0002" / "result.json").write_text(
            json.dumps(data["executions"][1]), encoding="utf-8",
        )
    report = assess(store, "demo")
    assert not report.passed and any(case.errors for case in report.cases)
