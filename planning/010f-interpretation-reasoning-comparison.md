# 010f: Interpretation efficiency and frozen reasoning comparison

**Status:** Stages A-C executed and closed under explicit approval; see
[010f results](010f_results.md). Generation now defaults to low with a high
override; interpretation's default remains high. The shared allowance is closed.
This record authorizes no further implementation or live calls. [010d results](010d_results.md),
[010e results](010e_results.md) and [010e third-freeze results](010e_third_freeze_results.md)
remain closed, unchanged evidence.

## Purpose and approval boundary

Adopt low generation reasoning on the strength of the completed comparison,
reduce avoidable interpretation corrections with a small prompt improvement,
then compare high versus low interpretation under one new freeze. Keep the
two stages independent: **generation fixed at low; interpretation is the
comparison variable**.

One explicit approval may cover stages A-C: offline preparation, the frozen
live comparison after the offline gate passes, then reporting. Autopilot may
advance within those boundaries without approval for each model call. Suggested
approval:

> Proceed with stages A-C in planning\010f-interpretation-reasoning-comparison.md.
> Adopt low generation with a high override, make the bounded offline preparation,
> then compare high/low interpretation with generation fixed at low under one
> fresh shared 200-call ceiling. Preserve prior evidence and my staging.
> Stop on integrity risks and before changing interpretation's default.

Unlike earlier comparisons, approval explicitly permits the **generation**
default change in A. It does not permit changing interpretation's high default,
alternative models, exploratory human trials, further fix/refreeze cycles or
Git writes, including staging, commits, pushes and branch/history changes.

## A: Offline preparation

Capture current staging, HEAD/branch, original-photo/runtime hashes, closed
results and prior evidence seals before changes. Use this new staging baseline,
not an old pass's assumptions.

### Independent stage settings

- Change generation's default from high to **low**, consistently across chat,
  replay and direct request APIs. Retain `--generation-reasoning high` and the
  corresponding explicit API override; no automatic fallback or hidden escalation.
- Add independent `--interpretation-reasoning high|low` support to chat/replay
  and their request path, **default high**. It applies to every interpretation
  request, including clarification answers, corrections and timeout-continuation
  interpretation. Generation and its corrections keep their separately selected
  effort; changing one stage must not change the other.
- Record both selected candidates in replay evidence; request attempts must
  continue to record the actual stage/effort sent. Resume must reject either
  candidate changing, including an omitted flag silently selecting a different
  default. Update offline assessment to verify each stage against its recorded
  setting, rather than assuming interpretation is always high.
- Keep evidence explicit: require both replay candidate fields, rather than
  silently interpreting an absent field. Version only affected persisted
  contracts when required, updating dependent code/tests/docs together. Preserve
  older records as archives, clearly rejecting unsupported versions; no
  compatibility loaders, migrations or old-evidence rewrites. No layout-format
  bump for agent-only changes.

### Surgical interpretation-prompt improvements

Use the correction evidence to clarify general rules, not special-case messages:

- State action-specific `source` ownership explicitly: only `edit` supplies it;
  `fresh` and `question` must omit it entirely, not emit null. Keep other
  action-specific field requirements consistent with the local contracts.
- Add one short valid initial-composition example for collective wording such
  as "all four photos", with empty `references`. Enumerate references only for
  individually identified photos; counts are not photo identities. Preserve
  existing explicit numbered-list support, taught names and clarification.

Keep the prompt concise; prefer clarifying existing wording over repeating it.
Do not redesign the transport schema or weaken validation to accept the previous
bad responses. No generation-prompt, renderer, geometry/layout, replay-input,
deployment, dependency or service-limit changes. No new inference stage,
automatic quality scoring, model judge or retry machinery.

### Offline gate

Use focused cases in existing tests for independent stage selection/defaults,
actual request effort, correction/answer routing, replay capture/resume mismatch,
assessment checks and unsupported evidence versions. Preserve provenance
regressions, multi-photo names, collective/numbered references, navigation,
clarification continuation and prepublication rejection. Controlled tests can
verify contracts/request wiring; they cannot prove prompt wording improves
live first-attempt validity.

Run the smallest covering suites, then the **full existing offline suite** and
unchanged offline sequence checks for 03-05. Update current CLI documentation,
examples of reasoning flags and directly related status, not historical results.
Preserve original data and deterministic rendering behavior.

At most **three unsuccessful targeted fix-and-verify cycles per blocker**.
Stop with evidence if blocked or if broader changes are needed. No live prompt
debugging before freeze. A frozen-pass defect does not reopen A.

## B: One frozen interpretation-only comparison

After the gate, create a fresh isolated pass directory, suggested session
`files\010f-evaluation-01`, and fresh projects for each candidate/case. Capture
HEAD plus working-file hashes; no commit is required. Freeze application/tests,
both prompts/schemas, layout guide/schema, dependency manifests and effective
runtime, sequences, source photos, controls, preferences and both reasoning
settings. Verify before each live invocation, answer/resume and transition.

Use **unchanged sequences/checks 03-05**: all three with interpretation **high**,
then all three with interpretation **low**. Explicitly set generation **low in
every invocation**. Keep the same deployment, photos/import order, 1200x1800
canvas, cropping forbidden and captured preferences. No shared project/name
history between candidates; do not compare latency against earlier code freezes
as if only reasoning had changed.

For each 05 case, answer only the expected breakfast photo-identity question
with `2`, origin `copilot`, using both original candidate flags on resume.
Unexpected questions stop that case; do not improvise answers or change prompts.
Do not manufacture invalid responses to force corrections.

Use the existing durable guard, with **one fresh shared 200-call ceiling**:
every live command, answer, retry and permitted matched pair must include
`--call-budget <010f-pass>\call-budget.json --max-calls 200`.
The primary envelope is conservatively 72 calls; the ceiling leaves headroom,
not a spending target. Never reset/replenish the counter, reuse old allowances
or dispatch unguarded diagnostics.

Retain existing four-call/two-interpretation caps, shared interpretation/generation
deadlines, token limits and disabled automatic service retries. Run sequentially
through the existing replay CLI, inspecting each stop.

- Preserve instruction/validation failures as evidence; continue unaffected
  frozen cases only where safe and useful.
- At most **one explicit failed-step retry across the pass**, only for a clearly
  transient service/transport failure, using existing `--resume --retry`.
  Preserve the original failure; no authentication loops or retries of uncertain
  publication/I/O.
- If primary evidence is materially inconclusive, at most **one justified extra
  matched high/low interpretation pair for one sequence**, in fresh projects
  with generation low. Keep separate results; no search for a pleasing run.
- **No implementation/prompt/input tuning after freeze.** Stop on changed
  frozen inputs, identity/integrity risk, uncertain publication/I/O, budget
  exhaustion or a blocker requiring scope/code changes. Preserve actual state;
  never repair/rewrite failed cases within the pass.

## C: Assess, report and stop

Use existing offline integrity assessment plus manual source/authored-difference
review. Check correct multi-photo bindings, no unrelated edits, exact proposal/
PNG selection and genuine clarification-answer-original-edit completion.
Record actual baselines before/after failures, not assumed rollback.

Compare interpretation **correctness first**, then efficiency:

| Measure | Required reporting |
|---|---|
| First-attempt validity | Valid initial interpretation responses / all attempted message or answer executions, n/N per candidate; supplemental answers counted separately and in totals. Exclude generation corrections from this metric. |
| Recovery | Invalid-response categories, interpretation correction calls, successful recoveries and exhausted/failed executions. Do not equate validity with semantic correctness. |
| Task adherence | Observed bindings, action/source/navigation, clarification behavior and original-task retention, including validation-passing misunderstandings. |
| Interpretation latency | First-attempt request durations and per-execution sums of all interpretation attempts, including correction/failed waits; report sample counts and questions/answers separately. Also report elapsed interpretation-stage time where existing evidence provides it; label request sums versus stage time accurately. |
| End-to-end and usage | Full message durations, generation durations/corrections, known input/output/reasoning/cached usage by stage, unknown/incomplete attempts and failures. Missing usage is not zero. |

Use within-freeze comparisons. Different valid questions, generated baselines,
small samples, fixed ordering and caching can affect results. Earlier evidence
can explain observed changes but does not isolate the prompt improvement from
other code changes; do not claim a controlled prompt-only speedup.

Write concise **`planning\010f_results.md`** with offline changes/contract versions,
freeze hashes, all six outcomes, exact settings, metrics/limitations, retry/repeat
accounting, final counter and preservation evidence. Seal the new pass artifacts,
verify them, and update directly related status/links. Preserve all closed
010d/010e results, prior freezes/seals and targeted-fix evidence untouched.

Recommend **high**, **low** or **inconclusive** for interpretation, then
**stop for review without changing interpretation's high default**. Generation
stays low with its high override. Close unused allowance; further fixes,
refreezes, default changes and human-led trials require new approval.
