# 019d: Measured reads and stored proposal thumbnails

**Status:** Complete and closed with the user's acceptance on 2026-11-28,
following offline verification and user-led browser testing.
The offline duplicate-request investigation was inconclusive, as permitted;
subsequent production observations show one conversation request per reopen.
See [results](019d_results.md) for measured reductions, browser evidence and
closeout. Further service calls, deployment and Git writes require separate approval.

See [initial performance results](019d_results.md) for measurements and preserved
JSONL locations, and [019](019-storage-abstraction-and-blob-persistence.md) for
the overall boundaries. Overall 019 is closed; this is not deployment scope.

## Outcome and scope

Make reopening and browsing saved collages cheaper without removing conversation
history, hiding proposals or changing the original-photo renderer.

Conversation JSON must not fetch image bodies. An image GET must retrieve only
the requested committed asset and the metadata needed to establish its identity.
History uses pre-generated small thumbnails; Current collage, historical modal
viewing and Download PNG retain the existing full-resolution PNG.

Apply the shared persistence/validation changes to Local and Blob. Local remains
the launcher default; Blob remains explicit. CLI/replay stay local and offline
capable, with their existing acceptance behavior. Shared proposal publication
produces the same complete asset package for all entry points, not a web-only
alternative implementation.

Out of scope: SAS delivery, Azure hosting/authentication, infrastructure/RBAC,
shared-client or credential lifetime, cross-request caching, background jobs,
history pagination/virtualization, original-photo thumbnails, model/prompt changes,
new retries, automatic repair/backfill/migration, deletion and Git writes.

## Implementation sequence

### 1. Separate proposal metadata and image validation

The current `Conversation.proposal()` fetches PNG bytes.
`ConversationFlow._core_bytes()`, detail projection and selection/result checks
use it while building a JSON snapshot, causing historical-image downloads.

Extract explicit metadata validation shared by these callers. Preserve strict
record/version/identity checks, project/photo and canvas relationships,
recipe/geometry/digest checks, history/task/intent/source relationships,
names/questions, operation/result and selection consistency. Removing a PNG
read must not remove those checks.

Conversation/detail/status projection and canonical revisions operate on
validated logical metadata, not image bodies. Revision/prepared-handoff
semantics still bind the canonical records; transport ETags, cached bytes and
lease diagnostics must not redefine them.

Image availability/corruption is checked when an asset is delivered, rather than
making every conversation GET certify every historical image. This is an
intentional read-boundary change: an unrelated corrupt historical PNG may leave
the transcript readable, but its own image GET must fail explicitly. Missing or
inconsistent published asset references remain metadata errors.

Keep full image verification where required for publication, CLI acceptance and
mutation/source operations. Do not introduce an unsafe metadata-only shortcut
for paid dispatch, stale preparation checks or selecting an editing source.

### 2. Target image delivery

Replace the full `_snapshot()` dependency in `ConversationFlow.preview()`.
Use narrowly typed storage/application helpers, not direct Blob SDK access from
the HTTP adapter or a second conversation implementation.

Bind the request to one publication snapshot. Establish that the proposal is
committed and belongs to the requested project/proposal, then validate its
requested asset's declared size, actual bytes, digest, PNG format and dimensions.
For Blob, validate head references and the target's state/event/proposal binding;
for Local, prove commitment through state and its corresponding proposal event,
not merely the existence of a proposal directory.

Do not replay unrelated history, download other proposal images or check original
photo properties just to serve an already-rendered PNG. Serving this asset does
not certify unrelated conversation history; the conversation endpoint owns that
broader metadata validation.

Keep the existing `/projects/{project_id}/proposals/{proposal_id}/preview` route,
content type, saved bytes, identifier validation and download behavior. Unknown
or unpublished proposals cannot be served.

### 3. Replace redundant HEAD-then-GET reads

Use bounded GETs for objects that must be downloaded anyway. Obtain the ETag
and response size/range information from that same download; check actual
streamed length and the immutable reference digest/size before using bytes.

Preserve one-head read consistency and mutable-head expected-ETag/lease fencing.
Do not follow a changed head mid-read or combine incompatible range responses.
SDK multi-range reads must stay pinned to the same ETag; oversize/truncated/
changed/missing responses fail explicitly with bounded memory consumption.
The head's returned ETag must remain usable by existing fenced writers.

Retain genuine existence/property/lease checks where no object body is needed.
In particular, preserve the original-photo presence/size checks on project
list/detail loading and fresh busy/ownership checks. Do not replace those checks
with full photo downloads or remove them to meet a count target.

SDK retries remain disabled; current token/connection/read timeouts and
request-local cache/snapshot limits stay unchanged.

### 4. Publish stored history thumbnails

Generate one deterministic thumbnail from the successfully rendered full PNG,
before publishing the proposal. Use the existing Pillow dependency and LANCZOS
resampling, with no model call, second layout render or original-photo
edit. No generation on GET, optional quality setting or additional service.

**Thumbnail contract:** PNG, longest edge at most 320 pixels, preserved aspect
ratio with integer rounding, each axis at least one pixel, no upscaling.
Use bounded RGB/RGBA output and an encoded limit of **512 KiB**. This covers the
existing 140px-wide/100px-high history display at roughly double density without
transferring full canvas images. The required typed `thumbnail` descriptor stores
`width`, `height`, `size`, `sha256` and `source_preview_digest`; the source digest
must equal the proposal's `preview_digest`.

Publish proposal metadata, full PNG and thumbnail as one package, committed with
the existing proposal event/baseline checkpoint. Bind the thumbnail descriptor
to its proposal and full PNG; verify generation from those exact saved PNG bytes.
Validate both images before publication. A thumbnail failure fails explicitly,
preserves existing operation/attempt accounting and does not trigger another
paid call. No visible half-package or success-shaped full-image fallback.

Local stages the complete package before its existing directory publication.
Blob uploads immutable candidates and advances references through the existing
leased/ETag-fenced head. Keep ambiguous-upload/publication preservation and
exact owned-candidate cleanup; do not collect historical committed assets.

Add `/projects/{project_id}/proposals/{proposal_id}/thumbnail` as a GET route with
the same targeted commitment/integrity checks and existing Host/Origin/CORS,
`no-store`, `nosniff` and safe-error behavior. Use a static `thumbnail` metrics
route label without identifiers. The UI derives its URL from validated IDs;
keep current conversation DTOs unless a directly necessary change is identified.

History images retain lazy loading, labels, keyboard behavior and modal opening,
but use this thumbnail route. Current collage/modal/download continue using
`preview`. A failed thumbnail shows an explicit unavailable state while allowing
the user to open the full saved preview; it does not silently fetch full images
for every history entry.

#### Affected versions and archives

Make the new thumbnail descriptor required on **Proposal record version 9**,
overriding Proposal's inherited version 8 without changing other conversation
records. Advance the **Blob storage head from version 2 to version 3**, with
required thumbnail references matching the proposal/preview identity sets and
descriptor sizes/digests.

Keep layout/project format 3, conversation state/events version 8, preferences,
attempts and prepared-handoff versions unchanged. This feature does not require
a new layout format or a blanket conversation-version bump.

Reject unsupported proposal/head versions explicitly. Use fresh test projects
and a fresh Blob namespace for the next milestone; existing trial namespaces
and local archived projects stay untouched. No legacy thumbnail fallback,
automatic conversion, backfill or dual-version path. Keep launcher defaults and
existing namespaces unchanged; document the explicit fresh-namespace launch.
Update affected examples/fixtures/contracts together, rather than rewriting
archived results.

### 5. Investigate duplicate conversation GETs offline

Trace mounting/effects, callback dependencies, request helpers and production
build behavior. Use focused tests or a production UI against a local stub API
if useful; no Azure or model requests.

Fix only an established cause with a regression case. Preserve legitimate
refresh/Check status calls, cancellation, project switching and recovery
freshness; do not add a cross-request cache or indiscriminate deduplication.

An inconclusive investigation is an acceptable outcome and does not block steps
1-4. Record what was checked and the browser Network initiator/build evidence
needed next. Continue that investigation during the browser-led milestone;
do not treat Strict Mode as established or silently broaden the run.

## Offline verification and measurable gates

Use existing fixtures/runners and the real SDK with offline transports where
applicable. A mocked client-call count alone is not proof of HTTP send counts.
Add focused cases that fail without these changes, then run the existing
API/Blob, relevant agent/CLI and web regression gates, lint and production build.
No dependency/environment installation or live service access is included.

| Area | Required gate |
|---|---|
| Conversation/detail/status JSON | Zero PNG, thumbnail or original-photo body reads. Preserve complete history, metadata validation and recovery/selection output. |
| Blob project list/detail/photo | In the existing single-project four-photo small-object fixture: at most 8 / 7 / 8 transport sends, respectively, down from patched 11 / 10 / 12. Keep the original-photo property checks. |
| Targeted full PNG / thumbnail | At most 5 Blob transport sends per successful GET for small, single-download fixtures: head, state, target event, proposal and requested asset. No listing, other history/proposal/image reads or original-photo property checks. Larger PNGs may require bounded, ETag-consistent SDK ranges. |
| Thumbnail geometry/bytes | Enforce 320px maximum edge, no upscaling, aspect-preserving rounding and 512 KiB actual encoded ceiling. Cover portrait, landscape, small and maximum-supported canvases. |
| Stored asset reuse | Fresh storage objects/process-equivalent reopen serves the same persisted thumbnail/full PNG bytes; GET performs no render, resize, upload or model call. |
| Integrity/publication | Reject corrupt/oversized/truncated/wrong-digest/wrong-dimension assets, malformed bindings, unsupported versions and unpublished packages. Unrelated image corruption does not force transcript image downloads. |
| Concurrency/recovery | Preserve older bound readers, fresh subsequent readers, fencing/lease loss, ambiguous outcomes, prepared-stage freshness, selection abandonment and no repeated paid dispatch. |
| UI | History fetches thumbnails; current/modal/download fetch full PNGs. Selection, history, error visibility and cancellation remain correct. |
| Duplicate GETs | An evidence-backed offline fix, or an explicit inconclusive report with browser follow-up. Not a mandatory one-request claim. |

Measure before/after on identical deterministic offline history fixtures, including
multiple proposals; record transport sends, image-body reads and response bytes.
The zero-image and targeted-read gates are primary; do not claim a guessed total
conversation count or promise laptop-to-US latency from these tests.
No larger ceilings, skipped validation, truncated history or hidden errors to
meet a metric. If a necessary integrity check makes a stated gate infeasible,
report the conflict rather than weakening it.

## Handoff and next browser-led milestone

Update architecture/current usage documentation for implemented boundaries and
affected versions. Extend [019d results](019d_results.md) with the offline evidence,
actual counts and duplicate-request outcome; keep phase evidence out of the main
README and do not add LESSONS without discussion.

Stop after the approved implementation/offline gate and provide a fresh-project/
namespace production-UI test setup. Do not launch against Azure, seed remote
history, invoke models, delete old data, stage or commit automatically.

With separate user authorization, repeat the same browsing sequence on fresh
supported data with several proposals, fresh JSONL and browser Network evidence.
Include a cold image load so thumbnails are observed; distinguish thumbnail,
full PNG and download requests. Compare like-for-like record counts and cache
conditions, not just aggregate attempts. Capture host/browser timings separately,
and use initiators/build evidence for any remaining duplicate GETs.

Browser testing and explicit user acceptance were required for closeout and are
now recorded in [019d results](019d_results.md); offline success alone was not
user sign-off. Authenticated hosting and any later SAS/client/cache optimization
remain separate decisions.
