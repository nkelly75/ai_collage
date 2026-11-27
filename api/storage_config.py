"""Explicit local/API-only Blob selection; no Azure imports in the Local path."""

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import re

from ai_collage.application.projects import FlowError, ProjectFlow, configured_store


DEV_ACCOUNT_URL = "https://stclgdevbik2twby4e2zu.blob.core.windows.net"
DEV_CONTAINER = "collage"
DEV_SUBSCRIPTION = "0c6a09a0-a933-49df-9b6b-b8f65440332f"
BLOB_VARIABLES = (
    "AI_COLLAGE_BLOB_ACCOUNT_URL", "AI_COLLAGE_BLOB_CONTAINER",
    "AI_COLLAGE_BLOB_SUBSCRIPTION_ID", "AI_COLLAGE_BLOB_NAMESPACE",
    "AI_COLLAGE_BLOB_PROOF_LEDGER",
)


def backend() -> str:
    value = os.environ.get("AI_COLLAGE_STORAGE_BACKEND", "Local").lower()
    if value not in {"local", "blob"}:
        raise FlowError("configuration_error", "Choose Local or Blob API storage.", 500)
    return value


@dataclass(frozen=True)
class BlobSettings:
    namespace: str
    ledger: Path | None


def blob_settings() -> BlobSettings:
    expected = {
        "AI_COLLAGE_BLOB_ACCOUNT_URL": {DEV_ACCOUNT_URL, DEV_ACCOUNT_URL + "/"},
        "AI_COLLAGE_BLOB_CONTAINER": {DEV_CONTAINER},
        "AI_COLLAGE_BLOB_SUBSCRIPTION_ID": {DEV_SUBSCRIPTION},
    }
    if any(os.environ.get(name) not in values for name, values in expected.items()):
        raise FlowError("configuration_error", "Configure the recorded development Blob target explicitly.", 500)
    namespace = os.environ.get("AI_COLLAGE_BLOB_NAMESPACE", "")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", namespace):
        raise FlowError("configuration_error", "Supply a valid isolated Blob namespace.", 500)
    if os.environ.get("AI_COLLAGE_LIVE") not in {None, "0"} or any(
        os.environ.get(name) for name in (
            "AI_COLLAGE_CALL_BUDGET_PATH", "AI_COLLAGE_MAX_CALLS", "AI_COLLAGE_TRIAL_PROJECT",
        )
    ):
        raise FlowError("configuration_error", "Blob slice mode cannot enable model/trial work.", 500)
    value = os.environ.get("AI_COLLAGE_BLOB_PROOF_LEDGER")
    ledger = None if value is None else Path(value)
    if ledger is not None and (
        not value or not ledger.is_absolute() or not ledger.is_file()
        or not namespace.startswith("proof-019b-")
    ):
        raise FlowError("configuration_error", "Invalid opt-in Blob proof ledger.", 500)
    return BlobSettings(namespace, ledger)


def reject_blob_conversation() -> None:
    if backend() == "blob":
        blob_settings()
        raise FlowError("blob_slice_only", "Conversation and proposal operations are not supported in Blob mode yet.", 501)


@contextmanager
def project_flow():
    if backend() == "local":
        yield ProjectFlow(configured_store())
        return
    settings = blob_settings()
    from azure.identity import AzureCliCredential
    from azure.storage.blob import ContainerClient
    from ai_collage.storage.blob import BlobProjectStorage

    options = {}
    if settings.ledger is not None:
        from blob_proof import ProofTransport
        options["transport"] = ProofTransport(settings.ledger)
    with AzureCliCredential(subscription=DEV_SUBSCRIPTION, process_timeout=10) as credential:
        with ContainerClient(
            DEV_ACCOUNT_URL, DEV_CONTAINER, credential=credential, retry_total=0,
            connection_timeout=10, read_timeout=30, **options,
        ) as container:
            yield ProjectFlow(configured_store(), BlobProjectStorage(container, settings.namespace))
