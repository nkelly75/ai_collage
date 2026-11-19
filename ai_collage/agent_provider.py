"""Optional Agent Framework adapter with a gate at the actual HTTP boundary."""

import asyncio
import json
import time
from pathlib import Path

from .agent_requests import RequestLog
from .agent_models import INTENT
from .models import CollageError, InputLayout
from .projects import parse_json

ENDPOINT = "https://nkfoundry26.openai.azure.com/openai/v1/"
DEPLOYMENT = "gpt-5.4-mini"
AUDIENCE = "https://ai.azure.com/.default"


def instructions(stage: str = "generation") -> str:
    package = Path(__file__).resolve().parent
    if stage == "interpretation":
        return (package / "prompts" / "request-intent.md").read_text(encoding="utf-8")
    if stage != "generation":
        raise CollageError("Unknown model stage.")
    prompt = package / "prompts" / "layout-agent.md"
    guide = package.parent / "docs" / "layout-format.md"
    return (
        prompt.read_text(encoding="utf-8")
        + "\n\n# Current recipe field guide\n\n"
        + guide.read_text(encoding="utf-8")
    )


def instruction_bundle() -> str:
    return (
        "# Interpretation instructions\n\n" + instructions("interpretation")
        + "\n\n# Generation instructions\n\n" + instructions("generation")
    )


def response_format(stage: str = "generation") -> dict[str, object]:
    if stage == "interpretation":
        # Provider requires an object root. The local discriminated union
        # enforces the stricter action-dependent fields.
        definitions = INTENT.json_schema()["$defs"]
        properties = {}
        for definition in definitions.values():
            properties.update(definition["properties"])
        properties["action"] = {
            "type": "string", "enum": ["edit", "fresh", "retry", "select", "question"],
        }
        schema = {
            "$defs": definitions, "type": "object", "properties": properties,
            "required": ["action"], "additionalProperties": False,
        }
    elif stage == "generation":
        schema = InputLayout.model_json_schema()
    else:
        raise CollageError("Unknown model stage.")

    def adapt(value: object) -> object:
        if isinstance(value, dict):
            # The nested whole/cover branches are mutually exclusive by mode,
            # so anyOf preserves their semantics without unsupported oneOf.
            return {
                ("anyOf" if key == "oneOf" else key): adapt(item)
                for key, item in value.items() if key != "discriminator"
            }
        if isinstance(value, list):
            return [adapt(item) for item in value]
        return value

    return {
        "type": "json_schema",
        "json_schema": {"name": f"collage_{stage}", "schema": adapt(schema), "strict": False},
    }


class FoundryModel:
    async def complete(self, context: dict[str, object], requests: RequestLog, purpose: str) -> str:
        # Optional imports stay out of engine-only commands and local chat controls.
        from azure.core.exceptions import ClientAuthenticationError
        from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
        from agent_framework.exceptions import AgentFrameworkException
        from openai import APIError, AsyncOpenAI
        import httpx

        gate = guarded_transport(requests, purpose, httpx.AsyncHTTPTransport(retries=0), context=context)
        try:
            async with DefaultAzureCredential(exclude_interactive_browser_credential=True) as credential:
                token = get_bearer_token_provider(credential, AUDIENCE)
                async with AsyncOpenAI(
                    base_url=ENDPOINT, api_key=token, max_retries=0,
                    timeout=requests.limits.timeout_seconds,
                    http_client=httpx.AsyncClient(transport=gate, follow_redirects=False),
                ) as sdk:
                    async with asyncio.timeout(requests.limits.timeout_seconds):
                        return await run_agent(context, sdk, requests)
        except (APIError, ClientAuthenticationError, AgentFrameworkException, TimeoutError) as exc:
            if gate.local_error is not None:
                raise gate.local_error from exc
            status = getattr(exc, "status_code", None)
            raise CollageError(
                f"Foundry request stopped ({type(exc).__name__}"
                f"{f', HTTP {status}' if status else ''}); no automatic retry."
            ) from exc


async def run_agent(context: dict[str, object], sdk: object, requests: RequestLog) -> str:
    from agent_framework import Agent
    from agent_framework.openai import OpenAIChatClient

    stage = context.get("stage")
    if not isinstance(stage, str) or stage not in {"interpretation", "generation"}:
        raise CollageError("A model request requires an explicit stage.")
    agent = Agent(
        client=OpenAIChatClient(model=DEPLOYMENT, async_client=sdk),
        name="CollageDesigner", instructions=instructions(stage),
        default_options={
            "store": False, "max_tokens": requests.limits.output_tokens,
            "reasoning": {"effort": "high"},
            "response_format": response_format(stage),
        },
    )
    response = await agent.run(json.dumps(context, ensure_ascii=False))
    if response.finish_reason != "stop" or not response.text.strip():
        raise CollageError("Model did not produce a completed response; no automatic retry.")
    return response.text


def guarded_transport(
    requests: RequestLog, purpose: str, transport: object, *,
    context: dict[str, object] | None = None,
):
    import httpx
    import tiktoken

    if tiktoken.model.encoding_name_for_model(DEPLOYMENT) != "o200k_base":
        raise CollageError("Verified byte-level tokenizer mapping changed; review input accounting.")

    class Guard(httpx.AsyncBaseTransport):
        used = False
        local_error: CollageError | None = None

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
            try:
                return await self.dispatch(request)
            except CollageError as exc:
                self.local_error = exc
                raise

        async def dispatch(self, request: httpx.Request) -> httpx.Response:
            if self.used:
                raise CollageError("Unexpected extra inference within one agent request.")
            if (
                request.method != "POST" or request.url.path != "/openai/v1/responses"
                or request.url.host != "nkfoundry26.openai.azure.com"
            ):
                raise CollageError("Unexpected provider endpoint; no request dispatched.")
            body = parse_json(request.content)
            if not isinstance(body, dict):
                raise CollageError("Provider request must be a JSON object.")
            limits = requests.limits
            if (
                body.get("model") != DEPLOYMENT or body.get("store") is not False
                or body.get("max_output_tokens") != limits.output_tokens
                or body.get("reasoning") != {"effort": "high"}
                or body.get("stream", False) is not False
                or body.get("tools") or body.get("previous_response_id")
                or body.get("conversation") or body.get("background", False)
            ):
                raise CollageError("Unsafe provider options; no request dispatched.")
            # o200k is byte-level BPE: one token per serialized UTF-8 byte is an
            # upper bound on text. Include schema/JSON syntax too, plus ample
            # framing reserve for at most four input messages and instructions.
            if not isinstance(body.get("input"), list) or len(body["input"]) > 4:
                raise CollageError("Unexpected provider message framing.")
            input_bound = len(request.content) + 4096
            history = context.get("history") if context is not None else None
            if (
                input_bound > limits.input_tokens and context is not None
                and isinstance(history, list) and history
            ):
                omitted = context.get("history_omitted")
                if type(omitted) is not int or omitted < 0:
                    raise CollageError("Invalid compact-history accounting; no request dispatched.")
                text = json.dumps(context, ensure_ascii=False)
                parts = [
                    part for message in body["input"] if isinstance(message, dict)
                    for part in message.get("content", []) if isinstance(part, dict)
                    and part.get("type") == "input_text" and part.get("text") == text
                ]
                if len(parts) != 1:
                    raise CollageError("Cannot identify context for input-size trimming; no request dispatched.")
                while input_bound > limits.input_tokens and history:
                    history.pop(0)
                    omitted += 1
                    context["history_omitted"] = omitted
                    parts[0]["text"] = json.dumps(context, ensure_ascii=False)
                    content = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    request = httpx.Request(
                        request.method, request.url,
                        headers={key: value for key, value in request.headers.items() if key != "content-length"},
                        content=content, extensions=request.extensions,
                    )
                    input_bound = len(content) + 4096
            attempt = requests.reserve(purpose, input_bound)
            self.used = True
            started = time.monotonic()
            try:
                async with asyncio.timeout(limits.timeout_seconds):
                    response = await transport.handle_async_request(request)
                    await response.aread()
            except (httpx.HTTPError, TimeoutError, asyncio.CancelledError):
                requests.finish(attempt.model_copy(update={
                    "status": "error", "duration": time.monotonic() - started,
                    "error": "transport interrupted or timed out",
                }))
                raise
            raw = parse_json(response.content)
            if not isinstance(raw, dict):
                raise CollageError("Invalid provider response envelope.")
            usage = raw.get("usage") or {}
            if not isinstance(usage, dict):
                raise CollageError("Invalid provider usage envelope.")
            input_details = usage.get("input_tokens_details") or {}
            output_details = usage.get("output_tokens_details") or {}
            complete = response.is_success and raw.get("status") == "completed"
            finished = attempt.model_copy(update={
                "status": "complete" if complete else ("incomplete" if response.is_success else "error"),
                "duration": time.monotonic() - started,
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "cached_tokens": input_details.get("cached_tokens"),
                "reasoning_tokens": output_details.get("reasoning_tokens"),
                "error": None if complete else f"HTTP {response.status_code}; status {raw.get('status')}",
            })
            requests.finish(type(attempt).model_validate(finished.model_dump()))
            return response

        async def aclose(self) -> None:
            await transport.aclose()

    return Guard()
