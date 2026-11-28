import asyncio
import json
import logging
import os

import azure.functions as func
from pydantic import ValidationError

from ai_collage.engine.models import MAX_JSON_BYTES, CollageError
from ai_collage.engine.projects import parse_json
from ai_collage.application.projects import FlowError, ProjectFlow, ProjectSetup, configured_store
from ai_collage.application.conversation import ConversationFlow, GenerationRequest, SelectionSubmission, Submission
from ai_collage.storage.contracts import StorageOutcomeUnknown, StorageUnavailable
from storage_config import conversation_flow, project_flow
from request_metrics import measure_request


MAX_BODY_BYTES = 160 * 1024 * 1024
app = func.FunctionApp()


def json_response(value: dict, status: int = 200, **headers: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(value), status_code=status, mimetype="application/json",
        headers={"Cache-Control": "no-store", **headers},
    )


def check_request(req: func.HttpRequest) -> None:
    authority = os.environ.get("AI_COLLAGE_API_AUTHORITY", "127.0.0.1:7071")
    origin = os.environ.get("AI_COLLAGE_UI_ORIGIN", "http://127.0.0.1:5173")
    if req.headers.get("Host") != authority:
        raise FlowError("forbidden_host", "Request Host is not the configured local API.", 403)
    if req.method == "POST" and req.headers.get("Origin") not in {None, origin}:
        raise FlowError("forbidden_origin", "Request Origin is not the configured local UI.", 403)


def create_project(req: func.HttpRequest, flow: ProjectFlow) -> dict:
    if not req.headers.get("Content-Type", "").lower().startswith("multipart/form-data;"):
        raise FlowError("unsupported_media", "Use a multipart/form-data upload.", 415)
    if len(req.get_body()) > MAX_BODY_BYTES:
        raise FlowError("request_too_large", "Upload exceeds the 160 MiB request limit.", 413)
    files = req.files
    try:
        form = req.form
        names = [f"photo_{n}" for n in range(1, len(files) + 1)]
        if (
            set(form) != {"metadata"} or len(form.getlist("metadata")) != 1
            or not 2 <= len(files) <= 6 or set(files) != set(names)
            or any(len(files.getlist(name)) != 1 for name in files)
        ):
            raise FlowError("invalid_request", "Supply metadata and 2-6 unique, contiguous photo_1...photo_N fields.")
        raw = form["metadata"].encode("utf-8")
        if len(raw) > 16 * 1024:
            raise FlowError("request_too_large", "Metadata exceeds 16 KiB.", 413)
        setup = ProjectSetup.model_validate(parse_json(raw))
        return flow.create(setup, [files[name].stream for name in names])
    finally:
        for name in files:
            for upload in files.getlist(name):
                upload.close()


def dispatch(req: func.HttpRequest, operation: str) -> func.HttpResponse:
    try:
        with measure_request(req.method, operation) as metrics:
            response = _dispatch_project(req, operation)
            if metrics is not None:
                metrics.complete(response.status_code, len(response.get_body()))
                response.headers["X-Collage-Metrics-Id"] = metrics.identifier
            return response
    except FlowError as exc:
        return request_error(exc)


def _dispatch_project(req: func.HttpRequest, operation: str) -> func.HttpResponse:
    try:
        check_request(req)
        with project_flow() as flow:
            if operation == "collection":
                if req.method == "POST":
                    result = create_project(req, flow)
                    return json_response(result, 201, Location=f"/api/projects/{result['project_id']}")
                return json_response({"projects": flow.list()})
            project_id = req.route_params["project_id"]
            if operation == "detail":
                return json_response(flow.detail(project_id))
            number = req.route_params["photo_id"]
            if not number.isascii() or not number.isdecimal() or len(number) > 2:
                raise FlowError("not_found", "Photo not found.", 404)
            raw, content_type = flow.photo(project_id, int(number))
            return func.HttpResponse(raw, mimetype=content_type, headers={
                "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            })
    except Exception as exc:
        return request_error(exc)


def request_error(exc: Exception) -> func.HttpResponse:
    if isinstance(exc, FlowError):
        return json_response({"error": {"code": exc.code, "message": str(exc)}}, exc.status)
    if isinstance(exc, StorageOutcomeUnknown):
        logging.exception("Blob publication outcome is unknown")
        return json_response({"error": {
            "code": "outcome_unknown", "message": "Publication may have completed; inspect saved project/request/action state before any retry.",
        }}, 500)
    if isinstance(exc, StorageUnavailable):
        logging.exception("Blob storage operation failed")
        return json_response({"error": {
            "code": "storage_unavailable", "message": "Blob storage is unavailable; check access and saved state.",
        }}, 503)
    if isinstance(exc, (ValidationError, CollageError, ValueError)):
        logging.info("Invalid API request: %s", type(exc).__name__)
        code, message, status = "invalid_request", "Invalid request ID, body or saved resource.", 400
    elif isinstance(exc, OSError):
        logging.exception("Local storage operation failed")
        code, message, status = "storage_error", "Local storage operation failed; check saved state before retrying.", 500
    else:
        logging.exception("Unexpected API failure")
        code, message, status = "server_error", "Operation failed; check saved state before retrying.", 500
    return json_response({"error": {"code": code, "message": message}}, status)


def json_body(req: func.HttpRequest) -> object:
    if req.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise FlowError("unsupported_media", "Use an application/json body.", 415)
    raw = req.get_body()
    if len(raw) > MAX_JSON_BYTES:
        raise FlowError("request_too_large", "JSON body exceeds 1 MiB.", 413)
    return parse_json(raw)


def _dispatch_conversation(req: func.HttpRequest, operation: str) -> func.HttpResponse:
    try:
        check_request(req)
        with conversation_flow() as flow:
            project_id = req.route_params["project_id"]
            if operation == "conversation":
                return json_response(flow.detail(project_id))
            if operation == "requests":
                submission = Submission.model_validate(json_body(req))
                result, created = asyncio.run(flow.interpret(project_id, submission))
                return json_response(result, 201 if created else 200)
            if operation == "operation":
                return json_response(flow.operation(project_id, req.route_params["request_id"]))
            if operation == "generate":
                body = GenerationRequest.model_validate(json_body(req))
                return json_response(asyncio.run(flow.generate(project_id, req.route_params["request_id"], body)))
            if operation == "selections":
                body = SelectionSubmission.model_validate(json_body(req))
                result, created = flow.select(project_id, body)
                return json_response(result, 201 if created else 200)
            if operation == "selection":
                return json_response(flow.selection(project_id, req.route_params["action_id"]))
            raw = (
                flow.thumbnail(project_id, req.route_params["proposal_id"]) if operation == "thumbnail"
                else flow.preview(project_id, req.route_params["proposal_id"])
            )
            return func.HttpResponse(raw, mimetype="image/png", headers={
                "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
            })
    except Exception as exc:
        return request_error(exc)


async def dispatch_conversation(req: func.HttpRequest, operation: str) -> func.HttpResponse:
    # Rendering and snapshot validation must not occupy the Functions event loop.
    try:
        with measure_request(req.method, operation) as metrics:
            response = await asyncio.to_thread(_dispatch_conversation, req, operation)
            if metrics is not None:
                metrics.complete(response.status_code, len(response.get_body()))
                response.headers["X-Collage-Metrics-Id"] = metrics.identifier
            return response
    except FlowError as exc:
        return request_error(exc)


@app.route(route="projects", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
def projects(req: func.HttpRequest) -> func.HttpResponse:
    return dispatch(req, "collection")


@app.route(route="projects/{project_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def project(req: func.HttpRequest) -> func.HttpResponse:
    return dispatch(req, "detail")


@app.route(route="projects/{project_id}/photos/{photo_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def photo(req: func.HttpRequest) -> func.HttpResponse:
    return dispatch(req, "photo")


@app.route(route="projects/{project_id}/conversation", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
async def conversation(req: func.HttpRequest) -> func.HttpResponse:
    return await dispatch_conversation(req, "conversation")


@app.route(route="projects/{project_id}/conversation/requests", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def conversation_requests(req: func.HttpRequest) -> func.HttpResponse:
    return await dispatch_conversation(req, "requests")


@app.route(route="projects/{project_id}/conversation/requests/{request_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
async def conversation_operation(req: func.HttpRequest) -> func.HttpResponse:
    return await dispatch_conversation(req, "operation")


@app.route(route="projects/{project_id}/conversation/requests/{request_id}/generate", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def conversation_generate(req: func.HttpRequest) -> func.HttpResponse:
    return await dispatch_conversation(req, "generate")


@app.route(route="projects/{project_id}/conversation/selections", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def conversation_selections(req: func.HttpRequest) -> func.HttpResponse:
    return await dispatch_conversation(req, "selections")


@app.route(route="projects/{project_id}/conversation/selections/{action_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
async def conversation_selection(req: func.HttpRequest) -> func.HttpResponse:
    return await dispatch_conversation(req, "selection")


@app.route(route="projects/{project_id}/proposals/{proposal_id}/preview", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
async def proposal_preview(req: func.HttpRequest) -> func.HttpResponse:
    return await dispatch_conversation(req, "preview")


@app.route(route="projects/{project_id}/proposals/{proposal_id}/thumbnail", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
async def proposal_thumbnail(req: func.HttpRequest) -> func.HttpResponse:
    return await dispatch_conversation(req, "thumbnail")
