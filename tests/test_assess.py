import asyncio
import copy
import json
from pathlib import Path

import pytest

from ai_collage.assess import assess, dark_portrait_errors, main
from ai_collage.projects import read_json
from ai_collage.replay import replay
from ai_collage.models import CollageError

from .helpers import REPO, layout_data, photo_file
from .test_agent import FakeModel, agent_project, asyncio_wakeup_pair, intent, reply, turns
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
    from ai_collage.geometry import resolve_layout
    from ai_collage.models import InputLayout

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

    monkeypatch.setattr("ai_collage.conversation.Conversation.__init__", forbidden)
    monkeypatch.setattr("ai_collage.conversation.Conversation.accept", forbidden)
    monkeypatch.setattr("ai_collage.agent_provider.FoundryModel.complete", forbidden)
    monkeypatch.setattr("ai_collage.agent_requests.RequestLog.__init__", forbidden)
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
