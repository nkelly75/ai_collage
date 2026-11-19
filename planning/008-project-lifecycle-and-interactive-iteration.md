# 008: Project lifecycle and interactive iteration

**Status: Complete and closed.** Implementation, offline verification, and the
separately authorized landscape smoke check are complete; see
[008_results.md](008_results.md) for evidence and limitations. The unused
smoke-check allowance is closed. This increment enables a natural-language
trial but does not authorize or include that human trial.
Vision ideas are separate in [007](007-image-understanding-and-interactive-design.md).

## Goal and scope

Provide the minimum support for reacting naturally to generated layouts, without
requiring the user to learn slash commands. Preserve ordinary targeted edits
and add the three behaviours below. Do not design a larger lifecycle system.

Acceptance is not completion. Saving/finalizing, new acceptance terminology,
branching, a UI and vision are outside this increment. Existing slash commands
may remain available for debugging/compatibility, but are not the trial workflow
or the internal action contract.

## Agreed natural-language behaviour

| Situation | Expected behaviour |
|---|---|
| "Make photo 3 smaller" | Edit the proposal just shown, preserving unrelated choices |
| "I hate that, try again" after an initial composition | Produce a fresh arrangement, retaining explicit user requirements |
| "I hate that, try again" after a targeted edit | Retry that edit from the proposal preceding the unsuccessful edit, rather than redesigning everything |
| "Go back to the first one" | Show and select that exact preserved proposal as the next editing baseline; wait for the next message |
| "Go back to the first one and make photo 2 smaller" | Generate an edit using that proposal as its source, in the same turn |
| An ambiguous reference such as "the better one" | Ask a short clarification only when the intended proposal is unclear |

### Fresh arrangement

Retain explicit requirements such as a dark background or an emphasized photo
unless the user changes them. Keep the last layout available as a reference,
with an explicit instruction to try something substantially different; do not
silently omit it or treat it as the arrangement to edit. Discard its authority
as the working composition, not the saved evidence or the user's requirements.

### Retry an edit

Use the preceding proposal as the source, retain the edit being attempted and
incorporate the user's new feedback. The disliked result can inform what to
avoid, but is not the baseline to keep modifying. Context distinguishes retrying
an edit from rejecting an initial composition. This is a new user-requested
design attempt, not an automatic retry of a failed service request.

### Return to an earlier proposal

Select and display the existing result without generating a variation or
rerendering it. Do not require acceptance or create an accepted version just
to select a baseline. No confirmation is needed when the reference is clear.
Later edits start from the selected proposal, not whichever was generated most
recently. Preserve all proposals/history rather than deleting disliked results.

## Implementation approach: interpret, then act

Currently every valid published proposal becomes the editing baseline.
Acceptance saves a version and selects its proposal; conversation can continue.
However, displaying a proposal does not select it, and local ratings neither
change the baseline nor enter model context.

Use the existing provider/model in two explicitly identified stages, with separate
prompts and response schemas. No extra agent framework, tools or classifier service.
Normal edits use two calls; selection or a clarification uses one. Questions
belong only to interpretation; generation returns only a layout recipe.

### 1. Interpret the user's request

Add a short `ai_collage\prompts\request-intent.md` prompt. Its context contains the
real user request/history, current baseline identity, and a compact catalogue of
published proposal IDs, their originating requests and source relationships.
Do not send image content or observer notes. Resolve catalogue entries from saved,
validated application records, not arbitrary IDs appearing in model text.

The strict interpretation response has exactly one action and its applicable
fields; it cannot contain a recipe, acceptance instruction or executable command:

| Action | Model supplies | Application resolves |
|---|---|---|
| `edit` | Source: current baseline or a published proposal ID | Exact source recipe/geometry; the latter supports "go back and edit" |
| `fresh` | No edit source | No editing baseline; last shown working proposal as an avoid-repeating reference |
| `retry` | The published proposal being retried | Its original task and actual edit source; a composition retry becomes fresh generation |
| `select` | A published proposal ID | Exact existing recipe/preview and the baseline to select |
| `question` | One short clarification | Display it without changing the baseline |

Use the existing short-question limit. Validate IDs, source relationships and
current control compatibility in application code. Never default an invalid or
ambiguous selection to the newest proposal. A valid-looking ID is not sufficient
evidence that a natural-language reference was understood; prompt for clarification
when the intended reference is unclear.

### 2. Execute the validated intent

For `edit`, `fresh` or `retry`, call the existing layout generator with a resolved
turn-specific context. Its strict response is the layout recipe itself
(`InputLayout`), without a proposal/question wrapper or lifecycle action.
The application publishes that recipe as a proposal after validation/rendering.
Remove the old generation reply union and its question-handling path; do not
keep a second generation contract for compatibility.

Supply the action, original user request, full real conversation history and
trusted controls, plus:

- **Edit:** the selected source's recipe/geometry as `editing_baseline` /
  `baseline_geometry`, not the most recently generated proposal by default.
- **Fresh:** null editing baseline/geometry; the previous recipe in a clearly
  separate reference-to-avoid field. Preserve explicit requirements from the
  user's history, without promoting old model choices to user requirements.
- **Retry:** the original task being retried, its original source, and the disliked
  result separately as feedback/reference. Repeated retries retain that originating
  task and source rather than treating "try again" itself as the original edit.

Resolve these fields from saved records after interpretation; do not ask the
layout generator to find the authoritative source again. A model-written task
summary must not replace the real requests or override trusted controls.

Do not select a different working baseline before generation succeeds. Validate,
render and publish as today, then make the new proposal the baseline. Record its
actual source, even if older than the latest proposal; a fresh composition has no
edit parent. Generation failure leaves the working baseline intact.

Interpretation handles ambiguity about the user's intent. Geometry infeasibility
may emerge later: use the existing bounded validation-feedback corrections,
then report an explicit failure if no valid recipe is produced. Do not let the
generator ask questions, relax the task/controls, or silently return to
interpretation. The user's next message goes through interpretation with the
failure available in history. A question-shaped generation response is invalid,
not a clarification to display or permission for another loop.

For `select`, validate the preserved proposal/preview, record the selection and
update the baseline, then display the existing PNG. Do not generate, rerender,
accept or create a new proposal/version. A compound return-and-edit goes directly
through `edit`; failure must not silently perform half of that request.

Neither selection nor editing may silently change canvas/cropping controls.
Incompatible sources require an explicit explanation/clarification, not a control
override. Keep the existing stale-state and artifact-integrity checks.

### 3. Persist only the provenance needed

Reuse `ConversationState.baseline` for the selected working proposal. Add typed,
turn-linked history/provenance sufficient to identify the interpreted action,
resolved source, originating task and any rejected reference. Record selection
as a distinct outcome, not acceptance or a newly generated proposal.

Persist successful provenance so return/retry works after restarting chat.
Questions, invalid replies and service failures remain honest history; they must
not become proposal sources or overwrite a validated intent during geometry
correction. Keep all saved proposals and accepted versions immutable.

Prefer one current conversation/proposal/history contract, not optional legacy
fields or inferred old lineage merely for compatibility. Version affected
persistent records when a breaking change requires it; update their producers,
consumers, tests and docs together. New-format sessions can use that complete
provenance directly. Preserve old sessions/evidence as untouched archives and
reject unsupported versions clearly, without loading a legacy conversation path,
rewriting archives or inventing source relationships.

Layout recipes and agent/conversation records are different contracts. This
design does not change recipe fields or rendering, so layout format 3 can remain
unchanged; no version 4 is currently required. A necessary agent-record version
bump does not imply a layout-format bump. An initial accepted layout in supported
formats remains a valid current edit source. No migration, separate requirements
database or branching system.

## Integration and call limits

| Component | Required change |
|---|---|
| `agent_models.py` | Strict intent/action records and persisted provenance; typed application result distinguishing proposal, selection and interpretation question; remove the old generation reply union |
| `agent_provider.py` and prompts | Intent schema versus recipe-only generation schema through the existing guarded provider; generation instructions follow the resolved intent |
| `conversation.py` | Bounded two-stage orchestration, source resolution, selection and publication with correct provenance |
| `chat.py` | Consume typed outcomes; display whether a layout was generated or restored, or a question asked; no slash commands required for these behaviours |
| `replay.py` / `assess.py` | Capture both stages and actual source identities; distinguish selection from generation using the current record contract, without a legacy execution/assessment path |
| Existing tests and CLI guide | Cover the new path, call accounting, resume and observer-feedback separation |

Keep the current **four actual model calls per user-message attempt**, shared
across both stages and validation corrections, not four per stage. Allow at most two
interpretation attempts, leaving the remaining allowance for generation if needed.
After a valid intent, geometry corrections retain it and its source; they do not
re-run interpretation. Exhaustion stops with an explicit error and unchanged
working baseline. Every dispatched call uses the existing request log and any
optional outer cap. Service failures still stop immediately without automatic retry.

An explicitly initiated retry is a new bounded message attempt, not an extension
of the failed attempt's correction loop. It must remain visible in the evidence
and consume the same phase-wide allowance; restarting a command or project does
not reset that allowance. No automatic application/SDK retry is added.

Keep the current deployment/reasoning, token bounds (50,000 conservative input,
25,000 output including reasoning per call), 120-second request timeout, no-tools
and no-hosted-history/storage rules. These limits apply independently to each
stage; unused tokens/calls are not a target to spend.
Capture stage identities in recorded contexts/usage, and
include both prompts in replay instruction identity checks so a change to either
cannot silently pass resume validation.

Do not build another replay runner or vision judge. Retain the existing fixed
sequences' user messages and behavioural checks; move their fixtures/consumers to
the current response/record contracts. Historical assessment evidence remains
an untouched record, not a requirement for continued executable compatibility.
New lifecycle replay outcomes must
record baseline/source changes truthfully: selecting an existing proposal is not
a new proposal, and a fresh/older-source generation is not a linear edit of the
previous output. Update affected integrity checks without weakening them or
rewriting old artifacts. Unsupported versions and changed instruction identities
must stop resume explicitly rather than being bypassed by compatibility logic.

Replay adaptation is required implementation work, not an optional repair left
until the live check. The current runner assumes a string reply matched to the
last history event, advances only for a newly generated proposal, and computes
changes against the previous working baseline. Its assessor assumes a linear
parent chain. Replace those assumptions with typed outcomes, successful selection
as a completed message, explicit actual source identities and source-relative
edit differences. Keep the prior displayed baseline distinguishable from the
edit source. Selection must not appear as a generated proposal or layout edit.
Capture both stages and count actual calls/corrections without mistaking the
extra interpretation call for a correction. Update prompt identity and
resume/integrity checks together; no legacy replay path is required.

Support an explicit recorded clarification-answer continuation in the existing
replay/conversation path. A question leaves the scripted step pending and its
baseline unchanged; an answer is a new user-message attempt linked to that step
and question, with the original request retained. Advance the script only when
that request completes with a proposal or selection, not when the question is
asked or answered. Preserve the original sequence snapshot and record supplemental
answer text/origin separately. Do not use manual chat followed by bypassed resume
checks, silently replace the scripted prompt, or build a second runner.

## Implementation order and completion checks

1. Before code changes, render `examples\emma_tilted_2x3.json` offline in a fresh
   isolated project and preserve a reference PNG and source/recipe hashes for
   the late deterministic check. Do not reuse or alter an archived project.
2. Add strict stage/action/result records and stage-aware provider wiring.
3. Implement source resolution, bounded orchestration and durable selection/
   generation provenance in the existing conversation service.
4. Update terminal output and directly dependent replay/assessment handling.
5. Add focused offline checks, run the full suite, and update the CLI guide.
   Record implementation results/limitations separately in `008_results.md`.
6. Complete the deterministic example sanity check below, as part of offline
   implementation completion.
7. After separate bounded live authorization, run the landscape smoke check
   below and record its outcome before starting a user-led trial.

Use existing fake-model and mocked-transport patterns; no real service calls.
Focused cases must demonstrate:

- Ordinary edit, fresh arrangement and both kinds of retry receive the correct
  source/task/reference; repeated retries do not drift to the rejected result.
- Exact return, next edit after return, and combined return-and-edit; selection
  preserves PNG bytes and accepted versions and makes no generation call.
- Clarification and invalid/unknown references do not change the baseline;
  clarification answers retain the real preceding question/request.
- The generator accepts only recipes; question/action envelopes are invalid.
  Failed generation preserves the baseline, reports failure and does not secretly
  call interpretation again.
- Restart preserves selected source and retry provenance for the current format;
  unsupported record versions fail clearly without touching archived data.
  Failures/stale state cannot partially select or publish.
- The four-call per-attempt cap spans both stages, all dispatches are counted,
  service errors do not automatically retry, and local-only mode still makes no
  model calls. Explicit retry/resume and fresh projects share the same outer
  counter; failed/timed-out calls are not refunded and exhaustion blocks dispatch.
- Replay clarification/answer continuation retains the question, original task
  and answer provenance, consumes the same outer budget, and advances the pending
  step exactly once only on successful completion. Restart and assessment
  distinguish assisted completion from an unanswered or uninterrupted step.
- Existing rendering, acceptance fidelity and replay/assessment regressions pass;
  captures and instruction identities cover both stages.

Use `.\.venv\Scripts\python.exe -m pytest -q .\tests` for final offline regression.
Offline success proves state/context/contract handling with controlled responses,
not that the live model reliably understands every phrase or designs differently.

### Late deterministic sanity check

Use `examples\emma_tilted_2x3.json` unchanged, with the documented import order:
Bridge 1, breakfast 2, London Eye 3, bookshop 4. In a fresh isolated project,
apply the recipe and reopen/rerender its accepted snapshot through the public
CLI. Confirm the 1200x1800 output and saved recipe/geometry preserve the mixed
whole/cover modes, crop pan/zoom, white borders, rounded corners, centre-based
tilts and back-to-front order. Compare decoded output pixels against the
pre-change reference and the rerender in the same environment, and inspect the
PNG for visible regressions. Rerender must not create another accepted version.
Preserve the PNG paths and comparison outcome in `008_results.md`; original
photos, recipe and pre-existing project data remain unchanged.

### Late landscape smoke check (separately gated)

First validate `examples\sequences\02_landscape_staggered_adjustments.json`
offline with `--check`, and exercise its four messages through the updated
runner with controlled fake-model responses in offline tests. This checks runner
integration, not real-model understanding, and does not replace the live replay.

For the later live smoke check, start with one fresh-project run of those same
four messages. Two-stage execution normally needs eight calls. The agreed budget
proposal is **32 actual calls total for this live phase**, including useful
recovery attempts, while retaining the four-call per-message-attempt cap.
This is a proposed new allowance for later execution approval, not authorization
or reuse of any closed 006 allowance.

Use the existing durable outer call guard, with one fresh budget file and a
32-call ceiling, for every live invocation in this phase. Run sequentially;
projects, resumes, targeted reruns and replacement runs after fixes all share
that file. Reserve before dispatch as today; failed requests and timeouts consume
calls, unknown usage stays unknown, and no restart/refund/reset renews the cap.
Offline implementation, tests, rendering and assessment consume none of it.
Keep existing per-call token/time limits; no new token-budget subsystem is needed.

Within the proposed allowance:

- Allow small, in-scope code or prompt fixes for observed defects, with relevant
  offline verification before further live calls. Preserve the failing evidence
  and record the reason for each fix/rerun. This is not permission for new
  capabilities, aesthetic tuning or repeatability rounds.
- Retry only the affected work when safe. If code, prompts or record identities
  invalidate resume, use a fresh project under the same counter rather than
  bypassing integrity checks. Any claimed complete post-fix replay must have
  coherent evidence under the resulting candidate, not stitched pre/post-fix
  outputs presented as one run.
- A service failure stops its invocation. After inspecting durable request and
  replay evidence, allow one deliberate retry of an apparently transient
  connection failure, provided no local request remains in flight and state is safe.
  Do not retry an uncertain interrupted request blindly; authentication, safety
  or integrity blockers stop live execution.
- A model clarification pauses the affected replay step, not the overall effort.
  Copilot may give a safe, sensible answer grounded in the script, saved proposal
  identities and established requirements, or choose a modest interpretation
  already permitted by the request (for example, how much "a bit smaller" means).
  Do not invent personal preferences, change the requested task/controls, supply
  a corrected recipe/geometry, or feed observer notes into the agent as an answer.
  If answering requires a genuinely new user decision, leave that step blocked
  and report it; continue other safe authorized work where possible.
- Record each such answer verbatim as Copilot-authored assistance, linked to the
  model's question and original step. Use the recorded replay continuation above;
  each answer gets the normal four-call per-attempt limit and consumes the same
  shared 32-call allowance. Allow at most two clarification-answer turns per
  scripted step; a repeated question without progress also triggers the existing
  non-progress stop. These are visible supplemental turns, not service retries.
- Stop recovery of the same blocker after two successive recovery attempts
  without demonstrable progress, such as a previously blocked step completing
  or a verified underlying defect being fixed. Unchanged failures do not justify
  consuming the remaining budget. Report a material blocker or exhausted cap
  rather than silently broadening scope or seeking a clean result indefinitely.
- Stop live spending when the smoke check succeeds. Record unused allowance;
  it does not authorize extra experiments or the subsequent human trial.

Capture both stages, usage, recipes and previews; run the updated offline
integrity assessor on that new evidence. Separately inspect the requested
behaviour: photo 3 emphasized on the right, the exact authored-centre swap of
photos 1 and 4 without size/style changes, photo 2 smaller and closer to photo 3,
and removal of photo 3's rounded corners without unrelated edits. Integrity
alone is not evidence that these requests succeeded. Report visual composition
and semantic failures honestly; do not broaden this into an aesthetic benchmark.
No automatic acceptance or hidden service retry. Clarifications use only the
bounded, recorded answer policy above; an interruption requires evidence inspection.
If safe execution can continue after a semantic/visual failure, capture subsequent
fixed messages too rather than discarding useful evidence; do not mark the failed
edit as successful. Apply the bounded recovery rules above where appropriate.
Record completed/blocked steps, failed attempts, fixes, actual consumption and
unknown usage in `008_results.md`, even if the full check cannot be completed.
Report clarification-assisted completion explicitly, including the additional
turns/calls; do not describe it as an uninterrupted four-message success or proof
that the original script needed no help.

## Authorization and exclusions

The user separately authorized the late landscape smoke check on 2026-11-19
after offline implementation. It completed using 8/32 calls; the unused allowance
is closed, not available for additional evaluation. The proposed rules above
record that pass's scope and guardrails, not a standing allowance.
Offline tests cannot establish real-model intent recognition quality, and one
live smoke check is not a general reliability claim.
Agree a separate bounded user-led trial after the enabling changes and review
of these sanity-check results. That is the intended next step, not a guarantee
of composition quality or broad language reliability.
The proposed feedback separation is ordinary
natural-language interaction in the application terminal, with observations to
Copilot in this conversation. Observer notes must not be forwarded into the
collage agent's context or used for undisclosed mid-trial coaching.

Keep the existing Git/data protections and request limits. No automatic
acceptance, deletion, hidden service retries or extra model calls outside the
agreed execution scope. No Git writes or changes to pre-existing trial data.
The user authorized implementation/offline checks and subsequently this one
bounded live smoke check, not human trials or additional model experiments.
Later increments can handle additional trial needs.
