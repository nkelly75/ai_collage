# 010h: Useful, recoverable progress

**Status:** Implemented and verified offline in one bounded pass; see
[010h results](010h_results.md). Stopped for a fresh human-led trial, not sign-off.
Follow-up to [010g observations](010g_results.md). One bounded offline pass,
then review and a fresh human-led trial, not another reasoning comparison.

## Goal and approval boundary

The user should not need to understand reference schemas, geometry diagnostics
or hidden task state to keep designing. Make ordinary wording and necessary
layout adjustments more forgiving, while keeping photo identity, saved-state
integrity and rendering constraints reliable.

Success means useful edits when possible and a reassuring, truthful way to
continue when not. It does not mean understanding every phrase, fitting every
enlargement or prescribing a workaround for every failure. Consistent recovery
from unforeseen failures matters more than a growing catalogue of niche fixes.
Use prompt clarification and small, directly necessary code changes, not more
inference stages or a general troubleshooting system.

One explicit approval may cover implementation, verification and reporting:

> Implement planning\010h-useful-recoverable-progress.md in one bounded offline
> pass. Cover conservative aliases, clarification recovery, resize-to-fit
> positioning/correction retention and friendly recoverable errors. Run focused
> regressions and the full offline suite. Preserve my staging, original photos
> and prior evidence. Stop on integrity risks or scope expansion, and hand back
> for a human-led trial. No live calls or Git writes.

Keep high interpretation / low generation and both explicit overrides.
No new inference stages, automatic service retries, increased call/token/time
limits, deployment/dependency changes, UI development or renderer redesign.
No live smoke check, benchmark or assistant-run trial belongs to this approval.

## 1. Natural references without guessing identities

Let interpretation propose a small set of useful aliases alongside establishing
a taught name, within its existing call. Code validates automatic aliases as
obvious shortened forms of the taught wording, not invented content synonyms.

- Accept a straightforward shortening such as "bridge" for "london bridge"
  when it uniquely identifies one photo. Handle surrounding wording such as
  "the bridge photo" without requiring another taught label for that phrase.
- Resolve against all current taught names/usable aliases. If a form could
  identify different photos, clarify; never pick by recency or silently replace
  another binding. Several labels for the same photo are not an identity conflict.
- Ask for confirmation before adopting broader model-proposed synonyms.
  Do not infer descriptions from unseen image contents or world knowledge.
- Preserve both the user's actual reference wording and the established
  name/photo evidence supporting its resolution. Do not demand identical
  strings, fabricate a quote, or record a model-proposed alias as user-taught.
  Keep alias provenance distinct; automatic short forms are not new user facts.
- A name plus an explicit matching number, e.g. "breakfast (photo 2)", should
  not fail merely because one reference supplies redundant identity evidence
  in a different form. Conflicting name/number identities still require clarity.

Use the simplest shared alias-resolution rule/representation that supports
these checks consistently in prompting, validation and evidence. No semantic
search, embeddings, exhaustive synonym catalogue or separate alias-generation
request. Prompt flexibility must be supported by the local grounding contract,
not achieved by disabling it.

## 2. Clarification should move the original task forward

Fix the question/answer handshake, not just its wording:

- A question inviting "Yes" to a specific photo identity must carry a validated
  structured candidate, tied to the pending task and the actual question.
  Reuse the existing confirmation mechanism where practical. If such a
  confirmation cannot be supported, ask for a photo number instead.
- An affirmative answer uses that exact pending candidate; it must not invent
  another identity. Rejection leaves the layout unchanged and permits clarification.
- Identity answers and corrected answers continue the originating edit/source,
  including after a rejected answer and restart. Do not silently downgrade them
  to naming-only acknowledgements or discard the original requested operation.
- Respect a clearly independent replacement request. A stale confirmation must
  not apply to a new task. Keep multi-photo answers and existing explicit name
  corrections working; clarify genuinely unresolved identities rather than guess.

Use concise prompt examples plus narrow consistency checks where necessary.
Do not silently rewrite an invalid interpretation into a successful edit.
Corrections remain inside the existing allowance; there is no new retry loop.

## 3. Enlargement includes necessary fit adjustments

The user should not need to add "move it inward so it fits" to an ordinary
enlargement. Update generation instructions to permit minimal necessary inward
repositioning of the resized photos. Preserve centres when the requested size
already fits; otherwise retain the rough arrangement and change only positions
needed for full containment, including borders and rotated sampling clearance.
This is limited creative permission, not a requirement for an optimal-placement
solver. Preserve unrelated photos, styling and stacking unless requested.

An explicit fixed centre/position/anchor takes precedence over that permission.
Do not silently reduce the requested enlargement if it cannot fit, even after
allowed repositioning: keep the previous proposal and explain that the user
can request a smaller enlargement. Distinguish a known inability to fit from
merely failing to produce a valid candidate; do not claim impossibility without
evidence.

For validation corrections, build on the latest failed candidate's successful
repairs rather than restoring offending values from the original baseline.
Retain the original task and unrelated authored choices. Prefer prompt changes;
any necessary feedback/context adjustment stays small and bounded to the current
attempt, within existing input/call limits.

The deterministic engine still validates and rejects invalid geometry. No
renderer clamping, clipping, hidden shrinking/cropping or new layout-repair
algorithm. No guarantee that prompting alone makes every enlargement succeed.

## 4. Make it clear that the conversation can continue

For a verified recoverable rejection, give a brief explanation, the actual
current proposal ID (or that none exists yet), and permission to rephrase or
request a different change. A precise diagnosis or guaranteed workaround is
not required. For example, when the unchanged baseline is verified:

> I couldn't apply that change. Your collage is still at P006. You can rephrase
> your request or ask for a different change.

Prefer "rephrase" or "reword" over "try again". Do not promise that repetition
will succeed, or that a bare "try again" resumes the task unless supported.

For identity-related clarifications or recoverable naming/mapping rejections,
also show a compact reminder of established names and their photo numbers:

> Names I know: 1 = london bridge, 2 = breakfast, 3 = london eye, 4 = bookshop.

Build this reminder directly from current validated application state, not
model recollection or another inference call. Use taught or explicitly confirmed
labels, not every automatic short form or synonym. Exclude unconfirmed proposals
and never invent descriptions for unnamed photos. If no names are established,
say so and suggest photo numbers. Omit the reminder for unrelated failures such
as resizing. It is a useful baseline, not a dump of internal alias/provenance data.

Other specific advice is optional and must follow a reliably identified cause:
photo numbers for unresolved identities, a smaller enlargement for a known
size/fit constraint. A failed geometry candidate alone does not establish that
the requested size cannot fit. When no useful tip is supported, omit it;
reassurance and continuation guidance are sufficient.

Make that reassurance the default fallback for recoverable failures whose
diagnostic does not map readily to useful advice. Do not spend extra calls or
build special-case diagnostic parsing to produce a detailed workaround.
Use the verified current state and the simple rephrasing message above; retain
the difficult diagnostic in the evidence. This is a presentation fallback,
not permission to swallow errors or assume an uncertain failure is recoverable.

Only assure unchanged layout when that is verified. Do not extend that assurance
to uncertain publication/I/O failures or imply that no state changed when names
were legitimately learned. Never present failure as success or automatically
dispatch another request. Recovery guidance should retain the pending task where
valid, without preventing an independent next request or making the user
reconstruct internal task state before they can continue.

Keep full technical diagnostics and stage/outcome evidence in application
records, separate from terminal presentation. Use small, reliable stage/outcome
categories or equivalent narrow handling, not error-string matching, a catch-all
that calls every failure recoverable, or an exhaustive diagnostic taxonomy.
The same underlying state can support a later UI exposing details; no diagnostic
viewer, new interactive command or graphical UI is required now.

## Offline verification and handoff

Before implementation, capture current staging, HEAD/branch and preservation
hashes for original data and prior evidence. Do not use an older pass's staging
snapshot as the current baseline.

Add focused regressions in existing suites for:

- Safe shortened names, broader-alias confirmation, collisions, redundant
  name/number evidence, conflicting identities and provenance.
- Invited "Yes"/rejection, corrected answers after validation failure,
  original-edit retention, restart and independent-task replacement.
- Resize-fit/correction context and preservation of unrelated values; fixed
  position and impossible/unsuccessful enlargement outcomes.
- Recovery presentation: retained diagnostics, accurate current-proposal
  reporting and default rephrasing guidance even when no specific tip is known.
  Check cause-appropriate hints and known-name reminders drawn only from
  validated state, including the no-names case and omission for unrelated
  failures. No unsupported retry shortcuts or false unchanged-state assurances
  for publication/I/O failures.

Use controlled clients and existing geometry helpers; do not test prompt
wording as though it proved live model adherence. Run the smallest covering
suites first, then the full existing offline suite and unchanged 03-05 sequence
checks. Preserve navigation, grounding, timeout/accounting and prepublication
regressions. Keep prompts concise by replacing conflicting wording rather than
piling on special cases for this trial's exact phrases. Test the general
recovery behaviour as well as the observed defects; do not make helpful failure
handling depend on recognizing only these recorded examples.

At most three unsuccessful targeted fix-and-verify cycles per blocker. Stop
with evidence if blocked, preservation fails or a broader redesign is needed.
Update current CLI documentation and directly related status. Version only
affected persisted contracts if their meaning/shape changes; update dependent
code/tests/docs together. Preserve older records as untouched archives and
clearly reject unsupported versions; no compatibility paths or migrations.
Do not bump layout format for these agent-only changes.

Write `planning\010h_results.md` with changes, verification, any affected record
versions, preservation checks and remaining limitations. Keep detailed evidence
there or in linked session artifacts, not duplicated in the planning index.
Stop ready for a fresh human-led project; do not resume/repair the old trial or
start the next one. Offline success is not user sign-off or proof of improved
live interpretation/design quality.
