import asyncio
from contextlib import contextmanager
import json
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

from azure.core.credentials import AccessToken
from azure.core.pipeline.transport import HttpRequest, HttpResponse, RequestsTransport
from azure.storage.blob import ContainerClient
import azure.functions as func
import pytest
from requests.structures import CaseInsensitiveDict
from azure.core.exceptions import AzureError

import function_app
import request_metrics
import storage_config
from blob_metrics import MeasuredBlobProjectStorage, MetricsTransport
from ai_collage.storage.contracts import StorageUnavailable
from .test_project_routes import isolate
from ..agent.test_agent import asyncio_wakeup_pair


def request():
    return func.HttpRequest(
        "GET", "http://127.0.0.1:7071/api/projects/private-project?sig=private-token",
        headers={"Host": "127.0.0.1:7071", "Authorization": "private-token"}, body=b"",
        route_params={"project_id": "private-project"},
    )


def selected_flow(monkeypatch, *, failure=None):
    @contextmanager
    def selected():
        flow = Mock()
        flow.list.return_value = [{"private-data": "not recorded"}]
        if failure is not None:
            flow.list.side_effect = failure
        yield flow
    monkeypatch.setattr(function_app, "project_flow", selected)


def test_metrics_are_disabled_without_opt_in(monkeypatch):
    selected_flow(monkeypatch)
    response = function_app.dispatch(request(), "collection")
    assert response.status_code == 200
    assert "X-Collage-Metrics-Id" not in response.headers
    assert request_metrics.current() is None


@pytest.mark.parametrize("failure,status", [(None, 200), (StorageUnavailable("private-error"), 503)])
def test_metrics_append_safe_records_and_preserve_http_results(tmp_path, monkeypatch, failure, status):
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("AI_COLLAGE_METRICS_PATH", str(path))
    selected_flow(monkeypatch, failure=failure)
    for _ in range(2):
        response = function_app.dispatch(request(), "collection")
        assert response.status_code == status
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        assert rows[-1]["request_id"] == response.headers["X-Collage-Metrics-Id"]
        assert rows[-1]["response_bytes"] == len(response.get_body())
    assert len(rows) == 2 and rows[0]["request_id"] != rows[1]["request_id"]
    assert rows[-1]["status"] == status
    assert rows[-1]["handler_ms"] >= 0
    assert rows[-1]["blob_requests"] == 0
    assert rows[-1]["blob_read_ms"] == 0
    assert "private" not in path.read_text()
    assert request_metrics.current() is None


def test_async_request_metrics_follow_worker_threads_without_cross_request_counts(tmp_path, monkeypatch):
    path = tmp_path / "metrics.jsonl"
    monkeypatch.setenv("AI_COLLAGE_METRICS_PATH", str(path))
    barrier = threading.Barrier(2)

    def dispatch(req, operation):
        metrics = request_metrics.current()
        assert metrics is not None
        barrier.wait(timeout=5)
        transport = MetricsTransport(Mock(), metrics)
        for _ in range(1 if operation == "conversation" else 2):
            transport.send(HttpRequest("GET", "https://private.example/?sig=private-token"))
        return func.HttpResponse(b"private bytes")

    monkeypatch.setattr(function_app, "_dispatch_conversation", dispatch)

    async def concurrent():
        return await asyncio.gather(
            function_app.dispatch_conversation(request(), "conversation"),
            function_app.dispatch_conversation(request(), "preview"),
        )

    responses = asyncio.run(concurrent())
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert {row["route"]: row["blob_requests"] for row in rows} == {"conversation": 1, "preview": 2}
    assert {row["request_id"] for row in rows} == {response.headers["X-Collage-Metrics-Id"] for response in responses}
    assert all(row["status"] == 200 and row["response_bytes"] == len(b"private bytes") for row in rows)
    assert "private" not in path.read_text()
    assert request_metrics.current() is None


@pytest.mark.parametrize("failure", [False, True])
def test_blob_read_timing_includes_lazy_chunks_and_does_not_double_count_metadata(tmp_path, monkeypatch, failure):
    clock = [0.0]
    monkeypatch.setattr(request_metrics, "perf_counter", lambda: clock[0])
    metrics = request_metrics.RequestMetrics(tmp_path / "metrics.jsonl", "GET", "preview", started=0)

    def properties():
        clock[0] += 1
        return SimpleNamespace(size=3, etag="known")

    def chunks():
        clock[0] += 3
        yield b"abc"
        clock[0] += 4
        if failure:
            raise AzureError("injected chunk failure")

    def download(**kwargs):
        assert kwargs["etag"] == "*"
        clock[0] += 2
        return SimpleNamespace(properties=SimpleNamespace(size=3, etag="known"), chunks=chunks)

    client = SimpleNamespace(get_blob_properties=properties, download_blob=download)
    container = Mock()
    container.get_blob_client.return_value = client
    storage = MeasuredBlobProjectStorage(container, "test", metrics)
    if failure:
        with pytest.raises(StorageUnavailable):
            storage._read_etag("object", 8)
    else:
        assert storage._read_etag("object", 8) == (b"abc", "known")
    assert metrics.blob_read_seconds == 9


def test_metrics_transport_preserves_failures_and_lifecycle(tmp_path):
    metrics = request_metrics.RequestMetrics(tmp_path / "metrics.jsonl", "GET", "photo")
    inner = MagicMock()
    inner.send.side_effect = StorageUnavailable("injected guard failure")
    transport = MetricsTransport(inner, metrics)
    transport.open()
    transport.sleep(0.1)
    with transport:
        with pytest.raises(StorageUnavailable, match="injected guard failure"):
            transport.send(HttpRequest("GET", "https://private.example/"))
    transport.close()
    assert metrics.blob_requests == 1
    inner.open.assert_called_once()
    inner.sleep.assert_called_once_with(0.1)
    inner.__enter__.assert_called_once()
    inner.__exit__.assert_called_once()
    inner.close.assert_called_once()


def test_actual_sdk_listing_works_through_metrics_transport_without_network(tmp_path, monkeypatch):
    metrics = request_metrics.RequestMetrics(tmp_path / "metrics.jsonl", "GET", "collection")

    class EmptyListing(HttpResponse):
        def __init__(self, req):
            super().__init__(req, None)
            self.status_code = 200
            self.headers = CaseInsensitiveDict({"Content-Type": "application/xml"})
            self.content_type = "application/xml"

        def body(self):
            return b'<?xml version="1.0"?><EnumerationResults><Blobs/><NextMarker/></EnumerationResults>'

    send = Mock(side_effect=lambda req, **kwargs: EmptyListing(req))
    monkeypatch.setattr(RequestsTransport, "send", send)
    credential = SimpleNamespace(get_token=lambda *args, **kwargs: AccessToken("offline-token", 4000000000))
    with ContainerClient(
        storage_config.DEV_ACCOUNT_URL, "collage", credential=credential,
        transport=MetricsTransport(RequestsTransport(), metrics), retry_total=0,
    ) as container:
        assert MeasuredBlobProjectStorage(container, "test", metrics).project_ids() == []
    assert metrics.blob_requests == 1
    assert metrics.blob_read_seconds > 0
    send.assert_called_once()


@pytest.mark.parametrize("value", ["", "relative.jsonl", "wrong.json"])
def test_invalid_metrics_configuration_rejects_before_application_work(monkeypatch, value):
    monkeypatch.setenv("AI_COLLAGE_METRICS_PATH", value)
    flow = Mock(side_effect=AssertionError("must not construct an application flow"))
    monkeypatch.setattr(function_app, "project_flow", flow)
    response = function_app.dispatch(request(), "collection")
    assert response.status_code == 500
    assert json.loads(response.get_body())["error"]["code"] == "configuration_error"
    flow.assert_not_called()


@pytest.mark.parametrize("failure,status", [(None, 200), (StorageUnavailable("injected primary failure"), 503)])
def test_metrics_write_failure_is_visible_without_masking_application_result(tmp_path, monkeypatch, caplog, failure, status):
    monkeypatch.setenv("AI_COLLAGE_METRICS_PATH", str(tmp_path / "metrics.jsonl"))
    selected_flow(monkeypatch, failure=failure)
    monkeypatch.setattr(Path, "open", Mock(side_effect=PermissionError("injected diagnostic failure")))
    response = function_app.dispatch(request(), "collection")
    assert response.status_code == status
    assert "timing was not recorded" in caplog.text
    assert request_metrics.current() is None


@pytest.mark.parametrize("name,inventory", [
    ("AI_COLLAGE_CALL_BUDGET_PATH", False),
    ("AI_COLLAGE_BLOB_PROOF_LEDGER", False),
    ("AI_COLLAGE_BLOB_PROOF_LEDGER", True),
])
def test_metrics_do_not_append_into_a_budget_or_proof_record(tmp_path, monkeypatch, name, inventory):
    ledger = tmp_path / "budget.jsonl"
    path = ledger.with_suffix(".objects.jsonl") if inventory else ledger
    path.write_text('{"used":2}\n')
    monkeypatch.setenv("AI_COLLAGE_METRICS_PATH", str(path))
    monkeypatch.setenv(name, str(ledger))
    selected_flow(monkeypatch)
    response = function_app.dispatch(request(), "collection")
    assert response.status_code == 500
    assert "must not share" in json.loads(response.get_body())["error"]["message"]
    assert path.read_text() == '{"used":2}\n'
