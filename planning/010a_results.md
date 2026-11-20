# 010a results: Grounded photo references

## Status

Implemented and verified offline under [010a](010a-grounded-photo-references.md),
then followed by the separately authorized live sanity check below.
Stopped for review. No exploratory human trials, Git writes, 010b ledger/
navigation redesign, or 010c timeout/reasoning changes were performed.

## Implemented

- Typed interpretation carries number/name/history references, proposed name
  updates and exact user evidence. Generation receives validated identities
  rather than being asked to guess names. Known literal name omissions,
  mismatched IDs/bindings, invalid history references and contradictory updates
  are rejected within the existing interpretation-correction limit.
- Project-local names retain their originating event/quote independently of the
  proposal baseline and recent transcript. Case/whitespace normalization,
  multiple aliases, conflict confirmations and explicit corrections are covered.
  Valid name facts remain saved if subsequent generation fails.
- Naming-only requests produce typed acknowledgements, with no proposal, preview,
  acceptance or baseline change. CLI, replay cursor/resume and offline assessment
  distinguish these from generation. Restart checks verify names against
  their committed audit updates without rewriting archives.
- Outstanding clarification preserves the whole original task through multiple
  questions; recent validated evidence supports unambiguous conversational
  references. Names and resolved references are essential size-guarded context,
  not part of disposable rolling wording. No extra inference stage was added.

Conversation state, proposals, events, acceptance intents, replay reports/steps
and assessments now use **record version 3**. Unsupported older conversation/
replay records are rejected, not migrated. Layout/project format remains 3;
sequence definitions, controls, preferences and request accounting are unchanged.
Use fresh conversation projects for later trials.

## Offline evidence

- Full suite: **432 passed**, using `python -m pytest -q --tb=short` in `.venv`.
  Tests prohibit network connections; provider integration uses mocked HTTP.
- Focused cases include unknown/known names, repeated clarification, naming plus
  edits, acknowledgements, conflicts/corrections, alias persistence across
  compaction/restarts/returns, pronouns, malformed evidence, generation failure,
  actual-payload size fitting, and replay/assessment integration. Adversarial
  cases reject unknown names disguised as history references and pronoun
  fragments embedded in unrelated words.
- One new CLI assertion initially matched the existing startup banner's word
  "Generated"; it was corrected to check actual proposal output and absence of
  previews/proposals. The full suite then passed. No blocker exhausted the
  three-failed-cycle bound.
- Before/after public CLI rendering of `examples\emma_tilted_2x3.json` in fresh
  isolated projects produced identical recipes, geometry and decoded pixels.
  The final 1200x1800 RGB pixel SHA-256 is
  `b01a65a9203b7f943c9dff43ff7bb4fda88e05e84c98a7e8a33654fc0e40adc0`.
- All **975 pre-existing photo/runtime files** in the preservation manifest,
  staged entries, HEAD and branch are unchanged.

Session evidence: `files\010a-preservation.json`,
`files\010a-verification-result.json` and `files\010a-verification.py`.
The isolated deterministic projects are in `files\010a-before-data`,
`files\010a-after-data` and `files\010a-final-data`. These are session artifacts,
not new trial projects.

## Authorized live sanity follow-up

The user separately authorized one run of
`examples\sequences\01_dark_portrait_adjustments.json`, completed in fresh
project `p010a-dark-portrait-01`.

- All four messages produced proposals, including reopening before straightening:
  **8 calls**, no corrections, clarification questions, failures or retries.
  Known usage: **37,725 input / 15,204 output tokens**, with no unknown usage.
  Message durations were 81.3, 17.2, 14.9 and 17.6 seconds.
- Evidence integrity passed. The three follow-up edits changed only the requested
  authored fields. The initial historical profile failed solely because borders
  were `#F5F5F5`, not exact `#FFFFFF`.
- With subsequent user approval, the assessment now accepts near-white borders
  with each RGB channel at least 240. All **31 assessment tests passed**,
  including threshold cases; reassessment of the same saved replay passed all
  four steps without further model calls. The original failed assessment remains
  preserved. Rendering and model prompts were unchanged.

Session evidence: `files\010a-live-sanity-data\users\local-dev\projects\p010a-dark-portrait-01`;
see `replay\report.json` and `replay\assessments\0001.json` through `0003.json`.
This is a numeric-reference regression sanity check, not live verification of
learned names/clarification or user sign-off. No further live calls are authorized.

## Limitations and next boundary

Interpretation still relies on the model to identify mentions, explicit naming
intent and consequential ambiguity. Code checks structural evidence and known
bindings; it does not prove every natural-language assertion, detect every
omitted unknown reference, or establish that a generated edit satisfies meaning.
Mocked responses do not demonstrate live clarification quality, speed or user
satisfaction. The current bounded recent window and conservative size accounting
remain; unlimited learned names can still cause an explicit essential-input
size failure rather than silent forgetting.

010b and 010c remain unstarted. Integrated human trials and any low-reasoning
experiment require separate authorization after the planned offline stages.
