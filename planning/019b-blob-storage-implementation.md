# 019b: Blob-backed initialized-project slice

**Status:** Draft for review, not implementation authorization. The user selected
API-only proof, Azure CLI authentication, and offline verification followed by
one bounded agent-run live proof and a separate user smoke check/sign-off.

The [development infrastructure record](019b-initial-blob-integration.md)
identifies the deployed account, resource-group portal link and verified access.
Infrastructure is ready; application persistence still uses local files.
See [019](019-storage-abstraction-and-blob-persistence.md) for the increment
sequence and private single-owner delivery target.

## Outcome and boundaries

Prove the same initialized-project lifecycle extracted in
[019a](019a-initial-local-storage-extraction.md) against real Azure Blob Storage:
create, list, reopen and retrieve original photos through local Functions HTTP
routes. A fresh worker must reopen the project without local saved project data.

This is an explicitly selected **API-only Blob mode**, not a working Blob-backed
conversation UI. Normal Functions/web operation remains local by default, and
offline CLI/replay remain local regardless of API storage configuration.
No frontend changes, migration, Functions deployment, new infrastructure,
Foundry/model calls, performance work or extension into 019c.

| API operation in Blob mode | Required behavior |
|---|---|
| `POST /api/projects` | Existing multipart contract; publish a complete initialized project; 201 and existing detail/Location shape. |
| `GET /api/projects` | List only completed projects in the configured namespace, sorted by ID; existing response shape. |
| `GET /api/projects/{id}` | Read and validate project/state/assets; existing detail shape and canvas source. |
| `GET /api/projects/{id}/photos/{number}` | Return validated original JPEG/PNG bytes, with existing content type, `no-store` and `nosniff`. |
| Conversation, request/status, generation, selection and proposal-preview routes | After existing Host/Origin checks, return 501 with `blob_slice_only`, before constructing a conversation flow, reading local project data or initializing any model provider. |

Do not make unsupported routes appear to work by initializing empty local state,
copying Blob projects into the local store or falling back to local persistence.
These routes retain their full existing behavior in Local mode.

## Configuration and authentication

Add `-StorageBackend Local|Blob` to `api\start.ps1`, defaulting to Local.
Use `AI_COLLAGE_STORAGE_BACKEND` for the worker's explicit selection; missing
means Local, while blank/unknown values fail with `configuration_error`.

Blob mode requires backend-only configuration:

| Setting | Meaning |
|---|---|
| `AI_COLLAGE_BLOB_ACCOUNT_URL` | HTTPS Blob endpoint recorded for the development account; no credentials, query string or arbitrary request-supplied host. |
| `AI_COLLAGE_BLOB_CONTAINER` | Existing `collage` container; the application does not create containers. |
| `AI_COLLAGE_BLOB_SUBSCRIPTION_ID` | Recorded development subscription, used to select the CLI credential context without changing CLI defaults. |
| `AI_COLLAGE_BLOB_NAMESPACE` | Explicit isolated logical namespace; one validated lowercase alphanumeric/hyphen segment, not a filesystem path. |

For this increment, reject a target account/container/subscription other than the
recorded development target. This is not a general cloud-target configuration
framework. Missing or invalid settings fail explicitly; do not silently substitute
local storage, another account, namespace or identity.

Use the existing `azure-identity` dependency's `AzureCliCredential`, scoped to
that subscription. No `DefaultAzureCredential` chain, interactive login,
connection strings, account keys, SAS or browser credentials. Azure RBAC remains
the storage access control; fixed owner `local-dev` is not end-user authentication.

Preserve the launcher's loopback binding, exact CORS/Host/Origin checks, request
limits and process-environment/cwd restoration. Local launches clear inherited
Blob settings from the worker environment without changing the caller's values.
Blob launches forward only validated backend settings. Reject Blob mode combined
with `-Live` or model-trial settings before starting the host; enforce the same
no-live rule for direct worker configuration.

Do not set `AzureWebJobsStorage` to this account. Application Blob persistence
and Functions host storage are separate concerns. Local mode must not construct
a Blob client/credential or make Azure calls.

## Code and dependency boundary

Reuse `ProjectStorage`, `ProjectFlow`'s existing preparation/initialization and
the current strict project/conversation models. Add one isolated Blob adapter,
for example `ai_collage\blob_storage.py`, selected by a small API-side factory.
Keep Azure-specific imports out of the engine, ordinary local storage imports,
CLI and replay. No generic filesystem/provider framework or second importer.

The current local guard may remain as a local contention optimization; its lock
files are not durable Blob state or a cross-host guarantee. Correctness must
hold for clients with independent local roots. Preserve Local mode's existing
guard coverage and publication behavior. Avoid creating local saved project,
conversation or photo copies in Blob mode; bounded temporary preparation and
photo-validation files are allowed and cleaned up.

Add `azure-storage-blob` as an API runtime dependency in `api\requirements.txt`,
using a compatible supported 12.x range and existing dependency conventions.
Reuse `azure-identity`; do not upgrade unrelated packages or add the Blob SDK to
engine-only requirements. SDK-specific tests can run in the existing API
environment. Installing/updating packages in `api\.venv` requires separate
explicit approval before pip runs; no root-environment or global-toolchain change.

Expected changes are the adapter, narrow storage/error-contract adjustments if
needed, API selection/dispatch, launcher, API dependency manifest, focused tests
and directly related documentation. Preserve current HTTP DTOs, upload limits,
photo numbering, canvas source, project/layout version and conversation version.

## Blob organization and publication

Use logical identities, not upload filenames, local absolute paths or
`Photo.imported_path` as Blob locators. Under the configured namespace, use:

```text
<namespace>/users/local-dev/published/<project-id>.json
<namespace>/users/local-dev/candidates/<project-id>/<attempt-id>/project.json
<namespace>/users/local-dev/candidates/<project-id>/<attempt-id>/conversation/state.json
<namespace>/users/local-dev/candidates/<project-id>/<attempt-id>/photos/<asset-id>
```

`attempt-id` is a fresh server-generated UUID hex value for each create attempt;
asset IDs come from the existing validated importer. Preserve prepared project
and initial conversation fields, including photo identity/digest and canvas
controls. Validate imported-photo metadata without resolving durable local paths;
factor a small existing validation helper only if necessary.

The completion document is a new, small strict storage envelope with only
`schema_version: 1`, `owner_id`, `project_id` and `attempt_id`. Validate exact
fields/types, supported version, expected identities and identifier syntax;
derive all referenced keys from them. It is not a new layout/project format or
second settings record. Reject unsupported envelope versions without a shim.

Publication order:

1. Reuse normal model-free photo validation and conversation initialization in
   private local scratch storage before writing candidate objects.
2. Upload original photos and the prepared project/state into the unique
   candidate namespace, without replacing existing objects.
3. Only after every required upload is confirmed, conditionally create the
   completion document with create-if-absent semantics. This is the visibility
   and duplicate-conflict boundary, not a multi-blob transaction.

`exists` is advisory; it does not reserve an ID. Competing creates, including
independent workers/local roots, must publish at most one completion document.
An existing ID returns `project_exists`/409, never replacement of the winner.
No leases, distributed-lock service or reservation/expiry framework is needed
for this immutable initialization slice.

List only the `published` prefix. Unpublished candidates are never projects.
Strictly validate published entries rather than silently skipping corrupt ones.
On load, validate the completion document, existing records, owner/project/photo
identity, canvas and presence/size of every required photo. A missing completion
document means no published project; missing/invalid referenced objects after
completion mean `invalid_project_state`/409.

Use existing strict bounded JSON parsing, including duplicate-field and
unsupported-version rejection. Keep the 1 MiB JSON, 25 MiB encoded-photo and
40,000,000 decoded-pixel limits. Bound actual streamed/downloaded bytes rather
than trusting Content-Length. Reuse image decoding/EXIF-oriented dimension
validation for photo delivery; never regenerate or re-encode originals.
GET/list operations perform no storage initialization, publication or repair.

## Failures, uncertainty and cleanup

Keep Blob authentication, permission, missing-container, transport and service
failures distinct from missing project/photo and invalid saved state. A 404 for
the container is not an empty project list. Translate known operational failures
to `storage_unavailable`/503; retain existing 404/409/input errors where
applicable. Log diagnostic causes server-side without exposing tokens, internal
records, paths or Azure exception details in HTTP responses.

Disable SDK transient retries for this increment, including publication writes.
Use finite connection/read and CLI-token process timeouts, documented with the
implementation; no automatic create retry or success-shaped fallback. Do not
claim that a client timeout cancels an in-flight storage request.

If the completion write may have reached Azure but its result is unknown, return
`outcome_unknown`/500, preserve the candidate objects and allow ordinary GET
lookup of the project ID. A lost HTTP response after publication is likewise
reconciled by reading, not resubmitting. A not-found read while an earlier create
may still be in flight is not proof of rollback.

For definite failures before publication, or a confirmed losing attempt, cleanup
is limited to that operation's known-owned, unreferenced objects. Never delete
objects that an uncertain/successful completion write could reference. Cleanup
failure remains visible in diagnostics and must not mask the primary failure.
A killed worker or uncertain upload may leave private orphaned candidates;
there is no automatic garbage collector, TTL cleanup or repair service.

## Verification and acceptance

All ordinary tests stay offline and block network access. Extend current
application/API/launcher tests and add small SDK-boundary mocks as needed, not
Azurite or a storage emulator. Required cases:

- Fresh-object reopen, sorted list, unchanged canvas/photo identity, EXIF-oriented
  dimensions and exact original bytes; GETs write nothing.
- Conditional publication conflicts from independent clients, partial uploads,
  failure before completion, and success-at-Azure followed by a lost completion
  response. Preserve the winner and uncertain candidates.
- Strict invalid/truncated/oversized records and photos, missing referenced
  objects, unsupported envelope versions and invalid key identities.
- Authentication/permission/container/network errors stay explicit and never
  become not-found, empty-list or Local-mode success.
- Blob mode rejects every unsupported route without local reads, model-provider
  initialization or writes; Local mode and CLI/replay remain unchanged.
- Explicit mode/config validation, no inherited accidental Blob/live mode,
  subscription-scoped CLI credential selection, environment restoration and
  operation after changing the disposable local data root.

Run focused cases first, then the existing root and API offline suites before
live proof. From the repository root, the API suite must explicitly select
`tests\api` with its existing `api\pytest.ini`; do not accidentally collect the
whole repository with the API interpreter. No frontend validation is required.

### Proposed agent-run real-account allowance

This allowance is part of the draft, not permission to run it now. After
implementation and explicit live-proof approval:

| Limit | Allowance |
|---|---|
| Target | Only the recorded development account/container; no provisioning or RBAC changes. |
| Runs/data | One planned agent-run proof, one fresh uniquely named `proof-019b-<uuid>` namespace, one project and two generated JPEG/PNG photos totaling at most 1 MiB. No user photos or archives. |
| Requests | At most 30 local HTTP requests and 200 Blob data-plane HTTP requests across the run, including readback and cleanup. SDK retries disabled; count requests in the proof harness, without a production budget framework. |
| Other services | No model calls, Foundry access, keys, SAS, production access or infrastructure deployments. |

Exercise the real local Functions HTTP routes: empty namespace, create, list,
detail, both original-photo downloads, duplicate rejection and unsupported-route
rejection. Restart the owned Functions host with a different disposable local
data root, then list/reopen/download again using the same Blob namespace.
Check the metadata and downloaded byte hashes against the generated originals.

Use a small explicit opt-in proof harness/instructions, outside default pytest
execution, with finite HTTP waits and the request caps above. Stop only processes
started for this proof. Clean successful test data only through the harness's
exact run-owned object inventory after requests have finished; delete its
completion document before referenced objects. This is not a product delete API
or a permission to clear the container. Preserve any uncertain objects and report
their identifiers for explicit follow-up rather than guessing that cleanup is safe.

A failed run is not permission for another live attempt. Bounded read-only
inspection and safe owned cleanup may use the remaining allowance; further live
runs need renewed approval. Record counts, outcomes and remaining test artifacts
in a separate 019b results record, not as success claims in the architecture.

Finally provide a short model-free API smoke-check procedure for the user, using
a separate namespace. The user's manual result/sign-off closes 019b; offline or
agent-run success alone does not. Do not imply that the browser conversation
workflow is ready until the separately approved 019c work is complete.

## Documentation and stop rules

After implementation, update `architecture.md` and `api\README.md` to describe
the actual two API storage modes, launch/configuration, authentication, failure
semantics and API-only limitation. Keep deployed facts in the infrastructure
record and execution evidence/accounting in the results record; link rather than
duplicate them. Do not change LESSONS without discussing a concrete lesson first.

Stop and revisit scope if this needs conversation persistence, broad agent
restructuring, new layout/project/conversation contracts, a migration, frontend
changes or additional cloud permissions/resources. No Git writes without
explicit approval. Approving infrastructure or these clarifying answers does
not approve implementation, Python installation or live application tests.
