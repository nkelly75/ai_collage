# 010h results: Useful, recoverable progress

**Status:** Implemented and verified offline; bounded pass closed for human review.
Scope: [010h](010h-useful-recoverable-progress.md). No live requests, Git writes
or new human trial belong to this pass. Offline results do not establish better
live interpretation/design quality or constitute user sign-off.

## What changed

**Conservative aliases.** One shared literal rule allows suffix shortenings of
taught names and article/photo wrappers, without inferring image contents.
Interpretation may propose up to four shortened aliases on a taught-name update;
code checks and records them separately from user-taught labels. Matching uses
all taught names, not recency. Different-photo collisions clarify; an explicit
answer can disambiguate that pending task without silently removing competing
names or making future ambiguous uses unambiguous. Navigation evidence uses the
same matching rule.

References retain the user's actual wording and stable photo number alongside
the project's original taught-name/quote/event evidence. A broader synonym
cannot be installed as an automatic alias: a structured question names the
candidate number and an established label, and only the user's exact affirmative
answer establishes the additional name. Pending candidates are not learned
facts. Matching name/number evidence can be redundant; conflicting adjacent
parenthetical numbers are rejected rather than ignored.

**Clarification continuity.** Questions carry whether the originating task is
design or naming-only. A design identity answer cannot silently become a
naming-only acknowledgement or mark that answer independent. These are rejected
interpretations for correction inside the existing allowance, not rewritten
successful actions. Invalid interpretation attempts no longer hide a pending
question when the user corrects an answer, including after restart. An invalid
independence claim cannot discard that task during correction. Clearly separate
replacement requests still work.

Identity confirmations validate the actual question's name and candidate photo
number; broader candidates also identify an established label. Yes must use the
exact pending assignment, and No must clarify without generation. Existing
explicit corrections and multi-photo identity answers remain supported.

**Enlargement and corrections.** Generation instructions now permit minimal
necessary inward movement of resized photos, retaining centres when they fit
and respecting explicit fixed positions/anchors. They prohibit silently shrinking
a requested enlargement. Each attempt also supplies bounded earlier validation
feedback alongside the latest failed candidate, so a later repair need not
reintroduce a previous failure. No geometry solver, renderer repair, clipping,
cropping permission change or semantic request parser was added.

**Recoverable presentation.** Exhausted validation before publication raises a
narrow typed rejection only after rechecking current state and loading/verifying
the actual baseline. Chat reports that source (or no proposal yet), reassures the
user they can rephrase or ask for a different change, and does not print the
internal diagnostic as the default response. Unknown diagnostics get the same
simple fallback, not an invented workaround or extra inference call.

Identity questions/rejections show one current taught/confirmed label per named
photo, directly from application state; no names means a suggestion to use photo
numbers. Automatic aliases and unconfirmed candidates are excluded. Unrelated
failures get no naming reminder. Raw responses, validation diagnostics and
stage/outcome records remain saved. Publication/I/O and integrity failures remain
explicit; they do not get an unverified unchanged-state assurance.

## Contracts and boundaries

Conversation/state, proposal, exchange/local-event and acceptance-intent records
are now **6**, for the distinct alias evidence and clarification-purpose contract.
Replay reports are **7**, rejecting older replay/conversation contracts on resume.
Replay steps and assessment reports remain **5**; request attempts remain **2**.
Layout/project format remains **3**. Sequence definitions, preferences and controls
remain **1**. There are no compatibility loaders or migrations: use a fresh
conversation/project for the next trial; prior PNGs and raw evidence stay archived.

Generation still defaults **low**, interpretation **high**, with both explicit
overrides. Deployment, dependencies, transport retries, stage deadlines,
call/token budgets, deterministic geometry and rendering are unchanged.

## Offline verification

Evidence directory:

`C:\Users\nkell\.copilot\session-state\621a42a9-2ec6-4af0-a2d9-fde02d818692\files\010h-offline-01`

The existing socket-blocking fixtures remained active. Controlled clients and
mocked HTTP transports were used, not real Foundry/authentication requests.

| Check | Result |
|---|---|
| Initial existing focused suites | 247 passed; seven fixture-contract failures, described below. |
| New focused cases, first run | 21 passed. |
| Focused new cases plus adapted provider/schema/legacy fixtures | 40 passed. |
| Full offline suite | **565 passed** in 264.08 seconds. |
| Unchanged sequences 03, 04 and 05, `--check` | All passed; definitions unchanged against HEAD. |
| Patch whitespace | Passed. |

The first integration run exposed five mocked-transport property-set assertions,
one flat-schema property-set assertion, and a naming-only confirmation fixture
that needed explicit `continuation: "naming"`. These fixtures were updated for
the new contract, rather than weakening runtime validation. The next covering
focused run passed; no blocker required repeated unsuccessful fix cycles.

New regressions cover literal/wrapped aliases and provenance after restart,
same-photo labels, collisions and explicit disambiguation, broader-name
confirmation, matching/conflicting numbers, Yes/No, corrected multi-photo answers
after invalid answers and restart, original task/source retention, independent
replacement, invalid confirmation wording, multi-photo fit correction retention,
unrelated-value preservation, fixed-position/impossible candidate rejection,
generic/identity recovery presentation, retained diagnostics, a usable next
request, and explicit uncertain publication/I/O errors. Existing navigation,
timeout/accounting, prepublication and unsupported-version tests remain in the
full gate.

## Preservation

The new pass captured its own entry baseline before application edits, rather
than reusing an older pass's staging snapshot. Entry HEAD:
`ee88d22093dd15dc310b01cb8f73c89916ec4acf`; branch `nkelly/plan-010`.

The preservation helper checks exact staged entries, HEAD/branch, installed
runtime/packages, **1,063** existing photo/project files under `photos` and all
`.collage-data*` roots, and closed results records including 010g observations.
It also verifies the original manifests and exact file sets for all five sealed
010d/010e/provenance/010f artifact roots. Final verification passed with staging,
HEAD/branch, runtime, original/archive files and all five prior seals unchanged.
This pass's immutable `evidence-sha256.json` manifest has SHA-256:

`2246f64b5664fcfb68c66d74f76ef63144f9c7b864ba9c43afdab2177583ef11`

The manifest includes the entry baseline, preservation helper/final check,
focused/full test logs and sequence checks; no older evidence root was written.

The user's staged files remain staged as supplied; intended implementation and
documentation edits are unstaged. The old trial `p010g-human-03`, original photos,
accepted/archive data and failed/successful prior evaluation evidence are not
resumed, repaired, rewritten or recounted.

## Human-led handoff and limitations

Stop after the offline gate and preservation check. The next step is a fresh
human-led project, not resuming the version-5 trial or automatically running a
smoke check. No new project has been created and no further calls authorized.

Suffix matching is deliberately literal, not a semantic synonym engine.
Unclear identities can still need clarification. The model still chooses
interpretation/actions and authored geometry; the new question-purpose and
candidate checks constrain that handshake but do not prove every natural-language
question is correctly classified.

Resize-fit permissions and repair retention are prompt-led. Controlled tests
prove the context/state/validation path, not that a live model will always
preserve an anchor, retain every repair or achieve the requested enlargement.
A failed candidate alone does not establish that the user's request is
impossible. The generic fallback deliberately avoids that claim or prescriptive
smaller-size advice when requested-size impossibility is not verified.
Legitimately learned names can remain saved when a subsequent layout attempt
fails; the unchanged-state assurance concerns the collage, not every name fact.
