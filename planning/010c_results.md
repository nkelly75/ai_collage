# 010c results: Timeout recovery and reasoning-trial preparation

## Status

Implemented and verified offline under the user's approval of
[010c](010c-timeout-recovery-and-reasoning-trials.md). Closed and stopped for
review of the integrated 010 result. Implementation used zero live calls, with
no Git writes, dependency changes or reasoning experiment. A later authorized
replay stopped in interpretation; the surgical fix and separately authorized
passing replay are recorded below.

## Implemented

- Interpretation shares a 120-second deadline across its calls/correction;
  generation gets an independent shared 180-second deadline. Remaining time
  flows through provider/SDK waits and is checked before dispatch; nested waits
  and corrections do not renew it. Local rendering/publication stays outside
  the model-stage deadlines. Existing four-call/two-interpretation caps remain.
- Confirmed generation timeout before publication records a typed timeout
  outcome, reports the unchanged editing baseline and explains explicit
  continuation. The same assurance is not used for generic service or
  publication/I/O failures. Actual dispatched attempts remain recorded,
  including cancellation and unavailable usage.
- A typed interpretation `resume` action reuses the saved validated intent,
  original source and photo bindings rather than reconstructing them. Original
  task/answers survive restart and optional-history trimming; a repeated prompt,
  "try again" or repeated short answer can continue through the existing
  interpretation stage. Repeated timeouts stay in that logical task. A new
  independent request supersedes it. No automatic retry or extra model stage.
- Chat/replay accept `--generation-reasoning high|low`. High remains default;
  interpretation stays high. The outbound gate verifies the selected effort,
  attempts record actual settings/remaining time, and replay records its
  candidate and rejects mismatched resume. Offline assessment checks candidate
  consistency. No live high/low comparison or default change.
- A small optional conversation callback supplies validated action/source/target
  progress and generation-start notifications. Chat prints these promptly;
  corrections are not announced as settled intents, and questions, naming and
  exact returns never announce generation. No progress is added to model context,
  authoritative event records or machine-readable replay output.
- Chat usage and `/status` now show readable project-wide **Known usage**.
  Missing/partially missing usage shows affected counts/attempt IDs and an
  incomplete-total warning. Machine-readable summary fields are unchanged;
  unavailable usage is neither estimated nor treated as free.

Conversation state, proposals, events, acceptance intents, replay reports/steps
and assessments now use **record version 5**. Request attempts use **version 2**
for stage/reasoning/deadline evidence. Unsupported older records are rejected,
not migrated or reinterpreted. Layout/project format remains **3**; sequence,
controls, preferences and optional call-budget records retain their versions.
Use fresh conversation/replay projects; older projects and PNGs remain archives.

## Offline evidence

- Final full suite: **490 passed** in 265.62 seconds with
  `.venv\Scripts\python.exe -m pytest -q --tb=short`. Tests block application
  networking; provider integration uses mocked HTTP and deadlines use controlled
  responses/simulated elapsed time rather than waiting for real deadlines.
- New cases cover shared/partially consumed deadlines, no dispatch after expiry,
  confirmed transport timeouts and unknown usage, recovery after clarification/
  restart, repeated timeouts, older-source return-and-edit, supersession,
  validated progress ordering/non-generation outcomes, readable partial usage,
  outgoing reasoning settings, replay candidate mismatches/tampering, and replay
  timeout retry with the original short answer. Existing 010a/010b cases pass.
- The first affected run had 194 passes and five assertion/diagnostic mismatches:
  four new expectations omitted the existing nullable accepted-version field;
  one existing diagnostic assertion required distinguishing reasoning mismatch
  from instruction mismatch. After those fixes, the focused run passed 32 cases;
  further deadline/terminal cases are included in the final full suite.
  No blocker exhausted the three-unsuccessful-cycle limit; no requirements,
  accounting safeguards or service limits were relaxed to obtain a pass.
- Before/after public CLI rendering of `examples\emma_tilted_2x3.json` in fresh
  isolated projects preserved the recipe, geometry and decoded RGB pixels.
  Pixel SHA-256:
  `b01a65a9203b7f943c9dff43ff7bb4fda88e05e84c98a7e8a33654fc0e40adc0`.
- All **975 pre-existing photo/runtime files**, original staged entries, HEAD
  and branch were unchanged in the preservation comparison.

Session evidence: `files\010c-preservation.json`,
`files\010c-verification-result.json` and `files\010c-verification.py`;
isolated deterministic projects are in `files\010c-before-data`,
`files\010c-after-data` and `files\010c-final-data`.

## Authorized live sanity follow-up and collective-reference correction

One separately authorized high-reasoning run of
`examples\sequences\01_dark_portrait_adjustments.json`, in fresh project
`p010c-dark-portrait-01`, stopped on the initial message after two interpretation
calls (one correction). No generation, proposal, timeout or acceptance occurred;
the remaining three messages were not run. Offline assessment correctly reports
an incomplete replay, not a pass. Known usage: 7,819 input / 4,399 output tokens,
none unknown; elapsed time 45.9 seconds. Staging, HEAD and branch were unchanged.

The initial intent invented literal references to photos 1, 3 and 4. Its
correction instead assigned known photo IDs to "the others" using unresolved
`unknown` evidence. Both representations violated the individual-reference
contract; the user's comparison itself was clear.

The user authorized a surgical repair: clarify in interpretation instructions
that collective wording stays in the complete task passed to generation, while
`references` binds only individually identified photos. Correction feedback now
explains that repair. Identity validation, schemas, record versions, call limits
and clarification rules are unchanged; no group parser or new inference was added.
Both observed invalid representations have controlled correction coverage;
the focused grounding/provider/prompt/replay checks passed **38 tests** offline.

Preserved evidence:
`files\010c-live-sanity-data\users\local-dev\projects\p010c-dark-portrait-01`,
including `replay\report.json`, `replay\assessments\0001.json` and both raw
interpretation events. The failed run remains untouched.

The user then separately authorized one fresh post-fix run,
`p010c-dark-portrait-02`. All four steps and the offline
`dark-portrait-adjustments` assessment passed, including integrity and reopening.
It used **8 calls**, with no correction, clarification, timeout or acceptance.
The initial intent bound only "photo 2", retaining the complete comparison.
Follow-up edits changed only photo 2 width (0.23 to 0.21), removed borders, then
zeroed rotations. Message durations: 71.8, 17.7, 18.1 and 17.4 seconds.
Known usage: **46,177 input / 14,369 output tokens**, none unknown.
Staging, HEAD and branch were unchanged. Evidence is alongside the failed run
under `p010c-dark-portrait-02`, including `replay\report.json` and
`replay\assessments\0001.json`. This sanity pass is not human sign-off or a live
timeout/reasoning comparison; the allowance is closed.

## Authorized landscape sanity follow-up

A separately authorized high-reasoning run of
`examples\sequences\02_landscape_staggered_adjustments.json`, in fresh project
`p010c-landscape-01`, generated its initial proposal without correction; that
step passed offline integrity assessment. The swap then exhausted its two
interpretation attempts: both responses correctly identified photos 1 and 4,
but quoted normalized singular "photo 1"/"photo 4" rather than literal text from
"photos 1 and 4". Exact quote validation rejected them before generation.
The later two messages were not run; the overall replay is incomplete, not a pass.

The run used **4 calls**, with one unsuccessful interpretation correction,
no timeout or acceptance. Initial/swap durations: 77.8/15.7 seconds.
Known usage: **19,317 input / 13,450 output tokens**, none unknown.
P001 remains the working baseline. Staging, HEAD and branch were unchanged.
No automatic repair, explicit retry or additional live call followed.
Evidence is under `files\010c-live-sanity-data\users\local-dev\projects\p010c-landscape-01`,
including raw events `000003.json`/`000004.json` and the incomplete integrity
assessment. This exposes another ordinary-wording/contract mismatch, not genuine
ambiguity about the user's requested photo identities. The allowance is closed.

The user authorized a bounded grounding fix and one fresh rerun. Numbered
references can now use normalized singular text when their IDs appear in an
explicit photo/image/picture-number list. Literal-name/history checks and
project-ID validation remain; unrelated quantities, numeric fragments and
decimal values do not supply this new evidence. No schema/version change or
extra inference stage. Focused offline grounding/provider/prompt/replay checks
passed **49 tests**, including the observed singular/plural mismatch and
negative identity cases.

The fresh high-reasoning run `p010c-landscape-02` completed all four steps and
passed offline integrity assessment: **8 calls**, no corrections, questions,
timeouts or acceptance. The formerly rejected normalized swap references were
accepted. Actual differences confirm an exact centre-position swap of photos
1/4 with unchanged sizes/style; photo 2 then moved right toward photo 3 and
shrunk (width 0.145 to 0.135); finally only photo 3's corner radius changed
(12 to 0). No unrelated fields changed. Initial metadata places larger photo 3
on the right and the other three staggered down the left on a light background;
subjective composition remains unassessed.

Message durations: 72.1, 20.5, 28.2 and 18.6 seconds.
Known usage: **47,884 input / 17,059 output tokens**, none unknown.
Staging, HEAD and branch were unchanged. Evidence is alongside the failed run
under `p010c-landscape-02`, including `replay\report.json` and
`replay\assessments\0001.json`. The separate rerun allowance is closed.

## Shared number-list matching for descriptive returns

The user authorized reusing the same explicit photo-number list helper in
descriptive history matching, replacing its singular-only scan. Retrieval and
navigation evidence now consistently recognize lists such as "photos 1 and 4"
and exclude changes involving only unrelated photos. Learned-name matching,
source/count evidence and competing-match confirmation rules are unchanged.
Focused history/navigation and numbered-reference checks passed **40 tests**
offline, including plural-list exclusion and rejection of an unconfirmed
competing destination. No record/schema changes or live calls were needed.

## Limitations and next boundary

Offline checks establish orchestration/contracts, not live wording reliability,
latency, composition quality or user sign-off. Interpretation still decides
whether a message continues or replaces the failed task; no semantic search or
special-case intent campaign was added. Essential context can still exceed the
unchanged input bound and fail explicitly. Cancellation stops local waiting, not
a promise that remote work or billing stopped; unavailable usage stays unknown.

Review the integrated 010 result before separately authorizing fresh-project
human trials, any live sanity replay or a controlled reasoning comparison.
Retain the umbrella's useful/recoverable-progress watchpoint rather than
overfitting awkward phrases or starting another unapproved stage.
