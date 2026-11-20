# 010e results: Interpretation fixes and second freeze

## Outcome and stop

**Recommendation: inconclusive for changing the default; low generation
remains promising.** Five of six primary replays completed and passed offline
integrity. Low-05 reached the intended resize but then failed proposal
provenance validation. The frozen pass stopped at that blocker, with no fix,
retry, matched repeat or default change. See [010e](010e-interpretation-fixes-and-second-freeze.md).

The previously observed name-binding/ordinal failures did not recur. Both
candidates completed the named edits and exact return. High-05 also completed
the numeric-answer-original-edit path. Low-05 resolved the correct identity and
generated the requested edit, but **cannot be counted as audited success**.
No human trial or interpretation-reasoning comparison was launched.

## Offline implementation

- The identity-answer path now recognizes both legal unresolved reference
  sources (`name` and `unknown`). The question's named focus disambiguates
  multi-name tasks; answers must supply one supported photo number. A validated
  pending answer can support normalized `photo N` references without inventing
  extra photo identities.
- Provider interpretation schemas now constrain reference/navigation fields
  by source/kind: history alone cites a reference event; ID/ordinal navigation
  cannot carry task/field/step metadata; descriptive/undo evidence requires
  its applicable fields. Local identity/evidence checks remain strict.
- Interpretation instructions distinguish learning an unknown identity from
  correcting a taught name, and require a pending edit's answer to complete
  the original edit rather than only acknowledge a name. No application
  guessing or automatic rewriting of malformed responses.
- Focused cases use varied labels/IDs/answer forms, restart and multi-photo
  tasks, plus unsupported/ambiguous numeric answers. Existing negative
  binding/navigation cases remain. No special cases for the replay filenames,
  breakfast, bridge, photo 2 or P001.

Offline reproduction before fixes: three expected failures and four passing
negative cases. First targeted fix verification: **172 passed**. After adding
unknown-source coverage to the existing multi-question test, final full offline
gate: **515 passed in 200.76s**. No unsuccessful fix cycles or live debugging.
CLI documentation was updated directly. Record versions remain unchanged:
no persisted shape was broken; layout remains 3 and conversation/replay 5.

## Second-freeze outcomes

| Case | High generation | Low generation |
|---|---|---|
| 03: Names and multi-photo edits | Completed, integrity passed. Photo 1 moved right 0.255 -> 0.285; photo 2 width 0.44 -> 0.42; only 2's radius then changed 16 -> 0. | Completed, integrity passed. Photo 1 moved right 0.28 -> 0.32; photo 2 width 0.36 -> 0.34; only 2's radius then changed 18 -> 0. |
| 04: Borders and exact return | Completed, integrity passed. Only four 8px white borders removed; exact P001 selected without generation/render/acceptance. | Completed, integrity passed. Only four 10px white borders removed; exact P001 selected without generation/render/acceptance. |
| 05: Identity clarification and original edit | Completed, assisted integrity passed. Asked the expected identity question; Copilot answer `2` taught breakfast=2 and changed only 2's width 0.37 -> 0.35. | Failed final provenance validation after the expected question and answer `2`. Binding and original-task resolution succeeded; raw generated recipe changes only 2's width 0.37 -> 0.33. Not an audited completion. |

All initial recipes used all four whole photos and requested light/dark
backgrounds; 03 had rounded corners. Outer space varied: high-03 used narrower
horizontal margins than low-03. "Generous" margins remain qualitative; no
exact-layout or subjective design-quality equivalence is claimed.

03 edits preserved unrelated authored fields and stacking. Both 04 selections
reused the first proposal/preview paths and preserved PNG digests/write times.
Both 05 questions preserved P001 before the recorded supplemental answer,
which retained the original resize request, source P001 and photo 2 binding.

Remaining interpretation corrections were one high and three low: three
initial-composition responses invented numbered quotes for "all four photos";
one low-05 question included an action-inappropriate `source`. Existing guards
rejected them; allowed corrections succeeded. No naming-reference event-ID or
ordinal-metadata corrections were needed. Interpretation was high for both
candidates, so these differences are not attributed to generation effort.

## New provenance blocker

Low-05's first interpretation of the resize request was invalid (event 4);
its corrected question was event 5 in the same logical task. After the answer,
the resolved edit correctly retained task origin 4, original wording and P001.
Generation published P002 and set the working baseline to P002. Subsequent
proposal validation rejected the origin because event 4's outcome was
`invalid`, not `intent`/`question`.

Read-only diagnosis confirmed P002's recipe digest, recomputed geometry and
PNG digest all match. The failure is the task-origin provenance condition,
not evidence of corrupted photo pixels or wrong edit targeting. Nevertheless,
P002 is **not trusted for use/acceptance**: replay recorded failure while the
conversation baseline had already advanced. Offline assessment reports this
baseline/outcome mismatch and an incomplete replay. Do not claim the baseline
stayed unchanged after this failure.

The corrected-question-after-invalid-origin case needs a separately approved
fix/review. No state repair, intent rewrite, guard bypass or further live calls
were attempted. Original P001, raw P002 and all events remain intact.

## Timing and usage

Generation HTTP request-attempt durations, seconds, from saved stage/effort/
duration fields; excludes interpretation/authentication/rendering:

| Operation | High | Low |
|---|---:|---:|
| 03 initial | 35.75 | 4.23 |
| 03 multi-photo edit | 12.59 | 2.55 |
| 03 corner edit | 2.38 | 3.88 |
| 04 initial | 39.06 | 4.44 |
| 04 border edit | 2.89 | 2.14 |
| 05 initial | 19.75 | 4.27 |
| 05 answer/edit | 5.02 | 2.59, failed final audit |
| Initial median, n=3 each | **35.75** | **4.27** |
| Paired completed edit median, n=3 each (03/04 only) | **2.89** | **2.55** |

All seven generation requests per candidate completed at the provider, with
no generation corrections. The low-05 failed workflow's request/usage is
retained above, not treated as a faster successful edit. Simple edits did not
uniformly improve: the low corner edit took longer. No generation occurs for
questions or exact selection.

Recorded full message durations, including interpretation/corrections/local
work, but excluding CLI startup between invocations:

| Case, message order | High seconds | Low seconds |
|---|---|---|
| 03 initial / multi-edit / corners | 56.67 / 22.55 / 11.03 | 35.56 / 18.08 / 19.84 |
| 04 initial / borders / return | 51.36 / 11.53 / 6.59 | 38.84 / 18.17 / 11.45 |
| 05 initial / question / answer | 40.64 / 6.56 / 23.55 | 31.77 / 17.58 / **22.14 failed** |
| Sum of recorded executions | 230.49 | 213.44 |

These unequal completion outcomes do not justify an end-to-end speed claim.
Generation request totals were 117.44s high / 24.09s low, including the failed
low workflow's completed generation. No service/timeout waits occurred;
interpretation correction waits are included in the message timings.

| Known usage | High | Low |
|---|---:|---:|
| Calls | 17 | 19 |
| All input / output | 97,058 / 32,608 | 106,939 / 11,852 |
| All reasoning tokens | 29,993 | 9,061 |
| Generation input / output | 46,181 / 24,642 | 46,177 / 3,346 |
| Generation reasoning tokens | 22,731 | 1,446 |
| Unknown-usage attempts | None | None |

Reasoning is included in output. Cached input: 58,112 high / 83,456 low
overall; 25,344 / 30,720 generation-only. No monetary saving is inferred.
Within this second freeze, initial low generation was substantially faster
without observed targeting degradation on the completed paired tasks.
Comparison with 010d shows improved observed binding/navigation outcomes, not
a controlled cross-implementation latency result. Small samples, fixed
high-then-low ordering, different generated baselines and the blocker limit
the conclusion.

## Guard accounting, preservation and evidence

One fresh shared ceiling: **36/200 calls**. No unguarded inference, explicit
failed-step retry, matched repeat, counter reset or extra pass after the
provenance stop. Unused allowance is closed. Interpretation remained high;
generation was the only reasoning variable. Defaults remain high unchanged.

HEAD `b0465c98a2ce99ce759faae37658054a11ba8146`, branch `nkelly/plan-010`.
Working-file hashes captured the unstaged implementation over the user's
existing staging. All **50 frozen files**, **975 original photo/runtime files**,
staged entries, HEAD/branch, closed 010d documents and its **262 sealed evidence
files** were preserved. No Git writes or old-data recovery/migration. Generation
prompt, renderer, dependency manifests, layout schema/guide and sequences stayed
unchanged. No code/test/prompt changes after the second freeze.

Session evidence root: `files\010e-evaluation-01`. It contains `before.json`,
`freeze.json`, offline reproduction/targeted/full logs, offline sequence checks,
per-invocation verification logs, candidate transition/stop/final preservation
records, and `provenance-blocker.json`.

`data\users\local-dev\projects\p010e-{high,low}-{03,04,05}` preserves reports,
steps/contexts, `replay\assessments\0001.json`, raw events, proposals/PNGs and
request attempts. Pre-answer stdout/state snapshots retain both clarification
boundaries. `measurements.json` contains exact per-request timings/usage,
authored changes, report hashes and selection hash checks;
`evidence-sha256.json` seals the new pass.

Evidence-manifest SHA-256:
`d1b2f0e25d39f5c5558ce2b6c2fd13912e779f710ff67e2e1fef6c67d0565555`.

Stop for review of the provenance blocker before further execution or a default
decision. The later separately approved interpretation high/low comparison
remains required; neither it nor a human trial is authorized by this handoff.
