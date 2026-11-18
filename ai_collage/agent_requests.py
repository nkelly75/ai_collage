"""Project-local request accounting, without cumulative usage allowances."""

import time
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Iterator

from pydantic import Field

from .agent_files import child, save
from .agent_models import Attempt, Limits, Record
from .models import CollageError
from .projects import ProjectStore, read_json


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


class RequestLog:
    def __init__(self, store: ProjectStore, project_id: str):
        self.root = child(store.project_dir(project_id), "conversation", "requests")
        self.limits = Limits()

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
            raise CollageError("Input exceeds the conservative token bound; history was not truncated.")
        records = self.attempts()
        attempt = Attempt(
            number=len(records) + 1, purpose=purpose, input_bound=input_bound,
            started=time.time(),
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
