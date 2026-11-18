# 006: Simplification and repeatability

**Status:** Revised pass `006-20261118-02` completed.
All eight planned replays completed: 32 successful messages, one preserved
service timeout and explicitly authorized retry, 33/200 calls, no development
recoveries. Targeted edits passed; visual composition quality still varies.
The frozen candidate remained unchanged. This pass is closed; unused allowance
does not authorize further calls or tuning.
The first attempt stopped on a landscape baseline swap failure. Preserve that
attempt; the revised pass below uses fresh allowances and records quality
failures without abandoning the remaining assessment.
Execution evidence belongs in [006_results.md](006_results.md), not this brief.

## Goal and scope

Make the agent integration easier to understand and improve the two existing
replay workflows. Complete a bounded experiment with honest mixed results,
not a requirement for a clean sweep, a general reliability claim or good design.

First address the known swap failure: exchange both original authored centre
pairs from `editing_baseline`, never derived top-left coordinates; preserve
sizes, styles, photo identities and layer order.
Then make one focused simplification pass: consolidate duplicated agent/field-guide
instructions, avoid sending irrelevant human-facing documentation, and make
small directly related code refactors where justified. Preserve exact-copy
editing rules, trusted controls and numeric validation feedback. Do not force
changes where there is no convincing simplification.

Keep the model/reasoning configuration, history semantics, layout/response
contracts, renderer, preferences, replay messages and assessment checks unchanged.
Checkpoint B, new capabilities, UI/cloud work and automated aesthetic scoring
are out of scope. Follow-up prompts might recover a bad edit, but recovery is
not demonstrated unless tested; do not add recovery messages to these fixtures.

## Execution

1. Record a new pass identity and verify the existing optional guard offline
   before live calls. Start fresh 200-call and two-recovery allowances; leave the
   first attempt's counter at 8/200 and preserve all its evidence.
2. Reuse `p006-baseline-portrait` and `p006-baseline-landscape` as before-change
   evidence, not samples to replace until clean. Make the targeted swap prompt
   fix, pass the full offline suite, then run one fresh repair-check replay of each:
   `01_dark_portrait_adjustments.json` and
   `02_landscape_staggered_adjustments.json` under `examples\sequences`.
3. Make the focused simplification pass and pass the full offline suite:
   `.\.venv\Scripts\python.exe -m pytest -q .\tests`.
4. Run one fresh candidate check of each sequence. Record requested-edit,
   unrelated-field and visual comparisons against the preserved baselines and
   repair checks. Use bounded recovery below where justified. These are
   development checks, not independent final assessment evidence.
5. With the full offline suite green and no known application safety/integrity
   defect, freeze the selected candidate source and assembled instructions,
   listing remaining quality issues. Quality passes are not a freeze prerequisite.
   Run each sequence twice on fresh projects, with no implementation/prompt
   changes between assessment runs; quality failures do not cancel planned repeats.
6. Assess saved evidence, compare targeted edits and inspect generated images.
   Record all outcomes, including failures, then stop and hand back the results.

That is eight planned new replays, normally 32 model calls. Repairs for baseline-
related or later development failures share the recovery allowance below.
Never add unchanged reruns until lucky, replace failed evidence, or expand the
batch to use spare budget. The fixed assessment repeats are planned evidence,
not replacements for failures.

## Quality findings versus hard stops

Wrong edits, unwanted styling, poor composition, rejected model proposals after
bounded corrections, and unexpected questions are quality/reliability findings.
Record them and continue other planned fresh replays. A question or failed
execution ends that sequence as the runner requires: do not skip steps or
answer on the user's behalf. Valid but wrong proposals may continue through
the unchanged sequence; identify downstream results based on a flawed layout.

Evidence corruption, unsafe application behaviour and unresolved interrupted
requests are not model-quality findings. The hard stops below still apply.

## Development recovery: two retries

Allow **two substantive recovery attempts total**, beyond the planned initial
work (the known swap fix and planned simplification), before the candidate freeze.
A recovery is a changed source/prompt approach after a failed offline,
repair or candidate check; patch mechanics and formatting fixes do not count.
Each recovery may use at most one fresh pair of development replays
and must pass the relevant offline checks before those calls.

Each recovery needs a concrete new hypothesis. Record one short line in the
results: failure, proposed change, check/outcome. Stop tuning if the same failure
recurs without new evidence/progress, or another recovery would exceed two.
If the candidate remains offline-green and safe, freeze it with known limitations
and complete the fixed assessment batch instead of ending the experiment.
This is one shared allowance for the new pass, not per stage or task;
new labels, commands or restarts cannot renew it.

Neither allowance relaxes the guardrails, permits extra unchanged failure reruns,
or authorizes post-freeze tuning. Application validation corrections are separate
from development recoveries and still consume the call cap.

## Outer guard: 200 calls

Use an optional pass-local hard cap of **200 actual model calls**, shared across
repair/simplification checks, development recoveries and frozen assessments.
Enforce it at the shared HTTP dispatch boundary; include validation corrections,
failed HTTP requests and timeouts. Reserve before dispatch and never refund
possibly dispatched requests.

The conservative bound is 12 replays (eight planned plus four recovery rechecks),
four messages each, at most four calls per message: **192 calls**, rounded to 200.
Normally the initial batch uses 32 calls; two full recovery pairs bring that
to 48 before corrections. This covers the scoped worst case without making
budget exhaustion the expected reason for an incomplete handoff.

Starting a newly authorized pass creates a fresh counter automatically.
For this revised pass, use a new path; never reset, refund or overwrite the
first attempt's 8/200 record. The two-recovery allowance also starts fresh.
Resuming that pass retains its spent count across commands/process restarts;
new projects and retries cannot replenish it. Persist only the small amount
of pass state needed for that rule. Ordinary replay/chat use must not require
allowance provisioning, a global budget, or ledger-path binding.

Keep the existing four-call-per-message limit, 50,000-input/25,000-output-token
limits and 120-second request timeout. No hidden SDK/service retries or provider
fallback. The cap is a ceiling, not a quota or a quoted monetary-cost limit.
Hard stops are call-cap exhaustion, authentication/service failure, an unresolved
interrupted request, evidence corruption, unsafe application behaviour or a
scope/Git/data-protection blocker. Offline-test failures pause live calls;
repair only within the remaining development allowance, and stop the pass if
offline-green status cannot be restored. Retain partial results. Quality findings
and exhausted/non-progressing tuning alone do not stop the assessment batch.

## Evidence and guardrails

Use the existing portrait-specific assessment and landscape integrity assessment.
Copilot also compares requested versus actual edits, unrelated-field preservation,
and visible spacing/overlap/obstruction; no new judge or scoring framework.
Separate mechanical results, instruction-following observations and subjective
judgment. Experiment completion means the planned assessment replays were
attempted and reported, unless a hard stop prevented them; it does not mean all
edits passed. Report completed, failed and unreached steps without hiding mixed
results. A small frozen sample is not user sign-off or proof of generalization.

Record baseline, repair, candidate and frozen source/instruction identities,
changes, offline results, project/artifact paths, per-replay outcomes and correction counts,
token usage, guard/recovery consumption, limitations and the stopping reason in the
results file. Raw JSON/PNG evidence stays in normal ignored runtime storage.

No Git writes: no staging, commits, pushes, branch/ref changes, stash or reset.
Preserve original photos, existing projects/archives, preferences and historical
reports/ledgers; use fresh projects and never automatically accept proposals.
No authentication/configuration changes, separate Foundry experiments, or
unapproved extra development/live runs. Previous phases' allowances do not apply.
