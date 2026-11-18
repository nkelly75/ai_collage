import asyncio
import copy
import json
import socket
import sys

import pytest
from pydantic import ValidationError

from ai_collage.agent_budget import RunLedger
from ai_collage.agent_files import child, digest, save
from ai_collage.agent_models import Controls, Exchange, Preferences, REPLY
from ai_collage.conversation import Conversation
from ai_collage.models import CollageError
from ai_collage.projects import read_json

from .helpers import framed_layout_data, layout_data

_CONNECT = socket.socket.connect


@pytest.fixture(autouse=True)
def asyncio_wakeup_pair(monkeypatch):
    if sys.platform != "win32":
        return

    def pair():
        # Windows asyncio uses a private loopback pair for wakeups. Do not
        # unblock socket.connect for test/application traffic.
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            client = socket.socket()
            try:
                _CONNECT(client, listener.getsockname())
                server, _ = listener.accept()
            except OSError:
                client.close()
                raise
        return server, client

    monkeypatch.setattr(socket, "socketpair", pair)


class FakeModel:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.contexts = []

    async def complete(self, context, ledger, purpose):
        self.contexts.append(context)
        attempt = ledger.reserve(purpose, 100)
        response = next(self.responses)
        ledger.finish(attempt.model_copy(update={
            "status": "error" if isinstance(response, Exception) else "complete",
            "input_tokens": 10, "output_tokens": 20,
        }))
        if isinstance(response, Exception):
            raise response
        return response


def reply(data=None):
    return json.dumps({"kind": "proposal", "recipe": data or layout_data()})


def ask(conversation, ledger, *responses, prompt="Make a collage"):
    model = FakeModel(*responses)
    return asyncio.run(conversation.request(prompt, model, ledger)), model


@pytest.fixture
def agent_project(store, sources):
    store.create("demo", sources)
    ledger = RunLedger.provision(store, "offline-test")
    return Conversation(store, "demo", canvas=(100, 100)), ledger


def test_proposals_resume_accept_older_and_idempotence(agent_project):
    conversation, ledger = agent_project
    store = conversation.store
    p1, _ = ask(conversation, ledger, reply())
    png = conversation.preview_path(p1).read_bytes()
    assert store.load("demo").current_version is None
    altered = layout_data()
    altered["canvas"]["background"] = "#202020"
    p2, _ = ask(conversation, ledger, reply(altered))
    resumed = Conversation(store, "demo")
    assert resumed.state.baseline == p2
    assert resumed.accept(p1) == 1
    assert resumed.state.baseline == p1
    assert resumed.accept(p1) == 1
    assert resumed.accept(p2) == 2
    assert resumed.accept(p1) == 3
    assert store.version_paths("demo", 1)[1].read_bytes() == png
    assert store.version_paths("demo", 3)[1].read_bytes() == png
    assert len(ledger.attempts()) == 2


def test_question_and_answer_use_real_history(agent_project):
    conversation, ledger = agent_project
    question = '{"kind":"question","question":"Which photo number?"}'
    result, _ = ask(conversation, ledger, question, prompt="Make breakfast smaller")
    assert result == "Which photo number?"
    assert conversation.state.baseline is None
    _, model = ask(Conversation(conversation.store, "demo"), ledger, reply(), prompt="Photo 2")
    assert model.contexts[0]["history"][0]["prompt"] == "Make breakfast smaller"
    assert model.contexts[0]["history"][0]["response"] == question
    assert len(ledger.attempts()) == 2


@pytest.mark.parametrize("bad", [
    "```json\n{}\n```", '{"kind":"question","question":""}',
    '{"kind":"question","question":"Hi","recipe":{}}',
    '{"kind":"question","kind":"proposal"}',
    '{"kind":"proposal","recipe":{"x":NaN}}',
])
def test_invalid_response_one_correction(agent_project, bad):
    conversation, ledger = agent_project
    result, model = ask(conversation, ledger, bad, reply())
    assert result == "P001"
    assert len(model.contexts) == 2
    assert model.contexts[1]["validation_feedback"]
    assert len(ledger.attempts()) == 2


def test_four_invalid_responses_preserve_good_baseline_and_block_fifth(agent_project):
    conversation, ledger = agent_project
    p1, _ = ask(conversation, ledger, reply())
    model = FakeModel("{}", "{}", "{}", "{}", reply())
    with pytest.raises(CollageError, match="correction failed"):
        asyncio.run(conversation.request("Make it nicer", model, ledger))
    assert conversation.state.baseline == p1
    assert len(ledger.attempts()) == 5
    assert len(model.contexts) == 4
    assert all(context["editing_baseline"] == conversation.proposal(p1).recipe.model_dump(mode="json")
               for context in model.contexts)


def test_fourth_attempt_succeeds_with_latest_candidate_feedback(agent_project):
    conversation, ledger = agent_project
    bad = layout_data()
    bad["layers"][1]["box"]["y"] = 0.9
    newer = copy.deepcopy(bad)
    newer["layers"][1]["box"]["y"] = 0.8
    result, model = ask(conversation, ledger, "{}", reply(bad), reply(newer), reply())
    assert result == "P001"
    assert len(ledger.attempts()) == len(model.contexts) == 4
    assert [event.outcome for event in conversation.history()] == [
        "invalid", "invalid", "invalid", "proposal",
    ]
    for context, candidate in zip(model.contexts[2:], (bad, newer), strict=True):
        feedback = json.loads(context["validation_feedback"])
        assert feedback["photo_id"] == 2
        assert feedback["overshoot_px"]["bottom"] > 0
        assert feedback["sampled_footprint_bounds_px"][3] > 100
        assert context["history"][-1]["response"] == reply(candidate)
        assert context["editing_baseline"] is None
        assert len(context["validation_feedback"].encode("utf-8")) <= 8192
    assert (
        json.loads(model.contexts[2]["validation_feedback"])["overshoot_px"]["bottom"]
        > json.loads(model.contexts[3]["validation_feedback"])["overshoot_px"]["bottom"]
    )


def test_service_error_no_correction_and_recorded_prompt(agent_project):
    conversation, ledger = agent_project
    model = FakeModel(CollageError("service stopped"), reply())
    with pytest.raises(CollageError, match="service stopped"):
        asyncio.run(conversation.request("Make it nicer", model, ledger))
    assert len(ledger.attempts()) == 1
    assert len(model.contexts) == 1
    assert conversation.history()[-1].outcome == "error"
    assert conversation.history()[-1].prompt == "Make it nicer"


def test_controls_crop_and_canvas_are_hard_constraints(agent_project):
    conversation, ledger = agent_project
    with pytest.raises(CollageError, match="correction failed"):
        ask(conversation, ledger, *[reply(framed_layout_data())] * 4)
    conversation.controls(Controls(width=100, height=100, cropping=True))
    p1, _ = ask(conversation, ledger, reply(framed_layout_data()))
    conversation.controls(Controls(width=100, height=100))
    with pytest.raises(CollageError, match="Cropping"):
        conversation.accept(p1)
    conversation.controls(Controls(width=120, height=100, cropping=True))
    with pytest.raises(CollageError, match="canvas"):
        conversation.accept(p1)
    assert conversation.store.load("demo").current_version is None


def test_defaults_snapshot_and_ratings_stay_local(agent_project):
    conversation, ledger = agent_project
    p1, _ = ask(conversation, ledger, reply())
    conversation.rate(p1, "partly", "Position is good")
    save(child(conversation.store.owner_dir, "preferences.json"), Preferences(
        preferences_version=1, borders="avoid", rounding="avoid", tilt="avoid"
    ))
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.preferences.borders == "prefer"
    context = resumed.context("Make it smaller")
    assert not any(event["kind"] == "rating" for event in context["history"])
    assert "original_filename" not in json.dumps(context)
    assert "uploads" not in json.dumps(context)
    assert len(ledger.attempts()) == 1
    with pytest.raises(CollageError, match="captured"):
        Conversation(conversation.store, "demo", preferences=conversation.state_path)


@pytest.mark.parametrize("proposal_id", ["../outside", "P001/../state", "P999"])
def test_proposal_ids_do_not_escape_or_select_unpublished(agent_project, proposal_id):
    conversation, _ = agent_project
    with pytest.raises(CollageError):
        conversation.proposal(proposal_id)


def test_preview_tampering_is_not_silently_rendered(agent_project):
    conversation, ledger = agent_project
    proposal_id, _ = ask(conversation, ledger, reply())
    conversation.preview_path(proposal_id).write_bytes(b"tampered")
    with pytest.raises(CollageError, match="identity"):
        conversation.accept(proposal_id)
    assert conversation.store.load("demo").current_version is None


def test_external_acceptance_conflict_is_explicit(agent_project, tmp_path):
    conversation, ledger = agent_project
    from .helpers import write_layout

    conversation.store.apply_layout("demo", write_layout(tmp_path))
    with pytest.raises(CollageError, match="outside"):
        ask(conversation, ledger, reply())
    assert len(ledger.attempts()) == 0


def test_proposal_render_failure_does_not_replace_baseline(agent_project, monkeypatch):
    conversation, ledger = agent_project
    p1, _ = ask(conversation, ledger, reply())

    def fail(*args):
        raise OSError("simulated render failure")

    monkeypatch.setattr("ai_collage.conversation.render_layout", fail)
    with pytest.raises(OSError, match="simulated"):
        ask(conversation, ledger, reply())
    assert Conversation(conversation.store, "demo").state.baseline == p1
    assert len(ledger.attempts()) == 2
    failed = Conversation(conversation.store, "demo").history()[-1]
    assert failed.outcome == "error"
    assert failed.prompt == "Make a collage"
    assert failed.response == reply()
    assert failed.attempt == 2


def test_acceptance_reconciles_exact_commit_after_index_failure(agent_project, monkeypatch):
    conversation, ledger = agent_project
    p1, _ = ask(conversation, ledger, reply())

    def fail(*args, **kwargs):
        raise OSError("simulated index failure")

    monkeypatch.setattr(conversation, "_append", fail)
    with pytest.raises(OSError, match="index failure"):
        conversation.accept(p1)
    assert conversation.store.load("demo").current_version == 1
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.expected_version == 1
    assert resumed.state.baseline == p1
    assert resumed.accept(p1) == 1
    assert not resumed.intent_path.exists()


def test_acceptance_precommit_failure_is_not_replayed(agent_project, monkeypatch):
    conversation, ledger = agent_project
    p1, _ = ask(conversation, ledger, reply())

    def fail(*args, **kwargs):
        raise OSError("simulated publish failure")

    monkeypatch.setattr(conversation.store, "accept_recipe", fail)
    with pytest.raises(OSError, match="publish failure"):
        conversation.accept(p1)
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.expected_version is None
    assert not resumed.intent_path.exists()


def test_shared_ledger_49_50_51_and_no_reset(store):
    ledger = RunLedger.provision(store, "shared")
    for number in range(1, 51):
        current = RunLedger(store, "shared")
        reservation = current.reserve("offline", 100)
        assert reservation.number == number
    with pytest.raises(CollageError, match="exhausted"):
        RunLedger(store, "shared").reserve("must not dispatch", 100)
    assert len(ledger.summary()["unknown_usage_attempts"]) == 50
    with pytest.raises(FileExistsError):
        RunLedger.provision(store, "shared")


def test_oversized_input_does_not_reserve_attempt(store):
    ledger = RunLedger.provision(store, "bounded")
    with pytest.raises(CollageError, match="token bound"):
        ledger.reserve("too large", 50_001)
    assert ledger.attempts() == []


def test_actual_usage_violation_halts_followup(store):
    ledger = RunLedger.provision(store, "bounded")
    attempt = ledger.reserve("offline", 100)
    with pytest.raises(CollageError, match="halted"):
        ledger.finish(attempt.model_copy(update={"status": "complete", "input_tokens": 50_001}))
    with pytest.raises(CollageError, match="halted"):
        RunLedger(store, "bounded").reserve("blocked", 100)


def test_chat_local_commands_without_agent_dependencies(agent_project, monkeypatch, capsys):
    conversation, _ = agent_project
    from ai_collage.__main__ import main

    for module in ("agent_framework", "azure.identity", "openai", "tiktoken"):
        monkeypatch.setitem(sys.modules, module, None)
    lines = iter(["/status", "/not-a-command", "/canvas 120 100", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(lines))
    assert main([
        "--data-dir", str(conversation.store.data_dir),
        "chat", "--project", "demo", "--no-open",
    ]) == 0
    output = capsys.readouterr()
    assert "Local-only" in output.out
    assert "Unknown command" in output.err


def response_envelope(text, *, status="completed"):
    return {
        "id": "resp_offline", "object": "response", "created_at": 1,
        "model": "gpt-5.4-mini", "status": status,
        "output": [{
            "id": "msg_offline", "type": "message", "role": "assistant", "status": "completed",
            "content": [{"type": "output_text", "text": text, "annotations": []}],
        }],
        "usage": {
            "input_tokens": 100, "output_tokens": 20, "total_tokens": 120,
            "input_tokens_details": {"cached_tokens": 10},
            "output_tokens_details": {"reasoning_tokens": 5},
        },
        "incomplete_details": {"reason": "max_output_tokens"} if status == "incomplete" else None,
    }


def test_prompt_sources_reload_independently_of_cwd_and_fail_if_missing(tmp_path, monkeypatch):
    from ai_collage import agent_provider

    package = tmp_path / "package"
    prompt = package / "prompts" / "layout-agent.md"
    guide = tmp_path / "docs" / "layout-format.md"
    prompt.parent.mkdir(parents=True)
    guide.parent.mkdir()
    prompt.write_text("# Agent\nFirst instructions.\n", encoding="utf-8")
    guide.write_text("# Format\nShared geometry rules.\n", encoding="utf-8")
    monkeypatch.setattr(agent_provider, "__file__", str(package / "agent_provider.py"))
    monkeypatch.chdir(guide.parent)

    assert agent_provider.instructions() == (
        prompt.read_text(encoding="utf-8")
        + "\n\n# Current recipe field guide\n\n"
        + guide.read_text(encoding="utf-8")
    )
    prompt.write_text("# Agent\nRevised instructions.\n", encoding="utf-8")
    assert "Revised instructions." in agent_provider.instructions()
    assert "First instructions." not in agent_provider.instructions()
    prompt.unlink()
    with pytest.raises(FileNotFoundError):
        agent_provider.instructions()
    prompt.write_text("# Agent\nRestored instructions.\n", encoding="utf-8")
    guide.unlink()
    with pytest.raises(FileNotFoundError):
        agent_provider.instructions()


@pytest.mark.parametrize("status", ["completed", "incomplete", "429", "401", "timeout", "oversize"])
def test_real_framework_mocked_http_gate(store, status):
    pytest.importorskip("agent_framework")
    import httpx
    from openai import AsyncOpenAI, APIError
    from agent_framework.exceptions import AgentFrameworkException
    from ai_collage.agent_provider import ENDPOINT, guarded_transport, instructions, run_agent

    ledger = RunLedger.provision(store, "mocked")
    captured = []
    text = '{"kind":"question","question":"Which photo?"}'

    async def handler(request):
        captured.append(json.loads(request.content))
        body = captured[-1]
        instruction_texts = [body.get("instructions", "")]
        instruction_texts.extend(
            part.get("text", "")
            for message in body["input"]
            for part in message.get("content", [])
            if isinstance(part, dict)
        )
        assert instructions() in instruction_texts
        schema = captured[-1]["text"]["format"]["schema"]
        assert schema["type"] == "object" and schema["additionalProperties"] is False
        assert not {"oneOf", "anyOf", "allOf", "enum", "const", "not"}.intersection(schema)
        assert set(schema["properties"]) == {"kind", "recipe", "question"}
        assert "oneOf" not in json.dumps(schema) and "discriminator" not in json.dumps(schema)
        if status in {"429", "401"}:
            return httpx.Response(int(status), json={"error": {"code": "offline", "message": "offline"}})
        if status == "timeout":
            raise httpx.ReadTimeout("simulated offline timeout")
        return httpx.Response(200, json=response_envelope(
            text, status="incomplete" if status == "incomplete" else "completed"
        ))

    gate = guarded_transport(ledger, "mock", httpx.MockTransport(handler))

    async def execute():
        async with AsyncOpenAI(
            base_url=ENDPOINT, api_key="offline-not-a-real-credential", max_retries=0,
            http_client=httpx.AsyncClient(transport=gate),
        ) as sdk:
            return await run_agent({"user_request": "x" * (60_000 if status == "oversize" else 1)}, sdk, ledger)

    if status == "completed":
        assert asyncio.run(execute()) == text
    else:
        with pytest.raises((CollageError, APIError, AgentFrameworkException)):
            asyncio.run(execute())
    if status == "oversize":
        assert captured == []
        assert ledger.attempts() == []
        return
    assert len(captured) == 1
    assert captured[0]["store"] is False
    assert captured[0]["max_output_tokens"] == 25_000
    assert captured[0]["reasoning"] == {"effort": "high"}
    assert not captured[0].get("tools")
    assert captured[0]["text"]["format"]["type"] == "json_schema"
    assert len(ledger.attempts()) == 1
    if status not in {"429", "401", "timeout"}:
        assert ledger.summary()["input_tokens"] == 100
        assert ledger.summary()["output_tokens"] == 20
        assert ledger.summary()["unknown_usage_attempts"] == []
    else:
        assert ledger.attempts()[0].status == "error"
        assert ledger.attempts()[0].duration is not None
        assert ledger.summary()["unknown_usage_attempts"] == [1]


def test_gate_rejects_an_extra_dispatch(store):
    pytest.importorskip("agent_framework")
    import httpx
    from ai_collage.agent_provider import DEPLOYMENT, ENDPOINT, guarded_transport

    ledger = RunLedger.provision(store, "mocked")
    dispatched = []

    async def handler(request):
        dispatched.append(request)
        return httpx.Response(200, json=response_envelope('{"kind":"question","question":"Which photo?"}'))

    gate = guarded_transport(ledger, "mock", httpx.MockTransport(handler))

    async def execute():
        async with httpx.AsyncClient(transport=gate) as client:
            payload = {
                "model": DEPLOYMENT, "store": False, "max_output_tokens": 25_000,
                "reasoning": {"effort": "high"}, "input": [],
            }
            await client.post(ENDPOINT + "responses", json=payload)
            with pytest.raises(CollageError, match="extra inference"):
                await client.post(ENDPOINT + "responses", json=payload)

    asyncio.run(execute())
    assert len(dispatched) == len(ledger.attempts()) == 1


def test_scripted_comparisons_preserve_exact_unrelated_fields(agent_project):
    from ai_collage.evaluate import compare
    from ai_collage.geometry import resolve_layout
    from ai_collage.models import InputLayout

    conversation, _ = agent_project
    photos = conversation.store.load("demo").photos

    def resolve(value):
        return resolve_layout(InputLayout.model_validate(value), photos, 1)

    data = layout_data()
    data["canvas"]["background"] = "#282828"
    data["layers"][0]["box"]["width"] = 0.4
    for layer in data["layers"]:
        layer.update(border={"width_px": 1, "color": "#FFFFFF"}, corner_radius_px=1, rotation_degrees=1)
    initial = resolve(data)
    assert compare(0, initial, None) == []
    smaller = copy.deepcopy(data)
    smaller["layers"][1]["box"] = {"x": 0.51, "y": 0.12, "width": 0.18}
    resized = resolve(smaller)
    assert compare(1, resized, initial) == []
    changed = copy.deepcopy(smaller)
    changed["layers"][0]["corner_radius_px"] = 2
    assert "Unrelated" in " ".join(compare(1, resolve(changed), initial))
    for layer in smaller["layers"]:
        layer["border"] = None
    borderless = resolve(smaller)
    assert compare(2, borderless, resized) == []
    for layer in smaller["layers"]:
        layer["rotation_degrees"] = 0
    straight = resolve(smaller)
    assert compare(3, straight, borderless) == []
    smaller["layers"].reverse()
    assert "stacking" in " ".join(compare(3, resolve(smaller), borderless))


def test_response_union_strictness_and_size():
    with pytest.raises(ValidationError):
        REPLY.validate_python({"kind": "question", "question": " "})
    with pytest.raises(ValidationError):
        REPLY.validate_python({"kind": "question", "question": "a" * 1001})
