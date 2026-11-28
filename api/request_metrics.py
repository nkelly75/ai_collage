"""Opt-in local request diagnostics, not a call budget or cloud telemetry."""

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import threading
from time import perf_counter
from uuid import uuid4

from ai_collage.application.projects import FlowError


_write_lock = threading.Lock()
_read_depth: ContextVar[int] = ContextVar("metrics_blob_read_depth", default=0)


def configured_path() -> Path | None:
    value = os.environ.get("AI_COLLAGE_METRICS_PATH")
    if value is None:
        return None
    try:
        path = Path(value)
        if (
            not value or not path.is_absolute() or path.suffix.lower() != ".jsonl"
            or not path.parent.is_dir() or (path.exists() and not path.is_file())
        ):
            raise FlowError("configuration_error", "Metrics require an absolute .jsonl file in an existing directory.", 500)
        for name in ("AI_COLLAGE_CALL_BUDGET_PATH", "AI_COLLAGE_BLOB_PROOF_LEDGER"):
            reserved = os.environ.get(name)
            if not reserved:
                continue
            protected = [Path(reserved)]
            if name == "AI_COLLAGE_BLOB_PROOF_LEDGER":
                protected.append(Path(reserved).with_suffix(".objects.jsonl"))
            if any(path.resolve() == other.resolve() for other in protected):
                raise FlowError("configuration_error", "Metrics must not share a call-budget or proof ledger.", 500)
    except (OSError, ValueError) as exc:
        raise FlowError("configuration_error", "Metrics output path is invalid or inaccessible.", 500) from exc
    return path


@dataclass
class RequestMetrics:
    path: Path
    method: str
    route: str
    identifier: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started: float = field(default_factory=perf_counter)
    status: int | None = None
    response_bytes: int | None = None
    blob_requests: int = 0
    blob_read_seconds: float = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def count_blob_request(self) -> None:
        with self._lock:
            self.blob_requests += 1

    @contextmanager
    def blob_read(self):
        depth = _read_depth.get()
        token = _read_depth.set(depth + 1)
        started = perf_counter()
        try:
            yield
        finally:
            _read_depth.reset(token)
            if depth == 0:
                with self._lock:
                    self.blob_read_seconds += perf_counter() - started

    def complete(self, status: int, response_bytes: int) -> None:
        self.status = status
        self.response_bytes = response_bytes

    def write(self) -> None:
        elapsed = perf_counter() - self.started
        backend = os.environ.get("AI_COLLAGE_STORAGE_BACKEND", "local").lower()
        with self._lock:
            record = {
                "metrics_version": 1,
                "request_id": self.identifier,
                "timestamp": self.timestamp,
                "method": self.method,
                "route": self.route,
                "backend": backend if backend in {"local", "blob"} else "invalid",
                "status": self.status,
                "handler_ms": round(elapsed * 1000, 3),
                "response_bytes": self.response_bytes,
                "blob_requests": self.blob_requests,
                "blob_read_ms": round(self.blob_read_seconds * 1000, 3),
            }
        try:
            with _write_lock, self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, separators=(",", ":")) + "\n")
        except OSError:
            logging.exception("Request metrics write failed; this request's timing was not recorded.")


_current: ContextVar[RequestMetrics | None] = ContextVar("request_metrics", default=None)


def current() -> RequestMetrics | None:
    return _current.get()


@contextmanager
def measure_request(method: str, route: str):
    path = configured_path()
    if path is None:
        yield None
        return
    metrics = RequestMetrics(path, method, route)
    token = _current.set(metrics)
    try:
        yield metrics
    finally:
        _current.reset(token)
        metrics.write()
