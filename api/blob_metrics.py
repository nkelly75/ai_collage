"""Measure Blob reads without altering validation, transport or publication."""

from azure.core.pipeline.transport import HttpTransport

from ai_collage.storage.blob import BlobProjectStorage
from request_metrics import RequestMetrics


class MetricsTransport(HttpTransport):
    def __init__(self, transport: HttpTransport, metrics: RequestMetrics):
        self.transport = transport
        self.metrics = metrics

    def open(self):
        return self.transport.open()

    def close(self):
        return self.transport.close()

    def __enter__(self):
        self.transport.__enter__()
        return self

    def __exit__(self, *args):
        return self.transport.__exit__(*args)

    def sleep(self, duration):
        return self.transport.sleep(duration)

    def send(self, request, **kwargs):
        self.metrics.count_blob_request()
        return self.transport.send(request, **kwargs)


class MeasuredBlobProjectStorage(BlobProjectStorage):
    def __init__(self, container, namespace: str, metrics: RequestMetrics):
        super().__init__(container, namespace)
        self.metrics = metrics

    def _properties(self, key: str, *, published: bool = False):
        with self.metrics.blob_read():
            return super()._properties(key, published=published)

    def _read_etag(self, key: str, limit: int, *, published: bool = False):
        with self.metrics.blob_read():
            return super()._read_etag(key, limit, published=published)

    def project_ids(self) -> list[str]:
        with self.metrics.blob_read():
            return super().project_ids()
