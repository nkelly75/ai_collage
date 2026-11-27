"""Local initialized-project publication and read-only delivery."""

from collections.abc import Mapping
from contextlib import contextmanager, nullcontext
import os
from pathlib import Path
import re
import tempfile
from typing import BinaryIO
from uuid import UUID

from pydantic import BaseModel

from ..agent.files import child, save
from ..agent.models import ConversationState, Proposal
from ..engine.imaging import load_photo
from ..engine.models import MAX_FILE_BYTES, CollageError, PhotoSizeError, Project
from ..engine.projects import ProjectStore, _write_json, read_json
from .contracts import (
    MAX_PREVIEW_BYTES, PhotoNotFound, ProjectExists, ProjectNotFound, RecordKind,
)


def read_preview(path: Path) -> bytes:
    with path.open("rb") as stream:
        size = os.fstat(stream.fileno()).st_size
        if size > MAX_PREVIEW_BYTES:
            raise CollageError("Preview exceeds the 128 MiB limit.")
        raw = stream.read(size + 1)
    if len(raw) != size:
        raise CollageError("Preview changed during its bounded read.")
    return raw


def record_parts(kind: RecordKind, identity: str) -> tuple[str, ...]:
    if kind == "state" and identity == "state":
        return ("conversation", "state.json")
    if kind == "event" and re.fullmatch(r"[0-9]{6,}", identity):
        return ("conversation", "events", f"{identity}.json")
    if kind == "attempt" and re.fullmatch(r"[0-9]{4,}", identity):
        return ("conversation", "requests", f"attempt-{identity}.json")
    if kind == "proposal" and re.fullmatch(r"P[0-9]{3,}", identity):
        return ("conversation", "proposals", identity, "proposal.json")
    if kind in {"operation", "selection"}:
        try:
            if str(UUID(identity)) == identity:
                return ("web-operations" if kind == "operation" else "web-selections", f"{identity}.json")
        except ValueError:
            pass
    raise CollageError("Invalid logical record identity.")


class LocalConversationStorage:
    supports_acceptance = True

    def __init__(self, store: ProjectStore, project_id: str):
        self.store = store
        self.project_id = project_id
        self.root = store.project_dir(project_id)

    def project(self) -> Project:
        return self.store.load(self.project_id)

    def path(self, kind: RecordKind, identity: str) -> Path:
        return child(self.root, *record_parts(kind, identity))

    def read(self, kind: RecordKind, identity: str) -> object | None:
        path = self.path(kind, identity)
        return read_json(path) if path.exists() else None

    def identities(self, kind: RecordKind) -> list[str]:
        if kind == "state":
            return ["state"] if self.path(kind, "state").exists() else []
        if kind == "proposal":
            directory = child(self.root, "conversation", "proposals")
            return sorted(p.name for p in directory.glob("P*") if re.fullmatch(r"P[0-9]{3,}", p.name))
        directories = {
            "event": ("conversation", "events"), "attempt": ("conversation", "requests"),
            "operation": ("web-operations",), "selection": ("web-selections",),
        }
        names = [p.stem.removeprefix("attempt-") if kind == "attempt" else p.stem
                 for p in child(self.root, *directories[kind]).glob("*.json")]
        if kind == "event":
            names = [name for name in names if re.fullmatch(r"[0-9]{6,}", name)]
        for name in names:
            record_parts(kind, name)
        return sorted(names, key=lambda name: (len(name), name))

    def write(self, kind: RecordKind, identity: str, value: BaseModel) -> None:
        save(self.path(kind, identity), value)

    def checkpoint(self):
        return nullcontext()

    def publish_proposal(self, proposal: Proposal, preview: Path) -> None:
        destination = self.path("proposal", proposal.proposal_id).parent
        destination.parent.mkdir(parents=True, exist_ok=True)
        save(preview.parent / "proposal.json", proposal)
        preview.parent.rename(destination)

    def preview(self, proposal_id: str) -> bytes:
        return read_preview(self.path("proposal", proposal_id).with_name("preview.png"))

    @contextmanager
    def photo_paths(self):
        yield self.store.photo_paths(self.project())

    def check_write(self) -> None:
        return


class LocalProjectStorage:
    def __init__(self, store: ProjectStore):
        self.store = store

    def exists(self, project_id: str) -> bool:
        return self.store.project_dir(project_id).exists()

    def conversation(self, project_id: str) -> LocalConversationStorage:
        if not self.exists(project_id):
            raise ProjectNotFound("Project not found.")
        return LocalConversationStorage(self.store, project_id)

    @contextmanager
    def mutation(self, project_id: str):
        from ..application.projects import project_guard

        with project_guard(self.store, project_id):
            yield self.conversation(project_id)

    def busy(self, project_id: str) -> bool:
        from ..application.projects import project_is_busy

        return project_is_busy(self.store, project_id)

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
