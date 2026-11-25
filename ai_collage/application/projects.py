"""Project lifecycle workflows over existing engine and agent capabilities."""

from __future__ import annotations

from contextlib import contextmanager
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
from ..engine.imaging import load_photo
from ..engine.models import (
    MAX_CANVAS_AXIS, MAX_FILE_BYTES, CollageError, PhotoMediaError, PhotoSizeError,
    Project, validate_project_id,
)
from ..engine.projects import ProjectStore, read_json


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
def project_guard(store: ProjectStore, project_id: str):
    validate_project_id(project_id)
    directory = child(store.owner_dir, ".locks")
    directory.mkdir(parents=True, exist_ok=True)
    with child(directory, f"{project_id}.lock").open("a+b") as lock:
        lock.seek(0, 2)
        if lock.tell() == 0:
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


class ProjectFlow:
    def __init__(self, store: ProjectStore):
        self.store = store

    def _load(self, project_id: str) -> tuple[Project, ConversationState]:
        directory = self.store.project_dir(project_id)
        if not directory.exists():
            raise FlowError("not_found", "Project not found.", 404)
        try:
            if not directory.is_dir():
                raise CollageError("Project entry is not a directory.")
            project = self.store.load(project_id)
            state = ConversationState.model_validate(
                read_json(child(directory, "conversation", "state.json"))
            )
            photo_digest = digest(json.dumps(
                [photo.model_dump() for photo in project.photos], sort_keys=True,
            ).encode())
            if state.project_id != project_id or state.photo_digest != photo_digest:
                raise CollageError("Project/photo identity mismatch.")
            if any(not path.is_file() for path in self.store.photo_paths(project).values()):
                raise CollageError("Missing imported photo.")
            CanvasSize(width=state.controls.width, height=state.controls.height)
            return project, state
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
            directories = sorted(self.store.projects_dir.iterdir())
        except FileNotFoundError:
            return []
        results = []
        for directory in directories:
            if directory.name.startswith("."):
                continue
            if not directory.is_dir():
                raise FlowError("invalid_project_state", "Unexpected entry in the project store.", 409)
            try:
                detail = self.detail(directory.name)
            except CollageError as exc:
                raise FlowError("invalid_project_state", "Invalid saved project ID; store unchanged.", 409) from exc
            results.append({
                "project_id": detail["project_id"], "canvas": detail["canvas"],
                "photo_count": len(detail["photos"]),
            })
        return results

    def photo(self, project_id: str, photo_id: int) -> tuple[bytes, str]:
        project, _ = self._load(project_id)
        paths = self.store.photo_paths(project)
        if photo_id not in paths:
            raise FlowError("not_found", "Photo not found.", 404)
        path = paths[photo_id]
        try:
            image, extension = load_photo(path)
            with image:
                photo = project.photos[photo_id - 1]
                if image.size != (photo.width, photo.height):
                    raise CollageError("Photo dimensions changed.")
            with path.open("rb") as stream:
                raw = stream.read(MAX_FILE_BYTES + 1)
            if len(raw) > MAX_FILE_BYTES:
                raise CollageError("Photo exceeds its size limit.")
        except (CollageError, FileNotFoundError) as exc:
            raise FlowError("invalid_project_state", "Saved photo is missing or invalid; project unchanged.", 409) from exc
        return raw, "image/jpeg" if extension == ".jpg" else "image/png"

    def create(self, setup: ProjectSetup, images: list[BinaryIO]) -> dict:
        if not 2 <= len(images) <= 6:
            raise FlowError("invalid_request", "Choose between 2 and 6 photos.")
        store = self.store
        with project_guard(store, setup.project_id):
            destination = store.project_dir(setup.project_id)
            if destination.exists():
                raise FlowError("project_exists", "That project ID is already saved.", 409)
            store.projects_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".create-web-", dir=store.projects_dir) as temporary:
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
                store.uploads_dir.mkdir(parents=True, exist_ok=True)
                published = []
                committed = False
                try:
                    paths = store.photo_paths(project)
                    for number, source in staging.photo_paths(project).items():
                        # Link without replacement; staging and destination share a filesystem.
                        os.link(source, paths[number])
                        published.append(paths[number])
                    staging.project_dir(setup.project_id).rename(destination)
                    committed = True
                finally:
                    if not committed:
                        for path in published:
                            path.unlink()
                return result
