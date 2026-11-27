"""Initialized-project persistence; conversation mutations remain local elsewhere."""

from collections.abc import Mapping
import os
from pathlib import Path
import tempfile
from typing import BinaryIO, Protocol

from .agent.files import child, save
from .agent.models import ConversationState
from .engine.imaging import load_photo
from .engine.models import MAX_FILE_BYTES, CollageError, PhotoSizeError, Project
from .engine.projects import ProjectStore, _write_json, read_json


class ProjectNotFound(CollageError):
    """No published project has this ID."""


class ProjectExists(CollageError):
    """Publication would replace an existing project entry."""


class PhotoNotFound(CollageError):
    """The project has no photo with this number."""


class ProjectStorage(Protocol):
    """Prepared-project IO; mutations require the caller's project guard."""

    def exists(self, project_id: str) -> bool: ...

    def publish(
        self, project: Project, state: ConversationState, photos: Mapping[int, BinaryIO],
    ) -> None:
        """Publish a prepared project, consuming photo streams from their current positions."""
        ...

    def project_ids(self) -> list[str]: ...

    def load(self, project_id: str) -> tuple[Project, ConversationState]: ...

    def photo(self, project: Project, photo_id: int) -> tuple[bytes, str]: ...


class LocalProjectStorage:
    def __init__(self, store: ProjectStore):
        self.store = store

    def exists(self, project_id: str) -> bool:
        return self.store.project_dir(project_id).exists()

    def publish(
        self, project: Project, state: ConversationState, photos: Mapping[int, BinaryIO],
    ) -> None:
        store = self.store
        destination = store.project_dir(project.project_id)
        if destination.exists():
            raise ProjectExists("That project ID is already saved.")
        paths = store.photo_paths(project)
        if state.project_id != project.project_id or set(photos) != set(paths):
            raise CollageError("Prepared project/state/photo identity mismatch.")
        store.projects_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".create-web-", dir=store.projects_dir) as temporary:
            root = Path(temporary)
            directory = root / "project"
            directory.mkdir()
            (directory / "layouts").mkdir()
            (directory / "renders").mkdir()
            _write_json(directory / "project.json", project)
            save(directory / "conversation" / "state.json", state)
            for number, stream in photos.items():
                size = 0
                with (root / f"photo-{number}").open("xb") as target:
                    while chunk := stream.read(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_FILE_BYTES:
                            raise PhotoSizeError(f"Photo {number} exceeds 25 MiB.")
                        target.write(chunk)
            store.uploads_dir.mkdir(parents=True, exist_ok=True)
            published = []
            committed = False
            try:
                for number, path in paths.items():
                    # Publish assets without replacement, then make the complete project visible.
                    os.link(root / f"photo-{number}", path)
                    published.append(path)
                directory.rename(destination)
                committed = True
            finally:
                if not committed:
                    for path in published:
                        path.unlink()

    def project_ids(self) -> list[str]:
        try:
            directories = sorted(self.store.projects_dir.iterdir())
        except FileNotFoundError:
            return []
        results = []
        for directory in directories:
            if directory.name.startswith("."):
                continue
            if not directory.is_dir():
                raise CollageError("Unexpected entry in the project store.")
            results.append(directory.name)
        return results

    def load(self, project_id: str) -> tuple[Project, ConversationState]:
        directory = self.store.project_dir(project_id)
        if not directory.exists():
            raise ProjectNotFound("Project not found.")
        if not directory.is_dir():
            raise CollageError("Project entry is not a directory.")
        project = self.store.load(project_id)
        state = ConversationState.model_validate(
            read_json(child(directory, "conversation", "state.json"))
        )
        if any(not path.is_file() for path in self.store.photo_paths(project).values()):
            raise CollageError("Missing imported photo.")
        return project, state

    def photo(self, project: Project, photo_id: int) -> tuple[bytes, str]:
        paths = self.store.photo_paths(project)
        if photo_id not in paths:
            raise PhotoNotFound("Photo not found.")
        path = paths[photo_id]
        image, extension = load_photo(path)
        with image:
            photo = project.photos[photo_id - 1]
            if image.size != (photo.width, photo.height):
                raise CollageError("Photo dimensions changed.")
        with path.open("rb") as stream:
            raw = stream.read(MAX_FILE_BYTES + 1)
        if len(raw) > MAX_FILE_BYTES:
            raise CollageError("Photo exceeds its size limit.")
        return raw, "image/jpeg" if extension == ".jpg" else "image/png"
