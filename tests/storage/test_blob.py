from contextlib import ExitStack
import io
import json
from types import SimpleNamespace
from unittest.mock import Mock

from azure.core import MatchConditions
from azure.core.credentials import AccessToken
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError, ServiceRequestError
from azure.core.pipeline.transport import HttpResponse, RequestsTransport
from azure.storage.blob import ContainerClient
import pytest
from requests.structures import CaseInsensitiveDict

from ai_collage.agent.conversation import Conversation
from ai_collage.application.projects import FlowError, ProjectFlow, ProjectSetup
from ai_collage.storage.blob import BlobProjectStorage
from ai_collage.engine.models import MAX_FILE_BYTES, CollageError
from ai_collage.engine.projects import ProjectStore
from ai_collage.storage.contracts import ProjectExists, ProjectNotFound, StorageOutcomeUnknown, StorageUnavailable


def azure_error(kind, code, status):
    error = kind(message="injected Azure failure")
    error.error_code = code
    error.status_code = status
    return error


@pytest.fixture
def blobs():
    objects = {}
    etags = {}
    container = Mock(spec=ContainerClient)
    sequence = 0

    def upload(key, data, **kwargs):
        nonlocal sequence
        assert kwargs["overwrite"] is False
        if key in objects:
            raise azure_error(HttpResponseError, "BlobAlreadyExists", 409)
        objects[key] = data if isinstance(data, bytes) else data.read()
        sequence += 1
        etags[key] = str(sequence)
        return {"etag": etags[key]}

    def client(key):
        def properties():
            if key not in objects:
                raise azure_error(ResourceNotFoundError, "BlobNotFound", 404)
            return SimpleNamespace(size=len(objects[key]), etag=etags[key])

        def download(**kwargs):
            assert kwargs["match_condition"] == MatchConditions.IfNotModified
            assert kwargs["etag"] == etags[key]
            assert kwargs["length"] <= MAX_FILE_BYTES + 1
            return SimpleNamespace(chunks=lambda: iter([objects[key]]))

        return SimpleNamespace(
            get_blob_properties=properties, download_blob=download,
            upload_blob=lambda data, **kwargs: container.uploads(key, data, **kwargs),
        )

    def delete(key, **kwargs):
        assert kwargs == {"etag": etags[key], "match_condition": MatchConditions.IfNotModified}
        del objects[key]
        del etags[key]

    container.uploads = Mock(side_effect=upload)
    container.get_blob_client.side_effect = client
    container.delete_blob.side_effect = delete
    container.list_blobs.side_effect = lambda **kwargs: [
        SimpleNamespace(name=name) for name in objects
        if name.startswith(kwargs["name_starts_with"])
    ]
    return container, objects


@pytest.fixture
def prepared(store, sources):
    project = store.create("trip", sources)
    state = Conversation(store, "trip", canvas=(900, 1600)).state
    return store, project, state


def publish(storage, prepared):
    store, project, state = prepared
    with ExitStack() as stack:
        streams = {n: stack.enter_context(p.open("rb")) for n, p in store.photo_paths(project).items()}
        storage.publish(project, state, streams)


def test_blob_lifecycle_uses_conditional_publication_and_reopens_without_local_data(blobs, prepared, tmp_path):
    container, objects = blobs
    storage = BlobProjectStorage(container, "test-019b")
    assert storage.project_ids() == []
    publish(storage, prepared)
    assert len(objects) == 5
    assert container.uploads.call_args_list[-1].args[0] == storage.completion_key("trip")
    before = dict(objects)
    writes = container.uploads.call_count
    flow = ProjectFlow(ProjectStore(tmp_path / "different-empty-root"), BlobProjectStorage(container, "test-019b"))
    assert flow.list() == [{"project_id": "trip", "canvas": {"width": 900, "height": 1600}, "photo_count": 2}]
    assert flow.detail("trip")["photos"] == [
        {"photo_id": p.photo_id, "width": p.width, "height": p.height} for p in prepared[1].photos
    ]
    for number, path in prepared[0].photo_paths(prepared[1]).items():
        assert flow.photo("trip", number) == (path.read_bytes(), "image/png")
    assert objects == before
    assert writes == container.uploads.call_count
    assert not flow.store.data_dir.exists()
    assert not any("uploads" in key or "\\" in key for key in objects)


def test_unpublished_candidates_are_not_projects_and_duplicate_cannot_replace_winner(blobs, prepared):
    container, objects = blobs
    storage = BlobProjectStorage(container, "test-019b")
    objects[storage.prefix + "candidates/orphan"] = b"private"
    assert storage.project_ids() == []
    publish(storage, prepared)
    before = dict(objects)
    with pytest.raises(ProjectExists):
        publish(BlobProjectStorage(container, "test-019b"), prepared)
    assert objects == before


@pytest.mark.parametrize("failure_index", [1, 2, 3, 4])
def test_candidate_failure_cleans_only_confirmed_owned_objects(blobs, prepared, failure_index):
    container, objects = blobs
    storage = BlobProjectStorage(container, "test-019b")
    objects[storage.prefix + "candidates/unrelated"] = b"keep"
    original = container.uploads.side_effect
    calls = 0

    def fail(key, data, **kwargs):
        nonlocal calls
        calls += 1
        if calls == failure_index:
            raise ServiceRequestError("injected upload failure")
        return original(key, data, **kwargs)

    container.uploads.side_effect = fail
    with pytest.raises(StorageUnavailable):
        publish(storage, prepared)
    assert objects == {storage.prefix + "candidates/unrelated": b"keep"}


@pytest.mark.parametrize("committed", [False, True])
def test_lost_completion_response_preserves_candidates_and_supports_lookup(blobs, prepared, committed):
    container, objects = blobs
    storage = BlobProjectStorage(container, "test-019b")
    original = container.uploads.side_effect

    def lose(key, data, **kwargs):
        if key == storage.completion_key("trip"):
            if committed:
                original(key, data, **kwargs)
            raise ServiceRequestError("lost completion response")
        return original(key, data, **kwargs)

    container.uploads.side_effect = lose
    with pytest.raises(StorageOutcomeUnknown):
        publish(storage, prepared)
    assert len(objects) == (5 if committed else 4)
    container.delete_blob.assert_not_called()
    if committed:
        assert storage.load("trip") == prepared[1:]
    else:
        with pytest.raises(ProjectNotFound):
            storage.load("trip")


def test_confirmed_completion_rejection_cleans_candidates_but_server_error_does_not(blobs, prepared):
    container, objects = blobs
    storage = BlobProjectStorage(container, "test-019b")
    original = container.uploads.side_effect

    for code, status, expected in [("AuthorizationFailure", 403, StorageUnavailable), ("InternalError", 500, StorageOutcomeUnknown)]:
        def fail(key, data, **kwargs):
            if key == storage.completion_key("trip"):
                raise azure_error(HttpResponseError, code, status)
            return original(key, data, **kwargs)
        container.uploads.side_effect = fail
        with pytest.raises(expected):
            publish(storage, prepared)
        assert len(objects) == (0 if status == 403 else 4)


@pytest.mark.parametrize("target,change", [
    ("completion", lambda raw: b'{"schema_version":1,"schema_version":1}'),
    ("completion", lambda raw: json.dumps({**json.loads(raw), "schema_version": 2}).encode()),
    ("completion", lambda raw: json.dumps({**json.loads(raw), "attempt_id": "../outside"}).encode()),
    ("completion", lambda raw: json.dumps({**json.loads(raw), "surprise": True}).encode()),
    ("project.json", lambda raw: json.dumps({**json.loads(raw), "project_id": "other"}).encode()),
    ("conversation/state.json", lambda raw: b"{}"),
    ("photo", lambda raw: b""),
])
def test_invalid_published_state_is_not_missing_or_empty(blobs, prepared, tmp_path, target, change):
    container, objects = blobs
    storage = BlobProjectStorage(container, "test-019b")
    publish(storage, prepared)
    key = storage.completion_key("trip") if target == "completion" else next(
        key for key in objects if ("/photos/" in key if target == "photo" else key.endswith("/" + target))
    )
    objects[key] = change(objects[key])
    flow = ProjectFlow(ProjectStore(tmp_path / "guards"), storage)
    with pytest.raises(FlowError) as error:
        flow.list()
    assert error.value.code == "invalid_project_state"
    assert error.value.status == 409


def test_missing_published_asset_and_bad_photo_bytes_are_invalid_saved_state(blobs, prepared, tmp_path):
    container, objects = blobs
    storage = BlobProjectStorage(container, "test-019b")
    publish(storage, prepared)
    key = next(key for key in objects if "/photos/" in key)
    original = objects[key]
    del objects[key]
    flow = ProjectFlow(ProjectStore(tmp_path / "guards"), storage)
    with pytest.raises(FlowError, match="incomplete or invalid"):
        flow.detail("trip")
    objects[key] = b"not an image"
    with pytest.raises(FlowError, match="missing or invalid"):
        flow.photo("trip", 1)
    objects[key] = original
    with pytest.raises(FlowError) as error:
        flow.photo("trip", 99)
    assert error.value.status == 404


@pytest.mark.parametrize("code,status", [("ContainerNotFound", 404), ("AuthorizationFailure", 403)])
def test_container_and_authorization_failures_do_not_look_like_missing_projects(blobs, code, status):
    container, _ = blobs
    storage = BlobProjectStorage(container, "test-019b")
    container.get_blob_client.side_effect = azure_error(ResourceNotFoundError if status == 404 else HttpResponseError, code, status)
    with pytest.raises(StorageUnavailable):
        storage.exists("trip")
    container.list_blobs.side_effect = azure_error(HttpResponseError, code, status)
    with pytest.raises(StorageUnavailable):
        storage.project_ids()


def test_cleanup_failure_is_logged_without_masking_original_failure(blobs, prepared, caplog):
    container, _ = blobs
    original = container.uploads.side_effect

    def fail(key, data, **kwargs):
        if key.endswith("project.json"):
            raise ServiceRequestError("primary upload failure")
        return original(key, data, **kwargs)

    container.uploads.side_effect = fail
    container.delete_blob.side_effect = ServiceRequestError("cleanup failed")
    with pytest.raises(StorageUnavailable) as error:
        publish(BlobProjectStorage(container, "test-019b"), prepared)
    assert "primary upload failure" in str(error.value.__cause__)
    assert "Could not clean an owned Blob candidate" in caplog.text


def test_oversized_stream_never_publishes_completion(blobs, prepared):
    container, objects = blobs
    store, project, state = prepared
    with pytest.raises(CollageError):
        BlobProjectStorage(container, "test-019b").publish(
            project, state, {1: io.BytesIO(b"x" * (MAX_FILE_BYTES + 1)), 2: io.BytesIO(b"unused")},
        )
    assert objects == {}


def test_real_sdk_uploads_are_conditional_and_return_etags_without_network(prepared, monkeypatch):
    sent = []

    class Created(HttpResponse):
        def __init__(self, request):
            super().__init__(request, None)
            self.status_code = 201
            self.headers = CaseInsensitiveDict({
                "ETag": '"confirmed"', "Last-Modified": "Fri, 27 Nov 2026 10:00:00 GMT",
                "Content-Length": "0",
            })

        def body(self):
            return b""

    def send(self, request, **kwargs):
        sent.append(request)
        return Created(request)

    monkeypatch.setattr(RequestsTransport, "send", send)
    credential = SimpleNamespace(get_token=lambda *args, **kwargs: AccessToken("offline-fixture-token", 4000000000))
    with ContainerClient(
        "https://offline.blob.core.windows.net", "collage", credential=credential, retry_total=0,
    ) as container:
        publish(BlobProjectStorage(container, "test-019b"), prepared)
    assert len(sent) == 5
    assert all(request.method == "PUT" and request.headers["If-None-Match"] == "*" for request in sent)
    assert "/published/trip.json" in sent[-1].url


def test_download_bounds_actual_chunks_even_when_size_metadata_lies(blobs):
    container, _ = blobs
    container.get_blob_client.side_effect = None
    client = container.get_blob_client.return_value
    client.get_blob_properties.return_value = SimpleNamespace(size=1, etag="unchanged")
    client.download_blob.return_value = SimpleNamespace(chunks=lambda: iter([b"too much"]))
    with pytest.raises(CollageError, match="size limit"):
        BlobProjectStorage(container, "test-019b")._read("bounded", 4)
