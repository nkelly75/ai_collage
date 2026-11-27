# 019a: Initial local storage extraction

**Status:** Complete and closed following implementation, offline verification
and the user's successful local smoke check/acceptance on 2026-11-27.
See [results and the 019b handoff](019a_results.md).
See [019](019-storage-abstraction-and-blob-persistence.md) for the agreed
sequence and private single-owner delivery target.

## Outcome

Extract one working read/write lifecycle: create an initialized web project,
list it, reopen it and retrieve its original photos through a narrow storage
boundary. Use real local files throughout, with no user-visible behavior change.
This is preparation for proving the same slice against real Blob in 019b,
not a complete storage conversion or claim of cloud readiness.

## Why this slice

At scoping, [ProjectFlow](../ai_collage/application/projects.py) staged uploads,
called [ProjectStore.create](../ai_collage/engine/projects.py), initialized
[Conversation](../ai_collage/agent/conversation.py), then published photos with
hard links and the project directory with a rename. Reopen/list/photo reads
also knew physical paths and the saved conversation-state location.

The coherent publication unit therefore includes original photos, project
metadata and initial conversation state. Publishing project metadata first and
adding conversation state afterward is not an acceptable extraction.

Proposal publication is deliberately deferred: it also couples rendering,
history events, baseline updates, provenance and request outcomes.

## Scope and responsibility split

| Area | Responsibility after extraction |
|---|---|
| HTTP adapter and UI | Existing requests, responses, limits and error/recovery presentation; no new API or UI behavior. |
| Application/agent logic | Validate the request, reuse photo validation and ordinary empty conversation initialization, and determine the initialized project's contents. Preserve domain/identity validation and existing error mapping. |
| Storage boundary | Publish the prepared initialized project without replacing an existing ID; enumerate published projects; read the records and original photo assets needed for reopen/photo retrieval. |
| Local implementation | Contained paths, physical record/asset reads and writes, staging, hard links/renames where appropriate, and operation-owned cleanup. |

Use the smallest typed interface and local implementation that serves those
operations. Define it at a dependency-safe shared boundary; the engine must not
gain an application/HTTP or Azure dependency. Reuse existing helpers rather than
introduce parallel importers, serializers or initialization logic.

Public storage operations should use logical project/asset identities and
bounded record/asset inputs or streams, not require callers to traverse a
durable project directory. Temporary local preparation files are acceptable.
Do not require all photo bytes to be held in memory together.

Move filesystem-specific publication out of `ProjectFlow`; merely wrapping its
current calls while leaving publication there does not satisfy this brief.
Route create/list/detail/photo through the extracted boundary, including the
project-validation path reused by conversation reads. Do not convert the
remaining conversation persistence as a consequence.

Retain the existing project mutation guard and its coverage. Its use of local
OS locks is intentional in 019a, not an implementation of a distributed lock.
Existing local consumers outside this slice may still use `ProjectStore` paths.

## Preservation and publication requirements

- Preserve current on-disk formats, directory organization, fixed owner,
  configuration/default data root, identifiers, canvas source and photo order.
  Existing local projects must remain readable without migration or rewriting.
- Preserve original image bytes and existing upload/decoded-image limits,
  EXIF-oriented metadata, strict record validation and path containment.
- Initialize the normal model-free conversation with existing preferences
  semantics, selected canvas and empty history. Do not create a second web
  settings record, competing canvas field or new initialization format.
- Publish only once the project, photos and initial state are complete.
  Duplicate IDs and competing creates must not overwrite data; retain explicit
  busy/duplicate outcomes.
- Handled pre-publication failures clean only the operation's own new files.
  Preserve existing projects and assets. A killed process may leave private
  staging/unreferenced assets, but must not expose a half-initialized project.
- Reads remain read-only: no initialization, repair, recovery writes or
  fallback data roots. Missing, invalid and inaccessible state remain distinct;
  a storage error must not look like an empty list.
- Keep today's conversation, current/history/source-selection and exact PNG
  download behavior working locally. Preserve offline CLI/replay and engine-only
  use; no model policy, retry, acceptance or rendering changes.

For 019b, document how prepared artifacts can be uploaded before a conditional
completion/publication record makes the project discoverable. Identify the
existence/conflict and incomplete-publication outcomes the boundary must express.
This is a concrete design note, not a Blob implementation or a promise of
atomic transactions across blobs. Do not expose local rename/hard-link semantics
as requirements on a future provider.

## Verification and acceptance

Use disposable generated-photo fixtures and existing test environments. Extend
existing tests rather than introduce a storage simulator or new test framework.

| Evidence | Required result |
|---|---|
| Create, then reopen through fresh storage/application objects | Same project ID, ordered photos/original bytes, canvas and empty initialized history; subsequent reads write nothing. |
| Existing saved-state fixtures | Read without migration; strict invalid-state and missing-asset behavior remains intact. |
| Duplicate and competing process creates | At most one published project; no replacement of the winner or unrelated data. |
| Injected preparation/publication failures | No partially visible project; handled failures clean owned assets and preserve pre-existing data. |
| Local workflow regressions | Existing API/application, engine storage, conversation and offline replay coverage remains passing; no external service calls. |

Relevant starting coverage is in
[engine storage tests](../tests/engine/test_storage.py),
[project-flow tests](../tests/application/test_project_flow.py),
[project-route tests](../tests/api/test_project_routes.py) and
[conversation-flow tests](../tests/application/test_conversation_flow.py).
Run focused cases first, then the existing root/API offline suites before
handoff. No frontend changes are expected; frontend validation is needed only
if a directly necessary frontend change is separately agreed.

Update [architecture](../architecture.md) to describe the implemented boundary
and record execution evidence separately after approval. User acceptance closes
019a; offline success alone is not sign-off.

## Exclusions and stop rules

No Azure access/provisioning, SDK installation, Azurite, real Blob integration,
model calls or new dependencies. No complete persistence abstraction, generic
filesystem API, elaborate fake Blob backend, queues, database, caching,
thumbnails, migration, automatic repair/cleanup service, deployment or
authentication implementation.

Do not convert proposal publication, conversation edits/history, request logs,
web-operation/selection records, CLI-only acceptance or evaluation archives to
the new boundary in this increment. Their current local behavior is retained.

If this slice requires broad agent restructuring, a persisted-contract change
or a second durable implementation of conversation initialization, stop and
revisit the boundary rather than expand scope. Preserve user data and staging;
no Git writes without explicit approval. Approval of 019a would not authorize
019b, cloud access or service calls.
