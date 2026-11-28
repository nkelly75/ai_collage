"""Project/conversation persistence contracts and storage outcomes."""

from collections.abc import Mapping
from contextlib import AbstractContextManager
from pathlib import Path
from typing import BinaryIO, Literal, Protocol

from pydantic import BaseModel

from ..agent.models import ConversationState, Proposal
from ..engine.models import CollageError, Project


class ProjectNotFound(CollageError):
    """No published project has this ID."""


class ProjectExists(CollageError):
    """Publication would replace an existing project entry."""


class PhotoNotFound(CollageError):
    """The project has no photo with this number."""


class ProposalNotFound(CollageError):
    """The project has no committed proposal with this ID."""


class StorageUnavailable(Exception):
    """A storage operation failed without publishing a new project."""


class StorageOutcomeUnknown(Exception):
    """Publication may have completed; preserve candidate objects and look up the project."""


class StorageBusy(CollageError):
    """Another writer owns this project's storage guard."""


RecordKind = Literal["state", "event", "proposal", "attempt", "operation", "selection"]
MAX_PREVIEW_BYTES = 128 * 1024 * 1024


class ConversationStorage(Protocol):
    """Logical record IO bound to one project snapshot or fenced writer."""

    project_id: str
    supports_acceptance: bool

    def project(self) -> Project: ...

    def read(self, kind: RecordKind, identity: str) -> object | None: ...

    def identities(self, kind: RecordKind) -> list[str]: ...

    def write(self, kind: RecordKind, identity: str, value: BaseModel) -> None: ...

    def checkpoint(self) -> AbstractContextManager[None]: ...

    def publish_proposal(self, proposal: Proposal, preview: Path) -> None: ...

    def preview(self, proposal_id: str) -> bytes: ...

    def thumbnail(self, proposal_id: str) -> bytes: ...

    def validate_assets(self, proposal: Proposal) -> None: ...

    def photo_paths(self) -> AbstractContextManager[Mapping[int, Path]]: ...

    def check_write(self) -> None: ...


class ProjectStorage(Protocol):
    """Prepared-project IO; publication must reject replacement independently of local guards."""

    def exists(self, project_id: str) -> bool: ...

    def publish(
        self, project: Project, state: ConversationState, photos: Mapping[int, BinaryIO],
    ) -> None:
        """Publish a prepared project, consuming photo streams from their current positions."""
        ...

    def project_ids(self) -> list[str]: ...

    def load(self, project_id: str) -> tuple[Project, ConversationState]: ...

    def photo(self, project: Project, photo_id: int) -> tuple[bytes, str]: ...

    def conversation(self, project_id: str) -> ConversationStorage: ...

    def mutation(self, project_id: str) -> AbstractContextManager[ConversationStorage]: ...

    def busy(self, project_id: str) -> bool: ...
