import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import azure.functions as func
from PIL import Image
import pytest

import function_app
from ai_collage.agent.conversation import Conversation
from ai_collage.engine.projects import ProjectStore


def image_bytes(format="JPEG", *, size=(20, 10), orientation=None):
    output = io.BytesIO()
    with Image.new("RGB", size, "red") as image:
        kwargs = {}
        if orientation is not None:
            exif = Image.Exif()
            exif[274] = orientation
            kwargs["exif"] = exif
        image.save(output, format=format, **kwargs)
    return output.getvalue()


def multipart(fields):
    boundary = "collage-test-boundary"
    parts = []
    for name, value in fields:
        header = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
        if isinstance(value, bytes):
            header += '; filename="../../untrusted.jpg"\r\nContent-Type: image/jpeg'
        else:
            value = value.encode()
        parts.append(header.encode() + b"\r\n\r\n" + value + b"\r\n")
    return b"".join(parts) + f"--{boundary}--\r\n".encode(), f"multipart/form-data; boundary={boundary}"


def setup_data(project_id="trip"):
    return {"project_id": project_id, "canvas": {"width": 1600, "height": 900}}


def fields(project_id="trip"):
    return [
        ("metadata", json.dumps(setup_data(project_id))),
        ("photo_2", image_bytes("PNG")),
        ("photo_1", image_bytes(orientation=6)),
    ]


@pytest.fixture(autouse=True)
def isolate(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_COLLAGE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AI_COLLAGE_API_AUTHORITY", "127.0.0.1:7071")
    monkeypatch.setenv("AI_COLLAGE_UI_ORIGIN", "http://127.0.0.1:5173")
    def blocked(*args, **kwargs):
        raise AssertionError("External services are forbidden")
    monkeypatch.setattr(socket.socket, "connect", blocked)


def request(method="GET", *, parts=None, route=None, **headers):
    body, content_type = multipart(parts) if parts is not None else (b"", "")
    values = {"Host": "127.0.0.1:7071", "Content-Type": content_type, **headers}
    return func.HttpRequest(method, "http://127.0.0.1:7071/api/projects",
                           headers=values, body=body, route_params=route or {})


def post(parts=None, **headers):
    return function_app.projects(request("POST", parts=fields() if parts is None else parts, **headers))


def detail(project_id="trip"):
    return function_app.project(request(route={"project_id": project_id}))


def payload(response):
    return json.loads(response.get_body())


def test_create_list_reopen_photo_and_existing_conversation_without_writes(tmp_path):
    root = tmp_path / "data"
    assert payload(function_app.projects(request())) == {"projects": []}
    assert not root.exists()
    response = post()
    assert response.status_code == 201
    data = payload(response)
    assert data == {
        **setup_data(), "photos": [
            {"photo_id": 1, "width": 10, "height": 20},
            {"photo_id": 2, "width": 20, "height": 10},
        ],
    }
    assert response.headers["Location"] == "/api/projects/trip"
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert payload(detail()) == data
    assert payload(function_app.projects(request()))["projects"] == [
        {**setup_data(), "photo_count": 2},
    ]
    image = function_app.photo(request(route={"project_id": "trip", "photo_id": "1"}))
    assert image.status_code == 200
    assert image.get_body() == image_bytes(orientation=6)
    assert image.mimetype == "image/jpeg"
    assert image.headers["X-Content-Type-Options"] == "nosniff"
    conversation = Conversation(ProjectStore(root), "trip")
    assert conversation.state.controls.width == 1600
    assert conversation.state.controls.height == 900
    assert conversation.state.history == []
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before
    assert len(list(root.rglob("*.png"))) == 1
    duplicate = post()
    assert duplicate.status_code == 409
    assert payload(duplicate)["error"]["code"] == "project_exists"
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("change,status", [
    (lambda f: f + [f[0]], 400),
    (lambda f: f + [f[1]], 400),
    (lambda f: f[1:], 400),
    (lambda f: [f[0], f[1], ("photo_3", f[2][1])], 400),
    (lambda f: f + [("surprise", "value")], 400),
    (lambda f: [("metadata", '{"project_id":"trip","project_id":"other","canvas":{"width":1,"height":1}}'), *f[1:]], 400),
    (lambda f: [("metadata", json.dumps({"project_id": "con", "canvas": {"width": 1, "height": 1}})), *f[1:]], 400),
    (lambda f: [("metadata", json.dumps({"project_id": "../other", "canvas": {"width": 1, "height": 1}})), *f[1:]], 400),
    (lambda f: [("metadata", json.dumps({"project_id": "trip", "canvas": {"width": True, "height": 1}})), *f[1:]], 400),
    (lambda f: [("metadata", json.dumps({"project_id": "trip", "canvas": {"width": "100", "height": 1}})), *f[1:]], 400),
    (lambda f: [f[0], f[1], ("photo_1", b"not an image")], 400),
    (lambda f: [f[0], f[1], ("photo_1", image_bytes("BMP"))], 415),
    (lambda f: [("metadata", " " * (16 * 1024 + 1)), *f[1:]], 413),
])
def test_invalid_uploads_are_explicit_and_never_publish(change, status, tmp_path):
    response = post(change(fields()))
    assert response.status_code == status
    assert "error" in payload(response)
    assert str(tmp_path) not in response.get_body().decode()
    assert payload(function_app.projects(request())) == {"projects": []}
    assert not list((tmp_path / "data").rglob(".create-*"))
    assert not list((tmp_path / "data").rglob("uploads/*"))


@pytest.mark.parametrize("header,value", [
    ("Host", "attacker.example:7071"), ("Origin", "https://attacker.example"), ("Origin", "null"),
])
def test_disallowed_authority_and_origin_cannot_write(header, value, tmp_path):
    assert post(**{header: value}).status_code == 403
    assert not (tmp_path / "data").exists()


def test_size_boundary_uses_actual_bytes_not_content_length():
    raw = image_bytes()
    exact = raw + b"\0" * (25 * 1024 * 1024 - len(raw))
    assert post([fields()[0], ("photo_1", exact), ("photo_2", raw)],
                **{"Content-Length": "1"}).status_code == 201
    assert post([("metadata", json.dumps(setup_data("large"))),
                 ("photo_1", exact + b"\0"), ("photo_2", raw)]).status_code == 413


def test_multiframe_and_actual_decoded_pixel_limit(tmp_path):
    output = io.BytesIO()
    with Image.new("RGB", (20, 10), "red") as first, Image.new("RGB", (20, 10), "blue") as second:
        first.save(output, format="PNG", save_all=True, append_images=[second])
    assert post([fields()[0], ("photo_1", output.getvalue()), fields()[1]]).status_code == 415
    assert post([fields()[0], ("photo_1", image_bytes(size=(8001, 5000))), fields()[1]]).status_code == 413
    assert payload(function_app.projects(request())) == {"projects": []}
    assert not list((tmp_path / "data").rglob(".create-*"))


def test_body_limit_uses_actual_length_before_multipart_parsing():
    response = function_app.projects(func.HttpRequest(
        "POST", "http://127.0.0.1:7071/api/projects",
        headers={"Host": "127.0.0.1:7071", "Content-Type": "multipart/form-data; boundary=x",
                 "Content-Length": "1"},
        body=b"x" * (160 * 1024 * 1024 + 1),
    ))
    assert response.status_code == 413
    assert payload(response)["error"]["code"] == "request_too_large"


def test_storage_read_failure_is_not_an_empty_collection(monkeypatch, tmp_path):
    original = Path.iterdir
    def denied(path):
        if path == ProjectStore(tmp_path / "data").projects_dir:
            raise PermissionError("injected read failure")
        return original(path)
    monkeypatch.setattr(Path, "iterdir", denied)
    response = function_app.projects(request())
    assert response.status_code == 500
    assert payload(response)["error"]["code"] == "storage_error"
    assert str(tmp_path) not in response.get_body().decode()


def test_corrupt_state_missing_assets_and_unknown_photo_are_distinct(tmp_path):
    assert detail().status_code == 404
    assert post().status_code == 201
    assert function_app.photo(request(route={"project_id": "trip", "photo_id": "3"})).status_code == 404
    root = tmp_path / "data"
    store = ProjectStore(root)
    state = store.project_dir("trip") / "conversation" / "state.json"
    before = state.read_bytes()
    state.write_bytes(before.replace(b'"record_version":8', b'"record_version":0'))
    assert detail().status_code == 409
    assert function_app.projects(request()).status_code == 409
    state.write_bytes(before)
    store.photo_paths(store.load("trip"))[1].unlink()
    assert detail().status_code == 409


def test_invalid_published_entry_does_not_look_missing_or_initialize_state(tmp_path):
    store = ProjectStore(tmp_path / "data")
    store.projects_dir.mkdir(parents=True)
    entry = store.project_dir("trip")
    entry.write_bytes(b"not a project directory")
    assert detail().status_code == 409
    assert payload(function_app.projects(request()))["error"]["code"] == "invalid_project_state"
    assert entry.read_bytes() == b"not a project directory"
    entry.unlink()
    assert post().status_code == 201
    state = entry / "conversation" / "state.json"
    state.unlink()
    assert detail().status_code == 409
    assert not state.exists()


@pytest.mark.parametrize("stage", ["import", "state", "publication"])
def test_failed_creation_cleans_owned_assets_and_preserves_existing(stage, monkeypatch, tmp_path):
    assert post().status_code == 201
    root = tmp_path / "data"
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    def fail(*args, **kwargs):
        raise OSError("injected failure")
    if stage == "state":
        monkeypatch.setattr("ai_collage.application.projects.Conversation", fail)
    elif stage == "publication":
        original = Path.rename
        def rename(source, destination):
            if Path(destination) == ProjectStore(root).project_dir("other"):
                return fail()
            return original(source, destination)
        monkeypatch.setattr(Path, "rename", rename)
    else:
        monkeypatch.setattr("ai_collage.engine.projects.load_photo", fail)
    assert post(fields("other")).status_code == 500
    for path, content in before.items():
        assert path.read_bytes() == content
    assert not ProjectStore(root).project_dir("other").exists()
    assert set(ProjectStore(root).uploads_dir.iterdir()) == set(
        p for p in before if p.parent == ProjectStore(root).uploads_dir
    )
    assert not list(ProjectStore(root).projects_dir.glob(".create-*"))


def test_lock_is_cross_process_and_released_after_writer_exit(tmp_path):
    root = tmp_path / "data"
    code = """
import sys, time
from pathlib import Path
from ai_collage.engine.projects import ProjectStore
from ai_collage.application.projects import project_guard
with project_guard(ProjectStore(Path(sys.argv[1])), 'trip'):
    print('locked', flush=True)
    time.sleep(60)
"""
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])}
    process = subprocess.Popen([sys.executable, "-c", code, str(root)], env=env,
                               stdout=subprocess.PIPE, text=True)
    try:
        assert process.stdout.readline().strip() == "locked"
        assert payload(post())["error"]["code"] == "project_busy"
    finally:
        process.terminate()
        process.wait(timeout=10)
        process.stdout.close()
    assert post().status_code == 201


@pytest.mark.parametrize("value", ["", "relative"])
def test_invalid_data_configuration_is_explicit(value, monkeypatch):
    monkeypatch.setenv("AI_COLLAGE_DATA_DIR", value)
    assert function_app.projects(request()).status_code == 500
