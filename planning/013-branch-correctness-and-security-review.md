# 013: Branch correctness and security review

**Status:** Review executed and closed; see [013 results](013_results.md).
One straightforward correctness defect was fixed and re-reviewed; no confirmed
security vulnerabilities were found. The scope below retains the approved
review/fix boundary, not authorization for further work.

## Purpose and comparison

Review the latest committed `nkelly/plan-010` against the starting branch,
`nkelly/llm-wip-1`, for correctness regressions and security vulnerabilities.
Cover the whole branch change, not just 012. Record both tip SHAs and confirm
ancestry at review start; use their committed trees for the initial comparison.
Keep subsequent working-tree fixes distinct from that baseline and from any
pre-existing staged or unstaged user changes.

[011](011-interpretation-and-naming-reassessment.md) already reassessed design
effectiveness, and [012](012_trial05_results.md) closed successfully after
implementation and human evaluation. Do not reopen that design exercise,
composition quality or isolated wording preferences without a concrete defect.
Passing tests and successful trials are evidence, not substitutes for review.

## Review priorities

- State and lifecycle correctness: task/source identity, clarification,
  confirmed-name approval, restart, interrupted writes, failure recovery,
  exact returns and explicit acceptance.
- Contract and consumer consistency: validation, version rejection, history,
  replay/assessment truthfulness, accounting and directly affected callers.
- Security boundaries: untrusted user/model input and stored records, path and
  owner/project isolation, unsafe writes or execution, secrets/privacy in
  requests and logs, and model claims bypassing code-owned authority.
- Relevant test coverage, including removed safeguards and error paths.
  Consult unchanged code where needed to understand a changed boundary.

Judge security against the actual local CLI and metadata-only model workflow,
not hypothetical deployed services. Distinguish introduced regressions,
pre-existing issues newly exposed by changes, and already documented limitations.
Do not turn unrelated old issues or style preferences into this phase's scope.

## Method and deliverable

Trace the changed code and its dependent paths. Use dedicated security review
and suitable focused correctness review capabilities sparingly. Existing offline
tests or small isolated probes may verify concrete concerns; no tuning campaign.

## Fix boundary and iteration

Apply obvious, well-understood bugs' straightforward fixes when they preserve
intended functionality and do not significantly change behaviour or structure.
Keep changes surgical, including directly related tests and documentation.
Verify fixes offline, preferably with a regression that fails before the repair;
re-review the affected paths and repeat as needed within this same scope.
Run broader existing checks when shared invariants warrant them.

Pause and discuss significant functionality changes, architectural redesign,
breaking contracts, migrations or fixes with uncertain/wider consequences.
Do not make speculative repairs or turn iteration into an open-ended redesign.
If the safe repair boundary is unclear, report the finding rather than patching.

Write a concise `013_results.md` with the captured comparison, coverage and
prioritized findings. Each finding needs branch file/line references, triggering
conditions, impact, supporting evidence/confidence and a minimal repair direction.
Separate confirmed defects from unresolved questions; say explicitly if there
are no confirmed findings. Record applied fixes, their verification/re-review,
remaining findings and meaningful coverage limits. Finish with the report, or
pause for the user's decision when a significant issue blocks safe completion.

## Guardrails

Zero live application model/cloud calls or implicit dependency downloads.
Application, prompt, test and documentation edits are allowed only for fixes
within the boundary above. No dependency or contract-version changes without
discussion. Tests/probes use temporary fixtures, not existing project recovery.

No Git writes, checkout, fetch, branches, commits, PRs, merges or broad refactoring.
Preserve staging, original photos, accepted versions, trial data and sealed
evidence. Leave fixes uncommitted for the user; neither findings nor iteration
authorize live evaluation or work outside this review.
