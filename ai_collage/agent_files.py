"""Bounded, atomic local record IO under the single-writer assumption."""

import hashlib
import os
import tempfile
from pathlib import Path

from pydantic import BaseModel

from .models import MAX_JSON_BYTES, CollageError
from .projects import _contained


def canonical(value: BaseModel) -> bytes:
    import json

    return json.dumps(
        value.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def child(root: Path, *parts: str) -> Path:
    return _contained(root, root.joinpath(*parts))


def save(path: Path, value: BaseModel) -> None:
    raw = canonical(value)
    if len(raw) > MAX_JSON_BYTES:
        raise CollageError("Conversation record exceeds the 1 MiB limit.")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".record-", delete=False) as file:
        temporary = Path(file.name)
        try:
            file.write(raw)
            file.flush()
            os.fsync(file.fileno())
        except OSError:
            file.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
