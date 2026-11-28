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
| `ai_collage\agent` | Conversation state, photo-reference memory, interpretation, proposals, local editing-source selection and acceptance; optional, bounded model requests. Uses the engine to validate and render, rather than generating replacement images. | [Conversation](ai_collage/agent/conversation.py), [requests](ai_collage/agent/requests.py), [provider](ai_collage/agent/provider.py) |
| `ai_collage\application` | User-operation orchestration across engine and agent capabilities. Coordinates projects, durable split-stage/selection operations, read-only transcript/preview projection and backend-owned request claims. | [ProjectFlow](ai_collage/application/projects.py), [ConversationFlow](ai_collage/application/conversation.py) |
| `ai_collage\storage` | Typed project/conversation persistence, logical record identities, proposal packages and backend-owned mutation guards. Local retains existing paths; Blob publishes immutable records through a leased head. Azure SDK imports stay in the Blob module. | [Contracts](ai_collage/storage/contracts.py), [LocalProjectStorage](ai_collage/storage/local.py), [BlobProjectStorage](ai_collage/storage/blob.py) |
| `ai_collage\cli` | Command parsing and terminal presentation for engine, conversation and evaluation operations. | [Main CLI](ai_collage/cli/main.py), [chat](ai_collage/cli/chat.py) |
| `ai_collage\evaluation` | Scripted conversation replay and offline assessment of saved evidence; tooling, not part of an ordinary web request. Live replay requires separate authorization. | [Replay](ai_collage/evaluation/replay.py), [assessment](ai_collage/evaluation/assess.py) |
| `api` | Thin Azure Functions HTTP adapter and local host configuration/launcher. Selects Local/default or API-only development Blob storage and translates application results/errors into HTTP responses. | [Functions](api/function_app.py), [storage selection](api/storage_config.py), [launcher](api/start.ps1) |
| `web` | React/TypeScript UI, temporary selection previews and API client for real saved projects, not another renderer or language interpreter. | [App](web/src/App.tsx), [API client](web/src/api.ts), [workspace](web/src/RealWorkspace.tsx) |

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
application (ProjectFlow / ConversationFlow)
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
HTTP operation storage and concurrency belong to `ConversationFlow`, not the
agent handoff or a client-supplied intent.

The default Local-mode web path supports create/save/list/reopen, photo serving, conversation,
backend-rendered proposals, historical thumbnail/modal viewing, explicit local
source selection and stored full-resolution PNG downloads. One Send interprets,
then generates if needed through separate HTTP requests. Questions, naming and
exact returns use the same agent behavior as CLI/replay. **Current collage**
is the saved editing baseline; viewing/downloading an older result does not
change it. Web acceptance/finalization is deliberately absent; existing
CLI/replay acceptance is unchanged.
The initial scripted prototype has been retired. Project pages load only
real backend state; unknown routes use the ordinary not-found page.

## A web create request, end to end

1. `web\src\api.ts` sends selected files and project/canvas metadata as a
   multipart HTTP request.
2. `api\function_app.py` checks the HTTP envelope, local Host/Origin and request
   limits, parses metadata/file fields, then calls `ProjectFlow.create`.
3. `ai_collage\application\projects.py` locks the project ID, checks existence
   through `ProjectStorage` and stages uploaded streams in private temporary
   storage. It calls the existing
   `ProjectStore.create` to import photos and create normal project records.
4. It constructs the existing `Conversation` to initialize normal conversation
   state, including canvas controls. This does not make a model request.
5. It passes the prepared project/state models and open original-photo streams
   to the selected `ProjectStorage.publish`. The local implementation stages the
   ordinary records and bounded photo copies on the destination filesystem,
   links assets without replacement and publishes the completed project
   directory last, with rollback for handled pre-publication failures.
   The Functions adapter returns HTTP 201; the UI navigates only after confirmed
   success.

Private preparation followed by storage-owned publication makes project
creation and initial conversation setup one published operation. It does not
replace the engine's photo importer, project models or storage format. There
are no CLI subprocesses, copied backend sources or second web-only
project/conversation implementations.

Reopening uses `ProjectStorage.load` for strict record reads and asset-presence
checks; `ProjectFlow` validates project/conversation/photo identity and canvas
without initializing or repairing saved state. Listing and photo delivery also
use the boundary. Photo responses serve imported original bytes; the local
implementation reuses engine image validation.

`ProjectStorage` uses logical project/photo IDs, existing record models and
streams, not durable directory traversal. `ProjectFlow` accepts an injected
implementation and defaults to `LocalProjectStorage` over the configured
`ProjectStore`. The existing local OS-held guard still covers existence checks,
preparation and publication; it is not a distributed lock. Temporary preparation
can be on another volume because publication copies streams into destination-local
staging before linking.

`ConversationStorage` extends this boundary to state/events, attempts, proposals/
PNGs and web operations/selections. `Conversation`, `RequestLog` and
`ConversationFlow` share one request-scoped session, using logical record IDs
rather than arbitrary paths. Local preserves existing files and acceptance;
Blob never reads local conversation records. The engine does not import storage
or acquire agent/application dependencies.

The API's request-scoped storage factory defaults to Local and imports no Azure
storage implementation or credentials on that path. Explicit Blob mode uses
the same preparation and `ProjectStorage` contract with `BlobProjectStorage`,
subscription-scoped `AzureCliCredential` and the fixed development container.
SDK retries are disabled, with finite token/connection/read timeouts.
CLI/replay do not use this API-side selection.

The local launcher keeps Local as its default. Explicit `-StorageBackend Blob`
supplies the recorded development target and stable `web-dev` namespace;
`-BlobNamespace` selects an alternate workspace instead of inheriting a prior
trial's namespace. Conflicting target environment settings are rejected.
These values are process-local and restored on exit; the launcher performs no
account discovery, sign-in or model preflight. Direct workers still require
explicit Blob environment configuration.

Opt-in local diagnostics belong to the API adapter, not the engine or
persistence contracts. `request_metrics.py` uses request-local context across
the async worker handoff and appends safe route/status/size/timing records to
the launcher-selected JSONL file. `blob_metrics.py` decorates the existing
transport (including any proof guard) and times complete metadata/list/read
operations without changing retries, validation or storage behavior. Nested
reads are not double-counted; transport attempts are not billing/budget counts.
The browser Network panel supplies the separate host/transfer cross-check.
Metrics are disabled normally and never send telemetry.

Blob publication initially uploads original photos and normal project/state
records under a unique candidate attempt, then conditionally creates one strict
**version-3 storage head** under `published`. The head references immutable
project/photos, state/events, attempts, operations/selections and proposal/PNG/thumbnail
packages with digests and byte sizes. Keys derive from logical identities inside
the selected owner/project namespace. Older head versions are rejected; old evidence stays
untouched. Proposal records use version 9; other conversation records remain version 8,
and project/layout format 3 is unchanged.

Each conversation mutation acquires a finite 60s lease on that head, with a
bounded renewal helper while the request owns it. Every head update carries
both lease ID and expected ETag. Claims and attempt reservations are published
before dispatch, not deferred until request end. Event/state, proposal/PNG/event/
baseline and completed selection/abandonment checkpoints advance atomically.
Unchanged originals and committed historical objects are retained.

Readers bind one head and validate only its immutable references. Canonical
browser revisions still exclude internal lease/ETag/attempt diagnostics.
Validated bytes are reused in a request-local cache capped at 128 MiB; no
persistent local cache is authoritative. Rendering uses owned temporary photo
paths and the unchanged renderer, then removes scratch files.
The API's storage factory also bounds read-snapshot reuse to one request.
Listing, detail loading and photo delivery reuse the same per-project head/
session; project loading does not repeat the session's original-photo checks.
Mutations discard any cached reader for that project before and after their
fresh leased writer, and busy checks still read current lease status.
Downloads use a bounded initial GET rather than a preceding HEAD, obtaining size
and ETag from the same response. Subsequent SDK ranges stay pinned to that ETag.
Original-photo property and fresh ownership checks remain separate HEADs.
JSON/head IO is capped at 1 MiB, originals at 25 MiB, encoded previews at
128 MiB and thumbnails at 512 KiB; canvas axes remain at most 4096.

`storage.assets` provides shared bounded PNG validation, targeted commitment
checks and deterministic Pillow thumbnail generation. Every new proposal publishes
its full PNG, required thumbnail descriptor and stored thumbnail together. Thumbnails
preserve aspect ratio, have a maximum edge of 320 pixels and never upscale.
Conversation JSON validates logical history, recipes and asset references without
reading image bodies. Image routes bind only the head/state/target event/proposal
and requested asset; they do not reconstruct unrelated history or inspect originals.
Local proves commitment from state/event membership, not a proposal directory.
Asset delivery validates bytes, digest, format and dimensions; publication and
mutation/source/acceptance paths retain full preview verification.

Losing writers cannot publish or dispatch again; expired ownership does not
reset paid claims. An ambiguous head response preserves potentially referenced
candidates and reports `outcome_unknown`. Definite never-published candidates
are cleaned only with confirmed ETags; cleanup/release errors are logged.
Service failures report `storage_unavailable`, without Local fallback.
No online orphan collector, migration or automatic paid retry is provided.

All existing web routes use the selected backend; `-Live` still explicitly gates
model calls. The dedicated [proof entrypoint](api/proof_function_app.py) injects
only four scripted replies through normal handlers/accounting/rendering.
The ordinary launcher pins `function_app.py`, never that entrypoint.
The separately authorized [proof runner](api/verify_blob_storage.py) owns its
hosts, explicit cross-restart send caps and exact successful-upload inventory.
It is not an application budget service or evidence of user acceptance.

## A conversation request, end to end

1. The browser sends text, one UUID and its last known revision to Functions.
   The application takes the selected backend's per-project mutation guard and
   persists a claim before calling `Conversation.interpret()`.
2. Interpretation either produces a final question/acknowledgement/selection,
   or saves a strict server-owned handoff. The browser shows a deterministic
   action/source/photo-reference summary, not another model-generated summary.
3. Only the still-active initiating Send automatically POSTs generation. The
   application claims the saved handoff once, verifies its revision/source
   binding and invokes `Conversation.generate()` with captured limits.
4. The agent validates/renders/publishes the ordinary immutable proposal package,
   including its stored thumbnail.
   The application records its result reference, and read-only routes project
   the transcript/current baseline and serve verified preview or thumbnail bytes.

Web-only, version-1 records under `web-operations` preserve submission identity,
stage claims and result references. They are not another agent memory or a
replacement project/layout format. Reads use `Conversation(read_only=True)`:
they validate shared history, names and proposals but cannot initialize or
repair acceptance. Duplicate POSTs cannot repeat model calls; unrelated
mutations in different projects need not block.

The Functions conversation adapter runs each request in an executor thread,
with a request-local event loop for async agent stages. Synchronous rendering,
snapshot validation and filesystem work stay off the shared Functions event
loop so other HTTP requests can be serviced. These remain ordinary bounded
HTTP requests, not detached jobs. Project-list/detail reads do not take the
conversational mutation guard.

Reload observes an existing operation, never resubmits its prompt. Prepared
work requires explicit Continue generation. A running claim without its OS-held
guard (Local) or confirmed live lease (Blob) is uncertain. Neither loss nor age
permits replay. Publication/result-recording ambiguity
blocks new paid work for inspection. No queue, background worker, automatic
paid retry or general crash-repair UI is present.

The existing model budgets remain 120s/180s. HTTP work envelopes add rendering/
storage headroom with pre-publication checks; they do not forcibly cancel
synchronous I/O. Browser disconnection is not evidence that backend work stopped.
The [API guide](api/README.md#conversation-and-recovery) defines actual deadlines
and recovery behavior.

## A local editing-source selection

1. A historical thumbnail opens a temporary React modal using the existing
   verified proposal PNG. No mutation occurs.
2. **Edit from this collage** sends a UUID, exact proposal ID, current revision
   and pending-task confirmation to the selection route, without model input.
3. `ConversationFlow` acquires the same project mutation guard, rejects stale/
   busy/uncertain state, validates the target and persists a local action claim.
   Confirmed unclaimed preparation is retired as `abandoned` before selection;
   running or interrupted work is never made cancelable by age.
4. `Conversation.select_proposal()` appends a distinct version-1
   `local_selection` history record and updates the baseline/pending-task
   boundary. Task/navigation and naming-history reconstruction understand this
   local event. Existing Exchange/LocalEvent records and layout formats are
   unchanged; no fake model response or accepted snapshot is created.
5. The application verifies the canonical outcome and completes its action
   record. The transcript projects a chronologically ordered user activity.
   Only a consistent saved result closes the modal and updates Current collage.

The read snapshot binds canonical history, operation and local-action records
to one verified revision; transcript projection uses that same action set,
not a later reread that could mix newer activity with an older baseline.
Version-1 `web-selections` records reference canonical events rather than
duplicating semantic history. Duplicate UUIDs return the original outcome,
never reselect after later work. An uncompleted claim blocks further mutations;
lost responses are reconciled using reads, not redispatch or automatic repair.
Selection preserves learned names and later proposals/messages. A subsequent
ordinary edit still goes through the existing interpretation/generation stages.

Downloading fetches the verified saved proposal PNG through the existing
preview route and a temporary browser object URL, then releases that URL.
It does not regenerate, resize, accept or select. Both local actions work
without live model access. The [API guide](api/README.md#local-source-selection-and-png-download)
documents their DTOs and failure states.

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
web-specific settings file. Web conversation submissions and local selections
create their respective additive application records; ordinary CLI/replay
projects do not.

The root `.venv` and `api\.venv` are separate dependency environments, not
separate backends. The Functions worker uses the API environment, which adds
the Functions SDK and reuses the root agent requirements while importing the
same checkout source. React has its own
Node toolchain; it does not render collages.

Python tests share the root `tests` tree. For example,
[application tests](tests/application/test_project_flow.py) exercise workflows
directly, while [API tests](tests/api/test_project_routes.py) exercise the HTTP
adapter. [Storage tests](tests/storage) exercise the Local/Blob adapters; the
Blob tests use the API environment for its SDK, not an API-owned test directory.
The default root suite selects the Local storage tests without requiring Azure
packages. Frontend tests remain under `web\src`. Suite/environment commands live
in the [CLI guide](docs/cli-guide.md#verification) and [API README](api/README.md#offline-tests).

The current host and default storage are local development facilities. Anonymous
Functions routes and local-origin restrictions are not production
authentication. Opt-in Blob storage supports the complete existing web workflow.
Deployment packaging and authenticated cloud hosting remain future work;
see the [API](api/README.md) and
[UI](web/README.md) guides for current setup and limits.
