"""Bounded immutable records published through one leased, conditional project head."""

from collections import OrderedDict
from collections.abc import Mapping
from contextlib import contextmanager
import logging
from pathlib import Path
import re
import tempfile
import threading
from time import monotonic
from typing import Annotated, BinaryIO, Literal
from uuid import uuid4

from azure.core import MatchConditions
from azure.core.exceptions import AzureError, HttpResponseError, ResourceNotFoundError
from azure.storage.blob import ContainerClient, ContentSettings
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..agent.files import canonical, digest
from ..agent.models import ConversationState, Digest, Proposal
from ..engine.imaging import load_photo
from ..engine.models import (
    MAX_FILE_BYTES, MAX_JSON_BYTES, OWNER_ID, CollageError, PhotoSizeError, Project,
    validate_project_id,
)
from ..engine.projects import parse_json, photo_extension
from .contracts import (
    MAX_PREVIEW_BYTES, PhotoNotFound, ProjectExists, ProjectNotFound, RecordKind,
    StorageBusy, StorageOutcomeUnknown, StorageUnavailable,
)
from .local import read_preview, record_parts


LEASE_SECONDS = 60
LEASE_RENEW_SECONDS = 20
CandidateId = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]


class ObjectReference(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    attempt_id: CandidateId
    sha256: Digest
    size: Annotated[int, Field(ge=1, le=MAX_PREVIEW_BYTES)]


class Completion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal[2]
    owner_id: Literal["local-dev"]
    project_id: str
    attempt_id: CandidateId
    project: ObjectReference
    photos: dict[str, ObjectReference]
    records: dict[RecordKind, dict[str, ObjectReference]]
    previews: dict[str, ObjectReference] = Field(default_factory=dict)

    @field_validator("project_id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        return validate_project_id(value)

    @model_validator(mode="after")
    def identities(self):
        if set(self.records) != {"state", "event", "proposal", "attempt", "operation", "selection"}:
            raise ValueError("Head record categories are incomplete.")
        if set(self.records["state"]) != {"state"}:
            raise ValueError("Head must reference exactly one conversation state.")
        for kind, records in self.records.items():
            for identity, reference in records.items():
                record_parts(kind, identity)
                if reference.size > MAX_JSON_BYTES:
                    raise ValueError("Record reference exceeds 1 MiB.")
        if self.project.size > MAX_JSON_BYTES:
            raise ValueError("Project reference exceeds 1 MiB.")
        if set(self.previews) != set(self.records["proposal"]):
            raise ValueError("Proposal/preview references differ.")
        for identity in self.previews:
            record_parts("proposal", identity)
        for asset, reference in self.photos.items():
            if not re.fullmatch(r"[0-9a-f]{32}", asset) or reference.size > MAX_FILE_BYTES:
                raise ValueError("Invalid photo reference.")
        return self


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

    def object_key(self, project_id: str, reference: ObjectReference, *parts: str) -> str:
        return f"{self.prefix}candidates/{project_id}/{reference.attempt_id}/{'/'.join(parts)}"

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

    def _read_etag(self, key: str, limit: int, *, published: bool = False) -> tuple[bytes, str]:
        properties = self._properties(key, published=published)
        if type(properties.size) is not int or not 0 < properties.size <= limit:
            raise CollageError("Saved Blob object is empty or exceeds its size limit.")
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
            return bytes(raw), properties.etag
        except ResourceNotFoundError as exc:
            if getattr(exc, "error_code", None) == "BlobNotFound":
                raise CollageError("Saved Blob object disappeared during a read.") from exc
            raise StorageUnavailable("Blob container is unavailable.") from exc
        except AzureError as exc:
            raise StorageUnavailable("Blob storage is unavailable.") from exc

    def _read(self, key: str, limit: int, *, published: bool = False) -> bytes:
        return self._read_etag(key, limit, published=published)[0]

    def _head(self, project_id: str) -> tuple[Completion, str]:
        raw, etag = self._read_etag(self.completion_key(project_id), MAX_JSON_BYTES, published=True)
        head = Completion.model_validate(parse_json(raw))
        if head.project_id != project_id:
            raise CollageError("Completion identity mismatch.")
        return head, etag

    def completion(self, project_id: str) -> Completion:
        return self._head(project_id)[0]

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

    def conversation(self, project_id: str):
        head, etag = self._head(project_id)
        return BlobConversationStorage(self, head, etag)

    def load(self, project_id: str) -> tuple[Project, ConversationState]:
        session = self.conversation(project_id)
        project = session.project()
        state = ConversationState.model_validate(session.read("state", "state"))
        if project.current_version is not None or state.initial_version is not None or state.expected_version is not None:
            raise CollageError("Blob web projects do not support accepted CLI versions.")
        if set(session.head.photos) != {p.asset_id for p in project.photos}:
            raise CollageError("Project photo references differ.")
        for photo in project.photos:
            photo_extension(photo)
            reference = session.head.photos[photo.asset_id]
            properties = self._properties(self.object_key(project_id, reference, "photos", photo.asset_id))
            if properties.size != reference.size:
                raise CollageError("Saved photo size changed.")
        return project, state

    def photo(self, project: Project, photo_id: int) -> tuple[bytes, str]:
        return self.conversation(project.project_id).photo(project, photo_id)

    def busy(self, project_id: str) -> bool:
        properties = self._properties(self.completion_key(project_id), published=True)
        return properties.lease.status == "locked"

    @contextmanager
    def mutation(self, project_id: str):
        key = self.completion_key(project_id)
        self._properties(key, published=True)
        try:
            lease = self.container.get_blob_client(key).acquire_lease(lease_duration=LEASE_SECONDS)
        except HttpResponseError as exc:
            if getattr(exc, "error_code", None) == "LeaseAlreadyPresent":
                raise StorageBusy("Project is busy; check saved state before retrying.") from exc
            raise StorageUnavailable("Cannot acquire the project lease.") from exc
        except AzureError as exc:
            raise StorageUnavailable("Project lease acquisition is unconfirmed.") from exc
        stop = threading.Event()
        session = None
        thread = None
        try:
            head, etag = self._head(project_id)
            session = BlobConversationStorage(self, head, etag, lease=lease)

            def renew():
                while not stop.wait(LEASE_RENEW_SECONDS):
                    try:
                        session.check_write()
                    except (StorageUnavailable, StorageOutcomeUnknown):
                        logging.exception("Project lease renewal stopped; no further dispatch/publication.")
                        return

            thread = threading.Thread(target=renew, name="collage-blob-lease", daemon=True)
            thread.start()
            yield session
        finally:
            stop.set()
            if thread is not None:
                thread.join()
            if session is not None:
                session.closed = True
            try:
                lease.release()
            except (AzureError, StorageUnavailable, OSError):
                logging.exception("Could not release the owned project lease; it will expire.")

    def _upload(self, key: str, raw: bytes, content_type: str) -> str:
        try:
            result = self.container.get_blob_client(key).upload_blob(
                raw, overwrite=False, max_concurrency=1,
                content_settings=ContentSettings(content_type=content_type),
            )
            if not isinstance(result["etag"], str):
                raise StorageUnavailable("Upload did not return an ownership ETag.")
            return result["etag"]
        except (AzureError, StorageUnavailable, OSError) as exc:
            raise StorageUnavailable("Candidate upload failed.") from exc

    def _cleanup(self, owned: list[tuple[str, str]]) -> None:
        for key, etag in reversed(owned):
            try:
                self.container.delete_blob(key, etag=etag, match_condition=MatchConditions.IfNotModified)
            except (AzureError, StorageUnavailable, OSError):
                logging.exception("Could not clean an owned Blob candidate: %s", key)

    def publish(self, project: Project, state: ConversationState, photos: Mapping[int, BinaryIO]) -> None:
        if state.project_id != project.project_id or set(photos) != {p.photo_id for p in project.photos}:
            raise CollageError("Prepared project/state/photo identity mismatch.")
        attempt_id = uuid4().hex
        prefix = f"{self.prefix}candidates/{project.project_id}/{attempt_id}/"
        owned: list[tuple[str, str]] = []
        preserve = False

        def upload(parts, raw, content_type):
            key = prefix + "/".join(parts)
            owned.append((key, self._upload(key, raw, content_type)))
            return ObjectReference(attempt_id=attempt_id, sha256=digest(raw), size=len(raw))

        try:
            references = {}
            for photo in project.photos:
                data = bytearray()
                while chunk := photos[photo.photo_id].read(1024 * 1024):
                    if len(data) + len(chunk) > MAX_FILE_BYTES:
                        raise PhotoSizeError("Photo exceeds 25 MiB.")
                    data.extend(chunk)
                raw = bytes(data)
                references[photo.asset_id] = upload(
                    ("photos", photo.asset_id), raw,
                    "image/jpeg" if photo_extension(photo) == ".jpg" else "image/png",
                )
            project_raw, state_raw = canonical(project), canonical(state)
            if max(len(project_raw), len(state_raw)) > MAX_JSON_BYTES:
                raise CollageError("Prepared record exceeds the 1 MiB limit.")
            project_ref = upload(("project.json",), project_raw, "application/json")
            state_ref = upload(record_parts("state", "state"), state_raw, "application/json")
            head = Completion(
                schema_version=2, owner_id=OWNER_ID, project_id=project.project_id,
                attempt_id=attempt_id, project=project_ref, photos=references,
                records={"state": {"state": state_ref}, "event": {}, "proposal": {},
                         "attempt": {}, "operation": {}, "selection": {}},
            )
            preserve = True
            try:
                self._upload(self.completion_key(project.project_id), canonical(head), "application/json")
            except StorageUnavailable as exc:
                cause = exc.__cause__
                if isinstance(cause, HttpResponseError) and getattr(cause, "error_code", None) in {
                    "BlobAlreadyExists", "ConditionNotMet",
                }:
                    preserve = False
                    raise ProjectExists("That project ID is already saved.") from exc
                if isinstance(cause, HttpResponseError) and cause.status_code is not None and (
                    400 <= cause.status_code < 500 and cause.status_code != 408
                ):
                    preserve = False
                    raise StorageUnavailable("Completion publication was rejected.") from exc
                raise StorageOutcomeUnknown("Look up the project before any further create.") from exc
        finally:
            if not preserve:
                self._cleanup(owned)


class BlobConversationStorage:
    supports_acceptance = False

    def __init__(self, storage: BlobProjectStorage, head: Completion, etag: str, *, lease=None):
        self.storage = storage
        self.project_id = head.project_id
        self.head = head
        self.etag = etag
        self.lease = lease
        self.closed = False
        self.lost = False
        self._confirmed = monotonic()
        self._lease_lock = threading.RLock()
        self._depth = 0
        self._owned: list[tuple[str, str]] = []
        self._cache: OrderedDict[str, bytes] = OrderedDict()
        self._cache_bytes = 0
        self._project: Project | None = None

    def _referenced(self, reference: ObjectReference, *parts: str) -> bytes:
        key = self.storage.object_key(self.project_id, reference, *parts)
        if key not in self._cache:
            raw = self.storage._read(key, reference.size)
            if len(raw) != reference.size or digest(raw) != reference.sha256:
                raise CollageError("Saved Blob object identity/digest changed.")
            self._remember(key, raw)
        return self._cache[key]

    def _remember(self, key: str, raw: bytes) -> None:
        while self._cache and self._cache_bytes + len(raw) > MAX_PREVIEW_BYTES:
            _, previous = self._cache.popitem(last=False)
            self._cache_bytes -= len(previous)
        self._cache[key] = raw
        self._cache_bytes += len(raw)

    def project(self) -> Project:
        if self._project is not None:
            return self._project
        project = Project.model_validate(parse_json(self._referenced(self.head.project, "project.json")))
        if project.project_id != self.project_id or project.current_version is not None:
            raise CollageError("Project identity or unsupported accepted version.")
        if set(self.head.photos) != {photo.asset_id for photo in project.photos}:
            raise CollageError("Project photo references differ.")
        for photo in project.photos:
            reference = self.head.photos[photo.asset_id]
            properties = self.storage._properties(
                self.storage.object_key(self.project_id, reference, "photos", photo.asset_id),
            )
            if properties.size != reference.size:
                raise CollageError("Saved photo size changed.")
        self._project = project
        return project

    def identities(self, kind: RecordKind) -> list[str]:
        return sorted(self.head.records[kind], key=lambda identity: (len(identity), identity))

    def read(self, kind: RecordKind, identity: str) -> object | None:
        parts = record_parts(kind, identity)
        reference = self.head.records[kind].get(identity)
        return None if reference is None else parse_json(self._referenced(reference, *parts))

    def check_write(self) -> None:
        with self._lease_lock:
            if self.lease is None or self.closed or self.lost:
                raise StorageUnavailable("No confirmed project writer; dispatch/publication is blocked.")
            if monotonic() - self._confirmed >= LEASE_SECONDS - 5:
                self.lost = True
                raise StorageUnavailable("Project writer confirmation expired.")
            try:
                self.lease.renew()
                self._confirmed = monotonic()
            except (AzureError, StorageUnavailable, OSError) as exc:
                self.lost = True
                raise StorageUnavailable("Project lease was lost or renewal is unconfirmed.") from exc

    def _candidate(self, raw: bytes, parts: tuple[str, ...], content_type: str) -> ObjectReference:
        self.check_write()
        reference = ObjectReference(attempt_id=uuid4().hex, sha256=digest(raw), size=len(raw))
        key = self.storage.object_key(self.project_id, reference, *parts)
        self._owned.append((key, self.storage._upload(key, raw, content_type)))
        self._remember(key, raw)
        return reference

    @contextmanager
    def checkpoint(self):
        outer = self._depth == 0
        previous = self.head.model_copy(deep=True) if outer else None
        if outer:
            self.check_write()
            self._owned = []
        self._depth += 1
        ambiguous = False
        try:
            yield
            if outer:
                self.check_write()
                validated = Completion.model_validate(self.head.model_dump())
                raw = canonical(validated)
                if len(raw) > MAX_JSON_BYTES:
                    raise CollageError("Publication head exceeds the 1 MiB limit.")
                try:
                    result = self.storage.container.get_blob_client(
                        self.storage.completion_key(self.project_id),
                    ).upload_blob(
                        raw, overwrite=True, lease=self.lease.id, etag=self.etag,
                        match_condition=MatchConditions.IfNotModified,
                        content_settings=ContentSettings(content_type="application/json"),
                        max_concurrency=1,
                    )
                except HttpResponseError as exc:
                    self.lost = True
                    if exc.status_code is not None and 400 <= exc.status_code < 500 and exc.status_code != 408:
                        raise StorageUnavailable("Fenced head publication was rejected.") from exc
                    ambiguous = True
                    raise StorageOutcomeUnknown("Head publication is unconfirmed; inspect the saved operation.") from exc
                except (AzureError, StorageUnavailable, OSError) as exc:
                    self.lost = True
                    ambiguous = True
                    raise StorageOutcomeUnknown("Head publication is unconfirmed; inspect the saved operation.") from exc
                if not isinstance(result.get("etag"), str):
                    ambiguous = True
                    self.lost = True
                    raise StorageOutcomeUnknown("Head publication returned no confirmed ETag.")
                self.head = validated
                self.etag = result["etag"]
        except Exception:
            if outer:
                self.head = previous
                if not ambiguous:
                    self.storage._cleanup(self._owned)
            raise
        finally:
            self._depth -= 1
            if outer:
                self._owned = []

    def write(self, kind: RecordKind, identity: str, value: BaseModel) -> None:
        raw = canonical(value)
        if len(raw) > MAX_JSON_BYTES:
            raise CollageError("Conversation record exceeds the 1 MiB limit.")
        with self.checkpoint():
            self.head.records[kind][identity] = self._candidate(raw, record_parts(kind, identity), "application/json")

    def publish_proposal(self, proposal: Proposal, preview: Path) -> None:
        raw = read_preview(preview)
        self._validate_preview(proposal, raw)
        with self.checkpoint():
            self.write("proposal", proposal.proposal_id, proposal)
            self.head.previews[proposal.proposal_id] = self._candidate(
                raw, ("conversation", "proposals", proposal.proposal_id, "preview.png"), "image/png",
            )

    @staticmethod
    def _validate_preview(proposal: Proposal, raw: bytes) -> None:
        if len(raw) > MAX_PREVIEW_BYTES or digest(raw) != proposal.preview_digest:
            raise CollageError("Preview size/digest mismatch.")
        import io
        from PIL import Image

        try:
            with Image.open(io.BytesIO(raw)) as image:
                if image.format != "PNG" or image.size != (
                    proposal.recipe.canvas.width, proposal.recipe.canvas.height,
                ) or getattr(image, "n_frames", 1) != 1:
                    raise CollageError("Preview format/dimensions mismatch.")
                image.verify()
        except (OSError, ValueError) as exc:
            raise CollageError("Saved preview is not a valid PNG.") from exc

    def preview(self, proposal_id: str) -> bytes:
        record_parts("proposal", proposal_id)
        reference = self.head.previews.get(proposal_id)
        if reference is None:
            raise CollageError("Unknown or unpublished proposal ID.")
        proposal = Proposal.model_validate(self.read("proposal", proposal_id))
        raw = self._referenced(reference, "conversation", "proposals", proposal_id, "preview.png")
        self._validate_preview(proposal, raw)
        return raw

    def photo(self, project: Project, photo_id: int) -> tuple[bytes, str]:
        photos = {photo.photo_id: photo for photo in project.photos}
        if photo_id not in photos:
            raise PhotoNotFound("Photo not found.")
        photo = photos[photo_id]
        reference = self.head.photos.get(photo.asset_id)
        if reference is None:
            raise CollageError("Missing imported photo reference.")
        raw = self._referenced(reference, "photos", photo.asset_id)
        with tempfile.TemporaryDirectory(prefix="collage-blob-photo-") as directory:
            path = Path(directory) / "photo"
            path.write_bytes(raw)
            image, extension = load_photo(path)
            with image:
                if image.size != (photo.width, photo.height) or extension != photo_extension(photo):
                    raise CollageError("Saved photo metadata changed.")
        return raw, "image/jpeg" if extension == ".jpg" else "image/png"

    @contextmanager
    def photo_paths(self):
        project = self.project()
        with tempfile.TemporaryDirectory(prefix="collage-blob-render-") as directory:
            paths = {}
            for photo in project.photos:
                raw, _ = self.photo(project, photo.photo_id)
                path = Path(directory) / f"{photo.asset_id}{photo_extension(photo)}"
                path.write_bytes(raw)
                paths[photo.photo_id] = path
            yield paths
