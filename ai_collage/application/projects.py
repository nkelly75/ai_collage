"""Project lifecycle workflows over existing engine and agent capabilities."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
import errno
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Annotated, BinaryIO

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from ..agent.conversation import Conversation
from ..agent.files import child, digest
from ..agent.models import ConversationState
from ..engine.models import (
    MAX_CANVAS_AXIS, MAX_FILE_BYTES, CollageError, PhotoMediaError, PhotoSizeError,
    Project, validate_project_id,
)
from ..engine.projects import ProjectStore
from ..storage.contracts import PhotoNotFound, ProjectExists, ProjectNotFound, ProjectStorage
from ..storage.local import LocalProjectStorage


class FlowError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


class CanvasSize(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    width: Annotated[int, Field(ge=1, le=MAX_CANVAS_AXIS)]
    height: Annotated[int, Field(ge=1, le=MAX_CANVAS_AXIS)]


class ProjectSetup(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    project_id: str
    canvas: CanvasSize

    @field_validator("project_id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        return validate_project_id(value)


def configured_store() -> ProjectStore:
    value = os.environ.get("AI_COLLAGE_DATA_DIR")
    if value is None:
        path = Path(__file__).resolve().parents[2] / ".collage-data-web"
    else:
        path = Path(value)
        if not value.strip() or not path.is_absolute():
            raise FlowError("configuration_error", "AI_COLLAGE_DATA_DIR must be an absolute path.", 500)
    return ProjectStore(path)


@contextmanager
def project_guard(store: ProjectStore, project_id: str, *, create: bool = True):
    validate_project_id(project_id)
    directory = child(store.owner_dir, ".locks")
    path = child(directory, f"{project_id}.lock")
    if not create and not path.exists():
        yield
        return
    if create:
        directory.mkdir(parents=True, exist_ok=True)
    with path.open("a+b" if create else "r+b") as lock:
        lock.seek(0, 2)
        if lock.tell() == 0 and create:
            lock.write(b"\0")
            lock.flush()
        lock.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                raise
            raise FlowError("project_busy", "Project is busy; check its saved state before retrying.", 409) from exc
        try:
            yield
        finally:
            if sys.platform == "win32":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def project_is_busy(store: ProjectStore, project_id: str) -> bool:
    try:
        with project_guard(store, project_id, create=False):
            return False
    except FlowError as exc:
        if exc.code != "project_busy":
            raise
        return True


class ProjectFlow:
    def __init__(self, store: ProjectStore, storage: ProjectStorage | None = None):
        self.store = store
        self.storage = LocalProjectStorage(store) if storage is None else storage

    def _load(self, project_id: str) -> tuple[Project, ConversationState]:
        validate_project_id(project_id)
        try:
            project, state = self.storage.load(project_id)
            photo_digest = digest(json.dumps(
                [photo.model_dump() for photo in project.photos], sort_keys=True,
            ).encode())
            if state.project_id != project_id or state.photo_digest != photo_digest:
                raise CollageError("Project/photo identity mismatch.")
            CanvasSize(width=state.controls.width, height=state.controls.height)
            return project, state
        except ProjectNotFound as exc:
            raise FlowError("not_found", "Project not found.", 404) from exc
        except (CollageError, ValidationError, FileNotFoundError, IsADirectoryError, NotADirectoryError) as exc:
            raise FlowError(
                "invalid_project_state", f"Saved project {project_id} is incomplete or invalid; it was not changed.", 409,
            ) from exc

    def detail(self, project_id: str) -> dict:
        project, state = self._load(project_id)
        return self._detail(project, state)

    @staticmethod
    def _detail(project: Project, state: ConversationState) -> dict:
        return {
            "project_id": project.project_id,
            "canvas": {"width": state.controls.width, "height": state.controls.height},
            "photos": [
                {"photo_id": p.photo_id, "width": p.width, "height": p.height}
                for p in project.photos
            ],
        }

    def list(self) -> list[dict]:
        try:
            project_ids = self.storage.project_ids()
        except CollageError as exc:
            raise FlowError("invalid_project_state", "Unexpected entry in the project store.", 409) from exc
        results = []
        for project_id in project_ids:
            try:
                detail = self.detail(project_id)
            except CollageError as exc:
                raise FlowError("invalid_project_state", "Invalid saved project ID; store unchanged.", 409) from exc
            results.append({
                "project_id": detail["project_id"], "canvas": detail["canvas"],
                "photo_count": len(detail["photos"]),
            })
        return results

    def photo(self, project_id: str, photo_id: int) -> tuple[bytes, str]:
        project, _ = self._load(project_id)
        try:
            return self.storage.photo(project, photo_id)
        except PhotoNotFound as exc:
            raise FlowError("not_found", "Photo not found.", 404) from exc
        except (CollageError, FileNotFoundError) as exc:
            raise FlowError("invalid_project_state", "Saved photo is missing or invalid; project unchanged.", 409) from exc

    def create(self, setup: ProjectSetup, images: list[BinaryIO]) -> dict:
        if not 2 <= len(images) <= 6:
            raise FlowError("invalid_request", "Choose between 2 and 6 photos.")
        store = self.store
        with project_guard(store, setup.project_id):
            if self.storage.exists(setup.project_id):
                raise FlowError("project_exists", "That project ID is already saved.", 409)
            with tempfile.TemporaryDirectory(prefix="collage-prepare-") as temporary:
                root = Path(temporary)
                sources = []
                for number, stream in enumerate(images, start=1):
                    source = root / f"photo-{number}"
                    size = 0
                    with source.open("xb") as target:
                        while chunk := stream.read(1024 * 1024):
                            size += len(chunk)
                            if size > MAX_FILE_BYTES:
                                raise FlowError("photo_too_large", f"Photo {number} exceeds 25 MiB.", 413)
                            target.write(chunk)
                    sources.append(source)
                staging = ProjectStore(root / "store")
                try:
                    project = staging.create(setup.project_id, sources)
                except PhotoSizeError as exc:
                    raise FlowError("photo_too_large", "A photo exceeds the supported byte/pixel limits.", 413) from exc
                except PhotoMediaError as exc:
                    raise FlowError("unsupported_media", "Only single-frame JPEG/PNG photos are supported.", 415) from exc
                except CollageError as exc:
                    raise FlowError("invalid_photos", "Choose readable, single-frame JPEG/PNG photos within the 40,000,000 pixel limit.") from exc
                conversation = Conversation(
                    staging, setup.project_id,
                    canvas=(setup.canvas.width, setup.canvas.height),
                )
                result = self._detail(project, conversation.state)
                with ExitStack() as stack:
                    photos = {
                        number: stack.enter_context(path.open("rb"))
                        for number, path in staging.photo_paths(project).items()
                    }
                    try:
                        self.storage.publish(project, conversation.state, photos)
                    except ProjectExists as exc:
                        raise FlowError("project_exists", "That project ID is already saved.", 409) from exc
                return result
