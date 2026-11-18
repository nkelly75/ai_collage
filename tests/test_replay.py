import asyncio
import json
from pathlib import Path

import pytest

from ai_collage.agent_requests import RequestLog
from ai_collage.agent_files import digest
from ai_collage.conversation import Conversation
from ai_collage.models import CollageError
from ai_collage.projects import read_json
from ai_collage.replay import ReplayReport, main, replay

from .helpers import REPO, layout_data
from .test_agent import FakeModel, asyncio_wakeup_pair, reply


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


def test_stepwise_resume_allows_only_future_edits_and_captures_evidence(store, scenario, tmp_path):
    path, data = scenario
    changed = layout_data()
    changed["canvas"]["background"] = "#202020"
    model = FakeModel(reply(), reply(changed))
    first = execute(store, path, model)
    assert first.next_step == 1 and len(model.contexts) == 1
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
    assert resumed.next_step == 2 and len(model.contexts) == 2
    result = resumed.executions[-1]
    assert result.reopened and result.status == "proposal"
    assert result.attempts == 1 and result.validation_corrections == 0
    assert [change.field for change in result.changes] == ["recipe.canvas.background"]
    assert read_json(Path(result.contexts[0]))["user_request"] == data["messages"][1]["prompt"]
    assert model.contexts[1]["editing_baseline"] == read_json(
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
    assert len(model.contexts) == 2


def test_remaining_reopens_at_the_declared_message(store, scenario, monkeypatch):
    path, _ = scenario
    requests = RequestLog(store, "demo")
    opened = []

    class ObservedConversation(Conversation):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            opened.append(self.state.baseline)

    monkeypatch.setattr("ai_collage.replay.Conversation", ObservedConversation)
    result = execute(store, path, FakeModel(reply(), reply()), remaining=True)
    assert opened == [None, "P001"]
    assert result.next_step == 2 and len(requests.attempts()) == 2


def test_failure_stops_batch_and_requires_explicit_retry(store, scenario):
    path, _ = scenario
    model = FakeModel(reply(), CollageError("Service stopped"), reply())
    result = execute(store, path, model, remaining=True)
    assert result.next_step == 1 and len(model.contexts) == 2
    assert result.executions[-1].status == "failed"
    assert "Service stopped" in result.executions[-1].error
    failure_path = store.project_dir("demo") / "replay" / "steps" / "0002" / "result.json"
    failure = failure_path.read_bytes()
    with pytest.raises(CollageError, match="explicit"):
        execute(store, path, model, resume=True)
    result = execute(store, path, model, resume=True, retry=True)
    assert result.next_step == 2 and len(model.contexts) == 3
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
    with pytest.raises(CollageError, match="explicit"):
        execute(store, path, FakeModel(reply()), resume=True)


def test_question_stops_without_advancing_or_answering(store, scenario):
    path, _ = scenario
    model = FakeModel('{"kind":"question","question":"Which photo?"}', reply())
    report = execute(store, path, model, remaining=True)
    assert report.next_step == 0 and len(model.contexts) == 1
    assert report.executions[0].question == "Which photo?"
    assert report.executions[0].status == "question"
    with pytest.raises(CollageError, match="question"):
        execute(store, path, model, resume=True, retry=True)
    assert len(model.contexts) == 1


def test_validation_corrections_capture_each_context(store, scenario):
    path, _ = scenario
    report = execute(store, path, FakeModel("not JSON", reply()))
    result = report.executions[0]
    assert result.status == "proposal" and result.attempts == 2
    assert result.validation_corrections == 1 and len(result.contexts) == 2
    assert read_json(Path(result.contexts[0]))["validation_feedback"] is None
    assert read_json(Path(result.contexts[1]))["validation_feedback"]


def test_question_matching_a_proposal_id_is_not_treated_as_a_proposal(store, scenario):
    path, _ = scenario
    report = execute(
        store, path,
        FakeModel(reply(), '{"kind":"question","question":"P001"}'), remaining=True,
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
            monkeypatch.setattr("ai_collage.replay.instructions", lambda: "Changed instructions")
            return response

    model = ChangedInstructions("not JSON", reply())
    report = execute(store, path, model)
    assert report.executions[0].status == "failed"
    assert "Instructions changed" in report.executions[0].error
    assert len(model.contexts) == 1 and len(requests.attempts()) == 1


def test_four_invalid_responses_stop_the_batch_before_the_next_message(store, scenario):
    path, _ = scenario
    requests = RequestLog(store, "demo")
    model = FakeModel(*["not JSON"] * 4, reply())
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
    model = FakeModel(*(["{}", "{}", "{}", reply()] * 4), reply())
    report = execute(store, path, model, remaining=True)
    assert report.next_step == 4 and len(model.contexts) == 16
    assert [result.attempts for result in report.executions] == [4] * 4
    assert [result.validation_corrections for result in report.executions] == [3] * 4
    assert len(RequestLog(store, "demo").attempts()) == 16
    assert not (store.owner_dir / "agent-runs").exists()
    execute(store, path, model, resume=True, remaining=True)
    assert len(model.contexts) == 16


def test_legacy_replay_can_resume_without_its_old_allowance(store, scenario):
    path, _ = scenario
    model = FakeModel(reply(), reply())
    execute(store, path, model)
    root = store.project_dir("demo") / "replay"
    original = (root / "steps" / "0001" / "result.json").read_bytes()
    report = read_json(root / "report.json")
    historical_path = str(store.data_dir / "missing-old-run" / "run.json")
    report["ledger_path"] = historical_path
    report.pop("requests_path")
    (root / "report.json").write_text(json.dumps(report), encoding="utf-8")
    result = execute(store, path, model, resume=True)
    assert result.next_step == 2 and result.ledger_path == historical_path
    assert result.requests_path == str(RequestLog(store, "demo").root)
    assert (root / "steps" / "0001" / "result.json").read_bytes() == original
    assert not (store.owner_dir / "agent-runs").exists()


@pytest.mark.parametrize("change", ["prompt", "canvas", "source", "instructions", "conversation"])
def test_resume_rejects_changed_execution_identity(store, scenario, monkeypatch, change):
    path, data = scenario
    model = FakeModel(reply(), reply())
    execute(store, path, model)
    if change == "prompt":
        data["messages"][0]["prompt"] = "A changed attempted message"
    elif change == "canvas":
        data["canvas"]["width"] = 120
    elif change == "source":
        data["images"].reverse()
    elif change == "instructions":
        monkeypatch.setattr("ai_collage.replay.instructions", lambda: "Changed instructions")
    else:
        conversation = Conversation(store, "demo")
        conversation.controls(conversation.state.controls.model_copy(update={"cropping": True}))
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CollageError, match="changed"):
        execute(store, path, model, resume=True)
    assert len(model.contexts) == 1


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
    model = FakeModel(reply(), reply())
    execute(store, path, model)
    report_path = store.project_dir("demo") / "replay" / "report.json"
    report = read_json(report_path)
    report["next_step"] = 2
    report_path.write_text(json.dumps(report), encoding="utf-8")
    with pytest.raises(CollageError, match="cursor"):
        execute(store, path, model, resume=True)
    assert len(model.contexts) == 1


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

    monkeypatch.setattr("ai_collage.replay.FoundryModel", forbidden)
    for filename, name in (
        ("01_dark_portrait_adjustments.json", "checkpoint-a"),
        ("02_landscape_staggered_adjustments.json", "landscape-staggered"),
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
    ('{"kind":"question","question":"Which photo?"}', 1),
    (CollageError("Service failed"), 1),
])
def test_cli_runs_one_step_and_reports_stop_status(store, scenario, monkeypatch, capsys, response, code):
    path, _ = scenario
    monkeypatch.setattr("ai_collage.replay.FoundryModel", lambda: FakeModel(response))
    assert main([
        "--sequence", str(path), "--data-dir", str(store.data_dir),
        "--project", "demo",
    ]) == code
    report = json.loads(capsys.readouterr().out)
    assert len(report["executions"]) == 1
