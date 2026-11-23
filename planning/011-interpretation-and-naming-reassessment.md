# 011: Interpretation and naming design reassessment

**Status:** Review approved, executed and closed for a human design decision;
see [011 results](011_results.md). No implementation or live evaluation was
performed. Any implementation needs a separately approved spec. The scope and
method below are retained as the approved review brief, not further authorization.

## Purpose

After [010](010-grounded-interpretation-and-human-trials.md), reassess whether
interpretation and naming deliver enough convenience and safety to justify
their complexity. Tested behaviour is not proof that the design is the simplest
worthwhile one. Prior investment is not a reason to retain it; fewer components
are not automatically safer or more reliable.

Seek the smallest convincing design for useful, recoverable conversation,
not another catalogue of fixes for individual awkward phrases.

## Scope and design stance

Review naming, reference grounding, ambiguity/confirmation, clarification
continuity and the responsibilities of the interpretation stage, including
its boundary with lifecycle/source selection and layout generation.

The separate interpretation responsibility is preferred: layout already has
substantial work and has performed reasonably well. Keep layout generation and
the deterministic engine outside redesign by default. Challenge the separation
only with a compelling argument, not merely to remove a model call.

Consider alternatives openly. Retaining the current design, simpler taught
names, numbers-only, and model-led language interpretation with a smaller
deterministic safety boundary are possibilities, not an exhaustive shortlist
or prescribed winner. No semantic-search infrastructure is presumed necessary.
Distinguish resolving wording for one request from permanently learning a name.

Preserve essential lifecycle behaviour: explicit acceptance, exact proposal
returns, correct older-source edits, retained tasks through clarification and
recoverable failures. Code must retain authority over persistence, valid photo/
proposal identities, controls and rendering. The model has metadata and taught
names, not knowledge of unseen image contents.

## Review method

1. Establish the committed baseline on the current branch before merges or
   structural refactoring. Trace the actual prompts, contracts, checks and
   state/context flow; identify responsibilities and coupling, not just file size.
2. Critically distinguish indispensable integrity safeguards from linguistic
   restrictions that duplicate model judgement or create avoidable friction.
   Examine plausible wrong bindings and recovery failures as well as successes.
3. Develop and compare credible alternatives, then recommend a direction.
   Explain what becomes simpler, what is removed or retained, and what user
   convenience, reliability, latency or auditability might be lost.

A rubber-duck review is useful for challenging architecture and assumptions.
Code review or another suitable focused reviewer may ground or challenge the
proposal. Use reviewers sparingly with distinct objectives; do not require a
particular tool or expand this into the later general correctness/security review.

Use committed code, tests and saved evidence, especially [trial 03](010g_results.md),
[trial 04](010g_trial04_results.md), [010h results](010h_results.md),
[replays 03-05](010h_replay_results.md) and the
[reasoning comparison](010f_results.md). Narrow offline probes may resolve a
specific uncertainty; use temporary isolated data, not existing project recovery.
Do not mistake mocked success or static reasoning for demonstrated live
language understanding. The final depth/position prompt tweak is not live-tested.

## Deliverable and decision gate

Produce a reasonably concise `011_results.md` with:

- Evidence-backed diagnosis, separating observed defects, design costs and
  hypotheses. Identify concrete code/prompt responsibilities.
- Alternatives and a justified recommendation; retaining the current design
  is valid if simpler alternatives do not earn their trade-offs.
- Representative walkthroughs covering taught/shortened or unfamiliar names,
  competing mappings, numeric answers/corrections, failed clarification recovery
  and older-proposal selection/editing. Show uncertainty handling, not just happy
  paths, without inventing special-case rules for each example.
- A clear proposed boundary between model judgement and deterministic checks,
  including persistent names, task/source authority and remaining failure modes.
- What evidence supports the recommendation, what remains unproven, and the
  smallest later implementation/validation scope, including any affected contracts.

Stop at that recommendation. Do not automatically implement, benchmark or
iterate through a tuning campaign. Escalate material integrity risks or scope
expansion rather than repairing them during this review.

## Guardrails

Zero live model/cloud calls. No application, prompt, test, dependency or contract
changes during the review; scratch offline probes are not production prototypes.
No Git writes, merges, branch changes or refactoring. Preserve staging, original
photos, accepted versions, archived projects and sealed evidence. Keep report
output separate from prior results; no compatibility loaders or migrations.
Final replays and a human-led trial belong to separately approved later work.
