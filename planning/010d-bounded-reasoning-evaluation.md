# 010d: Bounded reasoning evaluation

**Status:** Executed under the user's bounded live authorization and closed.
See [010d results](010d_results.md) for the comparison, limitations and accounting.
The frozen brief below remains the execution record, not permission for more calls.
Follow-up to [010a](010a_results.md), [010b](010b_results.md) and
[010c](010c_results.md), under [010](010-grounded-interpretation-and-human-trials.md).
An exploratory human-led trial remains a separate later step.

## Aim and frozen cases

Screen whether generation-only low reasoning looks potentially good enough,
compared with default high, for ordinary instruction adherence and latency.
Expect variance; identical designs, beautiful composition and perfect repeated
success are not requirements. This is a small screening experiment, not a
reliability benchmark or human sign-off.

Use the three new sequences, in order, first all with **high**, then all with
**low**, in six fresh projects under a fresh isolated session-artifact data root:

| Sequence | Checks |
|---|---|
| [03: Names](../examples/sequences/03_named_photo_adjustments.json) | Teach bridge=1 and breakfast=2 while creating; resume, shrink 2 and move 1 right without unrelated edits; remove only 2's rounding. |
| [04: Return](../examples/sequences/04_exact_proposal_return.json) | Create with borders, remove them, then resume and select the first proposal/PNG exactly, with no generation, rerendering or acceptance. |
| [05: Clarification](../examples/sequences/05_clarification_continuation.json) | Create; untaught breakfast must prompt for identity without an edit/baseline change; answer **2**, retaining the original resize task and learning the name. |

For 05, inspect the question. Supply `--resume --answer "2" --answer-origin copilot`
only for the expected photo-identity clarification, retaining the chosen
`--generation-reasoning`. The answer is supplemental, not a third scripted
message. Any other question stops that case; do not improvise answers or prompts.
All three sequences are Copilot-authored/user-approved, not unassisted human trials.

At launch, record HEAD and hashes of application code, model instructions/
layout guide/schema, dependency manifests, sequences and source photos; record
effective runtime versions, controls and captured preferences. Keep these fixed
through both candidates and any permitted repeats. Use identical input photos,
canvas/cropping and preferences, but independent projects with no learned-name
leakage. Interpretation remains high; change only `--generation-reasoning`.
Do not change models, prompts, tests, limits or implementation mid-comparison.
Record a discovered defect, do not repair it during this pass.

## Simple call guard and stop rules

- Choose one fresh pass directory in session artifacts. Every live replay,
  resume, answer and permitted retry uses the **same absolute**
  `--call-budget <pass-directory>\call-budget.json --max-calls 200`.
  This is one durable **200-call total ceiling**, not 200 per project/candidate.
  Use the existing guard, not new budget infrastructure. Never reset, replace or
  replenish its file, or dispatch unguarded diagnostic/model calls.
- The primary pass is normally about 32 calls; allowing four calls for each
  scripted message and planned answer gives a conservative 72-call envelope.
  The ceiling deliberately leaves ample headroom; it is not a target to consume.
  Existing four-call/two-interpretation caps, shared 120/180-second stage
  deadlines, token limits, durable usage and no automatic service retries remain.
- Run sequentially through the existing replay CLI, using `--remaining` and
  inspecting any stop. A failed case is evidence: preserve it and continue the
  other frozen cases/candidate unless safety, integrity or service availability
  prevents useful work. No retries for instruction/validation failures.
- Across the whole pass, allow at most **one explicit failed-step retry** for a
  clearly transient service/transport error, using existing `--resume --retry`
  and the same budget. Record the first failure and reason separately. Do not
  loop on authentication failures or publication/I/O uncertainty.
- If primary evidence is inconclusive, allow at most **one additional matched
  high/low pair for one selected sequence**, in fresh projects, only where that
  could materially clarify the decision. Record why it was chosen and keep
  first-pass results separate. No open-ended repeat campaign.
- Stop on budget exhaustion, identity/data-integrity risk, changed frozen inputs,
  or a blocker requiring code/scope changes. Report partial evidence honestly.
  Do not silently renew authorization to finish every case.

## Evidence and comparison

Before any live calls, run each sequence's offline `--check`. Keep immutable
raw events, contexts, proposals/PNGs, request records and replay reports. Run
the existing offline **integrity** assessment for each project; it is not an
instruction-adherence score. No new evaluator/profile or LLM judging is needed.

Review authored recipe differences and source/task evidence against the table.
Check actual direction/size/corner/border effects and unrelated-field
preservation; for exact return compare preserved proposal/PNG identity and
absence of generation. Do not demand identical high/low coordinates, fixed
colour shades or a particular percentage change for "a bit". Report wrong
photos/sources and unintended edits explicitly; do not average them away.
Classify adherence as followed, partial, failed or not assessable, with evidence.

Use request-attempt `stage`, `reasoning_effort` and `duration` for measured
generation latency, separately for initial layouts and edits. Show per-case
timings and small-sample medians for completed generation calls, with sample
counts. Report correction calls, failed/timeout waits and total message times
separately so faster failures or omitted work cannot look like improvements.
Include known input/output/reasoning usage and unknown attempts; do not invent
missing consumption or claim cost savings from incomplete usage.

## Guardrails and handoff

No Git writes, dependency changes, application changes, old-project recovery,
acceptance or writes to original photos/archived trials. Only fresh pass
artifacts and directly related results/tracker documentation may change during
execution. Keep evidence paths and hashes in a concise `010d_results.md`;
link rather than copying all raw data into planning documents.

Finish with **low looks promising**, **high remains preferable**, or
**inconclusive**, explaining adherence versus measured latency and limitations.
Do not automatically change the default or start alternative-model experiments.
Stop for review before the separately authorized exploratory human-led trial.
