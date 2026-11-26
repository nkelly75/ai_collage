"""Project-local request accounting, without cumulative usage allowances."""

import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from time import monotonic
from typing import Iterator

from pydantic import Field

from .files import child, save
from .models import Attempt, Limits, Reasoning, Record
from ..engine.models import CollageError
from ..engine.projects import ProjectStore, read_json


class CallBudget(Record):
    limit: int = Field(gt=0)
    used: int = Field(default=0, ge=0)


_active_budget: ContextVar[tuple[Path, int] | None] = ContextVar("call_budget", default=None)


@contextmanager
def call_budget(path: Path | None, limit: int = 200) -> Iterator[None]:
    """Optional single-writer pass guard; reopening never renews its allowance."""
    if path is None:
        yield
        return
    path = path.resolve()
    if path.exists():
        state = CallBudget.model_validate(read_json(path))
        if state.limit != limit or state.used > state.limit:
            raise CollageError("Outer call budget limit changed or its counter is inconsistent.")
    else:
        save(path, CallBudget(limit=limit))
    token = _active_budget.set((path, limit))
    try:
        yield
    finally:
        _active_budget.reset(token)


def _reserve_budget() -> None:
    active = _active_budget.get()
    if active is None:
        return
    path, limit = active
    state = CallBudget.model_validate(read_json(path))
    if state.limit != limit:
        raise CollageError("Outer call budget limit changed; no request dispatched.")
    if state.used >= limit:
        raise CollageError("Outer call budget exhausted; no request dispatched.")
    save(path, state.model_copy(update={"used": state.used + 1}))


class StageTimeout(CollageError):
    """A confirmed model-stage timeout, not a publication or generic I/O error."""


class WorkTimeout(CollageError):
    """An adapter's outer work envelope expired before publication."""


class RequestLog:
    def __init__(
        self, store: ProjectStore, project_id: str, *, generation_reasoning: Reasoning = "low",
        interpretation_reasoning: Reasoning = "high",
    ):
        if generation_reasoning not in {"high", "low"}:
            raise CollageError("Generation reasoning must be high or low.")
        if interpretation_reasoning not in {"high", "low"}:
            raise CollageError("Interpretation reasoning must be high or low.")
        self.root = child(store.project_dir(project_id), "conversation", "requests")
        self.limits = Limits()
        self.generation_reasoning = generation_reasoning
        self.interpretation_reasoning = interpretation_reasoning
        self.stage: str | None = None
        self._deadline: float | None = None
        self.work_deadline: float | None = None

    def check_work_deadline(self) -> None:
        if self.work_deadline is not None and monotonic() >= self.work_deadline:
            raise WorkTimeout("Application work deadline exhausted; check saved state before retrying.")

    def begin_stage(self, stage: str) -> None:
        if stage not in {"interpretation", "generation"}:
            raise CollageError("Unknown model stage.")
        self.stage = stage
        seconds = (
            self.limits.generation_timeout_seconds if stage == "generation"
            else self.limits.timeout_seconds
        )
        self._deadline = monotonic() + seconds

    def remaining_seconds(self) -> float:
        self.check_work_deadline()
        remaining = (
            self._deadline - monotonic() if self._deadline is not None
            else self.limits.timeout_seconds
        )
        if remaining <= 0:
            raise StageTimeout(f"{self.stage or 'Model'} stage deadline exhausted; no automatic retry.")
        return remaining

    def reasoning(self, stage: str | None = None) -> Reasoning:
        return (
            self.generation_reasoning if (stage or self.stage) == "generation"
            else self.interpretation_reasoning
        )

    def attempts(self) -> list[Attempt]:
        paths = sorted(self.root.glob("attempt-*.json"), key=lambda path: (len(path.name), path.name))
        records = []
        for number, path in enumerate(paths, 1):
            if path.name != f"attempt-{number:04d}.json":
                raise CollageError("Request log has an inconsistent attempt sequence.")
            record = Attempt.model_validate(read_json(child(self.root, path.name)))
            if record.number != number:
                raise CollageError("Request attempt identity mismatch.")
            records.append(record)
        return records

    def reserve(self, purpose: str, input_bound: int) -> Attempt:
        if input_bound > self.limits.input_tokens:
            raise CollageError(
                f"Input exceeds the conservative token bound ({input_bound:,} > "
                f"{self.limits.input_tokens:,}); no request was dispatched or allowance used. "
                "Shorten the request or start a fresh project. Saved proposals are unchanged."
            )
        records = self.attempts()
        attempt = Attempt(
            number=len(records) + 1, purpose=purpose, input_bound=input_bound,
            started=time.time(),
            stage=self.stage, reasoning_effort=self.reasoning() if self.stage else None,
            timeout_seconds=self.remaining_seconds(),
        )
        _reserve_budget()
        save(child(self.root, f"attempt-{attempt.number:04d}.json"), attempt)
        return attempt

    def finish(self, attempt: Attempt) -> None:
        path = child(self.root, f"attempt-{attempt.number:04d}.json")
        previous = Attempt.model_validate(read_json(path))
        if previous.status != "pending" or previous.number != attempt.number:
            raise CollageError("Attempt is not an outstanding reservation.")
        save(path, attempt)
        limits = self.limits
        if (
            (attempt.input_tokens is not None and attempt.input_tokens > limits.input_tokens)
            or (attempt.output_tokens is not None and attempt.output_tokens > limits.output_tokens)
        ):
            raise CollageError("Provider usage exceeded a per-request limit; request stopped.")

    def summary(self) -> dict[str, object]:
        records = self.attempts()
        return {
            "requests_path": str(self.root),
            "attempts": len(records),
            "input_tokens": sum(item.input_tokens or 0 for item in records),
            "output_tokens": sum(item.output_tokens or 0 for item in records),
            "unknown_usage_attempts": [
                item.number for item in records
                if item.input_tokens is None or item.output_tokens is None
            ],
        }
