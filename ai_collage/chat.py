"""Terminal controls stay local; ordinary text requests produce proposals."""

import asyncio
import json
import os
import shlex
import sys
from pathlib import Path

from pydantic import ValidationError

from .agent_budget import RunLedger
from .agent_models import Controls
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
only with a selected authorized run. Canvas/cropping changes affect future
proposals, not existing previews. Acceptance is separate from rating an edit."""


def open_preview(path: Path) -> None:
    try:
        if sys.platform != "win32":
            raise OSError("Automatic opening is supported on Windows; use the preview path.")
        os.startfile(path)
    except OSError as exc:
        print(f"Warning: preview could not be opened: {exc}. Open {path}", file=sys.stderr)


def local_command(
    conversation: Conversation, text: str, ledger: RunLedger | None, *, no_open: bool,
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
            "run": ledger.summary() if ledger else None,
        }, indent=2))
    else:
        raise CollageError("Unknown command or invalid arguments. Use /help.")
    return True


def run_chat(
    store: ProjectStore, project_id: str, *, canvas: tuple[int, int] | None,
    preferences: Path | None, run_id: str | None, no_open: bool,
) -> int:
    ledger = RunLedger(store, run_id) if run_id else None
    conversation = Conversation(store, project_id, canvas=canvas, preferences=preferences)
    print("Conversation resumed. Use /help. Generated previews are not accepted automatically.")
    print(f"Editing baseline: {conversation.state.baseline or conversation.state.initial_version or 'none'}")
    if ledger is None:
        print("Local-only mode: no authorized run selected.")

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
                    if not local_command(conversation, text, ledger, no_open=no_open):
                        return
                else:
                    if ledger is None:
                        raise CollageError("No authorized run selected; model requests are disabled.")
                    from .agent_provider import FoundryModel

                    result = await conversation.request(text, FoundryModel(), ledger)
                    print(result)
                    if result.startswith("P") and conversation.state.baseline == result:
                        path = conversation.preview_path(result)
                        print(path)
                        print(json.dumps(ledger.summary()))
                        if not no_open:
                            open_preview(path)
            except (CollageError, ValidationError, OSError, ValueError) as exc:
                print(f"Error: {exc}", file=sys.stderr)

    try:
        asyncio.run(loop())
    except KeyboardInterrupt:
        print("\nStopped; reserved attempts remain counted.")
    return 0
