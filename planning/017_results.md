# 017 results: Conversational photo identity memory

**Status:** Successfully completed and closed with the user's sign-off.
The latest authorized replay, `p017-replay-06c`, completed all ten
objectives. The subsequent human-led trial `p17-human-07` exposed a numeric
multi-mapping validation defect; its separately authorized narrow offline repair
passed **631 tests** and is now live-confirmed by the user's continuation.
The trial reached **P012**, including listing, confirmed reassignment, forgetting
and fresh re-establishment without reviving an old mapping. It remains user-led
and has not been advanced by Copilot. Earlier stopped passes remain preserved.
All Copilot replay allowances are closed. This closes the bounded phase, not
general reliability or broader Phase 1; it authorizes no merge or further live calls.
Scope and stop rules remain in the [approved brief](017-conversational-photo-identity-memory.md).

## Implementation and responsibility changes

Clear user-supplied labels and identity answers now save without confirmation;
conflicting assignments retain the exact old/new receipt and whole-batch gate.
Natural-language listing is code-rendered and read-only, including while a
question, reassignment or generation-timeout continuation is pending.
Forgetting removes only the requested label, preserving photos and other labels.
Fresh user identity evidence can establish it again.

There is one normalized name table and one shared automatic/approved application
path. A null photo ID is the minimal per-label forgotten record, not another
positive-name store. Active names and forgotten status remain essential context.
Current forgetting checks cover direct labels, cited supporting chains and
copied retry/resume bindings; historical evidence is not erased. Proposal returns
do not rewind memory. No synonym engine, general fact framework, dependency,
additional model stage or larger history window was added.

Actual task events retain the original label and subsequent identity answer;
there are no synthesized combined quotes or invented approval receipts.
Audit reconstruction checks automatic writes as well as approved batches.
Memory acknowledgements remain visible if subsequent generation fails.
Rejected interpretation candidates are cleared before correction, preventing a
failed copied binding from accidentally advancing into generation.

Interpretation still owns language meaning: co-occurrence and provenance checks
cannot prove arbitrary prose was understood. Initial mistaken learning remains
a deliberate trade-off; listing, correction and forgetting make it inspectable.
Casual `bridge` wording can use `Tower Bridge` without another persisted alias.

| Contract | Current version |
|---|---|
| Conversation, event, proposal, acceptance intent | 8 |
| Replay report | 9 |
| Replay step and assessment | 7 |
| Layout/project | 3, unchanged |
| Request attempt | 2, unchanged |
| Sequence, preferences, controls | Unchanged |

Use fresh conversational projects. Version-7 conversations, including
`p15-human-06`, remain untouched archives; there is no migration or backfill.

## Offline evidence

The initial implementation's complete offline suite passed **610 tests in 401.46 seconds**,
with network-blocking fixtures. The pre-edit collection was 594; no existing
test responsibility was discarded. All six sequence definitions passed the
existing offline structure/input-availability/hash check.

Former all-additions-gated cases now start with real conflicting assignments,
retaining approval/revision/rejection, source pinning, restart, exact-return,
timeout, tampering and interrupted-write coverage. Numeric-answer cases now
assert learning and whole-task continuation. Unsupported-version assertions use
the explicit fresh-project error and include version 7. New cases cover full
listing, multiple labels, negative-state persistence beyond both history windows,
historical-only forgetting, stale citation/retry refusal, fresh re-establishment,
pending-task inspection, mixed-batch atomicity, visible memory before generation
failure and replay snapshot/resize tampering.

Sequence 06 has its own small `photo-identity-memory` assessment profile.
It reconstructs memory from actual audited events, checks pre-answer questions
and exact reassignment approval, and verifies each intended 10% width reduction
with absolute normalized-width tolerance 0.000001. Centres, unrelated authored
fields and stacking must remain unchanged. Integrity-only completion is not
treated as success on the memory story.

The scope/diff was reviewed before live execution. Baseline/preservation evidence
is in session `files\017-memory`: `baseline.json`, `authorization.json`,
`tests-verified.txt`, `sequence-checks.txt` and `preservation.json`.
The index/staged patch, HEAD/branch, interpreter/packages, engine/layout contract,
generation response format and call/token/deadline limits were preserved.
Checks cover **4,649 pre-existing protected files** and **3,598 prior evidence
files**. No Git writes, installs or preflight service/credential probes occurred.

## Replay 06: partial, stopped at the first identity answer

The frozen single pass used fresh project `p017-replay-06`, the four original
London photos, 1200x1800 whole-photo controls, `gpt-5.4-mini`, high interpretation
and low generation. The fixed story, implementation, instructions, original
inputs, settings and budgets were frozen before dispatch. All 129 frozen
repository-file hashes, runtime/packages, limits and frozen preflight evidence
still matched at pass closure, before these outcome-only documentation updates.

| Execution | Observed outcome |
|---|---|
| 1: initial composition | P001 created with all four whole photos. No names saved or version accepted. |
| 2: shrink breakfast | Asked "Which numbered photo is breakfast?" Memory, baseline and original preview stayed unchanged. |
| 3: answer `Photo 2` | Interpretation twice supplied a binding citing event 3, the preceding question, as evidence for photo 2. That question contained no photo identity. Both candidates were rejected; the bounded correction did not repair the citation. Terminal `RequestRejected`; no generation, memory write or baseline advance. |
| Remaining story | Step 2 incomplete; steps 3-10 not executed. No claims of live listing, reassignment, forgetting, re-establishment or resize success. |

The only supplemental reply was the expected fixture identity answer `Photo 2`,
recorded separately with origin `copilot` after inspecting the actual question.
There were no corrective supplemental replies or reassignment approvals.
The existing internal interpretation correction used one additional call;
after its terminal rejection, the pass stopped immediately. The CLI's exit 1
at the ordinary question was its documented paused outcome, not the terminal
failure; the saved failed outcome on the answer was the stop.

| Stage | Calls | Input tokens | Output tokens |
|---|---:|---:|---:|
| Interpretation, high | 4 | 23,046 | 6,733 |
| Generation, low | 1 | 5,957 | 747 |
| Total | **5 / 32** | **29,003** | **7,480** |

All five provider responses have known usage; there were no pending, timeout or
unknown-usage attempts. Tokens above include provider-reported usage, not the
conservative input-bound estimate. **27 unused calls and five unused supplemental
replies are closed**, not a reserve for follow-up. The durable counter remains
truthfully `used: 5`; it was not reset or increased to manufacture closure.
There were no terminal retries, post-observation implementation/prompt/sequence
changes, extra probes, replacement project or second pass.

The final baseline remains P001, active/forgotten memory is empty, acceptance is
null, and the original recipe and PNG hashes match their first milestone.
The identity-specific offline assessment records step 1 passed and step 2 failed
on the missing required memory transition. The integrity assessment reports
no per-execution integrity errors but is incomplete, not passed overall.
Neither assessment claims coverage of unexecuted messages.

### Evidence and preservation

Session `files\017-memory` contains `offline-freeze.json`, `replay-freeze.json`,
the fixed `live-policy.json`, `calls.json`, three `live-NN.txt` logs and three
`milestone-NN.json` snapshots, both `assessment-*.txt` outputs and
`pass-closure.json`. `handoff-verification.json` records final preservation.
The fresh project's `conversation` directory retains actual
events, requests, inputs/responses and P001. Its `replay\assessments\0001.json`
and `0002.json` retain the identity and integrity assessments. The closure seals
the fresh project's file hashes as well as accounting and frozen-source checks.

An offline closeout helper initially used the application's 1 MiB-limited JSON
reader for the larger session freeze inventory; only that helper was corrected
to use the ordinary JSON reader. It dispatched nothing and changed no application
code, frozen evidence or live project. The original preservation helper's final
check also flagged four normal fresh-project upload copies because it assumed
all new data files would be inside the project directory. That frozen helper was
not changed. A supplementary audit verifies every pre-existing hash and permits
only the sealed replay directory plus the four exact imported files referenced
by its project, each matching its frozen original-photo hash.
The terminal milestone inspector's assertion intentionally recorded and stopped
on the failed required transition. Final checks preserve the user's index/staged
patch, branch/HEAD, all original photos, existing projects and prior sealed evidence.

## Handoff

The reduced naming ceremony and recovery safeguards are implemented and covered
offline, but this pass did **not** demonstrate the main conversational learning
path working live. The guard correctly refused unsupported evidence and left
state intact; that does not make the user-facing failure a success or establish
human-trial readiness. Review the saved citation failure before deciding the next
bounded work. Any further fix or live evaluation requires separate authorization.
No acceptance, Git write, upgrade of `p15-human-06` or human trial was initiated.

## Separately authorized offline citation-guidance repair

After reviewing the failed pass, the user authorized a small prompt/diagnostic
repair and regression coverage, explicitly excluding a replay-06 rerun.
The interpretation prompt now distinguishes a pending question's conversation ID
from supplied historical identity evidence. Direct numbered wording/numeric
answers need no historical citation. A complete edit-and-learning example shows
the binding and name update together, without fabricating a citation or quote.

Invalid citations are still rejected, with no silent stripping or relaxed
provenance checks. Feedback now identifies `references[index].event_id`, the
cited event and photo, and explains when to omit that field or cite actual
`reference_history` evidence. There is no new inference stage, parser, contract
version, history window or correction/call allowance.

Two regression cases reproduce the actual empty-reference question and short
`Photo 2` answer. Repeated bad citations leave memory/baseline unchanged and never
reach generation. Removing only the invalid citation in the controlled correction
saves breakfast automatically and continues the complete resize from its original
source. Correction context retains the short answer, failed candidate and
unchanged pre-correction memory/baseline; the original preview and acceptance
remain untouched. These are controlled-response checks, not proof of live-model
compliance.

The focused offline run passed **36 tests**, including the new cases, numeric/
multi-question continuation, restart/correction, and the complete task-history
suite's valid and invalid supporting-citation checks. Evidence and a fresh
staging/protected-file baseline are in session `files\017-citation-guidance`.
The original replay evidence and closed five-call counter remain unchanged.
No live call, replay resume/retry, acceptance, Git write or human trial occurred;
live validation of this repair still requires separate authorization.

## Separately authorized replay-06 repeat

The user then authorized another pass with a similar budget. It used fresh
`p017-replay-06b`, the unchanged ten-message sequence, original four photos,
1200x1800 whole-photo controls, `gpt-5.4-mini`, high interpretation/low generation,
and a fresh 32-call ceiling with at most six scoped replies/two per step.
The complete offline suite passed **612 tests in 394.74 seconds** and all six
sequence definitions passed offline validation before freezing this pass's
implementation, instructions, inputs, settings, expected checks and budget.

### Observed progress and assessment stop

P001 was created without invented names. On the first breakfast resize request,
the model asked **"Which photo is breakfast (1, 2, 3, or 4)?"**. Its recorded
`references` array was empty. Memory, baseline and preview were unchanged before
the permitted Copilot-origin answer **"Photo 2"**.

The first interpretation of that answer copied the prompt example's quote
`Make breakfast smaller` rather than the actual user request. Existing quote
validation rejected it. One bounded internal correction supplied the real quote,
without repeating the old invalid question citation. The application then
automatically saved **breakfast = 2**, without a naming confirmation, and generated
P002 from P001. Photo 2's width changed **0.38 -> 0.342**; an independent saved-
recipe comparison verifies its centre, every other authored field and stacking
were unchanged. Acceptance remains null. The previous citation blocker did not
recur; this is useful progress, not a clean correction-free run.

The frozen `photo-identity-memory` assessment nevertheless rejected step 2:
`Breakfast identity was used without the required preceding question.`
Its `identity_memory_errors` predicate requires an unresolved `breakfast`
reference inside the earlier question event; it does not recognize this real,
clearly worded question with `references: []`. The question action permits that
empty array. This is an overly strict assessment condition, not evidence that
the question was absent or the target/resize was wrong.

The pass stopped at that failed frozen check. No checker relaxation, application/
prompt/sequence edit, further dispatch or replacement pass followed. The saved
application outcome remains truthfully `proposal`, not an invented terminal
application failure. Step 1 passes assessment; step 2 fails that question check
only. Steps 3-10 were not executed. Both offline assessment reports are incomplete;
the integrity report has no per-execution errors. Listing, reassignment, forgetting
and re-establishment still have no live coverage from these two passes.

### Accounting, evidence and handoff

| Stage | Calls | Input tokens | Output tokens |
|---|---:|---:|---:|
| Interpretation, high | 4 | 23,388 | 1,917 |
| Generation, low | 2 | 13,297 | 883 |
| Total | **6 / 32** | **36,685** | **2,800** |

All usage is known; no service failures, timeouts, pending attempts or terminal
retries occurred. One expected identity answer used one of six supplemental
replies; no corrective Copilot reply or approval was supplied. The one internal
quote correction consumed its normal call. **26 unused calls and five unused
supplemental replies are closed**. Neither this allowance nor the earlier pass's
27 closed calls are available for continuation.

Session `files\017-replay-06b` holds the fresh baseline/freeze, unchanged
inspection helper, full-suite log, three invocation logs and milestones, both
offline assessment outputs, exact usage/project hashes in `pass-closure.json`,
and final `preservation.json`. The fresh project's actual events, requests,
P001/P002 and append-only assessments remain intact. Preservation checks cover
the user's staging/HEAD/branch, all pre-existing photos/projects, previous phase
evidence, source contracts and settings; new upload copies must match the four
frozen inputs exactly. Only outcome documentation changes after the freeze.

The learning/whole-task continuation now has successful live evidence after an
ordinary internal correction. The complete memory story remains unverified.
Review the assessment mismatch before authorizing a checker repair or another
bounded evaluation; no such follow-up or human trial was initiated.

## Assessment repair and completed replay 06c

The user authorized the offline repair followed by another replay, explicitly
deferring the full offline regression suite. The repair changes only the
identity profile's clarification predicate: the answer must link to an earlier
question execution in the same scripted step and actual conversation task.
The event must really be a question. Optional unresolved-reference metadata is
not required. Existing question/event integrity, answer provenance, pre-answer
memory/layout preservation, exact receipt, target, resize and unrelated-field
checks remain. No wording parser or extra model judge was added; the actual
questions were also reviewed during the pass.

Regression coverage now accepts both legal question encodings and rejects a
missing question, another step/task, a non-question event, absent/mislinked
answers, premature memory writes and premature layout changes. Existing wrong-
target, wrong-size, centre and tampered-snapshot negatives remain.
An initial assessment/replay-file run passed 92 cases; two new negative fixtures
incorrectly attempted to mutate frozen events. Those fixtures were corrected
to use copies. The final focused identity checks passed **14 cases**.
At that point the full suite was **not rerun**; its last 612-test result predated
this assessment repair. The subsequent full regression is recorded below.

The saved 06b run was reassessed entirely read-only. Its completed composition
and first learning/resize now pass, with only the expected incomplete-replay
error for unexecuted steps. The new result and checker hash are in session
`files\017-replay-06c\reassessment-06b.json`; its original reports and every
previously sealed project/evidence file remain unchanged.

### Frozen live pass and observed story

Fresh project `p017-replay-06c` used the unchanged ten-message sequence, original
four photos, 1200x1800 whole-photo controls, `gpt-5.4-mini`, high interpretation/
low generation and a fresh 32-call/six-reply ceiling. Six sequence definitions,
the focused results, repaired source, instructions, input hashes, settings,
expected checks, helper and budget were frozen before dispatch. There was no
post-observation tuning.

| Step | Observed result |
|---|---|
| 1 | P001 with all four whole photos; no names invented. |
| 2 | Asked which numbered photo was breakfast before `Photo 2`; saved breakfast = 2 automatically and published P002, shrinking only photo 2. |
| 3 | Listed breakfast = 2; no layout generation or mutation. |
| 4 | Saved favourite = 1 without a gate or layout change. |
| 5 | Displayed only favourite = 4 (was 1), held state unchanged, then applied the reviewed receipt after `Yes`; breakfast remained 2. |
| 6 | Reopened and shrank photo 4, not photo 1, producing P003. |
| 7 | Forgot breakfast only; favourite stayed 4 and the collage stayed P003. |
| 8 | Reopened and listed favourite = 4 only, retaining the breakfast tombstone. |
| 9 | Asked which photo breakfast meant now, before a fresh `Photo 2`; then re-established breakfast = 2 and published P004 with only its second resize. |
| 10 | Reopened and listed breakfast = 2 and favourite = 4; no extra layout change. |

Both `photo-identity-memory` and `integrity` assessments are complete and passed.
An independent full authored-recipe comparison verifies the three intended
width changes: photo 2 **0.38 -> 0.342**, photo 4 **0.38 -> 0.342**, and photo 2
**0.342 -> 0.3078**. Centres, all other authored fields and stacking remained
unchanged at each edit. Memory-only operations preserved the baseline and all
recipe/PNG hashes; final baseline is P004 and acceptance remains null.
The post-forgetting question had empty `references`, exercising the repaired
assessment condition in the real run.

### Accounting, classification and preservation

| Stage | Calls | Input tokens | Output tokens |
|---|---:|---:|---:|
| Interpretation, high | 13 | 84,788 | 11,941 |
| Generation, low | 4 | 29,532 | 1,488 |
| Total | **17 / 32** | **114,320** | **13,429** |

This was **clean scripted completion with normal expected answers/confirmation**:
two `Photo 2` identity answers and one `Yes` approving the inspected exact receipt.
All three replies have origin `copilot` and were supplied only after inspecting
their actual gates. There were **zero** internal validation corrections,
corrective Copilot replies, service failures, timeouts, terminal retries or
unknown-usage attempts. The assessments' `clarification_assisted: true` flag
records those ordinary answers; it does not mean misunderstanding recovery was
needed. **15 unused calls and three unused replies are closed**, with the
durable counter truthfully left at 17.

Session `files\017-replay-06c` retains baseline/freeze, focused test logs,
the separate 06b reassessment, thirteen invocation logs and milestones, both
final assessments, `pass-closure.json` and final preservation/handoff hashes.
The fresh project retains all actual conversation/request/context/answer data,
four immutable proposals and append-only assessments. Pre-existing projects,
photos, original assessments/evidence and the user's index/staged patch, branch
and HEAD are preserved. No Git writes, installs or additional live pass occurred.

This completes the scripted story, not phase sign-off or general language
reliability. At pass closure, the full offline regression check remained deferred;
a separately human-led fresh trial remained outstanding and was not started.

## Full offline regression follow-up

The user subsequently authorized the deferred complete offline regression.
The documented command passed **621 tests in 392.54 seconds**, with no failures
or skips:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider
```

This validates the application/test tree after the assessment repair, rather
than relying on the earlier 612-test result. Existing network-blocking fixtures
remained active, and the runner removed Azure/OpenAI environment variables.
No live calls, installs or application/test changes were made.

Session `files\017-full-regression` retains `run.py`, `baseline.json`,
`pytest.txt` and `verification.json`. Exact before/after preservation passed for
repository files, the index/staged patch, HEAD/branch and runtime/packages,
**4,815 protected files** and **3,686 prior evidence files**. Subsequent tracker
updates are documentation-only; previous sealed replay evidence is unchanged.

At this checkpoint, implementation, the scripted story and the full offline
gate were complete. This supported another human-led trial, not general language
reliability or phase sign-off. The user subsequently committed checkpoint
`70134f1` before starting the fresh trial below. No trial was started by the
regression run, and no live allowance was reopened.

## Human-led trial 07: narrow numeric-mapping repair

The user started fresh `p17-human-07` and created P001. For the next request,
"Swap the locations of the breakfast and london eye photos", the model asked
"Which photo IDs are the breakfast and London Eye photos?" The user's answer,
`2 for breakfast and 3 for london eye`, was clear. Both interpretation attempts
correctly bound breakfast to 2 and london eye to 3, proposed those lasting names
with the actual answer quote, and retained the swap.

The deterministic fresh-identity guard rejected both candidates: it recognized
photo-prefixed numbers and an entirely numeric single answer, but not these
explicit per-label numeric pairs. This was an application validation defect,
not another citation failure or a misunderstood answer. No names were saved,
generation was not reached, and the baseline stayed P001 with no acceptance.
The successful replay's single-name answers had not exercised this case.

The user authorized a narrow offline repair. Six added lines in the existing
guard recognize `N for <label>` evidence for that exact label during a same-task
clarification after any forgetting cutoff. They do not harvest arbitrary numbers
from prose. Known-ID, real-quote, receipt/conflict and forgetting checks remain;
there is no prompt, schema, model-stage, history-window or renderer change.

New synthetic integration cases fail before the repair and pass afterward:
both identities are saved without a receipt and the whole swap continues from
the original proposal after restart, including fresh re-learning after forgetting.
Negative cases retain rejection of quantities, percentages, signed/fractional
numbers, wrong or borrowed IDs, missing questions and pre-forgetting questions.
The final focused run passed **30 tests**; the complete offline suite passed
**631 tests in 427.52 seconds**, with network blocking and no skips or failures.
Both actual saved failed candidates also pass the repaired guard in a separate
read-only check; their original events and trial state were not rewritten.

Session `files\017-human07-mapping` retains baseline/preservation inventories,
the pre-fix reproduction, initial and corrected focused logs, the full-suite log
and `saved-candidate-check.txt`. The first post-repair focused run exposed a new
test-fixture comparison of raw versus normalized recipe defaults; that fixture
was corrected without further production changes.
The user's staging, HEAD/branch, original photos, all pre-existing project/trial
files and prior evidence are preserved. No Git writes, installs or live calls.

At the repair handoff, the running chat process needed restarting before the
user could continue `p17-human-07` with the original answer. Copilot did not
resume the trial, create a replacement project or run another replay.
The subsequent live confirmation is recorded below; phase sign-off remains separate.

## Human-led continuation through P012

The user continued the same project after the repair. Repeating the original
`2 for breakfast and 3 for london eye` answer saved both identities automatically
and completed the original swap as P002, without a naming receipt or another
interpretation correction. The offline repair therefore now has live evidence.
Further user-authored design requests reached P009 before the memory exercises.
Casual `bridge photo` and `the eye` references resolved to photos 1 and 3 without
saving those inferred short forms as additional names.

The user then tried Copilot's three suggested memory requests, adding their own
list requests and later adjustments. Saved events and exact recipe comparisons
support the user's positive report:

| Request or checkpoint | Observed outcome |
|---|---|
| Initial name listing | Tower Bridge = 1, breakfast = 2, london eye = 3. |
| Change breakfast to photo 1 | Displayed a reassignment receipt; applied only after the user's explicit confirmation. Tower Bridge = 1 remained a separate label. |
| List, forget breakfast, list again | Listing showed the approved photo-1 assignment, then removed breakfast after forgetting while retaining the other names. Every memory-only operation stayed at P009, with no new proposal. |
| Move Daunt Books down 5% of canvas height | Asked which photo; the user's `photo 4` answer saved Daunt Books = 4 and produced P010. Only photo 4's `center_y` changed, **0.27 -> 0.32**. |
| Move the book shop back up 3% | Resolved the casual reference to photo 4 without an extra alias or gate. Only its `center_y` changed, **0.32 -> 0.29**, in P011. |
| "Tilt the breakfast photo to the right" after forgetting | Asked **"Which photo number is breakfast now?"**. Breakfast remained forgotten and the baseline stayed P011; neither the original photo-2 mapping nor the later photo-1 reassignment was silently reused. |
| "The breakfast photo is photo 2" | Re-established breakfast = 2 automatically and continued the original tilt. P012 changes only photo 2's rotation, **-2 -> +2 degrees**; all other authored fields and stacking are unchanged. |

Final active memory is **Tower Bridge = 1, breakfast = 2, london eye = 3,
Daunt Books = 4**. There is no pending naming receipt. The baseline is P012,
with twelve preserved proposals and no accepted version.
The memory audit reconstructs the saved state successfully; every proposal's
recipe and preview still match its recorded hashes.

This is useful human-led progress, not a claim that the entire trial was
correction-free. Besides the original repaired mapping failure, the earlier
additional 20% all-photo enlargement needed two bounded internal geometry
corrections before completing as P004. The later memory exercises and P010-P012
completed without further validation corrections.

Read-only inspection evidence, listing/forgetting/re-learning milestones,
exact P009-P012 recipe differences and file hashes are retained in session
`files\017-human07-results\inspection.json`. Results and status updates are
documentation-only; no application/test changes or additional test run were
needed. User staging and trial data remain unchanged by Copilot, with no live
dispatch, automatic acceptance, trial closure or phase sign-off.

## User sign-off

After the human-led continuation, the user reported committing and pushing the
fixes and stated, "I think 017 is successful." Phase 017 is therefore successfully
completed and closed within its agreed scope. Earlier no-sign-off statements
describe their respective handoffs and remain as historical evidence.

This closes neither general language reliability nor the broader Phase 1.
Replay allowances remain closed; further live calls and branch integration
require separate authorization.
