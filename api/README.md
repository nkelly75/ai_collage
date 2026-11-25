# Local Python project API

Loopback-only Azure Functions routes create, list and reopen local photo/canvas
projects. Thin HTTP adapters call `ai_collage.application.projects` directly,
coordinating the existing engine importer and empty, model-free conversation
initialization.
No source copies, CLI subprocesses, model credentials or cloud storage are used.
The routes are anonymous development endpoints, not a deployable authentication
or ownership boundary.

## Setup and start in PowerShell

Use Python 3.12 and Core Tools 4.17.0 or newer 4.x. The original user-run
toolchain steps are in the [tooling guide](../planning/018b_tooling.md).
For a fresh API environment, from the checkout root:

```powershell
python -m venv .\api\.venv
.\api\.venv\Scripts\python.exe -m pip install -r .\api\requirements-dev.txt
.\api\.venv\Scripts\python.exe -m pip check
```

Skip installation when already set up. `api\requirements.txt` includes the
root engine requirements (Pillow/Pydantic) alongside the Functions SDK; the
root `.venv` is not used by the worker.

In a separate PowerShell terminal from Vite:

```powershell
.\api\start.ps1
```

The launcher selects `api\.venv`, adds the checkout to the process-local
`PYTHONPATH`, binds **127.0.0.1:7071**, and allows exactly
**http://127.0.0.1:5173** through CORS. It disables Core Tools telemetry,
keeps host secrets local and clears inherited storage/telemetry connections.
It never installs packages or changes global settings, and restores its
environment/cwd on exit, including failure. No activation,
`local.settings.json`, connection string, extension bundle or emulator is needed.
Stop with Ctrl+C; do not terminate unrelated processes occupying these ports.

To use another free loopback pair, match the UI's address and API base:

```powershell
.\api\start.ps1 -Port 7072 -UiOrigin http://127.0.0.1:5174
# Separate UI terminal:
$env:VITE_API_BASE_URL = 'http://127.0.0.1:7072'
npm --prefix .\web run dev -- --port 5174
```

`localhost` and `127.0.0.1` are different origins. Do not use wildcard CORS.
The host's printed `localhost` URL is not binding evidence:

```powershell
Invoke-RestMethod http://127.0.0.1:7071/api/projects
Get-NetTCPConnection -State Listen -LocalPort 7071,5173 |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

Expect loopback listeners, not `0.0.0.0`/`::`.

## Storage and request contract

New web projects default to **`.collage-data-web` under the checkout**, regardless
of the terminal directory. An optional **absolute** `AI_COLLAGE_DATA_DIR` selects
an isolated root; blank/relative overrides fail. Set it before starting the API.
There is no discovery/migration of other CLI roots or archives.
The fixed owner is `local-dev`, not an authenticated user.

| Route | Result |
|---|---|
| `GET /api/projects` | `{"projects":[{"project_id":"trip","canvas":{"width":1600,"height":900},"photo_count":2}]}`, sorted by ID. A missing fresh root returns an empty list without creating files. |
| `POST /api/projects` | Multipart create; HTTP 201 with project detail and a `Location` header. Existing IDs are never overwritten. |
| `GET /api/projects/<id>` | `{"project_id":"trip","canvas":{"width":1600,"height":900},"photos":[{"photo_id":1,"width":200,"height":100}, ...]}`. Dimensions are EXIF-oriented. |
| `GET /api/projects/<id>/photos/<number>` | Original imported JPEG/PNG bytes, `no-store` and `nosniff`. No caller-supplied paths. |

POST contains one text field `metadata`, UTF-8 JSON with exactly
`{"project_id":"trip","canvas":{"width":1600,"height":900}}`, at most 16 KiB.
Supply unique file fields `photo_1` through `photo_N`, with 2-6 contiguous
numbers. Field numbers determine selection order, not multipart ordering.
JPEG/PNG files must be single-frame, at most **25 MiB each** and
**40,000,000 decoded pixels**. Actual bytes/decoding are authoritative, not
filenames or MIME headers. Canvas axes are integer **1-4096 pixels**.
Duplicate JSON/form fields, unexpected fields and coerced values are rejected.

The launcher and adapter bound the total request to **160 MiB**, enough for six
25 MiB files and multipart overhead. Installed Functions hosts can reject a
body above their cap **before Python runs**, with an empty HTTP 500 or connection
abort rather than a reliable 413. The UI handles non-JSON/network failures
honestly and offers lookup; it does not automatically retry creation.
Application-handled size failures return 413.

Requests must use the configured local Host. POST also rejects foreign/`null`
browser Origins; origin-less local tools are permitted. These restrictions and
CORS are not authentication. Application failures use
`{"error":{"code":"...","message":"..."}}`: 400 invalid input, 403 forbidden
Host/Origin, 404 missing project/photo, 409 duplicate/busy/invalid saved state,
413 size, 415 media, 500 unexpected storage/server failure.
Unexpected errors are logged without exposing local paths in responses.

Creation stages photos and the normal empty conversation privately, publishing
the project directory last. Canvas dimensions live only in existing conversation
controls. An OS-held per-project lock rejects competing local creates.
Handled failures clean up owned staging/assets; a killed worker can leave
private staging/unreferenced assets, not a half-published project. There is no
garbage collector or protection against arbitrary CLI writes to this root.
GETs validate existing records without repair or initialization.

### Manual test-project cleanup

Stop the backend before deleting an entire selected
`users\local-dev\projects\<project-id>` directory under the configured data root.
This removes its project record, conversation and any saved layouts/renders;
the project disappears from the list after refresh, and its ID can be reused.
Imported photo copies remain separately under `users\local-dev\uploads`.
Leave those copies alone unless their references have been checked; deleting a
project directory is not complete disk cleanup. Original source photos are
untouched. No deletion UI/API or garbage collector is provided.

## Offline tests

All Python tests live under the checkout's `tests` directory. From the
repository root, select the environment and suite explicitly:

```powershell
# Core/application tests: existing Python environment, no Functions SDK required.
.\.venv\Scripts\python.exe -m pytest -q

# HTTP adapters and Functions launcher: API environment with the Functions SDK.
.\api\.venv\Scripts\python.exe -m pytest -q -c .\api\pytest.ini .\tests\api
```

Tests use generated photos/temp roots and block unmocked external services.
They cover multipart validation, original bytes/orientation, read-only reopening,
failure rollback, limits and cross-process guards. Launcher tests use fake Core
Tools in installed Windows PowerShell/PowerShell 7 hosts. The default root
configuration includes `tests\application` but excludes `tests\api`; the API
command selects `tests\api` explicitly. Both environments import the same checkout
source; moving tests does not require changing either environment.

Future deployment must package the entry point, host config, requirements and
shared `ai_collage` source, with target-platform dependencies, not Windows
venvs or reliance on this PowerShell import-path convenience. Deployment,
private Blob persistence and authentication remain separately scoped.

## Runtime storage-probe warning

The host can report `Unable to create client for AzureWebJobsStorage` while
storage is intentionally absent; see
[Azure/azure-functions-host#11636](https://github.com/Azure/azure-functions-host/issues/11636).
Working HTTP routes do not certify every internal health probe. Do not add a
storage account/emulator or disable health monitoring to silence this warning.
