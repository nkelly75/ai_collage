# 017: Conversational photo identity memory

**Status:** Successfully completed and closed with the user's sign-off.
Implementation and the latest separately authorized replay-06 pass
are complete. After the assessment repair, fresh `p017-replay-06c` completed all
ten objectives, and the subsequently authorized full offline regression passed.
Human-led `p17-human-07` then exposed a numeric multi-mapping validation defect;
the separately authorized narrow offline repair and full regression passed.
The user's continuation now live-confirms that repair and reaches P012, including
listing, confirmed reassignment, forgetting and fresh re-learning. The trial
remains user-led; Copilot has not advanced it or made further live calls.
Earlier stopped passes remain preserved.
See [017 results](017_results.md). All live allowances are closed; further live
evaluation by Copilot requires separate authorization. This closes the bounded
phase, not general reliability or broader Phase 1; no merge is authorized.

## Purpose and boundaries

Remember clear user-supplied photo identities as a conversation evolves, without
requiring a separate "remember" ceremony. Make those identities easy to inspect,
correct and forget. Keep the metadata-only agent and deterministic rendering of
original photos.

[011](011_results.md) and [012](012-model-led-references-and-confirmed-names.md)
deliberately separated task-local bindings from explicitly approved lasting names.
The user-led [016 trial](016-user-led-natural-language-trial.md) exposed the UX
cost: a previously supplied identity could become unavailable after compaction.
The [016 evidence-handoff repair](016_results.md) fixed supporting citations;
the user then reached P009 with the requested Bridge-only stacking change.
It did not make all established identities durable. This brief deliberately
changes that memory policy rather than enlarging history windows.

Scope is **project-level photo identity labels**, not general facts, preferences,
image understanding, generated descriptions or semantic-search memory.
Reuse one authoritative identity mechanism and the existing interpretation stage.
No new model stage, dependency, service, package restructuring, timeout redesign,
layout tuning, renderer change or layout-format bump.

## Remembering and resolving

- Save a new, non-conflicting identity from clear user teaching, such as
  "photo 2 is breakfast" or "call photo 4 Daunt Books", without confirmation.
  Learning alone creates no proposal or accepted version.
- A resolved identity question also supplies lasting knowledge: after
  "Make breakfast smaller" / "Which photo is breakfast?" / "Photo 2",
  remember `breakfast = 2` and continue the entire original edit from its
  original source. No additional confirmation or model stage.
- A number in an unrelated answer is not teaching. Ambiguous, hypothetical or
  explicitly temporary wording must not install a project-wide identity.
  An unresolved identity requires clarification, not a tentative lasting guess.
- Model-inferred paraphrases may resolve wording, but must not accumulate as
  saved aliases. Multiple distinct user-established labels may identify one photo.
  Adding one does not remove another. Keep case/whitespace normalization and
  stable numeric photo IDs; repeating an unchanged assignment is idempotent.
- Generation uses the validated photo bindings, not a fresh identity decision.
  The model cannot infer photo contents from undisclosed visual information.
  Ordinary numbered edits and resolvable references gain no routine naming gate.

For example, with only `Tower Bridge = 1` saved, "bring the bridge to the front"
may resolve to photo 1 without saving `bridge`, asking for another name or
introducing a naming gate. Clarify if more than one photo plausibly matches.
Only explicit additional teaching, such as "also call photo 1 bridge", supplies
another lasting label. Preserve model-led reference handling, not a suffix
allow-list, generated alias store or separate synonym engine.

Learning is visible through a concise code-rendered acknowledgement alongside
the normal response, not an extra question. Record actual user evidence and its
task relationship, including the original label and subsequent clarification
answer when they are in different messages. Never fabricate a combined user
quote, model approval or user-confirmation receipt.

Interpretation remains fallible: structural provenance/ID checks cannot prove
the meaning of arbitrary language. This policy accepts the risk of a mistaken
initial assignment persisting, in exchange for less friction and explicit
inspection/correction. Do not rebuild a natural-language parser or introduce
confidence thresholds to pretend that risk has been eliminated.

## Friendly clarification and failure feedback

Preserve the user-friendly recovery contract from
[010h](010h-useful-recoverable-progress.md). New validation must not make users
understand receipt IDs, evidence schemas or hidden state to keep designing.
Ask ordinary identity questions only for genuine unresolved meaning; do not
request technical state updates as a workaround for an invalid model response.

Use the existing bounded internal correction allowance. If a recoverable request
still cannot be applied, give a concise explanation, the verified current
baseline, useful active-name reminders and permission to rephrase or request a
different change. No extra inference stage, diagnostic parser or troubleshooting
framework. Keep technical diagnostics in the saved evidence.
If memory changed but the collage did not, say both truthfully. Do not promise
unchanged state or routine recoverability for uncertain publication, damaged
records or integrity failures.

## Listing, correction and forgetting

| Request | Required behaviour |
|---|---|
| "What photo names do you know?" | Return every active saved label and photo ID, including multiple labels per photo, from application state. Say explicitly when there are none. No layout generation or identity-state mutation; normal audit recording remains allowed. |
| Establish an existing label against a different photo | Display the exact old/new assignment and pause that batch and any associated edit for confirmation. Never silently overwrite or use the conflicting candidate. |
| Approve/correct/reject that pending change | Reuse the current receipt/continuation mechanism: approval applies only the displayed batch; correction produces a revised receipt; rejection leaves prior memory/layout unchanged. |
| "Forget the name breakfast" | Remove that normalized active label and acknowledge it without an extra confirmation. Do not remove its photo, other labels or collage edits. Persist that the association must not be reused from old evidence. |
| Use the forgotten name later without establishing its identity again | Do not recover its old association from history. Ask for the photo identity if needed to continue. A fresh clear user statement or answer can establish the identity again. |

Natural language is the expected interface; no new slash-command language is
required. Interpretation may consume its normal call for inspection, forgetting
or confirmation, but listing/forgetting alone must never call layout generation.
Render memory responses from validated application state/operations, not invented
model prose. Listing remains read-only while a conflicting change is pending
and must not approve, discard or retarget that change.

Forget only the requested label, not every name for the same photo. Clarify an
ambiguous label rather than guessing. Forgetting must also work when a label
exists only in historical evidence and is not currently in the saved name table.
Repeated forgetting is idempotent and reports the actual state truthfully.

**Forgotten stays forgotten until the user establishes the identity again.**
Removing a row alone is insufficient: old raw messages, compact records,
supporting citations, retries or older proposal returns must not resurrect or
silently reuse the association. Preserve those audit records untouched; enforce
the current memory policy when using them. Re-establishment needs fresh user
identity evidence after forgetting, not merely another request mentioning the
label or a model citing an earlier statement.

Retain only the minimal current per-label forgotten status/provenance needed for
that rule within the same identity mechanism. This is not a second positive-name
store, a transcript blacklist service or a general memory framework.
Do not opportunistically save inferred alternative labels to bypass forgetting.

## Persistence, lifecycle and implementation boundary

Current code assumes every lasting name has an approved receipt. Replace that
assumption coherently: new automatic assignments and explicit forgetting need
truthful audit evidence; conflicting reassignments retain actual approval
evidence. Use a shared memory-application path rather than duplicate automatic
and approved stores/commit implementations.

Keep the existing single pending-batch model. If one operation contains a
conflict, hold the complete memory batch and associated edit until resolved;
do not apply harmless-looking additions or removals ahead of the decision.
Read-only inspection is not a new modifying task. Essential ambiguity must be
resolved before its dependent operation is applied.

Validate schema, known IDs, actual evidence, normalized label uniqueness,
numeric/exact-label conflicts, current receipt/state/source and history/state
consistency. Invalid interpretations must not write memory. Preserve explicit
failures for damaged records, interrupted writes or external state conflicts.
Do not weaken the audit checker to accept arbitrary name-state differences.

Once validated memory is saved, a later generation failure may leave it saved,
just as approved names can today. Say what was remembered/forgotten and that the
collage did not change; retain the original recoverable task/source. No proposal
or baseline advance before successful validated publication.

Memory belongs to the project, not to an individual proposal. Returning to an
older proposal or undoing collage edits must not roll memory back. Active names
and necessary forgotten-state metadata remain essential context across restart,
compaction and optional-history fitting. Keep the three-recent-task/twelve-compact-
record policy, supporting-citation repair and existing input-size guards.
If essential context cannot fit, fail explicitly instead of dropping memory.

Expected code boundary: `ai_collage\agent` models, interpretation prompt,
reference validation, conversation persistence/context, natural-language operation
dispatch and directly dependent task-history consumers; `cli\chat.py` presentation;
`evaluation` replay/assessment and focused tests.
Keep the engine independent of agent/CLI/evaluation code.

Version affected persisted agent/evaluation contracts explicitly. Conversation
records currently use 7, replay reports 8 and replay-step/assessment records 6;
bump only contracts actually affected and document the resulting versions.
Keep layout/project format 3, unaffected request/settings contracts and supported
deterministic recipes unchanged. Use fresh conversational/replay projects.
Reject unsupported old agent records clearly; no migrations, legacy loaders,
compatibility shims, automatic name backfill or in-place trial upgrades.
Existing projects, previews and sealed evidence remain untouched archives.

## Offline gates

Before editing, capture a fresh baseline of HEAD/branch, staging, working changes,
runtime, original photos, existing projects/trials and prior evidence. Integrate
the user's staged 016 repair without unstaging, overwriting or committing it.

Use the existing environment and network-blocking tests, with synthetic temporary
projects and controlled model responses. Cover:

- Explicit learning and unambiguous numeric clarification learning, including
  invalid-answer recovery, restart and continuation of the whole original edit.
  No extra confirmation/generation for memory-only operations.
- Multiple labels, unchanged repeats, full truthful listing and memory surviving
  both history-selection windows and optional-payload fitting.
- A casual `bridge` reference using saved `Tower Bridge` reaches the intended
  photo without another saved label or gate; competing plausible targets clarify.
- Conflicting batches, exact confirmation/revision/rejection, stale or absent
  receipts, independent-task replacement and pinned-source continuation.
- Forgetting active and historical-only labels; repeated/ambiguous forgetting;
  no resurrection from recent/compact/cited evidence, restart, retry or an older
  proposal; fresh explicit teaching/clarification can establish the label again.
- No writes from inferred synonyms, unresolved guesses or invalid evidence;
  forged/contradictory claims and damaged state fail explicitly.
- Memory-only operations leave recipe, preview, baseline and acceptance unchanged;
  saved memory remains truthful after generation failure without duplicate edits.
- Replay/assessment accurately record each memory operation, state transition,
  gate and supplemental reply; reject tampered evidence and false completion.
- Recoverable naming/validation failures retain friendly baseline/continuation
  feedback and valid pending tasks; saved memory plus failed generation is
  reported truthfully without exposing technical repair instructions.

Preserve deterministic layout, pixel/rendering, geometry, storage and original-
photo coverage. Adapt obsolete "all additions need confirmation" and "numeric
clarification never learns" cases to the new policy, documenting any retirements
by responsibility rather than maintaining old production paths for old tests.
Retain essential lifecycle, source, integrity, accounting and recovery coverage.
Run focused cases, then the full resulting offline suite.

Create and offline-check `examples\sequences\06_photo_identity_memory.json`
through the existing replay path. Add focused offline assessment of its required
memory/layout transitions; integrity-only completion is not sufficient.
Keep this a small replay-specific profile/check, not a generic assertion DSL,
new runner or autonomous answer agent. Offline-check existing sequence definitions
and dependent mocked replay/assessment cases; no live reruns of 01-05.

Update the current README/CLI guide, relevant examples and planning status to
describe the implemented policy and version boundaries. Do not rewrite historical
plans/results to make them appear to have used the new policy.

Before live execution, all offline gates must pass, the scoped diff must be
reviewed, preservation must pass, and no material integrity/scope issue may remain.
Record remaining responsibilities and added memory/forgetting machinery honestly:
fewer user gates, one identity mechanism and no new model stage are acceptance
criteria; fewer lines are not. Stop for discussion if these boundaries cannot
be met without broader redesign.

## Conditional automatic replay 06

Approval to execute this brief includes **one serial live pass**, after the
offline gates above, without a second approval pause at that boundary.
The user supplied that execution approval; the offline gates still precede
any service dispatch.

Use `gpt-5.4-mini`, **high interpretation / low generation**, the existing four
London photos in order Bridge 1, breakfast 2, Eye 3, Daunt Books 4, a 1200x1800
canvas and no cropping. Choose one unused project ID, suggested
`p017-replay-06`, before starting. Never overwrite an existing project.
Freeze the implementation/instructions, complete sequence, input hashes,
settings, expected transitions and budget before the first live dispatch.
Concrete primary prompts may be authored offline to express the following fixed
story; do not tune them after observing live behaviour.

**Keep the ten-step story below.** These are coverage objectives, not a demand
for flawless live completion before a human-led trial can be considered.
Flexibility remains in the already-scoped question/receipt replies and in honest
assessment of recoverable or partial outcomes, not extra primary prompts,
mid-run script changes, broader retries or a larger allowance.
Expected identity questions and reassignment confirmation are normal successful
conversation, not failures merely because they require an answer.

| Step | Fixed objective and expected evidence |
|---|---|
| 1 | Create a simple whole-photo collage using all four numbered photos, with no supplied content names. |
| 2 | Ask to shrink breakfast by 10%, keeping its centre and everything else unchanged. An identity question must precede the supplied photo-2 answer; then save `breakfast = 2` and continue that edit without a naming gate. |
| 3 | List names: breakfast maps to 2; no proposal, layout change or invented labels. |
| 4 | Establish the user-chosen label `favourite = 1`, without a confirmation or layout change. |
| 5 | Request `favourite = 4` instead. Review the old/new receipt and confirm only that intended reassignment; breakfast stays 2 and the collage is unchanged. |
| 6 | Reopen and shrink favourite by 10%, with its centre and everything else unchanged. The resolved/edit target must be photo 4, not the former photo 1. |
| 7 | Forget breakfast only. Favourite remains 4; no layout change. |
| 8 | Reopen and list names: favourite maps to 4, breakfast is absent, and the forgotten association remains inactive. |
| 9 | Ask to shrink breakfast by another 10%, keeping its centre and everything else unchanged. Old evidence must not supply photo 2: inspect the identity question and unchanged memory/layout before supplying a fresh photo-2 answer. That answer establishes breakfast again and continues the edit. |
| 10 | Reopen and list names: breakfast maps to 2 and favourite to 4, with no extra layout change. |

Use the existing replay `--answer` path and `--answer-origin copilot` for
supplemental replies; keep the scripted prompt and actual reply separate.
The runner still pauses at questions/receipts. Copilot reviews the saved gate
and supplies a permitted reply; do not add automatic approval inside the runner
or bypass its state/continuation checks. Advance serially with evidence inspection
at the required checkpoints rather than blindly running past them.

### Scoped flexibility and budget

Fix the permitted decisions, **not exact answer strings**. Copilot may:

- Answer relevant identity questions using only the supplied fixture identities
  and the story's deliberate `favourite` assignments.
- Rephrase or expand a misunderstood answer without changing its meaning.
- Approve a displayed batch only when every change matches the current intended
  operation; correct an incorrect candidate or reject it and explain why.

Unexpected wording is allowed. A new substantive decision, unsupported identity
or unrelated change is not. Do not approve arbitrary mappings to keep progressing.
Do not supply an identity before observing the required question in steps 2/9;
doing so would hide a failure of clarification/forgetting. A rejected/discarded
task is not a completed edit.

**One pass; 32 total model calls; at most six Copilot-authored supplemental
replies, all within that same call ceiling.** Keep the existing maximum of two
supplemental answer turns per scripted step; the six-reply total does not enlarge
it. Rephrasings, approvals, corrections and rejections all count as replies.
All provider calls, including validation corrections, failures and timeouts,
consume the shared call allowance. Existing per-attempt call/token/deadline guards
and reasoning settings remain unchanged.

Use one fresh pass-local `--call-budget` path with `--max-calls 32` on every live
invocation; preserve its reservations across resumes/answers. No unguarded calls,
allowance reset/replenishment, effort escalation, alternative model or reuse of
an older phase's unused budget. Six replies are not six extra four-call budgets
outside the ceiling. No separate live probes.

Stop on a service/terminal execution failure, failed required transition,
unresolvable or out-of-scope decision, exhausted reply allowance, budget exhaustion,
integrity conflict or uncertain interrupted dispatch. Normal in-attempt validation
correction and the scoped question/receipt handling above remain allowed.
No `--retry` of failed executions, code/prompt tuning, substitute project or
second pass. Further fixes or live evaluation after a stopped/failed pass need
separate authorization; preserve and report the evidence rather than weakening
the checks.

## Results, human handoff and guardrails

Write concise `017_results.md` with the actual contract changes, removed/retained
responsibilities, offline outcomes, preservation and replay evidence/accounting.
Record every intervention and its reason, calls by stage, known usage and
unknown-usage attempts, corrections, remaining budget and stop condition.
Distinguish clean completion, assisted recovery and incomplete/failure; extensive
help is not a clean-pass claim. Separate normal expected answers/confirmation
from interventions correcting misunderstandings; both still count toward the
six-reply allowance. Assisted recovery can demonstrate useful progress.
If a step cannot complete through the permitted handling, stop as specified
above and report partial coverage rather than forcing completion or claiming
the remaining objectives passed. Close unused allowance at the end of this pass.

Keep outcome categories distinct: corrupted state, unapproved conflicting writes,
broken forgetting protection or budget violations are substantive safeguard
failures, not cosmetic friction. A bounded clarification, corrected candidate
or reassuring terminal rejection need not make the entire implementation
worthless. Offline contract/safeguard tests must still pass before the live run;
this distinction does not weaken assertions or waive unresolved integrity risks.

Check saved active/forgotten memory and actual target bindings at each milestone,
including intermediate questions, not just final names or completion status.
Verify memory-only operations preserve baseline, recipes, PNGs and acceptance;
verify each resize changes only its intended photo as requested. Preserve all
request/context/response/answer evidence. Assess offline after execution without
more generation. No image or proposal is automatically accepted.

Update this brief and the planning index with the outcome, then stop for review.
A completed replay supports readiness for another **separately human-led trial**,
not phase sign-off or permission to start that trial on the user's behalf.
A partial replay neither automatically rules out nor establishes readiness:
review demonstrated progress, recovery quality and unresolved limitations with
the user. No automatic fix-and-rerun cycle or perfection requirement is added.
Do not continue or upgrade `p15-human-06`; the next human trial uses a fresh
project and separately agreed commands.

No Git writes: no staging, commits, branches, stash/reset, merges, pushes or PRs.
Work in the current checkout and preserve user changes/staging, original photos,
all pre-existing projects/accepted versions/trials and prior sealed evidence.
Keep scratch/baseline artifacts in the session workspace, not new repository
tracking files. No installs/downloads or dependency changes; report missing
prerequisites. No Foundry experiments, credential/network probes or cloud access
outside the single explicitly gated replay. Neither autopilot mode, a failing
test nor unused budget relaxes these boundaries.
