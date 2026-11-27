# 019c: Complete web persistence in Blob

**Status:** Complete, explicitly accepted by the user and closed.
Implementation was approved, implemented and verified offline.
The renewed, separately approved model-free real-account proof passed after an
offline proof-guard repair. User-led web testing and explicit acceptance are
complete. See [019c results](019c_results.md) for both attempts and closeout.
The user agreed the outcome and verification responsibilities below.
[019b](019b_results.md) is closed after offline verification, its separately
approved real-account proof and explicit user acceptance. Its live allowance is
consumed; it does not authorize 019c calls.

See [019](019-storage-abstraction-and-blob-persistence.md) for sequencing and
the [infrastructure record](019b-initial-blob-integration.md) for the existing
development target. No resource deployment is required by this brief.

## Outcome and agreed scope

Run the existing Functions API and web UI locally, explicitly selecting Blob.
Blob is authoritative for the data required by the complete existing web
experience. Start with a fresh namespace containing no projects: upload photos,
create a project, converse and obtain deterministic collages. Refresh and restart
with a different empty local data root must restore the experience from Blob.

Local remains the default API mode; explicitly use `-StorageBackend Blob`.
CLI/replay remain local and offline-capable. No migration, discovery, compatibility
shim or copying of old local projects into Blob. Preserve existing local test
projects and archived evidence untouched.

| Existing capability | Required Blob-mode outcome |
|---|---|
| Create/list/reopen/original photos | Preserve the existing contracts and original bytes proved in 019b. |
| Conversation and learned photo references | Restore messages, history, names, preferences captured in the conversation, controls and pending questions from Blob. |
| Send and generation | Preserve the split interpretation/preparation/generation workflow, strict server-owned handoff and existing model/validation limits. |
| Request observation and recovery | Persist submissions, claims, attempts and outcomes; duplicates and refresh cannot repeat paid work. |
| Proposals and previews | Persist validated recipe/geometry/identity and the rendered PNG; serve saved full-resolution bytes without regeneration. |
| History and Current collage | Inspect historical collages; select an earlier editing source without losing later history or learned names. |
| Selection observation | Preserve action identity, confirmation, preparation abandonment and uncertain-action behavior. |
| Download PNG | Use the existing verified preview route and browser download behavior. |

No new UI features, web acceptance/finalization, image understanding, model
changes, cloud hosting, end-user authentication, new infrastructure, tenancy
framework, queue, background job, automatic paid retry or orphan collector.
Performance tuning remains optional 019d; correct and usable operation of the
agreed journey is required here, not an excuse to accept broken timeouts.

## Pre-implementation code trace

019b isolates initialized projects, but conversation operations still construct
local objects and use filesystem records directly. A backend selector alone
cannot convert the remaining workflow. This table records the starting seams;
current implemented behavior is in [architecture](../architecture.md).

| Current owner | Persistence that must cross the boundary |
|---|---|
| [ProjectFlow / storage](../ai_collage/application/projects.py), [contracts](../ai_collage/storage/contracts.py) | Project/state validation, publication, enumeration and photo delivery already use the initialized-project boundary. |
| [Conversation](../ai_collage/agent/conversation.py): initialization, `_commit`, `_append`, history/name checks | State, canonical events, identity/digests, record enumeration and interrupted-write evidence. |
| `Conversation.proposal`, `_publish`, baseline/source validation | Proposal record and PNG, publication identity, history/source relationships and preview digest; rendering currently uses local photo paths. |
| [RequestLog](../ai_collage/agent/requests.py): `attempts`, `reserve`, `finish` | Attempt enumeration, durable pre-dispatch reservation and completion/usage diagnostics. |
| [ConversationFlow](../ai_collage/application/conversation.py): `_snapshot`, `_save`, `_execute` | Web operation identity/sequence, prepared handoff, stage claims, result references and consistent revision projection. |
| `ConversationFlow.select`, `_save_selection`, selection observation | Selection claim, abandoned unstarted preparation, canonical selection event and final action outcome. |
| [API storage selection](../api/storage_config.py), [HTTP adapter](../api/function_app.py) | Blob currently rejects conversation routes; request-scoped factories must supply the same backend throughout a workflow. |

The existing operation claim is saved before dispatch. `RequestLog.reserve`
saves an attempt before the provider's actual HTTP call. These are correctness
boundaries, not optional diagnostics that can be uploaded at request end.
Proposal publication links recipe/PNG to history and baseline; selection binds
an action to a canonical event and any retired preparation.

CLI accepted versions and acceptance reconciliation remain local. Fresh Blob
web projects do not need an accepted-version import or a new web Accept feature.
Owner-level CLI preferences need not become a new cloud settings service:
retain the normal preferences captured in each new conversation.

## Approved code boundary

Extend `ai_collage\storage` with narrowly typed project/conversation persistence
operations, implemented for Local and Blob. Cover state/events, proposal packages,
attempts, web operations and selections; use logical IDs and current models,
not caller-supplied paths or a generic virtual filesystem.

Refactor the identified IO seams in `Conversation`, `RequestLog` and
`ConversationFlow` to use that boundary. Keep interpretation, reference/name
handling, layout validation, rendering, retry budgets, task history and response
projection shared. Do not create a separate Blob conversation implementation.
Local implementations retain their current record layout and behavior, including
CLI/replay acceptance. Engine modules do not acquire agent or Azure dependencies.

Request-scoped API factories must choose one backend and pass a consistent
storage session through project validation, agent operations, request accounting
and HTTP orchestration. A Blob conversation must never accidentally construct
a default Local `ProjectFlow` or `RequestLog`.

Temporary files are allowed for import, image decoding and deterministic
rendering. Materialize needed photo bytes into bounded request-owned scratch
storage and pass the normal renderer its local path mapping. Do not rewrite
photo identities/digests to scratch paths, hydrate a complete durable local
project tree, or use local files as a recovery authority. Delete owned scratch
files on normal exit; interrupted scratch is not published project state.

## Approved Blob publication and concurrency design

Use one strict per-project publication head under the namespace's `published`
prefix, with typed references to immutable project records and artifacts.
Preserve the unique candidate/attempt organization established by 019b.
The head identifies the currently committed record set; there is no arbitrary
path-to-Blob mapping or second conversation model.

For mutations, upload changed records/artifacts to fresh immutable candidate
keys, validate them, then conditionally publish their references through the
head. Unchanged originals/proposals remain referenced, not re-uploaded on every
mutation. Include digests and validated logical identities; derive keys within
the configured namespace/owner/project rather than trusting stored arbitrary URLs.

Group directly dependent writes at a publication checkpoint:

1. Commit an interpretation/generation claim before its stage can dispatch.
2. Commit each attempt reservation before a scripted or real provider call;
   finalize its diagnostics without erasing the reservation.
3. Commit an event and its updated state together. Publish a proposal's validated
   record/PNG with its event and baseline references, not a visible half-proposal.
4. Publish a prepared handoff before returning prepared status.
5. Commit selection state/event, any preparation abandonment and the completed
   action consistently. A durable claimed action still blocks competing changes
   if its final publication becomes uncertain.

Do not batch all checkpoints into a final upload after model work. A failed
response must leave the prior durable claim and any confirmed checkpoints
observable from another host.

### Writer ownership and fencing

Use a finite renewable Azure Blob lease on the publication head for the
project mutation guard, together with expected-ETag updates. Different projects
have independent guards. Competing tabs/workers/hosts using separate local roots
must receive the existing busy/conflict behavior without a local-lock dependency.
Initial project creation still uses conditional create-if-absent publication.

Candidate uploads can finish after ownership is lost, but publication must be
server-fenced: head writes carry the lease ID and expected ETag. A lease on an
unrelated lock Blob, followed by unfenced writes to mutable child records, is
not sufficient. Renew only while the owning bounded request is active; stop
its helper and release owned leases on exit. No persistent renewal service.

Check ownership before dispatch and each publication checkpoint. Lost/uncertain
renewal or publication prevents further dispatch; an in-flight model call cannot
be assumed canceled or rolled back. Preserve its durable claim and report
uncertainty if its outcome cannot be confirmed.

Lease expiration is not permission to replay an operation. An interpreting/
generating claim without confirmed live ownership is uncertain and blocks new
paid work, as today. Never reset claims, call counts or prepared handoffs because
their writer died, their lease expired or a fresh local root was selected.
If a compatible writer cannot safely determine ownership, fail explicitly.

### Readers and revisions

Bind each read to one committed head and its immutable referenced records.
Do not mix records obtained from unrelated head revisions. Validate the existing
project/photo, history/name, proposal/source, handoff and action/result invariants.
GET/list/status/preview routes do not initialize, claim, repair or publish.
Retain previously published immutable records so readers bound to an older head
can finish safely. Cleanup of never-published losing candidates must not collect
old committed snapshots; online garbage collection is outside this phase.

Keep the browser revision and generation state digest tied to the existing
canonical logical records. Internal ETags, lease renewals and attempt diagnostics
must not accidentally redefine the client's revision contract. Recheck the
client revision and saved preparation under the writer guard before mutation.

Preserve original-photo and preview digest validation. Reuse already validated
bytes within a request rather than repeatedly downloading the same artifact;
no persistent local cache or weakened validation as a shortcut.

## Contracts, limits and failure behavior

The mutable publication head requires an explicitly versioned **storage-only**
envelope, version 2. Use a fresh 019c namespace; leave 019b version-1
data/evidence untouched and reject unsupported envelopes explicitly. No migration,
dual-version read path or silent reinterpretation. Do not bump layout/project
format 3 or conversation record version 8 merely for storage extraction.
If an actual record-contract change becomes necessary, document and version
only that affected contract and update its dependent tests/docs together.

Preserve current HTTP DTOs, IDs, errors, Host/Origin/CORS checks, no-store/nosniff,
request limits, model corrections and interpretation/generation/work deadlines.
Keep bounded JSON reads/writes at 1 MiB per record, bounded original-photo bytes
at 25 MiB each, 2-6 photos, decoded-image limits and canvas axes at most 4096.
Bound the publication head itself at 1 MiB; exceeding it is an explicit failure,
not skipped history or truncated state.

Add a documented encoded-preview IO ceiling of 128 MiB, compatible with the
existing maximum canvas/RGBA renderer. Verify a maximum-supported render fits.
Bound actual streamed bytes and validate PNG dimensions/digest, not just declared
length or filename. This is a storage safety limit, not a larger canvas feature.

Storage credentials remain subscription-scoped Azure CLI credentials for the
existing development account/container. Keep finite SDK/token timeouts and
disabled SDK transient retries, including lease/publication calls. No keys,
SAS, broad storage credential chain, provisioning or RBAC changes.

The completed Blob mode permits the existing explicit `-Live` model workflow; without it,
model dispatch remains disabled. Model credentials/provider configuration stay
as currently implemented, distinct from storage authentication. Preserve optional
trial flags and their operator-owned external call-budget ledger: no allowance
renewal on restart/root change, no silent budget bypass. That existing local
single-writer trial ledger is not a cross-host aggregate budget; retain its
documented single-writer restriction and identical ledger across trial restarts.

Known storage/auth/permission/container failures remain `storage_unavailable`,
not missing projects, empty lists or Local fallback. Stale revisions/conflicting
claims remain explicit 409s. Corrupt or unsupported published state is rejected
without repair. Confirmed model failure/timeout remains distinct from uncertain
publication, and a valid saved previous collage must not disappear.

After an ambiguous head write, do not retry it blindly or delete potentially
referenced candidates. Reconcile using operation/action identity and committed
state where possible; otherwise report `outcome_unknown`, preserve evidence and
block new paid mutation. Definite unreferenced losing candidates may be cleaned
only with known ownership and conditional deletion. Cleanup/lease-release errors
are diagnosed without masking the primary failure. No container-wide deletion,
TTL repair, migration or automatic retry worker.

## Verification responsibilities and gates

### Offline implementation verification

Extend existing storage, agent, application, API and launcher tests with small
SDK-boundary mocks and scripted model clients. No emulator or network services.
Keep Local tests in the existing root environment and SDK-dependent Blob tests
in the API environment, with explicit suite selectors as documented today.
No dependency installation or upgrade is authorized by this brief.

Required cases include:

- Complete logical conversation/proposal/attempt/operation/selection round trips,
  unchanged photo bytes and read-only reopen using a different empty local root.
- Independent writers, duplicate submissions, stale revisions, single stage
  claims, immutable proposal publication and selection/abandonment races.
- Lease conflict, renewal failure and expiration during model/render work;
  stale writers cannot publish or cause a second model dispatch.
- Failure or lost response at claim, reservation, proposal/state, final operation
  and selection checkpoints, including success-at-Azure followed by lost response.
- Persisted consumed attempts and uncertain claims remain non-retryable after
  restart; prepared-but-unclaimed work remains explicitly continuable.
- Strict missing/corrupt/oversized records, mismatched identities/digests and
  previews, unsupported storage versions and explicit access/service failures.
- Model-free history/source selection/download, pending-task confirmation,
  existing names/questions/returns and all Local CLI/replay regressions.
- Factory/backend isolation, `-StorageBackend Blob -Live`, inherited-setting
  isolation, trial-ledger behavior and owned scratch/lease-helper cleanup.

Run focused cases first, then the root and combined API/Blob offline suites.
Frontend source should not need changes: exercise the existing UI against the
completed backend. If a directly required frontend edit emerges, keep it narrow
and run its existing tests/build; no redesign or dependency churn.

### Separately approved model-free real-account proof

Use a dedicated proof-only entrypoint/harness with a scripted `ModelClient`.
Reuse normal HTTP handlers, validation, `RequestLog`, agent stages, renderer and
Blob writes. Do not simply upload finished archived records: that proves readback,
not the write workflow. Do not add a production fake-provider flag, browser
parameter or fallback. Normal launches cannot select fixtures or bypass `-Live`.

Use read-only fixture material from local `project-02`, not its full history.
Inspection found that P001/P002 are suitable candidates: both are 1200x1800,
use photos 1-4, and P002 is parented to P001. Select only the needed intent/layout
responses; adapt to fresh identities/current validation and generate four small
photos with the required aspect ratios. Do not upload its original photos or
copy/change its persisted project. No replay through P015 or later proposals.

The short success journey is one initial proposal and one revision, then history,
Current collage selection, action/status lookup and PNG download/readback across
an owned host restart with a different empty local root. Return only the four
expected scripted interpretation/generation responses; unexpected stages or
corrections fail rather than consuming an open-ended response queue.
Reserve/finalize attempts normally, but do not fabricate paid provider usage.
Compare generated previews/originals to this run's own bytes/digests, not to
archived PNGs containing different source photos.

No Foundry/model HTTP calls or model credential construction in this proof.
Storage authentication remains real Azure CLI authentication. Offline tests must
verify that missing/exhausted scripted responses cannot fall back to Foundry.

Before any live run, agree an explicit allowance: exact target, one fresh
`proof-019c-<uuid>` namespace/project, four generated photos totaling at most
1 MiB, two proposals/four scripted responses, finite local HTTP/Blob request caps,
timeouts and cleanup inventory. Request caps must include token-independent
Blob IO, lease acquisition/renewal/release, readback and cleanup across restart.
Determine and instrument those caps after offline implementation; no guessed
large allowance or reuse of 019b's consumed budget.

Approval of the implementation spec does not approve that live run. Stop a
failed run without an automatic rerun; preserve uncertainty and use only
separately permitted inspection/owned cleanup. Successful cleanup deletes only
the exact run-owned inventory after all owned hosts/helpers stop, removing the
publication head before its referenced objects. Record actual evidence and
accounting in a separate 019c results record.

### User-driven web acceptance

The user supplies live model-backed coverage, not the agent proof. In a separate
fresh namespace, start the API and Vite locally, explicitly selecting Blob and
the existing `-Live` model gate. Start from an empty Projects list, upload fresh
photos, create a project and have a short basic conversation.

Inspect history, switch Current collage and download PNG. Refresh, then restart
the API using a different empty local data root with the same Blob namespace.
Verify restored photos/messages/names/current source/history/previews and another
normal conversation step. No old local project data should be needed.
The user's explicit result/sign-off closes 019c. This is the actual web experience,
not a repeated manual copy of the agent's fixture API proof.
No user-run model trial or service budget is implied by implementation approval; agree the
specific procedure/limits before its execution.

## Implementation ordering and stop rules

This is one phase delivering the complete workflow, not authority to ship a
partial Blob conversation UI as complete:

1. Define the typed record/artifact IO seams and Local adapters; prove Local
   behavior and pre-dispatch persistence remain intact.
2. Implement the versioned Blob head, immutable record publication and fenced
   mutation guard; prove failures/independent-writer behavior offline.
3. Wire all existing API operations through that backend and remove the 019b-only
   route rejection. Add proof-only fixture wiring and offline coverage.
4. Update implemented architecture/API/CLI/test documentation and a results
   record. Seek the separate real-account allowance, then user web acceptance.

Keep the [architecture](../architecture.md) current only with implemented
behavior; this brief retains the approved scope and gates. Maintain
`tests\storage`, `tests\agent`, `tests\application` and `tests\api` ownership.
Discuss any new LESSONS entry before adding it. Preserve user staging/history:
no Git writes, automatic commits, branch changes or pushes.

Revisit the scope if safe completion requires a broad agent rewrite, a generic
filesystem framework, distributed infrastructure beyond Blob primitives,
schema changes unrelated to affected persistence, migration, new UI features
or new permissions. Do not quietly reduce concurrency/recovery safeguards to
make the first plausible Blob implementation pass.
