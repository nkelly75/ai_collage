# Phase 1, Step 2: Conversational Layout Experiment

**Closed as a historical implementation/evaluation record.** The bounded
checkpoint A work is complete; the specification and execution history below
are retained as evidence, not an active work plan or authorization to continue.
Closure does not mean the implementation is stabilized, commit-ready, or
accepted by the user. The user is using Git staging to capture progress and
expects further changes before deciding to commit. Checkpoint B remains
unstarted and unapproved. No successor plan is created by this closure.

**Status: checkpoint A scripted checks passed; trial-ready.** A separately
authorized follow-up passed all four unchanged live cases and exact acceptance
in 4/6 meaningful development rounds, using 17/50 fresh requests. Further
inference is halted with 33 requests unspent. This is not a general reliability
claim or the user's final sign-off. See the
[latest handoff](#authorized-six-round-follow-up-handoff).
Checkpoint B and further implementation/evaluation remain unapproved.

The [follow-up](#prepared-follow-up-and-approval) used the revised
development-round and model-correction rules below. Earlier execution records
retain their original rules, counts, and failed outcomes.

## Prepared follow-up and approval

**Executed after explicit approval.** The user requested continuation and a
fresh 50-request budget after staging the previous edits. The existing
implementation was resumed, not rebuilt. Numeric containment feedback and the
bounded correction loop are implemented, alongside explicit baseline pixel
centres and high reasoning effort. The same four scripted requests and unchanged
acceptance checks now pass. No template engine, new rendering behavior,
deterministic recipe repairs, or subjective-quality search was added.

The approved follow-up had **six meaningful development rounds
total**, not overlapping per-package/macro allowances. It may make **up to three
validation-guided model corrections per user request**, four inference attempts
including the initial response. These correction limits are now implemented.

The prepared brief proposed reusing 47 requests, but the later direct user
instruction explicitly authorized a **fresh 50-request allowance**. That
approval was recorded before archiving the previous halted three-attempt ledger
and provisioning the new `step2-first-pass` allowance with unchanged per-attempt
limits. The old consumed attempts, unknown usage, excluded diagnostic archive,
and prior reports remain intact. The new allowance stopped at 17/50 and is
halted after success, not exhaustion.

Keep the completed pass's reported 6/6 cycles and original audit ledger unchanged.
The follow-up is tracked separately at 4/6 development rounds; no earlier
cycles were reclassified, refunded, or erased. Unused rounds and requests do
not authorize a new pass. Staging edits or switching execution mode alone does
not grant approval. Checkpoint B remains a separate approval.

## Purpose

Explore whether a metadata-only layout agent can turn a user's intent into a
useful collage, then make predictable adjustments through conversation.
The goal is not to find an objectively best layout or reproduce Emma's manual
collage exactly. It is to reach a result the user likes with little effort.

This continues Step 2 outlined in
[record 002](002-phase-1-offline-foundation.md), using the implemented
[format 2 contract](../docs/layout-format.md) and deterministic offline engine.
The broader product direction remains in the [planning index](README.md).

## Agreed product decisions

- One resumable conversation per local photo project; no named threads/branches.
- Request, preview, refine, then explicitly accept a successful proposal by ID.
  Failures preserve the good proposal and accepted version.
- Preferences are overridable defaults. Start with subtle borders, rounding,
  and tilt; edit remembered defaults explicitly, not through conversation.
- The user selects a canvas. Explicit local controls change canvas/cropping
  permission; whole photos are the default, with no inferred permission to crop.
- Use plain everyday requests and stable photo numbers, not design jargon.
  Without user-supplied descriptions the agent does not know photo contents.
- Ask short essential clarifications; otherwise make reasonable creative choices.
- Ratings/notes on edits are optional and separate from accepting a collage.
- A bounded Autopilot pass precedes the user-led trial and can end with useful
  partial progress. The user decides on additional budgets and final sign-off.

## Implementation scope

Use one Microsoft Agent Framework agent with the existing `gpt-5.4-mini`
Foundry deployment and keyless authentication. It proposes JSON from metadata,
preferences, and conversation context; ordinary Python code validates, renders,
persists, and accepts. Reuse shared engine capabilities directly, not CLI
subprocesses or model-generated shell commands. The model cannot accept layouts.

Build the minimal terminal conversation and durable proposal workflow, preserving
unrelated composition choices on targeted edits. Keep existing manual commands
and accepted snapshots usable: `apply-layout` accepts immediately and is not a
proposal API. Physical filenames and Python helper/module organization remain
implementation decisions within the contracts below.

## Terminal contract

Add this command shape, preserving the existing global `--data-dir` placement:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-step2 chat --project emma-agent-demo --canvas 1200 1800 --run step2-first-pass
```

`--project` names an existing format 2 project. `--canvas WIDTH HEIGHT` is
required when starting its conversation and omitted when resuming; if supplied
on resume it must equal the stored effective canvas or fail with guidance to
use `/canvas`. Canvas axes retain the engine's integer 1-4096 limits.

`--run` selects the shared local allowance ledger described below. Omitting it
permits local inspection/commands but disables model requests, without
initializing credentials or a model client. An exhausted run likewise leaves
local controls usable. An unknown run ID is an error, not a fresh allowance.
`--preferences FILE` may select the defaults file at conversation creation;
otherwise use the owner's defaults under the selected data root. A resume
uses the captured defaults; reject `--preferences` on resume rather than
silently replacing or ignoring them.
`--no-open` suppresses automatic preview opening for scripted/headless use.

A new conversation uses the current accepted recipe as its initial editing
baseline if there is one, otherwise starts without a recipe. Show which is in
use. A differing user-selected canvas is a pending control change, not a silent
rewrite of the accepted recipe. EOF and Ctrl+C exit cleanly; an interrupted
request remains counted and cannot be replayed automatically on resume.

Ordinary nonempty text requests go to the agent. Slash commands are interpreted
locally and never forwarded as model instructions:

| Action | Syntax | Effect |
|---|---|---|
| Open preview | `/show P003` | Open that immutable preview in the local viewer; retain its path if opening fails. |
| Rate an edit | `/rate P003 worked "That looks right"` | Append a local rating/note for the proposal's generating request and before/after pair. Rating tokens are `worked`, `partly`, and `failed`; an optional trailing note may contain spaces. |
| Accept | `/accept P003` | Accept that proposal and use it as the next editing baseline; retain other proposals for inspection. |
| Inspect | `/status` | Show effective controls, baseline proposal, accepted version, and request/token usage. |
| Change canvas | `/canvas 1600 900` | Set dimensions for subsequent generation; do not mutate an existing preview or accept a version. |
| Cropping permission | `/cropping allow` or `/cropping forbid` | Set the permission for subsequent generation, initially forbid. No immediate render or acceptance. |
| Exit | `/quit` | Preserve state for the next invocation. |
| Help | `/help` | Explain the commands and the distinction between local controls and model requests. |

These controls make no inference requests. Reject unknown commands, malformed
arguments, and unknown proposal IDs locally without changing state or asking
the model to interpret them. Do not execute shell syntax.

After a canvas/cropping change, show that the editing baseline has not yet
been regenerated under the new controls. Validate subsequent recipes against
those controls; changing
permission alone never silently crops or uncrops an existing proposal.
A natural-language request to change canvas or cropping permission should
explain the relevant local control, not change that authority on its own.

Accept an explicitly selected, valid preview without asking the model for a
replacement. Preserve its exact recipe and rendered result in the accepted
version. Acceptance and subsequent refinement remain in the same conversation.
The proposal must fit the current canvas/cropping controls; otherwise refuse
acceptance with explicit guidance, leaving the proposal viewable. Never
silently restore older permissions to accept it.
Accepting a proposal that is already the current accepted result is idempotent.
Accepting an older proposal after another version was accepted creates the next
ordinary immutable version and sets that proposal as the editing baseline.
That explicit selection supersedes incompatible earlier design directions;
do not let historical requests silently undo the chosen recipe on the next turn.
No arbitrary reset/delete or branch-switching command is needed.
Scripted evaluation calls the same underlying Python operations, not a second
implementation or terminal-typing automation.

Print a successful proposal's ID, preview path, and attempt/token summary before
opening its PNG in the OS viewer. A viewer failure is an explicit warning with
the usable path, not a failed generation or reason to make another model call.
Local commands and questions do not create an image. Turn failures show a
bounded readable error and retain the prior baseline; the interactive loop can
then accept another user action. Fatal state/authentication problems stop live
generation rather than repeatedly contacting the service.

### Clarification replies

A successful model turn can return either a proposed recipe or a short
clarification question in a validated response structure. A question creates
no proposal, changes no layout/control/default, and preserves the editing
baseline. Persist the actual exchange so the next typed answer continues it.
Do not treat a valid question as malformed output or trigger a correction call.

Ask only when needed: "Make the breakfast smaller" requires asking which photo
number the user means unless the user already supplied that association.
"Make photo 2 a bit smaller" does not require asking for an exact percentage.
Never infer photo contents from IDs, filenames, or dimensions.

Each clarification response consumes an inference attempt under the same
limits. Wait for the user's answer; do not generate answers on their behalf
or run an autonomous clarification loop. Questions about authority to change
canvas/cropping still direct the user to the explicit local controls.
No new question-only live sequence is required for the first pass; cover the
clarification/answer path with mocked responses and leave actual usefulness
to the interactive trial.

## Agent input/output contract

Use a strict response union, with no executable tools, shell commands, or
authority to modify project state:

| Kind | Required fields |
|---|---|
| `proposal` | `kind: "proposal"` and `recipe`: one complete current `InputLayout`. |
| `question` | `kind: "question"` and `question`: nonempty text, at most 1,000 characters. |

```json
{"kind": "question", "question": "Which photo number is the breakfast?"}
```

Forbid unknown fields and recipe/question mixtures.
Require a single JSON object, not Markdown fences, extracted JSON substrings,
or prose surrounding JSON. Apply the existing bounded strict JSON decoding
rules, including duplicate-key and non-finite-number rejection, before model
validation. Cap each response document at 1 MiB independently of token limits.

Python validates recipe structure, photo membership/exactly-once usage, current
canvas dimensions, cropping permission, source-dependent geometry, and actual
renderability. When cropping is forbidden, reject every `cover` layer even if
its chosen aspect ratio happens not to crop. No silent recipe repairs or
postprocessing that changes authored geometry/style to obtain a pass.
Use native schema-constrained output if supported for this same contract;
provider schema adaptation may change presentation, not accepted semantics.
If the chosen API cannot support the contract, stop at the compatibility gate
rather than silently switching providers or relaxing output validation.

Rebuild context from:

- The current field guide/schema, compact composition-pattern descriptions,
  and at most two compact recipe examples.
- Only stable photo IDs, oriented width/height, and derived aspect ratios from
  project metadata. Do not pass the full `inspect` output, which includes paths
  and filenames.
- The captured defaults, current trusted local controls, and the explicit
  editing-baseline recipe. Identify it on every request, especially after
  accepting an older proposal; the latest historical JSON is not necessarily
  the current baseline.
- Real user/assistant turns and local state-change context sufficient to retain
  explicit styling choices and user-supplied photo associations. Failed
  responses must be labelled as failed attempts, not successful proposals.

Treat user/model text as untrusted content, not authority to change controls,
limits, persistence paths, or acceptance. Local control changes are application
context, not fabricated user/assistant messages. Ratings remain local evidence,
not an automatic prompt optimizer. Never attach source images/previews or add
local paths, original filenames, credentials, or raw exception dumps from
application metadata/errors to model context. User-entered text is sent as
conversation content and can supply photo descriptions; this is not a promise
of general-purpose sensitive-data detection/redaction.
No provider-hosted conversation/session storage, web search, or tool loop.
Set provider response storage off where supported, without claiming this
disables all service logging/retention. Keep client resources properly closed.

For the next approved pass, allow up to three validation-guided corrections
after a completed response fails structural or hard layout/control validation:
at most four inference attempts for one user request, subject to the remaining
shared allowance. Stop on success or an applicable stop condition; three
corrections are a ceiling, not a target. A syntactically valid question needs no
correction and waits for the real user's answer. Service/authentication errors,
timeouts, incomplete responses, and rendering I/O/publication failures never
trigger this model-correction loop.

Each correction retains the original task and authoritative valid baseline,
while identifying the latest invalid candidate and its current failures.
Supply at most 20 sanitized validation errors, capped at 8 KiB UTF-8. For
containment failures, include the affected photo ID, derived outer/rotated
footprint bounds, canvas limits, and numeric overshoot in clearly labelled
units. Include safe position ranges for the current frame/rotation where these
can be computed using the engine's geometry, including sampling clearance.
Do not merely repeat "extends beyond the canvas" when numeric evidence is
available. Updated feedback must reflect each candidate, not stale earlier
geometry. This is diagnostic information, not an automatic recipe repair:
never move, clamp, clip, or resize authored values to force acceptance.

Field locations and offending constraints are appropriate; omit paths, stack
traces, and sensitive raw values. Preserve each attempt and feedback separately;
invalid candidates never replace the last valid editing baseline.
Subjective quality and scripted instruction-following checks are not a hidden
automatic model-retry channel.

## Persistence contract

Keep local conversation state under its project, separate from accepted
layouts: real turns and failed attempts, captured preferences, effective
controls, immutable successful recipes/previews, ratings, and the working
baseline pointer. Assign increasing stable IDs such as `P001`, independent of
accepted version numbers; use these in commands and output. A partially
published or failed proposal must not become the baseline.

Persist strict versioned logical records with these required contents:

| Record | Required contents |
|---|---|
| Conversation | Project/photo-set identity; expected accepted version or none; captured defaults; effective canvas/cropping controls; editing baseline reference or none; references to committed turns/proposals and local events. |
| Turn/attempt | Actual prompt/response or failed-attempt outcome; parent baseline; originating run/attempt IDs; result kind; sanitized validation/service error; references to a successful proposal if any. |
| Proposal | Stable proposal ID; originating turn and parent baseline; controls at creation; canonical validated recipe; recomputable geometry; recipe and preview SHA-256 digests; immutable PNG location. |
| Local event | Canvas/cropping changes, proposal acceptance/version link, or rating/note; ordering; proposal and originating request references where applicable. |
| Run allowance/attempt ledger | Approved run identity and limits; pre-dispatch reservation; per-attempt purpose, state, timing, outcome, and reported usage; cumulative request/token accounting. |

Use a distinct version marker for new conversation records, not an incompatible
reinterpretation of format 2 project/layout metadata. Split bounded records
rather than growing a transcript JSON file beyond the existing 1 MiB read
limit. Store one canonical recipe per proposal; references/indexes must not
become independently editable recipe copies. Recompute geometry on reopen and
verify artifact identities before viewing/accepting; altered or missing
successful previews are errors, not an invitation to regenerate silently.

Render and validate to staging, publish immutable proposal artifacts, then
commit the conversation's turn/baseline reference last. Failures before that
commit leave the prior good baseline visible. Preserve failed-attempt accounting
even if proposal publication fails.

Acceptance revalidates the selected proposal and expected accepted version,
then uses shared failure-safe accepted-version publication, not `apply-layout`
as a subprocess. The accepted PNG must be byte-identical to the inspected
preview; no inference or replacement render. Publish the project current
pointer last. Record acceptance intent durably so interruption after project
commit but before conversation-index update can be reconciled only to that
exact version/recipe/PNG. Before project commit, ordinary failures must preserve
the prior accepted version. After commit, never pretend acceptance did not
happen or create another version on automatic replay.
If safe reconciliation cannot be established, stop with an explicit state
conflict and preserved artifacts; no database/general recovery framework.

Keep the approved Autopilot run's request ledger outside individual projects,
under the owner's run-state directory in the fixed `.collage-data-step2` root.
Add that exact runtime root to `.gitignore` during approved implementation;
do not commit generated conversation, ledger, or render data.
Use run ID `step2-first-pass` for all checkpoint A inference, including
connectivity checks and corrections. Provision its capped allowance once only
after implementation approval, and reuse it across projects/resumed processes.
Starting another project/process, changing data roots, renaming ledgers, or
registering another run must not be used to refresh the approved allowance.
A CLI flag or editable local ledger is not user authorization or an account-wide
spending control; this remains a single-user local experiment.

Reject corrupt/inconsistent saved state explicitly. Keep the existing
single-local-writer assumption, bounded JSON reads, and path-containment rules.
If an accepted project version changes outside the conversation, detect and
report the conflict before further generation/acceptance rather than silently
rebasing the conversation or overwriting newer accepted work.
Local show/status/rating operations may remain available during an external
accepted-version conflict if their own records validate. Do not add a silent
rebase/reset action. Physical filenames, atomic-file helpers, and serialization
classes are implementation details subject to these guarantees.

## Preferences and creative direction

Use borders, corner rounding, and tilt as preference fields. Keep these defaults
separate from composition patterns and user-specified photo importance.
Use a strict preferences document with `preferences_version: 1` and required
fields `borders`, `rounding`, and `tilt`, each one of `prefer`, `avoid`, or
`agent_choice`. Reject unknown fields and invalid values. The initial document
uses `prefer` for all three.

For a new design with no explicit styling directions, guidance is white borders
of approximately 10 pixels, corner radii approximately 12 pixels, and mixed
gentle tilts of about 1-3 degrees on a 1200x1800 canvas. Scale down for smaller
frames/canvases and respect geometry/radius constraints. These are instructions,
not new engine limits or deterministic overrides of a generated recipe.
`avoid` means omit/disable that effect absent an explicit collage request;
`agent_choice` expresses no preference. An explicit request can supersede
either, but not hard controls such as cropping permission.

Place the default document under the owner namespace, separate from project
conversation state. If absent when a conversation is first created, create the
documented initial file once; never overwrite an existing file or silently
replace a malformed one. Existing offline commands must not create it.

Snapshot defaults at conversation creation. Editing the local file affects
future conversations only; natural-language updates to that file are deferred.
"No rounded corners for this collage" overrides this work, not the file.
Refine the selected baseline rather than reapplying defaults. Carry explicit
styling requests across turns unless superseded by a later request or explicit
proposal selection. Defaults never override engine safety or local controls.
Requests such as "make photo 3 the biggest" need no image descriptions.

## Small composition vocabulary

Include a handful of descriptive starting patterns in the agent's instructions:
balanced grid, hero with supporting photos, portrait strip, layered scrapbook,
and photo backdrop. Describe suitability and relationships, not fixed
coordinates or an exhaustive menu. These are internal design vocabulary,
not language users must learn. At most two compact recipe examples may help;
do not blindly copy their photo IDs/geometry. Patterns cannot infer which
photo deserves emphasis. No template engine, large catalogue, or multi-option
generation in this slice.

## Evaluation and learning

Separate three questions:

| Question | Evidence |
|---|---|
| Is the recipe valid and renderable? | Existing strict validation and deterministic rendering; focused offline tests for the new integration. |
| Does it follow directions? | Small agreed cases covering initial creation, preference overrides, photo emphasis, and targeted edits that preserve unrelated properties. |
| Is the composition appealing and easy to refine? | User inspection of previews and feedback on the interaction, using Emma's photos and existing examples as references rather than required answers. |

Use the fixed plain-language sequence below, with offline failure/resumption
tests alongside it. Mechanical validity does not prove instruction-following
or subjective appeal. Record weaknesses before adding features or automation.

### First scripted live sequence

Use a fresh format 2 project with Emma's four photos in the documented order:
Bridge 1, breakfast 2, Eye 3, bookshop 4. Start with a 1200x1800 canvas,
cropping forbidden, and the agreed subtle border/rounding/tilt defaults.
Do not pass filenames or inferred image descriptions to the model.

| Step | User request/action | Mechanical evidence |
|---|---|---|
| Initial creation | "Make a collage with a dark grey background. Make photo 2 smaller than the others." | Valid whole-photo preview, each photo once; dark neutral background; photo 2's untilted outer-frame area less than each other photo's. Positive white borders and positive rounding on all four; at least one nonzero gentle tilt. No accepted version yet. |
| Targeted edit | "Make photo 2 a bit smaller. Keep it in the same spot and leave the rest alone." | Photo 2's outer width decreases by at least one output pixel, centre stays within one pixel on each axis, and its mode/style/crop stay unchanged. Canvas, stacking, and every other layer remain unchanged. |
| Styling override | "Remove the borders. Leave everything else alone." | Every border absent or zero-width; other authored recipe fields and the defaults file unchanged. Do not silently resize boxes to compensate. |
| Resume and refine | Exit/restart, then "Make all the photos straight. Keep everything else as it is." | Resumed proposal/context used; rotations zero, borders still absent; other authored fields unchanged. |

Use these fixed comparisons, rather than tuning thresholds after seeing output:

- Parse the solid background's RGB bytes. Each channel must be 16-80 inclusive,
  with maximum minus minimum at most 12. This is the benchmark's documented
  dark-neutral range, not a universal definition of dark grey.
- Initial border widths must be 1-12 pixels with colour `#FFFFFF`, positive
  photo-edge radii at most 16 pixels, and absolute rotations at most 3 degrees;
  at least one angle must be nonzero. These are checks of this fixture's
  preferred subtle style, not additional engine limits for other requests.
- Use resolved untilted `box_pixels` areas to compare photo sizes. For the
  targeted edit, the integer outer width must decrease by at least one pixel.
  Compare centres as left/top plus half width/height, with at most one-pixel
  movement on either axis. Report actual size/area changes: a minimal numeric
  decrease proves direction, not that the change is perceptually sufficient.
- Compare model-validated recipe values keyed by stable photo ID, retaining
  layer-array order as its own invariant. Expand default fields; normalize
  equivalent hex case and absent/null/zero-width borders where appropriate.
  Do not hide nonzero geometry/style differences using broad tolerances.
- In the resize step, only photo 2's box coordinates/width may change; its
  position adjustment must satisfy the centre check. In the border step,
  only border fields may change. In the straightening step, only rotation
  fields may change. Other normalized coordinates/numeric fields must match
  after canonical validation, not just produce similar pixels.
- Removing an outside border in whole mode changes derived photo dimensions
  and can change derived height even when the authored box is unchanged.
  This is existing engine behaviour, not permission to change other fields.
- All four proposals must satisfy the active canvas/cropping controls and
  sampled-footprint checks. A question instead of a recipe in these fully
  specified core cases is a failed case, not a passing clarification test.

The wording "a bit smaller" deliberately does not prescribe a hidden percentage.
Do not inject more precise user instructions behind the scenes. The agent may
choose any engine-valid composition meeting the stated checks; no LLM judges
its own output.

Inspect and accept a selected successful proposal using local operations;
verify no inference call, exact accepted recipe/preview identity, immutable
earlier versions, and the resulting editing baseline. Exercise accepting an
older proposal and rating controls in offline tests with clearly synthetic
test feedback, not fabricated real-user judgments in the live history.

The sequence does not demand matching Emma's collage, a particular pattern,
or a model-generated explanation that merely claims success. Save requests,
proposals, objective comparisons, and failures as evidence.

Normally the four turns require four inference requests, at most sixteen under
the revised three-correction limit if every turn needs all its corrections.
The existing shared 50-attempt ceiling leaves room
for bounded implementation debugging; it is not fifty independent design
variants. Do not silently retry a renderable but instruction-noncompliant
response. A materially revised code/prompt/configuration approach after an
acceptance failure starts another development round; subsequent calls use the
same request ledger. A model correction within the application loop consumes
an inference attempt, not a separate development round.
Keep the four scripted user prompts and comparison rules fixed. Reuse passing
work where faithful context permits; if a fresh sequence/project is required
for a clean comparison, record why and count every repeated request.
Never replace a failed core proposal with a curated example and call it a pass.

### Offline acceptance checks

Use synthetic images and mocked model/HTTP responses for these tests:

- Proposal creation/rendering without acceptance; failed parse/control/geometry/
  rendering/publication preserving the good baseline; strict field/JSON limits.
- Up to three corrections for completed invalid output; success can occur on
  any allowed attempt. Prove the fourth total attempt is allowed and a fifth
  is blocked. No correction for a valid question, and no model retry on
  authentication/service/incomplete/timeout/render-I/O failure.
- Useful, bounded numeric geometry feedback updated for each failed candidate;
  include whole-photo height, canvas-axis scaling, rotated/sampled extents,
  and safe position ranges where available. Feedback must not silently repair
  recipes or advance the valid baseline.
- Questions followed by actual answers, no guessed image content, resumed
  baseline/defaults/style context, and accepting an older proposal despite
  newer unaccepted proposals.
- Whole-only enforcement until `/cropping allow`; cover allowed afterwards;
  canvas changes enforced; stale-control acceptance refused without restoring
  older permissions. Invalid local commands change nothing and call no model.
- Show/status/rating/accept/quit without inference or credential initialization;
  first acceptance, idempotent repeat acceptance, later reacceptance as a new
  version, proposal/accepted recipe and PNG identity, and immutable old versions.
- Interrupted acceptance either reconciled to its exact committed result or
  explicitly blocked; altered/missing previews, corrupt state, and external
  accepted-version changes never silently repaired or overwritten.
- Shared request reservations across projects and process reconstruction;
  attempts 49 and 50 allowed, attempt 51 blocked, pending/failed reservations
  never reclaimed, budget/preflight failure making no outbound inference.
- Full outbound context/output-limit/timeout/storage/retry configuration,
  including framework-generated messages/schema; no source paths/filenames/
  image bytes or credentials in the metadata payload; ratings stay local.

Routine tests must never initialize real credentials or contact Foundry.
Keep existing offline CLI commands/tests working without the optional agent
dependencies. Run targeted checks while developing, then the existing full
suite with the new offline cases before a successful handoff. Do not claim a
particular future test count or require real personal photos for unit tests.

## Provider and compatibility gate

After implementation approval, use the existing endpoint and `gpt-5.4-mini`
deployment documented in the
[separate Foundry experiment](../temp-foundry-test/README.md), with
`DefaultAzureCredential` and its documented token audience. Do not run or
modify those smoke-test scripts or reuse their environment as the application.
No new Azure resource, deployment, role, API key, interactive login, or service
configuration changes. If credentials are unavailable, stop with instructions.

Keep the provider/Azure dependencies minimal and pin the verified provider
version in an opt-in agent requirements manifest layered on the root app
requirements. Install only into the root app environment after changing that
manifest. Preserve engine-only setup/use; defer provider/credential imports and
client construction until a live operation is explicitly requested.

Before spending inference attempts, inspect the chosen SDK/framework API and
use a mocked transport to establish:

1. The structured response contract, local history reconstruction, and actual
   outbound request are supported without a hosted agent/session or tools.
2. The 25,000-token completion bound includes reasoning, response storage is
   disabled, the overall attempt has a 120-second deadline, and all SDK/framework
   inference retries/continuation loops are disabled. The request gate rejects
   unexpected additional inference rather than merely counting a hidden loop.
3. Every outbound inference goes through the shared budget reservation, including
   any framework-internal request. A high-level `agent.run` count is insufficient.
4. Input accounting covers the fully assembled request's instructions, examples,
   messages, schema, and serialization/framing overhead, using a verified
   tokenizer with a justified conservative allowance or a supported conservative
   upper bound. Do not pass an unsupported model name to a generic tokenizer and
   silently guess an encoding. Log the method/bound separately from actual
   provider-reported input usage.

If offline evidence cannot establish these guarantees, report a blocker before
inference. Schema transport or internal API choices may vary only while keeping
the same external semantics. A compatibility request to the actual model,
when necessary, consumes the same approved ledger; it is not a free preflight.
Never respond to incompatibility by raising limits, switching deployments/
providers, bypassing Agent Framework, or dropping hard validation.
If actual reported usage contradicts an enforced limit, preserve the evidence
and halt further live requests pending review.

## Delivery checkpoints and sign-off

### A. Bounded Autopilot implementation and handoff

Build the mechanics and terminal entry point; exercise the same Python path
using mocked tests and budgeted scripted live requests. Continue useful
in-scope work until core criteria pass, a limit prevents further progress, or
a blocker requires user input. An initial live failure is not itself a reason
to stop if evidence supports a permitted correction.

Always hand off passed/failed/not-reached results, usable outputs, limitations,
and accounting. Stop rather than inventing user feedback or optimizing
subjective quality. Preserve all recurrence/safety/budget stop rules. The user
may authorize another bounded pass after reviewing evidence; never replenish
allowances automatically. Full engineering success is readiness for trial,
not user sign-off; a limited partial result is still a valid honest handoff.

### B. Later user-led interactive trial

The user runs the delivered terminal, tries unscripted requests, inspects PNGs,
and optionally rates edits separately from accepting a collage. Conducting
the trial is not checkpoint A work. Do not fabricate its feedback during
Autopilot.

Agree its service allowance separately; unused checkpoint A slots are not
permission for free/unlimited interactive use. Phase sign-off follows review of
engineering evidence and actual user feedback. Accepting a collage is not
phase sign-off. Any subsequent implementation/prompt changes need an agreed
bounded follow-up, not a silent extension of checkpoint A.

## Initial Autopilot service ceiling

The user agreed **50 attempted Foundry model requests** for checkpoint A's
first pass. This is a ceiling, not a target or authorization for follow-on work.

The user subsequently explicitly authorized resuming checkpoint A with a
**fresh 50-request allowance**, excluding the two separately requested
France/Paris diagnostic calls. That authorization changed service accounting
only, not implementation retries, per-request caps, comparisons, or scope.
The original diagnostic ledger was preserved before provisioning the authorized
fresh allowance. See the latest handoff; no automatic renewal is permitted.

At preparation of the next pass, 3/50 attempts are consumed and **47 remain**.
The proposed development-round budget does not renew this service allowance.
The run stays halted until a separately approved execution start is recorded.
This preparation snapshot was superseded by the user's later explicit
fresh-50 authorization, preserved in the latest follow-up handoff.

- Count actual inference attempts, not high-level agent turns. Each initial
  generation, refinement, model-based correction, or inference connectivity
  check consumes an attempt. Failures and timeouts count even when no response
  or usage information returns.
- Share the ceiling across corrections/resumed runs. Reserve before dispatch;
  no process/project reset and no request 51.
- Preflight malformed/local-state/oversize-input failures before dispatch use
  no inference attempt. Once durably reserved for dispatch, a slot is consumed
  even if interrupted before a response; do not reclaim uncertain attempts.
  Never dispatch if the reservation cannot be saved.
- Disable SDK/framework automatic retries. Any explicitly permitted application
  retry or additional inference within an agent turn consumes another attempt.
- For the next approved pass, allow up to three validation-guided corrections
  as specified in the response contract: at most four attempts per user prompt,
  within remaining budgets. If those corrections fail, stop the turn and retain
  the good proposal. Each dispatched correction is metered like the initial call.
- Service/authentication errors, timeouts, and incomplete responses stop the
  turn with an explicit error, without automatic retry.
- Stop earlier when the agreed cases are complete or another limit is reached.
  Do not spend remaining calls searching for a subjectively perfect collage.
- Record per-attempt purpose, outcome, latency, and provider-reported input and
  output tokens, including cached/reasoning breakdowns where available. Report
  cumulative totals and identify missing usage rather than treating it as zero.
  Cached input and reasoning output breakdowns are subsets, not extra tokens
  to add to the provider's corresponding totals.
- This ceiling covers application Foundry inference, not the Copilot coding
  session's own usage. The later user-led trial requires a separate allowance.

The earlier Foundry screenshot (7 requests, about 4.55K tokens, estimated cost
below EUR 0.01) is not a forecast for layout/history-sized payloads.
Agreed limits:

| Limit | Ceiling |
|---|---|
| Inference attempts | 50 across the shared authorized service allowance, including failures and corrections; no automatic reset for a new development pass |
| Input per attempt | 50,000 tokens, including instructions, schema, metadata, history, and feedback |
| Output per attempt | 25,000 tokens, including reasoning tokens |
| Timeout per attempt | 120 seconds |
| Separate monetary cap | None; use the request/token limits as the spending guardrail |

Across 50 attempts this permits at most 2.5 million input and 1.25 million
allocated output tokens, not expected consumption or a quoted monetary cost.
Report estimated cost only where applicable verified pricing is available;
identify uncertainty and missing usage.

Verify model/API support and an enforceable input-token counting strategy
before live dispatch. If limits cannot be enforced, stop and report rather than
substituting an unverified tokenizer or increasing limits. If context is too
large, fail clearly; do not silently truncate or compact conversation history.
Any future compaction strategy needs separate scope agreement.

## Implementation development-round budget

These rules govern the **explicitly approved checkpoint A follow-up pass**.
They replace the overlapping per-package/macro limits for that pass, not its
historical audit. The completed pass used the earlier policy from
[record 004](004-engine-refactoring.md): two local cycles per package, two macro
rounds, and six shared cycles. Its reported 6/6 result stays closed.

- **One shared limit: six meaningful development rounds total.** The first
  follow-up hypothesis/change bundle is round 1, not a free preliminary pass.
  There are no additional per-package or macro counters. Work-package labels
  may organize reporting but cannot create or replenish allowances.
- **A round is a coherent, evidence-backed hypothesis/change bundle followed
  by its acceptance re-evaluation.** Before starting, record the failure being
  addressed, the hypothesis, intended changes, and the acceptance check that
  will close the round. That check may be a focused offline acceptance test or
  an applicable live case; it need not repeat every passing case after each edit.
  A failed acceptance re-evaluation closes the round. A subsequent materially
  changed application/prompt/configuration approach starts the next round.
- **Routine authoring friction is not a separate round.** Failed patch
  application, one-off audit/report formatting, incidental test-harness setup,
  and supporting targeted checks stay within the current bundle (or normal
  preparation/handoff). Record these briefly without charging separate rounds.
  Actual application-behavior failures or a different engineering hypothesis
  must not be relabelled as administrative fixes. Never weaken a test to avoid
  counting a failed acceptance check.
- **Application model corrections are not development rounds.** Up to three
  hard-validation corrections for one request belong to the same application
  turn. Every actual inference still consumes the shared service allowance.
  Further source/prompt changes after a failed acceptance evaluation require
  another development round. Re-running a failed live acceptance case without
  a material change also consumes a round and needs an evidence-backed reason;
  it is not a way to sample until lucky.
- **Stop for non-progress.** Stop after two consecutive rounds reproduce the
  same acceptance failure without new diagnostic evidence or measurable
  improvement. Record the comparison: for example, changed overflow magnitude,
  a newly passing case, or a newly isolated cause. Cosmetic log changes, renamed
  work packages, and repeated unchanged tests are not progress.
- Record each round's hypothesis, changes, acceptance evidence, result,
  progress/non-progress assessment, and remaining rounds. Preserve failed
  evidence and prior passing work where its context remains valid. Counters
  are shared across commands, agents, restarts, and sessions; splitting work
  or restarting does not reset the six-round limit.
- Stop when the cases pass, six rounds are used, the non-progress condition is
  met, service allowance is exhausted, or a safety/compatibility/scope blocker
  requires user input. Do not start a seventh round. Finish the scoped
  revalidation for round 6 and the accounting/handoff, even if it is partial.

The six-round development budget and shared Foundry allowance are independent.
Neither grants additional allowance under the other. The 50,000 input-token,
25,000 output-token, 120-second per-attempt caps, strict engine/response
validation, no SDK/service retries, no silent recipe repairs, and no-Git-write
guardrails remain unchanged. The later user-led trial is still out of scope.

## Implementation decisions and approval boundary

Choose physical filenames, Python modules/helpers, serialization classes,
atomic-file staging details, test organization, and the verified SDK API during
implementation. Keep these choices small and consistent with existing patterns;
they are not permission to alter the contracts above. The exact provider package
version and compatible structured-output request method must be verified, not
guessed.

No further product decision is required to review this brief. Stop and report
if implementation requires changed user-visible behaviour, extra authority,
unverifiable limits, relaxed acceptance checks, or an expanded retry/service
budget. Do not substitute an open-ended design investigation.

Explicit approval of checkpoint A authorizes only this bounded implementation,
its necessary app-environment dependencies, and the recorded first-pass live
evaluation. It does not authorize Git writes, Azure changes, the user-led live
trial, or follow-on Autopilot passes. Agree the interactive trial's allowance
after the checkpoint A handoff. Approval of this documentation edit is not
checkpoint A implementation approval.

The later explicit execution instruction authorized the follow-up's six
development rounds and expressly requested a fresh 50-request allowance,
superseding the prepared brief's proposed reuse of 47 slots. That completed
pass does not authorize further work or checkpoint B.

## Execution order and handoff

1. Establish a fresh offline test baseline and record protected photo/archive/
   example state and the user's existing Git index/worktree state.
2. Inspect provider APIs, implement strict records and the request gate, and
   establish mocked outbound-request/limit evidence before any live dispatch.
3. Add proposal/acceptance persistence through shared engine code, the response
   and conversation loop, preferences/controls, and terminal operations.
4. Exercise focused offline cases, then run the fixed scripted live sequence
   under `step2-first-pass`, correcting only within both budgets. Track objective
   results without autonomous subjective-quality optimization.
5. Run applicable scoped/full offline revalidation, confirm protected state,
   update current usage documentation for implemented behaviour only, and hand
   off. If blocked/exhausted, stop further inference/corrections and perform only
   safe accounting/inspection needed for an honest partial handoff.

No fleet, worktree sessions, nested agents, or autonomous multi-agent workflow
is needed for this pass. This brief does not require extra reviewer/model
rounds; any concrete review-driven correction still shares the same budgets.

Handoff must include:

- Engineering checks and each core live case as passed, failed, or not reached,
  with the exact request, proposal/preview paths, comparisons, and limitations.
- Runnable startup/resume/local-control instructions, and whether the terminal
  is usable now; distinguish instructions for future paid use from permission
  to execute them. Include `--no-open`/manual-viewer guidance.
- Attempt count, input/output token totals and missing usage, latency, verified
  cost estimate if available, and development-round/progress-stop accounting.
  Keep the closed earlier pass's cycle counts separate and unchanged.
- Any state conflict or compatibility issue, what is preserved, and evidence
  informing whether another separately approved pass would be useful.

Call the result trial-ready only if the engineering checks and all four core
live cases pass. Otherwise report material progress and its stopping reason.
Neither label is the user's final phase sign-off.

## Scope and guardrails

- Checkpoint A alone was approved for bounded implementation and its recorded
  evaluation. No separate Foundry experiments, authentication changes, user-led
  trial, or follow-on service pass are authorized.
- **No Git writes of any sort:** no staging, commits/amends, pushes, branch/ref
  changes, checkout, worktree creation, stash, reset, Git configuration changes,
  or other Git mutations. Read-only inspection is allowed; use
  `git --no-optional-locks --no-pager` where applicable. Ordinary approved file
  edits are allowed. Preserve the user's index, history, branch, and unrelated
  changes; the user reviews and commits independently.
- Preserve original photos, existing projects/archives, examples, and the
  separate Foundry smoke-test code/environment.
- No graphical UI, cloud deployment, authentication system, image understanding, image
  generation, new rendering effects, or template engine in the proposed slice.
- Preserve current layout rules, numeric limits, and exactly-once photo usage.
  Treat model output as untrusted input; never execute generated code or grant
  arbitrary filesystem/service access.
- Use mocked model responses for routine offline tests. Any live evaluation
  needs explicit approval and finite budgets; disable or account for all hidden
  SDK/framework retries and agent/tool loops.
- No automatic model/provider fallback, unapproved budget increases, relaxed
  validation, or broad autonomous quality-search loops.
- Prior phases' unused retries and service permissions do not carry forward.
  The 50-attempt ceiling applies to this approved checkpoint only; remaining
  slots do not authorize a follow-on pass or the interactive trial.

## Next approval boundary

Checkpoint A's engineering and four scripted live checks now pass. Review the
latest evidence before separately authorizing checkpoint B and its bounded
service allowance, or any additional implementation/evaluation. The completed
follow-up's unspent rounds and requests are not automatic permission to proceed.
Credentials work with the documented process-local PATH fix; no Azure
configuration changes or additional Foundry experiments were made.

## Checkpoint A execution record

This section preserves the **initial credential-blocked handoff**. Its status
and counters are historical; see the authorized resumption below for the
current outcome and accounting.

### Outcome and delivered mechanics

**Partial progress, not trial-ready.** The initial live invocation stopped at
credential acquisition. `DefaultAzureCredential` reported no usable credential,
including Azure CLI not being on PATH; Agent Framework surfaced
`ChatClientException`. No inference reached the request transport, so no attempt
was reserved. The raw Azure diagnostic was local output, not model context.
No authentication/configuration changes or retry followed this blocker.

Implemented optional metadata-only Agent Framework integration; strict reply
and versioned local records; conservative preflight and actual HTTP reservation;
durable conversations and immutable preview proposals; explicit controls,
ratings, acceptance and narrow acceptance recovery; lazy terminal integration;
and the fixed evaluation harness with exact comparisons and numeric evidence.
The existing immediate-accept `apply-layout` workflow remains available.
Source photos and curated examples were not used as replacement model output.

The root application environment resolved provider `agent-framework-openai`
1.18.2, OpenAI SDK 2.54.0, and HTTPX 0.28.1. Only the optional root manifest and
environment were changed; the separate smoke-test scripts/environment were
neither executed nor reused.

### Evidence

Fresh baseline: **252 offline tests passed**. Final implementation validation:
**284 offline tests passed**; dependency compatibility check passed. The added
cases use synthetic photos and fake responses, including the real framework
and SDK over a mocked HTTP transport. They establish request shape, schema
transport, no tools/hosted state, output/storage/retry configuration, conservative
input preflight, interrupted HTTP, 401/429 failures without retries, rejection
of extra inference, strict response correction, resumption, local controls,
older/idempotent acceptance, tampering/conflicts, failure recovery, ledger
exhaustion, and exact benchmark comparisons.

The Windows test-only fixture supplies asyncio's private loopback wakeup pair;
the application/test `socket.connect` network guard remains blocked. Tests do
not initialize real Azure credentials or contact Foundry.

| Fixed live case | Result |
|---|---|
| "Make a collage with a dark grey background. Make photo 2 smaller than the others." | Failed/blocked at Azure authentication before inference; no recipe or preview. |
| "Make photo 2 a bit smaller. Keep it in the same spot and leave the rest alone." | Not reached. |
| "Remove the borders. Leave everything else alone." | Not reached. |
| "Make all the photos straight. Keep everything else as it is." | Not reached. |
| Exact local acceptance of a live proposal | Not reached; covered with synthetic proposals offline only. |

There are no live photo-size/area measurements or proposal PNGs to inspect.
Actual provider/schema compatibility, instruction-following, and visual appeal
remain unverified. No user feedback or ratings were fabricated.

Preserved runtime evidence, relative to the repository root:

```text
.collage-data-step2\users\local-dev\projects\emma-agent-demo\evaluation-report.json
.collage-data-step2\users\local-dev\projects\emma-agent-demo\conversation\state.json
.collage-data-step2\users\local-dev\projects\emma-agent-demo\conversation\events\000001.json
.collage-data-step2\users\local-dev\agent-runs\step2-first-pass\run.json
```

The four-photo project has no accepted version. The report's generic
`ChatClientException` is the recorded failed case; the local Azure diagnostic
establishes the specific authentication blocker. The report is not overwritten
by rerunning the evaluator.

### Budgets and preservation

- **Inference: 0/50 attempts.** Input/output tokens: 0/0; no missing-usage
  attempts. No inference latency or price estimate applies; authentication
  failed before dispatch. The existing ledger is provisioned and must not be
  provisioned again. Unused slots are not permission for further calls.
- **Corrections: 4/6 shared cycles; 1/2 macro rounds.** Cycle 1 constrained the
  optional SDK/HTTP dependencies after the initial install resolved an
  incompatible SDK major. Cycle 2 enabled only Windows asyncio's private
  wakeup pair in offline tests. Macro cycle 3 preserved failed-publication
  exchanges and completed benchmark measurement/acceptance-error evidence.
  Their scoped/full rechecks passed. Cycle 4 corrected a partially applied
  documentation patch and checked the handoff's links/accounting.
- Package use: agent/context/preferences **1/2**; proposal/conversation
  persistence **1/2**; shared-engine/terminal **0/2**; tests/scripted evaluation
  **2/2**; documentation/handoff **1/2**. These overlap with, not add to, the
  shared ceiling. No correction was attempted for the credential blocker.
- All **78 protected file hashes matched**, covering original photos, curated
  examples, existing runtime archives, and the protected smoke-test files.
  Git HEAD stayed `ec7565f294ba956234d1f5108aa70fd8eccf7d42`.
  No staging, commits, pushes, branch/ref changes, or other Git mutation
  commands were run. The index byte hash differed at the first preservation
  check despite the same two staged paths; a subsequent read showed additional
  implementation files staged during the run. The source of those index changes
  is not established. The index was not restored, restaged, or rewritten by
  an agent command; do not assume all implementation edits remain unstaged.

Session artifacts retain the initial protection snapshot and detailed
correction ledger as `files\step2-baseline.json` and
`files\step2-corrections.json`.

### Usable now and next gate

The [CLI guide](../docs/cli-guide.md#conversational-proposals-optional) includes
local startup/resume, preferences, local controls, and future authorized live
usage. Resume `emma-agent-demo` **without `--run`** for local-only status/help
and clean exit; there is no generated proposal to show/accept. Engine examples
and manual recipes remain usable offline.

Make an existing permitted keyless credential accessible to the application
process, then agree a bounded follow-up after reviewing this evidence.
Reuse `step2-first-pass`, preserve the failed report, and use a fresh evaluation
project if a new fixed sequence is authorized. Do not infer permission for
checkpoint B or more calls from this handoff.

## Authorized resumption and final checkpoint A handoff

### Authorization and preserved progress

After a fresh user-performed Azure login, a token-only probe succeeded using
the root application environment and a process-local Azure CLI PATH addition.
At the user's explicit request, the original France/Paris smoke script then
succeeded unchanged for two turns. It was executed in the root environment,
not the separate experiment environment. The user excluded those two calls
from checkpoint A accounting and explicitly requested:

> Please continue checkpoint A with a fresh 50 request budget.

The two diagnostic attempts and their 88 input / 36 output tokens remain in
`agent-runs\archive\step2-diagnostics-before-authorized-resume`.
The active `step2-first-pass` ledger was provisioned once for this explicit
new authorization; its `authorization.json` links the approval and archive.
No attempts were deleted or reclaimed. Implementation counters carried forward
at 4/6 cycles; the new service allowance did not reset them.

The staged implementation was reused, not rebuilt. New evaluation projects
preserved the earlier authentication report and the subsequent schema-error
report. No passing collage proposal existed to reuse.

### Changes and final evidence

The first resumed inference failed HTTP 400: Responses forbids a top-level
`oneOf` in its output schema. The provider adapter now uses an object root with
the same payload fields and adapts nested mutually exclusive whole/cover
branches to supported `anyOf`. The unchanged strict local response union rejects
missing/mixed payloads and still enforces the full engine contract. No prompts,
comparison thresholds, geometry, controls, or accepted-output rules were relaxed.
Real framework/SDK mocked-request checks now cover this observed restriction.

The full offline suite passed again: **284 tests**. Two subsequent live
responses demonstrate working authentication, endpoint/deployment access, and
native JSON-schema transport, but **neither recipe was engine-valid**:

| Fixed live case | Final result |
|---|---|
| "Make a collage with a dark grey background. Make photo 2 smaller than the others." | Failed after the initial response and its one allowed validation correction: photo 4 extends beyond the canvas. |
| "Make photo 2 a bit smaller. Keep it in the same spot and leave the rest alone." | Not reached; no valid preceding proposal. |
| "Remove the borders. Leave everything else alone." | Not reached. |
| "Make all the photos straight. Keep everything else as it is." | Not reached. |
| Local acceptance of a live proposal | Not reached; synthetic acceptance/recovery checks still pass offline. |

Photo 4 had whole-mode normalized width `0.38`, a 10-pixel border, and source
aspect 3:4 on 1200x1800. Its derived unrounded normalized outer height is about
`0.334074`. The first response placed its top at `0.88` (bottom about `1.214074`);
the correction moved it to `0.83` (bottom about `1.164074`, still outside even
before tilt). This is not a marginal sampling/tolerance failure. Validation
prevented publication: **no successful proposal, PNG, or accepted version**.
No clipping, clamping, curated replacement, second correction, or user rating
was introduced to obtain a pass.

Evidence under `.collage-data-step2\users\local-dev\projects`:

```text
emma-agent-demo\evaluation-report.json                 initial auth failure
emma-agent-resume-01\evaluation-report.json            native-schema failure
emma-agent-resume-01\provider-diagnostic.json          bounded HTTP 400 details
emma-agent-resume-02\evaluation-report.json            final failed live case
emma-agent-resume-02\conversation\events\000001.json    initial recipe/error
emma-agent-resume-02\conversation\events\000002.json    correction recipe/error
```

### Final budget and protection accounting

**Renewed inference allowance: 3/50 attempts; run halted pending review.**
Attempt 1 was the schema HTTP 400 with unreported usage. Attempts 2/3 completed
at the API but failed layout containment. Known provider usage is **7,140 input
and 540 output tokens**, with attempt 1 explicitly unknown, not assumed free.
Cached input is 2,816 of those input tokens; reasoning output is 0 of those
output tokens. The separately excluded two diagnostic calls are not added to
these funded-run totals.

Recorded HTTP durations were 0.594, 2.188, and 1.953 seconds (4.735 seconds
total), excluding credential/setup/test time. No applicable pricing was
verified, so no monetary estimate is supplied. All per-request caps remained
50,000 input / 25,000 output including reasoning / 120 seconds.

**Implementation: 6/6 shared cycles; 1/2 macro rounds.** Cycle 5 completed the
resume-authorization audit record after a session helper passed a plain dict
to the existing BaseModel-only save function; it reused the already-created
allowance rather than provisioning again. Cycle 6 corrected the provider wire
schema and revalidated offline/live. Final package use:

| Package | Cycles |
|---|---|
| Agent/context/preferences | 2/2 |
| Proposal/conversation persistence | 1/2 |
| Shared-engine/terminal interaction | 0/2 |
| Tests/scripted evaluation | 2/2 |
| Documentation/handoff | 2/2 |

Package counts overlap within the shared cycles; they are not additive.
The unspent macro round and 47 service slots cannot override the exhausted
shared limit. No further implementation, prompt tuning, or inference followed
the failed correction. The active run's persisted `halted` flag prevents
accidental continuation.

All **78 original protected hashes matched**, and HEAD remained
`ec7565f294ba956234d1f5108aa70fd8eccf7d42`.
The user's staged index matched its resume SHA-256
`2990BCA9C97633FF8EEE28E6D1B172CED219DD739A1957BA8C2D434F8BA64094`;
no Git mutation commands were run. New schema/test/doc edits remain outside
the user's staged snapshot.

### Usable now and next gate

Resume `emma-agent-resume-02` without `--run` for local status/help and exit;
the [CLI guide](../docs/cli-guide.md#conversational-proposals-optional) includes
the exact command and process-local PATH fix. There is no live preview to
inspect or accept. The deterministic manual workflow remains usable offline.

**Partial progress, not trial-ready.** The remaining concrete issue is reliable
whole-photo containment and useful numeric correction feedback, not Azure
login. A separately authorized bounded follow-up could test more explicit
footprint/legal-position feedback or a compact worked layout example, preserving
the strict engine and the same benchmark. Neither that work nor checkpoint B
is authorized by unused requests.

## Authorized six-round follow-up handoff

### Authorization and preserved accounting

After staging the previous edits, the user explicitly requested:
"Please continue checkpoint A with a fresh 50 request budget." This authorized
the revised six-development-round checkpoint A follow-up and expressly renewed
its service allowance; it did not authorize checkpoint B or Git writes.

Approval was recorded before preserving the halted previous run at
`.collage-data-step2\users\local-dev\agent-runs\archive\step2-before-six-round-followup`.
Its three consumed attempts, known 7,140 input / 540 output tokens, and one
unknown-usage attempt remain unchanged. The excluded Paris diagnostics remain
in their earlier separate archive. A new `step2-first-pass` allowance uses the
same 50K input / 25K inclusive output / 120-second per-attempt ceilings.
Its `authorization.json` and `completion.json` preserve approval and final
accounting. The previous 6/6-cycle audit was not reset or rewritten.

### Implemented changes and development rounds

The existing application, dependency environment, engine rules, native response
schema, and evaluator were reused. Bounds failures now carry candidate-specific
outer, rotated, and sampled footprint bounds, pixel overshoot, and conservative
normalized safe-placement intervals when possible. Diagnostics reuse the
engine's half-up pixel sizing, rotation geometry, and sampling padding.
The recipe remains unchanged and is rejected if invalid.

The conversation allows up to three hard-validation corrections, four total
attempts. Each failed exchange and its latest feedback remain recorded; no
invalid candidate replaces the valid baseline. Baseline context includes
recomputable untilted pixel centres. Pixel-first resize instructions and an
arithmetic example guide the model without calculating a replacement recipe.
The final provider configuration explicitly requests and checks high reasoning
effort; reasoning shares the existing output-token cap.

| Round | Change and outcome | Progress assessment |
|---|---|---|
| 1 | Numeric geometry feedback, four-attempt loop, explicit axis units. Initial containment, border removal, resume/straightening and exact acceptance passed; resize drift was +2.5px x / +5px y. | New passing cases versus the previous containment blocker. |
| 2 | Explicit baseline pixel centres and resize arithmetic. One numeric containment correction succeeded; resize drift improved to 0px x / +5px y. | Measurable horizontal improvement; vertical arithmetic still failed. |
| 3 | Verified low reasoning effort. Resize drift worsened to 0px x / +78px y; other checks passed. | One consecutive non-progress round; low reasoning was insufficient. |
| 4 | High reasoning effort with unchanged prompts, engine, and comparisons. All four cases and exact acceptance passed. | Completed; stopped without using rounds 5 or 6. |

No subjective/scripted instruction-following failure triggered an automatic
model correction. Failed acceptance evaluations closed their development
rounds, and changed code/configuration preceded each new evaluation project.
All four `emma-agent-followup-01` through `-04` reports remain immutable evidence.

### Final engineering and live evidence

**295 offline tests passed**, versus the fresh 284-test baseline. Focused
regressions cover success on attempt four, refusal to dispatch a fifth attempt,
valid-baseline preservation, feedback for the latest candidate, safe-placement
intervals checked against actual whole/cover geometry, continuous/rounded/
sampled bounds failures, and oversized frames without a legal placement.
Real-framework mocked HTTP checks verify high reasoning, native structured
output, inclusive output caps, request metering, and no SDK/service retries.

Final evidence root:

```text
.collage-data-step2\users\local-dev\projects\emma-agent-followup-04
```

| Exact request | Result and comparison |
|---|---|
| Make a collage with a dark grey background. Make photo 2 smaller than the others. | Passed as `P001`: dark neutral background; photo 2 area 127,608px versus 219,096px for every other photo; required subtle borders, rounding and tilt. |
| Make photo 2 a bit smaller. Keep it in the same spot and leave the rest alone. | Passed as `P002`: width 312 to 300px; area 127,608 to 117,900px; centre stayed exactly (594, 726.5)px; unrelated authored fields and layer order unchanged. |
| Remove the borders. Leave everything else alone. | Passed as `P003`: only border fields changed. Derived whole-photo height changes are expected, not authored-field edits. |
| Make all the photos straight. Keep everything else as it is. | Passed after reopening as `P004`: only rotation fields changed; borders remained absent. |

Each immutable preview is at
`conversation\proposals\P001\preview.png` through `P004\preview.png`.
`evaluation-report.json` contains exact prompts, measurements, paths, and
comparison results. Accepting `P004` created version 1, with the exact proposal
recipe and byte-identical PNG, without another model call or replacement render.
Proposals did not change accepted state before that explicit evaluation action.

The final high-effort configuration used four calls for four requests, with no
model correction. Across the follow-up, one completed invalid geometry response
received a successful numeric-feedback correction in round 2. This is one
successful scripted run on the final configuration, not proof of broad model
reliability, subjective layout quality, or user approval.

### Service, preservation, and next gate

The fresh allowance used **17/50 requests**; **33 remain unspent**. Reported
usage totals **85,068 input / 19,126 output tokens**, with no missing usage.
Cached input is 44,288 of those input tokens; reasoning is 14,707 of those output
tokens, not additional usage. Summed recorded HTTP duration was about 99.38
seconds; setup, offline checks and documentation are excluded. The largest
conservative serialized-input bound was 30,759, below 50,000. No verified pricing
was obtained, so no monetary estimate is claimed.

The run is **halted after success**, not exhaustion. No more inference or
implementation followed the passing evaluation; only offline revalidation,
accounting and this handoff. No new dependencies, Azure configuration changes,
SDK retries, provider fallback, relaxed comparisons, or automatic recipe repairs
were introduced. Original photos, examples, archives, the earlier failed
reports, and the original closed cycle ledger remain protected.

The user's newly staged snapshot was preserved (index SHA-256
`D2B7FB1FC405D31C4949A9F1784096AB81C5A48DF3366F09545CB79E534DB026`);
HEAD stayed `ec7565f294ba956234d1f5108aa70fd8eccf7d42`.
No Git mutations were performed; this follow-up's source/test/doc edits remain
unstaged. All 78 protected hashes matched at baseline and final verification.

The terminal is usable locally now; the
[CLI guide](../docs/cli-guide.md#conversational-proposals-optional) gives the
exact startup/resume command and process-local Azure CLI PATH fix. Resume
`emma-agent-followup-04` without `--run` and with `--no-open`; `/show P004`
prints the existing final preview path for a manual viewer. Local status,
preview and explicit acceptance do not call the model.

**Trial-ready under checkpoint A's bounded checks.** Checkpoint B is the
separately approved user-led trial and remains unstarted. Neither the 33 unused
requests nor the two unused development rounds authorize it or further tuning.
