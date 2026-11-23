# 012 results: Model-led references and confirmed names

**Phase status:** Successfully completed and closed with the user's sign-off.
See [human-led trial 05 / phase closeout](012_trial05_results.md).

This record preserves the completed offline implementation pass.
Scope: [012 specification](012-model-led-references-and-confirmed-names.md),
following the selected [011 recommendation](011_results.md).
No live evaluation or branch integration was performed or authorized in that pass.

## Implemented boundary

Interpretation resolves task-local wording against confirmed labels and real
task evidence. Generated aliases, reference-source categories and deterministic
suffix/wrapper/pronoun acceptability rules are removed. Code still checks real
IDs, quoted facts, contradictory bindings, literal number/label conflicts and
cited evidence. This validates model claims, not their semantic correctness.

Explicit teaching proposes one fingerprinted, code-owned receipt. It shows every
addition/reassignment and pauses both durable writes and any associated action.
Natural-language approval commits only that exact current batch; rejection saves
nothing and cancels the unapplied action. Revision requires a new receipt.
There are no new naming slash commands. Confirmation uses interpretation and
may incur a model call; it is not an entirely local/free operation.

Multiple labels may identify one photo. Adding Daunt Books preserves bookshop;
reassigning one label does not remove others. Bare identity answers and inferred
paraphrases remain task-local, not automatically learned names. Clear edits and
exact returns without durable teaching need no naming gate.

Receipts survive restart with pinned task/source, controls, working baseline
and confirmed-name digest. Approval resumes that original action: naming-only
acknowledges, teaching-plus-edit generates, and teaching-plus-return selects the
exact saved PNG without generation. Local modifying controls/acceptance cannot
retarget a pending receipt. Invalid answers, timeout continuation and approved
names surviving a later generation failure retain truthful recovery state.

Useful, recoverable progress, not perfection, remains the goal. Ordinary edits,
resize-to-fit guidance, correction retention and recoverable-error presentation
are preserved. Naming confirmation is a deliberate memory gate, not a higher
bar for layout quality; uncertain persistence still stops rather than claiming
safe recovery.

Replay pauses explicitly at `name_confirmation`, without advancing or approving
automatically. Explicit answers retain actual decision/receipt provenance.
Assessment distinguishes pending, discarded, completed and exact-selection
outcomes while retaining source, recipe, preview and accounting checks.

## Contracts

| Contract | Current version |
|---|---|
| Conversation/state/proposal/event/acceptance intent | 7, previously 6 |
| Replay report | 8, previously 7 |
| Replay step / assessment report | 6, previously 5 |
| Request attempt | 2, unchanged |
| Layout / project | 3, unchanged |
| Sequence / preferences / controls | 1, unchanged |

Unsupported old records are rejected explicitly. Archives remain untouched;
there are no migrations, compatibility shims or parallel legacy paths.
Use fresh projects for later evaluation.

## Offline verification and review

The final frozen implementation passed **576 tests** with
`.\.venv\Scripts\python.exe -m pytest -q --tb=short`.
The closing conversation/history/replay/recovery run passed **259 tests**.
All five existing sequence definitions passed offline `--check`, unchanged.
These checks are not live replays or human sign-off.

One bounded read-only code review found and prompted fixes for reopening a
receipt-bound task after an interpretation error and incorrectly generating
after teaching-plus-exact-return approval. Five focused regressions passed,
including teaching-plus-retry retaining the original source.
A closing factual check reproduced conflicting literal numbers/labels being
accepted inside quoted phrases. Reusing literal number/name recognition now
rejects those bindings; photo-number labels also cannot contradict stable IDs.
These are factual guards, not a restored synonym or wrapper engine.

Controlled cases cover spelling/paraphrase bindings, padded numbers, multiple
labels, four user-described beach photos, numeric clarification without learning,
exact additions/replacements, approval/rejection/revision, stale decisions,
independent replacement, restart, tampering/interrupted writes, failure after
approval and dependent replay/assessment outcomes.

Thirteen obsolete interpretation test functions and one helper were retired:
source tags, generated aliases, literal shortening/collision policy, implicit
numeric learning, old confirmation fields and deterministic semantic-guess
policing. Relevant factual, lifecycle, provenance, accounting and recovery
responsibilities were adapted or replaced. All deterministic layout, geometry,
rendering, crop/tilt/stacking, storage and original-photo test files were retained
unchanged. Suite size was not the acceptance goal.

## Simplicity trade-off

`photo_references.py` decreased from 320 to 215 lines; the interpretation prompt
from 199 to 171. Reference/name contracts and language-rule responsibilities are
simpler. However, the eight affected Python files plus that prompt grew by
**114 lines overall**: confirmed memory needs receipt state, audit, continuation,
UI and consumer handling. This is **not a smaller overall implementation**.
Remaining lexical logic covers literal numbers/labels and existing navigation;
there is no new approval phrase dictionary, semantic-search service or framework.

The coherence gain is clearer ownership: model-led meaning, code-owned facts
and state, and explicit lasting memory. Durable-name/task safeguards are stronger;
better live interpretation or smoother interaction had not yet been established
at the offline handoff.

## Preservation and accounting

The final preservation check matched the fresh entry baseline:
**1,154 original/project files** and **1,248 sealed evidence files**, including
their aggregate hashes, are unchanged. HEAD remains
`ae9086e6f409cd5dd244b54cf74f9509ff66121c` on `nkelly/plan-010`;
the user's staging fingerprint is unchanged. No Git writes were performed.
Tests used temporary fixtures, not old trial projects or accepted images.

**Zero live model/service calls; no dependency installs/downloads.** Deployment,
reasoning defaults, deadlines, call/token guards, dependency manifests and
deterministic rendering modules remain unchanged. No layout tuning, package
refactor, vision, merge or PR was included.

Session evidence includes `012-baseline.json`, `012-preservation-after.json`,
`012-test-retirement.json`, `012-focused-review.json`,
`012-responsibility-comparison.json`, `012-sequence-checks.txt`,
`012-literal-conflicts.txt`, `012-offline-tests-complete.txt` and the matching
`012-tested-diff-complete.sha1`. The tested source diff was rechecked at closeout.

## Limitations and human handoff

Controlled responses cannot establish live semantic quality. The model may
misread paraphrases, competing targets, explicit teaching, independent replacement
or approval language; receipt integrity does not prove what "Yes" meant.
Confirmation adds interaction/call cost. Interrupted naming writes deliberately
stop for inspection rather than implementing a new recovery framework.
Broader `nudge`/compound-return navigation remains deferred.

The offline handoff required separately authorized replay evaluation and another
human-led trial before branch changes, PRs or merges. Those later runs and their
service budgets were not authorized by the implementation pass itself.

## Subsequent evaluation and phase closure

The [five-sequence replay follow-up](012_replay_results.md) retained a genuine
exact-return failure. The separately approved
[surgical repair and focused retest](012_return_repair_results.md) then completed
three fresh replay 04 runs without corrections; neither record is superseded
or rewritten by phase success.

[Human-led trial 05](012_trial05_results.md) reached P011. The user reported that
the trial went really well and the solution felt more reliable and predictable,
accepted the final compliment blip, and explicitly requested successful closure
of 012. This supports the bounded phase outcome and preserved recoverable-progress
goal, not a guarantee of general semantic reliability or broader Phase 1 completion.
Further fixes, trials, refactoring and branch integration are not initiated by
this closeout; the user will handle the commit.
