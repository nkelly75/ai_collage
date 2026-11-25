# 018c: Persistent project flow results

**Status:** Successfully completed and closed with the user's manual testing
and explicit sign-off. Later increments, including 018d, remain unapproved.
Scope: [018c brief](018c-persistent-project-flow.md).

## Delivered

- Real multipart create, sorted project list, independent detail reload and
  original-photo routes. The thin Functions adapter calls shared Python source;
  no source copies, CLI subprocesses or root-venv bridge.
- Separate `.collage-data-web` default, with an absolute data-root override.
  Existing CLI stores/archives are neither discovered nor migrated.
- Existing format-3 projects and empty, model-free conversation state; existing
  conversation controls are the sole canvas source. No format bump, initial
  layout, prompt, proposal or fabricated history.
- Private same-filesystem staging, project-directory publication last,
  operation-owned rollback, and nonblocking OS-held cross-process project guards.
  GETs validate without recovery writes or missing-state initialization.
- Connected create/list/reopen UI, backend photo URLs, visible loading/error/
  empty/missing states, request deadlines and cancellation. Failed setup retains
  selections; duplicate/uncertain creation offers lookup of the submitted ID.
  Navigating away from an in-flight create retains an explicit lookup notice.
- London script isolated at `/demo`, including when a real project is named
  `sample-london`. Reset affects only the demo. Retired health/check-backend and
  browser-draft plumbing removed.

The shared engine changes are narrow: typed photo size/media exceptions retain
the existing `CollageError` parent, and containment normalizes equivalent Windows
device-path prefixes. A real competing-create test exposed Python 3.12 briefly
returning prefixed/non-prefixed resolutions during directory creation. The fix
preserves escape rejection and has deterministic regression cases.

## Automated evidence

These are the original implementation checks, before the organization follow-up
below. Commands ran from the checkout root unless noted; current suite commands
are in the [CLI guide](../docs/cli-guide.md#verification) and
[API README](../api/README.md#offline-tests).

| Check | Command | Result |
|---|---|---|
| Full offline Python regression | `.\.venv\Scripts\python.exe -m pytest -q` | **635 passed**, including four Windows containment cases. |
| API, publication and launcher suite | In `api`: `.\.venv\Scripts\python.exe -m pytest -q` | **48 passed**. |
| Frontend behavior and API client | `npm --prefix .\web test` | **19 passed**. |
| TypeScript and production bundle | `npm --prefix .\web run build` | Passed; build includes type-checking. |
| Frontend lint | `npm --prefix .\web run lint` | Passed. |
| Patch whitespace | `git diff --check` | Passed. |

API cases use generated photos/temp roots and block external socket connects.
They cover selection order despite reordered multipart parts, exact original
bytes/EXIF orientation, normal empty Conversation resume, non-mutating reads,
strict/duplicate JSON and multipart fields, invalid IDs, corrupt/BMP/multiframe
images, the actual 25 MiB and 40,000,000-pixel boundaries, actual total-body length
despite a false Content-Length, invalid/missing saved state/assets, explicit
storage-read failures, failure injection before publication, competing worker
processes and lock release after process termination.

Launcher cases cover Windows PowerShell and PowerShell 7, default/alternate
loopback port pairs, invalid origins, version/environment failures and exact
environment/cwd restoration. Frontend cases cover real response shapes, pending
submission protection, preserved setup, duplicate/uncertain lookup, cancellation
after navigation, malformed/host responses, response-body deadlines, photo-load
errors and the independent demo.

## Organization and documentation follow-up

- Moved project lifecycle orchestration into
  `ai_collage\application\projects.py`, with a package-purpose docstring. The
  checkout-relative default data root and existing API behavior were preserved.
- Consolidated Python tests under root `tests`, separating
  `tests\application\test_project_flow.py` from
  `tests\api\test_project_routes.py` and the API launcher tests. The two existing
  virtual environments remain separate and unchanged; default root discovery
  excludes the Functions-specific suite.
- Follow-up checks passed **2 application cases** and **47 API/launcher cases**.
  After the filename-only clarifications, the **2 application** and **29 HTTP
  route cases** passed again. Default root collection found **637 tests**,
  including the application cases and excluding API tests; this collection
  check was not another full regression run.
- Added the current [architecture map](../architecture.md), linked from the
  README, and a maintenance reminder in the repository instructions. Current
  testing instructions were updated without rewriting earlier check results.

## Real host and browser evidence

Used Core Tools **4.17.0**, Functions runtime **4.1055.300.26527**, API Python
3.12 and the installed SDK **1.26.0**. Agent-owned Functions/Vite listeners were
confirmed at **127.0.0.1:7071/5173**, never wildcard-bound. All generated project
data lived in a session-artifact fixture root, not the default or user stores.

Actual HTTP checks verified 201/detail/Location, original JPEG/PNG bytes and
headers, EXIF-oriented metadata, duplicate 409, missing project/photo 404,
foreign Host/Origin 403 without publication, exact-origin CORS/preflight 204,
unsupported DELETE 404, and retired `/api/health` 404.

One multipart request containing **six valid JPEG files of exactly 26,214,400
bytes each** was accepted with **201**. Total body length was **157,287,413
bytes**, including multipart overhead. Every stored asset and all six HTTP photo
responses matched the input bytes. These were deliberately identical padded
generated JPEGs, each SHA-256
`bd02cab9f1d73abe82a44ef13351c11edc33089f89c796cf52e1332a5517b8e2`.
A photo of 25 MiB plus one byte returned **413**, with no published project or
staged/imported leftovers. These local checks are not an Internet upload
performance benchmark.

The real browser exercised the actual file input using generated JPEG/PNG
`File` objects and `DataTransfer` (not an automated operating-system file picker).
It created real `sample-london` with a **2048x1024** canvas and **320x160 /
120x240** photos, then reopened it on refresh. After terminating the owned API
host/workers, Projects showed an explicit unavailable/retry state while the
separate four-photo demo still produced P001. A new host process reopened the
same saved list/project and loaded both photos unchanged.

Browser inspection used **1280px desktop** and **360px narrow** same-origin
iframes. Saved photos retained proportions; project pages had no horizontal
overflow. Setup changed from two columns to one and its controls stayed within
the viewport. The desktop frame was scaled only for visual capture inside the
narrow app panel; layout measurements remained 1280px. Temporary frames were
removed. This is not physical-phone certification.

## Limits and handoff

- **Host-level oversized bodies:** At **167,772,161 bytes** (160 MiB plus one),
  this installed host rejects input before Python binding with an empty HTTP
  **500 or a connection abort**, not a dependable 413. The host log explicitly
  identifies its 167,772,160-byte cap. Application-handled size errors return
  413. No host patch or raised/lowered agreed limit was introduced. The UI
  treats non-JSON/network failures as uncertain and offers lookup without retry.
- The acknowledged storage-probe warning from 018b remains; no Azure storage
  account/emulator or health-monitoring workaround was added.
- Process death during publication can leave private staging/unreferenced
  assets; no crash journal, general garbage collector or shared-host/Blob
  concurrency guarantee is claimed. The user accepted possible wasted disk
  space for this local slice; adding photos to saved projects was parked.
- Verification servers/workers were stopped and generated project data,
  including the large uploads, removed. Small session-local HTTP evidence is
  retained. No packages were installed, models/cloud services invoked,
  original photos/archives modified, or Git writes performed.
- At the original implementation handoff, the pre-implementation staged-content
  fingerprint remained `63b8e48bc23bd51fffebf94701ab8b91a9d4b4f2`; implementation
  and handoff edits were left unstaged. Subsequent staging was user-managed;
  the user's index, history and branches were preserved throughout the follow-up.

## User acceptance and closeout

On 2026-11-25, the user reported manual testing, confirmed a persisted project
under `.collage-data-web\users\local-dev\projects`, and explicitly approved
closing 018c. This supplies the user sign-off that automated/browser checks
alone could not provide.

The [root UI quick start](../README.md#ui-getting-started) remains the current
usage guide. Safe manual removal of selected test-project directories, with
the backend stopped and imported copies left alone, is documented in the
[API cleanup notes](../api/README.md#manual-test-project-cleanup).

Conversation/generation, saved history actions,
editing/deletion, authentication, deployment and Blob persistence remain outside
018c. No later increment was started or authorized by this closeout. The user
will handle the commit; no staging, commit or branch operations were performed.
