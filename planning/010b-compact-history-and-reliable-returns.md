# 010b: Compact history and reliable returns

**Status:** Implemented and verified offline under the user's approval.
See [010b results](010b_results.md) for evidence, limitations and the separately
authorized live replay follow-up. Closed; 010c and further live evaluation
require separate approval.
Second stage of [010](010-grounded-interpretation-and-human-trials.md), building
on the implemented [010a](010a_results.md). Keep the simple implementation
guardrails from 010a. The approved scope and guardrails below are retained as
the implementation record; no live calls were included.

## Scope and agreed behaviour

Retain useful task/history evidence without sending the entire transcript.
Resolve proposal navigation from preserved evidence, not guesses about what a
past request achieved. Learned photo names remain independent of layout history.

- Group an originating request, its clarification answers and validation
  corrections as one logical task. Record outcomes honestly: generated proposal,
  exact selection, naming acknowledgement, question or failure. A failed request
  or a generated no-op must not be described as a successful layout change.
- Maintain compact, auditable task/proposal records: event references, original
  request, outcome, baseline before, actual source/result and navigation links.
  Record actual authored recipe differences deterministically, keyed by photo
  identity rather than layer index, including stacking changes. Keep requested
  changes distinct from observed changes; no model-written memory summaries.
- For "undo the last two edits", walk back two successful layout changes along
  the current proposal's ancestry, not the latest proposals created anywhere.
  Clarifications, failures, naming, acceptance, selections and no-ops do not add
  edit steps. A return does not erase abandoned branches.
- Edit/retry ancestry follows the actual source, not a rejected result or the
  baseline abandoned by a return-and-edit. A fresh arrangement retains a navigation
  predecessor pointing to its previous baseline, although it has no edit source.
  Do not invent a predecessor beyond the available project history.
- Allow descriptive returns anywhere in preserved project history, including
  older branches. Prefer the current branch when supported by the request;
  clarify genuinely competing matches or insufficient evidence.
- A pure return selects the exact preserved proposal/PNG: no generation,
  rerendering, acceptance or replacement proposal. Subsequent edits use it.
  Return-and-edit generates from the resolved older source, switching baseline
  only after successful publication. Generation failure leaves the prior baseline
  unchanged; valid learned-name updates retain 010a's independent persistence.

## Context and grounded navigation

- Keep detail for up to **three recent logical tasks**, plus up to **twelve
  compact task records** selected for relevance/recency. Avoid duplicating detail
  where a task appears in both sets. Preserve full audit evidence on disk.
- Retrieve deterministically from the compact records using explicit proposal
  IDs/ordinals, current ancestry, learned photo identities, request wording and
  recorded change facts. Resolve before/after relationships from recorded links.
  Use stable ranking/tie-breaking; ranking is not proof of an unambiguous match.
  No extra inference stage, model-directed retrieval or summarization calls.
- Supply bounded candidate metadata and relevant change evidence, not every old
  recipe or event. Missing/omitted evidence must be visible to interpretation;
  do not infer that an omitted record does not exist. Explicit IDs/ordinals
  remain directly addressable beyond the recent/compact windows.
- Interpretation must identify supported destination evidence for a return or
  older-source edit. Validate IDs, ancestry/counts and cited task/change evidence
  before selection/generation; a real proposal ID alone does not ground a
  descriptive request. Invalid responses use the existing correction limits.
  Missing or ambiguous evidence leads to clarification, not a fabricated match.
- Clarification should name a concrete candidate when supported, e.g.
  "Do you mean P007, before the thicker borders and bringing breakfast forward?"
  Persist the candidate, supporting evidence and original task, including any
  requested follow-up edit. A subsequent "yes" must retain that exact meaning
  across compaction/restart. A rejection must not select or generate anything;
  ask for the intended alternative if it remains unclear. Never reuse a
  superseded confirmation for a different request.
- Required names, active task/answers, resolved source, correction feedback and
  pending confirmation are essential context. Optional history/candidate detail
  may be reduced for size, preserving the evidence required by a resolved action.
  Keep the existing final serialized-byte-plus-reserve accounting and input/
  output limits. Drop optional material explicitly before reporting essential
  overflow; never silently drop required evidence or dispatch over the limit.

## Implementation boundary

Extend conversation records/context and typed interpretation as needed; keep
CLI, replay, offline assessment, prompts and usage documentation consistent.
Derive compact records/differences from authoritative events/proposals; verify
persisted indexes against that evidence. Do not treat cached summaries as truth.
Version only affected persisted contracts, reject unsupported versions without
migrations or compatibility shims, and preserve old projects as untouched archives.
Layout/project format 3 is unchanged.

Keep the current model, reasoning, timeouts, input/output limits, durable usage
recording, four-call per-message limit, at most two interpretation attempts and
no automatic service retries. Timeout/repeat-prompt UX and reasoning experiments
belong to 010c. No vision, composition work, renderer changes, UI, cloud work,
general-purpose semantic search, new dependencies or retry-budget infrastructure.

## Offline acceptance

Use focused tests plus affected lifecycle, 010a grounding, replay/integrity and
request-accounting checks. Include malformed/inconsistent responses. Demonstrate:

- More than twelve tasks, grouped multi-answer clarification, deterministic
  bounded context/retrieval, explicit old IDs/ordinals and descriptive retrieval
  beyond the recent window. Names and pending tasks survive size fitting/restart.
- Requested-versus-actual differences, failed tasks, no-ops, stacking and retries;
  these must not corrupt summaries or relative-undo counts.
- Exact return, multi-step undo, fresh-layout undo, older-branch return, ambiguous
  destination confirmation, rejection and restart followed by "yes".
- Pure returns preserve proposal/PNG bytes and acceptance with no generation;
  edits after returning use that source. Return-and-edit failure preserves the
  prior baseline. Invalid destination evidence cannot mutate navigation state.
- Actual outgoing payloads respect the unchanged size guard, visibly omit
  optional history where necessary and fail before dispatch on essential overflow.
  Preserve call accounting and replay source-relative assessment.

Repeat the umbrella's tilted-example comparison in fresh isolated projects:
recipe, geometry and decoded pixels must match the captured deterministic
baseline. Do not write to old trial projects. Offline success is not proof of
live interpretation quality or user sign-off.

## Autopilot guardrails and handoff

- **Zero live calls. No Git writes:** no staging, commits, pushes, branch changes,
  stashes, resets or history edits. Preserve user changes, photos and archived data.
- **Simple retry bound:** at most three unsuccessful targeted fix-and-verify
  cycles on the same blocker. Try materially different fixes where justified;
  do not repeat unchanged commands or reset the count by relabelling the problem.
  Stop sooner when evidence is conclusive. No retry-budget machinery.
- Stay within scope. Do not weaken tests, change requirements, relax limits or
  add fallbacks to make progress. If a necessary scope/design change blocks work,
  stop with evidence and the smallest decision needed.
- Finish with directly related documentation and concise `010b_results.md`:
  changes, contract versions, checks, deterministic comparison and limitations.
  Report blockers honestly. Stop for review; do not start 010c or live evaluation.
