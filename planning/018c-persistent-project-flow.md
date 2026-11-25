# 018c: Persistent project flow

**Status:** Successfully completed and closed with the user's manual testing
and explicit sign-off. See [018c results and runtime limits](018c_results.md).
Later increments remain unapproved.
See the [018 tracker](018-local-conversation-and-preview.md) for sequencing.

## Outcome and agreed scope

Deliver one usable local flow: choose photos and a canvas, **Create project**,
see the saved project in **Projects**, and reopen it by URL after browser
refresh or a backend restart. Python-managed files, not browser memory or a
running worker, are authoritative.

- Keep the user-entered project ID, used in the list and project URL. Reuse
  the existing validation, including Windows reserved-name rejection.
  Duplicate IDs fail without overwriting anything.
- Keep 2-6 JPEG/PNG photos, up to 25 MiB each, in selection order. Their
  stable numbers are identifiers, not stacking positions or inferred names.
- Keep the seven canvas presets and custom integer dimensions of 1-4096
  pixels per side. Save the actual dimensions, not a second preset identity.
- Selection and setup changes are unsaved until **Create project**. This is
  the interaction design, not a restriction to browser-only persistence.
- After creation, show the saved ID, numbered proportional photos and canvas
  dimensions. State plainly that conversation and collage generation are not
  connected yet. Do not generate an initial layout or fabricated history.
- No editing of photos/canvas after creation, project deletion/renaming,
  shared photo-library workflow, history/proposal actions or model calls.
- Use a separate local data root for new web projects. Existing CLI projects
  and archives are outside this increment.
- Keep the London script as a clearly labelled, separate demo that works
  without the backend. Its state and images never stand in for saved projects.

## UI behavior

| Surface | Required behavior |
|---|---|
| Projects (`/`) | Load saved project summaries from Python, sorted by ID. Show loading, genuinely empty, and failed states distinctly, with a manual retry. Keep a separate Demo entry available even when the API fails. |
| New project (`/new`) | Retain current validation and local photo previews. **Create project** sends the selected files/settings; show saving and prevent duplicate submissions or changes to that submission while pending. |
| Successful creation | Navigate to `/projects/<id>` only after confirmed persistence. Replace temporary object URLs with backend photo URLs and release local previews when no longer needed. |
| Saved project (`/projects/<id>`) | Load from the backend on direct visits and refresh, independently of the project-list cache. Show photos/settings, explicit loading/error/not-found states, and no active generation, acceptance or download controls. |
| Demo (`/demo`) | Keep the current scripted walkthrough and bundled assets, clearly marked as simulated and separate from saved projects. Move it out of the real-project URL namespace; `sample-london` remains a valid real project ID. No compatibility alias is required for its prototype URL. |

Preserve selected files, ID and dimensions after a failed create while the
setup screen remains mounted. Leaving setup or refreshing may discard an
unsaved selection; do not add draft autosave or browser storage.

Use bounded direct API requests: 10 seconds for JSON reads and 60 seconds
for creation, including response-body handling. No automatic POST retries,
polling or mock/offline success. A timeout, navigation abort or lost response
does **not** prove that the backend rolled back. Explain that the project may
have been saved and offer an explicit lookup of that ID before another create.
A duplicate response must likewise let the user open the existing project,
not overwrite it or manufacture another ID.

Ignore stale responses after navigation/unmount; release timers, requests and
object URLs. Report image-load failures visibly rather than hiding a missing
photo. Preserve the existing responsive layout and keyboard/accessibility
behavior; no broader redesign is needed.

Replace browser-draft/prototype-reset wording with truthful saved-project
wording. Scope any reset control to **Reset demo**; it must never delete saved
projects. Remove **Check backend**, its diagnostic-only component/tests and
`/api/health`: real project requests now supply connectivity/error feedback.
Retain relevant request-validation/timeout coverage for the real API.

## Backend and persistence decisions

### One isolated local store

Default to `.collage-data-web` under the checkout root, independent of the
calling terminal's working directory. Allow an absolute
`AI_COLLAGE_DATA_DIR` override for isolated fixtures/local operation; reject
blank or invalid overrides explicitly. Add the default root to `.gitignore`.
Do not discover, merge, migrate or fall back to other `.collage-data*` roots.
Use the existing fixed `local-dev` owner; this is not authentication.

Reuse `ProjectStore`, image decoding, strict models and contained asset paths.
Do not expose a shared library merely because the existing store internally
places UUID assets beneath the owner's `uploads` directory.

### Canvas: reuse existing conversation state

The current engine `Project` has no canvas field; the existing
`ConversationState.controls` already persists width/height.
Create a normal format-3 project and initialize its **empty, model-free
conversation state** with the chosen dimensions and existing default
preferences. No prompt, proposal, request log or model client is needed.
This is internal initialization, not a working chat feature.

Keep that state as the sole saved canvas source; do not add a competing web
settings file, duplicate canvas field, new layout/project format, migration
or compatibility path. Existing formats and CLI/replay behavior stay unchanged.
An offline `Conversation` resume of a newly created fixture must recover the
same dimensions and empty history.

### Publication and local concurrency

Keep HTTP handlers thin, composing ordinary Python application logic in a
small module. Reuse/extract the smallest existing creation/publication helpers
needed rather than duplicate image validation or build a new storage framework.
The starting points are [engine projects](../ai_collage/engine/projects.py),
[conversation initialization](../ai_collage/agent/conversation.py) and
[conversation models](../ai_collage/agent/models.py).

- Stage imports and empty conversation initialization privately on the same
  filesystem as the destination. Publish the project directory **last**, only
  when its metadata, photos and canvas state are complete. Do not expose a
  `ProjectStore.create` result first and initialize its canvas afterward.
- Handled pre-publication failures clean up only that operation's staged files
  and newly imported UUID assets. Preserve existing projects/assets byte for
  byte. Original source photos are copied, never modified or relocated.
- Use a non-waiting, OS-held local per-project mutation guard, covering the
  existence check through publication/rollback. It must work across local
  worker processes and release on process exit; an in-memory flag or permanent
  lock-directory marker alone is insufficient. A busy/duplicate create fails
  explicitly. Different project IDs need not block one another.
- A process kill may leave private staging/unreferenced assets, but must not
  expose a half-initialized project. Record that limitation; no general garbage
  collector, crash journal or archive-cleanup command is required.
- Reads must not initialize missing state, invoke recovery that writes files,
  or silently repair incompatible/corrupt records. Validate the existing
  project and conversation record versions, project/photo identity and canvas.
  Reuse strict read helpers/models without constructing a recovery-writing
  `Conversation` inside a GET handler.

A missing fresh root is an empty collection, not an instruction to create files
on GET. Ignore private staging/lock entries, but surface an invalid published
project explicitly rather than quietly omitting it or returning an empty list.
This guard protects cooperating local API creates only, not shared-host/Blob
operation or arbitrary concurrent CLI writes to this root.

## Initial HTTP contract

Use the existing Python v2 Functions app, anonymous **loopback-only** routes,
direct browser requests and `VITE_API_BASE_URL`. Keep exact-origin CORS,
initially `http://127.0.0.1:5173`, with no Vite proxy, wildcard CORS, credentials
or redirects. API addresses are public configuration, never secrets.

Restrict the request Host to the configured loopback API authority. For POST,
also reject foreign or `null` browser Origins before writing anything; share
the allowed UI origin with the host's CORS configuration. Origin-less local
command-line requests may be accepted. CORS alone does not prevent an unwanted
cross-origin write and is not authentication.

| Route | Request / successful response |
|---|---|
| `GET /api/projects` | `200 {"projects": [summary, ...]}`. A summary contains `project_id`, `canvas: {width, height}` and `photo_count`. |
| `POST /api/projects` | Multipart body described below; `201` with the saved project detail and a `Location` header for its API detail URL. |
| `GET /api/projects/<id>` | `200` detail containing `project_id`, `canvas: {width, height}` and ordered `photos: [{photo_id, width, height}, ...]`. Photo dimensions are EXIF-oriented metadata from the existing importer. |
| `GET /api/projects/<id>/photos/<photo_id>` | Original imported JPEG/PNG bytes with the correct image content type. Resolve the number through that project's validated asset mapping, never a caller-supplied filename/path. |

The frontend derives photo endpoint URLs using its configured API base and
the returned validated IDs. Do not return filesystem paths, owner upload
directories, raw conversation internals or client-supplied URLs.
Use `Cache-Control: no-store` for this local slice and
`X-Content-Type-Options: nosniff` for image responses.
Do not introduce thumbnails/another renderer.

### Upload shape and bounds

Send one multipart request containing:

- One text field `metadata`, UTF-8 JSON with exactly
  `{"project_id": "...", "canvas": {"width": 1200, "height": 1800}}`.
  Bound it to 16 KiB; reject duplicate JSON keys, unexpected fields, coerced
  numbers/booleans and invalid dimensions/IDs.
- File fields named `photo_1` through `photo_N`, with contiguous numbers and
  `N` from 2 to 6. These names define selection order independently of multipart
  part ordering. Reject duplicate/missing/unknown file or text fields.

Use the SDK's multipart support, retaining access to duplicate-field values
for validation. Check the actual body length before form parsing, not only
`Content-Length`. Bound the entire request to **160 MiB (167772160 bytes)**,
including multipart overhead; six permitted 25 MiB photos total 150 MiB.
Apply the same host request-body setting in the process-local launcher and
restore it on exit. Verify the installed host really accepts the maximum
supported combination; do not silently lower the agreed per-photo/count limits.
The [Functions setting reference](https://learn.microsoft.com/en-us/azure/azure-functions/functions-app-settings#functions_request_body_size_limit)
documents the host-level control; documentation alone is not a runtime check.

Enforce each file's actual bytes and the existing 40,000,000 decoded-pixel
limit; reject corrupt, unsupported or multiframe images with existing decoding
logic. Treat uploaded MIME types, filenames and browser checks as untrusted.
Persist bytes unchanged through server-assigned asset paths. Filenames, if
retained as provenance, are not storage paths, photo titles or identities.
Remove upload scratch files on completion/failure.

### Explicit failures

Application errors use `{"error": {"code": "...", "message": "..."}}` with
stable codes and a useful sanitized message. Distinguish invalid requests
(`400`), disallowed Host/Origin (`403`), missing project/photo (`404`),
duplicate/busy/invalid saved state
(`409`, with distinct codes), size limits (`413`), unsupported media (`415`)
and unexpected storage/server errors (`500`). Log unexpected errors on the
backend without returning stack traces/absolute paths or logging photo bytes.

Host-generated errors, including a host-level `413`, may not be JSON. The UI
must handle those and malformed responses honestly. A filesystem permission or
read failure is not an empty project list, and API failure never selects the
demo as a substitute saved project.
The installed host's observed oversized-body response differs from the intended
application status; see the [runtime limitation](018c_results.md#limits-and-handoff).

## Dependencies and implementation gate

The Functions worker uses `api\.venv` and directly imports/calls the existing
`ai_collage` source in this checkout. Do not copy or move that source, launch
the CLI as a subprocess, or invoke the root `.venv` as a bridge. The two
environments have their own installed dependencies but share one application
codebase; keep HTTP handling separate from reusable Python capabilities.

Read-only verification confirms the API environment has
`azure-functions==1.26.0`, `pytest==9.2.0`, **Pillow and Pydantic** installed,
passes `pip check`, and imports the shared engine/conversation source.
The model-free engine/conversation path needs the existing root engine
requirements, not `requirements-agent.txt`, Azure credentials or model SDKs.
No new frontend package or Functions toolchain is expected.

For a fresh setup, the user can restore the existing engine requirements
into the **API** environment, from the checkout root:

```powershell
.\api\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\api\.venv\Scripts\python.exe -m pip check
```

This is a user-run installation step, not an action performed while writing
this spec. Keep the root `.venv` untouched. During implementation, make
`api\requirements.txt` include the root engine requirements alongside the
existing Functions pin, so future API setup is reproducible. Make the checkout's
Python package importable from the Functions working directory through scoped
launcher/test configuration; no global PATH/PYTHONPATH changes or second copy
of `ai_collage`. Restore all launcher environment/cwd changes on exit.

**Deferred packaging constraint:** A future deployment artifact must include
the Functions entry point, host configuration, requirements and shared
`ai_collage` package, with dependencies installed for the target platform,
not a bundled Windows `.venv`. Local import-path/PowerShell setup must remain
a development convenience, not a deployed runtime requirement. Do not add
packaging infrastructure or perform deployment work in 018c.

Installation confirmation permits verification only. Start implementation
only when the user explicitly approves this brief. Recheck dependencies then;
if missing/incompatible, stop with exact user-run steps rather than installing,
upgrading environments or waiting/polling for setup. Small task-related UI
dependency changes and local npm installs follow the standing
[repository permission](../.github/copilot-instructions.md), without another
approval. Other unexpected dependencies require a handoff and renewed approval.

## Verification and acceptance

Use temporary new roots/generated photo fixtures for automated work, never
existing user project stores. Keep all application checks offline and block
unmocked external services. Local browser-to-Function traffic is in scope.

| Area | Required evidence |
|---|---|
| Persistence/service | Create/reopen preserves ID, canvas, photo numbers/order/oriented dimensions and imported bytes. Normal offline `Conversation` resume works; no layout, history entry or model request is created. Fresh reads are non-mutating. |
| Validation and isolation | Invalid IDs, duplicates, malformed/duplicate multipart/JSON fields, unsupported/corrupt/multiframe images, byte/pixel limits and path/foreign-photo attempts fail explicitly. Disallowed Host/Origin requests cause no writes. Invalid saved state and missing assets do not become successful empty/default responses. |
| Publication/concurrency | Inject failures during import, state initialization and final publication; no partial public project or alteration of existing data. Competing creates from separate processes yield one committed project at most; a released/crashed writer does not leave a permanently busy project. |
| HTTP/runtime | Actual Functions routes return the documented status/shapes/images, exact-origin CORS and loopback binding. Exercise one real six-file request with each valid generated image exactly 25 MiB, plus an over-limit case; verify bytes and cleanup. Padding tiny valid JPEG fixtures is acceptable, not modifying originals. |
| Frontend | Real API shapes, create success/failure/duplicate/uncertain result, list/detail loading/error/empty/not-found, photo-load failure, stale-response cleanup and request bounds. Refresh/direct URL loads saved data. Demo remains independent, including a real project named `sample-london`. |
| Real browser | Create with own selected fixture photos/canvas, reopen after refresh and an agent-owned backend restart, then exercise backend-unavailable feedback and the separate working demo. Check desktop and narrow/mobile viewport usability. Mocked fetch is not the integration proof. |

Run the API suite and existing frontend tests/lint/build. Run targeted root
engine/storage and conversation-initialization checks; if shared persistence
or conversation implementation is changed, run the full root offline suite.
Do not duplicate the frontend type-check already included in its build.
For large-fixture checks, verify the real fixed thresholds, not only patched
smaller constants.

Verification servers are temporary and agent-owned. Do not stop or reuse a
user-owned server without permission; use a free loopback port pair with
matching API base/CORS if defaults are occupied. Verify listener addresses
and responsiveness, then stop only those servers/processes started for the
run. Leave no background watchers, unattended retry loop or temporary large
upload fixtures. Unexpected host/firewall/tool requirements are a blocker,
not permission to expose the server or change machine-wide settings.

Update usage documentation only where behavior/setup changes: concise root
UI quick start, API setup/configuration/contract and web workflow/demo notes.
Keep phase evidence, commands/results and limitations in `018c_results.md`,
then link it from this brief and the tracker/index. Do not add a results
placeholder before execution or duplicate its accounting in usage READMEs.

## Bounded Autopilot handoff

Once explicitly approved and dependencies are ready, implement only this
brief, verify it, record the results and stop for the user's manual
create/list/reopen review. Automated/browser success is not user sign-off.
Do not mark 018c closed or begin 018d automatically.

No live model/Foundry calls or paid replay allowance; no cloud services,
Blob/Azurite, deployment, authentication implementation, vision, graphical
editing or new history/generation features. No Git writes (including
staging/commits/branches), global settings changes or modifications to original
photos, pre-existing projects/archives or historical evidence. Preserve the
user's staging, including any already-staged tracker edits.
