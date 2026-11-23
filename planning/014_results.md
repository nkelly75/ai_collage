# 014 results: Correctness and security review before main

**Status:** Executed and closed. Two medium correctness defects were reproduced,
surgically repaired and re-reviewed. No confirmed security vulnerabilities or
remaining significant findings requiring discussion were identified.
Scope: [014 brief](014-main-readiness-review.md). Repairs remain uncommitted;
review completion is not approval to merge or refactor.

## Captured comparison and coverage

Destination `main`: `ec7565f294ba956234d1f5108aa70fd8eccf7d42`.
Target `nkelly/llm-wip-1`: `7d912e29c64a5759e48cc4cde7b37e0184ea68aa`.
The merge base equals main: 13 target-only commits, no destination-only commits
or divergence. The committed tree difference spans 86 files; review covered
the complete application delta, including changes predating the narrower
[013 review](013_results.md), not just its repair.

Dedicated security and agent-correctness reviewers complemented direct review
of deterministic models, centre/pixel geometry, bounds feedback, storage and
dependent rendering/import helpers. Coverage included conversation/task/source
identity, naming approval, recovery, explicit acceptance, request/provider limits
and privacy, replay/assessment, CLI wiring, changed tests, configuration,
schemas, examples and current documentation. Historical plans supplied context,
not current contracts or permission for evaluation.

The findings below are defects in the new agent subsystem relative to main;
this comparison does not establish which intermediate phase introduced them.
Working-tree repairs are separate from the captured target and the user's
pre-existing staged 014 brief/index.

## Correctness findings: repaired

Both findings are **medium severity, high confidence**.
Line references here identify the captured committed target.

| Finding | Location | Trigger and impact | Surgical repair |
|---|---|---|---|
| Unfinished continuation lost after interpretation failure | `ai_collage\conversation.py:520-521,548-550`; `ai_collage\task_history.py:84-92` | A service error or interpretation timeout while answering a clarification or resuming a generation timeout hides the pending task. A later answer becomes a new task, or `resume` loses the confirmed original source. | Skip interpretation errors when locating pending work; permit continuation of a question/timeout through those errors without reopening completed tasks. |
| Older retry loses original clarification answers | `ai_collage\conversation.py:449-458` | Retrying a proposal after its task leaves recent history restores its request/source but omits its clarification answers from generation context. The model no longer receives the complete task being repeated. | Pin generation's active task to the resolved originating task and retain its answers alongside the current retry's feedback/answers. |

Eight focused regression cases failed before repair for the expected missing
continuation/origin evidence and pass afterward. They cover service errors,
I/O errors and timeouts, repeated failures with a validation correction,
restart, an older source distinct from the current baseline, and fresh/edit
retries outside recent history. The edit-retry case also clarifies the current
retry, retaining both sets of answers.

Existing independent-replacement coverage was extended through an interpretation
failure. Prior previews and explicit-acceptance boundaries remain unchanged.
No new automatic retries, request allowance, contract version, naming authority,
recipe repair or layout behaviour was added. The [CLI guide](../docs/cli-guide.md)
now states these recovery/context guarantees. Focused correctness and security
re-review found no significant issues in either repair.

## Security findings and limits

| # | Severity | File | Lines | Vulnerability | Confidence |
|---|----------|------|-------|---------------|------------|
| - | - | - | - | No confirmed vulnerabilities in the reviewed delta or repairs | - |

The security reviewer reported 94 successful isolated in-memory checks for the
committed comparison and eight for the repairs, with networking blocked and
synthetic/mocked inputs. These are review probes, not additional live trials.

Assurance is limited to the documented local, single-writer, metadata-only CLI.
Consistency hashes do not authenticate coordinated hostile filesystem rewrites.
No live model reliability claim, exhaustive decoder fuzzing, dependency
vulnerability verification or comprehensive audit of historical narratives/
binary evidence is implied. This was not a composition-effectiveness review
or approval for a hosted multi-user service.

## Verification, preservation and closure

The original full offline suite passed **580 tests**. The final repaired state
passed **588 tests**, including the eight new regression cases. The parent
focused repair run passed 56 tests; the correctness reviewer reported 294 scoped
tests before repair and 70 focused checks afterward. Counts overlap and are
not additive.

Direct deterministic verification passed 270 tests. A seeded offline probe
checked 3,822 advertised safe placement endpoints across 1,200 generated geometry
cases without failure. The generated layout schema matches the models; all
seven example recipes and five sequence definitions validated offline.
These checks do not exhaust numeric inputs or establish live semantic success.

Preservation checks cover 1,242 original/project files and 1,656 prior evidence
files, including the closed 013 record. Branch tips, HEAD, index/staged-diff
fingerprints, dependencies and runtime were preserved. Only the two production
files, two test files, directly related CLI-guide text and 014/index documentation
changed in the working tree; nothing was staged.

Session evidence is under `files\014-review`: baseline/preservation records,
review notes, the failing regressions, focused/full test logs and bounds probe.
No Git writes, live application model/cloud calls, installs/downloads,
original-photo changes or recovery/mutation of existing projects occurred.
Mechanical package refactoring was excluded. This closes 014; further
refactoring, live evaluation and integration require separate approval.
