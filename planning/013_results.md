# 013 results: Branch correctness and security review

**Status:** Executed and closed. One confirmed correctness defect was repaired
and re-reviewed. No confirmed security vulnerabilities or remaining significant
findings requiring an architectural/breaking change were identified.
Scope: [013 brief](013-branch-correctness-and-security-review.md).

## Captured comparison and coverage

Baseline `nkelly/llm-wip-1`:
`ec1432fb82cfc7f7ac836235e6b161373bdc364e`.
Target `nkelly/plan-010`:
`93c28567a026a7bef7d3e3d687a0df894a1a6ad6`.
The baseline is the merge base and an ancestor of the target.
The initial review covered the complete committed branch delta, not only 012.
Repairs below are separate, uncommitted working-tree changes.

Dedicated security and lifecycle correctness reviewers were used, with direct
review of request/provider guards, deadlines, stage settings, replay/assessment,
CLI presentation and their changed tests. Unchanged persistence, path containment,
ownership, validation, rendering and acceptance dependencies were traced where
needed. Prompts, examples and current documentation were checked against the
intended contracts; historical plans were context, not current specifications.
This was not another design-effectiveness or composition-quality reassessment.

## Correctness finding: repaired

**Medium severity; high confidence.**
`ai_collage\conversation.py:198-203`, in `_validate_proposal`.

An invalid initial interpretation followed by a valid teaching-plus-layout
correction creates a naming receipt. After restart and approval, generation
completes but publication fails with
`Proposal recipe, geometry, or preview identity mismatch`.
Approved names remain saved while the requested proposal is not published.
Both fresh composition and editing were reproduced offline.

The correction-origin check recognized validated `intent` and `question`
events but omitted `name_confirmation`, although that outcome was already valid
for an uncorrected task origin. The approval's wording is not the original
request, so it cannot supply the missing correction-origin evidence.

The surgical repair recognizes `name_confirmation` in that existing check.
Task identity, original wording, interpretation stage, exact confirmed intent,
source and all recipe/geometry/preview checks remain intact. No contract,
architecture or intended-functionality change was needed.

Two new regressions in `tests\test_agent.py:1758-1791` failed at publication before
the repair and pass afterward. They cover fresh/edit correction, receipt,
restart, approval, publication, retained task/source, prior PNG preservation and
no implicit acceptance. Focused re-review found no significant issues in the fix.

## Security findings

| # | Severity | File | Lines | Vulnerability | Confidence |
|---|----------|------|-------|---------------|------------|
| - | - | - | - | No confirmed vulnerabilities in the reviewed delta | - |

Review covered untrusted user/model claims, stored-record integrity, naming
receipts and navigation authority, path/owner isolation, unsafe execution/writes,
and credential/privacy handling. The security reviewer reported 18 successful
isolated in-memory checks with network access blocked.

These conclusions apply to the documented local, single-writer, metadata-only
workflow. Consistency hashes do not authenticate coordinated hostile rewrites
by someone already controlling the files. A future hosted multi-user service,
live model semantics and all possible adversarial inputs remain outside this
review's assurance.

## Verification, preservation and closure

The parent consumer/request/recovery run passed **127 tests**. The focused repair
and existing provenance/naming/replay checks passed **12 tests**; the reviewer
also rechecked the repair. The final full existing offline suite passed
**580 tests**. Counts overlap and are not additive. No live evaluation was run.

Fresh preservation checks cover **1,242** original/project files and **1,647**
files in nine prior evidence roots, including the closed 012 retest. Branch tips,
HEAD, staging/index fingerprints, dependencies and runtime were preserved.
The user's pre-existing staged 013 brief/index changes were not altered in the
index. Only the repair, its tests and this phase's documentation changed in the
working tree.

Session evidence is under `files\013-review`: `baseline.json`,
`review-notes.json`, the failing pre-repair regressions, successful focused/full
test logs and final preservation record.
No Git writes, dependency installs, contract-version changes, original-photo
changes, archived-project recovery or application model/cloud calls occurred.
Fixes remain uncommitted for the user. This closes 013, not permission for more
repairs, refactoring, live trials or branch integration.
