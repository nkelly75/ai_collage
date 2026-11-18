"""Fixed checkpoint A evaluation; never an autonomous search for nicer layouts."""

import argparse
import asyncio
import json
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from .agent_budget import RunLedger
from .agent_files import canonical, child, digest, save
from .conversation import Conversation
from .models import CollageError, ResolvedLayout
from .geometry import resolve_layout
from .projects import ProjectStore

PROMPTS = (
    "Make a collage with a dark grey background. Make photo 2 smaller than the others.",
    "Make photo 2 a bit smaller. Keep it in the same spot and leave the rest alone.",
    "Remove the borders. Leave everything else alone.",
    "Make all the photos straight. Keep everything else as it is.",
)


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


def compare(step: int, current: ResolvedLayout, previous: ResolvedLayout | None) -> list[str]:
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
                    layer["box"] = None
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
        raise ValueError("Unknown evaluation step.")
    if old != now:
        errors.append("Unrelated authored fields or stacking order changed.")
    return errors


class CaseResult(BaseModel):
    prompt: str
    status: str = "not_reached"
    proposal_id: str | None = None
    preview_path: str | None = None
    errors: list[str] = Field(default_factory=list)
    measurements: dict[str, object] = Field(default_factory=dict)


class EvaluationReport(BaseModel):
    project_id: str
    cases: list[CaseResult]
    acceptance_checked: bool = False
    run: dict[str, object] = Field(default_factory=dict)
    stopping_reason: str | None = None


async def evaluate(store: ProjectStore, project_id: str, ledger: RunLedger) -> EvaluationReport:
    from .agent_provider import FoundryModel

    report = EvaluationReport(
        project_id=project_id, cases=[CaseResult(prompt=prompt) for prompt in PROMPTS]
    )
    report_path = child(store.project_dir(project_id), "evaluation-report.json")
    if report_path.exists():
        raise CollageError("Evaluation evidence already exists; use a fresh evaluation project.")
    conversation = Conversation(store, project_id, canvas=(1200, 1800))
    project = store.load(project_id)
    if len(project.photos) != 4 or project.current_version is not None or conversation.state.history:
        raise CollageError("Evaluation requires a fresh, unaccepted four-photo project.")
    prefs_path = child(store.owner_dir, "preferences.json")
    prefs_digest = digest(prefs_path.read_bytes())
    previous = None
    client = FoundryModel()
    for step, prompt in enumerate(PROMPTS):
        if step == 3:
            conversation = Conversation(store, project_id)
        result = report.cases[step]
        try:
            proposal_id = await conversation.request(prompt, client, ledger)
            if proposal_id != conversation.state.baseline:
                raise CollageError("Core live case returned a question instead of a recipe.")
            proposal = conversation.proposal(proposal_id)
            resolved = resolve_layout(proposal.recipe, project.photos, 1)
            result.proposal_id = proposal_id
            result.preview_path = str(conversation.preview_path(proposal_id))
            result.measurements = {
                "outer_frames": {
                    str(item.photo_id): {
                        "width": item.box_pixels.width, "height": item.box_pixels.height,
                        "area": item.box_pixels.width * item.box_pixels.height,
                        "centre_x": item.box_pixels.x + item.box_pixels.width / 2,
                        "centre_y": item.box_pixels.y + item.box_pixels.height / 2,
                    } for item in resolved.geometry
                }
            }
            if step == 1 and previous is not None:
                before = next(item.box_pixels for item in previous.geometry if item.photo_id == 2)
                after = next(item.box_pixels for item in resolved.geometry if item.photo_id == 2)
                result.measurements["photo_2_change"] = {
                    "width_before": before.width, "width_after": after.width,
                    "width_change": after.width - before.width,
                    "area_before": before.width * before.height,
                    "area_after": after.width * after.height,
                    "area_change": after.width * after.height - before.width * before.height,
                    "centre_x_change": after.x + after.width / 2 - before.x - before.width / 2,
                    "centre_y_change": after.y + after.height / 2 - before.y - before.height / 2,
                }
            result.errors = compare(step, resolved, previous)
            if store.load(project_id).current_version is not None:
                result.errors.append("A proposal changed the accepted current version.")
            if digest(prefs_path.read_bytes()) != prefs_digest:
                result.errors.append("Remembered preferences changed.")
            result.status = "failed" if result.errors else "passed"
            previous = resolved
        except (CollageError, ValidationError, OSError) as exc:
            result.status = "failed"
            result.errors.append(str(exc))
            report.stopping_reason = str(exc)
            report.run = ledger.summary()
            save(report_path, report)
            return report
        report.run = ledger.summary()
        save(report_path, report)
    assert conversation.state.baseline is not None
    before_calls = len(ledger.attempts())
    try:
        chosen = conversation.proposal(conversation.state.baseline)
        version = conversation.accept(chosen.proposal_id)
        accepted = store.load_layout(store.load(project_id), version)
        _, accepted_png = store.version_paths(project_id, version)
        report.acceptance_checked = (
            canonical(accepted.recipe) == canonical(chosen.recipe)
            and digest(accepted_png.read_bytes()) == chosen.preview_digest
            and len(ledger.attempts()) == before_calls
        )
        report.stopping_reason = "Core sequence completed; see individual checks."
    except (CollageError, ValidationError, OSError) as exc:
        report.stopping_reason = f"Acceptance check stopped: {exc}"
    report.run = ledger.summary()
    save(report_path, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(".collage-data-step2"))
    parser.add_argument("--project", required=True)
    parser.add_argument("--run", choices=["step2-first-pass"], default="step2-first-pass")
    parser.add_argument("--provision-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        store = ProjectStore(args.data_dir)
        if args.provision_run:
            RunLedger.provision(store, args.run)
        ledger = RunLedger(store, args.run)
        report = asyncio.run(evaluate(store, args.project, ledger))
        print(report.model_dump_json(indent=2))
        return 0 if all(case.status == "passed" for case in report.cases) and report.acceptance_checked else 1
    except (CollageError, ValidationError, OSError) as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
