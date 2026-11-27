from contextlib import ExitStack, contextmanager, nullcontext
import asyncio
import io
import json
import threading
from types import SimpleNamespace
from time import monotonic
from unittest.mock import Mock
from uuid import uuid4
from urllib.parse import urlsplit

import azure.functions as func
from azure.core import MatchConditions
from azure.core.credentials import AccessToken
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError, ServiceRequestError
from azure.core.pipeline.transport import HttpResponse, RequestsTransport
from azure.storage.blob import ContainerClient
import pytest
from requests.structures import CaseInsensitiveDict
from PIL import Image
import httpx

from ai_collage.agent.conversation import Conversation
from ai_collage.application.projects import FlowError, ProjectFlow, ProjectSetup
from ai_collage.storage.blob import BlobProjectStorage, Completion
from ai_collage.engine.models import MAX_FILE_BYTES, CollageError
from ai_collage.engine.projects import ProjectStore
from ai_collage.storage.contracts import ProjectExists, ProjectNotFound, StorageBusy, StorageOutcomeUnknown, StorageUnavailable
from ai_collage.application.conversation import (
    ConversationFlow, ConversationSettings, GenerationRequest, SelectionSubmission, Submission,
)
from ai_collage.agent.models import ConversationState
from ai_collage.agent.requests import RequestLog, StageTimeout
from ai_collage.engine.geometry import resolve_layout
from ai_collage.engine.imaging import render_layout
from ai_collage.engine.models import InputLayout
from ai_collage.storage.contracts import MAX_PREVIEW_BYTES
from api.proof_fixture import PROMPTS, ScriptedModel, generated_photos
from ..agent.test_agent import asyncio_wakeup_pair


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
    leases = {}
    container.leases = leases
    sequence = 0

    def upload(key, data, **kwargs):
        nonlocal sequence
        if kwargs["overwrite"]:
            if key not in objects or kwargs.get("lease") != leases.get(key):
                raise azure_error(HttpResponseError, "LeaseIdMismatchWithBlobOperation", 412)
            if kwargs.get("etag") != etags[key]:
                raise azure_error(HttpResponseError, "ConditionNotMet", 412)
            assert kwargs["match_condition"] == MatchConditions.IfNotModified
        elif key in objects:
            raise azure_error(HttpResponseError, "BlobAlreadyExists", 409)
        objects[key] = data if isinstance(data, bytes) else data.read()
        sequence += 1
        etags[key] = str(sequence)
        return {"etag": etags[key]}

    def client(key):
        def properties():
            if key not in objects:
                raise azure_error(ResourceNotFoundError, "BlobNotFound", 404)
            return SimpleNamespace(
                size=len(objects[key]), etag=etags[key],
                lease=SimpleNamespace(status="locked" if key in leases else "unlocked"),
            )

        def acquire(**kwargs):
            assert kwargs["lease_duration"] == 60
            if key in leases:
                raise azure_error(HttpResponseError, "LeaseAlreadyPresent", 409)
            identity = str(uuid4())
            leases[key] = identity

            def renew():
                if leases.get(key) != identity:
                    raise azure_error(HttpResponseError, "LeaseIdMismatchWithLeaseOperation", 412)

            def release():
                renew()
                del leases[key]

            return SimpleNamespace(id=identity, renew=Mock(side_effect=renew), release=Mock(side_effect=release))

        def download(**kwargs):
            assert kwargs["match_condition"] == MatchConditions.IfNotModified
            assert kwargs["etag"] == etags[key]
            assert kwargs["length"] <= MAX_PREVIEW_BYTES + 1
            return SimpleNamespace(chunks=lambda: iter([objects[key]]))

        return SimpleNamespace(
            get_blob_properties=properties, download_blob=download,
            upload_blob=lambda data, **kwargs: container.uploads(key, data, **kwargs),
            acquire_lease=acquire,
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
    ("completion", lambda raw: json.dumps({**json.loads(raw), "schema_version": 1}).encode()),
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
    with pytest.raises(FlowError, match="invalid") as error:
        flow.photo("trip", 1)
    assert error.value.code == "invalid_project_state"
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


@pytest.fixture
def web_blob(blobs, tmp_path, monkeypatch):
    monkeypatch.setattr("ai_collage.agent.provider.FoundryModel",
                        lambda: pytest.fail("The model-free fixture must never construct Foundry."))
    container, objects = blobs
    storage = BlobProjectStorage(container, "test-019c")
    store = ProjectStore(tmp_path / "first-root")
    originals = generated_photos()
    ProjectFlow(store, storage).create(
        ProjectSetup(project_id="proof", canvas={"width": 1200, "height": 1800}),
        [io.BytesIO(raw) for raw in originals],
    )
    flow = ConversationFlow(store, ConversationSettings(live=True), ScriptedModel(), storage=storage)
    return flow, container, objects, originals


def scripted_send(flow, prompt):
    submission = Submission(request_id=str(uuid4()), prompt=prompt, revision=flow.detail("proof")["revision"])
    prepared, created = asyncio.run(flow.interpret("proof", submission))
    assert created and prepared["status"] == "prepared"
    completed = asyncio.run(flow.generate(
        "proof", submission.request_id, GenerationRequest(revision=prepared["revision"]),
    ))
    assert completed["status"] == "completed"
    return submission, prepared, completed


def test_complete_blob_workflow_restarts_without_local_projects_and_preserves_snapshots(web_blob, tmp_path):
    flow, container, objects, originals = web_blob
    initial = flow.storage.conversation("proof")
    for prompt in PROMPTS:
        scripted_send(flow, prompt)
    latest = flow.detail("proof")
    assert [p["proposal_id"] for p in latest["proposals"]] == ["P001", "P002"]
    assert latest["baseline"] == {"proposal_id": "P002"}
    pngs = {p: flow.preview("proof", p) for p in ("P001", "P002")}
    assert pngs["P001"] != pngs["P002"]
    assert ConversationState.model_validate(initial.read("state", "state")).history == []
    restored = ConversationFlow(
        ProjectStore(tmp_path / "second-root"), ConversationSettings(live=False),
        storage=BlobProjectStorage(container, "test-019c"),
    )
    assert {**restored.detail("proof"), "live_enabled": True} == latest
    action = SelectionSubmission(
        action_id=str(uuid4()), proposal_id="P001", revision=latest["revision"], abandon_pending=False,
    )
    selected, created = restored.select("proof", action)
    assert created and selected["status"] == "completed"
    assert restored.detail("proof")["baseline"] == {"proposal_id": "P001"}
    before = dict(objects)
    assert not restored.select("proof", action)[1]
    assert restored.selection("proof", action.action_id)["status"] == "completed"
    assert objects == before
    for number, raw in enumerate(originals, 1):
        assert ProjectFlow(restored.store, restored.storage).photo("proof", number) == (raw, "image/png")
    for p, raw in pngs.items():
        assert restored.preview("proof", p) == raw
    session = restored.storage.conversation("proof")
    state = ConversationState.model_validate(session.read("state", "state"))
    assert state.photo_names[0].name == "bridge"
    log = RequestLog(restored.store, "proof", persistence=session)
    assert len(log.attempts()) == 4
    assert log.summary()["unknown_usage_attempts"] == [1, 2, 3, 4]
    assert not restored.store.data_dir.exists()
    assert not flow.store.projects_dir.exists() and not flow.store.uploads_dir.exists()
    assert not container.leases


@pytest.mark.parametrize("window", ["claim", "reservation", "event", "prepared"])
@pytest.mark.parametrize("committed", [False, True])
def test_lost_checkpoint_response_preserves_paid_claim_and_never_redispatches(web_blob, window, committed):
    flow, container, objects, _ = web_blob
    original = container.uploads.side_effect
    failed = False
    head_key = flow.storage.completion_key("proof")

    def lose(key, raw, **kwargs):
        nonlocal failed
        if key == head_key and kwargs["overwrite"] and not failed:
            head = Completion.model_validate(json.loads(raw))
            if head.records["operation"]:
                identity, reference = next(iter(head.records["operation"].items()))
                operation = json.loads(objects[flow.storage.object_key(
                    "proof", reference, "web-operations", identity + ".json",
                )])
                reached = (
                    window == "claim" and not head.records["attempt"]
                    or window == "reservation" and bool(head.records["attempt"]) and not head.records["event"]
                    or window == "event" and bool(head.records["event"]) and operation["status"] == "interpreting"
                    or window == "prepared" and operation["status"] == "prepared"
                )
                if reached:
                    failed = True
                    if committed:
                        original(key, raw, **kwargs)
                    raise ServiceRequestError("lost checkpoint response")
        return original(key, raw, **kwargs)

    container.uploads.side_effect = lose
    submission = Submission(request_id=str(uuid4()), prompt=PROMPTS[0], revision=flow.detail("proof")["revision"])
    with pytest.raises(StorageOutcomeUnknown):
        asyncio.run(flow.interpret("proof", submission))
    assert failed and not container.leases
    restored = ConversationFlow(flow.store, flow.settings, ScriptedModel(), storage=flow.storage)
    detail = restored.detail("proof")
    if window == "claim" and not committed:
        assert detail["operation"] is None
    elif window == "prepared" and committed:
        assert detail["operation"]["status"] == "prepared"
    else:
        assert detail["operation"]["status"] == "uncertain"
        with pytest.raises(FlowError, match="existing operation"):
            asyncio.run(restored.interpret("proof", Submission(
                request_id=str(uuid4()), prompt=PROMPTS[0], revision=detail["revision"],
            )))
    before = dict(objects)
    if detail["operation"] is not None:
        duplicate, created = asyncio.run(restored.interpret("proof", submission))
        assert not created and duplicate["status"] in {"uncertain", "prepared"}
        assert objects == before


def test_lease_fences_independent_writers_and_expiration_does_not_replay_claim(web_blob):
    flow, container, objects, _ = web_blob
    other = BlobProjectStorage(container, "test-019c")
    key = flow.storage.completion_key("proof")
    with flow.storage.mutation("proof") as first:
        before = dict(objects)
        with pytest.raises(StorageBusy):
            with other.mutation("proof"):
                pytest.fail("Competing writer must not enter.")
        del container.leases[key]
        with other.mutation("proof"):
            with pytest.raises(StorageUnavailable):
                first.write("state", "state", ConversationState.model_validate(first.read("state", "state")))
        assert objects == before
    assert not container.leases


@pytest.mark.parametrize("window", ["claimed", "completed"])
@pytest.mark.parametrize("committed", [False, True])
def test_selection_final_checkpoint_is_atomic_and_ambiguous_claim_blocks_changes(web_blob, window, committed):
    flow, container, objects, _ = web_blob
    for prompt in PROMPTS:
        scripted_send(flow, prompt)
    before = flow.detail("proof")
    original = container.uploads.side_effect

    def lose(key, raw, **kwargs):
        if key == flow.storage.completion_key("proof") and kwargs["overwrite"]:
            head = Completion.model_validate(json.loads(raw))
            if head.records["selection"]:
                identity, reference = next(iter(head.records["selection"].items()))
                action = json.loads(objects[flow.storage.object_key(
                    "proof", reference, "web-selections", identity + ".json",
                )])
                if action["status"] == window:
                    if committed:
                        original(key, raw, **kwargs)
                    raise ServiceRequestError("lost selection final publication")
        return original(key, raw, **kwargs)

    container.uploads.side_effect = lose
    action = SelectionSubmission(
        action_id=str(uuid4()), proposal_id="P001", revision=before["revision"], abandon_pending=False,
    )
    with pytest.raises(StorageOutcomeUnknown):
        flow.select("proof", action)
    detail = flow.detail("proof")
    if window == "completed" and committed:
        assert detail["baseline"] == {"proposal_id": "P001"}
        assert flow.selection("proof", action.action_id)["status"] == "completed"
        assert any(message["role"] == "activity" for message in detail["messages"])
    else:
        assert detail["baseline"] == before["baseline"]
        assert not any(message["role"] == "activity" for message in detail["messages"])
        if window == "claimed" and not committed:
            with pytest.raises(FlowError) as error:
                flow.selection("proof", action.action_id)
            assert error.value.status == 404
        else:
            assert flow.selection("proof", action.action_id)["status"] == "uncertain"
            assert not detail["selection"]["enabled"]


def test_real_sdk_checkpoint_carries_lease_and_etag_fencing(blobs, prepared, monkeypatch):
    container, _ = blobs
    fake = BlobProjectStorage(container, "test-019c")
    publish(fake, prepared)
    head, etag = fake._head("trip")
    sent = []
    lease_id = str(uuid4())

    class Response(HttpResponse):
        def __init__(self, request):
            super().__init__(request, None)
            action = request.headers.get("x-ms-lease-action")
            self.status_code = 200 if action in {"renew", "release"} else 201
            self.headers = CaseInsensitiveDict({
                "ETag": '"confirmed"', "Last-Modified": "Fri, 27 Nov 2026 10:00:00 GMT",
                "Content-Length": "0", "x-ms-lease-id": lease_id,
            })
        def body(self):
            return b""

    def send(self, request, **kwargs):
        sent.append(request)
        return Response(request)

    monkeypatch.setattr(RequestsTransport, "send", send)
    credential = SimpleNamespace(get_token=lambda *args, **kwargs: AccessToken("offline-fixture-token", 4000000000))
    with ContainerClient("https://offline.blob.core.windows.net", "collage", credential=credential, retry_total=0) as client:
        storage = BlobProjectStorage(client, "test-019c")
        monkeypatch.setattr(storage, "_properties", lambda *args, **kwargs: object())
        monkeypatch.setattr(storage, "_head", lambda project_id: (head.model_copy(deep=True), etag))
        with storage.mutation("trip") as session:
            session.write("state", "state", prepared[2])
    commits = [request for request in sent if "x-ms-lease-action" not in request.headers
               and "/published/" in request.url]
    assert len(commits) == 1
    assert commits[0].headers["x-ms-lease-id"] == lease_id
    assert commits[0].headers["If-Match"] == etag
    assert any(request.headers.get("x-ms-lease-action") == "release" for request in sent)


def test_download_bounds_actual_chunks_even_when_size_metadata_lies(blobs):
    container, _ = blobs
    container.get_blob_client.side_effect = None
    client = container.get_blob_client.return_value
    client.get_blob_properties.return_value = SimpleNamespace(size=1, etag="unchanged")
    client.download_blob.return_value = SimpleNamespace(chunks=lambda: iter([b"too much"]))
    with pytest.raises(CollageError, match="size limit"):
        BlobProjectStorage(container, "test-019b")._read("bounded", 4)


def test_short_photo_stream_reads_are_consumed_to_eof(blobs, prepared):
    class ShortReads(io.BytesIO):
        def read(self, size=-1):
            return super().read(min(size, 7))

    container, _ = blobs
    store, project, state = prepared
    originals = {n: path.read_bytes() for n, path in store.photo_paths(project).items()}
    storage = BlobProjectStorage(container, "test-019c")
    storage.publish(project, state, {n: ShortReads(raw) for n, raw in originals.items()})
    assert all(storage.photo(project, n)[0] == raw for n, raw in originals.items())


@pytest.mark.parametrize("window", ["claim", "reservation", "proposal", "completed"])
@pytest.mark.parametrize("committed", [False, True])
def test_generation_checkpoint_failure_never_repeats_generation(web_blob, window, committed):
    flow, container, objects, _ = web_blob
    submission, _, _ = scripted_send(flow, PROMPTS[0])
    revision = flow.detail("proof")["revision"]
    second = Submission(request_id=str(uuid4()), prompt=PROMPTS[1], revision=revision)
    prepared, _ = asyncio.run(flow.interpret("proof", second))
    original = container.uploads.side_effect
    failed = False

    def lose(key, raw, **kwargs):
        nonlocal failed
        if key == flow.storage.completion_key("proof") and kwargs["overwrite"] and not failed:
            head = Completion.model_validate(json.loads(raw))
            ref = head.records["operation"][second.request_id]
            operation = json.loads(objects[flow.storage.object_key("proof", ref, "web-operations", second.request_id + ".json")])
            reached = (
                window == "claim" and operation["status"] == "generating" and len(head.records["attempt"]) == 3
                or window == "reservation" and len(head.records["attempt"]) == 4 and "P002" not in head.previews
                or window == "proposal" and "P002" in head.previews and operation["status"] == "generating"
                or window == "completed" and operation["status"] == "completed"
            )
            if reached:
                failed = True
                if committed:
                    original(key, raw, **kwargs)
                raise ServiceRequestError("lost generation checkpoint response")
        return original(key, raw, **kwargs)

    container.uploads.side_effect = lose
    request = GenerationRequest(revision=prepared["revision"])
    with pytest.raises(StorageOutcomeUnknown):
        asyncio.run(flow.generate("proof", second.request_id, request))
    assert failed and not container.leases
    restored = ConversationFlow(flow.store, flow.settings, ScriptedModel(), storage=flow.storage)
    status = restored.operation("proof", second.request_id)
    if window == "claim" and not committed:
        assert status["status"] == "prepared"
    else:
        assert status["status"] == ("completed" if window == "completed" and committed else "uncertain")
        writes = container.uploads.call_count
        assert asyncio.run(restored.generate("proof", second.request_id, request))["status"] == status["status"]
        assert container.uploads.call_count == writes
    assert restored.operation("proof", submission.request_id)["status"] == "completed"
    assert restored.preview("proof", "P001")


def test_expired_writer_during_render_keeps_previous_collage_and_paid_claim(web_blob, monkeypatch):
    flow, container, _, _ = web_blob
    scripted_send(flow, PROMPTS[0])
    original_png = flow.preview("proof", "P001")
    second = Submission(request_id=str(uuid4()), prompt=PROMPTS[1], revision=flow.detail("proof")["revision"])
    prepared, _ = asyncio.run(flow.interpret("proof", second))
    original = render_layout

    def lose(*args, **kwargs):
        original(*args, **kwargs)
        del container.leases[flow.storage.completion_key("proof")]

    monkeypatch.setattr("ai_collage.agent.conversation.render_layout", lose)
    with pytest.raises(StorageUnavailable):
        asyncio.run(flow.generate("proof", second.request_id, GenerationRequest(revision=prepared["revision"])))
    assert flow.detail("proof")["baseline"] == {"proposal_id": "P001"}
    assert flow.preview("proof", "P001") == original_png
    assert flow.operation("proof", second.request_id)["status"] == "uncertain"
    session = flow.storage.conversation("proof")
    assert len(RequestLog(flow.store, "proof", persistence=session).attempts()) == 4


def test_lost_writer_during_model_completion_preserves_consumed_pending_attempt(web_blob, monkeypatch, tmp_path):
    flow, container, _, _ = web_blob
    scripted_send(flow, PROMPTS[0])
    second = Submission(request_id=str(uuid4()), prompt=PROMPTS[1], revision=flow.detail("proof")["revision"])
    prepared, _ = asyncio.run(flow.interpret("proof", second))
    original = RequestLog.finish

    def lose(log, attempt):
        if log.stage == "generation":
            del container.leases[flow.storage.completion_key("proof")]
        original(log, attempt)

    monkeypatch.setattr(RequestLog, "finish", lose)
    with pytest.raises(StorageUnavailable):
        asyncio.run(flow.generate("proof", second.request_id, GenerationRequest(revision=prepared["revision"])))
    restored = ConversationFlow(ProjectStore(tmp_path / "restart"), flow.settings, ScriptedModel(), storage=flow.storage)
    assert restored.operation("proof", second.request_id)["status"] == "uncertain"
    assert restored.detail("proof")["baseline"] == {"proposal_id": "P001"}
    attempts = RequestLog(restored.store, "proof", persistence=flow.storage.conversation("proof")).attempts()
    assert len(attempts) == 4 and attempts[-1].status == "pending"
    writes = container.uploads.call_count
    asyncio.run(restored.generate("proof", second.request_id, GenerationRequest(revision=prepared["revision"])))
    assert container.uploads.call_count == writes


def test_expired_confirmation_blocks_dispatch_and_other_projects_remain_independent(web_blob, monkeypatch):
    flow, container, _, originals = web_blob
    ProjectFlow(flow.store, flow.storage).create(
        ProjectSetup(project_id="other", canvas={"width": 1200, "height": 1800}),
        [io.BytesIO(raw) for raw in originals],
    )
    with flow.storage.mutation("proof") as first:
        with flow.storage.mutation("other") as other:
            other.check_write()
        monkeypatch.setattr("ai_collage.storage.blob.monotonic", lambda: first._confirmed + 56)
        log = RequestLog(flow.store, "proof", persistence=first)
        with pytest.raises(StorageUnavailable, match="expired"):
            log.reserve("proof: interpretation", 100)
        assert log.attempts() == []
    assert not container.leases


def test_renewal_helper_loss_blocks_dispatch_and_stops_on_exit(web_blob, monkeypatch, caplog):
    flow, container, _, _ = web_blob
    failed = threading.Event()
    monkeypatch.setattr("ai_collage.storage.blob.LEASE_RENEW_SECONDS", 0.01)
    with flow.storage.mutation("proof") as session:
        def lose():
            failed.set()
            raise ServiceRequestError("renewal response lost")

        session.lease.renew.side_effect = lose
        assert failed.wait(2), "The bounded renewal helper did not run."
        with pytest.raises(StorageUnavailable):
            RequestLog(flow.store, "proof", persistence=session).reserve("proof: interpretation", 100)
        assert session.lost and session.identities("attempt") == []
    assert not container.leases
    assert not any(thread.name == "collage-blob-lease" for thread in threading.enumerate())
    assert "Project lease renewal stopped" in caplog.text


def test_work_deadline_crossing_during_proposal_upload_cannot_publish_it(web_blob, monkeypatch):
    flow, container, _, _ = web_blob
    scripted_send(flow, PROMPTS[0])
    second = Submission(request_id=str(uuid4()), prompt=PROMPTS[1], revision=flow.detail("proof")["revision"])
    prepared, _ = asyncio.run(flow.interpret("proof", second))
    original = container.uploads.side_effect
    expired = False

    def upload(key, raw, **kwargs):
        nonlocal expired
        result = original(key, raw, **kwargs)
        if key.endswith("/P002/preview.png"):
            expired = True
        return result

    original_clock = monotonic
    monkeypatch.setattr(container.uploads, "side_effect", upload)
    monkeypatch.setattr("ai_collage.agent.requests.monotonic", lambda: original_clock() + (1000 if expired else 0))
    with pytest.raises(FlowError) as error:
        asyncio.run(flow.generate("proof", second.request_id, GenerationRequest(revision=prepared["revision"])))
    assert expired and error.value.code == "stage_timeout"
    assert flow.detail("proof")["baseline"] == {"proposal_id": "P001"}
    assert [p["proposal_id"] for p in flow.detail("proof")["proposals"]] == ["P001"]


def test_deadline_crossing_during_reservation_cannot_dispatch(web_blob, monkeypatch):
    flow, container, _, _ = web_blob
    expired = False
    original = container.uploads.side_effect
    original_clock = monotonic

    def upload(key, raw, **kwargs):
        nonlocal expired
        result = original(key, raw, **kwargs)
        if key == flow.storage.completion_key("proof") and kwargs["overwrite"]:
            expired = True
        return result

    monkeypatch.setattr(container.uploads, "side_effect", upload)
    monkeypatch.setattr("ai_collage.agent.requests.monotonic", lambda: original_clock() + (121 if expired else 0))
    with flow.storage.mutation("proof") as session:
        log = RequestLog(flow.store, "proof", persistence=session)
        log.begin_stage("interpretation")
        with pytest.raises(StageTimeout):
            log.reserve("proof: interpretation", 100)
        assert expired and len(log.attempts()) == 1 and log.attempts()[0].status == "pending"


def test_unclaimed_preparation_continues_after_restart_or_requires_confirmed_abandonment(web_blob, tmp_path):
    flow, container, _, _ = web_blob
    scripted_send(flow, PROMPTS[0])
    second = Submission(request_id=str(uuid4()), prompt=PROMPTS[1], revision=flow.detail("proof")["revision"])
    prepared, _ = asyncio.run(flow.interpret("proof", second))
    restored = ConversationFlow(ProjectStore(tmp_path / "restart"), flow.settings, ScriptedModel(), storage=flow.storage)
    assert restored.operation("proof", second.request_id)["can_continue"]
    action = SelectionSubmission(
        action_id=str(uuid4()), proposal_id="P001", revision=prepared["revision"], abandon_pending=False,
    )
    with pytest.raises(FlowError):
        restored.select("proof", action)
    action = action.model_copy(update={"abandon_pending": True})
    selected, _ = restored.select("proof", action)
    assert selected["status"] == "completed"
    assert restored.operation("proof", second.request_id)["status"] == "abandoned"
    assert len(RequestLog(restored.store, "proof", persistence=flow.storage.conversation("proof")).attempts()) == 3


def test_maximum_canvas_render_fits_encoded_preview_ceiling(prepared, tmp_path):
    store, project, _ = prepared
    recipe = InputLayout.model_validate({
        "schema_version": 3, "canvas": {"width": 4096, "height": 4096, "background": "#2B2B2B"},
        "layers": [
            {"photo_id": n, "mode": "cover", "box": {
                "center_x": x, "center_y": 0.5, "width": 0.5, "height": 1.0,
            }} for n, x in ((1, 0.25), (2, 0.75))
        ],
    })
    resolved = resolve_layout(recipe, project.photos, 1)
    path = tmp_path / "maximum.png"
    render_layout(resolved, project.photos, store.photo_paths(project), path)
    assert 0 < path.stat().st_size <= MAX_PREVIEW_BYTES
    with Image.open(path) as image:
        assert image.format == "PNG" and image.size == (4096, 4096)
        image.verify()


def test_corrupt_blob_head_is_a_saved_state_conflict_not_bad_http_input(web_blob):
    flow, _, objects, _ = web_blob
    key = flow.storage.completion_key("proof")
    objects[key] = json.dumps({**json.loads(objects[key]), "schema_version": 1}).encode()
    with pytest.raises(FlowError) as error:
        flow.detail("proof")
    assert error.value.status == 409 and error.value.code == "invalid_conversation_state"


@pytest.mark.parametrize("exhausted", [False, True])
def test_missing_or_exhausted_fixture_responses_never_fall_back_to_foundry(web_blob, exhausted):
    flow, _, _, _ = web_blob
    if exhausted:
        for prompt in PROMPTS:
            scripted_send(flow, prompt)
    submission = Submission(request_id=str(uuid4()), prompt="Unexpected fixture request",
                            revision=flow.detail("proof")["revision"])
    with pytest.raises(FlowError):
        asyncio.run(flow.interpret("proof", submission))
    session = flow.storage.conversation("proof")
    assert len(RequestLog(flow.store, "proof", persistence=session).attempts()) == (4 if exhausted else 0)


def test_full_proof_journey_uses_normal_http_handlers_offline(blobs, tmp_path, monkeypatch):
    import importlib
    import function_app
    import api.verify_blob_storage as verification

    monkeypatch.setattr(function_app, "conversation_flow", function_app.conversation_flow)
    proof_app = importlib.import_module("api.proof_function_app")
    monkeypatch.setattr(function_app, "conversation_flow", proof_app.fixture_conversation_flow)
    monkeypatch.setattr("ai_collage.agent.provider.FoundryModel",
                        lambda: pytest.fail("Proof must not construct model credentials or a real provider."))
    proof = verification.Proof(tmp_path / "proof", http_requests=60, blob_requests=800)
    proof.port = 7071
    container, objects = blobs
    original = container.uploads.side_effect

    def record(key, data, **kwargs):
        result = original(key, data, **kwargs)
        with proof.inventory.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"key": key, "etag": result["etag"]}) + "\n")
        return result

    container.uploads.side_effect = record
    phase = "first-root"

    @contextmanager
    def factory():
        yield ProjectFlow(ProjectStore(proof.output / phase), BlobProjectStorage(container, proof.namespace))

    monkeypatch.setattr(function_app, "project_flow", factory)
    monkeypatch.setattr(proof_app, "project_flow", factory)
    monkeypatch.setattr(proof_app, "backend", lambda: "blob")
    monkeypatch.setattr(proof_app, "blob_settings", lambda: SimpleNamespace(ledger=proof.ledger))
    monkeypatch.setenv("AI_COLLAGE_API_AUTHORITY", "127.0.0.1:7071")

    class HandlerClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, **kwargs):
            outgoing = httpx.Request(method, url, **kwargs)
            parts = urlsplit(url).path.removeprefix("/api/").split("/")
            route = {"project_id": "proof"}
            if len(parts) == 1:
                operation = "collection"
            elif len(parts) == 2:
                operation = "detail"
            elif parts[2] == "photos":
                route["photo_id"] = parts[3]
                operation = "photo"
            elif parts[2] == "proposals":
                route["proposal_id"] = parts[3]
                operation = "preview"
            elif len(parts) == 3:
                operation = "conversation"
            elif parts[3] == "requests":
                operation = "requests" if len(parts) == 4 else "operation" if len(parts) == 5 else "generate"
                if len(parts) > 4:
                    route["request_id"] = parts[4]
            else:
                operation = "selections" if len(parts) == 4 else "selection"
                if len(parts) > 4:
                    route["action_id"] = parts[4]
            request = func.HttpRequest(method, url, headers=dict(outgoing.headers),
                                      body=outgoing.read(), route_params=route)
            response = (
                function_app.dispatch(request, operation) if operation in {"collection", "detail", "photo"}
                else asyncio.run(function_app.dispatch_conversation(request, operation))
            )
            headers = {"Content-Type": response.mimetype, **dict(response.headers)}
            return httpx.Response(response.status_code, headers=headers,
                                  content=response.get_body(), request=outgoing)

    def start(name):
        nonlocal phase
        phase = name
        return proof.request("GET", "projects").json()["projects"]

    monkeypatch.setattr(proof, "start", start)
    monkeypatch.setattr(verification.httpx, "Client", lambda **kwargs: HandlerClient())
    monkeypatch.setattr(verification, "AzureCliCredential", lambda **kwargs: nullcontext(None))
    monkeypatch.setattr(verification, "ContainerClient", lambda *args, **kwargs: nullcontext(container))
    proof.run()
    assert proof.report["status"] == "passed" and proof.report["model_calls"] == 0
    assert proof.report["cleanup_complete"] and objects == {} and not container.leases
    assert proof.report["http_requests"] <= proof.limits.http_requests
