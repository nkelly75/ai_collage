import os
import json
import shutil
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

from azure.core import MatchConditions
from azure.core.credentials import AccessToken
from azure.core.pipeline.transport import HttpRequest, HttpResponse, RequestsTransport
from azure.storage.blob import ContainerClient
import pytest
from requests.structures import CaseInsensitiveDict

from ai_collage.storage.blob import BlobProjectStorage
from ai_collage.storage.contracts import StorageUnavailable
from blob_proof import ProofLimits, ProofTransport, limits_path
import api.verify_blob_storage as verification


def test_proof_requires_explicit_opt_in_before_creating_evidence_or_credentials(monkeypatch, tmp_path):
    proof = Mock(side_effect=AssertionError("must not create a proof"))
    monkeypatch.setattr(verification, "Proof", proof)
    monkeypatch.setattr("sys.argv", [
        "api.verify_blob_storage", "--output-dir", str(tmp_path / "new"),
        "--max-http-requests", "40", "--max-blob-requests", "800",
    ])
    with pytest.raises(SystemExit) as error:
        verification.main()
    assert error.value.code == 2
    proof.assert_not_called()
    assert not (tmp_path / "new").exists()


def test_http_budget_blocks_before_another_request(tmp_path, monkeypatch):
    proof = verification.Proof(tmp_path / "proof", http_requests=40, blob_requests=800)
    proof.http_count = 40
    client = Mock(side_effect=AssertionError("must not construct an HTTP client"))
    monkeypatch.setattr(verification.httpx, "Client", client)
    with pytest.raises(RuntimeError, match="allowance is exhausted"):
        proof.request("GET", "projects")
    client.assert_not_called()


@pytest.mark.parametrize("extra", [False, True])
def test_cleanup_refuses_unexpected_inventory_and_deletes_completion_first(tmp_path, monkeypatch, extra):
    proof = verification.Proof(tmp_path / "proof", http_requests=40, blob_requests=800)
    prefix = proof.namespace + "/users/local-dev/"
    candidate = prefix + "candidates/proof/" + "a" * 32 + "/"
    completion = prefix + "published/proof.json"
    expected = {
        completion, candidate + "project.json", candidate + "conversation/state.json",
        candidate + "photos/" + "b" * 32, candidate + "photos/" + "c" * 32,
    }
    proof.inventory.write_text("".join(json.dumps({"key": key, "etag": "known-etag"}) + "\n" for key in expected))
    container_factory = MagicMock()
    container = container_factory.return_value.__enter__.return_value
    container.list_blobs.return_value = [SimpleNamespace(name=name) for name in (
        expected | {prefix + "unexpected"} if extra else expected
    )]
    container.get_blob_client.return_value.get_blob_properties.return_value.etag = "known-etag"
    monkeypatch.setattr(verification, "AzureCliCredential", MagicMock())
    monkeypatch.setattr(verification, "ContainerClient", container_factory)
    if extra:
        with pytest.raises(RuntimeError, match="Unexpected proof inventory"):
            proof.cleanup()
        container.delete_blob.assert_not_called()
        assert proof.report["cleanup_complete"] is False
    else:
        proof.cleanup()
        calls = container.delete_blob.call_args_list
        assert calls[0].args[0] == completion
        assert {call.args[0] for call in calls} == expected
        assert all(call.kwargs == {
            "etag": "known-etag", "match_condition": MatchConditions.IfNotModified,
        } for call in calls)
        assert proof.report["cleanup_complete"] is True


@pytest.mark.parametrize("url,allowed", [
    (verification.DEV_ACCOUNT_URL + "/collage?restype=container&comp=list&prefix={namespace}/users/local-dev/", True),
    (verification.DEV_ACCOUNT_URL + "/collage?restype=container&comp=list&prefix={namespace}/users/local-dev/published/", True),
    (verification.DEV_ACCOUNT_URL + "/collage?restype=container&comp=list&prefix={namespace}/users/local-dev/published-elsewhere/", False),
    (verification.DEV_ACCOUNT_URL + "/collage?restype=container&comp=list&prefix={namespace}/users/", False),
    (verification.DEV_ACCOUNT_URL + "/collage/{namespace}/users/local-dev/published/proof.json", True),
    (verification.DEV_ACCOUNT_URL + "/other/blob", False),
    ("https://other.example/collage/blob", False),
])
def test_transport_allows_container_listing_but_refuses_other_targets(tmp_path, monkeypatch, url, allowed):
    ledger = tmp_path / "requests.jsonl"
    ledger.write_text("")
    namespace = "proof-019c-" + "a" * 32
    limits_path(ledger).write_text(ProofLimits(
        namespace=namespace, http_requests=40, blob_requests=800,
    ).model_dump_json())
    send = Mock(return_value=object())
    monkeypatch.setattr(RequestsTransport, "send", send)
    transport = ProofTransport(ledger)
    if allowed:
        transport.send(HttpRequest("GET", url.format(namespace=namespace)))
        send.assert_called_once()
    else:
        with pytest.raises(StorageUnavailable, match="different target"):
            transport.send(HttpRequest("GET", url.format(namespace=namespace)))
        send.assert_not_called()
        assert ledger.read_text() == ""


def test_real_sdk_project_listing_passes_through_proof_transport_without_network(tmp_path, monkeypatch):
    namespace = "proof-019c-" + "a" * 32
    ledger = tmp_path / "requests.jsonl"
    ledger.write_text("")
    limits_path(ledger).write_text(ProofLimits(
        namespace=namespace, http_requests=50, blob_requests=1200,
    ).model_dump_json())

    class EmptyListing(HttpResponse):
        def __init__(self, request):
            super().__init__(request, None)
            self.status_code = 200
            self.headers = CaseInsensitiveDict({"Content-Type": "application/xml"})
            self.content_type = "application/xml"

        def body(self):
            return (
                '<?xml version="1.0" encoding="utf-8"?>'
                '<EnumerationResults ServiceEndpoint="' + verification.DEV_ACCOUNT_URL + '/" ContainerName="collage">'
                '<Prefix>' + namespace + '/users/local-dev/published/</Prefix>'
                '<Blobs/><NextMarker/></EnumerationResults>'
            ).encode()

    send = Mock(side_effect=lambda request, **kwargs: EmptyListing(request))
    monkeypatch.setattr(RequestsTransport, "send", send)
    credential = SimpleNamespace(get_token=lambda *args, **kwargs: AccessToken("offline-fixture-token", 4000000000))
    with ContainerClient(
        verification.DEV_ACCOUNT_URL, verification.DEV_CONTAINER, credential=credential,
        retry_total=0, transport=ProofTransport(ledger),
    ) as container:
        assert BlobProjectStorage(container, namespace).project_ids() == []
    send.assert_called_once()
    assert len(ledger.read_text().splitlines()) == 1


@pytest.mark.parametrize("method,path", [
    ("DELETE", "/collage"),
    ("GET", "/collage/proof-019c-" + "b" * 32 + "/users/local-dev/published/proof.json"),
    ("PUT", "/collage/{namespace}/users/local-dev/published/other.json"),
    ("DELETE", "/collage/{namespace}/users/local-dev/candidates/proof/../../other"),
])
def test_proof_transport_blocks_unowned_keys_and_container_deletion(tmp_path, monkeypatch, method, path):
    ledger = tmp_path / "requests.jsonl"
    ledger.write_text("")
    namespace = "proof-019c-" + "a" * 32
    limits_path(ledger).write_text(ProofLimits(namespace=namespace, http_requests=40, blob_requests=800).model_dump_json())
    send = Mock()
    monkeypatch.setattr(RequestsTransport, "send", send)
    with pytest.raises(StorageUnavailable, match="different target"):
        ProofTransport(ledger).send(HttpRequest(method, verification.DEV_ACCOUNT_URL + path.format(namespace=namespace)))
    send.assert_not_called()
    assert ledger.read_text() == ""


def test_confirmed_put_inventory_records_latest_etag_and_send_budget_includes_failed_calls(tmp_path, monkeypatch):
    ledger = tmp_path / "requests.jsonl"
    ledger.write_text("")
    namespace = "proof-019c-" + "a" * 32
    limits_path(ledger).write_text(ProofLimits(namespace=namespace, http_requests=40, blob_requests=2).model_dump_json())
    send = Mock(side_effect=[
        SimpleNamespace(status_code=201, headers={"ETag": '"first"'}),
        SimpleNamespace(status_code=201, headers={"ETag": '"second"'}),
    ])
    monkeypatch.setattr(RequestsTransport, "send", send)
    transport = ProofTransport(ledger)
    key = namespace + "/users/local-dev/published/proof.json"
    request = HttpRequest("PUT", verification.DEV_ACCOUNT_URL + "/collage/" + key)
    transport.send(request)
    transport.send(request)
    assert [json.loads(line) for line in transport.inventory.read_text().splitlines()] == [
        {"key": key, "etag": '"first"'}, {"key": key, "etag": '"second"'},
    ]
    with pytest.raises(StorageUnavailable, match="allowance is exhausted"):
        transport.send(request)
    assert send.call_count == 2 and len(ledger.read_text().splitlines()) == 2


@pytest.mark.parametrize("changed", [False, True])
def test_cleanup_refuses_escaping_inventory_or_changed_etags(tmp_path, monkeypatch, changed):
    proof = verification.Proof(tmp_path / "proof", http_requests=40, blob_requests=800)
    key = proof.namespace + "/users/local-dev/published/proof.json" if changed else "other/users/local-dev/published/proof.json"
    proof.inventory.write_text(json.dumps({"key": key, "etag": "confirmed"}) + "\n")
    factory = MagicMock()
    container = factory.return_value.__enter__.return_value
    container.list_blobs.return_value = [SimpleNamespace(name=key)]
    container.get_blob_client.return_value.get_blob_properties.return_value.etag = "changed"
    monkeypatch.setattr(verification, "AzureCliCredential", MagicMock())
    monkeypatch.setattr(verification, "ContainerClient", factory)
    with pytest.raises(RuntimeError, match="changed since" if changed else "Invalid proof upload inventory"):
        proof.cleanup()
    container.delete_blob.assert_not_called()


@pytest.mark.skipif(os.name != "nt" or shutil.which("powershell.exe") is None, reason="Windows process ownership check")
def test_proof_checks_listener_ownership_and_stops_only_its_processes(tmp_path):
    proof = verification.Proof(tmp_path / "proof", http_requests=40, blob_requests=800)
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        proof.port = reservation.getsockname()[1]
    listener = subprocess.Popen([
        sys.executable, "-c",
        "import socket,sys,time; s=socket.socket(); s.bind(('127.0.0.1',int(sys.argv[1]))); s.listen(); time.sleep(120)",
        str(proof.port),
    ])
    other = None
    try:
        proof.process = listener
        proof.process_action()
        other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
        proof.process = other
        with pytest.raises(subprocess.CalledProcessError):
            proof.process_action()
        proof.stop()
        assert listener.poll() is None
        assert other.poll() is not None
    finally:
        if other is not None and other.poll() is None:
            proof.process = other
            proof.stop()
        proof.process = listener
        proof.stop()
