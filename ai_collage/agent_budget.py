"""A shared persistent request ledger, never an implicit new allowance."""

import time
from pathlib import Path

from .agent_files import child, save
from .agent_models import Attempt, Limits, RunConfig
from .models import CollageError, validate_project_id
from .projects import ProjectStore, read_json


class RunLedger:
    def __init__(self, store: ProjectStore, run_id: str):
        validate_project_id(run_id)
        self.root = child(store.owner_dir, "agent-runs", run_id)
        self.path = child(self.root, "run.json")
        self.config = RunConfig.model_validate(read_json(self.path))
        if self.config.run_id != run_id:
            raise CollageError("Run ledger identity mismatch.")

    @classmethod
    def provision(
        cls, store: ProjectStore, run_id: str, limits: Limits | None = None,
    ) -> "RunLedger":
        validate_project_id(run_id)
        root = child(store.owner_dir, "agent-runs", run_id)
        root.mkdir(parents=True, exist_ok=False)
        save(child(root, "run.json"), RunConfig(run_id=run_id, limits=limits or Limits()))
        return cls(store, run_id)

    def attempts(self) -> list[Attempt]:
        paths = sorted(self.root.glob("attempt-*.json"))
        records = []
        for number, path in enumerate(paths, 1):
            if path.name != f"attempt-{number:04d}.json":
                raise CollageError("Run ledger has an inconsistent attempt sequence.")
            record = Attempt.model_validate(read_json(child(self.root, path.name)))
            if record.number != number:
                raise CollageError("Run attempt identity mismatch.")
            records.append(record)
        if len(records) > self.config.limits.max_attempts:
            raise CollageError("Run ledger exceeds its approved allowance.")
        return records

    def reserve(self, purpose: str, input_bound: int) -> Attempt:
        self.check_available()
        if input_bound > self.config.limits.input_tokens:
            raise CollageError("Input exceeds the conservative token bound; history was not truncated.")
        records = self.attempts()
        attempt = Attempt(
            number=len(records) + 1, purpose=purpose, input_bound=input_bound,
            started=time.time(),
        )
        save(child(self.root, f"attempt-{attempt.number:04d}.json"), attempt)
        return attempt

    def check_available(self) -> None:
        self.config = RunConfig.model_validate(read_json(self.path))
        if self.config.halted:
            raise CollageError("This run is halted pending review.")
        records = self.attempts()
        if len(records) >= self.config.limits.max_attempts:
            raise CollageError("Run request allowance exhausted; no request was sent.")

    def finish(self, attempt: Attempt) -> None:
        path = child(self.root, f"attempt-{attempt.number:04d}.json")
        previous = Attempt.model_validate(read_json(path))
        if previous.status != "pending" or previous.number != attempt.number:
            raise CollageError("Attempt is not an outstanding reservation.")
        save(path, attempt)
        limits = self.config.limits
        if (
            (attempt.input_tokens is not None and attempt.input_tokens > limits.input_tokens)
            or (attempt.output_tokens is not None and attempt.output_tokens > limits.output_tokens)
        ):
            save(self.path, self.config.model_copy(update={"halted": True}))
            raise CollageError("Provider usage exceeded a verified bound; run halted.")

    def summary(self) -> dict[str, object]:
        records = self.attempts()
        return {
            "run_id": self.config.run_id,
            "attempts": len(records),
            "limit": self.config.limits.max_attempts,
            "input_tokens": sum(item.input_tokens or 0 for item in records),
            "output_tokens": sum(item.output_tokens or 0 for item in records),
            "unknown_usage_attempts": [
                item.number for item in records
                if item.input_tokens is None or item.output_tokens is None
            ],
        }
