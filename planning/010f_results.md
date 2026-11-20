# 010f results

## Outcome

**Recommend retaining high interpretation for now.** All six primary replays
completed, passed offline integrity assessment and preserved the requested
targets/unrelated fields. High interpretation was valid on its first attempt in
9/9 executions; low in 8/9, with one successful navigation-evidence correction.
Low reduced interpretation request time/tokens, but the correction's surrounding
work erased the small end-to-end benefit in this sample. This is not evidence
that low is generally unreliable or that high is statistically superior.

Stages A-C of [010f](010f-interpretation-reasoning-comparison.md) are complete
and closed. **Generation now defaults to low, with an explicit high override.
Interpretation's default remains high**, with low selectable independently.
No automatic escalation was added. Scripted success is not human sign-off;
human-led trials remain separately approved work.

## Offline preparation and contracts

Captured current staging, HEAD/branch, original-photo/runtime hashes and prior
closed records/seals before changing files. The approved preparation:

- Wired independent stage settings through chat, replay, request payloads and
  actual-attempt accounting; clarification answers, corrections and
  timeout-continuation interpretation use the selected interpretation effort.
- Required both candidates in replay reports, rejected resume changes to either
  (including omitted flags choosing different defaults), and updated assessment
  to check each stage against its recorded setting.
- Clarified that only edit has action-level `source`, including prohibition of
  null elsewhere; added one initial "all four photos" example with empty
  references. Validation was not weakened.
- Updated current CLI documentation and focused existing regression tests.

Only the affected persisted shape was bumped: **ReplayReport 6**, requiring both
candidate fields. Replay steps, assessments, conversation/proposal/event/
acceptance records remain **5**; request attempts remain **2**; layout/project
remain **3**. Unsupported older replay reports are rejected, not migrated or
silently assigned candidates. Old archives remain untouched.

The initial focused suites passed **105 tests**. The first full gate exposed
five mocked-HTTP generation test failures: the fixture passed a generation
context to the agent but not its transport guard, previously hidden by identical
stage defaults. The fixture now shares that context and asserts stage-specific
defaults; no production workaround was added. Targeted verification passed
12 tests, then the full existing offline suite passed **540 tests in 557.51s**.
One unsuccessful verification cycle; no unresolved failure. Unchanged offline
03-05 checks passed. No dependencies, renderer/geometry, generation prompt,
layout contract, input sequence or service limits changed.

## Freeze and execution

Fresh pass: session `files\010f-evaluation-01`, six new projects
`data\users\local-dev\projects\p010f-{high,low}-{03,04,05}`.
Here **high/low names interpretation**, not generation.

HEAD: `b0465c98a2ce99ce759faae37658054a11ba8146`;
branch: `nkelly/plan-010`. The freeze identifies working files, not HEAD alone.
It captures 50 application/test/input files, both prompts/schemas, layout
guide/schema, dependency manifests, installed runtime, original photos,
controls/preferences, deployment and both candidate settings.

Freeze SHA-256:
`8017305bb375ed4e33f82ad14bcfc0b8232fa39e4ca01d040c9c598570d5b8a7`.
Combined instructions SHA-256:
`b60a0e8a24c1367ce3c6dbb1a07dd4e9b4675047896963ba2f732c090f075f92`.

The captured Foundry deployment remained `gpt-5.4-mini`. All projects used the
same four photos/import order, 1200x1800, cropping forbidden and captured style
preferences. All high-interpretation cases ran first, then all low cases,
sequentially. Generation was explicitly **low on every invocation and answer**.
Frozen-input/preservation verification preceded every live invocation and
candidate transition. No application/test/prompt/input changes followed freeze.

## All six outcomes

| Sequence | High interpretation | Low interpretation |
|---|---|---|
| 03: Names and multi-photo edits | Bridge/1 moved right 0.29 -> 0.32; breakfast/2 width 0.36 -> 0.34; only 2's radius then 16 -> 0. | Bridge/1 moved right 0.29 -> 0.33; breakfast/2 width 0.36 -> 0.33; only 2's radius then 14 -> 0. |
| 04: Borders and exact return | Only four white 8px borders removed, then exact P001 selected without generation. | Same intended edits/return; one interpretation correction before exact P001 selection, without generation. |
| 05: Clarification and original edit | Asked "Which photo is breakfast?"; approved answer `2`, origin `copilot`, taught breakfast=2 and changed only 2's width 0.34 -> 0.30. | Same question/binding/continuation; changed only 2's width 0.38 -> 0.32. |

All initial recipes used each of the four whole photos once, with light
backgrounds in 03/05, dark in 04, and rounded corners in 03. Generated baselines,
styling and edit amounts varied legitimately; there is no subjective design
equivalence claim.

Both 03 runs retained bridge=1 and breakfast=2 after reopening and targeted
the correct photos. Both 04 returns reused the first proposal's ID/paths and
matching PNG digest, with file write times preceding the return request.
Both 05 questions left actual baseline P001 and no learned names; answer event
4 linked the breakfast fact to question event 3. P002 retained original task
origin 3, original resize prompt and source P001, not a new task derived from
the answer text.

Actual final baselines for both candidates: **03 P003; 04 P001; 05 P002**.
All proposals reopened and passed the shared provenance audit without changing
any project files. No accepted version/proposal was created.

## Interpretation validity and recovery

First-attempt validity means the first interpretation response passed local
schema, grounding and navigation checks, not just that transport completed.
It is separate from semantic correctness and excludes generation corrections.

| Executions | High valid / attempted | Low valid / attempted |
|---|---:|---:|
| Scripted messages, including the identity question | 8/8 | 7/8 |
| Of those, identity questions | 1/1 | 1/1 |
| Supplemental answers, counted separately | 1/1 | 1/1 |
| Total messages plus answers | **9/9** | **8/9** |
| Interpretation correction calls / recovered executions | 0 / 0 | 1 / 1 |
| Exhausted, failed or unexpected-question executions | 0 | 0 |

Low-04's return first emitted `select P001` with `continues_task: true` but no
grounded destination evidence. Event 5 rejected it:
"A return/older-source edit requires grounded destination evidence."
The same bounded interpretation stage corrected this by supplying ordinal
navigation text "first proposal"; event 6 selected exact P001. Baseline remained
P002 until successful selection. No recipe was generated or rewritten.

Neither candidate exhibited the previous forbidden action-level `source` or
collective-count reference errors. This is encouraging observation, not an
isolated prompt-only causal comparison against prior code freezes. No invalid
response was manufactured. There were **zero generation corrections**, service
failures, timeouts, uncertain publications or unknown/incomplete usage attempts.

One shared **33/200** counter: high used 16 calls (9 interpretation, 7 generation);
low used 17 (10 interpretation, 7 generation). No explicit failed-step retry or
optional matched pair was used. The primary evidence supports conservatively
retaining high; an extra pair was not needed to justify leaving its default
unchanged. No counter reset, unguarded model diagnostic or automatic service
retry occurred. The unused **167 calls are closed**, not future authorization.

## Within-freeze interpretation timings

Seconds per execution: first interpretation HTTP request / sum of all
interpretation HTTP requests, including correction waits. There were no failed
service waits to omit.

| Execution | High first / sum | Low first / sum |
|---|---:|---:|
| 03 initial and names | 4.59 / 4.59 | 2.09 / 2.09 |
| 03 two-photo edit | 2.70 / 2.70 | 2.39 / 2.39 |
| 03 corners | 2.38 / 2.38 | 2.09 / 2.09 |
| 04 initial | 2.39 / 2.39 | 1.72 / 1.72 |
| 04 borders | 2.56 / 2.56 | 1.80 / 1.80 |
| 04 return | 3.17 / 3.17 | 1.64 / 4.30 |
| 05 initial | 2.39 / 2.39 | 2.80 / 2.80 |
| 05 identity question, n=1 each | 2.44 / 2.44 | 1.98 / 1.98 |
| 05 supplemental answer, n=1 each | 4.13 / 4.13 | 2.91 / 2.91 |
| Median over 9 executions | **2.56 / 2.56** | **2.09 / 2.09** |
| Total over 9 executions | **26.75 / 26.75** | **19.42 / 22.08** |

Low's correction request took 2.66s. Request sums are **not full interpretation
stage time**: the records do not timestamp stage entry/final validation.
The derivable first-dispatch-to-last-completion span includes the intervening
correction validation/context/preflight gap, but excludes work before first
dispatch and after final completion. Its total was **26.75s high / 27.27s low**;
low-04 return alone spanned **9.49s** versus 4.30s of HTTP requests. This prevents
misrepresenting the correction as costing only its additional HTTP duration.

## Full-message timings and fixed-low generation

Recorded message durations include interpretation, corrections and local
validation/rendering, but exclude CLI startup and gaps between commands.

| Sequence/messages | High interpretation seconds | Low interpretation seconds |
|---|---|---|
| 03 initial / two-photo edit / corners | 26.03 / 16.45 / 16.11 | 21.72 / 15.88 / 17.63 |
| 04 initial / borders / return | 28.56 / 16.26 / 8.59 | 28.58 / 17.64 / 15.06 |
| 05 initial / question / answer | 29.11 / 7.69 / 22.80 | 28.42 / 6.01 / 21.53 |
| Sum, n=9 executions each | **171.61** | **172.47** |

Generation was low in both candidates, with seven successful requests each.
Initial-generation medians (n=3) were 3.58s / 3.94s; edit medians (n=4)
2.15s / 2.52s; total generation HTTP time 20.30s / 21.53s (high/low
interpretation respectively). Exact returns and questions made no generation
calls. Per-request values are in the sealed measurements.

These are observed execution sums, not batch wall time or isolated
interpretation-stage measurements. The sub-second total message difference
does not establish an end-to-end winner.

## Known token usage

| Stage / interpretation candidate | Calls | Input | Output | Reasoning | Cached input |
|---|---:|---:|---:|---:|---:|
| Interpretation / high | 9 | 46,624 | 3,298 | 2,759 | 34,816 |
| Interpretation / low | 10 | 52,095 | 1,251 | 693 | 40,960 |
| Generation (low) / high | 7 | 45,878 | 3,380 | 1,478 | 30,720 |
| Generation (low) / low | 7 | 45,818 | 2,971 | 1,066 | 37,632 |
| All / high | 16 | 92,502 | 6,678 | 4,237 | 65,536 |
| All / low | 17 | 97,913 | 4,222 | 1,759 | 78,592 |

Reasoning tokens are included in output; cached tokens are included in input.
All four usage fields were known for all 33 requests; missing usage was not
treated as zero. Low used fewer output/reasoning tokens but one extra input
context. No monetary saving is inferred.

Small samples, fixed high-then-low ordering, caching, network/local overhead and
different generated baselines limit conclusions. Low remains a possible future
candidate; these results do not justify trading a modest request-level gain
for an observed extra correction by changing interpretation's default now.

## Preservation and evidence

Verified unchanged against this pass's entry snapshot: user staging,
HEAD/branch, **975 pre-existing original-photo/runtime files**, closed 010d/010e
records, and sealed evidence/file sets: `010d-evaluation-01` (262),
`010e-evaluation-01` (273), `provenance-followup-01` (3),
`010e-evaluation-02` (277). The old failed low-05 evidence was not repaired,
resumed, recovered or reassessed as successful. No Git writes.

The new pass retains entry/freeze snapshots, offline logs including the initial
test-fixture failure, unchanged sequence checks, per-invocation verifications,
both question-state/report snapshots, raw request/event/context/proposal/PNG
and replay evidence, and six offline assessments. `extract.py` reads saved
evidence and performs read-only proposal reopening; it sends no requests.
`measurements.json` includes exact timings, usage, errors, changes, events,
report hashes and exact-return digest checks.

Measurements SHA-256:
`357c2b8eaa8dd830ca83f6ce41532200bd6e17e88997bd784e576ef6ecc4a316`.
After final frozen-input/preservation verification, `evidence-sha256.json`
sealed **275 files**; its exact file set and every digest were verified.
Evidence-manifest SHA-256:
`ed59192d9f3faf64b08ae0541e38a19fee44da3e02f1c44c189f703d27cd4dfd`.

**Stop:** interpretation remains high; generation stays low with a high
override. Further implementation, trials, refreezes and interpretation-default
changes require new approval.
