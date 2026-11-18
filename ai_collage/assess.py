"""Assess saved replay evidence offline; never generate or accept a layout."""

import argparse
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from .agent_files import canonical, child, digest, save
from .agent_models import Proposal
from .geometry import resolve_layout
from .models import CollageError, ResolvedLayout
from .projects import ProjectStore, read_json
from .replay import ReplayReport, StepResult

Profile = Literal["integrity", "dark-portrait-adjustments"]


def _semantic(resolved: ResolvedLayout) -> dict:
    value = resolved.recipe.model_dump(mode="json")
    value["canvas"]["background"] = value["canvas"]["background"].upper()
    for layer in value["layers"]:
        border = layer["border"]
        if border is None or border["width_px"] == 0:
            layer["border"] = None
        else:
            border["color"] = border["color"].upper()
    return value


def dark_portrait_errors(
    step: int, current: ResolvedLayout, previous: ResolvedLayout | None,
) -> list[str]:
    """Preserve the historical dark portrait checks, including exact white borders."""
    errors = []
    now = _semantic(current)
    if step == 0:
        color = current.recipe.canvas.background
        rgb = [int(color[index:index + 2], 16) for index in (1, 3, 5)]
        if not (all(16 <= item <= 80 for item in rgb) and max(rgb) - min(rgb) <= 12):
            errors.append("Background is outside the declared dark-neutral range.")
        areas = {g.photo_id: g.box_pixels.width * g.box_pixels.height for g in current.geometry}
        if not all(areas[2] < area for photo_id, area in areas.items() if photo_id != 2):
            errors.append("Photo 2 is not smaller than every other photo.")
        for layer in current.recipe.layers:
            if (
                layer.border is None or not 1 <= layer.border.width_px <= 12
                or layer.border.color.upper() != "#FFFFFF"
                or not 1 <= layer.corner_radius_px <= 16
                or abs(layer.rotation_degrees) > 3
            ):
                errors.append(f"Photo {layer.photo_id} does not follow the subtle-style defaults.")
        if not any(layer.rotation_degrees for layer in current.recipe.layers):
            errors.append("Initial proposal has no tilt.")
        return errors
    if previous is None:
        return ["No preceding successful proposal to compare."]
    old = _semantic(previous)
    if step == 1:
        a = next(g.box_pixels for g in previous.geometry if g.photo_id == 2)
        b = next(g.box_pixels for g in current.geometry if g.photo_id == 2)
        if b.width >= a.width:
            errors.append("Photo 2 did not get at least one pixel narrower.")
        if (
            abs((a.x + a.width / 2) - (b.x + b.width / 2)) > 1
            or abs((a.y + a.height / 2) - (b.y + b.height / 2)) > 1
        ):
            errors.append("Photo 2 centre moved by more than one pixel.")
        for value in (old, now):
            for layer in value["layers"]:
                if layer["photo_id"] == 2:
                    layer["box"]["width"] = None
                    if "height" in layer["box"]:
                        layer["box"]["height"] = None
    elif step == 2:
        if any(layer["border"] is not None for layer in now["layers"]):
            errors.append("Some borders remain.")
        for value in (old, now):
            for layer in value["layers"]:
                layer["border"] = None
    elif step == 3:
        if any(layer["rotation_degrees"] != 0 for layer in now["layers"]):
            errors.append("Some photos are still tilted.")
        if any(layer["border"] is not None for layer in now["layers"]):
            errors.append("Borders returned after resume.")
        for value in (old, now):
            for layer in value["layers"]:
                layer["rotation_degrees"] = 0
    else:
        raise ValueError("Unknown dark portrait step.")
    if old != now:
        errors.append("Unrelated authored fields or stacking order changed.")
    return errors


class CaseAssessment(BaseModel):
    execution: int
    step: int
    name: str
    recorded_outcome: str
    status: Literal["passed", "failed", "not_assessed"] = "not_assessed"
    errors: list[str] = Field(default_factory=list)


class AssessmentReport(BaseModel):
    record_version: Literal[1] = 1
    project_id: str
    profile: Profile
    replay_sha256: str
    complete: bool = False
    passed: bool = False
    errors: list[str] = Field(default_factory=list)
    cases: list[CaseAssessment] = Field(default_factory=list)
    report_path: str | None = None


def _proposal(
    store: ProjectStore, project_id: str, replay: ReplayReport,
    result: StepResult, parent: str | None,
) -> ResolvedLayout:
    if result.proposal_id is None:
        raise CollageError("Proposal execution has no proposal ID.")
    directory = child(store.project_dir(project_id), "conversation", "proposals", result.proposal_id)
    proposal = Proposal.model_validate(read_json(child(directory, "proposal.json")))
    if proposal.proposal_id != result.proposal_id or proposal.parent != parent:
        raise CollageError("Proposal identity or parent does not match the replay.")
    controls = replay.sequence.canvas
    recipe = proposal.recipe
    if proposal.controls != controls or (recipe.canvas.width, recipe.canvas.height) != (
        controls.width, controls.height,
    ):
        raise CollageError("Proposal does not match the recorded canvas/controls.")
    if not controls.cropping and any(layer.mode != "whole" for layer in recipe.layers):
        raise CollageError("Proposal crops a photo while cropping is forbidden.")
    resolved = resolve_layout(recipe, store.load(project_id).photos, 1)
    if (
        proposal.geometry != resolved.geometry
        or proposal.recipe_digest != digest(canonical(recipe))
        or proposal.preview_digest != digest(child(directory, "preview.png").read_bytes())
    ):
        raise CollageError("Proposal geometry, recipe or preview identity mismatch.")
    return resolved


def assess(
    store: ProjectStore, project_id: str, *, profile: Profile = "integrity",
) -> AssessmentReport:
    root = child(store.project_dir(project_id), "replay")
    replay_path = child(root, "report.json")
    replay = ReplayReport.model_validate(read_json(replay_path))
    project = store.load(project_id)
    report = AssessmentReport(
        project_id=project_id, profile=profile, replay_sha256=digest(replay_path.read_bytes()),
    )
    if replay.project_id != project_id:
        report.errors.append("Replay project identity mismatch.")
    try:
        captured_instructions = child(root, "instructions.md").read_text(encoding="utf-8")
        if digest(captured_instructions.encode("utf-8")) != replay.instructions_sha256:
            report.errors.append("Captured instructions do not match the replay.")
        paths = store.photo_paths(project)
        if set(paths) != set(range(1, len(replay.sources) + 1)):
            report.errors.append("Replay source photos do not match the project.")
        else:
            for photo_id, source in enumerate(replay.sources, 1):
                if digest(paths[photo_id].read_bytes()) != source.sha256:
                    report.errors.append(f"Imported photo {photo_id} does not match its recorded hash.")
    except (OSError, UnicodeError) as exc:
        report.errors.append(f"Cannot read captured instructions or imported photos: {exc}")

    profile_matches = True
    if profile == "dark-portrait-adjustments":
        profile_matches = (
            [message.name for message in replay.sequence.messages]
            == ["initial", "resize", "remove-borders", "straighten"]
            and (replay.sequence.canvas.width, replay.sequence.canvas.height) == (1200, 1800)
            and {photo.photo_id for photo in project.photos} == {1, 2, 3, 4}
            and replay.sequence.messages[-1].reopen_before
        )
        if not profile_matches:
            report.errors.append(
                "The dark portrait profile requires its four named steps, a 1200x1800 "
                "four-photo canvas and reopening before straightening."
            )

    cursor = 0
    parent = None
    previous = None
    for number, result in enumerate(replay.executions, 1):
        case = CaseAssessment(
            execution=number, step=result.step, name=result.name, recorded_outcome=result.status,
        )
        report.cases.append(case)
        if (
            result.step != cursor or not 0 <= result.step < len(replay.sequence.messages)
            or result.name != replay.sequence.messages[result.step].name
            or result.prompt != replay.sequence.messages[result.step].prompt
            or result.reopened != replay.sequence.messages[result.step].reopen_before
        ):
            case.errors.append("Execution does not match the recorded message/cursor.")
        try:
            captured = StepResult.model_validate(read_json(
                child(root, "steps", f"{number:04d}", "result.json")
            ))
            if captured != result:
                case.errors.append("Per-execution result does not match the replay report.")
            if result.status == "proposal":
                current = _proposal(store, project_id, replay, result, parent)
                if profile == "dark-portrait-adjustments" and profile_matches and 0 <= result.step < 4:
                    case.errors.extend(dark_portrait_errors(result.step, current, previous))
                previous = current
                case.status = "failed" if case.errors else "passed"
            elif result.status in {"pending", "question"} and number != len(replay.executions):
                case.errors.append("Replay continued after an interrupted execution or question.")
        except (CollageError, ValidationError, OSError) as exc:
            case.errors.append(f"{type(exc).__name__}: {exc}")
            if result.status == "proposal":
                previous = None
        if case.errors:
            case.status = "failed"
        if result.status == "proposal":
            cursor += 1
            parent = result.proposal_id
    if replay.next_step != cursor:
        report.errors.append("Replay cursor does not match its successful proposal executions.")
    report.complete = (
        cursor == len(replay.sequence.messages) and replay.next_step == cursor
        and bool(replay.executions) and replay.executions[-1].status == "proposal"
    )
    if not report.complete:
        report.errors.append("Replay is incomplete; unexecuted messages have not been assessed.")
    report.passed = (
        report.complete and not report.errors
        and all(case.status != "failed" for case in report.cases)
    )
    return report


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
