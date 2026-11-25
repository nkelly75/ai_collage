# Architecture

The original Python backend remains the core: models can propose layouts, but
deterministic code validates geometry and renders the original photos. The CLI
and local web/API are different entry points into that backend, not separate
collage implementations.

This describes the current code, not a deployment plan. The
[planning index](planning/README.md) tracks approval gates and implementation
status; the [README](README.md) is the usage entry point.

## Packages and adapters

| Area | Responsibility | Useful starting points |
|---|---|---|
| `ai_collage\engine` | Offline layout/project contracts, geometry, photo validation, deterministic rendering and project storage. | [Models](ai_collage/engine/models.py), [geometry](ai_collage/engine/geometry.py), [imaging](ai_collage/engine/imaging.py), [ProjectStore](ai_collage/engine/projects.py) |
| `ai_collage\agent` | Conversation state, photo-reference memory, interpretation, proposals and acceptance; optional, bounded model requests. Uses the engine to validate and render, rather than generating replacement images. | [Conversation](ai_collage/agent/conversation.py), [requests](ai_collage/agent/requests.py), [provider](ai_collage/agent/provider.py) |
| `ai_collage\application` | User-operation orchestration across engine and agent capabilities. Currently coordinates project creation, listing, reopening and photo retrieval. | [Package purpose](ai_collage/application/__init__.py), [ProjectFlow](ai_collage/application/projects.py) |
| `ai_collage\cli` | Command parsing and terminal presentation for engine, conversation and evaluation operations. | [Main CLI](ai_collage/cli/main.py), [chat](ai_collage/cli/chat.py) |
| `ai_collage\evaluation` | Scripted conversation replay and offline assessment of saved evidence; tooling, not part of an ordinary web request. Live replay requires separate authorization. | [Replay](ai_collage/evaluation/replay.py), [assessment](ai_collage/evaluation/assess.py) |
| `api` | Thin Azure Functions HTTP adapter and local host configuration/launcher. Translates requests into application calls and results/errors into HTTP responses. | [Functions](api/function_app.py), [launcher](api/start.ps1) |
| `web` | React/TypeScript UI, temporary selection previews and API client. Also contains an isolated scripted demo, not another renderer or language interpreter. | [App](web/src/App.tsx), [API client](web/src/api.ts), [demo](web/src/useDemo.ts) |

## How the entry points fit together

Arrows show the main calls/dependencies, not every helper import. Python
package names below are under `ai_collage`, except for `api` and `web`.

```text
web (React UI)
    |
    | HTTP
    v
api (Functions adapter)
    |
    | ordinary Python calls
    v
application (ProjectFlow)
    |                 |
    v                 v
  engine <---------- agent

cli ----------------> engine / agent / evaluation
evaluation ---------> engine / agent
```

The CLI currently calls engine/agent capabilities directly; it does not route
through `ProjectFlow` or start Functions. Both paths use the same Python source.
The application package adds coordination where an operation spans those
existing capabilities.

`Conversation.request()` composes the same separately callable `interpret()`
and `generate()` stages. Interpretation either finishes with a normal result
(question, naming confirmation, acknowledgement or exact selection), or returns
a typed `PreparedGeneration` handoff. That data-only value can round-trip
through JSON and continue with fresh conversation/request objects or a new
process. It binds the project/photos, saved state/history and layout sources,
task boundary, consumed correction allowance, limits and reasoning settings;
stale or already-used handoffs are rejected before another model call.
The existing correction/validation/publication loop is shared, not copied.
No new ordinary-project record or layout format is introduced. This is an
internal agent contract, not authority to trust browser-supplied intent;
HTTP operation storage and concurrency remain future application/API work.

The real web path currently supports create/save/list/reopen and photo serving.
Its agent use is empty conversation initialization, not live chat or generation.
The separate `/demo` route simulates conversation/proposals with bundled assets;
it is not evidence that conversational API integration is implemented.

## A web create request, end to end

1. `web\src\api.ts` sends selected files and project/canvas metadata as a
   multipart HTTP request.
2. `api\function_app.py` checks the HTTP envelope, local Host/Origin and request
   limits, parses metadata/file fields, then calls `ProjectFlow.create`.
3. `ai_collage\application\projects.py` locks the project ID and stages the
   uploaded streams as temporary files. It calls the existing
   `ProjectStore.create` to import photos and create normal project records.
4. It constructs the existing `Conversation` to initialize normal conversation
   state, including canvas controls. This does not make a model request.
5. It publishes the completed project last, with rollback for handled failures.
   The Functions adapter returns the result as HTTP 201; the UI navigates only
   after confirmed success.

The additional application-level staging makes project creation and initial
conversation setup one published operation. It does not replace the engine's
photo importer, project models or storage format. There are no CLI subprocesses,
copied backend sources or second web-only project/conversation implementations.

Reopening uses `ProjectFlow` to validate the existing project, conversation and
photo identity without initializing or repairing saved state. Photo responses
serve the imported original bytes; image validation still uses the engine.

## Boundaries to preserve

- Keep layout validation, geometry and rendering in `engine`. It must not depend
  on agent, application, CLI, Functions or React.
- Keep conversational behavior and model-provider integration in `agent`.
  Application workflows reuse it rather than implementing a second agent.
- Put cross-capability workflows in `application`; keep Functions request and
  response types in `api`. The current workflow uses plain Python models,
  streams and backend objects, with no Azure Functions SDK dependency.
- Keep browser state/presentation in `web`. Client-side checks help the user;
  authoritative validation and persistence remain in Python.

Current layout details belong in the [field guide](docs/layout-format.md) and
[schema](docs/layout.schema.json), not duplicated here.

## Storage, environments and tests

Web projects default to the separate checkout-relative `.collage-data-web`
root. The CLI selects its root through `--data-dir`; web listing does not
discover CLI roots or archives. Both paths use the existing backend record
formats. Web canvas settings live in conversation controls, not another
web-specific settings file.

The root `.venv` and `api\.venv` are separate dependency environments, not
separate backends. The Functions worker uses the API environment, which adds
the Functions SDK while importing the same checkout source. React has its own
Node toolchain; it does not render collages.

Python tests share the root `tests` tree. For example,
[application tests](tests/application/test_project_flow.py) exercise workflows
directly, while [API tests](tests/api/test_project_routes.py) exercise the HTTP
adapter. Frontend tests remain under `web\src`. Suite/environment commands live
in the [CLI guide](docs/cli-guide.md#verification) and [API README](api/README.md#offline-tests).

The current host and storage are local development facilities. Anonymous
Functions routes and local-origin restrictions are not production
authentication. Deployment packaging, authenticated cloud hosting and private
Blob persistence remain future work; see the [API](api/README.md) and
[UI](web/README.md) guides for current setup and limits.
