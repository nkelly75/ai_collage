# Local Python API

Loopback-only Azure Functions routes create, list and reopen local photo/canvas
projects and expose real conversation/previews. Thin HTTP adapters call the
project/conversation application workflows, coordinating the same engine and
agent used by CLI/replay. No source copies or CLI subprocesses are used.
**Local storage is the default** for the complete web workflow. Explicit
development Blob mode supports that same workflow, including conversations,
history, source selection and stored PNGs, while the API/UI still run locally.
Model access requires explicit `-Live`. In Local mode, creation, source
selection and reads never initialize credentials or make model calls.
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
root agent requirements (including engine and keyless model dependencies)
alongside the Functions SDK; the
root `.venv` is not used by the worker.

In a separate PowerShell terminal from Vite:

```powershell
.\api\start.ps1
# Explicitly enable potentially paid conversation stages instead:
.\api\start.ps1 -Live
```

The launcher selects `api\.venv`, adds the checkout to the process-local
`PYTHONPATH`, binds **127.0.0.1:7071**, and allows exactly
**http://127.0.0.1:5173** through CORS. It disables Core Tools telemetry,
keeps host secrets local and clears inherited storage/telemetry connections.
It never installs packages or changes global settings, and restores its
environment/cwd on exit, including failure. No activation,
`local.settings.json`, connection string, extension bundle or emulator is needed.
Stop with Ctrl+C; do not terminate unrelated processes occupying these ports.
Live requests use the same backend deployment and noninteractive
`DefaultAzureCredential` path as the CLI. Keep credentials in the backend's
existing environment/sign-in setup, never Vite/browser configuration. This
launcher does not sign in or make a model preflight.

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
413 size, 415 media, 422 confirmed model/validation failure, 503 live disabled,
504 confirmed stage timeout, 500 unexpected storage/server failure or uncertain
publication. The error code and saved operation matter, not HTTP status alone.
Unexpected errors are logged without exposing local paths in responses.

Local-mode creation stages photos and the normal empty conversation privately, publishing
the project directory last. Canvas dimensions live only in existing conversation
controls. An OS-held per-project lock rejects competing local creates and conversation
mutations across tabs/worker processes.
Project-list/detail reads do not acquire that mutation guard.
Handled failures clean up owned staging/assets; a killed worker can leave
private staging/unreferenced assets, not a half-published project. There is no
garbage collector or protection against arbitrary CLI writes to this root.
GETs validate existing records without repair or initialization.

## Conversation and recovery

| Route | Request / result |
|---|---|
| `GET /api/projects/<id>/conversation` | `{project_id, revision, live_enabled, messages, baseline, pending, operation, proposals, selection}`. Messages contain stable `id`, `role` (`user`, `assistant`, `activity`), `text`, `kind`, nullable `proposal_id`. Baseline is null or `{proposal_id}`. Pending is null or `{kind, message}` for a question/name confirmation. Operation is the latest unresolved operation, or null. Published proposals contain `{proposal_id,width,height}`; selection contains `{enabled,reason,confirmation,action}`. |
| `POST /api/projects/<id>/conversation/requests` | Strict JSON `{request_id, prompt, revision}`; canonical UUID, nonempty prompt at most 256 KiB UTF-8, current 64-hex revision. HTTP 201 for new operation, 200 for a recognized duplicate. Interpretation only. |
| `GET /api/projects/<id>/conversation/requests/<uuid>` | Read an existing operation, including completed/failed results. |
| `POST /api/projects/<id>/conversation/requests/<uuid>/generate` | Strict JSON `{revision}`. Claim the server-held prepared handoff once. HTTP 200; no browser intent/recipe/limit overrides. |
| `GET /api/projects/<id>/proposals/<proposal_id>/preview` | Verified immutable published PNG, `no-store`/`nosniff`. Does not regenerate or accept it. |
| `POST /api/projects/<id>/conversation/selections` | Strict JSON `{action_id,proposal_id,revision,abandon_pending}`. Canonical UUID and revision, exact published proposal ID and strict boolean. Model-free local source selection; 201/new or 200/recognized duplicate. |
| `GET /api/projects/<id>/conversation/selections/<uuid>` | Read the original local action's status/outcome, without selecting again or repairing state. |

JSON bodies are at most 1 MiB, with duplicate/unknown fields and coercions
rejected. Operation DTOs contain `request_id`, `status`, `summary`,
`result_kind`, `message`, `proposal_id`, nullable `{code,message}` `error`,
`can_continue` and current `revision`. Status is `interpreting`, `prepared`,
`generating`, `completed`, `failed`, `uncertain` or terminal `abandoned`. Result kinds match the
agent's proposal/selection/question/name_confirmation/acknowledgement.
Responses contain no handoffs, raw model JSON, reasoning, credentials or paths.

### Local source selection and PNG download

`baseline` is **Current collage**, not necessarily the newest proposal.
Source selection preserves all proposals, learned names, accepted versions
and later history. A separate canonical `local_selection` event records the
navigation/task boundary; the projected `activity` entry is not a fabricated
assistant response. It can be repeated to choose a different saved proposal.

Selection eligibility is authoritative: `enabled`/`reason` cover busy or
unresolved work, `confirmation` explains which pending task would end, and
`action` identifies unresolved selection work when present. Selecting while
a question, name receipt or valid unclaimed preparation is pending requires
`abandon_pending: true` bound to the shown revision. A changed revision requires
a fresh read/confirmation. Unconfirmed proposed names are not applied;
already learned names and consumed attempts remain saved.

The same OS-held project guard serializes selection against stage claims.
Only prepared work that has never been claimed can be retired. Its original
operation becomes `abandoned`, with `can_continue: false`; an old generation
POST returns that terminal outcome without dispatch. Running/interrupted/
uncertain work cannot be canceled this way. `confirmation_required`,
`already_current`, `action_id_conflict` and `selection_unresolved` are explicit
409 errors, alongside existing stale/busy/operation errors.

Selection responses contain `{action_id,proposal_id,status,revision,message}`.
Status is `completed`, `saving` (claimed with a guard held), or `uncertain`
(uncompleted claim without that guard). Uncompleted reads may have a null
revision. A completed action identifies the source it selected at that point,
not an assertion that it is still current. Identical duplicates never append
activity or reselect, even after later changes.

Additive version-1 records under `web-selections` bind each action to its
canonical event and any retired preparation. Persisted claims block competing
mutations after partial publication; there is no age-based retry or repair.
The browser reconciles a lost response with the original action GET and a
consistent conversation read, not another POST. Invalid saved state fails
explicitly rather than repairing it. Local selection does not require `-Live`
or initialize a provider.

Download uses the existing preview GET. The browser downloads its exact PNG
bytes at the stored proposal dimensions with a safe project/proposal filename.
No acceptance, thumbnail substitution, resizing or new render is involved.

One Send automatically chains the two stage requests when generation is needed.
After refresh, **Continue generation** is required for prepared work. A lost
response must be followed by a GET, not a resubmitted prompt. A repeated UUID
with changed submission returns `request_id_conflict`; competing mutation
returns `project_busy`; unresolved prior work returns `operation_unresolved`;
stale revision/source returns `stale_revision`/`stale_preparation` (all 409).
`live_disabled` is 503, and a configured trial's other projects return
`trial_project_only` (403).

Model-stage limits remain **120s interpretation / 180s generation**, sharing
correction budgets exactly as CLI/replay. HTTP work envelopes target
**150s / 210s**, with checks before model work and before publication, including
after rendering. The browser waits **160s / 220s**, including body parsing;
ordinary reads wait 10s and creation 60s. The app-wide Functions execution
ceiling is 225s, not an increase to a model budget. The hosted 230s HTTP
load-balancer limit is not a local Core Tools limit.

These are not guarantees of forcible synchronous-render/storage cancellation.
Browser timeout/disconnection and a killed worker can leave an unknown outcome.
Read the saved result/preview. Confirmed terminal failures (`stage_failed` or
`stage_timeout`) do not auto-retry; a new explicit Send is a new potentially
paid attempt and must use existing agent recovery semantics. Names saved during
interpretation are not rolled back.
Exhausted generation-validation attempts report that no valid layout was
created within the attempt limit and the previous preview is unchanged.
The UI automatically refreshes confirmed failure state using read-only GETs;
this is not another stage attempt. If those reads fail, manual status checking
remains available without describing the known failure as an unknown outcome.

An interrupted claim or uncertain publication (`outcome_unknown`) blocks a new
paid mutation for manual evidence inspection. A claim is never made retryable
just because it is old or its process/lock disappeared. Completed agent writes
with an unrecorded application result may still show their verified current
preview while reporting uncertainty. No automatic repair, queue or retry worker
is present. Browser status observation is bounded to 225s per session, at most
one GET every 2s, then manual **Check status**.

Conversation/operation/selection/preview handlers execute in request-scoped executor
threads, not on the Functions worker's shared event loop. Each stage runs its
async model call in that thread's event loop; synchronous validation, rendering
and storage therefore do not block the shared loop servicing other requests.
This is not a detached job or queue. Project guards, stage limits and uncertain
outcome handling are unchanged; disconnecting a browser does not stop a worker
thread or roll back its work.

### Bounded single-project trials

For a separately authorized trial, configure the same absolute ledger and
project on every host restart, alongside an isolated `AI_COLLAGE_DATA_DIR`:

```powershell
.\api\start.ps1 -Live -TrialProject trial-project -CallBudgetPath C:\absolute\trial\calls.json -MaxCalls 12
```

The launcher sets process-local `AI_COLLAGE_LIVE`, `AI_COLLAGE_TRIAL_PROJECT`,
`AI_COLLAGE_CALL_BUDGET_PATH` and `AI_COLLAGE_MAX_CALLS`, clearing inherited trial
settings for an ordinary launch and restoring them on exit. The application
requires all three budget settings together and restricts live mutations to
that project. The existing `call_budget` guard reserves actual attempts in
`RequestLog.reserve`, across stages/process restarts. Limits cannot be renewed
by reopening. Keep trials single-writer and do not share their ledger with
another host/store. This example does not authorize any trial or extra calls.

### Manual Local test-project cleanup

Stop the backend before deleting an entire selected
`users\local-dev\projects\<project-id>` directory under the configured data root.
This removes its project record, conversation and any saved layouts/renders;
the project disappears from the list after refresh, and its ID can be reused.
Imported photo copies remain separately under `users\local-dev\uploads`.
Leave those copies alone unless their references have been checked; deleting a
project directory is not complete disk cleanup. Original source photos are
untouched. No deletion UI/API or garbage collector is provided.

<a id="api-only-development-blob-mode"></a>

## Development Blob mode

All existing project/conversation/request/status/generation/selection/preview
routes use authoritative Blob persistence. The existing web UI needs no separate
storage setting. CLI/replay and ordinary `.\api\start.ps1` launches remain Local.
Use a fresh namespace; there is no import or migration of prior local projects.
019c is complete after offline verification, its separately approved real-account
proof and explicit user acceptance; see [results](../planning/019c_results.md).

Use the existing development target from the
[infrastructure record](../planning/019b-initial-blob-integration.md), with
the already authorized Azure CLI identity. The launcher never signs in, creates
resources or changes CLI defaults. Set backend-only variables before launch:

```powershell
$env:AI_COLLAGE_BLOB_ACCOUNT_URL = '<development Blob endpoint from the infrastructure record>'
$env:AI_COLLAGE_BLOB_CONTAINER = 'collage'
$env:AI_COLLAGE_BLOB_SUBSCRIPTION_ID = '<development subscription from the infrastructure record>'
$env:AI_COLLAGE_BLOB_NAMESPACE = 'web-019c-' + [guid]::NewGuid().ToString('N')
$env:AI_COLLAGE_DATA_DIR = Join-Path $env:TEMP ('collage-019c-' + [guid]::NewGuid().ToString('N'))
.\api\start.ps1 -StorageBackend Blob
# For an explicitly authorized model-backed trial:
# .\api\start.ps1 -StorageBackend Blob -Live
```

The endpoint, container and subscription must match that development target.
Namespaces are 1-64 lowercase alphanumeric/hyphen characters, starting and
ending with an alphanumeric character. Missing/invalid settings fail explicitly;
there is no Local fallback. Direct workers select
`AI_COLLAGE_STORAGE_BACKEND=Blob`; missing means Local, blank/unknown fails.
Local launches clear inherited Blob configuration only in the worker and restore
the caller's environment on exit. Blob accepts the existing explicit `-Live`
and optional trial flags. Without `-Live`, model dispatch stays disabled, but
Blob reads/writes still access Azure. Model authentication remains separate
from storage authentication. Keep a trial's same external budget ledger and
single-writer restriction across restarts; a different root never renews calls.
`AI_COLLAGE_DATA_DIR` is not the authority for saved Blob projects. Import,
decoding and rendering use owned temporary files, not a durable local project copy.

Authentication uses subscription-scoped `AzureCliCredential` only: no credential
chain, account key, SAS or browser credential. CLI-token process timeout is 10s;
Blob connection/read timeouts are 10s/30s. SDK retries are disabled. This does
not guarantee cancellation of a timed-out in-flight upload.
Application Blob configuration never supplies Functions host storage.

One strict **version-2 storage head** references immutable project/photos,
conversation state/events, attempts, operations/selections and proposals/PNGs.
Initial create is conditional; mutations hold a finite renewable 60s lease on
the head and publish with lease ID plus expected ETag. Claims/reservations
precede dispatch. Event/state, complete proposals and selection/abandonment
advance through coherent checkpoints. Different projects have independent
guards; competing writers receive 409. Lease expiry never authorizes paid replay.

Reads bind one committed head, validate digests/identities and never initialize
or repair. Historical committed objects remain so an older reader can finish.
Canonical browser revisions do not include lease renewals or attempt diagnostics.
Validated bytes are cached only within a request, up to 128 MiB.
JSON records and the head are capped at 1 MiB, originals at 25 MiB each, and
encoded PNG previews at 128 MiB. Canvas axes remain at most 4096.
Version-1 Blob envelopes are rejected; use a fresh 019c namespace and preserve
019b evidence. Project/layout format 3 and conversation record version 8 are unchanged.

Known service/authentication/permission/container failures return
`storage_unavailable`/503, not an empty list or a project 404. Invalid published
state returns 409. An ambiguous head write returns `outcome_unknown`/500
and preserves its candidate objects and prior durable claims. Inspect project,
request or selection status with GET, never automatic POST retry.
An interpreting/generating claim without live ownership is uncertain and blocks
new paid work; not-found while a create might still run is not proof of rollback.
Definite pre-publication failures clean only confirmed-owned objects using their
ETags. Cleanup failures are logged without masking the original failure.
There is no general Blob deletion API or orphan collector.

### Separately approved real-account proof

Ordinary pytest never runs this proof. After **separate explicit live approval**,
from the repository root, choose a new absolute evidence directory whose parent
already exists. Set `$approvedHttpCap` and `$approvedBlobCap` to the separately
agreed integer ceilings first; there are deliberately no default live allowances:

```powershell
.\api\.venv\Scripts\python.exe -m api.verify_blob_storage --allow-azure --output-dir C:\absolute\new-proof-directory `
  --max-http-requests $approvedHttpCap --max-blob-requests $approvedBlobCap
```

Use the module invocation, not the script path. This starts its own loopback
Functions hosts and verifies listener ownership. A dedicated entrypoint uses
four tiny generated 3:4 PNGs (at most 1 MiB together) and exactly four scripted
interpretation/generation replies for P001/P002. The small recipe subset comes
from archived `project-02`; its originals and persisted records are not uploaded
or changed. Normal handlers, validation, attempt reservation and renderer still
run. No Foundry/model credentials or model HTTP calls occur; scripted usage
remains unknown rather than fabricated billing.

The journey checks create/list/detail/originals/duplicate 409, two proposals,
history/Current collage selection and full PNG downloads. After an owned host
restart with another empty root, it compares the entire conversation, request/
action statuses, previews and original bytes again. Ordinary launches pin
`function_app.py`, not the proof entrypoint; no production fake-provider flag exists.

The fresh `proof-019c-<uuid>` namespace contains only project `proof`.
`requests.jsonl` counts every Blob send across hosts, lease calls and cleanup;
its `.limits.json` sidecar binds explicit caps to that namespace.
The transport rejects other accounts, namespaces, project keys and container
deletion before sending. Successful PUTs record key/ETag ownership in
`.objects.jsonl`, including replaced head references and retained historical
objects. Report, generated downloads/previews, ledgers and host logs stay in
the evidence directory. Ordinary operation does not use these proof ledgers.

On success, cleanup first validates an exact run-owned inventory, then deletes
the completion document before its referenced objects using captured ETags.
On uncertainty/failure, preserve the namespace and evidence; an incomplete
inventory is **not** evidence that no objects exist. Do not clear the container,
guess at cleanup or rerun without renewed approval.

### User-led web acceptance

019b is closed with its duplicate manual API test waived; see its
[historical closeout](../planning/019b_results.md#user-acceptance-and-closeout).
Its consumed allowance is not authorization for this new proof or a web trial.

019c is accepted and closed following successful user-led testing; see
[closeout](../planning/019c_results.md#user-led-web-acceptance-and-closeout).
The acceptance procedure was to exercise the actual local API/Vite UI with
Blob and explicitly authorized live models, in a separate fresh namespace:
empty Projects, upload/create, a short conversation, history/Current collage
selection and PNG download. Refresh, then restart with another empty local root,
keeping the same Blob namespace and any single-writer trial budget ledger.
Restore photos/messages/names/current source/history/previews and continue a
normal conversation step. Do not copy old local projects or regenerate previews
on reopen. Any future trial still needs agreed procedure/model limits; completed
acceptance does not authorize further service calls.

## Offline tests

All Python tests live under the checkout's `tests` directory. From the
repository root, select the environment and suite explicitly:

```powershell
# Core/application tests: existing Python environment, no Functions SDK required.
.\.venv\Scripts\python.exe -m pytest -q

# HTTP adapters, launcher and Blob adapter: API environment with both SDKs.
.\api\.venv\Scripts\python.exe -m pytest -q -c .\api\pytest.ini .\tests\api .\tests\storage\test_blob.py
```

Tests use generated photos/temp roots and block unmocked external services.
They cover multipart/JSON validation, original bytes/orientation, read-only
reopening, split stages, durable claims, failure windows, limits and
cross-process guards. Blob tests use SDK-boundary mocks, the full scripted
HTTP journey and real-SDK create/lease/ETag serialization checks with HTTP
transport replaced; no Azure account or emulator.
Proof lifecycle tests use only disposable owned loopback listeners/processes.
Launcher tests use fake Core
Tools in installed Windows PowerShell/PowerShell 7 hosts. The default root
configuration includes `tests\application` and `tests\storage\test_local.py`,
but excludes `tests\api` and SDK-dependent `tests\storage\test_blob.py`.
From the repository root, the API command must select both API and Blob adapter
tests explicitly. The API pytest configuration supplies both defaults only
when pytest is invoked from the `api` directory; do not omit the explicit paths
from the repository-root command.
Test ownership follows the source responsibility, not its execution environment.
Both environments import the same checkout source; no dependency changes are
needed for this organization.

Future deployment must package the entry point, host config, requirements and
shared `ai_collage` source, with target-platform dependencies, not Windows
venvs or reliance on this PowerShell import-path convenience. Deployment and authentication remain separately scoped; completed web Blob
persistence has completed its separately approved live proof and user acceptance;
see [019c results](../planning/019c_results.md).

## Runtime storage-probe warning

The host can report `Unable to create client for AzureWebJobsStorage` while
storage is intentionally absent; see
[Azure/azure-functions-host#11636](https://github.com/Azure/azure-functions-host/issues/11636).
Working HTTP routes do not certify every internal health probe. Do not add a
storage account/emulator or disable health monitoring to silence this warning.
