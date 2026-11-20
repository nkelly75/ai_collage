"""Terminal controls stay local; ordinary text requests produce proposals."""

import asyncio
import json
import os
import shlex
import sys
from pathlib import Path

from pydantic import ValidationError

from .agent_requests import RequestLog
from .agent_models import Controls, Reasoning, ResolvedIntent
from .conversation import Conversation
from .models import CollageError
from .projects import ProjectStore

HELP = """/show P001
/rate P001 worked|partly|failed [note]
/accept P001
/status
/canvas WIDTH HEIGHT
/cropping allow|forbid
/help
/quit
These commands are local and free of model calls. Other text goes to Foundry
only with --live. Canvas/cropping changes affect future
proposals, not existing previews. Acceptance is separate from rating an edit."""


def open_preview(path: Path) -> None:
    try:
        if sys.platform != "win32":
            raise OSError("Automatic opening is supported on Windows; use the preview path.")
        os.startfile(path)
    except OSError as exc:
        print(f"Warning: preview could not be opened: {exc}. Open {path}", file=sys.stderr)


def show_usage(requests: RequestLog) -> None:
    usage = requests.summary()
    print(
        f"Project requests: {usage['attempts']}. Known usage: "
        f"{usage['input_tokens']:,} input / {usage['output_tokens']:,} output tokens."
    )
    unknown = usage["unknown_usage_attempts"]
    if unknown:
        identifiers = ", ".join(str(number) for number in unknown)
        print(
            f"Usage unavailable for {len(unknown)} request{'s' if len(unknown) != 1 else ''} "
            f"(attempt{'s' if len(unknown) != 1 else ''} {identifiers}); totals are incomplete."
        )


def show_progress(kind: str, intent: ResolvedIntent | None) -> None:
    if kind == "generation":
        print("Generating layout...", flush=True)
    elif intent is None:
        print(
            "Intent: clarification needed." if kind == "question" else "Intent: remember photo names.",
            flush=True,
        )
    else:
        source = intent.source
        label = (
            source.proposal_id or f"accepted version {source.accepted_version}"
            if source is not None else "no editing source"
        )
        targets = sorted({item.photo_id for item in intent.references if item.photo_id is not None})
        suffix = f"; target photo{'s' if len(targets) != 1 else ''} " + ", ".join(
            str(number) for number in targets
        ) if targets else ""
        print(f"Intent: {intent.action}; source {label}{suffix}.", flush=True)


def local_command(
    conversation: Conversation, text: str, requests: RequestLog, *, no_open: bool,
) -> bool:
    parts = shlex.split(text)
    if not parts:
        raise CollageError("Empty command.")
    command, *args = parts
    if command == "/quit" and not args:
        return False
    if command == "/help" and not args:
        print(HELP)
    elif command == "/show" and len(args) == 1:
        conversation.proposal(args[0])
        path = conversation.preview_path(args[0])
        print(path)
        if not no_open:
            open_preview(path)
    elif command == "/rate" and len(args) >= 2:
        conversation.rate(args[0], args[1], " ".join(args[2:]) or None)
        print("Rating saved locally; no model call.")
    elif command == "/accept" and len(args) == 1:
        version = conversation.accept(args[0])
        print(f"Accepted {args[0]} as version {version}.")
    elif command == "/canvas" and len(args) == 2:
        try:
            width, height = (int(value) for value in args)
        except ValueError as exc:
            raise CollageError("Canvas dimensions must be integers.") from exc
        conversation.controls(Controls(
            width=width, height=height, cropping=conversation.state.controls.cropping
        ))
        print("Canvas updated for future proposals; existing preview is unchanged.")
    elif command == "/cropping" and len(args) == 1 and args[0] in {"allow", "forbid"}:
        conversation.controls(conversation.state.controls.model_copy(
            update={"cropping": args[0] == "allow"}
        ))
        print("Cropping permission updated; existing preview is unchanged.")
    elif command == "/status" and not args:
        print(json.dumps({
            "project": conversation.project_id,
            "baseline": conversation.state.baseline,
            "accepted_version": conversation.store.load(conversation.project_id).current_version,
            "controls": conversation.state.controls.model_dump(),
            "preferences": conversation.state.preferences.model_dump(),
        }, indent=2))
        show_usage(requests)
    else:
        raise CollageError("Unknown command or invalid arguments. Use /help.")
    return True


def run_chat(
    store: ProjectStore, project_id: str, *, canvas: tuple[int, int] | None,
    preferences: Path | None, live: bool, no_open: bool,
    generation_reasoning: Reasoning = "high",
) -> int:
    conversation = Conversation(store, project_id, canvas=canvas, preferences=preferences)
    requests = RequestLog(store, project_id, generation_reasoning=generation_reasoning)
    print("Conversation resumed. Use /help. Generated previews are not accepted automatically.")
    print(f"Editing baseline: {conversation.state.baseline or conversation.state.initial_version or 'none'}")
    print(f"Generation reasoning: {generation_reasoning}; interpretation reasoning: high.")
    if not live:
        print("Local-only mode: omit model requests, or restart with --live.")

    async def loop() -> None:
        while True:
            try:
                text = input("You: ")
            except EOFError:
                return
            if not text.strip():
                continue
            try:
                if text.startswith("/"):
                    if not local_command(conversation, text, requests, no_open=no_open):
                        return
                else:
                    if not live:
                        raise CollageError("Model requests are disabled; restart chat with --live.")
                    from .agent_provider import FoundryModel

                    result = await conversation.request(
                        text, FoundryModel(), requests, progress=show_progress,
                    )
                    if result.kind == "question":
                        print(result.question)
                    elif result.kind == "acknowledgement":
                        print(result.acknowledgement)
                    else:
                        assert result.proposal_id is not None
                        label = "Generated" if result.kind == "proposal" else "Restored"
                        print(f"{label} {result.proposal_id}")
                        path = conversation.preview_path(result.proposal_id)
                        print(path)
                        if not no_open:
                            open_preview(path)
                    show_usage(requests)
            except (CollageError, ValidationError, OSError, ValueError) as exc:
                print(f"Error: {exc}", file=sys.stderr)
                show_usage(requests)

    try:
        asyncio.run(loop())
    except KeyboardInterrupt:
        print("\nStopped; dispatched requests remain recorded.")
    return 0
