# 018e: Real conversation and previews

**Status:** Successfully completed and closed with the user's manual testing
and explicit sign-off on 2026-11-26; see [results and limits](018e_results.md).
Implementation, the described API dependency restoration and the
bounded three-message/12-call live trial authorized by the user on 2026-11-25:
"Go ahead with implementing ... Stick to the agreed scope and guardrails."
The live allowance, including unused calls, is closed.
The user authorized targeted manual-feedback improvements on 2026-11-26:
coherent progress/recovery controls, contextual composer/Enter behavior,
image-load feedback and an offline responsiveness investigation/fix. These
are implemented and verified in the [results follow-up](018e_results.md#manual-feedback-follow-up),
without new Copilot model calls. The user subsequently accepted the overall
results after further browser iteration. Later phases remain unapproved.
[018d](018d_results.md) is complete and closed; its unused allowance is closed.
See the [018 tracker](018-local-conversation-and-preview.md) for later phases.

## Outcome and agreed boundaries

Turn a saved local photo/canvas project into a working conversational workspace:
send a prompt, see real interpretation/generation progress, and view the
backend-rendered result. Refreshing or reopening restores the saved conversation
and current editing preview, not simulated or browser-only state.

One **Send** automatically interprets and then generates when needed, using
separate HTTP requests. There is no additional approval of an interpretation.
Expose the existing natural-language capabilities, including ordinary edits,
clarification answers, photo-name learning/listing/forgetting/reassignment
confirmation, retries and exact returns to earlier proposals. Do not redesign
or tune that agent behavior.

In scope: thin Functions routes, application orchestration, server-held stage
handoffs and operation claims, read-only conversation/preview retrieval, real
workspace wiring, honest timeout/recovery states and focused verification.

Out of scope: proposal thumbnail navigation, dedicated **Continue from here**
baseline selection, acceptance/download controls, photo/canvas editing,
adding photos, deletion, graphical editing, vision, cloud deployment,
authentication, Blob, queues/background jobs and broad agent evaluation.
The dedicated design-workflow controls remain 018f; **Continue generation**
after refresh is recovery, not that future baseline-selection action.

Preserve CLI/replay commands, model-facing instructions, reasoning defaults,
correction allowances, layout/conversation formats and original photos. Do not
reopen 018d's replay allowance or use old projects as trial fixtures.

## Workspace behavior

Reuse the current responsive conversation-left / preview-right design.
Saved projects must not inherit the demo's suggested-message restrictions,
timers, hard-coded proposal IDs or acceptance/download buttons.

| Surface or outcome | Required behavior |
|---|---|
| Empty project | Show its actual numbered photos and canvas, an empty transcript/preview and an enabled composer when live requests are available. Do not generate on create, open or refresh. |
| Send | Record one user submission, disable competing sends and show **Understanding your request**. Keep the existing preview visible while working. |
| Prepared generation | Show a short validated action/source/target summary, then **Creating your layout** and automatically start generation in the still-active initiating view. No fabricated percentages, token streaming or extra summary-model call. |
| Question or naming confirmation | Show the backend's question and allow an ordinary text reply. Do not auto-answer identities, auto-approve names or enter generation merely because interpretation finished. |
| Acknowledgement/name listing | Display the existing backend result without inventing a layout or generation phase. |
| Proposal | Display its actual immutable PNG and proposal ID; update the editing baseline only after confirmed publication. No separate browser renderer. |
| Natural-language return | Display the exact selected preserved proposal. Do not regenerate, accept it, erase later messages or roll back photo names. |
| Transcript | Persist user messages and meaningful assistant outcomes with stable IDs/order. Show proposal IDs and concise summaries, but defer historical thumbnail/action controls. Never display raw model JSON, correction transcripts or hidden reasoning as chat. |
| Reopen/refresh | Reload transcript, baseline, pending question/receipt and operation status from Python. Completed work must be visible after a backend restart. Unsaved composer text need not survive. |
| Prepared work found on reload | Show **Continue generation**; do not start a paid stage automatically. During this unresolved operation, disable a competing new Send. |
| Another tab is working | Explain the busy/conflict state and refresh status; do not submit a replacement request or overwrite a newer preview with an old response. |
| Failure | Preserve the submitted message and explicit failure/recovery information. Distinguish missing preview, failed image load, unavailable backend and genuinely empty state. |

Keep `/demo` separate, simulated and usable without the backend. Reuse modest
presentation pieces where helpful, not the demo state machine or a general UI
workflow framework. Preserve keyboard submission, accessible labels/status,
narrow-screen layout, stale-response cancellation and original-photo display.
Do not introduce browser storage, draft autosave or client-side language parsing.

## Shared backend and application boundary

Use the [018d stages](../ai_collage/agent/conversation.py):
`Conversation.interpret()` returns a normal `RequestResult` or
`PreparedGeneration`; `Conversation.generate()` consumes the latter.
The [architecture map](../architecture.md) remains the responsibility boundary.

Put orchestration in a small `ai_collage\application` conversation module,
alongside the existing [project flow](../ai_collage/application/projects.py).
Functions handles HTTP validation/serialization and invokes ordinary Python
workflows. Reuse existing project guards, strict records, contained paths,
atomic writes, request accounting and provider integration. Do not call CLI
subprocesses, copy agent logic or put Functions types into the agent.

The backend owns prompts, validated intents, prepared handoffs, source binding,
call accounting and operation transitions. The browser sends text and opaque
identifiers, never a trusted intent, recipe, filesystem path, provider setting,
reasoning override or replacement correction allowance.

### Minimal web-operation records

Add a small, strictly versioned application record under each web project's
private operation directory. This is additive web orchestration data, not a
new engine/conversation format or a second conversational memory. Do not
discover/migrate CLI stores or backfill unrelated archives.

An operation retains its opaque request ID, exact submission/revision identity,
request-start boundary, stage/claim state, server-held prepared handoff when
applicable, and references to its canonical outcome/events. Retain the safe
error classification and enough evidence to distinguish completion, failure
and uncertainty after a lost response. Persist the submission once, before
model dispatch; do not create a new chat message per validation correction.

Use the existing agent events/proposals/names as authoritative semantic history.
Project the web transcript from operation boundaries and those results; do not
copy raw model history into a competing browser transcript store. Return safe
user-facing summaries, not raw records, absolute paths or exception details.
Normal CLI/replay projects acquire no web-operation records.

### Claims, duplicate requests and stale state

Use the existing non-waiting, OS-held per-project mutation guard across worker
processes, extended to every conversational mutation. Hold it over validation,
durable claim, the stage call and result recording. Reject competing mutations
from other tabs/processes; a disabled button alone is not protection.
Read-only status/preview requests must remain usable while a stage is running.

Require these transitions:

```text
new request -> interpreting -> final result
                           -> prepared -> generating -> final proposal
stage execution ----------> known failure OR uncertain/interrupted outcome
```

- Persist a stage claim before dispatch. Store the prepared handoff before
  telling the browser generation is available. Atomically claim it before
  invoking generation; a duplicate request must never claim it twice.
- A repeated request ID with the same original submission returns its existing
  operation/status/outcome without another interpretation. A reused ID with
  different content is a conflict. An accepted duplicate is not a new request
  merely because its original revision is now old.
- A repeated generation POST returns the existing result or busy/uncertain
  status without dispatching again. Do not let an old completed operation
  reselect its proposal or alter the current baseline.
- Compare the supplied revision for a new submission, and revalidate the
  prepared operation's project/state/source binding before generation.
  Stale state fails before a model call; do not silently reinterpret the text.
- A running claim is not a queue lease. Browser abandonment, elapsed time,
  worker restart or lock release alone must not make it executable again.
  Uncertain publication/recording outcomes fail closed and need inspection.

This is cooperating local API protection, not distributed locking or protection
against arbitrary CLI writes into the web root. Detect conflicts with such
writes; do not advertise collaborative editing.

## HTTP contract and read model

Keep the existing create/list/detail/photo routes and exact loopback Host,
Origin/CORS and no-redirect/no-credential browser policy. Add narrowly scoped
conversation and immutable-preview routes. The following route names are the
proposed contract, not authority to expand the API:

| Route | Request / successful response |
|---|---|
| `GET /api/projects/<id>/conversation` | Current revision, projected messages, baseline/preview identity, pending interaction, live-enabled flag and latest unresolved operation/recovery status. |
| `POST /api/projects/<id>/conversation/requests` | Strict JSON: `request_id`, `prompt`, `revision`. Interpret one new submission; return its final result or a prepared operation. |
| `GET /api/projects/<id>/conversation/requests/<request_id>` | Read existing operation status/result without making model calls. |
| `POST /api/projects/<id>/conversation/requests/<request_id>/generate` | Claim and execute the stored prepared generation. Accept only the expected revision, not a client-supplied handoff or intent. |
| `GET /api/projects/<id>/proposals/<proposal_id>/preview` | Validated published PNG bytes; no regeneration, arbitrary file access or acceptance. |

Use strict bounded IDs (UUID request IDs and existing project/proposal rules).
JSON bodies are at most the existing 1 MiB JSON limit; decoded prompts retain
the existing nonempty/256 KiB UTF-8 limit. Reject duplicate JSON keys, unknown/coerced
fields and wrong content types before dispatch.

DTOs must explicitly distinguish final result kinds, prepared/running state,
known failure and uncertain outcome. Include stable operation/event/proposal
identities and an opaque revision, plus safe recovery capabilities/reasons.
Do not infer whether retry is safe from HTTP status alone. Use 201 for a newly
created interpretation operation, 200 for reads/completed or prepared generation
responses and recognized duplicate results; conflicts/busy/stale requests use
409 with the relevant safe operation identity where available. Application
timeouts use a structured 504; host/network failures may have no usable JSON.
Document the final DTOs and error codes in the API guide during implementation.

GETs are read-only: do not construct a recovery-writing conversation, create a
missing operation, repair records or initialize credentials. Validate published
records and immutable-preview identity using shared backend helpers. If a
snapshot changes during a read, retry that local read within its deadline or
return an explicit conflict; do not expose half-published state as success.
Preserve `no-store` and image `nosniff`; visible image-load errors are required.

After Send, the browser generates/retains one request ID for that submission.
Cancel listeners/timers and ignore late responses after unmount/navigation.
Never issue a generation POST from an obsolete interpretation callback.
On reload, the conversation read identifies unresolved work without relying
on browser storage or resubmitting its prompt.

## Deadlines and honest recovery

Retain the existing model-stage ceilings: interpretation **120 seconds**,
generation **180 seconds**, with validator corrections sharing the stage
deadline and generation sharing the remaining four-call attempt allowance.
Splitting HTTP calls must not reset that allowance or change CLI/replay limits.

Proposed initial web timing policy:

| Boundary | Interpretation | Generation |
|---|---|---|
| Existing model-stage budget | 120s | 180s |
| Application response envelope target | 150s | 210s |
| Browser stage-request deadline, including body parsing | 160s | 220s |

Keep ordinary JSON/status reads at 10s and project creation at 60s in the
browser. Configure an explicit 225s Functions execution ceiling as the outer
guard, below the documented [hosted HTTP response limit](https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale#timeout)
of 230s. The hosted load-balancer limit is not a claim about local Core Tools.
Verify the app-wide host setting preserves existing project-route behavior.

The application envelope reserves time for context/validation, rendering,
storage and response delivery; it is not extra model time. Check remaining
time around bounded stage work and before publication. Do not pretend that
an asyncio/browser timeout can forcibly stop synchronous rendering or storage.
If execution outlives the intended response envelope, or the host kills a
worker, report/reconcile uncertainty rather than promise cancellation or
rollback. Verify headroom with offline fixtures/controlled delays. If normal
supported inputs cannot fit, report the blocker instead of silently shortening
the model budget, raising host limits or adding background infrastructure.

| Observed state | Recovery policy |
|---|---|
| Interpretation prepared; generation definitely never claimed | The original still-active Send continues automatically. After reload/navigation interruption, require **Continue generation**, using the same operation and consumed correction allowance. |
| Stage still running | Display its saved phase. Read status; never dispatch another stage or duplicate the current one. |
| Response lost, backend actually completed | Read and display the recorded result/current baseline; do not retry or regenerate. |
| Confirmed stage failure/timeout with verified terminal state | Show the existing diagnostic/recovery meaning. Any retry is an explicit new, potentially paid conversation attempt using existing agent recovery semantics and a new request ID, not reuse of a consumed handoff. |
| Interrupted claim or publication/result-recording uncertainty | Show outcome unknown and block another paid mutation until resolved/inspected. Do not expire the claim into a retry or assert that the baseline is unchanged. |

Status reads may repeat on a modest bounded cadence while observing an active
operation (proposed 2s, no overlapping reads, at most 225s per observation
session). Then offer an explicit **Check status** action. These GETs are not
model retries. Stop observation on unmount or a terminal/uncertain state;
after a connectivity failure offer manual checking, not an endless loop.

No automatic paid retries, automatic restart recovery, stop/cancel-model
control, cross-stage atomic transaction or general crash-repair UI is included.
Interpretation may already have saved names. Preserve and report those effects;
do not roll them back because generation failed. Full recovery UX remains
018f, but these safety distinctions are required in the first integration.

## Runtime and dependency changes proposed for approval

Model access stays in Python through the existing `FoundryModel`, deployment,
keyless credential path and provider limits. Never put tokens, provider URLs
or credentials into browser requests, configuration or responses.

Add an explicit local launcher opt-in (proposed `.\api\start.ps1 -Live`);
without it, browsing/creation remains model-free and conversational dispatch
fails clearly before model access. Expose live availability in the read DTO
and show actionable setup information in the UI. Do not initialize credentials
on startup/GET or add an interactive sign-in flow. Preserve process-local
environment restoration, loopback binding and existing telemetry/storage rules.

The API environment currently contains only engine requirements plus Functions.
For live conversation it must reuse `requirements-agent.txt`, retaining
`azure-functions==1.26.0` and the existing agent dependency selections.
Propose replacing its root engine include with the root agent include and
restoring `api\.venv` from `api\requirements-dev.txt` after that manifest change.
No new frontend library, global tool, emulator, root-environment rebuild or
dependency upgrade is proposed. Implementation approval must cover this
project-local dependency restoration; drafting permits none.

Update the architecture map, API/UI READMEs and directly affected usage/testing
instructions after implementation. Keep the main README approachable and
phase accounting in the results record. Update related LESSONS references
only as needed; discuss any new lesson separately.

## Offline verification and usable-slice criteria

Use generated photos, fresh temporary roots, controlled model clients and
blocked external network access. No paid calls, credentials or provider
preflights are needed to prove the application/HTTP/UI state machine.

| Focus | Required evidence |
|---|---|
| Real workflow projection | Empty project, proposal, edit, question/answer, name acknowledgement/listing/forgetting/conflict confirmation and exact selection project to correct DTOs/UI without parsing model JSON in React. |
| Persistence | Refresh/reopen and a fresh backend process restore transcript, names, current preview and pending interaction; GETs do not mutate saved bytes or initialize model access. |
| Stage boundaries | One Send drives two real requests only when needed; phase/summary sequencing is truthful; non-generation results never call generation. A fresh view requires Continue for prepared work. |
| Duplicate/stale/concurrent requests | Same-ID resubmission, different payload under one ID, double generation, old revisions, cross-tab/cross-process mutations and old callbacks cannot cause duplicate model dispatch or baseline changes. |
| Failure windows | Lost interpretation/generation responses, claim-before-dispatch interruption, publication-before-result-recording interruption, storage errors, host/non-JSON failure and unknown outcomes never become automatic paid retries or false unchanged-baseline assurances. |
| Budgets and deadlines | Preserve four-call/correction accounting across HTTP and fresh objects; stage deadlines stay 120/180; browser deadlines cover response parsing; status observation is bounded and model-free. Test timeout cases with controlled time/delays, not paid induced failures. |
| Regression/UI | Preserve create/list/reopen/photos, separate demo, keyboard/narrow layout, image-load errors, late-response cleanup and CLI/replay behavior. Existing accepted/layout formats stay unchanged. |

Add focused cases in the existing application/API/frontend suites; reuse
existing helpers rather than duplicate the agent's capability suite. Run the
full existing root and separate API Python suites, frontend tests, lint and
build/type-check:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\api\.venv\Scripts\python.exe -m pytest -q -c .\api\pytest.ini .\tests\api
npm --prefix .\web test
npm --prefix .\web run lint
npm --prefix .\web run build
```

Verify actual loopback host/browser connectivity and real rendered-image
delivery, not only mocked UI tests. Use existing tools; no new end-to-end
framework is required. Do not claim physical-phone or cloud readiness.

## Proposed bounded real UI smoke trial

After the full offline gate is green, propose one small agent-driven trial
through the actual browser -> Functions -> existing agent -> renderer path.
This tests the new integration, not the original agent's breadth or resilience.
If approved with implementation, run it without an intermediate approval pause
while checks stay green; finish with the user's manual review.

Use one fresh session-artifact data root, one new web project and the four
repository London photos in their normal 1-4 order, at 1200x1800. Never use
`.collage-data-web`, CLI user roots or old trial projects. Start owned loopback
servers with that explicit root and stop them after the dependent checks.
Do not terminate unrelated processes or silently reuse an unverified server.

Send exactly these three ordinary messages, once each, inspecting every outcome:

1. `Make a simple collage using all four photos, with a light background, generous margins and rounded corners.`
2. `Make photo 2 a bit smaller. Leave everything else alone.`
3. `Remove the rounded corners from photo 2 only. Leave everything else alone.`

**Maximum: 12 model calls total** (three attempts, at most four each), including
internal corrections, failed dispatches and timeouts. Enforce one persistent
12-call ledger at actual backend `RequestLog.reserve` calls, using the existing
`call_budget` mechanism across both stage endpoints and host restart. A browser
counter or a context established only in the launching shell is insufficient.
Keep this single-project trial single-writer, with no other live submissions.
Document any narrow launcher/application budget configuration needed, and
reject missing/inconsistent trial configuration before model dispatch.

Between completed messages, reload/reopen and verify the saved transcript and
preview without extra model calls; restart the owned backend after the second
completed message and verify restoration before the third. Do not deliberately
interrupt live work or manufacture timeouts to test recovery.

Check initial generation/progress, a decrease in photo 2's authored width with
no unrelated edit, then removal of photo 2's rounding only. Confirm unchanged
accepted version, correct immutable previews, restored state and exact call
accounting. Capture browser screenshots and backend evidence; screenshots alone
are not proof of persistence or requested edits.

Any question, naming receipt, failure, timeout, interrupted execution, cap
exhaustion or unexpected result stops the entire trial for handoff. No guessed
answers, prompt tuning, failed-step retry, rerun project, replacement ledger,
extra scenario or renewed allowance is included. Internal validator corrections
remain the existing bounded behavior. Fix extraction/integration regressions
offline where in scope, but do not perform further live calls after a stop
without a new decision.

## Approval and handoff

The user's 2026-11-25 approval covers implementation, the described dependency
restoration and the three-message/12-call live allowance. Record actual verification and
accounting in `018e_results.md` only after execution produces evidence; no
results placeholder is needed.

Stop for the user's manual review/sign-off after the authorized work. Do not
close 018e on scripted success alone or begin 018f automatically. No Git writes,
global installs, original-photo edits or changes to pre-existing project/archive
data are authorized. Preserve the user's staging, history and branches.
