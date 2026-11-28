# 019d: Performance results and closeout

**Status:** Complete and closed with the user's acceptance on 2026-11-28.
The launcher/diagnostics, small patch and separately approved
[read-path/thumbnail work](019d-measured-read-and-thumbnail-improvements.md)
are implemented, verified offline and exercised in user-led browser testing.
This closes bounded 019d and overall 019, not Azure hosting or authentication.

## Measurements (2026-11-27)

Local Functions in Ireland accessed US-region Blob storage, without `-Live` or
model calls. The user performed Projects -> reopen -> view P001 -> download PNG,
then two repeats, on a four-photo project with three saved proposals.
The baseline used the development UI; the patched repeat used the user's
reported production React bundle.

The patch increased ordinary JSON/download deadlines from 10s to 20s, removed
duplicate original-photo property checks and reused per-project read snapshots
within each request. Selection/model deadlines, retries and writer safeguards
were unchanged.

| Measure | Baseline | Patched / production UI |
|---|---:|---:|
| Logged GETs | 25 | 18 |
| Blob transport attempts | 832 | 597 |
| Slowest backend handler | 10.49s | 7.72s |
| Backend HTTP responses | All 200 | All 200 |

| Route | Blob attempts per GET, before -> after | Median handler time, before -> after |
|---|---:|---:|
| Projects | 17 -> 11 | 3.32s -> 2.79s |
| Project detail | 14 -> 10 | 2.94s -> 2.55s |
| Original photo | 18 -> not observed | 5.25s -> not observed |
| Conversation | 45 -> 45 | 7.40s -> 7.62s |
| PNG preview/download | 44 -> 44 | 7.03s -> 7.22s |

Each patched pass logged six GETs and 199 Blob attempts. The comparable
Projects/detail changes saved **30 attempts** across three passes. Of the other
205 fewer attempts, 72 reflect absent photo GETs, 88 two fewer PNG GETs and 45
one fewer conversation/recovery GET. Thus the total 28.2% reduction is not a
like-for-like backend improvement; browser image reuse is possible but unproven.

The baseline included a user-reported timeout and Check status recovery despite
backend HTTP 200. The repeat had no handler above the old 10s deadline, so it
does not demonstrate the benefit of the new 20s deadline. Backend metrics do
not establish browser completion or paint time.

**Remaining bottlenecks:** Conversation and PNG reads still cost about 7-8s.
Snapshot validation loads historical PNG bytes even for conversation JSON and
individual PNG delivery. Two near-simultaneous conversation GETs persisted on
every reopen; the earlier Strict Mode explanation remains unconfirmed.
Approximately 98% of summed handler time was inside measured Blob read operations
in both runs, including authentication/checks, not solely network time.
Concurrent handler totals are not experiment wall-clock time, and transport
attempts are not billing counts.

## Initial improvement candidates

- Trace duplicate conversation GETs using browser Network initiators and loaded
  bundle evidence before changing the UI.
- Separate metadata consistency checks from historical image-byte validation;
  avoid loading every PNG to return JSON or one requested PNG.
- Consider bounded GETs instead of redundant HEAD-then-GET where size, digest,
  identity and ETag checks can remain intact. These read-path changes need a
  short approved brief and focused integrity/freshness tests.
- After authenticated Azure hosting, remeasure with Functions near storage.
  Consider short-lived authorized SAS image delivery to bypass the backend
  image proxy. SAS, shared-client/cross-request caching and broad architectural
  changes remain deferred, not part of this immediate patch.

## Preserved raw evidence

Both JSONL snapshots were verified present locally, outside Git, under:

`%USERPROFILE%\.copilot\session-state\621a42a9-2ec6-4af0-a2d9-fde02d818692\files`

- Baseline: `019d-user-metrics-baf7060fa1e74e5c9dff04e3ff7e60f5.jsonl`
- Production repeat: `019d-user-prod-metrics-e1645d57f7fc4a51a4eafab74200403f.jsonl`

They contain request IDs, static routes, status, timings, sizes and transport
counts, not click identities or browser timings. See the
[diagnostics guide](../api/README.md#lightweight-local-request-metrics) and
[production measurement setup](../web/README.md#local-production-ui-measurements).
This record adds no authorization for Azure/model calls or Git writes.

## Approved read-path and thumbnail improvements

Local and Blob now publish Proposal 9 packages with required stored thumbnails;
Blob heads use version 3. Other conversation records stay at 8 and layout/project
format stays at 3. Conversation JSON validates metadata without image bodies.
PNG/thumbnail delivery checks only the committed target and requested asset.
Bounded GETs replace download-only HEAD/GET pairs, retaining original-photo
property checks and ETag-pinned ranges. History uses thumbnails; Current collage,
modal and download retain full PNGs.

### Controlled offline comparison

Real Azure SDK sends used a read-only fake HTTP transport with external network
connections blocked. Separate processes loaded the user's staged pre-change
Python sources via read-only `git show`, or the working sources. Both generated
the same four synthetic photos, canvas, two prompts and two deterministic recipes;
neither used archived project data or Azure/model services.
This is measured execution of both implementations, not a reconstructed count.

| Route | SDK sends, before -> after | Image body GETs, before -> after | Response bytes, before -> after |
|---|---:|---:|---:|
| Projects | 11 -> 8 | 0 -> 0 | 100 -> 100 |
| Project detail | 10 -> 7 | 0 -> 0 | 254 -> 254 |
| Original photo | 12 -> 8 | 1 -> 1 | 113 -> 113 |
| Conversation | 31 -> 16 | 2 -> 0 | 1,128 -> 1,128 |
| P001 full PNG | 30 -> 5 | 2 -> 1 | 18,041 -> 18,041 |
| P001 thumbnail | Not available -> 5 | Not available -> 1 | Not available -> 3,429 |

JSON byte counts use the adapter's ordinary serialization and collection wrapper;
image counts are actual saved response bytes, not compressed wire traffic.
Projects/detail/photo/full-PNG response hashes match across both executions.
Conversation keeps the same projected history/shape and byte count; request UUIDs
and the contract-bound canonical revision differ. P001's 213x320 thumbnail is
about **81% smaller** than its unchanged full PNG.
These two-proposal counts are not directly comparable with the earlier
three-proposal live 45/44 counts, and do not predict laptop-to-US latency.

The focused suites verify zero-image JSON, exact transport gates, persisted-byte
reuse without GET rendering/uploads, portrait/landscape/small/maximum thumbnail
geometry, corruption/dimensions/actual byte ceilings, unsupported versions,
ETag changes between SDK ranges, prior-reader consistency, fencing and recovery.
Injected thumbnail upload failure preserves the prior proposal and durable paid
claim; retry/status cannot dispatch again. Local orphan packages cannot be served.
Web coverage includes thumbnail-only history, explicit unavailable states,
full-preview modal/download behavior and in-flight project-switch cancellation.

Verification covered the current **987 Python cases**: the initial full run had
981 passes and three new test-harness failures (GET Origin versus existing Host/CORS
semantics, the Local publication error type, and an SDK fake-response method).
Those harness issues were corrected; the affected storage/application suites
passed all 113 cases, including three added Local thumbnail cases, and the final
API/metrics/proof/version follow-up passed all 58. The final focused SDK/read/
integrity gate passed all 18 cases, including zero-image operation status.
No production changes followed
the full run. All 83 web tests, lint and the production build passed; the build
explicitly targets `http://127.0.0.1:7071` (`index-BCoVOcy5.js`).

### Offline duplicate-request investigation and handoff

The offline trace found one conversation load on ordinary mount/rerender,
one per explicit refresh, and a new cancelled/rebound load on project switching.
Stable callbacks and the single-fetch request helper do not establish a
production duplicate cause. **Inconclusive:** no speculative deduplication,
cache or Strict Mode removal was added.
The next browser milestone should capture Network initiator stacks and loaded
production asset names, plus cold thumbnail/full-preview/download requests.

Use fresh supported projects and an explicit fresh Blob namespace; keep `web-dev`
and earlier namespaces untouched. Supported proposals must first be created with
separate model-call authorization. Then omit `-Live`, build with the explicit
local API URL and follow the [production measurement setup](../web/README.md#local-production-ui-measurements)
with fresh JSONL. No services or remote projects were started/seeded in this run.
At that handoff, browser verification and user acceptance remained outstanding;
the subsequent trial and closeout below satisfy those gates.

Additional evidence under the same session `files` directory:
`019d-controlled-reads.py`, `019d-controlled-before.json`,
`019d-controlled-after.json`, `019d-improvements-offline-1.txt` and
`019d-improvements-changed-tests.txt`, `019d-improvements-api-final.txt` and
`019d-final-read-gates.txt`.
The controlled helper loads sources in
memory and cleans its own temporary fixture directories; staging is unchanged.

## User-led browser verification and closeout (2026-11-28)

The user created fresh P001/P002 proposals in `web-019d-thumbnails`, then
restarted the API without `-Live` and with a fresh metrics log. Browser testing
covered opening the four-photo project, viewing P001 and downloading PNG, with
two initial repeats and subsequent production-bundle/thumbnail observations.
The full log includes 39 GETs, all backend HTTP 200, with 329 Blob transport sends.
It records browsing only, not the preceding model-call preparation.

Keep the two observed UI segments separate: the earlier segment has 23 GETs
and 208 sends, with development-module initiators, paired conversation requests
and no thumbnail GETs. The segment from 18:48 UTC onward has 16 GETs and
121 sends; screenshots confirm the production `index-BCoVOcy5.js` bundle,
stored thumbnails and one conversation request per observed reopen.
These segments are not identical click sequences or cache conditions; their
aggregate totals are not a controlled performance comparison.

| Route | Production GETs | Blob sends per GET | Median backend handler |
|---|---:|---:|---:|
| Projects | 1 | 8 | 2.29s |
| Project detail | 2 | 7 | 2.36s |
| Original photo | 4 | 8 | 3.41s |
| Conversation | 2 | 16 | 3.47s |
| Full PNG | 5 | 5 | 3.15s |
| Thumbnail | 2 | 5 | 2.59s |

The live sends meet the offline small-object gates. The conversation has two
proposals, unlike the earlier three-proposal baseline: use the controlled
offline comparison above for like-for-like reductions, not live 45 -> 16.
Thumbnails contain 88,712/89,277 bytes versus approximately 1,765,000 bytes
for full PNGs, about 95% smaller on these real photos.

The screenshot's `X-Collage-Metrics-Id`,
`c8a9f148-c328-4105-8abf-173eb36dc10c`, matches the 88,712-byte thumbnail
with five Blob sends and 2.601s backend time, versus approximately 2.64s
browser duration and 2.61s waiting for the server. Conversation and selected
preview Timing panels show approximately 3.25s/3.14s server wait.
The selected preview's Timing panel alone does not establish download identity.
Measured Blob reads account for approximately 98.9% of summed production
handler time, including authentication/validation; this is neither pure network
time nor experiment wall-clock time. No image-paint measurement was captured.

The earlier browser-cancelled conversation requests still completed as paired
backend 200s. Their absence in the confirmed-production observations supports
development effect replay for this trial, not an established production
duplication defect. No speculative deduplication or Strict Mode removal is needed.

Preserved JSONL snapshot, under the session `files` directory above:
`019d-user-thumbnail-metrics-86264a125ec84e868d7dc6eb16d0d31d.jsonl`.
Original user-supplied log:
`C:\Users\nkell\AppData\Local\Temp\collage-019d-reads-86264a125ec84e868d7dc6eb16d0d31d.jsonl`.
Browser screenshots remain attached to the session.

The user explicitly requested completion-tracker updates after reviewing these
results, accepting 019d and closing overall 019. No additional browser trial is
required for this scope. Earlier namespaces, archived projects and original
photos remain untouched; no Git writes are part of closeout.

### Deferred opportunities

Authentication/ownership and Azure hosting remain separately approved work.
Remeasure after hosting, ideally with Functions near storage and managed identity,
before pursuing detailed client/authentication-versus-Blob timing instrumentation.
Safe client/credential reuse, authorized direct image delivery, conversation read
projections and original-photo thumbnails remain optional, evidence-driven
follow-ups, not unfinished 019 tasks or authorization for new work.
