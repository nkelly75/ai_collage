# 018e results: Real conversation and previews

**Status:** Successfully completed and closed with the user's manual testing
and explicit sign-off on 2026-11-26. Initial approved implementation and bounded
verification completed on 2026-11-25, followed by the user-approved refinements
below. Closure does not authorize 018f. The Copilot live allowance, including
unused calls, is closed.

Scope and stop rules: [018e brief](018e-real-conversation-and-previews.md).
The user authorized that brief, API dependency restoration and its bounded
three-message/12-call trial on 2026-11-25.

## Implemented slice

| Area | Result |
|---|---|
| Application | `ConversationFlow` composes the existing interpretation/generation stages across HTTP. Private version-1 operation records persist one UUID/submission, claims, prepared handoff and canonical outcome references. |
| Protection | Existing OS-held per-project guard covers conversational mutations across processes/tabs. Revision/source checks and duplicate recognition prevent repeated model dispatch. An interrupted claim is uncertain, not a renewable lease. |
| Read path | Shared `Conversation(read_only=True)` validates existing history/names/proposals without initialization or acceptance recovery. DTOs project safe messages/pending interactions/current baseline; the preview route verifies immutable published PNG bytes. |
| HTTP/runtime | Five conversation/preview routes, bounded strict JSON and existing Host/Origin/error boundaries. Explicit `-Live` opt-in; model-free creation/browsing remains available. Optional single-project persistent trial ledger is applied inside the backend request context. |
| Deadlines | Existing 120s/180s model ceilings and four-call allowance preserved. Adapter work envelopes are 150s/210s with checks around work/before publication, including after rendering; browser deadlines are 160s/220s including JSON parsing. Host ceiling is 225s. |
| UI | Real saved-project workspace; one Send, actual phase labels, validated action/source/photo-reference summary, current rendered preview and persistent transcript. Ordinary text answers/naming/returns use the shared agent. Restored prepared work requires explicit Continue generation. |
| Recovery | Lost responses trigger status inspection, not paid resubmission. Bounded status observation, busy/stale errors, image errors, confirmed failure and unknown outcome remain distinct. Uncertain work blocks another paid mutation for inspection. |

No separate agent, browser renderer, model-facing prompt change, recipe format
bump, queue, background job, migration, cloud deployment, graphical/photo
editing or 018f acceptance/navigation/download control was added. The scripted
demo remains separate.

The root `requirements-agent.txt` selections were reused in `api\.venv`,
constrained to the root environment's installed versions; the Functions pin
was retained. No root-environment rebuild, global install, frontend dependency
change or unrelated upgrade was performed. `pip check` reported no broken
requirements. API/UI usage guides and the implemented architecture map were
updated; no new LESSONS entry was added.

## Offline verification

| Gate | Actual outcome |
|---|---|
| Focused application/shared-stage tests | 39 passed. |
| Root Python suite | **674 passed** in 531.48s: 661 existing cases plus 13 new application cases. |
| Separate API environment/suite | **67 passed**: 47 existing cases plus 12 conversation-route and 8 live/trial-launcher cases. |
| Frontend | **54 passed**, clean lint, successful build/type-check. The existing 19 cases plus 35 focused conversation-client/workspace cases. |
| Restored API dependencies | `pip check` clean. |

New application cases exercise fresh-process reads, split handoffs, repeated
POSTs, old-operation replay without baseline reselection, ordinary questions/
answers, name lifecycle and receipt approval, exact returns, stale input,
cross-process busy observation, confirmed timeout, claim interruption and
publication-before-result-recording interruption. Controlled rendering delay
proves the outer work check can stop before publication without shortening the
180s model setting. Read-only acceptance and tampered-preview checks preserve
saved bytes rather than repairing them.

HTTP cases cover strict JSON/DTOs, original Host/Origin boundaries, disabled
live access, missing/invalid identities, duplicate calls and real PNG delivery
with controlled model clients. Launcher cases cover both installed Windows
PowerShell and PowerShell 7, explicit trial settings, inherited-setting cleanup
and caller-environment restoration.

Frontend cases cover one-Send sequencing, real/restored phases, questions and
acknowledgements, explicit Continue, lost/late responses, bounded observation,
disabled live access, stale/unmounted callbacks and preview errors. Tests use
controlled responses and blocked external network access; no paid failure or
timeout was induced.

For the initial implementation, commands were the brief's full root/API/frontend gate, with the API suite
explicitly selected from the checkout root. Focused gates and the expanded API
gate were run as cases were added. There were no failing test runs. A stale
setup-screen sentence was noticed during model-disabled browser preflight,
corrected and covered; frontend tests/lint/build remained green.

## Actual local browser / model smoke trial

Used the real Browser canvas, Vite, Functions, existing provider/agent and
deterministic renderer. No direct CLI/replay generation or mocked browser
response substituted for the UI path.

Evidence root:
`C:\Users\nkell\.copilot\session-state\621a42a9-2ec6-4af0-a2d9-fde02d818692\files\018e-evidence`

One project, `p18e-smoke`, lives in the isolated `data` root there. The four
repository London originals were selected in their normal 1-4 order through
the actual file-input handler and creation UI, at 1200x1800. A temporary
loopback-only fixture directory supplied the original bytes to the browser's
file input; it was not another application API or generated-image source.
The model-disabled workspace and original-photo delivery were verified before
enabling the trial. Existing `.collage-data-web` and CLI roots were not used.

Owned listeners were verified on `127.0.0.1:7083` (API) and
`127.0.0.1:5183` (UI). During the preflight swap to `-Live`, terminating the
launching shell left its known Core Tools child bound to the port. The first
replacement host could not bind. That verified owned child was stopped by
specific PID, then the correct live-enabled/capped host was verified before
the first submitted message. No submitted message or model call was retried.

| Step | Exact UI message | Actual result | Calls |
|---|---|---|---|
| 1 | Make a simple collage using all four photos, with a light background, generous margins and rounded corners. | P001, all four photos, positive rounding on each. | 2 |
| 2 | Make photo 2 a bit smaller. Leave everything else alone. | P002; photo 2 authored width **0.42 -> 0.38**, with no other recipe change. | 2 |
| 3 | Remove the rounded corners from photo 2 only. Leave everything else alone. | P003; photo 2 radius **18 -> 0**, with no other recipe change. | 2 |

Each message showed **Understanding your request** then **Creating your layout**.
The action/source/photo-reference summary was visible during generation.
Mutation-observed phase labels/timestamps are preserved in
`browser-phases.json`; they are actual UI observations, not simulated timers.
Browser preview checks confirmed successful 1200x1800 image loading.
Browser screenshots of the workspace/P001/P003 were captured in this session's
Browser tool history; the immutable full preview PNGs remain in the data root.

Reload after P001 restored its message/result/preview without a model request.
After P002 completed and its exact edit was checked, the owned API and workers
were stopped and restarted with the **same root and ledger**. Both a GET and
the reloaded UI restored four messages/P002 with the ledger still at four.
Only then was the third message submitted. Final reload restored six messages/
P003, with no pending question or unresolved operation.

### Accounting and objective checks

- **6 / 12 calls**, one interpretation plus one generation per message.
- **37,593 input tokens; 2,494 output tokens**; all six attempts have known usage.
- Zero validation corrections, questions, naming receipts, failed model calls,
  stage timeouts, paid retries or reruns in the three-message execution.
- Ledger `calls.json` remained limit 12 / used 6 across stage endpoints and host
  restart. Its unused six calls are now closed, not available for further work.
- Every attempt completed with the existing high interpretation / low generation
  settings. All six canonical events are the expected intent/proposal pairs.
- Accepted version stayed **null** throughout. No automatic acceptance occurred.
- Source-original hashes remained unchanged; P001's saved preview digest still
  matched its initial recorded digest after all edits. Every published proposal/
  preview passed shared canonical identity validation.

Supporting artifacts include `root-tests.txt`, `api-tests.txt`,
`agent-constraints.txt`, `source-hashes.json`, `step-1-view.json`,
`step-2-check.json`, `restored-after-restart.json`, `final-checks.json`,
`final-conversation.json`, `browser-phases.json`, the ledger and the complete
isolated project history/request/proposal files.

## Manual-feedback follow-up

On 2026-11-26 the user reported positive manual browser iteration, including
continuation in another tab, and authorized targeted improvements before
sign-off. Read-only inspection through P013 confirmed completed operations,
clarification continuation and successful bounded layout corrections. The
reported book-shop tilt request completed as P013 despite a browser timeout;
the precise timed-out HTTP request was not established. These observations
do not replace the user's visual judgment or constitute acceptance.

Implemented:

- Answered-question/name prompts no longer remain visible while their reply is
  processed. Continue generation is hidden during the initiating tab's
  automatic generation, but retained for recovered prepared/unstarted work.
- Idle refresh is labeled **Refresh conversation**; recovery uses **Check
  status** and explains that it reads saved state without resending/model calls.
  Neither control interrupts this tab's active request.
- A confirmed completed response survives a failed subsequent transcript
  refresh as a confirmed result awaiting refresh, not an unknown mutation.
  Recovered completion explicitly acknowledges the original request.
- Proposal-specific preview loading remains visible until the matching image's
  load event. Errors/reload remain explicit and image sizing is preserved.
- Contextual question/name placeholders and Enter-to-send / Shift+Enter-newline
  behavior share the existing guarded submission path; composition, repeated
  keydown and empty/busy input do not dispatch another request.

The project list itself took approximately 30-34 ms for two projects and
does not acquire the conversation mutation guard. A controlled offline test
held the actual rendering path behind a thread gate and demonstrated that
the old async adapter blocked the Functions event loop until an independent
watchdog released it. Conversation/operation/preview request execution now
runs in request-scoped executor threads, with request-local event loops for
agent stages. The same test now reads the project list and active generation
status before releasing rendering. No queue, detached job, changed lock,
new dependency, deadline increase or paid retry was introduced.

| Follow-up gate | Actual outcome |
|---|---|
| Frontend suite | **60 passed** (six new cases), lint clean, build/type-check successful. |
| API suite | **68 passed**, including the gated rendering/concurrent-read regression. |
| Shared application conversation cases | **13 passed**; core agent/renderer code was not changed in this follow-up. |

The concurrency regression failed before the adapter fix and passed afterward.
Frontend fork-worker startup timed out without running tests; the existing
runner's single-thread mode (`--pool=threads --maxWorkers=1`) ran the full suite.
Intermediate assertion/type-check issues were corrected before the final
green gates. One existing App navigation call-count assertion failed once;
the unchanged test passed on the full-suite rerun. No dependencies were
installed and no new model/browser trial
was run. Existing user-owned project data was not modified by this work.
No server processes were started, stopped or manually restarted.

All follow-up changes remain unstaged. The user's staging fingerprint at this
follow-up's entry, `dcd044aa279087a7fb7813cab7fce4aa8344d01b`, was preserved.
API/UI guides and the implemented architecture map reflect the improvements.
At this checkpoint, manual sign-off was still pending; no 018f work was authorized.

### Confirmed-failure recovery correction

The user's subsequent restart confirmed responsive project listing during
conversations and working Enter submission. "Grow the book shop by 12%" then
exhausted three generation-validation attempts, correctly leaving P013 as the
baseline. The UI nevertheless appended unknown-outcome wording to the
confirmed `stage_failed` response. The user authorized this focused correction.

Confirmed `stage_failed` (422) and `stage_timeout` (504) now automatically
reconcile the original operation and conversation with GETs only. Consistent
terminal state restores the composer without repeating any paid stage. A
failed refresh preserves the confirmed failure and offers manual Check status;
contradictory saved status remains blocked and never offers Continue.
Generation-validation exhaustion now has specific safe wording: no valid
layout within the attempt limit, previous preview unchanged, no automatic
retry, and names may already have changed. Other failure causes retain their
existing messages/codes; model/attempt limits and validation are unchanged.

Offline verification: **64 frontend cases passed**, lint/build/type-check
green; **14 application conversation cases passed**; **13 conversation-route
cases passed**. New cases cover known failure/timeout auto-refresh, failed
refresh fallback, contradictory status, and real bounded validation rejection
with preserved proposal/preview bytes. No model calls or server restarts were
performed. The user's staging fingerprint at this correction's entry,
`82de2edad8d48a1a3af034e6ac08029ed48c5651`, was preserved.

### Optional refresh placement

After successful P014 and positive image-loading feedback, the user approved
separating optional cross-tab synchronization from recovery. Idle refresh is
now a small icon beside the fixed Conversation heading, with tooltip and
accessibility label "Refresh saved conversation and preview", disabled or
hidden during this tab's active request. Explicit Check status remains beside
recovery messages; there is no idle refresh button in the composer.
This supersedes the initial text-button placement described above.

The full frontend suite passed **65 cases**, with clean lint and successful
build/type-check. The added case verifies header placement, accessible naming,
busy disabling and read-only synchronization of another tab's saved changes.
No dependency, backend behavior or model call changed. User staging remained
`82de2edad8d48a1a3af034e6ac08029ed48c5651`; manual sign-off was still pending at
this checkpoint.

## Manual sign-off and phase closure

On 2026-11-26 the user accepted the overall results and explicitly requested
that the Markdown records consider 018e done: "I'm happy with the overall
results." Their browser testing in `project-02` exercised iterative layouts,
clarification/name resolution and continuation in another tab. They confirmed
fast project listing during conversations after restart, working Enter
submission, successful failure recovery followed by P014, and useful
preview-loading feedback, then continued with further small conversational
edits before sign-off.

This closes the agreed local prompt-to-preview slice, including its targeted
manual-feedback refinements. It is user acceptance, not an inference from
scripted checks. The broader 018 workflow remains incomplete: proposal
navigation, explicit acceptance/download and later trial scope remain tentative
and unapproved. No further Copilot model calls were made for this closeout.
Git staging, commit and branch management remain with the user; the closeout
preserved their entry staging fingerprint
`6a2df023ac8fbb8092430a3a70827e03a68ca960`.

## Handoff and limits

The initial owned verification servers were stopped after dependent checks. Original
photos and the isolated evidence store/ledger are preserved; temporary browser
input copies and the fixture launcher were removed. No Git writes
were performed: the user's entry staging fingerprint
`751b19044dd357392d63b07f4d25b066b3f3faf5` was preserved, including their staged
planning edits.

The agreed 018e work is **complete and closed with the user's sign-off**.
The live pass is deliberately small; it does not certify broad agent reliability,
all physical-phone/desktop combinations, cloud readiness, distributed locking
or automatic crash repair. Synchronous I/O cannot be forcibly rolled back by
a browser timeout; uncertain publication remains blocked for inspection.
Full recovery UX and dedicated design-workflow controls remain 018f.
No further Copilot live calls or 018f implementation are authorized.
