"""Assess saved replay evidence offline; never generate or accept a layout."""

import argparse
from pathlib import Path
import sys
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from .agent_files import canonical, child, digest, save
from .agent_models import (
    HISTORY, INTENT, Attempt, ConversationState, Exchange, Proposal, QuestionIntent, RememberIntent,
)
from .geometry import resolve_layout
from .models import CollageError, ResolvedLayout
from .projects import ProjectStore, read_json
from .photo_references import name_history
from .replay import ReplayReport, StepResult, authored_changes

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
    """Check dark portrait edits, allowing near-white borders."""
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
                or any(int(layer.border.color[index:index + 2], 16) < 240 for index in (1, 3, 5))
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
    record_version: Literal[3] = 3
    project_id: str
    profile: Profile
    replay_sha256: str
    complete: bool = False
    passed: bool = False
    clarification_assisted: bool = False
    errors: list[str] = Field(default_factory=list)
    cases: list[CaseAssessment] = Field(default_factory=list)
    report_path: str | None = None


def _proposal(
    store: ProjectStore, project_id: str, replay: ReplayReport,
    result: StepResult,
) -> ResolvedLayout:
    if result.proposal_id is None:
        raise CollageError("Proposal execution has no proposal ID.")
    directory = child(store.project_dir(project_id), "conversation", "proposals", result.proposal_id)
    proposal = Proposal.model_validate(read_json(child(directory, "proposal.json")))
    parent = proposal.intent.source.proposal_id if proposal.intent.source else None
    if proposal.proposal_id != result.proposal_id or proposal.parent != parent:
        raise CollageError("Proposal identity or parent does not match the replay.")
    if result.status == "proposal" and (
        proposal.intent != result.intent or proposal.intent.source != result.source
        or proposal.turn_id != result.event_id
    ):
        raise CollageError("Proposal source/task provenance does not match the replay.")
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
    baseline = None
    published: dict[str, ResolvedLayout] = {}
    state = ConversationState.model_validate(read_json(child(
        store.project_dir(project_id), "conversation", "state.json",
    )))
    events = {
        number: HISTORY.validate_python(read_json(child(
            store.project_dir(project_id), "conversation", "events", f"{number:06d}.json",
        ))) for number in state.history
    }
    if project.current_version is not None or state.accepted_proposal is not None:
        report.errors.append("Replay changed acceptance.")
    if digest(canonical(state)) != replay.conversation_sha256:
        report.errors.append("Conversation state does not match the recorded replay identity.")
    try:
        name_history(state.photo_names, events, {photo.photo_id for photo in project.photos})
    except CollageError as exc:
        report.errors.append(str(exc))
    previous_attempts = 0
    for number, result in enumerate(replay.executions, 1):
        case = CaseAssessment(
            execution=number, step=result.step, name=result.name, recorded_outcome=result.status,
        )
        report.cases.append(case)
        if result.baseline_before != baseline:
            case.errors.append("Execution baseline does not match the previous outcome.")
        if (
            result.step != cursor or not 0 <= result.step < len(replay.sequence.messages)
            or result.name != replay.sequence.messages[result.step].name
            or result.prompt != replay.sequence.messages[result.step].prompt
            or result.reopened != replay.sequence.messages[result.step].reopen_before
        ):
            case.errors.append("Execution does not match the recorded message/cursor.")
        try:
            if result.answer is not None:
                report.clarification_assisted = True
                reference = result.answers_execution
                if (
                    result.answer_origin not in {"user", "copilot"}
                    or reference is None or not 1 <= reference < number
                ):
                    case.errors.append("Clarification answer has no valid provenance.")
                else:
                    question = replay.executions[reference - 1]
                    preceding = replay.executions[number - 2]
                    repeated_answer = (
                        preceding.status == "failed"
                        and preceding.answers_execution == reference
                        and preceding.answer == result.answer
                        and preceding.answer_origin == result.answer_origin
                    )
                    if (
                        question.status != "question" or question.step != result.step
                        or (reference != number - 1 and not repeated_answer)
                    ):
                        case.errors.append("Answer does not continue the pending question.")
                answered = {
                    item.answers_execution for item in replay.executions[:number]
                    if item.step == result.step and item.answer is not None
                }
                if len(answered) > 2:
                    case.errors.append("Clarification-answer limit exceeded.")
            elif result.answer_origin is not None or result.answers_execution is not None:
                case.errors.append("Clarification provenance has no answer.")
            captured = StepResult.model_validate(read_json(
                child(root, "steps", f"{number:04d}", "result.json")
            ))
            if captured != result:
                case.errors.append("Per-execution result does not match the replay report.")
            before = result.usage_before.get("attempts")
            after = result.usage_after.get("attempts")
            if (
                type(before) is not int or type(after) is not int
                or before != previous_attempts or after - before != result.attempts
                or not 0 <= result.attempts <= len(result.contexts) <= 4
            ):
                raise CollageError("Execution call accounting is inconsistent.")
            previous_attempts = after
            stages = []
            for index, context_path in enumerate(result.contexts, 1):
                expected_path = child(root, "steps", f"{number:04d}", f"context-{index:04d}.json")
                if Path(context_path).resolve() != expected_path.resolve():
                    raise CollageError("Captured context path is outside its execution.")
                context = read_json(expected_path)
                if not isinstance(context, dict) or context.get("stage") not in {
                    "interpretation", "generation",
                }:
                    raise CollageError("Captured context has no valid stage.")
                stage = context["stage"]
                stages.append(stage)
                if (
                    context.get("user_request") != (
                        result.answer if result.answer is not None else result.prompt
                    )
                    or context.get("trusted_controls") != replay.sequence.canvas.model_dump(mode="json")
                    or (
                        stage == "generation"
                        and context.get("resolved_intent") != (
                            result.intent.model_dump(mode="json") if result.intent else None
                        )
                    )
                ):
                    raise CollageError("Captured stage context does not match the execution.")
            interpretations = stages.count("interpretation")
            if (
                not 1 <= interpretations <= 2
                or stages != ["interpretation"] * interpretations
                + ["generation"] * (len(stages) - interpretations)
                or (result.status in {"selection", "question", "acknowledgement"} and "generation" in stages)
                or (result.status == "proposal" and "generation" not in stages)
            ):
                raise CollageError("Execution stage order or limits are inconsistent.")
            for index in range(before + 1, after + 1):
                attempt = Attempt.model_validate(read_json(child(
                    store.project_dir(project_id), "conversation", "requests",
                    f"attempt-{index:04d}.json",
                )))
                if attempt.number != index or attempt.purpose != f"{project_id}: {stages[index - before - 1]}":
                    raise CollageError("Request accounting does not match the captured stages.")
            if result.status in {"proposal", "selection", "question", "acknowledgement"}:
                event = events.get(result.event_id)
                if (
                    not isinstance(event, Exchange)
                    or event.outcome != result.status or event.proposal_id != result.proposal_id
                    or event.intent != result.intent
                    or event.prompt != (result.answer if result.answer is not None else result.prompt)
                ):
                    case.errors.append("Conversation event does not match the execution outcome.")
                elif result.status == "question":
                    question_reply = INTENT.validate_json(event.response or "")
                    if not isinstance(question_reply, QuestionIntent) or question_reply.question != result.question:
                        case.errors.append("Recorded question does not match its conversation event.")
                elif result.status == "acknowledgement":
                    reply = INTENT.validate_json(event.response or "")
                    expected = "Remembered: " + "; ".join(
                        f"{item.name} = photo {item.photo_id}" for item in event.name_updates
                    ) + "."
                    if (
                        not isinstance(reply, RememberIntent) or not event.name_updates
                        or result.acknowledgement != expected or result.intent is not None
                        or result.source is not None or result.changes
                        or result.preview_path is not None or result.proposal_path is not None
                    ):
                        case.errors.append("Acknowledgement does not match a naming-only update.")
                    if profile == "dark-portrait-adjustments":
                        case.errors.append("Historical profile requires a generated proposal.")
                    case.status = "failed" if case.errors else "passed"
            if result.status in {"proposal", "selection"}:
                if result.intent is None or result.source != result.intent.source:
                    raise CollageError("Successful execution has no matching resolved intent.")
                if result.source is not None and (
                    result.source.accepted_version is not None
                    or result.source.proposal_id not in published
                ):
                    raise CollageError("Execution source was not published before this step.")
                current = _proposal(store, project_id, replay, result)
                previous = published.get(result.source.proposal_id) if result.source else None
                expected_changes = (
                    authored_changes(
                        previous.recipe.model_dump(mode="json"), current.recipe.model_dump(mode="json"),
                    ) if previous is not None and result.status == "proposal" else []
                )
                if result.changes != expected_changes:
                    case.errors.append("Authored differences do not match the actual edit source.")
                if result.status == "selection":
                    if (
                        result.proposal_id not in published or result.intent.action != "select"
                        or result.source is None or result.source.proposal_id != result.proposal_id
                    ):
                        case.errors.append("Selection is not an exact previously published proposal.")
                else:
                    if result.proposal_id in published or result.intent.action == "select":
                        case.errors.append("Generation identity/action is inconsistent.")
                    assert result.proposal_id is not None
                    published[result.proposal_id] = current
                if profile == "dark-portrait-adjustments" and profile_matches and 0 <= result.step < 4:
                    if result.status != "proposal":
                        case.errors.append("Historical profile requires a generated proposal.")
                    else:
                        case.errors.extend(dark_portrait_errors(result.step, current, previous))
                case.status = "failed" if case.errors else "passed"
            elif result.status == "pending" and number != len(replay.executions):
                case.errors.append("Replay continued after an interrupted execution.")
            elif result.status == "question" and number != len(replay.executions):
                following = replay.executions[number]
                if following.answers_execution != number or following.answer is None:
                    case.errors.append("Replay continued without answering its pending question.")
        except (CollageError, ValidationError, OSError) as exc:
            case.errors.append(f"{type(exc).__name__}: {exc}")
        if case.errors:
            case.status = "failed"
        if result.status in {"proposal", "selection"}:
            cursor += 1
            baseline = result.proposal_id
        elif result.status == "acknowledgement":
            cursor += 1
    if replay.next_step != cursor:
        report.errors.append("Replay cursor does not match its successful executions.")
    if state.baseline != baseline:
        report.errors.append("Conversation baseline does not match the replay outcomes.")
    report.complete = (
        cursor == len(replay.sequence.messages) and replay.next_step == cursor
        and bool(replay.executions) and replay.executions[-1].status in {
            "proposal", "selection", "acknowledgement",
        }
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
