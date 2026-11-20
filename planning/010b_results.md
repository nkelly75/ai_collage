# 010b results: Compact history and reliable returns

## Status

Implemented offline under the user's approval of
[010b](010b-compact-history-and-reliable-returns.md). Verified offline, then
followed by the separately authorized live sanity check below. Closed and
stopped for review. No Git writes, new dependencies or 010c work.

## Implemented

- Logical task IDs group requests, clarification answers and validation
  corrections. Compact records are derived from authoritative events/proposals,
  not a separately trusted cache. Baseline transitions and task provenance are
  checked; the complete audit remains on disk.
- Deterministic recipe differences identify photos by number and stacking
  separately. Requested wording remains distinct from observed changes.
  Failures, questions, naming and selections do not become generated edits;
  unchanged recipes do not add undo steps.
- Undo follows actual-source ancestry. Fresh arrangements retain a separate
  navigation predecessor; retries branch from the original source rather than
  counting the rejected result. Exact return reuses preserved proposal/PNG bytes.
  Return-and-edit publishes from the selected source atomically, retaining the
  prior working baseline if generation fails.
- Context includes up to three detailed logical tasks and twelve additional
  compact records, with deterministic retrieval by wording, learned identities,
  recorded changes and ancestry. Explicit IDs/ordinals and relative undo can
  address proposals outside these windows. Branch/recency qualifiers constrain
  matching; competing descriptions require clarification.
- Typed navigation evidence is checked before selection/generation. Concrete
  return confirmations retain destination, action, original task and supporting
  evidence across restart. Rejection cannot select/generate; an explicitly
  independent replacement request supersedes the pending task.
- Final payload fitting can omit optional compact records, recent detail and
  catalogue entries, with omission accounting. Active task/answers, names,
  pending confirmation, resolved sources and required evidence remain essential.
  The existing byte-plus-reserve calculation and all service limits are unchanged.
  No new inference stage, retrieval call or model-generated memory summary.

Conversation state, proposals, events, acceptance intents, replay reports/steps
and assessments now use **record version 4**. Unsupported older records,
including 010a's version 3 conversations/replays, are rejected without migration.
Layout/project format remains **3**. Replay and assessment share photo-keyed
source-relative differences; current usage and prompts document the new context.

## Offline evidence

- Final full suite: **463 passed** in 941.42 seconds, using `.venv` Python with
  `-m pytest -q --tb=short`. Tests prohibit application networking; provider
  integration uses mocked HTTP. This includes the final navigation-quote,
  field/direction and explicit branch/recency boundary checks.
- Coverage includes more than twelve tasks, grouped multi-answer clarification,
  actual outgoing HTTP size fitting, old IDs/ordinals, descriptive retrieval and
  older branches, no-op/failed tasks, fresh/retry ancestry, exact selections,
  persistent confirmations/rejection, compound failure, corrupted provenance,
  and offline replay resume/assessment. Existing 010a grounding cases remain.
- Initial failures required updating fixtures for the deliberately changed
  interpretation contract and the larger bounded catalogue. The old size-plateau
  test now samples after that catalogue reaches its bound. No blocker exhausted
  the three-unsuccessful-cycle limit; no requirements or service limits were relaxed.
- Before/after public CLI rendering of `examples\emma_tilted_2x3.json` in fresh
  isolated projects preserved the recipe, geometry and decoded RGB pixels.
  Pixel SHA-256:
  `b01a65a9203b7f943c9dff43ff7bb4fda88e05e84c98a7e8a33654fc0e40adc0`.
- All **975 pre-existing photo/runtime files**, the original staged entries,
  HEAD and branch were unchanged in the preservation comparison.

Session evidence: `files\010b-preservation.json`,
`files\010b-verification-result.json` and `files\010b-verification.py`;
isolated deterministic projects are in `files\010b-before-data` and
`files\010b-after-data`, with the final candidate checked in
`files\010b-final-data`. The verification manifest includes candidate-file hashes.

## Authorized live sanity follow-up

One separately authorized run of
`examples\sequences\01_dark_portrait_adjustments.json` completed in fresh
project `p010b-dark-portrait-01`. All four steps passed the offline
`dark-portrait-adjustments` assessment, including integrity checks and reopening.
Follow-up edits changed only photo 2's width, borders and rotations respectively.

The run used **9 calls**, including one bounded interpretation correction: the
initial response listed references to all four photos although only photo 2 was
mentioned. Grounding rejected those unsupported references; the corrected
interpretation succeeded. No clarification, timeout, service failure, explicit
retry or acceptance occurred. Message durations: 84.3, 16.0, 15.6 and 18.4 seconds.
Known usage: **47,875 input / 15,694 output tokens**, with no unknown usage.

Session evidence: `files\010b-live-sanity-data\users\local-dev\projects\p010b-dark-portrait-01`;
see `replay\report.json` and `replay\assessments\0001.json`.
This is numeric-reference regression evidence, not live verification of all
010b navigation cases or human sign-off. The allowance is closed; no further
live calls are authorized.

## Limitations and next boundary

Retrieval/field checks use conservative English vocabulary and explicit learned
names, not general semantic search. Interpretation still identifies task scope,
consequential ambiguity and whether a new request replaces a pending one.
Code validates supporting facts, not every natural-language assertion. Unfamiliar
descriptions or confirmation wording may need clarification; omitted unknown
references and broader language understanding remain model limitations.

Undo cannot manufacture a proposal before the available proposal chain, including
an initial accepted snapshot without a corresponding proposal ID. Optional
history is bounded, but essential names/task answers can still exceed the
unchanged input bound and fail explicitly. Authored changes, not subjective
visual strength, determine no-ops.

Offline checks do not establish live language quality, latency or user sign-off.
010c and further live evaluation remain unstarted and require separate approval.
