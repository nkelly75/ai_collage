"""Replay JSON-defined conversations, without evaluating or accepting layouts."""

import argparse
import asyncio
from pathlib import Path
import sys
import time
from typing import Annotated, Literal

from pydantic import BaseModel, Field, RootModel, ValidationError, model_validator

from .agent_requests import RequestLog, call_budget
from .agent_files import canonical, child, digest, save
from .agent_models import Controls, Digest, Exchange, LayoutSource, Record, ResolvedIntent
from .agent_provider import FoundryModel, instruction_bundle
from .conversation import Conversation, ModelClient
from .models import MAX_FILE_BYTES, CollageError
from .projects import ProjectStore, read_json

Name = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")]


class Message(Record):
    name: Name
    prompt: Annotated[str, Field(min_length=1, pattern=r"\S")]
    reopen_before: bool = False


class Sequence(Record):
    name: Name
    images: Annotated[list[str], Field(min_length=2, max_length=6)]
    canvas: Controls
    messages: Annotated[list[Message], Field(min_length=1)]

    @model_validator(mode="after")
    def unique_names(self) -> "Sequence":
        if len({message.name for message in self.messages}) != len(self.messages):
            raise ValueError("Message names must be unique.")
        if any(not image.strip() for image in self.images):
            raise ValueError("Image paths must be nonempty.")
        return self


class Source(Record):
    path: str
    sha256: Digest


class Change(BaseModel):
    field: str
    before: object
    after: object


class StepResult(BaseModel):
    model_config = {**Record.model_config, "frozen": False}
    record_version: Literal[3] = 3
    step: int
    name: str
    prompt: str
    reopened: bool
    status: Literal["pending", "proposal", "selection", "question", "acknowledgement", "failed"] = "pending"
    baseline_before: str | None = None
    source: LayoutSource | None = None
    intent: ResolvedIntent | None = None
    event_id: int | None = None
    answer: str | None = None
    answer_origin: Literal["user", "copilot"] | None = None
    answers_execution: int | None = None
    proposal_id: str | None = None
    proposal_path: str | None = None
    preview_path: str | None = None
    question: str | None = None
    acknowledgement: str | None = None
    error: str | None = None
    contexts: list[str] = Field(default_factory=list)
    changes: list[Change] = Field(default_factory=list)
    usage_before: dict[str, object]
    usage_after: dict[str, object] = Field(default_factory=dict)
    attempts: int = 0
    validation_corrections: int = 0
    duration_seconds: float = 0


class ReplayReport(BaseModel):
    model_config = {**Record.model_config, "frozen": False}
    record_version: Literal[3] = 3
    project_id: str
    sequence: Sequence
    sources: list[Source]
    requests_path: str | None = None
    instructions_sha256: Digest
    conversation_sha256: Digest
    next_step: int = 0
    executions: list[StepResult] = Field(default_factory=list)


def authored_changes(before: object, after: object, path: str = "recipe") -> list[Change]:
    if isinstance(before, dict) and isinstance(after, dict):
        return [
            change
            for key in sorted(before.keys() | after.keys())
            for change in authored_changes(before.get(key), after.get(key), f"{path}.{key}")
        ]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [
            change
            for index, (old, new) in enumerate(zip(before, after, strict=True))
            for change in authored_changes(old, new, f"{path}[{index}]")
        ]
    return [] if before == after else [Change(field=path, before=before, after=after)]


def load_sequence(path: Path) -> tuple[Sequence, list[Source]]:
    sequence = Sequence.model_validate(read_json(path))
    sources = []
    for image in sequence.images:
        source = (path.resolve().parent / image).resolve()
        if source.stat().st_size > MAX_FILE_BYTES:
            raise CollageError(f"{source}: photo exceeds the 25 MiB file limit.")
        sources.append(Source(path=str(source), sha256=digest(source.read_bytes())))
    return sequence, sources


async def replay(
    store: ProjectStore, project_id: str, sequence_path: Path, *,
    resume: bool = False, remaining: bool = False, retry: bool = False,
    answer: str | None = None, answer_origin: Literal["user", "copilot"] | None = None,
    client: ModelClient | None = None,
) -> ReplayReport:
    sequence, sources = load_sequence(sequence_path)
    assembled = instruction_bundle()
    instruction_hash = digest(assembled.encode("utf-8"))
    root = child(store.project_dir(project_id), "replay")
    requests = RequestLog(store, project_id)
    report_path = child(root, "report.json")
    if retry and not resume:
        raise CollageError("--retry requires --resume.")
    if answer is not None:
        if not resume or retry or not answer.strip() or answer_origin is None:
            raise CollageError("An answer requires --resume and an explicit origin, without --retry.")
    elif answer_origin is not None:
        raise CollageError("An answer origin requires an answer.")
    answers_execution = None
    if resume:
        report = ReplayReport.model_validate(read_json(report_path))
        if (
            report.project_id != project_id or report.sources != sources
            or report.sequence.name != sequence.name or report.sequence.canvas != sequence.canvas
            or report.instructions_sha256 != instruction_hash
        ):
            raise CollageError("Replay identity, sources, controls or instructions changed.")
        locked = max((item.step + 1 for item in report.executions), default=0)
        if sequence.messages[:locked] != report.sequence.messages[:locked]:
            raise CollageError("Previously attempted messages changed; use a fresh replay project.")
        if (
            not 0 <= report.next_step <= len(sequence.messages)
            or report.next_step != sum(
                item.status in {"proposal", "selection", "acknowledgement"} for item in report.executions
            )
        ):
            raise CollageError("Replay cursor is inconsistent.")
        conversation = Conversation(store, project_id)
        if digest(canonical(conversation.state)) != report.conversation_sha256:
            raise CollageError("Conversation changed outside the replay; inspect before continuing.")
        if report.executions and report.executions[-1].status not in {
            "proposal", "selection", "acknowledgement",
        }:
            last = report.executions[-1]
            if last.status == "question":
                if answer is None:
                    raise CollageError("Replay paused for a question; supply --answer and --answer-origin.")
                answered = {
                    item.answers_execution for item in report.executions
                    if item.step == report.next_step and item.answer is not None
                }
                if len(answered) >= 2:
                    raise CollageError("Two clarification answers already attempted for this step.")
                answers_execution = len(report.executions)
            elif last.status == "pending":
                raise CollageError("Interrupted replay step; inspect evidence before any further calls.")
            else:
                if answer is not None or not retry:
                    raise CollageError("Previous step failed; an explicit --resume --retry is required.")
                answer, answer_origin = last.answer, last.answer_origin
                answers_execution = last.answers_execution
        elif retry or answer is not None:
            raise CollageError("There is no failed step to retry or question to answer.")
        report.sequence = sequence
    else:
        if store.project_dir(project_id).exists():
            raise CollageError("Project already exists; use --resume or a fresh project ID.")
        store.create(project_id, [Path(source.path) for source in sources])
        conversation = Conversation(
            store, project_id, canvas=(sequence.canvas.width, sequence.canvas.height)
        )
        if sequence.canvas.cropping:
            conversation.controls(sequence.canvas)
        report = ReplayReport(
            project_id=project_id, sequence=sequence, sources=sources,
            instructions_sha256=instruction_hash,
            conversation_sha256=digest(canonical(conversation.state)),
        )
        save(report_path, report)
        child(root, "instructions.md").write_text(assembled, encoding="utf-8")
    report.requests_path = str(requests.root)
    end = len(sequence.messages) if remaining else min(report.next_step + 1, len(sequence.messages))
    while report.next_step < end:
        message = sequence.messages[report.next_step]
        if message.reopen_before:
            conversation = Conversation(store, project_id)
        baseline_before = conversation.state.baseline
        history_start = len(conversation.history())
        before_attempts = len(requests.attempts())
        result = StepResult(
            step=report.next_step, name=message.name, prompt=message.prompt,
            reopened=message.reopen_before, usage_before=requests.summary(),
            baseline_before=baseline_before, answer=answer, answer_origin=answer_origin,
            answers_execution=answers_execution,
        )
        directory = child(root, "steps", f"{len(report.executions) + 1:04d}")
        directory.mkdir(parents=True, exist_ok=False)
        save(child(directory, "sequence.json"), sequence)
        report.executions.append(result)
        save(report_path, report)
        save(child(directory, "result.json"), result)

        class RecordedModel:
            async def complete(
                self, context: dict[str, object], current_requests: RequestLog, purpose: str,
            ) -> str:
                if digest(instruction_bundle().encode("utf-8")) != report.instructions_sha256:
                    raise CollageError("Instructions changed; no further model request was sent.")
                path = child(directory, f"context-{len(result.contexts) + 1:04d}.json")
                save(path, RootModel[dict[str, object]](context))
                result.contexts.append(str(path))
                provider = client if client is not None else FoundryModel()
                try:
                    return await provider.complete(context, current_requests, purpose)
                finally:
                    save(path, RootModel[dict[str, object]](context))

        started = time.monotonic()
        try:
            reply = await conversation.request(
                answer if answer is not None else message.prompt, RecordedModel(), requests,
            )
            event = conversation.history()[-1]
            if not isinstance(event, Exchange) or conversation.state.history[-1] != reply.event_id:
                raise CollageError("Request outcome does not match the recorded conversation event.")
            result.event_id = reply.event_id
            result.intent = event.intent
            result.source = event.intent.source if event.intent else None
            if reply.kind == "question" and event.outcome == "question":
                result.status = "question"
                result.question = reply.question
            elif reply.kind == "acknowledgement" and event.outcome == "acknowledgement":
                result.status = "acknowledgement"
                result.acknowledgement = reply.acknowledgement
            elif (
                event.outcome in {"proposal", "selection"} and event.outcome == reply.kind
                and event.proposal_id == reply.proposal_id
            ):
                assert reply.proposal_id is not None
                proposal = conversation.proposal(reply.proposal_id)
                result.status = reply.kind
                result.proposal_id = reply.proposal_id
                result.preview_path = str(conversation.preview_path(reply.proposal_id))
                result.proposal_path = str(child(
                    conversation.preview_path(reply.proposal_id).parent, "proposal.json",
                ))
                source_recipe = conversation.source_recipe(result.source)
                if result.status == "proposal" and source_recipe is not None:
                    result.changes = authored_changes(
                        source_recipe.model_dump(mode="json"), proposal.recipe.model_dump(mode="json")
                    )
            else:
                raise CollageError("Request outcome does not match the recorded conversation event.")
            if (
                store.load(project_id).current_version is not None
                or conversation.state.accepted_proposal is not None
            ):
                raise CollageError("Replay unexpectedly changed acceptance; stop and inspect.")
            if result.status in {"proposal", "selection", "acknowledgement"}:
                report.next_step += 1
        except (CollageError, ValidationError, OSError) as exc:
            result.status = "failed"
            result.error = f"{type(exc).__name__}: {exc}"
        finally:
            new_events = conversation.history()[history_start:]
            if new_events and isinstance(new_events[-1], Exchange):
                last_event = new_events[-1]
                result.event_id = conversation.state.history[-1]
                result.intent = last_event.intent
                result.source = last_event.intent.source if last_event.intent else None
            result.duration_seconds = time.monotonic() - started
            result.usage_after = requests.summary()
            result.attempts = len(requests.attempts()) - before_attempts
            result.validation_corrections = sum(
                isinstance(event, Exchange) and event.outcome == "invalid"
                for event in new_events
            )
            report.conversation_sha256 = digest(canonical(conversation.state))
            save(child(directory, "result.json"), result)
            save(report_path, report)
        if result.status not in {"proposal", "selection", "acknowledgement"}:
            break
        answer = answer_origin = answers_execution = None
    return report


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
    parser.add_argument("--answer", help="Supplement the pending question; do not replace the script.")
    parser.add_argument("--answer-origin", choices=["user", "copilot"])
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
            ))
        print(report.model_dump_json(indent=2))
        return 0 if report.executions[-1].status in {"proposal", "selection", "acknowledgement"} else 1
    except (CollageError, ValidationError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
