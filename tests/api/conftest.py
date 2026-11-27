import pytest

from storage_config import BLOB_VARIABLES


@pytest.fixture(autouse=True)
def isolate_api_storage_configuration(monkeypatch):
    monkeypatch.delenv("AI_COLLAGE_STORAGE_BACKEND", raising=False)
    for name in BLOB_VARIABLES:
        monkeypatch.delenv(name, raising=False)
