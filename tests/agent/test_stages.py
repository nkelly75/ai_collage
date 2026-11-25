import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
from pydantic import ValidationError

from ai_collage.agent.conversation import Conversation, RequestRejected
from ai_collage.agent.files import save
from ai_collage.agent.models import Controls, PreparedGeneration
from ai_collage.agent.requests import RequestLog, StageTimeout, call_budget
from ai_collage.engine.models import CollageError
from ai_collage.engine.projects import ProjectStore, read_json

from .test_agent import (
    FakeModel, agent_project, ask, asyncio_wakeup_pair, intent, photo_reference, reply,
)


def snapshot(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*") if path.is_file()
    }


def run_split(conversation, prompt, model, requests, progress=None):
    prepared = asyncio.run(conversation.interpret(prompt, model, requests, progress=progress))
    if not isinstance(prepared, PreparedGeneration):
        return prepared, conversation
    prepared = PreparedGeneration.model_validate_json(prepared.model_dump_json())
    reopened = Conversation(conversation.store, conversation.project_id)
    log = RequestLog(
        conversation.store, conversation.project_id,
        generation_reasoning=requests.generation_reasoning,
        interpretation_reasoning=requests.interpretation_reasoning,
    )
    log.limits = requests.limits
    return asyncio.run(reopened.generate(prepared, model, log, progress=progress)), reopened


@pytest.mark.parametrize("scenario", [
    "fresh", "edit", "corrections", "identity", "receipt", "timeout", "independent",
])
def test_composed_and_reconstructed_stages_preserve_semantics(agent_project, tmp_path, scenario):
    conversation, requests = agent_project
    prompt = "Make a collage"
    responses = [intent("fresh"), reply()]
    if scenario != "fresh":
        ask(conversation, requests, reply())
        prompt = "Make photo 2 smaller"
        responses = [intent("edit", source="current"), reply()]
    if scenario == "corrections":
        responses = ["{}", *responses[:1], "{}", reply()]
    elif scenario == "identity":
        ask(conversation, requests, prompt="Make breakfast smaller", action=intent(
            "question", question="Which photo is breakfast?",
            references=[photo_reference("breakfast", None)],
        ))
        prompt = "Photo 2"
        responses[0] = intent("edit", source="current", references=[photo_reference("Photo 2", 2)])
    elif scenario == "receipt":
        ask(conversation, requests, prompt="Photo 1 is breakfast", action=intent(
            "remember", name_updates=[{"name": "breakfast", "photo_id": 1, "quote": "Photo 1 is breakfast"}],
        ))
        ask(conversation, requests, prompt="Photo 2 is breakfast; make breakfast smaller", action=intent(
            "edit", source="current", references=[photo_reference("breakfast", 2)],
            name_updates=[{"name": "breakfast", "photo_id": 2, "quote": "Photo 2 is breakfast"}],
        ))
        prompt = "Yes, remember those"
        responses[0] = intent("names", decision="approve", receipt_event=conversation.state.pending_names.event_id)
    elif scenario in {"timeout", "independent"}:
        with pytest.raises(StageTimeout):
            asyncio.run(conversation.request(
                "Make photo 2 smaller",
                FakeModel(intent("edit", source="current"), StageTimeout("offline")),
                requests,
            ))
        prompt = "try again" if scenario == "timeout" else "Start a new arrangement"
        responses[0] = intent("resume") if scenario == "timeout" else intent("fresh", continues_task=False)

    branches = []
    for mode in ("composed", "split"):
        root = tmp_path / mode
        shutil.copytree(conversation.store.data_dir, root)
        store = ProjectStore(root)
        current = Conversation(store, "demo")
        log = RequestLog(store, "demo", generation_reasoning="high", interpretation_reasoning="low")
        model = FakeModel(*responses)
        notifications = []

        def progress(kind, value):
            notifications.append((kind, value))

        if mode == "split":
            result, current = run_split(current, prompt, model, log, progress)
        else:
            result = asyncio.run(current.request(prompt, model, log, progress=progress))
        attempts = [
            item.model_dump(exclude={"started", "duration", "timeout_seconds"})
            for item in log.attempts()
        ]
        branches.append((
            result, current.state, current.history(), current.tasks(), model.contexts,
            notifications, attempts, current.proposal(result.proposal_id),
            current.preview_path(result.proposal_id).read_bytes(),
        ))
        assert store.load("demo").current_version is None
    assert branches[0] == branches[1]


@pytest.mark.parametrize("outcome", ["question", "remember", "names", "select", "list_names"])
def test_interpretation_returns_final_outcomes_without_generation(agent_project, outcome):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    prompt = "What next?"
    response = intent("question", question="Which photo?")
    expected = "question"
    if outcome in {"remember", "names"}:
        prompt = "Photo 1 is breakfast"
        response = intent("remember", name_updates=[{"name": "breakfast", "photo_id": 1, "quote": prompt}])
        expected = "acknowledgement"
        if outcome == "names":
            ask(conversation, requests, prompt=prompt, action=response)
            prompt = "Photo 2 is breakfast"
            response = intent("remember", name_updates=[{"name": "breakfast", "photo_id": 2, "quote": prompt}])
            expected = "name_confirmation"
    elif outcome == "select":
        prompt = f"Return to {first}"
        response = intent("select", proposal_id=first)
        expected = "selection"
    elif outcome == "list_names":
        response = intent("list_names")
        expected = "acknowledgement"
    model = FakeModel(response)
    result = asyncio.run(conversation.interpret(prompt, model, requests))
    assert result.kind == expected
    assert len(model.contexts) == 1
    assert model.contexts[0]["stage"] == "interpretation"
    assert conversation.state.baseline == first


@pytest.mark.parametrize("change", [
    "project", "photos", "photo-metadata", "controls", "reuse", "history", "source", "calls",
])
def test_invalid_handoff_is_rejected_without_calls_or_mutations(agent_project, sources, change):
    conversation, requests = agent_project
    ask(conversation, requests, reply())
    prepared = asyncio.run(conversation.interpret(
        "Make photo 2 smaller", FakeModel(intent("edit", source="current")), requests,
    ))
    assert isinstance(prepared, PreparedGeneration)
    if change in {"project", "photos"}:
        project_id = "other" if change == "project" else "demo"
        other = ProjectStore(conversation.store.data_dir.parent / "other")
        other.create(project_id, sources)
        conversation = Conversation(other, project_id, canvas=(100, 100))
    elif change == "photo-metadata":
        path = conversation.store.project_dir("demo") / "project.json"
        data = read_json(path)
        data["photos"][0]["original_filename"] = "changed.png"
        path.write_text(json.dumps(data), encoding="utf-8")
    elif change == "controls":
        conversation.controls(Controls(width=200, height=100))
    elif change == "reuse":
        asyncio.run(conversation.generate(prepared, FakeModel(reply()), requests))
    elif change == "history":
        path = conversation.root / "events" / f"{conversation.state.history[-1]:06d}.json"
        data = read_json(path)
        data["response"] = "{}"
        path.write_text(json.dumps(data), encoding="utf-8")
    elif change == "source":
        conversation.preview_path("P001").write_bytes(b"changed")
    else:
        prepared = prepared.model_copy(update={"calls_used": 2})
    model = FakeModel(reply())
    before = snapshot(conversation.store.data_dir)
    with pytest.raises(CollageError):
        asyncio.run(conversation.generate(prepared, model))
    assert not model.contexts
    assert snapshot(conversation.store.data_dir) == before


def test_split_keeps_logical_allowance_without_provider_reservations(agent_project):
    conversation, requests = agent_project

    class UnloggedModel(FakeModel):
        async def complete(self, context, log, purpose):
            self.contexts.append(context)
            return next(self.responses)

    model = UnloggedModel("{}", intent("fresh"), "{}", "{}", reply())
    prepared = asyncio.run(conversation.interpret("Make a collage", model, requests))
    assert prepared.calls_used == 2 and requests.attempts() == []
    with pytest.raises(RequestRejected):
        asyncio.run(Conversation(conversation.store, "demo").generate(
            PreparedGeneration.model_validate_json(prepared.model_dump_json()), model,
        ))
    assert len(model.contexts) == 4
    conversation = Conversation(conversation.store, "demo")
    assert [event.outcome for event in conversation.history()] == [
        "invalid", "intent", "invalid", "invalid",
    ]


def test_split_keeps_outer_budget_and_preflight_failure_evidence(agent_project, tmp_path):
    conversation, requests = agent_project
    ledger = tmp_path / "budget.json"
    with call_budget(ledger, 1):
        prepared = asyncio.run(conversation.interpret("Make a collage", FakeModel(intent("fresh")), requests))
    with call_budget(ledger, 1), pytest.raises(CollageError, match="Outer call budget exhausted"):
        asyncio.run(Conversation(conversation.store, "demo").generate(prepared, FakeModel(reply())))
    assert read_json(ledger)["used"] == 1
    assert len(requests.attempts()) == 1
    conversation = Conversation(conversation.store, "demo")
    assert conversation.history()[-1].outcome == "error"
    assert conversation.history()[-1].attempt is None
    assert not conversation.history()[-1].generation_timeout


def test_reconstructed_generation_starts_its_deadline_and_preserves_settings(agent_project, monkeypatch):
    conversation, requests = agent_project
    clock = [1000.0]
    monkeypatch.setattr("ai_collage.agent.requests.monotonic", lambda: clock[0])
    requests.generation_reasoning = "high"
    prepared = asyncio.run(conversation.interpret("Make a collage", FakeModel(intent("fresh")), requests))
    clock[0] += 1000
    reopened = Conversation(conversation.store, "demo")
    before = snapshot(conversation.store.data_dir)
    with pytest.raises(CollageError, match="limits/reasoning changed"):
        asyncio.run(reopened.generate(prepared, FakeModel(reply()), RequestLog(conversation.store, "demo")))
    assert snapshot(conversation.store.data_dir) == before

    class ClockModel(FakeModel):
        async def complete(self, context, log, purpose):
            result = await super().complete(context, log, purpose)
            clock[0] += 50
            return result

    asyncio.run(reopened.generate(prepared, ClockModel("{}", reply())))
    attempts = requests.attempts()
    assert [attempt.timeout_seconds for attempt in attempts] == [120, 180, 130]
    assert [attempt.reasoning_effort for attempt in attempts] == ["high", "high", "high"]
    with pytest.raises(ValidationError):
        PreparedGeneration.model_validate({**prepared.model_dump(), "handoff_version": 2})


def test_generation_continues_in_a_fresh_process_with_network_blocked(agent_project, tmp_path):
    conversation, requests = agent_project
    prepared = asyncio.run(conversation.interpret("Make a collage", FakeModel(intent("fresh")), requests))
    handoff = tmp_path / "handoff.json"
    save(handoff, prepared)
    code = """
import asyncio
import socket
import sys
from pathlib import Path
from ai_collage.agent.conversation import Conversation
from ai_collage.agent.models import PreparedGeneration
from ai_collage.engine.projects import ProjectStore
from tests.agent.test_agent import FakeModel, reply
loop = asyncio.new_event_loop()
def blocked(*args, **kwargs):
    raise AssertionError("Offline continuation must not open network connections.")
socket.socket.connect = blocked
socket.create_connection = blocked
try:
    conversation = Conversation(ProjectStore(Path(sys.argv[1])), "demo")
    prepared = PreparedGeneration.model_validate_json(Path(sys.argv[2]).read_bytes())
    print(loop.run_until_complete(conversation.generate(prepared, FakeModel(reply()))).model_dump_json())
finally:
    loop.close()
"""
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])}
    completed = subprocess.run(
        [sys.executable, "-c", code, str(conversation.store.data_dir), str(handoff)],
        env=env, capture_output=True, text=True, timeout=30, check=True,
    )
    assert json.loads(completed.stdout)["proposal_id"] == "P001"
    reopened = Conversation(conversation.store, "demo")
    assert reopened.proposal("P001").intent == prepared.intent
    assert [item.stage for item in requests.attempts()] == ["interpretation", "generation"]
