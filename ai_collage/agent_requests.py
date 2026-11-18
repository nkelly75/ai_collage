"""Project-local request accounting, without cumulative usage allowances."""

import time

from .agent_files import child, save
from .agent_models import Attempt, Limits
from .models import CollageError
from .projects import ProjectStore, read_json


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
