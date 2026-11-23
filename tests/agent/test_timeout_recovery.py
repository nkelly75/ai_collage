import asyncio
import json

import pytest

from ai_collage.agent.models import Attempt, LayoutSource
from ai_collage.agent.requests import RequestLog, StageTimeout
from ai_collage.cli.chat import show_usage
from ai_collage.agent.conversation import Conversation
from ai_collage.engine.models import CollageError
from ai_collage.engine.projects import read_json

from .test_agent import (
    FakeModel, agent_project, ask, asyncio_wakeup_pair, intent, photo_reference,
    reply, response_envelope,
)


@pytest.mark.parametrize("stage", ["interpretation", "generation"])
def test_stage_corrections_share_deadline_and_stop_before_another_dispatch(
    agent_project, monkeypatch, stage,
):
    conversation, requests = agent_project
    clock = [1000.0]
    monkeypatch.setattr("ai_collage.agent.requests.monotonic", lambda: clock[0])

    class ClockModel(FakeModel):
        async def complete(self, context, log, purpose):
            text = await super().complete(context, log, purpose)
            if context["stage"] == stage:
                clock[0] += 120 if stage == "interpretation" else 180
            return text

    model = ClockModel("{}") if stage == "interpretation" else ClockModel(intent("fresh"), "{}")
    with pytest.raises(StageTimeout, match="timed out"):
        asyncio.run(conversation.request("Make a collage", model, requests))
    assert len(model.contexts) == (1 if stage == "interpretation" else 2)
    assert conversation.state.baseline is None
    assert conversation.history()[-1].generation_timeout == (stage == "generation")
    assert requests.attempts()[-1].timeout_seconds == (120 if stage == "interpretation" else 180)


def test_partial_stage_budget_is_reused_and_generation_gets_a_new_budget(agent_project, monkeypatch):
    conversation, requests = agent_project
    clock = [1000.0]
    monkeypatch.setattr("ai_collage.agent.requests.monotonic", lambda: clock[0])

    class ClockModel(FakeModel):
        async def complete(self, context, log, purpose):
            text = await super().complete(context, log, purpose)
            clock[0] += 50
            return text

    model = ClockModel("{}", intent("fresh"), "{}", reply())
    asyncio.run(conversation.request("Make a collage", model, requests))
    assert [item.timeout_seconds for item in requests.attempts()] == [120, 70, 180, 130]
    assert [item.stage for item in requests.attempts()] == [
        "interpretation", "interpretation", "generation", "generation",
    ]


@pytest.mark.parametrize("stage", ["interpretation", "generation"])
def test_exhausted_correction_budget_cannot_dispatch_again(agent_project, monkeypatch, stage):
    conversation, requests = agent_project
    clock = [1000.0]
    monkeypatch.setattr("ai_collage.agent.requests.monotonic", lambda: clock[0])
    original_context = conversation.context
    counts = {"interpretation": 0, "generation": 0}

    def context(*args, **kwargs):
        counts[kwargs["stage"]] += 1
        if kwargs["stage"] == stage and counts[stage] == 2:
            clock[0] += 200
        return original_context(*args, **kwargs)

    monkeypatch.setattr(conversation, "context", context)
    model = FakeModel("{}") if stage == "interpretation" else FakeModel(intent("fresh"), "{}")
    with pytest.raises(StageTimeout):
        asyncio.run(conversation.request("Make a collage", model, requests))
    assert counts[stage] == 2
    assert len(model.contexts) == (1 if stage == "interpretation" else 2)
    assert conversation.history()[-2].outcome == "invalid"
    assert conversation.history()[-1].attempt is None


@pytest.mark.parametrize("continuation", ["try again", "Make breakfast smaller", "2"])
def test_timeout_continuation_keeps_original_task_answers_and_source_after_restart(
    agent_project, continuation,
):
    conversation, requests = agent_project
    original, _ = ask(conversation, requests, reply())
    ask(
        conversation, requests, prompt="Make breakfast smaller",
        action=intent("question", question="Which photo is breakfast?",
                      references=[photo_reference("breakfast", None)]),
    )
    before = conversation.preview_path(original).read_bytes()
    model = FakeModel(
        intent("edit", source="current", references=[photo_reference("2", 2)]),
        StageTimeout("simulated timeout"),
    )
    with pytest.raises(StageTimeout, match='baseline is unchanged.*try again'):
        asyncio.run(conversation.request("2", model, requests))
    resumed = Conversation(conversation.store, "demo")
    assert resumed.state.baseline == original
    assert resumed.preview_path(original).read_bytes() == before
    assert resumed.store.load("demo").current_version is None
    retry = FakeModel(intent("resume"), reply())
    result = asyncio.run(resumed.request(continuation, retry, requests))
    assert result.proposal_id == "P002"
    assert retry.contexts[0]["failed_task"]["resolved_intent"]["source"] == LayoutSource(
        proposal_id=original,
    ).model_dump(mode="json")
    generation = retry.contexts[1]
    assert generation["original_task"] == "Make breakfast smaller"
    assert generation["active_task"]["request"] == "Make breakfast smaller"
    assert "2" in generation["active_task"]["answers"]
    assert generation["editing_baseline"] == resumed.proposal(original).recipe.model_dump(mode="json")
    assert resumed.proposal("P002").parent == original
    assert len(resumed.tasks()) == 2
    assert resumed.context("Next")["failed_task"] is None


def test_older_source_timeout_and_repeated_timeout_never_edit_the_current_result(agent_project):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    latest, _ = ask(conversation, requests, reply())
    model = FakeModel(intent("edit", source=first), StageTimeout("offline timeout"))
    with pytest.raises(StageTimeout):
        asyncio.run(conversation.request(f"Return to {first} and make photo 2 smaller", model, requests))
    for _ in range(2):
        conversation = Conversation(conversation.store, "demo")
        model = FakeModel(intent("resume"), StageTimeout("offline timeout"))
        with pytest.raises(StageTimeout):
            asyncio.run(conversation.request("try again", model, requests))
        assert model.contexts[-1]["resolved_intent"]["source"] == LayoutSource(
            proposal_id=first,
        ).model_dump(mode="json")
        assert conversation.state.baseline == latest
    resumed = Conversation(conversation.store, "demo")
    model = FakeModel(intent("resume"), reply())
    result = asyncio.run(resumed.request("try again", model, requests))
    assert resumed.proposal(result.proposal_id).parent == first
    assert len(resumed.tasks()) == 3


@pytest.mark.parametrize("continuation", ["clarification", "timeout"])
@pytest.mark.parametrize("failure", [CollageError, OSError, StageTimeout])
def test_interpretation_errors_preserve_unfinished_task_after_restart(
    agent_project, continuation, failure,
):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    latest, _ = ask(conversation, requests, reply())
    preview = conversation.preview_path(latest).read_bytes()
    original = f"Return to {first} and make one photo smaller"
    if continuation == "clarification":
        initial = FakeModel(intent("question", question="Which photo number?"))
        asyncio.run(conversation.request(original, initial, requests))
        answer = "2"
        resolved = intent("edit", source=first, references=[photo_reference("2", 2)])
    else:
        initial = FakeModel(intent("edit", source=first), StageTimeout("offline timeout"))
        with pytest.raises(StageTimeout):
            asyncio.run(conversation.request(original, initial, requests))
        answer = "try again"
        resolved = intent("resume")
    task_id = conversation.history()[-1].task_id
    for correction in (False, True):
        conversation = Conversation(conversation.store, "demo")
        model = FakeModel(*(["{}"] if correction else []), failure("offline failure"))
        with pytest.raises(failure):
            asyncio.run(conversation.request(answer, model, requests))
        assert len(model.contexts) == (2 if correction else 1)
        assert all(context["stage"] == "interpretation" for context in model.contexts)
        assert conversation.state.baseline == latest
    reopened = Conversation(conversation.store, "demo")
    pending = reopened.context(answer)
    if continuation == "clarification":
        assert pending["pending_question"]["original_task"] == original
    else:
        assert pending["failed_task"]["task_id"] == task_id
    model = FakeModel(resolved, reply())
    result = asyncio.run(reopened.request(answer, model, requests))
    proposal = reopened.proposal(result.proposal_id)
    assert proposal.intent.task_turn == task_id
    assert proposal.intent.task_request == original
    assert proposal.parent == first
    assert model.contexts[-1]["active_task"]["request"] == original
    assert answer in model.contexts[-1]["active_task"]["answers"]
    assert reopened.preview_path(latest).read_bytes() == preview
    assert reopened.store.load("demo").current_version is None
    assert len(Conversation(reopened.store, "demo").tasks()) == 3


def test_new_task_supersedes_timeout_and_resume_without_failure_is_invalid(agent_project):
    conversation, requests = agent_project
    failed = FakeModel(intent("fresh"), StageTimeout("offline"))
    with pytest.raises(StageTimeout):
        asyncio.run(conversation.request("Make a collage", failed, requests))
    with pytest.raises(CollageError, match="offline interpretation"):
        asyncio.run(conversation.request(
            "try again", FakeModel(CollageError("offline interpretation")), requests,
        ))
    conversation = Conversation(conversation.store, "demo")
    model = FakeModel(intent("fresh", continues_task=False), reply())
    asyncio.run(conversation.request("Start a different arrangement instead", model, requests))
    assert len(conversation.tasks()) == 2
    assert model.contexts[-1]["active_task"] == {
        "request": "Start a different arrangement instead", "answers": [],
    }
    assert model.contexts[-1]["failed_task"] is None
    model = FakeModel(intent("resume"), intent("question", question="Which task?"))
    result = asyncio.run(conversation.request("try again", model, requests))
    assert result.kind == "question"
    assert "No confirmed" in model.contexts[-1]["validation_feedback"]


@pytest.mark.parametrize("publication", [False, True])
def test_unrelated_failures_do_not_claim_safe_timeout_recovery(agent_project, monkeypatch, publication):
    conversation, requests = agent_project
    if publication:
        def fail(*args):
            raise OSError("disk unavailable")
        monkeypatch.setattr(conversation, "_publish", fail)
        model = FakeModel(intent("fresh"), reply())
    else:
        model = FakeModel(intent("fresh"), CollageError("Service stopped"))
    with pytest.raises((CollageError, OSError)) as failure:
        asyncio.run(conversation.request("Make a collage", model, requests))
    assert "baseline is unchanged" not in str(failure.value)
    assert not conversation.history()[-1].generation_timeout
    assert Conversation(conversation.store, "demo").context("try again")["failed_task"] is None


def test_progress_is_validated_once_and_arrives_before_generation(agent_project):
    conversation, requests = agent_project
    notifications = []

    class ObservedModel(FakeModel):
        async def complete(self, context, log, purpose):
            assert context.get("progress") is None
            if context["stage"] == "generation":
                assert notifications == [("intent", "fresh"), ("generation", "fresh")]
            return await super().complete(context, log, purpose)

    model = ObservedModel("{}", intent("fresh"), "{}", reply())
    asyncio.run(conversation.request(
        "Make a collage", model, requests,
        progress=lambda kind, resolved: notifications.append((kind, resolved.action if resolved else None)),
    ))
    assert len(notifications) == 2
    assert model.contexts[1]["validation_feedback"]


@pytest.mark.parametrize("action", ["question", "remember", "select"])
def test_nongeneration_progress_does_not_announce_layout(agent_project, action):
    conversation, requests = agent_project
    first, _ = ask(conversation, requests, reply())
    prompt = "What next?"
    if action == "question":
        response = intent("question", question="Which photo?")
    elif action == "remember":
        prompt = "photo 2 is breakfast"
        response = intent("remember", name_updates=[{"name": "breakfast", "photo_id": 2, "quote": prompt}])
    else:
        prompt = f"Return to {first}"
        response = intent("select", proposal_id=first)
    notifications = []
    model = FakeModel(response)
    asyncio.run(conversation.request(
        prompt, model, requests, progress=lambda kind, resolved: notifications.append(kind),
    ))
    assert "generation" not in notifications and len(notifications) == 1


@pytest.mark.parametrize("missing", ["none", "all", "partial"])
def test_readable_project_usage_preserves_unknown_attempt_ids(store, capsys, missing):
    requests = RequestLog(store, "usage")
    attempt = requests.reserve("offline", 100)
    requests.finish(attempt.model_copy(update={
        "status": "error" if missing != "none" else "complete",
        "input_tokens": None if missing == "all" else 50,
        "output_tokens": 20 if missing == "none" else None,
    }))
    reopened = RequestLog(store, "usage")
    before = reopened.summary()
    show_usage(reopened)
    text = capsys.readouterr().out
    assert "Project requests: 1. Known usage:" in text
    assert "unknown_usage_attempts" not in text
    if missing == "none":
        assert "50 input / 20 output" in text and "incomplete" not in text
    else:
        assert "Usage unavailable for 1 request (attempt 1); totals are incomplete." in text
    assert reopened.summary() == before


@pytest.mark.parametrize("interpretation", ["high", "low"])
def test_chat_progress_low_candidate_and_readable_status_are_terminal_only(
    agent_project, monkeypatch, capsys, interpretation,
):
    from ai_collage.cli.main import main

    conversation, requests = agent_project
    model = FakeModel("{}", intent("fresh", references=[photo_reference("photo 2", 2)]), reply())
    lines = iter(["Make photo 2 stand out", "/status", "/quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(lines))
    monkeypatch.setattr("ai_collage.agent.provider.FoundryModel", lambda: model)
    assert main([
        "--data-dir", str(conversation.store.data_dir), "chat", "--project", "demo",
        "--live", "--no-open", "--interpretation-reasoning", interpretation,
    ]) == 0
    output = capsys.readouterr()
    assert not output.err
    assert output.out.count("Intent:") == output.out.count("Generating layout...") == 1
    assert "; target photo 2." in output.out
    assert output.out.index("Intent:") < output.out.index("Generating layout...") < output.out.index("Generated P001")
    assert "unknown_usage_attempts" not in output.out
    assert f"Generation reasoning: low; interpretation reasoning: {interpretation}." in output.out
    assert [item.reasoning_effort for item in requests.attempts()] == [interpretation, interpretation, "low"]


@pytest.mark.parametrize("generation", ["high", "low"])
@pytest.mark.parametrize("interpretation", ["high", "low"])
@pytest.mark.parametrize("stage", ["interpretation", "generation"])
def test_actual_payload_reasoning_and_attempt_settings(store, stage, generation, interpretation):
    import httpx
    from openai import AsyncOpenAI
    from ai_collage.agent.provider import ENDPOINT, guarded_transport, run_agent

    requests = RequestLog(
        store, "candidate", generation_reasoning=generation,
        interpretation_reasoning=interpretation,
    )
    captured = []
    expected = generation if stage == "generation" else interpretation
    context = {"stage": stage, "user_request": "Make a collage"}

    async def handler(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json=response_envelope(
            reply() if stage == "generation" else intent("fresh"),
        ))

    gate = guarded_transport(requests, "candidate", httpx.MockTransport(handler), context=context)

    async def execute():
        async with AsyncOpenAI(
            base_url=ENDPOINT, api_key="offline", max_retries=0,
            http_client=httpx.AsyncClient(transport=gate),
        ) as sdk:
            await run_agent(context, sdk, requests)

    asyncio.run(execute())
    assert captured[0]["reasoning"] == {"effort": expected}
    attempt = Attempt.model_validate(read_json(requests.root / "attempt-0001.json"))
    assert attempt.stage == stage and attempt.reasoning_effort == expected
    assert 0 < attempt.timeout_seconds <= (180 if stage == "generation" else 120)


def test_transport_timeout_is_identified_without_credentials_or_live_calls(agent_project, monkeypatch):
    import httpx
    from ai_collage.agent.provider import FoundryModel

    conversation, requests = agent_project

    class OfflineCredential:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    async def handler(request):
        body = json.loads(request.content)
        if body["text"]["format"]["name"] == "collage_interpretation":
            return httpx.Response(200, json=response_envelope(intent("fresh")))
        raise httpx.ReadTimeout("offline timeout")

    monkeypatch.setattr("azure.identity.aio.DefaultAzureCredential", lambda **kwargs: OfflineCredential())
    monkeypatch.setattr("azure.identity.aio.get_bearer_token_provider", lambda *args: "offline")
    monkeypatch.setattr("httpx.AsyncHTTPTransport", lambda **kwargs: httpx.MockTransport(handler))
    with pytest.raises(StageTimeout, match="before publication"):
        asyncio.run(conversation.request("Make a collage", FoundryModel(), requests))
    assert requests.summary()["unknown_usage_attempts"] == [2]
    assert requests.attempts()[-1].status == "error"
    resumed = Conversation(conversation.store, "demo")
    assert resumed.context("try again")["failed_task"] is not None
