import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from ai_collage.agent.conversation import Conversation
from ai_collage.agent.files import save
from ai_collage.agent.models import AcceptanceIntent
from ai_collage.agent.requests import StageTimeout
from ai_collage.application.conversation import (
    ConversationFlow, ConversationSettings, GenerationRequest, SelectionSubmission, Submission,
)
from ai_collage.application.projects import FlowError, ProjectFlow, ProjectSetup
from ai_collage.engine.projects import read_json
from ai_collage.engine.models import CollageError
from ..agent.test_agent import FakeModel, asyncio_wakeup_pair, intent, photo_reference, reply


@pytest.fixture
def flow(store, sources):
    with sources[0].open("rb") as a, sources[1].open("rb") as b:
        ProjectFlow(store).create(ProjectSetup(
            project_id="demo", canvas={"width": 100, "height": 100},
        ), [a, b])
    return ConversationFlow(store, ConversationSettings(live=True))


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def send(flow, prompt, *responses):
    flow.client = FakeModel(*responses)
    submission = Submission(
        request_id=str(uuid4()), prompt=prompt, revision=flow.detail("demo")["revision"],
    )
    operation, created = asyncio.run(flow.interpret("demo", submission))
    assert created
    return operation, submission


def generate(flow, operation, *responses):
    flow.client = FakeModel(*responses)
    return asyncio.run(flow.generate("demo", operation["request_id"], GenerationRequest(
        revision=operation["revision"],
    )))


def select(flow, proposal_id, *, abandon=False, revision=None, action_id=None):
    submission = SelectionSubmission(
        action_id=action_id or str(uuid4()), proposal_id=proposal_id,
        revision=revision or flow.detail("demo")["revision"], abandon_pending=abandon,
    )
    result, created = flow.select("demo", submission)
    return result, created, submission


def two_proposals(flow):
    for prompt in ("Make a collage", "Make another collage"):
        prepared, _ = send(flow, prompt, intent("fresh"))
        generate(flow, prepared, reply())


def test_transcript_keeps_selection_activity_with_its_snapshot(flow, monkeypatch):
    two_proposals(flow)
    before = flow.detail("demo")
    original_snapshot = flow._snapshot
    selected = False

    def select_after_snapshot(project_id):
        nonlocal selected
        result = original_snapshot(project_id)
        if not selected:
            selected = True
            flow.select(project_id, SelectionSubmission(
                action_id=str(uuid4()), proposal_id="P001",
                revision=before["revision"], abandon_pending=False,
            ))
        return result

    monkeypatch.setattr(flow, "_snapshot", select_after_snapshot)
    assert flow.detail("demo") == before
    assert flow.detail("demo")["baseline"] == {"proposal_id": "P001"}


def test_local_selection_is_repeatable_model_free_durable_and_keeps_names(flow):
    two_proposals(flow)
    named, _ = send(flow, "Photo 2 is breakfast", intent("remember", name_updates=[
        {"name": "breakfast", "photo_id": 2, "quote": "Photo 2 is breakfast"},
    ]))
    assert named["result_kind"] == "acknowledgement"
    original = Conversation(flow.store, "demo", read_only=True)
    pngs = {p: flow.preview("demo", p) for p in ("P001", "P002")}
    flow.settings.live = False
    flow.client = FakeModel()
    first, created, submission = select(flow, "P001")
    assert created and first["status"] == "completed" and not flow.client.contexts
    restored = ConversationFlow(flow.store, flow.settings, flow.client)
    view = restored.detail("demo")
    assert view["baseline"] == {"proposal_id": "P001"}
    assert view["selection"]["enabled"] and view["selection"]["confirmation"] is None
    assert view["messages"][-1]["role"] == "activity"
    assert view["messages"][-1]["text"] == "You chose collage P001 as the starting point for further edits."
    assert [p["proposal_id"] for p in view["proposals"]] == ["P001", "P002"]
    assert Conversation(flow.store, "demo", read_only=True).state.photo_names == original.state.photo_names
    select(restored, "P002")
    before = snapshot(flow.store.data_dir)
    duplicate, created = restored.select("demo", submission)
    assert not created and duplicate["proposal_id"] == "P001"
    assert restored.detail("demo")["baseline"]["proposal_id"] == "P002"
    assert snapshot(flow.store.data_dir) == before
    with pytest.raises(FlowError) as error:
        restored.select("demo", submission.model_copy(update={"proposal_id": "P002"}))
    assert error.value.code == "action_id_conflict"
    assert flow.store.load("demo").current_version is None
    for p, raw in pngs.items():
        assert restored.preview("demo", p) == raw
    restored.settings.live = True
    select(restored, "P001")
    prepared, _ = send(restored, "Make photo 2 smaller", intent("edit", source="current"))
    assert restored.client.contexts[-1]["current_layout"] == original.proposal("P001").recipe.model_dump(mode="json")
    generate(restored, prepared, reply())
    assert Conversation(flow.store, "demo", read_only=True).proposal("P003").parent == "P001"


@pytest.mark.parametrize("pending", ["question", "names", "prepared"])
def test_confirmed_selection_ends_only_the_pending_task_and_retires_preparation(flow, pending):
    two_proposals(flow)
    for photo in (1,):
        prompt = f"Photo {photo} is breakfast"
        send(flow, prompt, intent("remember", name_updates=[
            {"name": "breakfast", "photo_id": photo, "quote": prompt},
        ]))
    request = None
    if pending == "question":
        send(flow, "Make the tower smaller", intent("question", question="Which photo is the tower?"))
    elif pending == "names":
        send(flow, "Photo 2 is breakfast", intent("remember", name_updates=[
            {"name": "breakfast", "photo_id": 2, "quote": "Photo 2 is breakfast"},
        ]))
    else:
        request, _ = send(flow, "Make photo 1 smaller", intent("edit", source="current"))
    saved = Conversation(flow.store, "demo", read_only=True)
    abandoned = saved.selection_task()
    view = flow.detail("demo")
    assert view["selection"]["confirmation"]
    before = snapshot(flow.store.data_dir)
    with pytest.raises(FlowError) as error:
        select(flow, "P001")
    assert error.value.code == "confirmation_required"
    assert snapshot(flow.store.data_dir) == before
    select(flow, "P001", abandon=True)
    restored = Conversation(flow.store, "demo", read_only=True)
    assert restored.selection_task() is None and restored._pending_question() is None
    assert restored.state.pending_names is None and restored.state.photo_names == saved.state.photo_names
    assert next(t for t in restored.tasks() if t.task_id == abandoned).outcome == "abandoned"
    assert flow.detail("demo")["pending"] is None and flow.detail("demo")["operation"] is None
    if request:
        contexts = len(flow.client.contexts)
        assert generate(flow, request)["status"] == "abandoned"
        assert not flow.client.contexts
        assert contexts == 1
    next_request, _ = send(flow, "Make photo 2 smaller", intent("edit", source="current"))
    assert flow.client.contexts[-1]["pending_question"] is None
    assert flow.client.contexts[-1]["active_task"]["request"] == "Make photo 2 smaller"
    generate(flow, next_request, reply())
    assert Conversation(flow.store, "demo", read_only=True).proposal("P003").parent == "P001"


def test_selection_rejects_stale_confirmation_unknown_target_and_unresolved_claim(flow):
    two_proposals(flow)
    old = flow.detail("demo")["revision"]
    select(flow, "P001")
    before = snapshot(flow.store.data_dir)
    for target, revision, code in (
        ("P002", old, "stale_revision"),
        ("P999", None, None),
        ("P001", None, "already_current"),
    ):
        with pytest.raises((FlowError, CollageError)) as error:
            select(flow, target, revision=revision)
        if code:
            assert error.value.code == code
        assert snapshot(flow.store.data_dir) == before
    prepared, _ = send(flow, "Make photo 1 smaller", intent("edit", source="current"))
    operation = read_json(flow._path("demo", prepared["request_id"]))
    operation["status"] = "generating"
    flow._path("demo", prepared["request_id"]).write_text(json.dumps(operation))
    assert not flow.detail("demo")["selection"]["enabled"]
    with pytest.raises(FlowError) as error:
        select(flow, "P002", abandon=True)
    assert error.value.code == "operation_unresolved"


@pytest.mark.parametrize("window", ["retirement", "state", "result"])
def test_selection_partial_publication_fails_closed_without_repair(flow, monkeypatch, window):
    two_proposals(flow)
    prepared, _ = send(flow, "Make photo 1 smaller", intent("edit", source="current"))
    submission = SelectionSubmission(
        action_id=str(uuid4()), proposal_id="P001", revision=flow.detail("demo")["revision"], abandon_pending=True,
    )
    if window == "retirement":
        original = flow._save
        def fail(operation):
            if operation.status == "abandoned":
                raise OSError("offline retirement failure")
            return original(operation)
        monkeypatch.setattr(flow, "_save", fail)
    elif window == "state":
        monkeypatch.setattr(Conversation, "_commit", lambda *args: (_ for _ in ()).throw(OSError("offline state failure")))
    else:
        original = flow._save_selection
        def fail(action):
            if action.status == "completed":
                raise OSError("offline result failure")
            return original(action)
        monkeypatch.setattr(flow, "_save_selection", fail)
    with pytest.raises(OSError):
        flow.select("demo", submission)
    before = snapshot(flow.store.data_dir)
    assert flow.selection("demo", submission.action_id)["status"] == "uncertain"
    assert flow.select("demo", submission)[1] is False
    for action in (
        lambda: generate(flow, prepared),
        lambda: asyncio.run(flow.interpret("demo", Submission(
            request_id=str(uuid4()), prompt="Another edit", revision=submission.revision,
        ))),
        lambda: flow.select("demo", submission.model_copy(update={"action_id": str(uuid4())})),
    ):
        with pytest.raises(FlowError) as error:
            action()
        assert error.value.code == "selection_unresolved"
    assert snapshot(flow.store.data_dir) == before


def test_selection_and_generation_share_the_cross_process_guard(flow, monkeypatch):
    two_proposals(flow)
    prepared, _ = send(flow, "Make photo 1 smaller", intent("edit", source="current"))
    entered, release = threading.Event(), threading.Event()
    original = Conversation.select_proposal
    def held(self, *args, **kwargs):
        entered.set()
        assert release.wait(5), "Offline selection gate was not released."
        return original(self, *args, **kwargs)
    monkeypatch.setattr(Conversation, "select_proposal", held)
    with ThreadPoolExecutor(max_workers=1) as executor:
        selecting = executor.submit(select, flow, "P001", abandon=True)
        try:
            assert entered.wait(3)
            assert not flow.detail("demo")["selection"]["enabled"]
            with pytest.raises(FlowError) as error:
                generate(flow, prepared)
            assert error.value.code == "project_busy"
        finally:
            release.set()
        assert selecting.result(timeout=5)[0]["status"] == "completed"
    assert generate(flow, prepared)["status"] == "abandoned" and not flow.client.contexts


def test_pending_confirmation_cannot_authorize_a_changed_state(flow):
    two_proposals(flow)
    send(flow, "Make the tower smaller", intent("question", question="Which photo is the tower?"))
    old = flow.detail("demo")["revision"]
    send(flow, "List photo names", intent("list_names"))
    before = snapshot(flow.store.data_dir)
    with pytest.raises(FlowError) as error:
        select(flow, "P001", abandon=True, revision=old)
    assert error.value.code == "stale_revision"
    assert snapshot(flow.store.data_dir) == before and flow.detail("demo")["pending"]["kind"] == "question"


def test_local_selection_preserves_cli_acceptance_and_uncorrupted_navigation(flow):
    two_proposals(flow)
    select(flow, "P001")
    conversation = Conversation(flow.store, "demo")
    assert conversation.accept("P002") == 1
    assert Conversation(flow.store, "demo", read_only=True).state.baseline == "P002"
    assert conversation.select_proposal("P001") > 0
    assert Conversation(flow.store, "demo", read_only=True).state.baseline == "P001"
    assert flow.store.load("demo").current_version == 1


def test_split_duplicate_reads_and_fresh_process_preserve_one_turn(flow):
    first, submission = send(flow, "Make a collage", intent("fresh"))
    assert first["status"] == "prepared" and first["can_continue"]
    assert first["summary"] == "Fresh; source: none; photo references: as requested."
    before = snapshot(flow.store.data_dir)
    assert flow.detail("demo")["operation"] == first
    assert flow.operation("demo", submission.request_id) == first
    duplicate, created = asyncio.run(flow.interpret("demo", submission))
    assert duplicate == first and not created and len(flow.client.contexts) == 1
    assert snapshot(flow.store.data_dir) == before
    flow = ConversationFlow(flow.store, flow.settings)
    completed = generate(flow, first, reply())
    assert completed["status"] == "completed" and completed["proposal_id"] == "P001"
    view = flow.detail("demo")
    assert view["baseline"] == {"proposal_id": "P001"}
    assert [m["role"] for m in view["messages"]] == ["user", "assistant"]
    assert view["messages"][-1]["text"] == "Created P001."
    assert view["operation"] is None
    before = snapshot(flow.store.data_dir)
    assert generate(flow, first) == completed
    assert flow.preview("demo", "P001").startswith(b"\x89PNG")
    assert snapshot(flow.store.data_dir) == before
    script = """
import json, socket, sys
from pathlib import Path
from ai_collage.application.conversation import ConversationFlow, ConversationSettings
from ai_collage.engine.projects import ProjectStore
def blocked(*args, **kwargs): raise AssertionError('network forbidden')
socket.socket.connect = blocked
print(json.dumps(ConversationFlow(ProjectStore(Path(sys.argv[1])), ConversationSettings(live=True)).detail('demo')))
"""
    result = subprocess.run(
        [sys.executable, "-c", script, str(flow.store.data_dir)], capture_output=True,
        text=True, timeout=30, check=True,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])},
    )
    assert json.loads(result.stdout) == view
    assert snapshot(flow.store.data_dir) == before


def test_old_operations_never_reselect_a_previous_baseline(flow):
    first, original = send(flow, "Make a collage", intent("fresh"))
    generate(flow, first, reply())
    second, _ = send(flow, "Make another collage", intent("fresh"))
    generate(flow, second, reply())
    before = snapshot(flow.store.data_dir)
    assert asyncio.run(flow.interpret("demo", original))[1] is False
    assert generate(flow, first)["proposal_id"] == "P001"
    assert flow.detail("demo")["baseline"]["proposal_id"] == "P002"
    assert snapshot(flow.store.data_dir) == before


def test_exhausted_layout_attempts_report_confirmed_failure_and_preserve_preview(flow):
    first, _ = send(flow, "Make a collage", intent("fresh"))
    generate(flow, first, reply())
    original = flow.preview("demo", "P001")
    prepared, submission = send(flow, "Grow photo 1", intent("edit", source="current"))
    invalid = json.loads(reply())
    invalid["layers"][0]["box"]["center_x"] = 3
    with pytest.raises(FlowError) as error:
        generate(flow, prepared, *(reply(invalid) for _ in range(3)))
    assert error.value.code == "stage_failed" and error.value.status == 422
    assert "Couldn't create a valid layout within the attempt limit." in str(error.value)
    assert "Your previous preview is unchanged." in str(error.value)
    assert len(flow.client.contexts) == 3
    saved = flow.operation("demo", submission.request_id)
    assert saved["status"] == "failed" and not saved["can_continue"]
    assert saved["error"]["message"] == str(error.value)
    view = flow.detail("demo")
    assert view["operation"] is None and view["baseline"] == {"proposal_id": "P001"}
    assert view["messages"][-1]["text"] == str(error.value)
    assert flow.preview("demo", "P001") == original


def test_question_name_lifecycle_and_exact_return_projection(flow):
    first, _ = send(flow, "Make a collage", intent("fresh"))
    generate(flow, first, reply())
    original_png = flow.preview("demo", "P001")
    question, _ = send(flow, "Make breakfast smaller", intent(
        "question", question="Which photo is breakfast?",
        references=[photo_reference("breakfast", None)],
    ))
    assert question["result_kind"] == "question"
    assert flow.detail("demo")["pending"]["message"] == "Which photo is breakfast?"
    listed, _ = send(flow, "List photo names", intent("list_names"))
    assert listed["result_kind"] == "acknowledgement"
    assert flow.detail("demo")["pending"]["kind"] == "question"
    answer, _ = send(flow, "Photo 2", intent(
        "edit", source="current", references=[photo_reference("Photo 2", 2)],
    ))
    generate(flow, answer, reply())
    assert flow.detail("demo")["pending"] is None
    returned, _ = send(flow, "Return to P001", intent("select", proposal_id="P001"))
    assert returned["result_kind"] == "selection"
    assert flow.preview("demo", "P001") == original_png
    assert flow.store.load("demo").current_version is None
    for photo in (1, 2):
        prompt = f"Photo {photo} is breakfast"
        named, _ = send(flow, prompt, intent("remember", name_updates=[
            {"name": "breakfast", "photo_id": photo, "quote": prompt},
        ]))
    assert named["result_kind"] == "name_confirmation"
    assert "breakfast = photo 2" in flow.detail("demo")["pending"]["message"]
    current = Conversation(flow.store, "demo", read_only=True)
    approved, _ = send(flow, "Yes, remember those", intent(
        "names", decision="approve", receipt_event=current.state.pending_names.event_id,
    ))
    assert approved["result_kind"] == "acknowledgement"
    assert flow.detail("demo")["pending"] is None
    listed, _ = send(flow, "List photo names", intent("list_names"))
    assert "breakfast = photo 2" in listed["message"]
    forgotten, _ = send(flow, "Forget breakfast", intent("forget", name_updates=[
        {"name": "breakfast", "photo_id": None, "quote": "Forget breakfast"},
    ]))
    assert forgotten["result_kind"] == "acknowledgement"
    listed, _ = send(flow, "List photo names", intent("list_names"))
    assert "No photo names learned" in listed["message"]


def test_stale_duplicate_and_overlapping_prepared_submissions_dispatch_nothing(flow):
    operation, original = send(flow, "Make a collage", intent("fresh"))
    before = snapshot(flow.store.data_dir)
    for submission, code in (
        (original.model_copy(update={"prompt": "Different"}), "request_id_conflict"),
        (original.model_copy(update={"request_id": str(uuid4())}), "operation_unresolved"),
    ):
        with pytest.raises(FlowError) as error:
            asyncio.run(flow.interpret("demo", submission))
        assert error.value.code == code
    with pytest.raises(FlowError, match="changed"):
        asyncio.run(flow.generate("demo", original.request_id, GenerationRequest(revision="0" * 64)))
    assert snapshot(flow.store.data_dir) == before and len(flow.client.contexts) == 1
    generate(flow, operation, reply())
    with pytest.raises(FlowError) as error:
        asyncio.run(flow.interpret("demo", original.model_copy(update={"request_id": str(uuid4())})))
    assert error.value.code == "stale_revision"


def test_running_claim_is_observable_and_blocks_another_process(flow):
    async def exercise():
        entered, release = asyncio.Event(), asyncio.Event()

        class WaitingModel(FakeModel):
            async def complete(self, context, log, purpose):
                entered.set()
                await release.wait()
                return await super().complete(context, log, purpose)

        flow.client = WaitingModel(intent("fresh"))
        submission = Submission(request_id=str(uuid4()), prompt="Make a collage",
                                revision=flow.detail("demo")["revision"])
        running = asyncio.create_task(flow.interpret("demo", submission))
        await entered.wait()
        try:
            assert flow.detail("demo")["operation"]["status"] == "interpreting"
            script = """
import json, sys
from pathlib import Path
from ai_collage.application.conversation import ConversationFlow, ConversationSettings
from ai_collage.application.projects import FlowError, project_guard
from ai_collage.engine.projects import ProjectStore
store = ProjectStore(Path(sys.argv[1]))
print(ConversationFlow(store, ConversationSettings()).detail('demo')['operation']['status'])
try:
    with project_guard(store, 'demo'): print('unexpected lock')
except FlowError as error: print(error.code)
"""
            result = subprocess.run([sys.executable, "-c", script, str(flow.store.data_dir)],
                                    capture_output=True, text=True, check=True, timeout=30)
            assert result.stdout.splitlines() == ["interpreting", "project_busy"]
        finally:
            release.set()
            await running
    asyncio.run(exercise())


@pytest.mark.parametrize("stage", ["interpretation", "generation"])
def test_confirmed_timeouts_are_terminal_but_never_retry_automatically(flow, stage):
    if stage == "generation":
        operation, submission = send(flow, "Make a collage", intent("fresh"))
        action = lambda: generate(flow, operation, StageTimeout("offline timeout"))
    else:
        submission = Submission(request_id=str(uuid4()), prompt="Make a collage",
                                revision=flow.detail("demo")["revision"])
        flow.client = FakeModel(StageTimeout("offline timeout"))
        action = lambda: asyncio.run(flow.interpret("demo", submission))
    with pytest.raises(FlowError) as error:
        action()
    assert error.value.status == 504
    view = flow.detail("demo")
    assert view["operation"] is None and view["baseline"] is None
    assert view["messages"][-1]["kind"] == "failed"
    calls = len(flow.client.contexts)
    saved = flow.operation("demo", submission.request_id)
    assert saved["status"] == "failed"
    asyncio.run(flow.interpret("demo", submission))
    assert len(flow.client.contexts) == calls


@pytest.mark.parametrize("window", ["claim", "result-record"])
def test_interrupted_execution_and_publication_uncertainty_fail_closed(flow, monkeypatch, window):
    if window == "claim":
        class InterruptedModel:
            async def complete(self, *args):
                raise asyncio.CancelledError()
        flow.client = InterruptedModel()
        submission = Submission(request_id=str(uuid4()), prompt="Make a collage",
                                revision=flow.detail("demo")["revision"])
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(flow.interpret("demo", submission))
    else:
        operation, submission = send(flow, "Make a collage", intent("fresh"))
        real_save = flow._save
        def broken_save(value):
            if value.status == "completed":
                raise OSError("result disk failed")
            real_save(value)
        monkeypatch.setattr(flow, "_save", broken_save)
        with pytest.raises(OSError):
            generate(flow, operation, reply())
    before = snapshot(flow.store.data_dir)
    view = flow.detail("demo")
    assert view["operation"]["status"] == "uncertain"
    assert view["baseline"] == (None if window == "claim" else {"proposal_id": "P001"})
    assert not view["operation"]["can_continue"]
    duplicate, created = asyncio.run(flow.interpret("demo", submission))
    assert duplicate["status"] == "uncertain" and not created
    with pytest.raises(FlowError) as error:
        asyncio.run(flow.interpret("demo", submission.model_copy(update={"request_id": str(uuid4())})))
    assert error.value.code == "operation_unresolved"
    assert snapshot(flow.store.data_dir) == before


def test_outer_work_deadline_stops_before_publication_without_shortening_model_limits(flow, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr("ai_collage.application.conversation.monotonic", lambda: clock[0])
    monkeypatch.setattr("ai_collage.agent.requests.monotonic", lambda: clock[0])
    operation, _ = send(flow, "Make a collage", intent("fresh"))
    from ai_collage.agent import conversation as module
    render = module.render_layout
    def slow_render(*args, **kwargs):
        result = render(*args, **kwargs)
        clock[0] += 211
        return result
    monkeypatch.setattr(module, "render_layout", slow_render)
    with pytest.raises(FlowError) as error:
        generate(flow, operation, reply())
    assert error.value.code == "stage_timeout"
    assert flow.detail("demo")["baseline"] is None
    log = read_json(flow.store.project_dir("demo") / "conversation" / "requests" / "attempt-0002.json")
    assert log["timeout_seconds"] == 180
    assert not list(flow.store.project_dir("demo").glob("conversation/proposals/P*"))


def test_read_only_access_never_repairs_acceptance_or_tampered_preview(flow):
    operation, _ = send(flow, "Make a collage", intent("fresh"))
    generate(flow, operation, reply())
    conversation = Conversation(flow.store, "demo")
    save(conversation.intent_path, AcceptanceIntent(
        proposal_id="P001", previous_version=None, next_version=1,
    ))
    before = snapshot(flow.store.data_dir)
    with pytest.raises(FlowError):
        flow.detail("demo")
    assert snapshot(flow.store.data_dir) == before
    conversation.intent_path.unlink()
    conversation.preview_path("P001").write_bytes(b"tampered")
    before = snapshot(flow.store.data_dir)
    with pytest.raises(FlowError):
        flow.preview("demo", "P001")
    assert snapshot(flow.store.data_dir) == before


def test_trial_ledger_is_shared_across_stage_objects_and_cannot_renew(flow, tmp_path):
    ledger = tmp_path / "ledger.json"
    settings = ConversationSettings(live=True, budget_path=ledger, max_calls=2, trial_project="demo")
    flow.settings = settings
    operation, _ = send(flow, "Make a collage", intent("fresh"))
    reopened = ConversationFlow(flow.store, settings)
    generate(reopened, operation, reply())
    assert read_json(ledger) == {"record_version": 1, "limit": 2, "used": 2}
    with pytest.raises(FlowError):
        send(reopened, "Make another collage", intent("fresh"))
    assert read_json(ledger)["used"] == 2
    before = snapshot(flow.store.data_dir)
    changed = ConversationFlow(flow.store, ConversationSettings(
        live=True, budget_path=ledger, max_calls=3, trial_project="demo",
    ))
    with pytest.raises(CollageError, match="budget limit changed"):
        send(changed, "One more", intent("fresh"))
    assert snapshot(flow.store.data_dir) == before


def test_disabled_and_incomplete_configuration_dispatch_nothing(flow):
    flow.settings = ConversationSettings()
    before = snapshot(flow.store.data_dir)
    with pytest.raises(FlowError) as error:
        send(flow, "Make a collage", intent("fresh"))
    assert error.value.code == "live_disabled" and not flow.client.contexts
    assert snapshot(flow.store.data_dir) == before
    with pytest.raises(FlowError):
        ConversationSettings(live=True, max_calls=12)
