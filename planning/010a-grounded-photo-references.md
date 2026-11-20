# 010a: Grounded photo references

**Status:** Implemented and verified offline under the user's approval.
See [010a results](010a_results.md) for evidence, limitations and the separately
authorized live replay follow-up. Closed; 010b and further live trials are not
authorized by this implementation.
First stage of [010](010-grounded-interpretation-and-human-trials.md).
The approved scope and guardrails below are retained as the implementation record.

## Scope and agreed behaviour

Ground photo identities before generation, using numbers, user-taught names and
clear conversational references such as "make it bigger" after discussing photo 2.
Do not add layout-based references, image understanding or general-purpose memory.

- Clarify unknown or ambiguous identities; preserve creative freedom.
  "Move photo 2 a bit right" needs no exact distance. If breakfast is known but
  bookshop is not, ask only for bookshop's number.
- Learn explicit mappings immediately, including "2" answering "Which photo
  number is breakfast?" No redundant confirmation.
- Names belong to the project across restarts and proposal returns. Allow
  multiple taught names per photo, without inventing synonyms.
- Clarify conflicting assignments; leave the existing mapping unchanged until
  resolved. Apply explicit corrections immediately, such as "I meant photo 3,
  not photo 2". Moving one name must not move that photo's other names.
- A naming-only message acknowledges the update without generation, a proposal
  or a baseline change. Naming plus an edit can do both.
- Hold the complete edit until required references are resolved. Preserve the
  original task through clarification; do not execute only its clear portion.

## Implementation boundary

- Extend typed interpretation to carry resolved photo references and proposed
  name updates with their supporting user/clarification/history evidence.
  Pass validated identities to generation. Validate photo IDs, existing bindings
  and evidence references in code; do not trust a confidence score or claim that
  code can prove every natural-language interpretation correct.
- Store compact bindings with their originating event references in conversation
  state, independent of the selected proposal; retain auditable updates.
  Compare names case-insensitively with surrounding/repeated whitespace
  normalized; preserve display wording. Do not add fuzzy synonym matching.
- Persist only validated name updates. An explicit learned fact is independent
  of layout success: a subsequent generation failure must not undo it.
  Invalid interpretation responses must not mutate names or the baseline.
- Include bindings and resolved references as essential context, not disposable
  recent-history text. Retain the current size guard; report an explicit failure
  if essential context cannot fit rather than silently forgetting names.
- Add a typed acknowledgement outcome for naming-only messages. Keep CLI,
  replay and assessment consistent: acknowledgement is not a generated proposal.
  Update affected prompts, tests and usage documentation.
- Version affected persisted conversation/replay contracts as needed, keeping
  one current implementation and rejecting unsupported records without migration.
  Preserve old evidence untouched. Layout/project format 3 is unchanged.

Proposal ledgers, return-resolution redesign and broader compaction belong to
010b. Timeout/retry-UX changes and reasoning experiments belong to 010c.
Keep current model, reasoning, input/output/time limits, per-message call limits
and no-automatic-service-retry behaviour unchanged. No new model stage or
summarization call, renderer changes, composition work, UI or cloud work.

## Offline acceptance

Use focused tests plus affected existing lifecycle, replay/integrity and
request-accounting checks. Include malformed/inconsistent model responses,
not just ideal responses. Demonstrate:

- Learning, alias reuse, explicit corrections and conflict clarification;
  persistence beyond the recent window, after restart and after proposal return.
- Naming-only acknowledgement without generation; combined naming/edit;
  complete-task clarification with a known and an unknown name; clear pronouns;
  qualitative amounts proceeding without unnecessary questions.
- Invalid IDs, contradictory bindings or invalid evidence are rejected before
  mutation/generation; resolved identities reach generation; an explicit learned
  mapping survives generation failure.
- Effective context retains bindings during size fitting. Replay and assessment
  handle acknowledgements without inventing proposals or breaking source history.

Before changes, capture the umbrella's tilted-example baseline in an isolated
session project. Afterward, use another fresh project to compare recipe, geometry
and decoded pixels. Do not write to old trial projects. Mocked language responses
prove orchestration, not live semantic accuracy; human trials follow all three stages.

## Autopilot guardrails and handoff

- **Zero live calls. No Git writes:** no staging, commits, pushes, branch changes,
  stashes, resets or history edits. Preserve user changes, photos and archived data.
- **Simple retry bound:** at most three unsuccessful targeted fix-and-verify
  cycles on the same blocker. Try materially different fixes where justified;
  do not loop unchanged commands or reset the count by relabelling the problem.
  Stop sooner if evidence is conclusive. No new retry-budget infrastructure.
- Stay within this scope. Do not weaken tests, change requirements, relax limits
  or add fallbacks to make progress. If blocked by a required scope/design change,
  stop and report evidence and the smallest decision needed.
- Finish with directly related documentation and a concise `010a_results.md`:
  changes, contract versions, checks, deterministic comparison and limitations.
  Report any blocker honestly; do not claim blocked work complete. Stop for review.
