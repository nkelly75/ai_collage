# 010e third-freeze results

## Outcome

**Recommend low generation for a separately approved preference change.**
All six primary replays completed and passed offline integrity assessment.
The requested edits preserved unrelated authored fields, both exact returns
reused P001, and both clarification answers completed their original edit.
Low generation showed no observed adherence disadvantage in these cases and
substantially shorter initial-generation requests.

The provenance regression arose **naturally in both 05 runs**: an invalid
question interpretation, a valid correction, then the approved answer `2`.
Both resulting proposals passed audit and reopened successfully. This is live
evidence for the targeted fix, not just ordinary question/answer success.
Scripted success is not human sign-off or proof of general reliability.

Stages D-F of [010e](010e-interpretation-fixes-and-second-freeze.md#third-freeze-follow-up)
are complete and closed. **Defaults remain high; interpretation remained high.**
No further fixes, repeats, model experiments or default changes were performed.
The earlier [010e results](010e_results.md) remain unchanged, including their
failed low-05 evidence; this pass does not retrospectively repair that case.

## Readiness and freeze

Captured current staging, HEAD/branch, settings, runtime and preservation hashes
before checks. Unchanged offline checks for sequences 03-05 passed; the full
existing offline suite passed **527 tests in 507.93s**. Required regression
coverage includes corrected questions/answers, restart/retry, supported identity
bindings and rejection of invalid/unrelated provenance before publication.
No implementation/test/prompt/input changes were made under this approval.

Fresh pass: session `files\010e-evaluation-02`, with six new projects under
`data\users\local-dev\projects\p010e-{high,low}-{03,04,05}`.
The freeze contains 50 application/test/input files plus effective runtime,
instructions/settings and preservation metadata. HEAD:
`b0465c98a2ce99ce759faae37658054a11ba8146`; branch: `nkelly/plan-010`.
Working-file hashes identify the user's staged implementation, not HEAD alone.

Freeze SHA-256:
`fdad4f343220de5f0191d61ccbf59e0b189d1ec95ea6563a6618fe98e04fd4d2`.

The unchanged endpoint/deployment was the captured Foundry `gpt-5.4-mini`.
All projects used 1200x1800, cropping forbidden, the same four source photos
and captured style preferences. Only generation effort varied. All high cases
ran first, then all low cases, sequentially. Every live invocation/resume used
the same fresh guard and was preceded by frozen-input/preservation verification.
Earlier staging snapshots/verifiers were not reused as the current baseline.

## Primary outcomes

| Sequence | High generation | Low generation |
|---|---|---|
| 03: Names and multi-photo edits | Bridge/1 moved right 0.271667 -> 0.286667; breakfast/2 width 0.42 -> 0.40; only 2's radius then 16 -> 0. | Bridge/1 moved right 0.28 -> 0.32; breakfast/2 width 0.41 -> 0.37; only 2's radius then 14 -> 0. |
| 04: Borders and exact return | Only four white 8px borders removed, then exact P001 selected. | Only four white 8px borders removed, then exact P001 selected. |
| 05: Clarification and original edit | Expected identity question; Copilot answer `2` learned breakfast=2 and changed only 2's width 0.433333 -> 0.39 from P001. | Expected identity question; Copilot answer `2` learned breakfast=2 and changed only 2's width 0.34 -> 0.30 from P001. |

All six completed and passed integrity. All initial recipes used each of the
four whole photos once, with light backgrounds in 03/05 and dark in 04;
03 had rounded corners. Amounts, margins and styling varied legitimately.
No subjective design-quality equivalence or exact geometry target is claimed.
03 retained learned names after reopen and edited both intended targets.
Both 04 selections reused first-proposal paths, matching PNG digests and
unchanged write times, with zero generation calls and no acceptance.

Actual final working baselines in both candidates: **03 P003; 04 P001; 05 P002**.
Both 05 questions left P001 and no learned names before the answer. Both answers
retained the original resize task/source and taught the binding with question
evidence. No accepted version/proposal was created anywhere.

High-05's invalid question is event 3, corrected question event 4, name fact
event 5; P002 retains task origin 3. Low-05's corresponding events are 4, 5
and 6; P002 retains task origin 4. Both audit and reopening succeeded without
rewriting any task/evidence. No invalid response was manufactured.

## Corrections and limits

Two interpretation corrections per candidate, all at high interpretation:

- High-03 initially included forbidden `source` on a fresh action.
- High-05 and low-05 initially included forbidden `source` on a question.
- Low-05 initial composition invented individually numbered reference text for
  the collective phrase "all four photos."

Existing guards rejected these; the permitted correction succeeded each time.
There were **no generation corrections**, service failures, timeouts, uncertain
publication outcomes or unknown-usage attempts. The remaining interpretation
variance is not evidence about low generation effort.

One shared **36/200** counter: 18 calls per candidate, each comprising seven
generation and eleven interpretation calls. No explicit failed-step retry or
optional matched pair was used; primary evidence was sufficient for the bounded
recommendation. No counters were reset, no extra diagnostics dispatched model
calls, and the unused 164-call allowance is closed with this handoff.
Existing per-message caps, deadlines, token limits and disabled automatic service
retries were unchanged.

## Within-freeze timing and usage

Generation HTTP request durations in seconds; interpretation/local work excluded.
Every row below completed successfully, including delivery/audit.

| Operation | High | Low |
|---|---:|---:|
| 03 initial | 20.44 | 3.25 |
| 03 two-photo edit | 9.51 | 2.28 |
| 03 corners | 3.63 | 2.50 |
| 04 initial | 30.02 | 3.58 |
| 04 borders | 2.44 | 2.19 |
| 05 initial | 34.94 | 3.78 |
| 05 answer/edit | 4.64 | 3.27 |
| Initial median, n=3 each | **30.02** | **3.58** |
| Edit median, n=4 each | **4.13** | **2.39** |
| Total generation HTTP time | 105.61 | 20.84 |

Recorded full message execution durations include interpretation, corrections
and local validation/rendering, but not CLI startup or gaps between commands:

| Sequence/messages | High seconds | Low seconds |
|---|---|---|
| 03 initial / two-photo edit / corners | 42.92 / 18.22 / 12.28 | 22.67 / 11.78 / 12.55 |
| 04 initial / borders / return | 40.92 / 10.69 / 8.05 | 14.78 / 10.84 / 6.64 |
| 05 initial / question / answer | 46.52 / 12.47 / 21.14 | 29.77 / 15.23 / 20.14 |
| Sum of recorded executions | **213.21** | **144.40** |

These are sums of observed executions, not batch wall time. Full-message gains
were smaller than generation-only gains; some individual low messages took
longer. All correction waits are included; there were no omitted failed waits.

| Known usage | High | Low |
|---|---:|---:|
| Calls | 18 | 18 |
| All input / output tokens | 102,578 / 27,912 | 102,443 / 11,494 |
| All reasoning tokens | 25,041 | 8,786 |
| All cached input tokens | 73,216 | 78,080 |
| Generation input / output tokens | 46,281 / 20,838 | 46,261 / 3,050 |
| Generation reasoning tokens | 18,748 | 1,157 |
| Generation cached input tokens | 30,720 | 30,720 |
| Unknown-usage attempts | None | None |

Reasoning is included in output; cached input is included in input. No monetary
savings are inferred. Samples are small, high-then-low ordering is fixed and
generated baselines differ. The result supports low as a practical candidate,
not statistical equivalence or broad model superiority. Prior passes show
observed reliability improvement, not controlled cross-implementation timing.

## Preservation and evidence

Verified unchanged: current user staging, HEAD/branch, 975 pre-existing original
photo/runtime files, closed 010d/010e results and all prior sealed evidence:
262 files in `010d-evaluation-01`, 273 in `010e-evaluation-01`, and three in
`provenance-followup-01`. The old failed low-05 P002/state/events were not loaded
for recovery, repaired, resumed or reassessed as successful. No Git writes.

New pass evidence contains `before.json`, `freeze.json`, the full offline log,
sequence checks, per-invocation preservation records, question-state snapshots,
all raw request/event/context/proposal/PNG/replay files and six offline
`replay\assessments\0001.json` reports. `measurements.json` records exact timings,
usage, authored differences, report hashes, events and exact-return digest checks.
`extract.py` only reads saved evidence; it does not judge quality or dispatch calls.

Measurements SHA-256:
`096339f3e3041bca5ff41182710e72bb29c1ccbdb3feb77c238334c60cc54f6d`.
The new pass's `evidence-sha256.json` seals **277 files** after final preservation
verification. Evidence-manifest SHA-256:
`b093c07b170dcbea316ba2ef1f946c95db7735c90a7a99756e8aaa91cee7cd23`.

**Stop:** no default changes. A separately approved low-generation preference
must retain the explicit high override. The separately bounded interpretation
comparison and exploratory human-led trial remain outstanding.
