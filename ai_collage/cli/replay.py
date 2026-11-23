"""Replay JSON-defined conversations, without evaluating or accepting layouts."""

import argparse
import asyncio
from pathlib import Path
import sys

from pydantic import RootModel, ValidationError

from ..agent.requests import call_budget
from ..engine.models import CollageError
from ..engine.projects import ProjectStore
from ..evaluation.replay import load_sequence, replay


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sequence", required=True, type=Path)
    parser.add_argument("--data-dir", type=Path, default=Path(".collage-data-v3"))
    parser.add_argument("--project")
    parser.add_argument("--call-budget", type=Path, help="Optional durable cap shared by this pass.")
    parser.add_argument("--max-calls", type=int, default=200, help="Immutable cap for --call-budget (default 200).")
    parser.add_argument("--check", action="store_true", help="Validate inputs offline; create nothing.")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retry", action="store_true")
    parser.add_argument("--remaining", action="store_true", help="Run all remaining messages, not just one.")
    parser.add_argument("--answer", help="Answer the pending question/naming receipt; do not replace the script.")
    parser.add_argument("--answer-origin", choices=["user", "copilot"])
    parser.add_argument("--generation-reasoning", choices=["high", "low"], default="low")
    parser.add_argument("--interpretation-reasoning", choices=["high", "low"], default="high")
    args = parser.parse_args(argv)
    if not args.check and not args.project:
        parser.error("--project is required for live execution.")
    try:
        if args.check:
            sequence, sources = load_sequence(args.sequence)
            print(RootModel[dict[str, object]]({
                "sequence": sequence.model_dump(mode="json"),
                "sources": [source.model_dump() for source in sources],
            }).model_dump_json(indent=2))
            return 0
        store = ProjectStore(args.data_dir)
        with call_budget(args.call_budget, args.max_calls):
            report = asyncio.run(replay(
                store, args.project, args.sequence,
                resume=args.resume, remaining=args.remaining, retry=args.retry,
                answer=args.answer, answer_origin=args.answer_origin,
                generation_reasoning=args.generation_reasoning,
                interpretation_reasoning=args.interpretation_reasoning,
            ))
        print(report.model_dump_json(indent=2))
        return 0 if report.executions[-1].status in {"proposal", "selection", "acknowledgement"} else 1
    except (CollageError, ValidationError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
