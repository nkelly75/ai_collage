# 010d results: Bounded reasoning evaluation

## Outcome

**Low looks promising for generation**, not an end-to-end reliability pass.
Both candidates followed the checked layout instructions whenever generation
was reached. Initial-generation median request time fell from **21.55s to
3.33s** (three calls each); edit-generation median fell from **2.92s to 2.13s**
(three calls each). The unchanged high-reasoning interpretation stage still
blocked clarification continuation in both candidates and exact return in one.
Keep the default high unchanged pending review.

The six primary fresh-project runs under [010d](010d-bounded-reasoning-evaluation.md)
are complete and this pass is closed. No extra matched pair was warranted:
generation already supplied a useful preliminary signal, while repeating the
shared interpretation failures would not isolate generation reasoning.
This is not human sign-off; exploratory human trials and alternative models
have not been launched.

## Frozen setup and guard accounting

- Ran 03, 04, 05 with high, then the same cases with generation-only low.
  Interpretation remained high; deployment remained `gpt-5.4-mini`.
  Runtime versions/settings and input hashes are in `freeze.json`.
- HEAD `b0465c98a2ce99ce759faae37658054a11ba8146`, branch
  `nkelly/plan-010`. The user-staged preparation was included through working
  file hashes; no Git mutations were made. All **50 frozen files**, **975
  pre-existing photo/runtime files**, staged entries, HEAD and branch were
  unchanged. No implementation, prompts, tests, dependencies or default changes.
- All projects used 1200x1800, cropping disabled, and identical captured
  `prefer` defaults for borders/rounding/tilt. Each had independent name/history
  state. The three offline sequence checks completed before the first live call.
- One durable `call-budget.json`, **36/200 calls used**, shared by every live
  invocation including both planned Copilot answers. No unguarded inference,
  explicit failed-step retries, matched repeats, timeouts, service failures or
  budget replenishment. The unused allowance is closed, not future permission.
- Each candidate used 18 calls: 12 interpretation and 6 generation.
  Three interpretation correction calls each; five invalid interpretation
  responses under high and four under low. The replay's
  `validation_corrections` counts invalid responses, not just follow-up calls.
  No generation corrections. All HTTP requests completed with known usage;
  completed HTTP requests can still yield rejected interpretation output.
- No acceptances, original-photo edits or writes to previous trial projects.

## Instruction adherence

| Case | High | Low |
|---|---|---|
| 03: Names and edits | **Followed**, after one interpretation correction. Bridge=1 and breakfast=2 survived reopen; only 1's horizontal centre and 2's width changed, then only 2's rounding. | **Followed**, after the same kind of correction. Correct targets and unrelated-field preservation. |
| 04: Borders and exact return | **Partial**: initial dark layout with thin white borders and border-only removal followed; return failed after interpretation correction. Baseline safely stayed P002. | **Followed**: border-only removal, then exact P001 selection after one interpretation correction; no new generation/render or acceptance. |
| 05: Clarification continuation | **Partial**: initial layout and expected identity question followed. Planned answer `2` failed interpretation twice; no resize/name learning was published. | **Partial**: same expected question; planned answer `2` failed interpretation twice. Original resize never reached generation. |

All six initial layouts used all four whole photos with the requested
light/dark background. Cases 03/05 left generous outer space; 03 used rounded
corners. Compositions varied as permitted, including no tilt in low-04 despite
the soft `prefer` default. No subjective design-quality equivalence is claimed.

Exact authored edit evidence:

- 03 high: photo 1 `center_x` 0.275 -> 0.305; photo 2 width 0.37 -> 0.35;
  next edit changed only photo 2 radius 14 -> 0.
- 03 low: photo 1 `center_x` 0.30 -> 0.34; photo 2 width 0.37 -> 0.34;
  next edit changed only photo 2 radius 18 -> 0.
- 04 both: only four border fields changed, from 8px white to null.
  Low subsequently selected the original P001/proposal/preview paths.
  Its PNG hash matched the stored digest, and proposal/PNG write times
  preceded the selection execution. No new proposal or generation call.
- 05 both: question and failed answer preserved baseline P001, with no learned
  names, replacement proposal or acceptance. Pre-answer state snapshots retain
  that boundary. Successful answer-and-task continuation was **not demonstrated**.

Observed interpretation defects, preserved rather than repaired:

- 03 both initially attached event IDs to `source: name` references; correction
  removed them and generation then followed the requested two-photo edit.
- 04 high first quoted an absent literal P001, then supplied an invalid
  `task_id` for ordinal navigation. Low also initially supplied invalid
  navigation metadata, but corrected it. Both used **high interpretation**:
  the differing return outcome is not evidence that low generation improved it.
- 05 high supplied unsupported short-answer name-update evidence. Low returned
  a `remember` interpretation with rejected name-correction evidence, rather
  than a resolved resize. The validator stopped both before any edit.

Offline integrity reports pass for high-03, low-03 and low-04. The other three
honestly report incomplete replays; their completed proposal cases passed
integrity, while failed/question executions are not assessed as successes.
Integrity is separate from the manual instruction review above.

## Timing and known usage

Generation **request-attempt durations**, seconds, from saved `stage`,
`reasoning_effort` and `duration`; not full CLI/stage wall time:

| Generated operation | High | Low |
|---|---:|---:|
| 03 initial | 21.55 | 4.14 |
| 03 two-photo edit | 9.80 | 2.61 |
| 03 corner edit | 2.66 | 2.13 |
| 04 initial | 17.58 | 3.33 |
| 04 border edit | 2.92 | 2.11 |
| 05 initial | 41.13 | 3.08 |
| Initial median, n=3 each | **21.55** | **3.33** |
| Edit median, n=3 each | **2.92** | **2.13** |
| All generation median, n=6 each | 13.69 | 2.84 |

No generation measurements exist for either failed 05 answer or either 04
return: selection does not generate. No failed waits were counted as faster
generation. The total generation-request time was 95.62s high / 17.39s low.

Full recorded message-execution durations (includes interpretation,
corrections and local work; excludes CLI startup between invocations):

| Case, message order | High seconds | Low seconds |
|---|---|---|
| 03 initial / multi-edit / corners | 39.00 / 24.92 / 11.92 | 16.17 / 18.30 / 11.16 |
| 04 initial / borders / return | 29.64 / 11.47 / **12.67 failed** | 14.14 / 10.80 / 22.45 selected |
| 05 initial / question / answer | 53.44 / 6.01 / **24.00 failed** | 13.91 / 5.50 / **25.48 failed** |
| Sum of recorded executions | 213.08 | 137.91 |

Interpretation correction HTTP waits totalled 13.89s high / 27.52s low,
already included above, not extra time to add. No service/timeout waits.
The low return succeeded but took longer; end-to-end outcomes must not be
conflated with generation latency.

| Known usage | High | Low |
|---|---:|---:|
| All calls: input / output | 94,973 / 28,478 | 94,012 / 12,449 |
| All calls: reasoning | 25,947 | 10,105 |
| Generation only: input / output | 39,004 / 20,250 | 38,567 / 2,565 |
| Generation only: reasoning | 18,483 | 952 |
| Unknown-usage attempts | None | None |

Reasoning tokens are included in output, not additional usage. Cached input
was 64,512 high / 71,936 low overall; generation-only cached input was 25,856
for each. These are measurements, not a monetary cost estimate. Small samples,
different generated baselines and fixed high-then-low ordering limit causal
claims; initial latency improved much more than simple edit latency.

## Evidence and handoff

Evidence root in this Copilot session: `files\010d-evaluation-01`
(`C:\Users\nkell\.copilot\session-state\621a42a9-2ec6-4af0-a2d9-fde02d818692\files\010d-evaluation-01`).

- `freeze.json`, `verification-log.jsonl`, candidate-transition and final
  preservation records: settings/versions, Git identity/staging and before/after
  file hashes. `check-*.json` records the offline input checks.
- `data\users\local-dev\projects\p010d-{high,low}-{03,04,05}`: each project's
  `replay\report.json`, steps/contexts, `replay\assessments\0001.json`, raw
  conversation events, immutable proposals/PNGs and request attempts.
- `*-initial.stdout.json` preserves pre-answer reports; `*-answer.stdout.json`
  and `*-05-question-state.json` preserve assisted-continuation boundaries.
- `measurements.json`: exact timings/usage, all six replay SHA-256 values,
  authored differences and exact-return identity/hash evidence.
  `evidence-sha256.json` seals the pass-local evidence files.

Evidence-manifest SHA-256:
`cf4666c9bf386c34cbff66fcae0a0336f79d86d1dd4bc9f435cf1f2915a66f22`.

The remaining weakness exposed here is interpretation/binding/navigation,
not observed generation adherence. Review those failures separately before
relying on a human-led trial; do not silently fix and rerun this frozen pass.
Low merits consideration for that later trial, but no default or model change
has been made.
