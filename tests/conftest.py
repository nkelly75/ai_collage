import socket

import pytest

from ai_collage.projects import ProjectStore

from .helpers import photo_file


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Offline tests must not open network connections.")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def store(tmp_path):
    return ProjectStore(tmp_path / "data")


@pytest.fixture
def sources(tmp_path):
    return [
        photo_file(tmp_path / "one.png", (40, 20), "red"),
        photo_file(tmp_path / "two.png", (20, 40), "blue"),
    ]
