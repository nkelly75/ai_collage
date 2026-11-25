import json
import logging
import os

import azure.functions as func
from pydantic import ValidationError

from ai_collage.engine.models import CollageError
from ai_collage.engine.projects import parse_json
from ai_collage.application.projects import FlowError, ProjectFlow, ProjectSetup, configured_store


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
        raise FlowError("forbidden_origin", "Upload Origin is not the configured local UI.", 403)


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
        check_request(req)
        flow = ProjectFlow(configured_store())
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
    except FlowError as exc:
        return json_response({"error": {"code": exc.code, "message": str(exc)}}, exc.status)
    except (ValidationError, CollageError, ValueError) as exc:
        logging.info("Invalid project request: %s", type(exc).__name__)
        return json_response({"error": {"code": "invalid_request", "message": "Invalid project ID, metadata or upload."}}, 400)
    except OSError:
        logging.exception("Local project storage operation failed")
        return json_response({"error": {"code": "storage_error", "message": "Local storage operation failed; check saved state before retrying."}}, 500)
    except Exception:
        logging.exception("Unexpected project API failure")
        return json_response({"error": {"code": "server_error", "message": "Project operation failed; check saved state before retrying."}}, 500)


@app.route(route="projects", methods=["GET", "POST"], auth_level=func.AuthLevel.ANONYMOUS)
def projects(req: func.HttpRequest) -> func.HttpResponse:
    return dispatch(req, "collection")


@app.route(route="projects/{project_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def project(req: func.HttpRequest) -> func.HttpResponse:
    return dispatch(req, "detail")


@app.route(route="projects/{project_id}/photos/{photo_id}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def photo(req: func.HttpRequest) -> func.HttpResponse:
    return dispatch(req, "photo")
