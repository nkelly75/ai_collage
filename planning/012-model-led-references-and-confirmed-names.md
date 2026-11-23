# 012: Model-led references and confirmed names

**Status:** Successfully completed and closed after offline verification,
separately authorized replay follow-ups and the user-led trial.
See [012 results](012_results.md) for implementation evidence and
[trial 05 / phase closeout](012_trial05_results.md) for the user's sign-off.
Basis: [011 results](011_results.md), including post-review clarifications.
The execution requirements below retain the original approved scope.
No merges, refactoring or further live trials are authorized by this closeout.

## Aim and scope

Keep separate interpretation and layout stages. Let interpretation use the
model's language capabilities over supplied labels and task evidence; keep code
authoritative over real IDs, state, source selection, publication and acceptance.
Preserve original-photo rendering and the generally successful layout behaviour.

Aim for simpler deterministic interpretation with fewer niche language rules.
This is a design goal, not a required reduction in lines. Assess the entire
result, including prompts and confirmation UX; do not replace a phrase-rule
catalogue with a large prompt, parallel mechanisms or a new framework.

Implement task-local bindings and explicitly confirmed durable labels. Update
directly dependent contracts, context, chat, replay/assessment, tests and current
documentation together. No layout tuning, reasoning/model changes, general
navigation redesign, package reorganisation, vision or semantic-search service.

## Binding and memory policy

Interpretation receives confirmed label-to-ID mappings and bounded real task
evidence. It resolves wording, contextual references and genuine uncertainty.
The model cannot see photos or guess their content. Resolved IDs remain
authoritative for generation; generation must not reinterpret the chosen identity.

Remove stored generated aliases and the deterministic suffix/wrapper/pronoun
allow-lists that independently decide whether ordinary wording is acceptable.
Retain small structural checks: valid IDs, genuine quoted reference/evidence
when supplied, contradictory duplicate bindings and straightforward numeric/
exact-label conflicts. Case/whitespace normalization and numeric tokens such as
`01` meaning 1 are appropriate; rebuilding a natural-language parser is not.
Remove unnecessary reference-source bookkeeping rather than preserving it through
compatibility paths. An inferred binding is not proof of semantic correctness.

Several distinct confirmed labels may refer to one photo. Adding a label does
not remove existing labels. An existing normalized label cannot silently change
IDs; proposed replacements show the exact previous and new assignments.
Repeating an unchanged confirmed mapping needs no new write or confirmation.

Distinguish explicit teaching ("map Daunt Books to photo 4", "Photo 4 is the one
with the sand castle") from a task-local answer ("Photo 3" after an identity
question). Interpretation proposes durable changes only for explicit teaching.
Inferred spelling variations, synonyms and clarification bindings are not
automatically promoted into persistent labels.

Clear layout edits using photo numbers or resolvable existing names proceed
directly. Neither every interpretation nor every proposal needs approval.
The additional gate applies only to proposed new/changed durable mappings;
essential identity questions remain possible when a target is genuinely unclear.

Task-local bindings belong to the original task and survive its corrections,
clarification and restart. Later requests can use visible recent evidence, but
an unconfirmed label is not durable memory and may require clarification once
that evidence is unavailable. Do not resolve competing plausible targets by recency
alone or require users to invent unique labels: photo numbers always remain usable.

## One durable-name confirmation gate

Use one code-owned pending batch tied to the originating task, exact candidate
mappings and applicable source/state. Display every addition/replacement in a
compact code-rendered receipt, not model-written approval prose.

**Pause durable writes and any associated edit until approval.** There is no
edit-first path, later name commit or implicit approval through image acceptance.
Naming-only requests use the same gate and make no layout proposal.

Natural language is the primary interaction, not a new slash-command language.
After displaying its exact receipt, ask for confirmation; ordinary replies such
as "Yes, remember those" or "No, that's not right" go through interpretation
with the pending receipt/task context. Users need not quote internal batch IDs.
Code commits only its own current batch after a validated approval decision,
not mappings substituted in the model's reply. Wrong, stale or reused receipt
references cannot approve another batch; a reply without a pending receipt
cannot approve anything.

Corrections propose a revised receipt for approval; rejection saves nothing.
Unclear or unrelated replies do not silently approve. Use the same interpretation
flow, not another approval phrase dictionary or separate confirmation agent.
Natural-language confirmation can consume interpretation calls and can still
be misinterpreted; structural receipt checks do not prove language meaning.
Optional local tooling hooks are acceptable only if useful for building/replay
verification; they are not the assumed user workflow or implicit live approval.

For teaching-plus-editing, confirmation continues the original validated task
from its original source, without reinterpreting approval as a new request or
requiring the user to repeat the edit. Approved teaching-only replies do not
generate a layout; approved combined replies continue into generation.
Model interpretation/generation requires `--live`, including confirmation
interpretation, with existing per-attempt call/deadline/usage guards. Do not
describe natural-language confirmation as an entirely local/free operation.

Rejection cancels that pending batch and associated unapplied task, leaving
confirmed names and the working/accepted layout unchanged; explain how to rephrase.
While a batch is pending, handle approval, correction or rejection before another
modifying task; an explicit independent replacement must not inherit approval.
Local source/control changes must not silently invalidate or retarget a receipt.
Read-only status/show/help and quit/resume remain available.

Retain the batch across restart; resuming never approves or dispatches by itself.
State/source conflicts must fail explicitly, not rebase the gate silently.
After valid confirmation, a later generation failure may leave the approved
names saved, but must preserve the verified working layout and recoverable task.
Do not promise all state is unchanged when only the collage is unchanged.

## Lifecycle and dependent consumers

Preserve explicit image acceptance, exact preview selection without generation,
older-source editing, retry/timeout source identity and invalid-answer recovery.
Keep actual recipe-change/ancestry records and bounded essential context.

Name-related navigation/context consumers must use confirmed labels and validated
bindings consistently; do not retain a second synonym engine to keep old callers
working. Preserve navigation evidence/source checks and adjust only dependent
name handling. The broader `nudge`/compound-return vocabulary issue is not part
of this pass. Stop if removing shared helpers requires a wider navigation redesign.

Replay must recognize and stop truthfully at pending naming approval, never
automatically confirm or mark a gated task complete. Record the actual approval
message/decision (or explicitly identified tooling action) and
actual continuation provenance. Offline assessment must distinguish pending,
discarded and completed tasks without treating a gate as a model/service failure.
Do not silently change replay inputs or claim an offline check is a live replay.
Existing sequences without durable teaching should not acquire extra confirmation
stops. Sequences explicitly teaching names may now pause at the naming gate;
do not evade that distinction to keep every old replay uninterrupted.

## Offline acceptance cases

Use controlled responses and existing generated-photo fixtures, not real calls.

| Case | Required outcome |
|---|---|
| Clear numbered edit or exact proposal return, without durable teaching | Proceed without a naming confirmation; pure selection still uses no generation. |
| Confirmed `tower bridge -> 1`; request says `bridge` | Model binding to 1 can reach generation without a literal-suffix prerequisite or persistent alias write. |
| Confirmed `bookshop -> 4`; request says `book shop` | Binding to 4 is accepted; spacing variation teaches nothing durable. |
| Add `Daunt Books -> 4` | Display/confirm addition; retain `bookshop -> 4`. Explicit reassignment shows old/new mapping and changes only that label. |
| Four beach photos; user teaches sand-castle label for 4 | Confirm supplied description; later controlled binding uses 4. Unknown visual detail or competing targets clarifies rather than invents knowledge. |
| Identity question answered `Photo 3`, including after invalid answer/restart | Continue original task/source with task-local identity; no automatic durable label or extra naming gate. |
| Padded numbers or multiple explicit names | Support valid normalized IDs. A deliberately swapped durable candidate is displayed but cannot be saved or used for its associated edit before exact approval. |
| Teaching-only versus teaching-plus-editing | Same natural-language gate. A validated affirmative reply approves the exact receipt; teaching-only makes no generation call, combined confirmation keeps the original task/source. |
| Negative, revised or unclear confirmation; `Yes` with no pending receipt; wrong/stale/reused receipt reference | No unapproved naming write or generation. A revision requires a new receipt; rejection cancels the associated unapplied task. Invalid responses retain truthful recovery state. |
| Restart, interrupted commit or external state change | Preserve/reconcile exact approved records without auto-approval, duplicate dispatch or silent partial mapping; surface uncertain integrity explicitly. |
| Exact-label/number contradiction, missing photo or forged cited evidence | Reject or clarify before generation; never silently override identity/state authority. |
| Older proposal, timeout or generation failure after approval | Preserve existing lifecycle/source semantics, approved-name truth and verified layout recovery. |
| Replay/assessment at the gate | Pause accurately; no automatic approval, false completion or hidden calls. |

These verify the application's handling of model claims, not that a live model
will choose every binding correctly. Keep that distinction in the results.

## Execution, verification and handoff

Capture a fresh baseline of staging, HEAD/branch, implementation/settings,
original photos, existing project/accepted data and prior evidence before edits.
Preserve the user's edits and staging; never reuse an older preservation baseline.

Version affected persisted contracts explicitly. At approval, conversation records
were 6 and replay reports 7; choose necessary new versions coherently, retain
layout/project format 3, reject unsupported old records and use fresh projects.
No migrations, dual paths or compatibility shims.

Run focused regressions and the full resulting offline suite, plus existing
sequence definition checks where applicable. Preserve all deterministic layout,
geometry/rendering, crop/tilt/stacking and original-photo tests; do not discard
them as part of interpretation simplification.

Reassess interpretation tests against the new responsibilities. Remove obsolete
alias/source-tag/phrase-rule assertions when that behaviour is deliberately
retired; adapt still-relevant cases and add focused tests for the new boundary.
Do not maintain obsolete production behaviour solely to satisfy old tests.
Retain coverage of essential lifecycle, integrity, accounting and recovery
invariants even when fixtures/contracts change. Report removals by responsibility
and rationale, not just a before/after test count. Test quality, not suite volume,
is the goal; passing a smaller suite must not conceal lost essential safeguards.

Briefly compare removed/retained responsibilities, remaining language-specific
rules and new confirmation-state cost. Document if simplicity gains are limited.
Use a focused rubber-duck/code review of the changed boundary if useful, without
expanding into the later general review or repeated redesign cycles.

Write `012_results.md` with changes, contract versions, verification, preservation,
limitations and a human-led handoff; update current guides/index. Stop on material
integrity risks, scope expansion or repeated unsuccessful repair cycles.

**Zero live calls in this autopilot pass.** No installs unless a changed manifest
or missing dependency requires them; dependency downloads need separate
authorization. No Git writes, branches, PRs, merges or package moves.
Do not overwrite original photos, old trial data or sealed evidence.

The original handoff required separately authorized replay evaluation, then
another human-led trial before branch changes, PRs or merges. Those evaluations
are now complete: [replay follow-up](012_replay_results.md),
[focused return repair/retest](012_return_repair_results.md) and
[human-led trial 05](012_trial05_results.md). Their permissions and budgets
remain separate from the original offline implementation pass and are closed.
