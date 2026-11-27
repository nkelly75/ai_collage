"""Immutable initialized-project candidates, made visible by one conditional Blob write."""

from collections.abc import Mapping
import logging
from pathlib import Path
import re
import tempfile
from typing import Annotated, BinaryIO, Literal
from uuid import uuid4

from azure.core import MatchConditions
from azure.core.exceptions import AzureError, HttpResponseError, ResourceNotFoundError
from azure.storage.blob import ContainerClient, ContentSettings
from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..agent.files import canonical
from ..agent.models import ConversationState
from ..engine.imaging import load_photo
from ..engine.models import (
    MAX_FILE_BYTES, MAX_JSON_BYTES, OWNER_ID, CollageError, PhotoSizeError, Project,
    validate_project_id,
)
from ..engine.projects import parse_json, photo_extension
from .contracts import (
    PhotoNotFound, ProjectExists, ProjectNotFound, StorageOutcomeUnknown, StorageUnavailable,
)


class Completion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Annotated[int, Field(strict=True, ge=1, le=1)]
    owner_id: Literal["local-dev"]
    project_id: str
    attempt_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]

    @field_validator("project_id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        return validate_project_id(value)


class BlobProjectStorage:
    def __init__(self, container: ContainerClient, namespace: str):
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", namespace):
            raise ValueError("Invalid Blob namespace.")
        self.container = container
        self.prefix = f"{namespace}/users/{OWNER_ID}/"

    def completion_key(self, project_id: str) -> str:
        return f"{self.prefix}published/{validate_project_id(project_id)}.json"

    def candidate_prefix(self, completion: Completion) -> str:
        return f"{self.prefix}candidates/{completion.project_id}/{completion.attempt_id}/"

    def _properties(self, key: str, *, published: bool = False):
        try:
            return self.container.get_blob_client(key).get_blob_properties()
        except ResourceNotFoundError as exc:
            if getattr(exc, "error_code", None) != "BlobNotFound":
                raise StorageUnavailable("Blob container is unavailable.") from exc
            if published:
                raise ProjectNotFound("Project not found.") from exc
            raise CollageError("Published project references a missing object.") from exc
        except AzureError as exc:
            raise StorageUnavailable("Blob storage is unavailable.") from exc

    def _read(self, key: str, limit: int, *, published: bool = False) -> bytes:
        properties = self._properties(key, published=published)
        if type(properties.size) is not int or not 0 <= properties.size <= limit:
            raise CollageError("Saved Blob object exceeds its size limit.")
        if properties.size == 0:
            return b""
        try:
            download = self.container.get_blob_client(key).download_blob(
                offset=0, length=limit + 1, max_concurrency=1,
                etag=properties.etag, match_condition=MatchConditions.IfNotModified,
            )
            raw = bytearray()
            for chunk in download.chunks():
                if len(raw) + len(chunk) > limit:
                    raise CollageError("Saved Blob object exceeds its size limit.")
                raw.extend(chunk)
            if len(raw) != properties.size:
                raise CollageError("Saved Blob object is truncated or changed.")
            return bytes(raw)
        except ResourceNotFoundError as exc:
            if getattr(exc, "error_code", None) == "BlobNotFound":
                raise CollageError("Saved Blob object disappeared during a read.") from exc
            raise StorageUnavailable("Blob container is unavailable.") from exc
        except AzureError as exc:
            raise StorageUnavailable("Blob storage is unavailable.") from exc

    def completion(self, project_id: str) -> Completion:
        result = Completion.model_validate(parse_json(self._read(
            self.completion_key(project_id), MAX_JSON_BYTES, published=True,
        )))
        if result.project_id != project_id:
            raise CollageError("Completion identity mismatch.")
        return result

    def exists(self, project_id: str) -> bool:
        try:
            self._properties(self.completion_key(project_id), published=True)
            return True
        except ProjectNotFound:
            return False

    def project_ids(self) -> list[str]:
        prefix = f"{self.prefix}published/"
        try:
            results = []
            for blob in self.container.list_blobs(name_starts_with=prefix):
                name = blob.name.removeprefix(prefix)
                if not name.endswith(".json"):
                    raise CollageError("Unexpected published Blob entry.")
                project_id = validate_project_id(name[:-5])
                self.completion(project_id)
                results.append(project_id)
            return sorted(results)
        except AzureError as exc:
            raise StorageUnavailable("Cannot enumerate Blob projects.") from exc
        except (ProjectNotFound, ValueError) as exc:
            raise CollageError("Published project is missing or invalid.") from exc

    def load(self, project_id: str) -> tuple[Project, ConversationState]:
        prefix = self.candidate_prefix(self.completion(project_id))
        project = Project.model_validate(parse_json(self._read(f"{prefix}project.json", MAX_JSON_BYTES)))
        state = ConversationState.model_validate(parse_json(self._read(
            f"{prefix}conversation/state.json", MAX_JSON_BYTES,
        )))
        if project.project_id != project_id:
            raise CollageError("Project identity mismatch.")
        for photo in project.photos:
            photo_extension(photo)
            properties = self._properties(f"{prefix}photos/{photo.asset_id}")
            if type(properties.size) is not int or not 0 < properties.size <= MAX_FILE_BYTES:
                raise CollageError("Saved photo exceeds its size limit or is empty.")
        return project, state

    def photo(self, project: Project, photo_id: int) -> tuple[bytes, str]:
        photos = {photo.photo_id: photo for photo in project.photos}
        if photo_id not in photos:
            raise PhotoNotFound("Photo not found.")
        photo = photos[photo_id]
        prefix = self.candidate_prefix(self.completion(project.project_id))
        raw = self._read(f"{prefix}photos/{photo.asset_id}", MAX_FILE_BYTES)
        with tempfile.TemporaryDirectory(prefix="collage-blob-photo-") as directory:
            path = Path(directory) / "photo"
            path.write_bytes(raw)
            image, extension = load_photo(path)
            with image:
                if image.size != (photo.width, photo.height) or extension != photo_extension(photo):
                    raise CollageError("Saved photo metadata changed.")
        return raw, "image/jpeg" if extension == ".jpg" else "image/png"

    def publish(
        self, project: Project, state: ConversationState, photos: Mapping[int, BinaryIO],
    ) -> None:
        if state.project_id != project.project_id or set(photos) != {p.photo_id for p in project.photos}:
            raise CollageError("Prepared project/state/photo identity mismatch.")
        records = (canonical(project), canonical(state))
        if any(len(raw) > MAX_JSON_BYTES for raw in records):
            raise CollageError("Prepared record exceeds the 1 MiB limit.")
        extensions = {photo.photo_id: photo_extension(photo) for photo in project.photos}
        completion = Completion(
            schema_version=1, owner_id=OWNER_ID, project_id=project.project_id, attempt_id=uuid4().hex,
        )
        prefix = self.candidate_prefix(completion)
        owned: list[tuple[str, str]] = []
        cleanup = True
        committed = False

        def upload(key, data, content_type):
            result = self.container.get_blob_client(key).upload_blob(
                data, overwrite=False, max_concurrency=1,
                content_settings=ContentSettings(content_type=content_type),
            )
            etag = result["etag"]
            if not isinstance(etag, str):
                raise CollageError("Upload did not return an ownership ETag.")
            owned.append((key, etag))

        try:
            for photo in project.photos:
                with tempfile.TemporaryFile() as prepared:
                    size = 0
                    while chunk := photos[photo.photo_id].read(1024 * 1024):
                        size += len(chunk)
                        if size > MAX_FILE_BYTES:
                            raise PhotoSizeError("Photo exceeds 25 MiB.")
                        prepared.write(chunk)
                    prepared.seek(0)
                    upload(
                        f"{prefix}photos/{photo.asset_id}", prepared,
                        "image/jpeg" if extensions[photo.photo_id] == ".jpg" else "image/png",
                    )
            upload(f"{prefix}project.json", records[0], "application/json")
            upload(f"{prefix}conversation/state.json", records[1], "application/json")
            # From this point, only a confirmed rejection permits removing candidates.
            cleanup = False
            try:
                self.container.get_blob_client(self.completion_key(project.project_id)).upload_blob(
                    canonical(completion), overwrite=False,
                    content_settings=ContentSettings(content_type="application/json"),
                )
            except HttpResponseError as exc:
                if getattr(exc, "error_code", None) in {"BlobAlreadyExists", "ConditionNotMet"}:
                    cleanup = True
                    raise ProjectExists("That project ID is already saved.") from exc
                if exc.status_code is not None and 400 <= exc.status_code < 500 and exc.status_code != 408:
                    cleanup = True
                    raise StorageUnavailable("Completion publication was rejected.") from exc
                raise StorageOutcomeUnknown("Look up the project before any further create.") from exc
            except (AzureError, StorageUnavailable, OSError) as exc:
                cleanup = False
                raise StorageOutcomeUnknown("Look up the project before any further create.") from exc
            committed = True
        except AzureError as exc:
            raise StorageUnavailable("Candidate upload failed.") from exc
        finally:
            if cleanup and not committed:
                for key, etag in reversed(owned):
                    try:
                        self.container.delete_blob(
                            key, etag=etag, match_condition=MatchConditions.IfNotModified,
                        )
                    except (AzureError, StorageUnavailable, OSError):
                        logging.exception("Could not clean an owned Blob candidate: %s", key)
