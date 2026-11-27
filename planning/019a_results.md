# 019a results: Initial local storage extraction

**Status:** Complete and closed on 2026-11-27 following offline verification
and the user's successful local smoke check/acceptance. The user authorized implementation of the
[019a brief](019a-initial-local-storage-extraction.md), subject to its scope and
guardrails. No Azure access, model calls, installations or Git writes.

## Implemented boundary

[ProjectStorage](../ai_collage/storage/contracts.py) and
[LocalProjectStorage](../ai_collage/storage/local.py) cover
existence checks, initialized-project publication, published project IDs,
project/conversation-state reads and original-photo delivery.
The interface uses logical IDs, existing typed records and photo streams,
not durable project-directory traversal.

[ProjectFlow](../ai_collage/application/projects.py) keeps request/domain
validation and HTTP-independent error mapping. It prepares uploads privately
using the unchanged engine importer and ordinary model-free `Conversation`
initializer, then passes prepared records and open original-photo streams to
storage. The implementation defaults to local storage and is injectable.
No provider configuration switch or Azure dependency was introduced.

Local publication writes the existing records and bounded photo copies into
destination-local private staging, links assets without replacement, then
publishes the project directory last. Handled failures remove only its new
asset links; a process kill may still leave private staging/unreferenced assets,
as before. Stream copying allows preparation on another volume; it adds one
bounded local photo-copy pass, not a claimed performance improvement.

The existing OS-held project guard still covers the existence check through
preparation/publication. Reads are read-only and preserve the distinction
between missing, corrupt and inaccessible data. The project validation reused
by conversation reads also goes through the new boundary.

Local formats, paths, owner, configuration, defaults, original bytes and canvas
source are unchanged. Existing saved projects require no migration. Engine,
agent, CLI/replay, HTTP and frontend implementations were not changed.
Conversation mutations, proposals, request logs, web-operation/selection
records and CLI acceptance retain their existing local persistence.

## Offline evidence

| Check | Result |
|---|---|
| Root core/application suite | 694 passed. |
| Explicit API suite in the API environment | 74 passed. |
| Focused storage additions | Seven cases, included in the root suite: real injected local-storage lifecycle/fresh reopen with no read writes; pre-extraction-style saved project read preservation; three publication failure windows; asset collision cleanup; duplicate publication refusal. |

Commands from the repository root, using the existing environments:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider
.\api\.venv\Scripts\python.exe -m pytest -q -c .\api\pytest.ini .\tests\api
```

Existing API coverage also passed for original bytes/EXIF metadata, strict
limits and invalid states, handled create failures, cross-process guards and
duplicate creation. Root coverage includes conversation/source/history,
rendering and offline CLI/replay regressions and engine dependency isolation.
An initial API invocation without the explicit test path broadened collection;
it was stopped and replaced by the two completed commands above.

Tests used generated photos and temporary roots with network-blocking fixtures.
No application was run against the user's saved-project roots. No real servers
were started, frontend code changed or live model trial performed.
Architecture was updated; no new lessons were added.

## Concrete 019b handoff, not implementation authorization

Prove this same slice against the development Blob account before extending
conversation persistence. The local protocol is a starting point, not evidence
that Azure integration works.

- Use logical owner/project/asset IDs for blob keys, not raw filesystem paths
  or upload filenames. Keep blobs private and backend-mediated.
- Upload validated photos and initial records into an operation-owned,
  immutable candidate namespace. Publish a completion record referencing that
  candidate only after all required objects exist. Enumerate completed projects,
  not upload/staging prefixes.
- Conditionally create the completion record without replacing an existing
  project ID. The existence check is advisory, not a reservation. The local OS
  guard is not a shared-host guarantee; conditional publication/shared
  coordination must enforce the Blob slice's conflicts.
- An existing published ID corresponds to `ProjectExists`; no completion
  record means no published project. A published record with missing/invalid
  referenced objects is invalid saved state, not an empty/missing project.
  Authorization/network/storage failures must remain explicit.
- A lost publication response does not prove rollback. Preserve uncertain
  outcomes and permit lookup; do not blindly retry or delete candidate objects
  that a successful completion record might reference. Cleanup is limited to
  objects known to belong to an unsuccessful operation.

This is not a multi-blob transaction, an implemented manifest format or a
distributed-lock design. SDK/authentication setup and real-account integration
need the separate 019b brief and approval. Revision/claim handling for all
conversation mutations belongs to the later complete-web-persistence scope.

## Acceptance and limits

After the recommended model-free create/list/reopen/photo smoke check, the
user reported "That went well" and moved on to discussing 019b. That establishes
acceptance of the bounded local extraction; no additional Copilot trial occurred.
Normal conversation/history/selection/download behavior remains available
locally. Neither offline evidence nor this acceptance certifies general model
quality or cloud readiness.

019a is closed. 019b, deployed Functions, authentication,
full Blob-backed web operation and performance work have not been implemented
or authorized. User staging is preserved; committing remains user-managed.
