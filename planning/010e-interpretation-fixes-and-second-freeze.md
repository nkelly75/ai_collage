# 010e: Interpretation fixes and second-frozen generation comparison

**Status:** Offline fixes executed; second-frozen comparison stopped and closed
on a new provenance blocker. See [010e results](010e_results.md).
A subsequent targeted provenance fix is implemented and verified offline.
The **third-freeze follow-up (D-F below) is executed and closed**;
see [third-freeze results](010e_third_freeze_results.md).
Original A-C and all live allowances remain closed. No default change or further
execution is authorized.
[010d](010d-bounded-reasoning-evaluation.md) and its [results](010d_results.md)
remain closed, unchanged evidence.

## Original approval boundary (A-C, closed)

The original approval covered stages A-C below: offline fixes, then the frozen
live comparison once the offline gate passed, then reporting. That execution
is closed; it does not authorize another fix pass or comparison. The retained
original approval wording was:

> Proceed with 010e's offline fixes and second-frozen generation comparison.
> Keep interpretation high, preserve 010d evidence, and stop before changing defaults.

Default changes, interpretation high/low experiments, alternative models and
exploratory human-led trials require separate approval. No Git writes are
authorized, including staging, commits, pushes or branch/history changes.

## A: General interpretation fixes, offline only

Investigate and address the three failure families recorded in 010d:

| Area | Required behavior |
|---|---|
| Learned-name references | A multi-photo edit using established names resolves the correct IDs after reopen, without unnecessary/conflicting reference metadata. |
| Proposal navigation | Ordinary ordinal/explicit-ID return requests identify the preserved proposal through supported evidence; selection does not regenerate, rerender or accept it. |
| Clarification continuation | An identity answer such as `2` to an unknown-name question learns the supported binding and completes the original edit, rather than losing it or only acknowledging the name. |

The recorded model responses are regression evidence, not proof that each
problem is application logic alone. Trace the prompt, transport schema, local
validation and task continuation together. Prefer the simplest consistent
contract/evidence handling over patching individual error strings.

Likely starting points: `ai_collage\prompts\request-intent.md`,
`agent_models.py`, `agent_provider.py`, `photo_references.py`, `task_history.py`
and `conversation.py`, with directly dependent replay/assessment code,
existing tests and documentation updated only where necessary.

Keep changes surgical and general:

- No special cases for breakfast, bridge, photo 2, P001, these exact prompts
  or these filenames. Use varied names, photo IDs and return wording in focused
  offline regression cases, including multi-photo edits and restart.
- Preserve strict photo/source identity, supported name evidence, genuine
  ambiguity handling and unrelated-field protection. Do not accept fabricated
  quotes, silently reinterpret invalid metadata, or guess unseen photo contents.
  Negative cases must still reject wrong/unknown IDs, unsupported bindings and
  ambiguous navigation.
- Exercise the actual question-answer-original-task path, not merely a successful
  naming acknowledgement. Include unsupported/conflicting answers; a valid
  answer must reach generation with the intended source and complete task.
- Do not change the generation prompt, renderer, layout contract, replay
  messages, deployment, reasoning defaults or service limits to obtain passes.
  No new inference stages, compatibility paths, evaluators or retry machinery.
  If a persisted interpretation contract must break, version only affected
  records and update dependent code/tests/docs together; archives remain untouched.
  A necessary change outside this scope requires review before proceeding.

**Offline gate:** Reproduce the observed failures with controlled responses,
add focused varied positive/negative coverage, then pass targeted checks and
the full existing offline suite before any live calls. Preserve original
photos, archived projects and deterministic rendering behavior. Record what
changed and any contract versions. Offline success does not promise live success.

At most **three unsuccessful targeted fix-and-verify cycles per blocker**.
Do not reset the count by relabelling it, weaken checks or repeat unchanged
attempts. Stop with evidence if blocked. Stage A uses **zero live calls**:
there is no live debugging/tuning loop before the freeze.

## B: Second freeze and generation-only comparison

After the offline gate, create a new isolated pass directory and fresh projects.
Capture HEAD plus working-file hashes; no commit is required. Freeze application
code/tests, interpretation and generation instructions/schemas, layout guide,
dependency manifests/effective runtime versions, sequences, source photos,
controls and preferences. Verify frozen inputs before each invocation, resume
and candidate transition. Keep 010d artifacts and original data unchanged.

Use the **unchanged 03-05 sequences and checks from 010d**, in the same order:
all three with high generation, then all three with low generation. Interpretation
remains **high throughout**, including answers/corrections. Deployment and all
other settings remain fixed. Each project has independent name/history state.
For 05, answer only the expected photo-identity question with `2`, origin
`copilot`, retaining the candidate flag on resume. Unexpected questions stop
that case; do not improvise prompts or answers.

Reuse the existing guard, with a **fresh single pass-wide 200-call ceiling**:
every live command, answer, retry and permitted matched repeat must use the
same absolute `--call-budget <010e-pass>\call-budget.json --max-calls 200`.
Never reuse/replenish 010d's closed allowance, reset the counter or dispatch
unguarded diagnostics. About 32 normal calls / a conservative 72-call primary
envelope leaves generous headroom; 200 is a ceiling, not a spending target.

Keep the existing four-call/two-interpretation caps, shared 120/180-second
stage deadlines, token limits and disabled automatic service retries.
Run sequentially using the existing replay CLI; inspect each stop.

- Failed instruction/validation cases are evidence, not retry permission.
  Preserve them and continue unaffected frozen cases unless a broader blocker
  prevents useful/safe execution.
- Allow at most **one explicit failed-step retry across the entire pass**, only
  for a clearly transient service/transport failure, using existing
  `--resume --retry`. Preserve the first failure. No authentication loops or
  retries of uncertain publication/I/O outcomes.
- If primary evidence is materially inconclusive, allow at most **one additional
  matched high/low pair for one selected sequence**, in fresh projects, with
  an explicit reason and separate results. No repeated search for a pleasing pass.
- Once frozen, **no implementation/prompt/input fixes or tuning**. A new
  defect does not reopen stage A within this approval. Stop the pass on changed
  frozen inputs, budget exhaustion, identity/integrity risk, or a blocker
  requiring scope/code changes; report partial evidence honestly.

## C: Compare, report and stop

Use existing offline integrity assessment plus manual authored-difference/
source review, as in 010d. Check learned multi-photo targets, unrelated-field
preservation, exact proposal/PNG reuse, and genuine answer-and-edit completion.
Keep raw requests, contexts, events, proposals and reports, including failures.
No new automated quality score or LLM judging.

Compare high/low **within this second freeze**. Contrast with 010d to explain
observed changes, not as a controlled timing comparison between implementations.
Judge adherence first, then generation request durations (initials and edits
separately, with sample counts), full message times, corrections/failed waits
and known usage/unknown attempts. Do not credit interpretation-only outcomes
to generation reasoning or demand identical designs/perfect repeatability.

Write concise `010e_results.md` with implementation/offline evidence, freeze
hashes, preserved data/Git staging checks, all primary outcomes, retry/repeat
accounting and the final shared counter. Update only directly related status/
documentation; do not replace 010d results. Recommend **low**, **high**, or
**inconclusive** for generation and explain remaining limitations.

**Stop for review without changing defaults**, even if low looks clearly better.
A later approved default change must retain an explicit high override.
Scripted success is not human sign-off.

## Required later follow-up: Interpretation reasoning

Plan a separately approved **interpretation high-versus-low comparison**, not
permanent high-only interpretation. It will need a bounded brief and any explicit
configuration support, with generation effort fixed at the then-selected setting.
Freeze again and judge binding, clarification/task continuation and navigation
correctness before latency/usage. Do not vary both stages together.
This follow-up, any resulting default change, and exploratory human trials
are **not authorized by approval of 010e**.

## Third-freeze follow-up

### Approval boundary (D-F only)

Execution is complete; the following is the retained approval boundary, not
permission to repeat the pass.

One new explicit approval may authorize readiness checks, one third-frozen
generation comparison, reporting and stop. It does **not** reopen A-C or authorize
more implementation fixes. Autopilot may advance through D-F without asking about
each model call, within the existing stop rules.

Suggested autopilot prompt:

> Proceed with stages D-F (the third freeze) in
> planning\010e-interpretation-fixes-and-second-freeze.md.
> Run the offline readiness gate, then the bounded live high/low generation
> comparison with interpretation high and a fresh shared 200-call ceiling.
> Preserve 010d/010e evidence and my staging. Stop and report on integrity risks,
> and stop before changing defaults. Do not make further implementation fixes.

No Git writes, default/model changes, interpretation-reasoning experiment,
human trial or additional comparison pass are authorized. The unused allowance
from either earlier comparison is not carried forward.

### D: Readiness gate on the current implementation

Use the implemented targeted fix: corrections retain the logical task origin,
and matching confirmed intent plus recipe/geometry/preview provenance are checked
before publication/baseline advancement. Its offline regression evidence is in
the session's `files\provenance-followup-01`; this is not live sign-off.

Run the **full existing offline suite** and unchanged offline sequence checks
before any live calls. Confirm coverage of a corrected question followed by an
answer, answer correction, restart/retry, supported identity bindings, and
rejection of invalid/unrelated provenance before publication. Do not add fixes,
rewrite tests or tune prompts/inputs under this approval. An offline failure or
missing required coverage stops execution for review.

At entry, before checks, capture the user's current staging, HEAD/branch,
effective settings and preservation hashes anew; verify again before freezing.
Do not require them to match an older staging snapshot. Preserve all old photos,
runtime data, closed `010d_results.md` and `010e_results.md`, and both original
sealed evaluation directories, including low-05's failed P002/state/events.
Do not resume, repair, reassess as newly successful, or overwrite that failed case.
Preserve the targeted fix's sealed offline evidence too.

### E: Third freeze and generation-only comparison

Create a new isolated pass directory, suggested `files\010e-evaluation-02`,
and fresh projects for every primary case. Freeze the **current implementation**
after D; capture and verify the same input/settings classes required by B.
Use a fresh snapshot/preservation baseline, not an old verifier that expects
the old code or staging. Earlier freeze manifests remain unchanged.

Apply B's execution rules to this new pass: unchanged sequences/checks 03-05,
all three high-generation runs first, then all three low-generation runs.
Interpretation remains **high throughout**, including answers/corrections.
Only generation effort varies; deployment, other settings and original photos
stay fixed. On each 05 run, only the expected photo-identity question may receive
the approved Copilot answer `2`, retaining the candidate flag on resume.

Use the existing guard with **one fresh shared 200-call ceiling** across every
live command, answer, permitted retry and optional matched pair:
`--call-budget <third-freeze-pass>\call-budget.json --max-calls 200`.
Do not reuse/reset/replenish an earlier counter or make unguarded diagnostics.
Retain B's four-call/two-interpretation caps, deadlines/token limits and disabled
automatic service retries. Retain its pass-wide maximum of **one clearly
transient failed-step retry** and **one justified matched high/low pair** for
one sequence; those are ceilings, not required work.

Do not manufacture invalid model responses or alter 05 to force the provenance
regression. Record whether a corrected-question path arises naturally; ordinary
live clarification success and controlled offline regression coverage are
different evidence.

No implementation/test/prompt/input changes are permitted under D-F; readiness
checks are read-only. Apply B's stop rules: ordinary adherence failures are retained evidence,
but changed frozen inputs, identity/integrity risk, uncertain publication/I/O,
budget exhaustion or a blocker requiring code/scope changes stops the pass.
No repair/retry loop for a new defect.

### F: New results and stop

Use C's assessment, authored-difference/source review and timing/usage accounting
for this pass. Report all six primary outcomes, assisted answers, corrections,
failures and actual before/after baselines; do not infer unchanged state from
a failed replay. Include retry/repeat accounting and the final shared counter.

Write **`planning\010e_third_freeze_results.md`**, seal the new pass evidence and
update only directly related status/links. Do not replace or append to the closed
`010e_results.md`, either old freeze, or earlier evidence seals.

Compare generation adherence/latency **within the third freeze**. Contrast prior
results for observed reliability changes, not controlled cross-implementation
latency. Separate successful paired operations from failed-delivery timing, and
interpretation effects from generation effort. State whether the specific
corrected-question lifecycle was covered live or only offline.

Recommend low, high or inconclusive with the remaining limitations, then
**stop for review without changing defaults**. This approval ends with that
handoff or a blocking stop; further fixes/refreezes need fresh approval.
The required later interpretation comparison and human-led trial remain separate.
