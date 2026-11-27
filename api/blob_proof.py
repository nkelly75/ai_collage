"""Opt-in proof-only transport accounting, shared across owned worker restarts."""

import json
from pathlib import Path
import re
from urllib.parse import parse_qs, unquote, urlsplit

from azure.core.pipeline.transport import RequestsTransport
from pydantic import BaseModel, ConfigDict, Field

from ai_collage.application.projects import project_guard
from ai_collage.engine.projects import ProjectStore
from ai_collage.engine.projects import read_json
from ai_collage.storage.contracts import StorageUnavailable


class ProofLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    namespace: str = Field(pattern=r"^proof-019c-[0-9a-f]{32}$")
    http_requests: int = Field(ge=1, le=1000)
    blob_requests: int = Field(ge=1, le=10000)


def limits_path(ledger: Path) -> Path:
    return ledger.with_suffix(".limits.json")


def owned_key(namespace: str, key: str) -> bool:
    prefix = namespace + "/users/local-dev/"
    if key == prefix + "published/proof.json":
        return True
    if not key.startswith(prefix):
        return False
    return re.fullmatch(
        r"candidates/proof/[0-9a-f]{32}/(?:project\.json|photos/[0-9a-f]{32}|"
        r"conversation/(?:state\.json|events/[0-9]{6,}\.json|requests/attempt-[0-9]{4,}\.json|"
        r"proposals/P[0-9]{3,}/(?:proposal\.json|preview\.png))|"
        r"web-(?:operations|selections)/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\.json)",
        key.removeprefix(prefix),
    ) is not None


class ProofTransport(RequestsTransport):
    def __init__(self, ledger: Path):
        super().__init__()
        self.ledger = ledger
        self.limits = ProofLimits.model_validate(read_json(limits_path(ledger)))
        self.inventory = ledger.with_suffix(".objects.jsonl")

    def send(self, request, **kwargs):
        target = urlsplit(request.url)
        path = unquote(target.path)
        prefix = f"/collage/{self.limits.namespace}/users/local-dev/"
        query = parse_qs(target.query)
        scoped = path.startswith("/collage/") and owned_key(
            self.limits.namespace, path.removeprefix("/collage/"),
        )
        listing = (
            request.method == "GET" and path == "/collage"
            and query.get("comp") == ["list"] and query.get("restype") == ["container"]
            and query.get("prefix") in (
                [prefix.removeprefix("/collage/")],
                [prefix.removeprefix("/collage/") + "published/"],
            )
        )
        if target.scheme != "https" or target.netloc != "stclgdevbik2twby4e2zu.blob.core.windows.net" or not (scoped or listing):
            raise StorageUnavailable("Blob proof transport refused a different target or namespace.")
        with project_guard(ProjectStore(self.ledger.parent), "blob-proof-budget"):
            with self.ledger.open(encoding="utf-8") as stream:
                count = sum(1 for _ in stream)
            if count >= self.limits.blob_requests:
                raise StorageUnavailable("The Blob proof request allowance is exhausted.")
            with self.ledger.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps({"method": request.method, "url": request.url}) + "\n")
        response = super().send(request, **kwargs)
        if request.method == "PUT" and query.get("comp") != ["lease"] and response.status_code == 201:
            etag = response.headers.get("ETag")
            if not isinstance(etag, str):
                raise StorageUnavailable("Proof upload returned no ownership ETag; preserve its namespace.")
            with project_guard(ProjectStore(self.ledger.parent), "blob-proof-budget"):
                with self.inventory.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps({"key": path.removeprefix("/collage/"), "etag": etag}) + "\n")
        return response
