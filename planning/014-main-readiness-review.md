# 014: Correctness and security review before main

**Status:** Executed and closed; see [014 results](014_results.md).
Two correctness defects were surgically repaired and re-reviewed; no confirmed
security vulnerabilities remain. Repairs are uncommitted for the user.
Mechanical package refactoring was excluded and belongs to a later, separately
approved phase; review completion is not approval to merge.

## Purpose and comparison

Review the latest committed `nkelly/llm-wip-1` against destination branch `main`
for correctness regressions and security vulnerabilities before integration.
Capture both tip SHAs and their merge base at review start. Review the complete
committed tree difference (`main` to `nkelly/llm-wip-1`); if ancestry has diverged,
explain destination-only changes and integration risks rather than silently
substituting a merge-base comparison.

Keep any subsequent working-tree repairs distinct from the captured comparison
and pre-existing user changes. No checkout or merge is needed for review.
[013 results](013_results.md) provide prior evidence for part of this delta,
not assurance for changes predating that comparison or their interactions.

This is a traditional code review, not another design-effectiveness assessment.
Preserve the accepted direction from [011](011_results.md) and
[012](012_trial05_results.md); do not reopen composition preferences or redesign
interpretation without a concrete correctness/security issue.

## Coverage and method

Cover changed deterministic and LLM-related code, tests, configuration and
dependent documentation. Trace unchanged callers/helpers where necessary.
Priorities are rendering/geometry and original-photo integrity; persistence,
paths and ownership; task/source identity, naming approval, recovery and explicit
acceptance; contracts and dependent consumers; request limits and privacy; and
truthful replay/assessment evidence.

Use dedicated security review and suitable focused correctness review sparingly.
Judge risks against the actual local CLI, single-writer, metadata-only model
workflow, not hypothetical hosting. Distinguish introduced/newly exposed defects
from unrelated pre-existing issues and documented limitations. Tests and human
success are evidence, not substitutes for examining error paths and boundaries.

## Repairs and verification

Apply obvious, well-understood, surgical bug fixes that preserve intended
functionality without significant behavioural or structural changes. Add focused
regressions, preferably demonstrating failure before repair, and update directly
related documentation. Re-review affected paths and iterate within that boundary.
Use existing offline checks, escalating to the full suite for shared invariants
and the final repaired state.

Pause to discuss architectural changes, breaking contracts, migrations,
significant functionality changes or repairs with uncertain/wider consequences.
No speculative repairs, package moves, dependency changes or contract-version
changes. The planned deterministic/LLM sub-package separation is explicitly
not part of 014, even if it would make some code easier to review.

## Deliverable and guardrails

Write a concise `014_results.md`: captured comparison, coverage/limits,
prioritized findings with file/line references, triggering conditions, impact,
evidence/confidence, applied fixes and verification/re-review. Separate confirmed
defects from unresolved questions; explicitly report if no findings remain.
Update this tracker and the planning index at closure, or report a material
decision blocker. Review completion is not approval to merge.

Zero live application model/cloud calls or dependency downloads. Tests/probes
use isolated temporary fixtures, never recovery or mutation of existing projects.
Preserve original photos, accepted versions, trial data, sealed evidence and
the user's staging. No Git writes, fetch, checkout, branches, commits, PRs or
merges. Leave repairs uncommitted for the user. Further evaluation, package
refactoring and integration require separate approval.
