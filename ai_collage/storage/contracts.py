"""Initialized-project persistence contract and storage outcomes."""

from collections.abc import Mapping
from typing import BinaryIO, Protocol

from ..agent.models import ConversationState
from ..engine.models import CollageError, Project


class ProjectNotFound(CollageError):
    """No published project has this ID."""


class ProjectExists(CollageError):
    """Publication would replace an existing project entry."""


class PhotoNotFound(CollageError):
    """The project has no photo with this number."""


class StorageUnavailable(Exception):
    """A storage operation failed without publishing a new project."""


class StorageOutcomeUnknown(Exception):
    """Publication may have completed; preserve candidate objects and look up the project."""


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
