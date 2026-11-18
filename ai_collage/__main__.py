"""Thin command-line interface for the offline engine."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from .models import CollageError
from .projects import ProjectStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline deterministic photo collage engine.")
    parser.add_argument("--data-dir", type=Path, default=Path(".collage-data"))
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("create", "inspect", "apply-layout", "render"):
        subparser = commands.add_parser(command)
        subparser.add_argument("--project", required=True)
        if command == "create":
            subparser.add_argument("--images", nargs="+", type=Path, required=True)
        elif command == "apply-layout":
            subparser.add_argument("--layout", type=Path, required=True)
        elif command == "render":
            subparser.add_argument("--version", type=int)
    chat = commands.add_parser("chat", help="Create/resume a proposal conversation.")
    chat.add_argument("--project", required=True)
    chat.add_argument("--canvas", nargs=2, type=int)
    chat.add_argument("--preferences", type=Path)
    chat.add_argument("--run")
    chat.add_argument("--no-open", action="store_true")
    args = parser.parse_args(argv)
    try:
        store = ProjectStore(args.data_dir)
        if args.command == "chat":
            from .chat import run_chat

            return run_chat(
                store, args.project, canvas=tuple(args.canvas) if args.canvas else None,
                preferences=args.preferences, run_id=args.run, no_open=args.no_open,
            )
        elif args.command == "create":
            store.create(args.project, args.images)
            result = store.inspect(args.project)
        elif args.command == "inspect":
            result = store.inspect(args.project)
        elif args.command == "apply-layout":
            layout, output = store.apply_layout(args.project, args.layout)
            saved_layout, _ = store.version_paths(args.project, layout.version)
            result = {
                "version": layout.version,
                "layout_path": str(saved_layout),
                "render_path": str(output),
            }
        else:
            result = {"render_path": str(store.render(args.project, args.version))}
        print(json.dumps(result, indent=2))
        return 0
    except (CollageError, ValidationError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
