import asyncio
import json
import threading
from uuid import uuid4

import azure.functions as func
import pytest

import function_app
from ai_collage.application.conversation import ConversationFlow, ConversationSettings
from ai_collage.application.projects import ProjectFlow, ProjectSetup, configured_store
from ..agent.test_agent import FakeModel, asyncio_wakeup_pair, intent, reply
from .test_project_routes import image_bytes, isolate, payload
from io import BytesIO


@pytest.fixture
def api_flow(monkeypatch):
    store = configured_store()
    ProjectFlow(store).create(
        ProjectSetup(project_id="trip", canvas={"width": 100, "height": 100}),
        [BytesIO(image_bytes()), BytesIO(image_bytes())],
    )
    model = FakeModel(intent("fresh"), reply())
    settings = ConversationSettings(live=True)
    monkeypatch.setattr(function_app, "ConversationFlow", lambda source: ConversationFlow(source, settings, model))
    return store, settings, model


def call(endpoint, *, body=None, raw=None, request_id=None, proposal_id=None, **headers):
    values = {"Host": "127.0.0.1:7071", **headers}
    if body is not None or raw is not None:
        values.setdefault("Content-Type", "application/json")
    req = func.HttpRequest(
        "POST" if body is not None or raw is not None else "GET",
        "http://127.0.0.1:7071/api/projects/trip/conversation",
        headers=values, body=raw if raw is not None else json.dumps(body).encode() if body is not None else b"",
        route_params={"project_id": "trip", "request_id": request_id, "proposal_id": proposal_id},
    )
    return asyncio.run(endpoint(req))


def submission():
    return {"request_id": str(uuid4()), "prompt": "Make a collage",
            "revision": payload(call(function_app.conversation))["revision"]}


def test_real_stage_http_contract_duplicate_posts_and_png(api_flow):
    store, _, model = api_flow
    before = {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()}
    empty = call(function_app.conversation)
    assert empty.status_code == 200 and empty.headers["Cache-Control"] == "no-store"
    assert payload(empty)["messages"] == [] and payload(empty)["live_enabled"]
    assert {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()} == before
    body = submission()
    prepared = call(function_app.conversation_requests, body=body)
    assert prepared.status_code == 201
    op = payload(prepared)
    assert op["status"] == "prepared"
    assert "prepared" not in op and "prompt" not in op and "state_digest" not in op
    assert call(function_app.conversation_requests, body=body).status_code == 200
    completed = call(function_app.conversation_generate, body={"revision": op["revision"]},
                     request_id=body["request_id"])
    assert completed.status_code == 200 and payload(completed)["proposal_id"] == "P001"
    assert len(model.contexts) == 2
    assert call(function_app.conversation_generate, body={"revision": op["revision"]},
                request_id=body["request_id"]).status_code == 200
    read = call(function_app.conversation_operation, request_id=body["request_id"])
    assert payload(read)["status"] == "completed" and len(model.contexts) == 2
    png = call(function_app.proposal_preview, proposal_id="P001")
    assert png.status_code == 200 and png.mimetype == "image/png"
    assert png.get_body().startswith(b"\x89PNG")
    assert png.headers["X-Content-Type-Options"] == "nosniff"
    view = payload(call(function_app.conversation))
    assert view["baseline"]["proposal_id"] == "P001"
    assert view["messages"][-1]["text"] == "Created P001."
    assert store.load("trip").current_version is None


@pytest.mark.parametrize("raw,status", [
    (b'{"request_id":"a","request_id":"b"}', 400),
    (b'{"request_id":1,"prompt":"x","revision":"0"}', 400),
    (b'null', 400),
    (b'{"prompt":false}', 400),
    (b'[]', 400),
    (b' ' * (1024 * 1024 + 1), 413),
])
def test_invalid_stage_json_never_dispatches(api_flow, raw, status):
    store, _, model = api_flow
    before = {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()}
    response = call(function_app.conversation_requests, raw=raw)
    assert response.status_code == status and "error" in payload(response)
    assert not model.contexts
    assert {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()} == before
    assert str(store.data_dir) not in response.get_body().decode()


@pytest.mark.parametrize("changes,status", [
    ({"Origin": "null"}, 403),
    ({"Origin": "https://foreign.example"}, 403),
    ({"Host": "foreign.example"}, 403),
    ({"Content-Type": "text/plain"}, 415),
])
def test_stage_envelope_guards_apply_to_json_posts(api_flow, changes, status):
    response = call(function_app.conversation_requests, body=submission(), **changes)
    assert response.status_code == status and not api_flow[2].contexts


def test_unknown_fields_disabled_host_and_invalid_ids_are_explicit(api_flow):
    _, settings, model = api_flow
    response = call(function_app.conversation_requests, body={**submission(), "handoff": {}})
    assert response.status_code == 400
    settings.live = False
    response = call(function_app.conversation_requests, body=submission())
    assert response.status_code == 503 and payload(response)["error"]["code"] == "live_disabled"
    assert payload(call(function_app.conversation))["live_enabled"] is False
    assert call(function_app.conversation_operation, request_id="../elsewhere").status_code == 400
    assert call(function_app.conversation_operation, request_id=str(uuid4())).status_code == 404
    assert not model.contexts


def test_rendering_does_not_block_worker_status_or_project_listing(api_flow, monkeypatch):
    import ai_collage.agent.conversation as conversation_module

    body = submission()
    prepared = payload(call(function_app.conversation_requests, body=body))
    entered = threading.Event()
    release = threading.Event()
    render = conversation_module.render_layout

    def held_render(*args, **kwargs):
        entered.set()
        assert release.wait(5), "Offline render gate was not released."
        return render(*args, **kwargs)

    monkeypatch.setattr(conversation_module, "render_layout", held_render)
    watchdog = threading.Timer(3, release.set)
    watchdog.start()

    async def observe():
        req = func.HttpRequest(
            "POST", "http://127.0.0.1:7071/api/projects/trip/conversation/requests/x/generate",
            headers={"Host": "127.0.0.1:7071", "Content-Type": "application/json"},
            body=json.dumps({"revision": prepared["revision"]}).encode(),
            route_params={"project_id": "trip", "request_id": body["request_id"]},
        )
        generating = asyncio.create_task(function_app.conversation_generate(req))
        try:
            assert await asyncio.to_thread(entered.wait, 2)
            assert not release.is_set(), "Rendering blocked the worker event loop until the watchdog fired."
            listing = func.HttpRequest(
                "GET", "http://127.0.0.1:7071/api/projects",
                headers={"Host": "127.0.0.1:7071"}, body=b"",
            )
            status = func.HttpRequest(
                "GET", "http://127.0.0.1:7071/api/projects/trip/conversation",
                headers={"Host": "127.0.0.1:7071"}, body=b"",
                route_params={"project_id": "trip"},
            )
            projects, current = await asyncio.wait_for(asyncio.gather(
                asyncio.to_thread(function_app.projects, listing),
                function_app.conversation(status),
            ), timeout=1)
            assert projects.status_code == 200 and len(payload(projects)["projects"]) == 1
            assert payload(current)["operation"]["status"] == "generating"
            assert not generating.done() and not release.is_set()
        finally:
            release.set()
            result = await generating
            assert result.status_code == 200

    try:
        asyncio.run(observe())
    finally:
        release.set()
        watchdog.cancel()
