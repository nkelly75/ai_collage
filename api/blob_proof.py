"""Opt-in proof-only transport accounting, shared across owned worker restarts."""

import json
from pathlib import Path
from urllib.parse import urlsplit

from azure.core.pipeline.transport import RequestsTransport

from ai_collage.application.projects import project_guard
from ai_collage.engine.projects import ProjectStore
from ai_collage.storage.contracts import StorageUnavailable


MAX_PROOF_REQUESTS = 200


class ProofTransport(RequestsTransport):
    def __init__(self, ledger: Path):
        super().__init__()
        self.ledger = ledger

    def send(self, request, **kwargs):
        with project_guard(ProjectStore(self.ledger.parent), "blob-proof-budget"):
            lines = self.ledger.read_text(encoding="utf-8").splitlines()
            if len(lines) >= MAX_PROOF_REQUESTS:
                raise StorageUnavailable("The Blob proof request allowance is exhausted.")
            target = urlsplit(request.url)
            if (
                target.scheme != "https"
                or target.netloc != "stclgdevbik2twby4e2zu.blob.core.windows.net"
                or not (target.path == "/collage" or target.path.startswith("/collage/"))
            ):
                raise StorageUnavailable("Blob proof transport refused a different target.")
            with self.ledger.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"method": request.method, "url": request.url}) + "\n")
        return super().send(request, **kwargs)
