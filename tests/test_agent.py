import asyncio
import copy
import json
import socket
import sys

import pytest
from pydantic import ValidationError

from ai_collage.agent_requests import RequestLog
from ai_collage.agent_files import child, digest, save
from ai_collage.agent_models import Controls, Exchange, LayoutSource, Preferences, INTENT
from ai_collage.conversation import Conversation
from ai_collage.models import CollageError
from ai_collage.models import InputLayout
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

    async def complete(self, context, requests, purpose):
        self.contexts.append(context)
        attempt = requests.reserve(purpose, 100)
        response = next(self.responses)
        requests.finish(attempt.model_copy(update={
            "status": "error" if isinstance(response, Exception) else "complete",
            "input_tokens": 10, "output_tokens": 20,
        }))
        if isinstance(response, Exception):
            raise response
        return response


def reply(data=None):
    return json.dumps(data or layout_data())


def intent(action, **fields):
    return json.dumps({"action": action, "references": [], "name_updates": [], **fields})


def turns(*responses):
    return [
        item for index, response in enumerate(responses)
        for item in (intent("fresh") if index == 0 else intent("edit", source="current"), response)
    ]


def ask(conversation, requests, *responses, prompt="Make a collage", action=None):
    action = action or (
        intent("edit", source="current") if conversation.baseline() else intent("fresh")
    )
    if prompt == "Make a collage" and json.loads(action)["action"] == "select":
        prompt = f"Return to {json.loads(action)['proposal_id']}"
    model = FakeModel(action, *responses)
    result = asyncio.run(conversation.request(prompt, model, requests))
    return result.proposal_id if result.kind != "question" else result.question, model


@pytest.fixture
def agent_project(store, sources):
    store.create("demo", sources)
    requests = RequestLog(store, "demo")
    return Conversation(store, "demo", canvas=(100, 100)), requests


def test_proposals_resume_accept_older_and_idempotence(agent_project):
    conversation, requests = agent_project
    store = conversation.store
    p1, _ = ask(conversation, requests, reply())
    png = conversation.preview_path(p1).read_bytes()
    assert store.load("demo").current_version is None
    altered = layout_data()
    altered["canvas"]["background"] = "#202020"
    p2, _ = ask(conversation, requests, reply(altered))
    resumed = Conversation(store, "demo")
    assert resumed.state.baseline == p2
    assert resumed.accept(p1) == 1
    assert store.load_layout(store.load("demo"), 1).recipe == resumed.proposal(p1).recipe
    assert resumed.state.baseline == p1
    assert resumed.accept(p1) == 1
    assert resumed.accept(p2) == 2
    assert resumed.accept(p1) == 3
    assert store.version_paths("demo", 1)[1].read_bytes() == png
    assert store.version_paths("demo", 3)[1].read_bytes() == png
    assert len(requests.attempts()) == 4


def test_question_and_answer_use_real_history(agent_project):
    conversation, requests = agent_project
    question = intent("question", question="Which photo number?")
    result, _ = ask(conversation, requests, action=question, prompt="Make breakfast smaller")
    assert result == "Which photo number?"
    assert conversation.state.baseline is None
    _, model = ask(Conversation(conversation.store, "demo"), requests, reply(), prompt="Photo 2")
    assert model.contexts[0]["history"][0]["prompt"] == "Make breakfast smaller"
    assert model.contexts[0]["history"][0]["response"] == question
    assert len(requests.attempts()) == 3


def test_resize_context_keeps_authored_center_instead_of_rounded_pixel_center(agent_project):
    conversation, requests = agent_project
    data = layout_data()
    data["layers"][0]["box"] = {"center_x": 0.3, "center_y": 0.3, "width": 0.19}
    p1, _ = ask(conversation, requests, reply(data))
    baseline = conversation.proposal(p1)
    resumed = Conversation(conversation.store, "demo")
    smaller = copy.deepcopy(data)
    smaller["layers"][0]["box"]["width"] = 0.17
    p2, model = ask(resumed, requests, reply(smaller), prompt="Make photo 1 smaller in the same spot")
    context = model.contexts[1]
    assert context["editing_baseline"] == baseline.recipe.model_dump(mode="json")
    assert context["editing_baseline"]["schema_version"] == 3
    frame = context["baseline_geometry"][0]
    assert frame == baseline.geometry[0].model_dump(mode="json")
    assert "untilted_center_pixels" not in frame
    pixels = frame["box_pixels"]
    assert pixels["x"] + pixels["width"] / 2 == 30.5
    assert baseline.recipe.layers[0].box.center_x * 100 == 30
    updated = resumed.proposal(p2)
    assert updated.recipe.layers[0].box.model_dump() == {
        "center_x": 0.3, "center_y": 0.3, "width": 0.17,
    }
    assert resumed.store.load("demo").current_version is None


@pytest.mark.parametrize("bad", [
    "```json\n{}\n```", '{"kind":"question","question":""}',
    '{"kind":"question","question":"Hi","recipe":{}}',
    '{"kind":"question","kind":"proposal"}',
    '{"kind":"proposal","recipe":{"x":NaN}}',
])
def test_invalid_response_one_correction(agent_project, bad):
    conversation, requests = agent_project
    result, model = ask(conversation, requests, bad, reply())
    assert result == "P001"
    assert len(model.contexts) == 3
    assert model.contexts[2]["validation_feedback"]
    assert len(requests.attempts()) == 3


def test_four_invalid_responses_preserve_good_baseline_and_block_fifth(agent_project):
    conversation, requests = agent_project
    p1, _ = ask(conversation, requests, reply())
    model = FakeModel(intent("edit", source="current"), "{}", "{}", "{}", reply())
    with pytest.raises(CollageError, match="correction failed"):
        asyncio.run(conversation.request("Make it nicer", model, requests))
    assert conversation.state.baseline == p1
    assert len(requests.attempts()) == 6
    assert len(model.contexts) == 4
    assert all(context["editing_baseline"] == conversation.proposal(p1).recipe.model_dump(mode="json")
               for context in model.contexts[1:])


def test_fourth_attempt_succeeds_with_latest_candidate_feedback(agent_project):
    conversation, requests = agent_project
    bad = layout_data()
    bad["layers"][1]["box"]["center_y"] = 0.95
    newer = copy.deepcopy(bad)
    newer["layers"][1]["box"]["center_y"] = 0.9
    result, model = ask(conversation, requests, reply(bad), reply(newer), reply())
    assert result == "P001"
    assert len(requests.attempts()) == len(model.contexts) == 4
    assert [event.outcome for event in conversation.history()] == [
        "intent", "invalid", "invalid", "proposal",
    ]
    for context, candidate in zip(model.contexts[2:], (bad, newer), strict=True):
        feedback = json.loads(context["validation_feedback"])
        assert feedback["photo_id"] == 2
        assert feedback["overshoot_px"]["bottom"] > 0
        assert feedback["sampled_footprint_bounds_px"][3] > 100
        assert "safe_box_position_normalized" not in feedback
        assert (
            feedback["safe_box_center_normalized"]["center_y"][1]
            < candidate["layers"][1]["box"]["center_y"]
        )
        assert context["failed_candidate"] == reply(candidate)
        assert context["editing_baseline"] is None
        assert len(context["validation_feedback"].encode("utf-8")) <= 8192
    assert (
        json.loads(model.contexts[2]["validation_feedback"])["overshoot_px"]["bottom"]
        > json.loads(model.contexts[3]["validation_feedback"])["overshoot_px"]["bottom"]
    )


def test_service_error_no_correction_and_recorded_prompt(agent_project):
    conversation, requests = agent_project
    model = FakeModel(CollageError("service stopped"), reply())
    with pytest.raises(CollageError, match="service stopped"):
        asyncio.run(conversation.request("Make it nicer", model, requests))
    assert len(requests.attempts()) == 1
    assert len(model.contexts) == 1
    assert conversation.history()[-1].outcome == "error"
    assert conversation.history()[-1].prompt == "Make it nicer"


def test_conversation_records_requests_without_explicit_accounting_setup(agent_project):
    conversation, requests = agent_project
    result = asyncio.run(conversation.request("Make a collage", FakeModel(*turns(reply()))))
    assert result.kind == "proposal" and result.proposal_id == "P001"
    assert len(requests.attempts()) == 2
    assert conversation.history()[-1].run_id is None


def test_controls_crop_and_canvas_are_hard_constraints(agent_project):
    conversation, requests = agent_project
    with pytest.raises(CollageError, match="correction failed"):
        ask(conversation, requests, *[reply(framed_layout_data())] * 4)
    conversation.controls(Controls(width=100, height=100, cropping=True))
    p1, _ = ask(conversation, requests, reply(framed_layout_data()))
    conversation.controls(Controls(width=100, height=100))
    with pytest.raises(CollageError, match="Cropping"):
        conversation.accept(p1)
    conversation.controls(Controls(width=120, height=100, cropping=True))
    with pytest.raises(CollageError, match="canvas"):
        conversation.accept(p1)
    assert conversation.store.load("demo").current_version is None


def test_defaults_snapshot_and_ratings_stay_local(agent_project):
    conversation, requests = agent_project
    p1, _ = ask(conversation, requests, reply())
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
    assert len(requests.attempts()) == 2
    with pytest.raises(CollageError, match="captured"):
        Conversation(conversation.store, "demo", preferences=conversation.state_path)


def test_compact_context_bounds_history_and_loads_old_sources_on_demand(agent_project):
    conversation, requests = agent_project
    earlier_size = None
    for number in range(20):
        ask(conversation, requests, reply(), prompt=f"Design request {number}")
        if number == 15:
            earlier_size = len(json.dumps(conversation.context("Make another edit")))
    assert earlier_size is not None
    assert len(json.dumps(conversation.context("Make another edit"))) <= earlier_size + 256
    before = {path: path.read_bytes() for path in conversation.root.rglob("*") if path.is_file()}
    context = conversation.context("Go back to the second one")
    assert context["original_request"] == "Design request 0"
    assert [entry["prompt"] for entry in context["history"]] == [
        "Design request 17", "Design request 18", "Design request 19",
    ]
    assert context["history_omitted"] == 17
    assert len(context["compact_tasks"]) == 12
    assert "schema_version" not in json.dumps(context["history"])
    assert all(entry["response"] is None for entry in context["history"])
    ids = {entry["proposal_id"] for entry in context["proposals"]}
    assert {"P001", "P002", "P018", "P019", "P020"} <= ids
    assert len(ids) <= 17
    assert context["proposal_count"] == 20
    assert context["current_layout"] == conversation.proposal("P020").recipe.model_dump(mode="json")
    assert before == {path: path.read_bytes() for path in conversation.root.rglob("*") if path.is_file()}
    for prompt in ("Return to P004", "Return to the 4th one"):
        assert "P004" in {
            entry["proposal_id"] for entry in conversation.context(prompt)["proposals"]
        }

    proposal_id, model = ask(
        conversation, requests, reply(), prompt="Retry that old edit",
        action=intent("retry", proposal_id="P002"),
    )
    generation = model.contexts[-1]
    assert generation["original_task"] == "Design request 1"
    assert generation["editing_baseline"] == conversation.proposal("P001").recipe.model_dump(mode="json")
    assert generation["reference_to_avoid"] == conversation.proposal("P002").recipe.model_dump(mode="json")
    assert conversation.proposal(proposal_id).parent == "P001"
    assert len(conversation.history()) == 42
    selected, _ = ask(conversation, requests, action=intent("select", proposal_id="P004"))
    assert selected == "P004"
    assert conversation.state.baseline == "P004"
    assert conversation.preview_path("P004").read_bytes() == before[conversation.preview_path("P004")]


@pytest.mark.parametrize("proposal_id", ["../outside", "P001/../state", "P999"])
def test_proposal_ids_do_not_escape_or_select_unpublished(agent_project, proposal_id):
    conversation, _ = agent_project
    with pytest.raises(CollageError):
        conversation.proposal(proposal_id)


def test_preview_tampering_is_not_silently_rendered(agent_project):
    conversation, requests = agent_project
    proposal_id, _ = ask(conversation, requests, reply())
    conversation.preview_path(proposal_id).write_bytes(b"tampered")
    with pytest.raises(CollageError, match="identity"):
        conversation.accept(proposal_id)
    assert conversation.store.load("demo").current_version is None


def test_external_acceptance_conflict_is_explicit(agent_project, tmp_path):
    conversation, requests = agent_project
    from .helpers import write_layout

    conversation.store.apply_layout("demo", write_layout(tmp_path))
    with pytest.raises(CollageError, match="outside"):
        ask(conversation, requests, reply())
    assert len(requests.attempts()) == 0


def test_proposal_render_failure_does_not_replace_baseline(agent_project, monkeypatch):
    conversation, requests = agent_project
    p1, _ = ask(conversation, requests, reply())

    def fail(*args):
        raise OSError("simulated render failure")

    monkeypatch.setattr("ai_collage.conversation.render_layout", fail)
    with pytest.raises(OSError, match="simulated"):
        ask(conversation, requests, reply())
    assert Conversation(conversation.store, "demo").state.baseline == p1
    assert len(requests.attempts()) == 4
    failed = Conversation(conversation.store, "demo").history()[-1]
    assert failed.outcome == "error"
    assert failed.prompt == "Make a collage"
    assert failed.response == reply()
    assert failed.attempt == 4


@pytest.mark.parametrize("field,value", [
    ("task_turn", 999),
    ("task_request", "An unrelated task"),
    ("source", LayoutSource(proposal_id="P999")),
])
def test_invalid_provenance_is_rejected_before_publication(
    agent_project, monkeypatch, field, value,
):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    publish = conversation._publish

    def changed_intent(prompt, raw, resolved, log, resolved_intent):
        return publish(
            prompt, raw, resolved, log, resolved_intent.model_copy(update={field: value}),
        )

    monkeypatch.setattr(conversation, "_publish", changed_intent)
    with pytest.raises(CollageError, match="identity"):
        ask(conversation, requests, reply())
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.baseline == first
    assert not (conversation.root / "proposals" / "P002").exists()
    assert [event.outcome for event in resumed.history()] == [
        "intent", "proposal", "intent", "error",
    ]
    assert resumed.state.accepted_proposal is None


def test_acceptance_reconciles_exact_commit_after_index_failure(agent_project, monkeypatch):
    conversation, requests = agent_project
    p1, _ = ask(conversation, requests, reply())

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
    conversation, requests = agent_project
    p1, _ = ask(conversation, requests, reply())

    def fail(*args, **kwargs):
        raise OSError("simulated publish failure")

    monkeypatch.setattr(conversation.store, "accept_recipe", fail)
    with pytest.raises(OSError, match="publish failure"):
        conversation.accept(p1)
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.expected_version is None
    assert not resumed.intent_path.exists()


def test_project_request_log_keeps_history_without_a_cumulative_cap(store):
    requests = RequestLog(store, "demo")
    assert not requests.root.exists()
    for number in range(1, 52):
        current = RequestLog(store, "demo")
        reservation = current.reserve("offline", 100)
        assert reservation.number == number
    assert len(requests.summary()["unknown_usage_attempts"]) == 51
    assert requests.root == store.project_dir("demo") / "conversation" / "requests"
    assert RequestLog(store, "another-project").attempts() == []
    assert not (store.owner_dir / "agent-runs").exists()


def test_oversized_input_does_not_reserve_attempt(store):
    requests = RequestLog(store, "bounded")
    with pytest.raises(CollageError, match="token bound"):
        requests.reserve("too large", 50_001)
    assert requests.attempts() == []


@pytest.mark.parametrize("usage", [{"input_tokens": 50_001}, {"output_tokens": 25_001}])
def test_actual_usage_violation_is_recorded_and_stops_the_request(store, usage):
    requests = RequestLog(store, "bounded")
    attempt = requests.reserve("offline", 100)
    with pytest.raises(CollageError, match="per-request limit"):
        requests.finish(attempt.model_copy(update={"status": "complete", **usage}))
    assert all(getattr(requests.attempts()[0], key) == value for key, value in usage.items())
    assert RequestLog(store, "bounded").reserve("next explicit request", 100).number == 2


def test_chat_local_commands_without_agent_dependencies(agent_project, monkeypatch, capsys):
    conversation, _ = agent_project
    from ai_collage.__main__ import main

    for module in ("agent_framework", "azure.identity", "openai", "tiktoken"):
        monkeypatch.setitem(sys.modules, module, None)
    lines = iter(["/status", "/not-a-command", "/canvas 120 100", "Make a collage", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(lines))
    assert main([
        "--data-dir", str(conversation.store.data_dir),
        "chat", "--project", "demo", "--no-open",
    ]) == 0
    output = capsys.readouterr()
    assert "Local-only" in output.out
    assert "Unknown command" in output.err
    assert "restart chat with --live" in output.err
    assert not RequestLog(conversation.store, "demo").root.exists()


def test_chat_live_opt_in_needs_no_allowance(agent_project, monkeypatch, capsys):
    conversation, requests = agent_project
    from ai_collage.__main__ import main

    model = FakeModel(*turns(reply()))
    monkeypatch.setattr("ai_collage.agent_provider.FoundryModel", lambda: model)
    lines = iter(["Make a collage", "/status", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(lines))
    assert main([
        "--data-dir", str(conversation.store.data_dir),
        "chat", "--project", "demo", "--live", "--no-open",
    ]) == 0
    output = capsys.readouterr()
    assert not output.err and "Project requests: 2." in output.out
    assert len(model.contexts) == len(requests.attempts()) == 2
    assert not (conversation.store.owner_dir / "agent-runs").exists()
    assert conversation.store.load("demo").current_version is None


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
@pytest.mark.parametrize("stage", ["interpretation", "generation"])
def test_real_framework_mocked_http_gate(store, status, stage):
    pytest.importorskip("agent_framework")
    import httpx
    from openai import AsyncOpenAI, APIError
    from agent_framework.exceptions import AgentFrameworkException
    from ai_collage.agent_provider import ENDPOINT, guarded_transport, instructions, run_agent

    requests = RequestLog(store, "mocked")
    captured = []
    text = reply() if stage == "generation" else intent("fresh")

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
        assert instructions(stage) in instruction_texts
        schema = captured[-1]["text"]["format"]["schema"]
        assert schema["type"] == "object" and schema["additionalProperties"] is False
        assert not {"oneOf", "anyOf", "allOf", "enum", "const", "not"}.intersection(schema)
        assert set(schema["properties"]) == (
            {"schema_version", "canvas", "layers"} if stage == "generation"
            else {"action", "source", "proposal_id", "question", "references", "name_updates",
                  "decision", "receipt_event", "continuation", "navigation", "continues_task", "return_confirmation"}
        )
        assert "oneOf" not in json.dumps(schema) and "discriminator" not in json.dumps(schema)
        definitions = schema["$defs"]
        if stage == "generation":
            version = schema["properties"]["schema_version"]
            assert version["minimum"] == version["maximum"] == 3
            assert set(definitions["WholeBox"]["required"]) == {
                "center_x", "center_y", "width",
            }
        if status in {"429", "401"}:
            return httpx.Response(int(status), json={"error": {"code": "offline", "message": "offline"}})
        if status == "timeout":
            raise httpx.ReadTimeout("simulated offline timeout")
        return httpx.Response(200, json=response_envelope(
            text, status="incomplete" if status == "incomplete" else "completed"
        ))

    context = {
        "stage": stage,
        "user_request": "x" * (60_000 if status == "oversize" else 1),
    }
    gate = guarded_transport(requests, "mock", httpx.MockTransport(handler), context=context)

    async def execute():
        async with AsyncOpenAI(
            base_url=ENDPOINT, api_key="offline-not-a-real-credential", max_retries=0,
            http_client=httpx.AsyncClient(transport=gate),
        ) as sdk:
            return await run_agent(context, sdk, requests)

    if status == "completed":
        assert asyncio.run(execute()) == text
        if stage == "generation":
            assert InputLayout.model_validate(json.loads(text)).schema_version == 3
        else:
            assert INTENT.validate_python(json.loads(text)).action == "fresh"
    else:
        with pytest.raises((CollageError, APIError, AgentFrameworkException)):
            asyncio.run(execute())
    if status == "oversize":
        assert captured == []
        assert requests.attempts() == []
        return
    assert len(captured) == 1
    assert captured[0]["store"] is False
    assert captured[0]["max_output_tokens"] == 25_000
    assert captured[0]["reasoning"] == {"effort": "low" if stage == "generation" else "high"}
    assert not captured[0].get("tools")
    assert captured[0]["text"]["format"]["type"] == "json_schema"
    assert len(requests.attempts()) == 1
    if status not in {"429", "401", "timeout"}:
        assert requests.summary()["input_tokens"] == 100
        assert requests.summary()["output_tokens"] == 20
        assert requests.summary()["unknown_usage_attempts"] == []
    else:
        assert requests.attempts()[0].status == "error"
        assert requests.attempts()[0].duration is not None
        assert requests.summary()["unknown_usage_attempts"] == [1]


def test_gate_rejects_an_extra_dispatch(store):
    pytest.importorskip("agent_framework")
    import httpx
    from ai_collage.agent_provider import DEPLOYMENT, ENDPOINT, guarded_transport

    requests = RequestLog(store, "mocked")
    dispatched = []

    async def handler(request):
        dispatched.append(request)
        return httpx.Response(200, json=response_envelope('{"kind":"question","question":"Which photo?"}'))

    gate = guarded_transport(requests, "mock", httpx.MockTransport(handler))

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
    assert len(dispatched) == len(requests.attempts()) == 1


@pytest.mark.parametrize("essential_oversize", [False, True])
def test_actual_payload_trims_optional_history_before_reserving(store, essential_oversize):
    pytest.importorskip("agent_framework")
    import httpx
    from openai import AsyncOpenAI
    from agent_framework.exceptions import AgentFrameworkException
    from ai_collage.agent_provider import ENDPOINT, guarded_transport, run_agent

    context = {
        "stage": "generation", "original_request": "Keep the original design",
        "history": [{"task_id": i + 1, "prompt": str(i) + "x" * 16_000} for i in range(3)],
        "history_omitted": 4,
        "recent_tasks": [{"task_id": i + 1, "outcome": "proposal"} for i in range(3)],
        "compact_tasks": [{"task_id": i + 10, "request": "y" * 16_000} for i in range(3)],
        "compact_tasks_omitted": 2,
        "required_tasks": [{"task_id": 8, "request": "before thicker borders", "proposal_id": "P001"}],
        "active_task": {"request": "Return to before thicker borders", "answers": ["Yes"]},
        "failed_task": {
            "task_id": 8, "resolved_intent": {"action": "edit", "source": {"proposal_id": "P001"}},
        },
        "proposals": [{"proposal_id": "P001"}],
        "user_request": "x" * 60_000 if essential_oversize else "Make photo 2 smaller",
        "editing_baseline": layout_data(), "original_task": "Make photo 2 smaller",
        "pending_question": {"prompt": "Make one smaller", "response": "Which photo?"},
        "failed_candidate": reply(), "validation_feedback": "The box is outside the canvas",
        "photo_names": [{"name": "breakfast", "photo_id": 2, "event_id": 1, "quote": "photo 2 is breakfast"}],
        "resolved_intent": {"references": [photo_reference("breakfast", 2)]},
    }
    original = copy.deepcopy(context)
    requests = RequestLog(store, "trim")
    captured = []

    async def handler(request):
        captured.append(request)
        return httpx.Response(200, json=response_envelope(reply()))

    gate = guarded_transport(requests, "trim: generation", httpx.MockTransport(handler), context=context)

    async def execute():
        async with AsyncOpenAI(
            base_url=ENDPOINT, api_key="offline", max_retries=0,
            http_client=httpx.AsyncClient(transport=gate),
        ) as sdk:
            return await run_agent(context, sdk, requests)

    if essential_oversize:
        with pytest.raises(AgentFrameworkException):
            asyncio.run(execute())
        assert captured == [] and requests.attempts() == []
        assert context["history"] == []
        assert "no request was dispatched" in str(gate.local_error)
        assert "50,000" in str(gate.local_error)
    else:
        assert asyncio.run(execute()) == reply()
        assert len(captured) == len(requests.attempts()) == 1
        assert requests.attempts()[0].input_bound == len(captured[0].content) + 4096 <= 50_000
        body = json.loads(captured[0].content)
        assert str(len(captured[0].content)) == captured[0].headers["content-length"]
        texts = [
            part["text"] for message in body["input"] for part in message["content"]
            if part.get("type") == "input_text"
        ]
        assert json.dumps(context, ensure_ascii=False) in texts
    removed = len(original["history"]) - len(context["history"])
    assert removed > 0
    assert context["history"] == original["history"][removed:]
    assert context["history_omitted"] == original["history_omitted"] + removed
    assert context["compact_tasks"] == [] and context["compact_tasks_omitted"] == 5
    assert context["recent_tasks"] == original["recent_tasks"][removed:]
    optional = {"history", "history_omitted", "recent_tasks", "compact_tasks", "compact_tasks_omitted",
                "proposals", "proposals_omitted"}
    assert {key: value for key, value in context.items() if key not in optional} == {
        key: value for key, value in original.items() if key not in optional
    }


def test_foundry_preserves_local_input_limit_error_without_credentials_or_dispatch(store, monkeypatch):
    pytest.importorskip("agent_framework")
    import httpx
    from ai_collage.agent_provider import FoundryModel

    class OfflineCredential:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    async def no_dispatch(request):
        raise AssertionError("Oversized input must not reach HTTP dispatch")

    monkeypatch.setattr("azure.identity.aio.DefaultAzureCredential", lambda **kwargs: OfflineCredential())
    monkeypatch.setattr("azure.identity.aio.get_bearer_token_provider", lambda *args: "offline")
    monkeypatch.setattr("httpx.AsyncHTTPTransport", lambda **kwargs: httpx.MockTransport(no_dispatch))
    requests = RequestLog(store, "limit")
    with pytest.raises(CollageError, match="conservative token bound") as failure:
        asyncio.run(FoundryModel().complete(
            {"stage": "generation", "user_request": "x" * 60_000}, requests, "limit: generation",
        ))
    assert "ChatClientException" not in str(failure.value)
    assert "50,000" in str(failure.value)
    assert "Saved proposals are unchanged" in str(failure.value)
    assert requests.attempts() == []


def test_response_union_strictness_and_size():
    with pytest.raises(ValidationError):
        INTENT.validate_json(intent("question", question=" "))
    with pytest.raises(ValidationError):
        INTENT.validate_json(intent("question", question="a" * 1001))


def test_optional_outer_cap_survives_new_projects_and_context_restarts(store, tmp_path):
    import httpx
    from ai_collage.agent_provider import DEPLOYMENT, ENDPOINT, guarded_transport
    from ai_collage.agent_requests import call_budget

    path = tmp_path / "pass.json"
    payload = {
        "model": DEPLOYMENT, "store": False, "max_output_tokens": 25_000,
        "reasoning": {"effort": "high"}, "input": [],
    }
    dispatched = []

    async def handler(request):
        dispatched.append(json.loads(request.content))
        return httpx.Response(429, json={"error": {"message": "offline"}})

    async def send(project):
        gate = guarded_transport(RequestLog(store, project), "offline", httpx.MockTransport(handler))
        async with httpx.AsyncClient(transport=gate) as client:
            return await client.post(ENDPOINT + "responses", json=payload)

    with call_budget(path, 1):
        assert asyncio.run(send("first")).status_code == 429
    with call_budget(path, 1):
        with pytest.raises(CollageError, match="Outer call budget exhausted"):
            asyncio.run(send("second"))
    assert dispatched == [payload]
    assert read_json(path)["used"] == 1
    assert RequestLog(store, "first").attempts()[0].status == "error"
    assert RequestLog(store, "second").attempts() == []
    with pytest.raises(CollageError, match="limit changed"):
        with call_budget(path, 2):
            pass


def test_outer_cap_does_not_count_oversized_preflight_or_leak_after_exit(store, tmp_path):
    from ai_collage.agent_requests import call_budget

    path = tmp_path / "pass.json"
    with call_budget(path, 1):
        with pytest.raises(CollageError, match="token bound"):
            RequestLog(store, "first").reserve("offline", 50_001)
        assert read_json(path)["used"] == 0
        RequestLog(store, "first").reserve("offline", 100)
    RequestLog(store, "second").reserve("ordinary unguarded use", 100)
    assert read_json(path)["used"] == 1


@pytest.mark.parametrize("old_version", [1, 2])
def test_proposal_response_rejects_old_recipe_versions(old_version):
    data = layout_data()
    data["schema_version"] = old_version
    with pytest.raises(ValidationError, match="Unsupported schema_version"):
        InputLayout.model_validate(data)


def test_fresh_retry_and_old_source_edit_keep_durable_provenance(agent_project):
    conversation, requests = agent_project
    p1, _ = ask(conversation, requests, reply(), prompt="Use a dark background")
    changed = layout_data()
    changed["layers"][1]["box"]["width"] = 0.18
    p2, _ = ask(conversation, requests, reply(changed), prompt="Make photo 2 smaller")
    resumed = Conversation(conversation.store, "demo")
    p3, model = ask(
        resumed, requests, reply(changed), prompt="I hate that, try again",
        action=intent("retry", proposal_id=p2),
    )
    generation = model.contexts[1]
    assert generation["editing_baseline"] == resumed.proposal(p1).recipe.model_dump(mode="json")
    assert generation["reference_to_avoid"] == resumed.proposal(p2).recipe.model_dump(mode="json")
    assert generation["original_task"] == "Make photo 2 smaller"
    p4, model = ask(
        resumed, requests, reply(changed), prompt="Try again, smaller still",
        action=intent("retry", proposal_id=p3),
    )
    assert model.contexts[1]["original_task"] == "Make photo 2 smaller"
    assert resumed.proposal(p4).parent == p1
    assert resumed.proposal(p4).intent.task_turn == resumed.proposal(p2).intent.task_turn
    p5, model = ask(resumed, requests, reply(), action=intent("fresh"), prompt="Start over")
    assert model.contexts[1]["editing_baseline"] is None
    assert model.contexts[1]["baseline_geometry"] is None
    assert model.contexts[1]["reference_to_avoid"] == resumed.proposal(p4).recipe.model_dump(mode="json")
    assert resumed.proposal(p5).parent is None
    p6, model = ask(
        resumed, requests, reply(changed),
        action=intent("edit", source=p1, navigation={"kind": "ordinal", "text": "first"}),
        prompt="Go back to the first and shrink photo 2",
    )
    assert resumed.proposal(p6).parent == p1
    assert model.contexts[1]["editing_baseline"] == resumed.proposal(p1).recipe.model_dump(mode="json")
    assert resumed.store.load("demo").current_version is None


def test_composition_retry_and_exact_selection_are_not_acceptance(agent_project, monkeypatch):
    conversation, requests = agent_project
    p1, _ = ask(conversation, requests, reply(), prompt="Make an airy collage")
    p2, model = ask(
        conversation, requests, reply(), action=intent("retry", proposal_id=p1), prompt="Try again",
    )
    assert model.contexts[1]["editing_baseline"] is None
    assert model.contexts[1]["original_task"] == "Make an airy collage"
    assert model.contexts[1]["reference_to_avoid"] is not None
    before = conversation.preview_path(p1).read_bytes()

    def forbidden(*args):
        raise AssertionError("Selection must not render or accept")

    monkeypatch.setattr("ai_collage.conversation.render_layout", forbidden)
    monkeypatch.setattr(conversation.store, "accept_recipe", forbidden)
    client = FakeModel(intent(
        "select", proposal_id=p1, navigation={"kind": "ordinal", "text": "first"},
    ))
    result = asyncio.run(conversation.request("Go back to the first one", client, requests))
    assert result.kind == "selection" and result.proposal_id == p1
    assert len(client.contexts) == 1
    assert conversation.preview_path(p1).read_bytes() == before
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.baseline == p1
    assert resumed.state.accepted_proposal is None
    assert resumed.proposal(p2).parent is None


@pytest.mark.parametrize("bad_quote", ["P001", "first proposal"])
def test_return_correction_explains_ordinal_evidence_and_selects_exact_png(
    agent_project, monkeypatch, bad_quote,
):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    changed = layout_data()
    changed["canvas"]["background"] = "#202020"
    latest, _ = ask(conversation, requests, reply(changed))
    png = conversation.preview_path(first).read_bytes()

    def forbidden(*args):
        raise AssertionError("Corrected selection must not render or accept")

    monkeypatch.setattr("ai_collage.conversation.render_layout", forbidden)
    monkeypatch.setattr(conversation.store, "accept_recipe", forbidden)
    client = FakeModel(
        intent("select", proposal_id=first, navigation={"kind": "id", "text": bad_quote}),
        intent("select", proposal_id=first, navigation={"kind": "ordinal", "text": "first proposal"}),
    )
    result = asyncio.run(conversation.request("Go back to the first proposal.", client, requests))
    assert result.kind == "selection" and result.proposal_id == first
    assert [context["stage"] for context in client.contexts] == ["interpretation", "interpretation"]
    assert "kind 'ordinal'" in client.contexts[1]["validation_feedback"]
    assert client.contexts[1]["failed_candidate"]
    assert conversation.preview_path(first).read_bytes() == png
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.baseline == first and resumed.state.accepted_proposal is None
    assert resumed.proposal(latest).proposal_id == latest


def test_failed_compound_edit_keeps_current_baseline_and_no_generation_questions(agent_project):
    conversation, requests = agent_project
    p1, _ = ask(conversation, requests, reply())
    p2, _ = ask(conversation, requests, reply())
    client = FakeModel(
        intent("edit", source=p1, navigation={"kind": "ordinal", "text": "first"}),
        intent("question", question="Can I change the canvas?"),
        intent("select", proposal_id=p1),
        json.dumps({"kind": "proposal", "recipe": layout_data()}),
        reply(),
    )
    with pytest.raises(CollageError, match="correction failed"):
        asyncio.run(conversation.request("Go back to first and enlarge photo 2", client, requests))
    assert Conversation(conversation.store, "demo").state.baseline == p2
    assert [context["stage"] for context in client.contexts] == [
        "interpretation", "generation", "generation", "generation",
    ]
    assert all(
        context["resolved_intent"]["source"]["proposal_id"] == p1 for context in client.contexts[1:]
    )
    assert conversation.history()[-1].outcome == "invalid"


def test_invalid_intent_gets_only_two_attempts_and_unknown_id_never_selects(agent_project):
    conversation, requests = agent_project
    p1, _ = ask(conversation, requests, reply())
    client = FakeModel(intent("select", proposal_id="P999"), "{}", intent("fresh"), reply())
    with pytest.raises(CollageError, match="correction failed"):
        asyncio.run(conversation.request("Go back to it", client, requests))
    assert len(client.contexts) == 2 and conversation.state.baseline == p1
    assert all(context["stage"] == "interpretation" for context in client.contexts)


def test_two_interpretations_leave_only_two_generation_calls(agent_project):
    conversation, requests = agent_project
    client = FakeModel("{}", intent("fresh"), "{}", reply(), reply())
    result = asyncio.run(conversation.request("Make a collage", client, requests))
    assert result.kind == "proposal" and len(requests.attempts()) == 4
    assert [context["stage"] for context in client.contexts] == [
        "interpretation", "interpretation", "generation", "generation",
    ]
    assert len(conversation.context("Next request")["history"]) == 1


@pytest.mark.parametrize("question_correction", [False, True])
def test_clarification_task_survives_interpretation_correction_and_restart(
    agent_project, question_correction,
):
    conversation, requests = agent_project
    question = intent("question", question="Which photo?")
    question_model = FakeModel(*(["{}"] if question_correction else []), question)
    asyncio.run(conversation.request("Make one photo stand out", question_model, requests))
    client = FakeModel("{}", intent("fresh"), reply())
    resumed = Conversation(conversation.store, "demo")
    result = asyncio.run(resumed.request("Photo 2", client, requests))
    assert result.proposal_id is not None
    proposal = resumed.proposal(result.proposal_id)
    assert proposal.intent.task_request == "Make one photo stand out"
    assert proposal.intent.task_turn == 1
    assert client.contexts[-1]["user_request"] == "Photo 2"
    assert client.contexts[-1]["history"][0]["prompt"] == "Make one photo stand out"
    reopened = Conversation(conversation.store, "demo")
    assert len(reopened.tasks()) == 1
    assert reopened.tasks()[0].task_id == proposal.intent.task_turn
    retried, _ = ask(
        reopened, requests, reply(), prompt="Try again",
        action=intent("retry", proposal_id=result.proposal_id),
    )
    assert reopened.proposal(retried).intent.task_turn == proposal.intent.task_turn


@pytest.mark.parametrize("action", ["fresh", "edit"])
def test_interpretation_correction_keeps_one_task_origin(agent_project, action):
    conversation, requests = agent_project
    if action == "edit":
        ask(conversation, requests, reply())
    start = conversation._next_event()
    fields = {"source": "current"} if action == "edit" else {}
    model = FakeModel("{}", intent(action, **fields), reply())
    result = asyncio.run(conversation.request("Use an airy arrangement", model, requests))
    resumed = Conversation(conversation.store, "demo")
    proposal = resumed.proposal(result.proposal_id)
    task = resumed.tasks()[-1]
    assert proposal.intent.task_turn == task.task_id == start
    assert task.events == [start, start + 1, start + 2]
    assert task.request == proposal.intent.task_request == "Use an airy arrangement"


@pytest.mark.parametrize("evidence,field,value", [
    ("question", "outcome", "invalid"),
    ("question", "task_id", 2),
    ("intent", "task_id", 2),
    ("intent", "task_request", "An unrelated task"),
])
def test_corrected_task_rejects_invalid_or_unrelated_provenance(
    agent_project, evidence, field, value,
):
    conversation, requests = agent_project
    asyncio.run(conversation.request(
        "Make one photo stand out",
        FakeModel("{}", intent("question", question="Which photo?")), requests,
    ))
    proposal_id, _ = ask(conversation, requests, reply(), prompt="Photo 2")
    number = next(
        number for number, event in zip(conversation.state.history, conversation.history(), strict=True)
        if event.outcome == evidence
    )
    path = conversation.root / "events" / f"{number:06d}.json"
    data = read_json(path)
    target = data["intent"] if field == "task_request" else data
    target[field] = value
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CollageError, match="identity"):
        conversation.proposal(proposal_id)


def test_initial_accepted_layout_is_a_valid_source(agent_project, tmp_path):
    conversation, _ = agent_project
    from .helpers import write_layout

    conversation.store.create("accepted", [
        *conversation.store.photo_paths(conversation.store.load("demo")).values(),
    ])
    conversation.store.apply_layout("accepted", write_layout(tmp_path))
    resumed = Conversation(conversation.store, "accepted", canvas=(100, 100))
    requests = RequestLog(conversation.store, "accepted")
    proposal_id, model = ask(resumed, requests, reply())
    assert model.contexts[-1]["resolved_intent"]["source"]["accepted_version"] == 1
    assert resumed.proposal(proposal_id).intent.source.accepted_version == 1
    assert resumed.store.load("accepted").current_version == 1


def test_fresh_layout_keeps_initial_accepted_recipe_as_reference(agent_project, tmp_path):
    conversation, _ = agent_project
    from .helpers import write_layout

    conversation.store.create(
        "accepted", list(conversation.store.photo_paths(conversation.store.load("demo")).values()),
    )
    conversation.store.apply_layout("accepted", write_layout(tmp_path))
    resumed = Conversation(conversation.store, "accepted", canvas=(100, 100))
    requests = RequestLog(conversation.store, "accepted")
    proposal_id, model = ask(resumed, requests, reply(), action=intent("fresh"))
    assert model.contexts[-1]["editing_baseline"] is None
    assert model.contexts[-1]["reference_to_avoid"] is not None
    assert resumed.proposal(proposal_id).intent.reference.accepted_version == 1


def test_incompatible_source_requires_clarification_without_changing_controls(agent_project):
    conversation, requests = agent_project
    conversation.controls(Controls(width=100, height=100, cropping=True))
    proposal_id, _ = ask(conversation, requests, reply(framed_layout_data()))
    conversation.controls(Controls(width=100, height=100, cropping=False))
    client = FakeModel(
        intent("select", proposal_id=proposal_id),
        intent("question", question="That proposal uses cropping; change the local control first?"),
    )
    result = asyncio.run(conversation.request("Go back to that one", client, requests))
    assert result.kind == "question"
    assert conversation.state.controls.cropping is False
    assert conversation.state.accepted_proposal is None
    assert len(client.contexts) == 2


def test_generation_service_failure_never_reinterprets(agent_project):
    conversation, requests = agent_project
    client = FakeModel(intent("fresh"), CollageError("service stopped"), reply())
    with pytest.raises(CollageError, match="service stopped"):
        asyncio.run(conversation.request("Make a collage", client, requests))
    assert len(client.contexts) == 2
    assert conversation.state.baseline is None
    assert conversation.history()[-1].stage == "generation"
    assert conversation.history()[-1].intent.action == "fresh"

    class PreflightFailure(FakeModel):
        async def complete(self, context, requests, purpose):
            if context["stage"] == "generation":
                raise CollageError("Authentication unavailable before dispatch")
            return await super().complete(context, requests, purpose)

    with pytest.raises(CollageError, match="before dispatch"):
        asyncio.run(conversation.request("Try another composition", PreflightFailure(intent("fresh")), requests))
    assert len(requests.attempts()) == 3
    assert conversation.history()[-1].attempt is None


def test_concurrent_state_change_during_inference_is_not_overwritten(agent_project):
    conversation, requests = agent_project

    class ConcurrentModel(FakeModel):
        async def complete(self, context, requests, purpose):
            raw = await super().complete(context, requests, purpose)
            other = Conversation(conversation.store, "demo")
            other.controls(Controls(width=120, height=100))
            return raw

    with pytest.raises(CollageError, match="Conversation changed"):
        asyncio.run(conversation.request("Make a collage", ConcurrentModel(intent("fresh")), requests))
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.controls.width == 120
    assert len(resumed.history()) == 1 and resumed.state.baseline is None


@pytest.mark.parametrize("old_version", [1, 2, 3, 4, 5, 6])
def test_old_conversation_rejected_without_writing(agent_project, old_version):
    conversation, requests = agent_project
    state = read_json(conversation.state_path)
    state["record_version"] = old_version
    conversation.state_path.write_text(json.dumps(state), encoding="utf-8")
    before = conversation.state_path.read_bytes()
    with pytest.raises(ValidationError, match="record_version"):
        Conversation(conversation.store, "demo")
    assert conversation.state_path.read_bytes() == before and not requests.attempts()


def test_intent_prompt_identity_reloads_and_stage_schema_is_strict(tmp_path, monkeypatch):
    from ai_collage import agent_provider

    package = tmp_path / "package"
    prompt = package / "prompts" / "request-intent.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text("Interpret first", encoding="utf-8")
    monkeypatch.setattr(agent_provider, "__file__", str(package / "agent_provider.py"))
    assert agent_provider.instructions("interpretation") == "Interpret first"
    prompt.write_text("Updated intent", encoding="utf-8")
    assert agent_provider.instructions("interpretation") == "Updated intent"
    schema = agent_provider.response_format("interpretation")["json_schema"]["schema"]
    assert schema["type"] == "object" and schema["additionalProperties"] is False
    assert set(schema["properties"]) == {
        "action", "source", "proposal_id", "question", "references", "name_updates", "decision", "receipt_event",
        "navigation", "continuation", "continues_task", "return_confirmation",
    }
    for data in (
        {"action": "fresh", "source": "current"},
        {"action": "select", "proposal_id": "P001", "recipe": {}},
        {"action": "edit"},
    ):
        with pytest.raises(ValidationError):
            INTENT.validate_python({"references": [], "name_updates": [], **data})


def photo_reference(text, photo_id, **fields):
    return {"text": text, "photo_id": photo_id, **fields}


def photo_name(name, photo_id, quote, **fields):
    return {"name": name, "photo_id": photo_id, "quote": quote, **fields}


@pytest.mark.parametrize("name,photo_id,answer", [
    ("harbour", 1, "1"), ("forest", 2, "Photo 2"),
])
@pytest.mark.parametrize("question_correction", [False, True])
def test_unknown_label_answer_resumes_original_edit_after_restart(
    agent_project, name, photo_id, answer, question_correction,
):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    prompt = f"Make {name} smaller. Leave the other photo alone."
    question = FakeModel(*(["{}"] if question_correction else []), intent(
        "question", question=f"Which photo is {name}?",
        references=[photo_reference(name, None)],
    ))
    asyncio.run(conversation.request(prompt, question, requests))
    changed = layout_data()
    changed["layers"][photo_id - 1]["box"]["width"] -= 0.01
    model = FakeModel(intent(
        "edit", source="current",
        references=[photo_reference(f"photo {photo_id}", photo_id)],
    ), reply(changed))
    resumed = Conversation(conversation.store, "demo")
    result = asyncio.run(resumed.request(answer, model, requests))
    proposal = resumed.proposal(result.proposal_id)
    assert proposal.parent == first and proposal.intent.task_request == prompt
    assert model.contexts[-1]["original_task"] == prompt
    assert model.contexts[-1]["resolved_intent"]["references"][0]["photo_id"] == photo_id
    assert not resumed.state.photo_names and resumed.state.pending_names is None
    assert resumed.store.load("demo").current_version is None




def test_interpretation_transport_schema_constrains_reference_and_navigation_metadata():
    from ai_collage.agent_provider import response_format

    definitions = response_format("interpretation")["json_schema"]["schema"]["$defs"]
    assert set(definitions["PhotoReference"]["properties"]) == {"text", "photo_id", "event_id"}
    navigation = {
        branch["properties"]["kind"]["const"]: branch
        for branch in definitions["NavigationEvidence"]["anyOf"]
    }
    for kind in ("id", "ordinal"):
        for field in ("task_id", "field", "steps"):
            assert navigation[kind]["properties"][field] == {"type": "null"}
    for kind in ("before", "after"):
        assert {"task_id", "field"} <= set(navigation[kind]["required"])
    assert "steps" in navigation["undo"]["required"]


@pytest.mark.parametrize("wording,ids", [
    ("Swap the positions of photos 1 and 4.", [1, 4]),
    ("Arrange photos 1, 3 and 4 on the left.", [1, 3, 4]),
    ("Arrange images 1,3,4 together.", [1, 3, 4]),
    ("Swap pictures 1 & 4.", [1, 4]),
    ("Swap photos 01 and 04.", [1, 4]),
])
def test_normalized_numbered_references_ground_in_explicit_lists(wording, ids):
    from ai_collage.photo_references import ground_references

    action = INTENT.validate_json(intent("fresh", references=[
        photo_reference(f"photo {number}", number) for number in ids
    ]))
    assert ground_references(
        action, wording, task_request=wording, photos={1, 2, 3, 4}, names=[],
        reference_history={},
    ) == []


@pytest.mark.parametrize("wording,reference,photos", [
    ("Move photo 1 right by 4 pixels.", photo_reference("photo 4", 4), {1, 2, 3, 4}),
    ("Move photo 1 and use 4px borders.", photo_reference("photo 4", 4), {1, 2, 3, 4}),
    ("Use photos 1 and 4.5 as a size.", photo_reference("photo 4", 4), {1, 2, 3, 4}),
    ("Use photos 1 and 40.", photo_reference("photo 4", 4), {1, 2, 3, 4}),
    ("Swap photos 1 and 4.", photo_reference("photo 4", 4), {1, 2}),
])
def test_numbered_list_grounding_does_not_invent_identity_or_relax_other_evidence(
    wording, reference, photos,
):
    from ai_collage.photo_references import ground_references

    action = INTENT.validate_json(intent("fresh", references=[reference]))
    with pytest.raises(CollageError):
        ground_references(
            action, wording, task_request=wording, photos=photos, names=[],
            reference_history={},
        )


def test_numbered_list_swap_reaches_generation_after_restart(agent_project):
    conversation, requests = agent_project
    initial = layout_data()
    for layer in initial["layers"]:
        layer["box"]["center_y"] = 0.4
    first, _ = ask(conversation, requests, reply(initial))
    changed = copy.deepcopy(initial)
    changed["layers"][0]["box"], changed["layers"][1]["box"] = (
        changed["layers"][1]["box"], changed["layers"][0]["box"],
    )
    client = FakeModel(
        intent("edit", source="current", references=[
            photo_reference("photo 1", 1), photo_reference("photo 2", 2),
        ]),
        reply(changed),
    )
    result = asyncio.run(Conversation(conversation.store, "demo").request(
        "Swap the positions of photos 1 and 2. Keep their sizes and styling unchanged.",
        client, requests,
    ))
    assert result.kind == "proposal" and len(client.contexts) == 2
    assert client.contexts[1]["resolved_intent"]["source"]["proposal_id"] == first
    assert {item["photo_id"] for item in client.contexts[1]["resolved_intent"]["references"]} == {1, 2}


@pytest.mark.parametrize("invented", [
    photo_reference("photo 1", 1),
    photo_reference("photo 2", 1),
])
def test_invalid_individual_bindings_are_corrected_without_losing_comparison_task(
    agent_project, invented,
):
    conversation, requests = agent_project
    prompt = "Make a collage with a dark grey background. Make photo 2 smaller than the others."
    target = photo_reference("photo 2", 2)
    client = FakeModel(
        intent("fresh", references=[target, invented]),
        intent("fresh", references=[target]),
        reply(),
    )
    result = asyncio.run(conversation.request(prompt, client, requests))
    assert result.kind == "proposal" and len(client.contexts) == 3
    assert client.contexts[1]["validation_feedback"]
    generation = client.contexts[2]
    assert generation["original_task"] == generation["user_request"] == prompt
    assert generation["resolved_intent"]["references"] == [
        {**target, "event_id": None},
    ]
    assert [event.outcome for event in conversation.history()] == ["invalid", "intent", "proposal"]


def remember(conversation, requests, name="breakfast", photo_id=2):
    prompt = f"Photo {photo_id} is {name}"
    client = FakeModel(intent(
        "remember", name_updates=[photo_name(name, photo_id, prompt)],
    ))
    result = asyncio.run(conversation.request(prompt, client, requests))
    if result.kind == "name_confirmation":
        result = asyncio.run(conversation.request(
            "Yes, remember those", FakeModel(intent("names", decision="approve", receipt_event=result.event_id)),
            requests,
        ))
    return result


def test_names_survive_compaction_restart_selection_and_ground_generation(agent_project):
    conversation, requests = agent_project
    result = remember(conversation, requests)
    assert result.kind == "acknowledgement" and "breakfast = photo 2" in result.acknowledgement
    assert conversation.state.baseline is None and not (conversation.root / "proposals").exists()
    remember(conversation, requests, "croissant")
    p1, _ = ask(conversation, requests, reply())
    for _ in range(4):
        ask(conversation, requests, reply(), prompt="Keep the dark background")
    conversation = Conversation(conversation.store, "demo")
    refs = [photo_reference("BREAKFAST", 2)]
    _, model = ask(
        conversation, requests, reply(), prompt="Move BREAKFAST a bit right",
        action=intent("edit", source="current", references=refs),
    )
    assert model.contexts[0]["history_omitted"] > 0
    assert {item["name"] for item in model.contexts[0]["photo_names"]} == {"breakfast", "croissant"}
    assert model.contexts[1]["resolved_intent"]["references"][0]["photo_id"] == 2
    selected = FakeModel(intent("select", proposal_id=p1))
    asyncio.run(conversation.request(f"Return to {p1}", selected, requests))
    assert len(Conversation(conversation.store, "demo").state.photo_names) == 2
    assert conversation.store.load("demo").current_version is None


def test_grounding_clarifies_whole_task_without_learning_numeric_answer(agent_project):
    conversation, requests = agent_project
    prompt = "Move photo 1 right and breakfast higher"
    first = FakeModel(intent(
        "question", question="Which photo number is breakfast?",
        references=[photo_reference("photo 1", 1), photo_reference("breakfast", None)],
    ))
    question = asyncio.run(conversation.request(prompt, first, requests))
    assert question.kind == "question" and conversation.state.baseline is None
    client = FakeModel(intent(
        "fresh",
        references=[photo_reference("photo 1", 1), photo_reference("breakfast", 2)],
    ), reply())
    result = asyncio.run(Conversation(conversation.store, "demo").request("2", client, requests))
    assert result.kind == "proposal" and client.contexts[1]["original_task"] == prompt
    assert not client.contexts[1]["photo_names"] and conversation.state.pending_names is None
    assert {item["photo_id"] for item in client.contexts[1]["resolved_intent"]["references"]} == {1, 2}


def test_multiple_name_questions_retain_the_original_complete_task(agent_project):
    conversation, requests = agent_project
    prompt = "Move breakfast closer to bookshop"
    client = FakeModel(intent(
        "question", question="Which photo is breakfast?",
        references=[photo_reference("breakfast", None),
                    photo_reference("bookshop", None)],
    ))
    asyncio.run(conversation.request(prompt, client, requests))
    client = FakeModel(intent(
        "question", question="Which photo is bookshop?",
        references=[photo_reference("breakfast", 2),
                    photo_reference("bookshop", None)],
    ))
    asyncio.run(conversation.request("2", client, requests))
    conversation = Conversation(conversation.store, "demo")
    client = FakeModel(intent(
        "fresh", references=[photo_reference("breakfast", 2), photo_reference("bookshop", 1)],
    ), reply())
    asyncio.run(conversation.request("1", client, requests))
    assert client.contexts[0]["pending_question"]["original_task"] == prompt
    assert client.contexts[1]["original_task"] == prompt
    assert not conversation.state.photo_names


def test_longer_learned_name_is_not_confused_with_a_shorter_name(agent_project):
    conversation, requests = agent_project
    remember(conversation, requests, "breakfast", 1)
    remember(conversation, requests, "full breakfast", 2)
    _, client = ask(
        conversation, requests, reply(), prompt="Move the full breakfast photo a bit right",
        action=intent("fresh", references=[photo_reference("full breakfast", 2)]),
    )
    assert client.contexts[1]["resolved_intent"]["references"][0]["photo_id"] == 2


def test_only_unknown_name_is_clarified_and_pronoun_has_visible_evidence(agent_project):
    conversation, requests = agent_project
    remember(conversation, requests)
    ask(conversation, requests, reply())
    refs = [photo_reference("breakfast", 2), photo_reference("bookshop", None)]
    client = FakeModel(intent("question", question="Which photo number is bookshop?", references=refs))
    asyncio.run(conversation.request("Move breakfast closer to bookshop", client, requests))
    assert conversation.state.baseline == "P001"
    client = FakeModel(intent(
        "edit", source="current",
        references=[photo_reference("breakfast", 2), photo_reference("bookshop", 1)],
    ), reply())
    asyncio.run(conversation.request("1", client, requests))
    _, model = ask(
        conversation, requests, reply(), prompt="Move breakfast a bit right",
        action=intent("edit", source="current", references=[photo_reference("breakfast", 2)]),
    )
    event_id = conversation.state.history[-1]
    client = FakeModel(intent(
        "edit", source="current",
        references=[photo_reference("it", 2, event_id=event_id)],
    ), reply())
    result = asyncio.run(conversation.request("Make it bigger", client, requests))
    assert result.kind == "proposal" and len(client.contexts) == 2
    assert client.contexts[1]["resolved_intent"]["references"][0]["photo_id"] == 2












def test_binding_evidence_and_state_tampering_are_rejected_on_restart(agent_project):
    conversation, requests = agent_project
    remember(conversation, requests, "  Full   Breakfast  ")
    assert conversation.state.photo_names[0].name == "Full Breakfast"
    state = read_json(conversation.state_path)
    state["photo_names"][0]["photo_id"] = 1
    conversation.state_path.write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(CollageError, match="Photo-name state"):
        Conversation(conversation.store, "demo")


def test_chat_acknowledgement_does_not_open_a_preview(agent_project, monkeypatch, capsys):
    from ai_collage.chat import run_chat

    conversation, _ = agent_project
    prompt = "Photo 2 is breakfast"
    client = FakeModel(
        intent("remember", name_updates=[photo_name("breakfast", 2, prompt)]),
        intent("names", decision="approve", receipt_event=1),
    )
    inputs = iter([prompt, "Yes, remember those", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr("ai_collage.agent_provider.FoundryModel", lambda: client)
    monkeypatch.setattr("ai_collage.chat.open_preview", lambda _: pytest.fail("No naming preview"))
    assert run_chat(
        conversation.store, "demo", canvas=None, preferences=None, live=True, no_open=False,
    ) == 0
    output = capsys.readouterr().out
    assert "Remembered: breakfast = photo 2." in output
    assert "Remember these names: breakfast = photo 2" in output
    assert "Generated P" not in output and len(client.contexts) == 2
    assert not (conversation.root / "proposals").exists()


















def test_corrected_multi_photo_answer_survives_rejected_answer_and_restart(agent_project):
    conversation, requests = agent_project
    baseline, _ = ask(conversation, requests, reply())
    task = "Put bridge above bookshop"
    question = intent("question", question="Which numbers are bridge and bookshop?",
                      references=[photo_reference("bridge", None), photo_reference("bookshop", None)])
    asyncio.run(conversation.request(task, FakeModel(question), requests))
    with pytest.raises(CollageError, match="correction failed"):
        asyncio.run(conversation.request("both 4", FakeModel("{}", "{}"), requests))
    conversation = Conversation(conversation.store, "demo")
    answer = "Photo 1 and photo 2, respectively."
    client = FakeModel(
        intent("remember"),
        intent("edit", source="current", references=[
            photo_reference("bridge", 1), photo_reference("bookshop", 2),
        ]),
        reply(),
    )
    result = asyncio.run(conversation.request(answer, client, requests))
    assert result.kind == "proposal"
    assert client.contexts[2]["original_task"] == task
    assert client.contexts[2]["resolved_intent"]["source"]["proposal_id"] == baseline
    assert len({event.task_id for event in conversation.history()[2:]}) == 1
    assert Conversation(conversation.store, "demo").state.baseline == result.proposal_id
    assert not conversation.state.photo_names


def test_resize_corrections_retain_prior_repairs_and_leave_unrelated_authored_values(agent_project):
    conversation, requests = agent_project
    baseline = layout_data()
    baseline["canvas"]["background"] = "#112233"
    baseline["layers"][0]["corner_radius_px"] = 1
    ask(conversation, requests, reply(baseline))
    enlarged = copy.deepcopy(baseline)
    for layer in enlarged["layers"]:
        layer["box"]["width"] *= 2
    repaired_one = copy.deepcopy(enlarged)
    repaired_one["layers"][0]["box"]["center_x"] = 0.2
    repaired_both = copy.deepcopy(repaired_one)
    repaired_both["layers"][1]["box"]["center_y"] = 0.4
    _, client = ask(conversation, requests, reply(enlarged), reply(repaired_one), reply(repaired_both),
                    prompt="Enlarge all photos by 100%")
    correction = client.contexts[-1]
    assert json.loads(correction["failed_candidate"]) == repaired_one
    assert json.loads(correction["validation_feedback"])["photo_id"] == 2
    assert json.loads(correction["prior_validation_feedback"][0])["photo_id"] == 1
    assert correction["editing_baseline"] == InputLayout.model_validate(baseline).model_dump(mode="json")
    assert conversation.baseline() == InputLayout.model_validate(repaired_both)
    fields = {change.field for change in conversation.tasks()[-1].changes}
    assert fields == {"recipe.photos.1.box.width", "recipe.photos.2.box.width",
                      "recipe.photos.1.box.center_x", "recipe.photos.2.box.center_y"}


@pytest.mark.parametrize("fixed", [False, True])
def test_unsuccessful_or_impossible_enlargement_preserves_previous_proposal(agent_project, fixed):
    from ai_collage.conversation import RequestRejected
    from ai_collage.chat import rejection_message
    conversation, requests = agent_project
    baseline, _ = ask(conversation, requests, reply())
    candidate = layout_data()
    candidate["layers"][1]["box"]["width"] = 0.4 if fixed else 0.6
    prompt = "Enlarge photo 2 by 100% without moving it" if fixed else "Enlarge photo 2 by 200%"
    client = FakeModel(intent("edit", source="current", references=[photo_reference("photo 2", 2)]),
                       *([reply(candidate)] * 3))
    with pytest.raises(RequestRejected) as rejected:
        asyncio.run(conversation.request(prompt, client, requests))
    assert rejected.value.source.proposal_id == baseline and not rejected.value.identity
    assert conversation.state.baseline == baseline
    assert conversation.baseline() == InputLayout.model_validate(layout_data())
    feedback = json.loads(client.contexts[-1]["validation_feedback"])
    assert (feedback["safe_box_center_normalized"] is not None) == fixed
    message = rejection_message(rejected.value, conversation)
    assert "still at P001" in message and "rephrase" in message
    assert "Names I know" not in message and "photo numbers" not in message
    assert "cannot fit" not in message


@pytest.mark.parametrize("known", [False, True])
def test_chat_identity_rejections_show_validated_names_or_numbers_and_preserve_diagnostics(
    agent_project, monkeypatch, capsys, known,
):
    from ai_collage.chat import run_chat
    conversation, requests = agent_project
    if known:
        remember(conversation, requests, "london bridge", 1)
    bad = intent("fresh", references=[photo_reference("invented name", 99)])
    client = FakeModel(bad, bad)
    lines = iter(["Move invented name", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(lines))
    monkeypatch.setattr("ai_collage.agent_provider.FoundryModel", lambda: client)
    run_chat(conversation.store, "demo", canvas=None, preferences=None, live=True, no_open=True)
    output = capsys.readouterr()
    assert "No proposal exists yet." in output.err and "rephrase" in output.err
    assert ("Names I know: 1 = london bridge." if known else "refer to photos by number") in output.err
    assert "matching user-established" not in output.err and "try again" not in output.err
    events = Conversation(conversation.store, "demo").history()
    assert events[-1].response == bad and "unknown photo number" in events[-1].error


def test_chat_generic_recovery_reports_real_baseline_and_accepts_a_different_next_request(
    agent_project, monkeypatch, capsys,
):
    from ai_collage.chat import run_chat
    conversation, requests = agent_project
    remember(conversation, requests)
    ask(conversation, requests, reply())
    bad = '{"unexpected":"diagnostic-without-a-special-workaround"}'
    client = FakeModel(bad, bad, intent("edit", source="current"), reply())
    lines = iter(["Use a darker background", "Use a different background", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(lines))
    monkeypatch.setattr("ai_collage.agent_provider.FoundryModel", lambda: client)
    run_chat(conversation.store, "demo", canvas=None, preferences=None, live=True, no_open=True)
    output = capsys.readouterr()
    assert "Your collage is still at P001." in output.err and "rephrase" in output.err
    assert "Names I know" not in output.err and "photo numbers" not in output.err
    assert "diagnostic-without" not in output.err and "Generated P002" in output.out
    assert any(event.response == bad and event.error for event in Conversation(conversation.store, "demo").history())


def test_chat_identity_question_reminder_excludes_unconfirmed_candidates(agent_project, monkeypatch, capsys):
    from ai_collage.chat import run_chat
    conversation, requests = agent_project
    remember(conversation, requests, "london bridge", 1)
    client = FakeModel(intent(
        "question", question="Do you mean photo 1 (london bridge) by river crossing?",
        references=[photo_reference("river crossing", None)],
    ))
    lines = iter(["Move river crossing", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(lines))
    monkeypatch.setattr("ai_collage.agent_provider.FoundryModel", lambda: client)
    run_chat(conversation.store, "demo", canvas=None, preferences=None, live=True, no_open=True)
    output = capsys.readouterr()
    assert "Names I know: 1 = london bridge.\n" in output.out
    assert not output.err
    assert len(Conversation(conversation.store, "demo").state.photo_names) == 1


def test_chat_publication_io_failure_is_not_called_recoverable(agent_project, monkeypatch, capsys):
    from ai_collage.chat import run_chat
    conversation, _ = agent_project
    client = FakeModel(intent("fresh"), reply())
    lines = iter(["Make a collage", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(lines))
    monkeypatch.setattr("ai_collage.agent_provider.FoundryModel", lambda: client)

    def fail_publication(*args, **kwargs):
        raise OSError("Uncertain disk write")

    monkeypatch.setattr(Conversation, "_publish", fail_publication)
    run_chat(conversation.store, "demo", canvas=None, preferences=None, live=True, no_open=True)
    output = capsys.readouterr()
    assert "Error: Uncertain disk write" in output.err
    assert "still at" not in output.err and "rephrase" not in output.err
    assert "Proposal publication stopped: OSError." == Conversation(conversation.store, "demo").history()[-1].error


def name_decision(conversation, requests, receipt, *responses, decision="approve"):
    client = FakeModel(
        intent("names", decision=decision, receipt_event=receipt.event_id), *responses,
    )
    result = asyncio.run(conversation.request(
        "Yes, remember those" if decision == "approve" else "No, that's not right",
        client, requests,
    ))
    return result, client


@pytest.mark.parametrize("label,wording,photo_id", [
    ("tower bridge", "bridge", 1),
    ("bookshop", "book shop", 2),
    ("bookshop", "bookstore", 2),
])
def test_model_led_wording_reaches_generation_without_writing_an_alias(
    agent_project, label, wording, photo_id,
):
    conversation, requests = agent_project
    remember(conversation, requests, label, photo_id)
    names = conversation.state.photo_names
    result, client = ask(
        Conversation(conversation.store, "demo"), requests, reply(),
        prompt=f"Move {wording} higher",
        action=intent("fresh", references=[photo_reference(wording, photo_id)]),
    )
    resumed = Conversation(conversation.store, "demo")
    assert result == "P001" and len(client.contexts) == 2
    assert client.contexts[1]["resolved_intent"]["references"][0]["text"] == wording
    assert resumed.state.photo_names == names and resumed.state.pending_names is None
    assert not any(event.name_updates for event in resumed.history()[-2:])


def test_additions_replacements_and_unchanged_names_preserve_other_labels_and_acceptance(agent_project):
    conversation, requests = agent_project
    baseline, _ = ask(conversation, requests, reply())
    conversation.accept(baseline)
    png = conversation.preview_path(baseline).read_bytes()
    remember(conversation, requests, "bookshop", 2)
    remember(conversation, requests, "Daunt Books", 2)
    prompt = "Actually bookshop is photo 1"
    gate = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "remember", name_updates=[photo_name("bookshop", 1, prompt)],
    )), requests))
    assert gate.kind == "name_confirmation"
    assert "bookshop = photo 1 (was photo 2)" in gate.question
    assert {item.name: item.photo_id for item in conversation.state.photo_names} == {
        "bookshop": 2, "Daunt Books": 2,
    }
    result, _ = name_decision(conversation, requests, gate)
    assert result.kind == "acknowledgement"
    assert {item.name: item.photo_id for item in conversation.state.photo_names} == {
        "bookshop": 1, "Daunt Books": 2,
    }
    names = conversation.state.photo_names
    before = len(requests.attempts())
    repeated = remember(conversation, requests, "bookshop", 1)
    assert repeated.kind == "acknowledgement" and len(requests.attempts()) == before + 1
    assert conversation.state.photo_names == names
    assert conversation.state.baseline == baseline and conversation.store.load("demo").current_version == 1
    assert conversation.preview_path(baseline).read_bytes() == png


def test_swapped_candidate_batch_is_displayed_but_never_saved_or_edited_without_approval(agent_project):
    conversation, requests = agent_project
    prompt = "Photo 1 is bridge; photo 2 is bookshop. Move bridge higher."
    client = FakeModel(intent(
        "fresh", references=[photo_reference("bridge", 2), photo_reference("bookshop", 1)],
        name_updates=[photo_name("bridge", 2, prompt), photo_name("bookshop", 1, prompt)],
    ))
    gate = asyncio.run(conversation.request(prompt, client, requests))
    assert gate.kind == "name_confirmation" and len(client.contexts) == 1
    assert "bridge = photo 2; bookshop = photo 1" in gate.question
    assert not conversation.state.photo_names and conversation.state.baseline is None
    assert not (conversation.root / "proposals").exists()
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.pending_names == conversation.state.pending_names
    declined, model = name_decision(resumed, requests, gate, decision="reject")
    assert declined.kind == "acknowledgement" and "not applied" in declined.acknowledgement
    assert len(model.contexts) == 1 and not resumed.state.photo_names
    assert resumed.state.pending_names is None and resumed.state.baseline is None


def test_combined_approval_after_restart_keeps_original_task_and_older_source(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    second_data = layout_data()
    second_data["canvas"]["background"] = "#112233"
    second, _ = ask(conversation, requests, reply(second_data))
    prompt = f"Photo 2 is bookshop. Go back to {first} and move bookshop higher."
    gate_client = FakeModel(intent(
        "edit", source=first, navigation={"kind": "id", "text": first},
        references=[photo_reference("bookshop", 2)],
        name_updates=[photo_name("bookshop", 2, "Photo 2 is bookshop")],
    ))
    gate = asyncio.run(conversation.request(prompt, gate_client, requests))
    assert len(gate_client.contexts) == 1 and conversation.state.baseline == second
    assert not conversation.state.photo_names
    changed = layout_data()
    changed["layers"][1]["box"]["center_y"] -= 0.02
    resumed = Conversation(conversation.store, "demo")
    result, client = name_decision(resumed, requests, gate, reply(changed))
    proposal = resumed.proposal(result.proposal_id)
    assert proposal.parent == first and proposal.intent.task_request == prompt
    assert client.contexts[1]["original_task"] == prompt
    assert client.contexts[1]["editing_baseline"] == resumed.proposal(first).recipe.model_dump(mode="json")
    assert resumed.tasks()[-1].changes[0].field == "recipe.photos.2.box.center_y"
    assert len(resumed.tasks()[-1].changes) == 1
    assert resumed.state.photo_names[0].receipt_event == gate.event_id
    assert resumed.state.pending_names is None and resumed.store.load("demo").current_version is None


def test_revised_batch_needs_new_approval_and_rejects_the_stale_receipt(agent_project):
    conversation, requests = agent_project
    prompt = "Map bridge to photo 1"
    first = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "remember", name_updates=[photo_name("bridge", 1, prompt)],
    )), requests))
    revision = "Actually bridge is photo 2"
    revised = asyncio.run(conversation.request(revision, FakeModel(intent(
        "remember", name_updates=[photo_name("bridge", 2, revision)],
    )), requests))
    assert revised.event_id != first.event_id and "bridge = photo 2" in revised.question
    stale = intent("names", decision="approve", receipt_event=first.event_id)
    with pytest.raises(CollageError, match="correction failed"):
        asyncio.run(conversation.request("Yes", FakeModel(stale, stale), requests))
    assert not conversation.state.photo_names
    assert conversation.state.pending_names.event_id == revised.event_id
    resumed = Conversation(conversation.store, "demo")
    name_decision(resumed, requests, revised)
    assert resumed.state.photo_names[0].photo_id == 2
    assert resumed.state.photo_names[0].receipt_event == revised.event_id


@pytest.mark.parametrize("bad_kind", ["wrong-receipt", "substitution", "ready-edit"])
def test_unapproved_or_substituted_batch_cannot_write_names_or_generate(agent_project, bad_kind):
    conversation, requests = agent_project
    prompt = "Photo 2 is bookshop; move bookshop higher"
    gate = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "fresh", references=[photo_reference("bookshop", 2)],
        name_updates=[photo_name("bookshop", 2, "Photo 2 is bookshop")],
    )), requests))
    fields = {"decision": "approve", "receipt_event": gate.event_id}
    if bad_kind == "wrong-receipt":
        fields["receipt_event"] += 1
    elif bad_kind == "substitution":
        fields["name_updates"] = [photo_name("bookshop", 1, prompt)]
    bad = intent("fresh") if bad_kind == "ready-edit" else intent("names", **fields)
    client = FakeModel(bad, bad)
    with pytest.raises(CollageError, match="correction failed"):
        asyncio.run(conversation.request("Yes", client, requests))
    assert all(item["stage"] == "interpretation" for item in client.contexts)
    assert not conversation.state.photo_names and conversation.state.baseline is None
    assert conversation.state.pending_names.event_id == gate.event_id
    assert not (conversation.root / "proposals").exists()


@pytest.mark.parametrize("with_edit", [False, True])
def test_unclear_reply_and_interpretation_failure_retain_the_same_pending_receipt(agent_project, with_edit):
    conversation, requests = agent_project
    prompt = "Map castle to photo 2" + (" and move castle higher" if with_edit else "")
    gate = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "fresh" if with_edit else "remember",
        references=[photo_reference("castle", 2)] if with_edit else [],
        name_updates=[photo_name("castle", 2, prompt)],
    )), requests))
    question = asyncio.run(conversation.request("Maybe", FakeModel(intent(
        "question", question="Should I remember castle as photo 2?",
        continuation="design" if with_edit else "naming",
    )), requests))
    assert question.kind == "question" and conversation.state.pending_names.event_id == gate.event_id
    with pytest.raises(CollageError, match="offline interpretation failure"):
        asyncio.run(conversation.request("Yes", FakeModel(CollageError("offline interpretation failure")), requests))
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.pending_names.event_id == gate.event_id and not resumed.state.photo_names
    result, _ = name_decision(resumed, requests, gate, *([reply()] if with_edit else []))
    assert result.kind == ("proposal" if with_edit else "acknowledgement")
    reopened = Conversation(conversation.store, "demo")
    assert reopened.state.photo_names[0].name == "castle"
    assert len(reopened.tasks()) == 1 and reopened.state.pending_names is None


def test_approved_teaching_and_return_selects_the_exact_saved_preview_without_generation(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    first_png = conversation.preview_path(first).read_bytes()
    second, _ = ask(conversation, requests, reply())
    prompt = f"Photo 2 is castle; return to {first}"
    gate = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "select", proposal_id=first, navigation={"kind": "id", "text": first},
        name_updates=[photo_name("castle", 2, "Photo 2 is castle")],
    )), requests))
    assert conversation.state.baseline == second and not conversation.state.photo_names
    result, client = name_decision(conversation, requests, gate)
    assert result.kind == "selection" and result.proposal_id == first
    assert len(client.contexts) == 1 and client.contexts[0]["stage"] == "interpretation"
    reopened = Conversation(conversation.store, "demo")
    assert reopened.state.baseline == first and reopened.state.photo_names[0].name == "castle"
    assert reopened.preview_path(first).read_bytes() == first_png
    assert len(list((reopened.root / "proposals").iterdir())) == 2
    assert reopened.store.load("demo").current_version is None


def test_teaching_with_retry_retains_the_rejected_proposals_original_task_and_source(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    original_task = "Move photo 2 higher"
    second, _ = ask(conversation, requests, reply(), prompt=original_task)
    prompt = f"Photo 2 is castle; I dislike {second}, try again"
    gate = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "retry", proposal_id=second, name_updates=[photo_name("castle", 2, "Photo 2 is castle")],
    )), requests))
    result, client = name_decision(conversation, requests, gate, reply())
    reopened = Conversation(conversation.store, "demo")
    proposal = reopened.proposal(result.proposal_id)
    assert proposal.intent.task_request == original_task and proposal.parent == first
    assert proposal.intent.reference.proposal_id == second
    assert client.contexts[1]["original_task"] == original_task
    assert reopened.state.photo_names[0].name == "castle" and reopened.state.pending_names is None


@pytest.mark.parametrize("already_used", [False, True])
def test_approval_without_a_pending_receipt_or_reusing_an_approved_one_is_rejected(agent_project, already_used):
    conversation, requests = agent_project
    if already_used:
        remember(conversation, requests)
    names = conversation.state.photo_names
    bad = intent("names", decision="approve", receipt_event=1)
    with pytest.raises(CollageError, match="correction failed"):
        asyncio.run(conversation.request("Yes", FakeModel(bad, bad), requests))
    assert conversation.state.photo_names == names and conversation.state.pending_names is None
    assert conversation.state.baseline is None


@pytest.mark.parametrize("question_first", [False, True])
def test_independent_replacement_cannot_inherit_a_pending_name_approval(agent_project, question_first):
    conversation, requests = agent_project
    prompt = "Map castle to photo 2 and move castle higher"
    gate = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "fresh", references=[photo_reference("castle", 2)],
        name_updates=[photo_name("castle", 2, "Map castle to photo 2")],
    )), requests))
    if question_first:
        asyncio.run(conversation.request("Move forest instead", FakeModel(intent(
            "question", question="Which photo is forest?", continues_task=False,
            references=[photo_reference("forest", None)],
        )), requests))
        assert conversation.state.pending_names is None
        result = asyncio.run(conversation.request("Photo 1", FakeModel(intent(
            "fresh", references=[photo_reference("forest", 1)],
        ), reply()), requests))
    else:
        result = asyncio.run(conversation.request("Use photo 1 instead", FakeModel(intent(
            "fresh", references=[photo_reference("photo 1", 1)], continues_task=False,
        ), reply()), requests))
    assert result.kind == "proposal" and not conversation.state.photo_names
    assert conversation.state.pending_names is None
    stale = intent("names", decision="approve", receipt_event=gate.event_id)
    with pytest.raises(CollageError, match="correction failed"):
        asyncio.run(Conversation(conversation.store, "demo").request("Yes", FakeModel(stale, stale), requests))


@pytest.mark.parametrize("fields,prompt", [
    ({"references": [photo_reference("photo 99", 99)]}, "Move photo 99"),
    ({"references": [photo_reference("photo 1", 2)]}, "Move photo 1"),
    ({"references": [photo_reference("bookshop", 1)]}, "Move bookshop"),
    ({"references": [photo_reference("bookshop (photo 1)", 2)]}, "Move bookshop (photo 1)"),
    ({"references": [photo_reference("the bookshop photo", 1)]}, "Move the bookshop photo"),
    ({"references": [photo_reference("bookshop", 2, event_id=999)]}, "Move bookshop"),
    ({"references": [photo_reference("forest", 2)]}, "Move photo 1"),
    ({"name_updates": [photo_name("forest", 2, "invented user quote")]}, "Move forest"),
    ({"name_updates": [photo_name("forest", 2, "photo 1")]}, "Move photo 1"),
    ({"name_updates": [photo_name("forest", 99, "Photo 99 is forest")]}, "Photo 99 is forest"),
    ({"name_updates": [photo_name("photo 1", 2, "Call photo 2 photo 1")]}, "Call photo 2 photo 1"),
    ({"name_updates": [photo_name("bookshop", 1, "Photo 2 is bookshop")]}, "Move photo 1"),
    ({"name_updates": [
        photo_name("forest", 1, "Photo 1 is forest"),
        photo_name("FOREST", 2, "Photo 1 is forest"),
    ]}, "Photo 1 is forest"),
])
def test_structural_binding_conflicts_fail_before_generation(agent_project, fields, prompt):
    conversation, requests = agent_project
    remember(conversation, requests, "bookshop", 2)
    bad = intent("fresh", **fields)
    client = FakeModel(bad, bad)
    with pytest.raises(CollageError, match="correction failed"):
        asyncio.run(conversation.request(prompt, client, requests))
    assert len(client.contexts) == 2 and conversation.state.baseline is None
    assert conversation.state.photo_names[0].photo_id == 2
    assert conversation.state.pending_names is None
    assert all(context["stage"] == "interpretation" for context in client.contexts)


def test_pending_names_block_local_source_changes_and_detect_receipt_tampering(agent_project):
    conversation, requests = agent_project
    baseline, _ = ask(conversation, requests, reply())
    prompt = "Photo 2 is bookshop"
    gate = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "remember", name_updates=[photo_name("bookshop", 2, prompt)],
    )), requests))
    with pytest.raises(CollageError, match="pending naming receipt"):
        conversation.controls(Controls(width=101, height=100))
    with pytest.raises(CollageError, match="pending naming receipt"):
        conversation.accept(baseline)
    path = child(conversation.root, "events", f"{gate.event_id:06d}.json")
    data = read_json(path)
    data["name_receipt"]["updates"][0]["photo_id"] = 1
    path.write_text(json.dumps(data), encoding="utf-8")
    before = len(requests.attempts())
    with pytest.raises(CollageError, match="receipt changed"):
        Conversation(conversation.store, "demo")
    assert len(requests.attempts()) == before and conversation.state.baseline == baseline
    assert not conversation.state.photo_names and conversation.store.load("demo").current_version is None


def test_external_controls_cannot_retarget_the_receipt_after_restart(agent_project):
    conversation, requests = agent_project
    prompt = "Map castle to photo 2"
    gate = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "remember", name_updates=[photo_name("castle", 2, prompt)],
    )), requests))
    data = read_json(conversation.state_path)
    data["controls"]["width"] = 101
    conversation.state_path.write_text(json.dumps(data), encoding="utf-8")
    resumed = Conversation(conversation.store, "demo")
    client = FakeModel(intent("names", decision="approve", receipt_event=gate.event_id))
    with pytest.raises(CollageError, match="receipt conflicts"):
        asyncio.run(resumed.request("Yes", client, requests))
    assert not client.contexts and not resumed.state.photo_names
    assert resumed.state.pending_names.event_id == gate.event_id


def test_local_chat_resume_and_status_redisplay_the_receipt_without_approval_or_calls(agent_project, monkeypatch, capsys):
    from ai_collage.chat import run_chat

    conversation, requests = agent_project
    prompt = "Map castle to photo 2"
    gate = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "remember", name_updates=[photo_name("castle", 2, prompt)],
    )), requests))
    before = len(requests.attempts())
    inputs = iter(["/status", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    run_chat(conversation.store, "demo", canvas=None, preferences=None, live=False, no_open=True)
    assert gate.question in capsys.readouterr().out
    assert len(requests.attempts()) == before
    assert Conversation(conversation.store, "demo").state.pending_names.event_id == gate.event_id


@pytest.mark.parametrize("approval", [False, True])
def test_interrupted_naming_state_commit_preserves_evidence_and_blocks_duplicate_dispatch(agent_project, monkeypatch, approval):
    conversation, requests = agent_project
    prompt = "Map castle to photo 2"
    response = intent("remember", name_updates=[photo_name("castle", 2, prompt)])
    if approval:
        gate = asyncio.run(conversation.request(prompt, FakeModel(response), requests))
        response = intent("names", decision="approve", receipt_event=gate.event_id)
        prompt = "Yes, remember those"

    def fail_commit(state):
        raise OSError("Interrupted naming state write")

    monkeypatch.setattr(conversation, "_commit", fail_commit)
    with pytest.raises(OSError, match="Interrupted naming"):
        asyncio.run(conversation.request(prompt, FakeModel(response), requests))
    state_bytes = conversation.state_path.read_bytes()
    before = len(requests.attempts())
    with pytest.raises(CollageError, match="Interrupted naming write"):
        Conversation(conversation.store, "demo")
    assert conversation.state_path.read_bytes() == state_bytes
    assert len(requests.attempts()) == before and not conversation.state.photo_names
    assert not (conversation.root / "proposals").exists()


def test_approved_name_survives_generation_timeout_with_unchanged_layout_and_pinned_resume(agent_project):
    from ai_collage.agent_requests import StageTimeout

    conversation, requests = agent_project
    baseline, _ = ask(conversation, requests, reply())
    png = conversation.preview_path(baseline).read_bytes()
    prompt = "Photo 2 is bookshop; move bookshop higher"
    gate = asyncio.run(conversation.request(prompt, FakeModel(intent(
        "edit", source="current", references=[photo_reference("bookshop", 2)],
        name_updates=[photo_name("bookshop", 2, "Photo 2 is bookshop")],
    )), requests))
    with pytest.raises(StageTimeout):
        name_decision(conversation, requests, gate, StageTimeout("offline timeout"))
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.photo_names[0].name == "bookshop" and resumed.state.pending_names is None
    assert resumed.state.baseline == baseline and resumed.preview_path(baseline).read_bytes() == png
    changed = layout_data()
    changed["layers"][1]["box"]["center_y"] -= 0.02
    client = FakeModel(intent("resume"), reply(changed))
    result = asyncio.run(resumed.request("Try again", client, requests))
    assert result.kind == "proposal" and client.contexts[1]["original_task"] == prompt
    assert client.contexts[1]["resolved_intent"]["source"]["proposal_id"] == baseline
    assert len(resumed.state.photo_names) == 1 and resumed.store.load("demo").current_version is None


@pytest.mark.parametrize("unknown", ["surfboard", "beach"])
def test_four_similar_photos_use_confirmed_descriptions_or_task_local_questions(agent_project, unknown):
    conversation, _ = agent_project
    paths = list(conversation.store.photo_paths(conversation.store.load("demo")).values())
    conversation.store.create("beach", paths * 2)
    beach = Conversation(conversation.store, "beach", canvas=(100, 100))
    requests = RequestLog(conversation.store, "beach")
    remember(beach, requests, "sand castle", 4)
    data = layout_data()
    for number in (3, 4):
        layer = copy.deepcopy(data["layers"][number - 3])
        layer["photo_id"] = number
        layer["box"]["center_y"] = 0.65
        data["layers"].append(layer)
    result, client = ask(
        beach, requests, reply(data), prompt="Move the castle photo higher",
        action=intent("fresh", references=[photo_reference("the castle photo", 4)]),
    )
    assert result == "P001" and len(client.contexts[1]["photos"]) == 4
    assert client.contexts[1]["resolved_intent"]["references"][0]["photo_id"] == 4
    question = asyncio.run(beach.request(f"Move {unknown} higher", FakeModel(intent(
        "question", question=f"Which photo number is {unknown}?",
        references=[photo_reference(unknown, None)],
    )), requests))
    assert question.kind == "question" and beach.state.baseline == result
    assert [(item.name, item.photo_id) for item in beach.state.photo_names] == [("sand castle", 4)]
