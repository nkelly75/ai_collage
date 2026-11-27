from contextlib import contextmanager
import json
from pathlib import Path
from unittest.mock import MagicMock, Mock

from azure.core.pipeline.transport import HttpRequest, RequestsTransport
import azure.functions as func
import pytest

import function_app
import storage_config
from blob_proof import ProofTransport
from ai_collage.application.projects import FlowError
from ai_collage.storage.contracts import StorageOutcomeUnknown, StorageUnavailable


@pytest.fixture
def blob_environment(monkeypatch):
    for name, value in {
        "AI_COLLAGE_STORAGE_BACKEND": "Blob",
        "AI_COLLAGE_BLOB_ACCOUNT_URL": storage_config.DEV_ACCOUNT_URL,
        "AI_COLLAGE_BLOB_CONTAINER": storage_config.DEV_CONTAINER,
        "AI_COLLAGE_BLOB_SUBSCRIPTION_ID": storage_config.DEV_SUBSCRIPTION,
        "AI_COLLAGE_BLOB_NAMESPACE": "test-019b",
        "AI_COLLAGE_LIVE": "0",
    }.items():
        monkeypatch.setenv(name, value)
    for name in ("AI_COLLAGE_CALL_BUDGET_PATH", "AI_COLLAGE_MAX_CALLS", "AI_COLLAGE_TRIAL_PROJECT"):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize("name,value", [
    ("AI_COLLAGE_STORAGE_BACKEND", ""),
    ("AI_COLLAGE_STORAGE_BACKEND", "unknown"),
    ("AI_COLLAGE_BLOB_ACCOUNT_URL", "https://other.example"),
    ("AI_COLLAGE_BLOB_ACCOUNT_URL", storage_config.DEV_ACCOUNT_URL + "?sig=secret"),
    ("AI_COLLAGE_BLOB_CONTAINER", "other"),
    ("AI_COLLAGE_BLOB_SUBSCRIPTION_ID", ""),
    ("AI_COLLAGE_BLOB_NAMESPACE", "../escape"),
    ("AI_COLLAGE_LIVE", "1"),
    ("AI_COLLAGE_TRIAL_PROJECT", "trip"),
])
def test_invalid_blob_configuration_never_constructs_credentials(blob_environment, monkeypatch, name, value):
    credential = Mock(side_effect=AssertionError("must not construct credentials"))
    monkeypatch.setattr("azure.identity.AzureCliCredential", credential)
    monkeypatch.setenv(name, value)
    with pytest.raises(FlowError) as error:
        with storage_config.project_flow():
            pytest.fail("invalid configuration must not yield a flow")
    assert error.value.code == "configuration_error"
    credential.assert_not_called()


def test_local_selection_does_not_construct_blob_clients(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_COLLAGE_DATA_DIR", str(tmp_path / "local"))
    credential = Mock(side_effect=AssertionError("must not construct credentials"))
    monkeypatch.setattr("azure.identity.AzureCliCredential", credential)
    with storage_config.project_flow() as flow:
        assert flow.list() == []
    credential.assert_not_called()


def test_blob_factory_scopes_cli_identity_and_disables_retries(blob_environment, monkeypatch, tmp_path):
    monkeypatch.setenv("AI_COLLAGE_DATA_DIR", str(tmp_path / "guards"))
    credential = MagicMock()
    container = MagicMock()
    monkeypatch.setattr("azure.identity.AzureCliCredential", credential)
    monkeypatch.setattr("azure.storage.blob.ContainerClient", container)
    with storage_config.project_flow() as flow:
        assert flow.storage.prefix == "test-019b/users/local-dev/"
    credential.assert_called_once_with(subscription=storage_config.DEV_SUBSCRIPTION, process_timeout=10)
    assert container.call_args.kwargs["retry_total"] == 0
    assert container.call_args.kwargs["connection_timeout"] == 10
    assert container.call_args.kwargs["read_timeout"] == 30


@pytest.mark.parametrize("operation", [
    "conversation", "requests", "operation", "generate", "selections", "selection", "preview",
])
def test_all_unsupported_blob_routes_reject_before_local_or_model_access(
    blob_environment, monkeypatch, operation,
):
    forbidden = Mock(side_effect=AssertionError("must not access conversation/local state"))
    monkeypatch.setattr(function_app, "ConversationFlow", forbidden)
    monkeypatch.setattr(function_app, "configured_store", forbidden)
    req = func.HttpRequest("GET", "http://127.0.0.1:7071/api/projects/trip/conversation",
                           headers={"Host": "127.0.0.1:7071"}, body=b"", route_params={"project_id": "trip"})
    response = function_app._dispatch_conversation(req, operation)
    assert response.status_code == 501
    assert json.loads(response.get_body())["error"]["code"] == "blob_slice_only"
    forbidden.assert_not_called()


@pytest.mark.parametrize("failure,status,code", [
    (StorageUnavailable("secret Azure details"), 503, "storage_unavailable"),
    (StorageOutcomeUnknown("secret Azure details"), 500, "outcome_unknown"),
])
def test_blob_operational_errors_have_safe_explicit_http_outcomes(monkeypatch, failure, status, code):
    @contextmanager
    def failed_flow():
        raise failure
        yield
    monkeypatch.setattr(function_app, "project_flow", failed_flow)
    req = func.HttpRequest("GET", "http://127.0.0.1:7071/api/projects",
                           headers={"Host": "127.0.0.1:7071"}, body=b"")
    response = function_app.dispatch(req, "collection")
    assert response.status_code == status
    assert json.loads(response.get_body())["error"]["code"] == code
    assert b"secret Azure details" not in response.get_body()


def test_proof_transport_counts_before_send_and_stops_at_cap(tmp_path, monkeypatch):
    ledger = tmp_path / "requests.jsonl"
    ledger.write_text("")
    send = Mock(return_value=object())
    monkeypatch.setattr(RequestsTransport, "send", send)
    transport = ProofTransport(ledger)
    request = HttpRequest("GET", storage_config.DEV_ACCOUNT_URL + "/collage/blob")
    transport.send(request)
    assert len(ledger.read_text().splitlines()) == 1
    ledger.write_text("{}\n" * 200)
    with pytest.raises(StorageUnavailable, match="allowance is exhausted"):
        transport.send(request)
    assert send.call_count == 1
