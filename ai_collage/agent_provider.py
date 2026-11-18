"""Optional Agent Framework adapter with a gate at the actual HTTP boundary."""

import asyncio
import json
import time
from pathlib import Path

from .agent_budget import RunLedger
from .agent_models import REPLY
from .models import CollageError
from .projects import parse_json

ENDPOINT = "https://nkfoundry26.openai.azure.com/openai/v1/"
DEPLOYMENT = "gpt-5.4-mini"
AUDIENCE = "https://ai.azure.com/.default"


def instructions() -> str:
    package = Path(__file__).resolve().parent
    prompt = package / "prompts" / "layout-agent.md"
    guide = package.parent / "docs" / "layout-format.md"
    return (
        prompt.read_text(encoding="utf-8")
        + "\n\n# Current recipe field guide\n\n"
        + guide.read_text(encoding="utf-8")
    )


def response_format() -> dict[str, object]:
    definitions = REPLY.json_schema()["$defs"]
    # Responses requires an object root, not a root union. The local REPLY
    # validator still enforces the exact kind-dependent fields and rejects mixes.
    schema = {
        "$defs": definitions,
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["proposal", "question"]},
            "recipe": definitions["ProposalReply"]["properties"]["recipe"],
            "question": definitions["QuestionReply"]["properties"]["question"],
        },
        "required": ["kind"],
        "additionalProperties": False,
    }

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
        "json_schema": {"name": "collage_reply", "schema": adapt(schema), "strict": False},
    }


class FoundryModel:
    async def complete(self, context: dict[str, object], ledger: RunLedger, purpose: str) -> str:
        # Optional imports stay out of engine-only commands and local chat controls.
        from azure.core.exceptions import ClientAuthenticationError
        from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
        from agent_framework.exceptions import AgentFrameworkException
        from openai import APIError, AsyncOpenAI
        import httpx

        gate = guarded_transport(ledger, purpose, httpx.AsyncHTTPTransport(retries=0))
        try:
            async with DefaultAzureCredential(exclude_interactive_browser_credential=True) as credential:
                token = get_bearer_token_provider(credential, AUDIENCE)
                async with AsyncOpenAI(
                    base_url=ENDPOINT, api_key=token, max_retries=0,
                    timeout=ledger.config.limits.timeout_seconds,
                    http_client=httpx.AsyncClient(transport=gate, follow_redirects=False),
                ) as sdk:
                    async with asyncio.timeout(ledger.config.limits.timeout_seconds):
                        return await run_agent(context, sdk, ledger)
        except (APIError, ClientAuthenticationError, AgentFrameworkException, TimeoutError) as exc:
            status = getattr(exc, "status_code", None)
            raise CollageError(
                f"Foundry request stopped ({type(exc).__name__}"
                f"{f', HTTP {status}' if status else ''}); no automatic retry."
            ) from exc


async def run_agent(context: dict[str, object], sdk: object, ledger: RunLedger) -> str:
    from agent_framework import Agent
    from agent_framework.openai import OpenAIChatClient

    agent = Agent(
        client=OpenAIChatClient(model=DEPLOYMENT, async_client=sdk),
        name="CollageDesigner", instructions=instructions(),
        default_options={
            "store": False, "max_tokens": ledger.config.limits.output_tokens,
            "reasoning": {"effort": "high"},
            "response_format": response_format(),
        },
    )
    response = await agent.run(json.dumps(context, ensure_ascii=False))
    if response.finish_reason != "stop" or not response.text.strip():
        raise CollageError("Model did not produce a completed response; no automatic retry.")
    return response.text


def guarded_transport(ledger: RunLedger, purpose: str, transport: object):
    import httpx
    import tiktoken

    if tiktoken.model.encoding_name_for_model(DEPLOYMENT) != "o200k_base":
        raise CollageError("Verified byte-level tokenizer mapping changed; review input accounting.")

    class Guard(httpx.AsyncBaseTransport):
        used = False

        async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
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
            limits = ledger.config.limits
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
            attempt = ledger.reserve(purpose, input_bound)
            self.used = True
            started = time.monotonic()
            try:
                async with asyncio.timeout(limits.timeout_seconds):
                    response = await transport.handle_async_request(request)
                    await response.aread()
            except (httpx.HTTPError, TimeoutError, asyncio.CancelledError):
                ledger.finish(attempt.model_copy(update={
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
            ledger.finish(type(attempt).model_validate(finished.model_dump()))
            return response

        async def aclose(self) -> None:
            await transport.aclose()

    return Guard()
