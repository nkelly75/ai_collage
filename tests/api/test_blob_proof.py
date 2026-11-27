import os
import shutil
import socket
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

from azure.core import MatchConditions
from azure.core.pipeline.transport import HttpRequest, RequestsTransport
import pytest

from ai_collage.storage.contracts import StorageUnavailable
from blob_proof import ProofTransport
import api.verify_blob_storage as verification


def test_proof_requires_explicit_opt_in_before_creating_evidence_or_credentials(monkeypatch, tmp_path):
    proof = Mock(side_effect=AssertionError("must not create a proof"))
    monkeypatch.setattr(verification, "Proof", proof)
    monkeypatch.setattr("sys.argv", ["api.verify_blob_storage", "--output-dir", str(tmp_path / "new")])
    with pytest.raises(SystemExit) as error:
        verification.main()
    assert error.value.code == 2
    proof.assert_not_called()
    assert not (tmp_path / "new").exists()


def test_http_budget_blocks_before_another_request(tmp_path, monkeypatch):
    proof = verification.Proof(tmp_path / "proof")
    proof.http_count = 30
    client = Mock(side_effect=AssertionError("must not construct an HTTP client"))
    monkeypatch.setattr(verification.httpx, "Client", client)
    with pytest.raises(RuntimeError, match="allowance is exhausted"):
        proof.request("GET", "projects")
    client.assert_not_called()


@pytest.mark.parametrize("extra", [False, True])
def test_cleanup_refuses_unexpected_inventory_and_deletes_completion_first(tmp_path, monkeypatch, extra):
    proof = verification.Proof(tmp_path / "proof")
    prefix = proof.namespace + "/users/local-dev/"
    candidate = prefix + "candidates/proof/attempt/"
    completion = prefix + "published/proof.json"
    expected = {
        completion, candidate + "project.json", candidate + "conversation/state.json",
        candidate + "photos/one", candidate + "photos/two",
    }
    container_factory = MagicMock()
    container = container_factory.return_value.__enter__.return_value
    container.list_blobs.return_value = [SimpleNamespace(name=name) for name in (
        expected | {prefix + "unexpected"} if extra else expected
    )]
    container.get_blob_client.return_value.get_blob_properties.return_value.etag = "known-etag"
    storage_factory = Mock()
    storage = storage_factory.return_value
    storage.prefix = prefix
    storage.candidate_prefix.return_value = candidate
    storage.completion_key.return_value = completion
    storage.load.return_value = (SimpleNamespace(photos=[
        SimpleNamespace(asset_id="one"), SimpleNamespace(asset_id="two"),
    ]), None)
    monkeypatch.setattr(verification, "BlobProjectStorage", storage_factory)
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
    (verification.DEV_ACCOUNT_URL + "/collage?restype=container&comp=list", True),
    (verification.DEV_ACCOUNT_URL + "/collage/blob", True),
    (verification.DEV_ACCOUNT_URL + "/other/blob", False),
    ("https://other.example/collage/blob", False),
])
def test_transport_allows_container_listing_but_refuses_other_targets(tmp_path, monkeypatch, url, allowed):
    ledger = tmp_path / "requests.jsonl"
    ledger.write_text("")
    send = Mock(return_value=object())
    monkeypatch.setattr(RequestsTransport, "send", send)
    transport = ProofTransport(ledger)
    if allowed:
        transport.send(HttpRequest("GET", url))
        send.assert_called_once()
    else:
        with pytest.raises(StorageUnavailable, match="different target"):
            transport.send(HttpRequest("GET", url))
        send.assert_not_called()
        assert ledger.read_text() == ""


@pytest.mark.skipif(os.name != "nt" or shutil.which("powershell.exe") is None, reason="Windows process ownership check")
def test_proof_checks_listener_ownership_and_stops_only_its_processes(tmp_path):
    proof = verification.Proof(tmp_path / "proof")
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
