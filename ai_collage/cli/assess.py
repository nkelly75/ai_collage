"""Assess saved replay evidence offline; never generate or accept a layout."""

import argparse
from pathlib import Path
import sys

from pydantic import ValidationError

from ..agent.files import child, save
from ..engine.models import CollageError
from ..engine.projects import ProjectStore
from ..evaluation.assess import assess


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".collage-data-v3"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--profile", choices=["integrity", "dark-portrait-adjustments"], default="integrity")
    args = parser.parse_args(argv)
    try:
        store = ProjectStore(args.data_dir)
        report = assess(store, args.project, profile=args.profile)
        root = child(store.project_dir(args.project), "replay", "assessments")
        numbers = [int(path.stem) for path in root.glob("*.json") if path.stem.isascii() and path.stem.isdigit()]
        path = child(root, f"{max(numbers, default=0) + 1:04d}.json")
        report.report_path = str(path)
        save(path, report)
        print(report.model_dump_json(indent=2))
        return 0 if report.passed else 1
    except (CollageError, ValidationError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
