# 018f: Current collage, history and download

**Status:** Successfully completed and closed on 2026-11-26 with the user's
manual sign-off and requested Demo retirement. The agreed workflow and final
cleanup are verified; see [018f results](018f_results.md) for evidence and limits.
[018e](018e_results.md) is complete and closed with manual sign-off; all earlier
Copilot live allowances remain closed. See the
[018 tracker](018-local-conversation-and-preview.md) for phase boundaries.

## Outcome and agreed boundaries

Complete the basic local design workflow without exposing separate Select,
Accept or finalization concepts. Users can continue chatting from the
**Current collage**, inspect earlier results without changing it, explicitly
choose an earlier result as the starting point for further edits, and download
any saved result at its original canvas resolution.

Keep the conversation-left / collage-right workspace. Historical viewing is
temporary and separate from the current editing source. Choosing a source is
an explicit, durable local action; downloading is read-only. Neither requires
acceptance, rendering a new proposal or an LLM request.

In scope: historical thumbnails and modal, current-collage labeling, saved
source-selection activity, confirmed abandonment of pending clarification or
unclaimed preparation when switching sources, PNG download, thin application/
API connections, and focused offline/model-free verification.

Out of scope: web Accept/finalization controls, accepted-version management,
graphical layout editing, photo/canvas changes, adding/removing photos, deletion,
draft autosave, automatic repair or retry, stopping running model work, agent
prompt/reasoning tuning, new evaluation scenarios, vision, authentication,
cloud/Blob, queues and broad end-to-end trials. Existing CLI/replay acceptance
and natural-language return behavior remain intact. 018g stays separate and
unapproved.

### User-approved closeout cleanup

After accepting the real workflow, the user requested retirement of the original
fixed-message Demo: its navigation, fake project page, script, bundled sample
assets and supporting styling. Remove Demo-only tests/types while preserving
shared components and styles needed by real saved projects. Verify the real
workspace and retired route before closing 018f.

That cleanup is complete and supersedes the original Demo-retention requirement.
The user's further smoke test and commit remain user-managed; this closeout
does not authorize Git writes, 018g or additional model calls.

## User-visible interactions

| Surface or action | Required behavior | Persistence |
|---|---|---|
| Current collage | Rename the right-hand **Preview** heading to **Current collage**, with the explanation **Edits start from this collage**. Show its actual proposal ID and a **Download PNG** action. An older selected proposal can be current; do not call it Latest. | Uses the saved editing baseline, not separate browser state. |
| Successful new layout | Update Current collage after confirmed publication. Show a prominent right-panel overlay through the saved-state handoff and actual PNG loading; keep failures/recovery explicit. Ordinary chat remains the primary workflow. | Existing immutable proposal and baseline behavior; transient loading feedback. |
| Historical result | Show a small, labeled thumbnail with its original proposal-bearing conversation outcome. Failed or non-layout responses must not acquire invented thumbnails. Repeated references identify the same preserved proposal. | References the existing saved proposal; no copied browser history. |
| Open thumbnail | Open a modal showing that exact proposal, its ID, **Download PNG** and **Edit from this collage**. Leave Current collage and the editing source unchanged. | Temporary, per-tab viewing only. |
| Close modal | Close through the close control or Escape and return focus to the thumbnail. Closing, reopening or refreshing never selects the viewed proposal. | Nothing to save. |
| Edit from this collage | Attach smaller helper text to this button: **Use this as the starting point for future edits. Your history stays saved.** Do not present it as a statement about viewing/downloading; hide it for Already current. Save the exact source selection, then close the modal and update Current collage only after confirmed success. No extra confirmation for an ordinary switch with no pending work. | Durable baseline change and user activity, not a new proposal or acceptance. |
| Selection activity | Append a visually distinct user activity entry with the selected thumbnail: **You chose collage P008 as the starting point for further edits.** Use the actual ID. Do not present it as an assistant reply or a text prompt the user typed. | Stable identity and chronological position, restored after reopen. |
| Download | Download the exact stored PNG for the displayed proposal, whether historical or current, at its stored canvas dimensions. | No project, baseline, naming, acceptance or operation mutation. |
| Reopen/refresh | Restore the saved current source and activity alongside existing messages, pending interaction and status. The modal starts closed; unsaved viewing state need not survive. | Read the backend; never redispatch an action. |

Source selection is repeatable, not a one-way decision. After choosing P003,
the user can open P005 and choose **Edit from this collage** to make P005
current again, or choose any other saved proposal, subject to the same
busy/uncertain-work safeguards and pending-work confirmation. Each actual
choice is recorded; no proposal, later history or learned name is removed.

Label an already-current proposal as current and disable redundant selection
when there is no unfinished task. If choosing that same source would abandon
pending clarification or unclaimed preparation, keep the action available
with the confirmation below: ending that task is a real saved action even
though the source itself does not change. Never dismiss pending work silently.

Historical browsing and downloads may remain available during work or recovery
where valid published images can be read. **Edit from this collage** is disabled
with a clear reason while this tab is submitting, another mutation owns the
project guard, or a mutation has an uncertain outcome. Image-read failure must
not be misrepresented as an empty project or successful download.

Preserve the 018e contextual composer, Enter/Shift+Enter behavior, IME handling,
fixed conversation-header refresh, Check status recovery, truthful stage
feedback, image-load/reload handling and responsive layout.
Use existing React/Bootstrap modal facilities, with keyboard focus management,
accessible names and visible errors. Start with lazy-loaded thumbnails from
the existing verified PNG path; do not eagerly fetch every full-size historical
image or introduce a second renderer.

## Switching while an interaction is unfinished

The following are distinct from running or uncertain execution:

| Saved state | Selection behavior |
|---|---|
| No pending interaction or unresolved operation | Select directly after server validation. |
| Unanswered question | Explain that switching ends the unanswered request; require explicit confirmation before selection. Preserve the question and later history as historical records. |
| Unconfirmed naming reassignment | Explain that the pending name change and any associated edit will not be applied. Require confirmation. Preserve already learned names; never implicitly approve or reverse a naming change. |
| Prepared generation, never claimed | Allow confirmed abandonment and selection only after the backend proves this exact preparation is still unclaimed. Do not generate first or refund/renew its consumed interpretation allowance. |
| Running, interrupted/uncertain, or inconsistent state | Block selection and offer existing read-only status/inspection guidance. Time elapsed, a closed tab or a released guard is not evidence that cancellation is safe. |

Confirmation applies to the exact pending state and target shown to the user.
A stale revision or changed operation requires a fresh read and, if applicable,
fresh confirmation. Canceling the confirmation leaves both source and pending
work untouched. There is no standalone cancel-running-request feature.

A completed selection ends the abandoned logical task, clears only its pending
question/receipt or preparation eligibility, and makes subsequent messages
start from the selected layout. Do not let a later answer, refresh, stale
callback or old **Continue generation** POST resume the abandoned task.
Retain its original submission, outcomes and actual model-attempt accounting;
show a concise abandoned-request outcome where needed, not a misleading
generation failure.

## Shared backend and persistence approach

Use the existing boundaries in the [architecture map](../architecture.md).
This is a bounded extension, not an agent rewrite. Surgical backend changes
are expected within the proposed implementation scope to keep the saved
baseline, navigation history and pending-task state consistent. The boundary
is avoiding major restructuring, not leaving the backend untouched;
the user explicitly approved this bounded implementation on 2026-11-26.

- `agent`: provide a small deterministic source-selection/task-boundary entry
  point using the existing exact-selection, naming and canonical history
  invariants. Validate the target as an already published proposal in this
  project. No model client, fake model response, invented raw JSON or call
  reservation is needed.
- `application`: coordinate the local action, pending-work abandonment,
  revision/guard checks, durable outcome and transcript projection. Extend the
  current operation-based projection to include local activity in its actual
  chronological position.
- `api`: validate the HTTP envelope and opaque identifiers, call the ordinary
  workflow and return safe typed results. Keep Functions/HTTP types outside the
  agent and engine.
- `web`: present thumbnails/modal/current source, request the local action and
  download bytes. Never author an intent/recipe, mutate a baseline optimistically
  or infer cancellation safety from a button state.

At briefing, `Conversation._select()` was private and model-path-oriented;
`LocalEvent` covered controls/rating/accept, while pending questions,
names and logical tasks are reconstructed from canonical history. Do not just
change `state.baseline`, inject a frontend message or clear a pointer without
updating those invariants. Reuse a canonical selection outcome where truthful;
keep the application action distinctly identifiable as user activity. Any
necessary event-model change must include task/navigation reconstruction and
pending-name validation, not only serialization.

Preserve learned names, forgotten-name protections, controls, original photos,
all later proposals/messages and accepted versions. Source selection must not
create an accepted snapshot, render/copy a new proposal or restore old names.
The next ordinary edit uses the selected recipe through the existing shared
interpretation/generation path; naming and generation behavior otherwise stay
unchanged.

Use strictly validated, versioned records. Prefer the smallest change that
retains existing ordinary project/layout/conversation contracts. If a persisted
contract must break, version only that affected contract and update dependent
code/tests/docs together; do not silently reinterpret old records, add dual
paths or migrate user archives. A design requiring loss of access to existing
web conversations or wider storage/agent restructuring is a review stop, not
permission hidden in this brief. Do not bump layout format 3 for this feature.

### Guarding, duplicate actions and uncertain outcomes

Give each source-selection action a stable UUID and immutable identity binding
the project, target, revision and abandonment confirmation. Use the existing
non-waiting, cross-process per-project mutation guard for selection and
preparation abandonment, just as for generation.

Under that guard, validate the current revision, target proposal and exact
pending/operation state before any mutation. A racing generation claim wins
or loses against selection; it must never run from an abandoned handoff.
Retire unclaimed preparation durably so it no longer blocks a new Send or
permits generation.

Persist enough claim/outcome evidence to distinguish completion, confirmed
rejection and uncertainty. Abandonment and selection are one user action:
report success only after operation state, canonical history, baseline and
activity references agree. This does not require a new general transaction
framework. Partial publication must fail closed for inspection, not silently
reset a task or assert that nothing changed.

An identical duplicate action returns its saved outcome without selecting
again or appending activity. Reusing its ID with different content is a
conflict. In particular, replaying an old successful action after further
edits must not move Current collage back. Aborted/unknown responses are
reconciled with reads using the original action identity, never another POST
or a new action ID. A known rejection keeps the modal open with its error.
For an unknown save outcome, keep the modal open, block competing mutations
and offer Check status; reconcile the current saved baseline before claiming
success or failure.

Read-only history/image/status routes remain usable during active work and
retain the 018e executor-thread responsiveness. GETs must not initialize
credentials, repair records or write state. Avoid introducing a second
semantic history; application action records reference canonical events.

## Proposed HTTP and download contract

These routes describe the intended small connection, not a request for a
general navigation/version API:

| Route | Proposed contract |
|---|---|
| `GET /api/projects/<id>/conversation` | Extend the existing read DTO with stable local-activity identities/order and safe source-selection eligibility/confirmation reasons. Return canonical proposal references and canvas dimensions sufficient for current/history display; keep pending/operation semantics explicit. |
| `POST /api/projects/<id>/conversation/selections` | Strict JSON: `action_id`, `proposal_id`, `revision`, `abandon_pending` boolean. The confirmation authorizes only the pending state bound by that revision. Return the saved action outcome/reference and current revision; no prompt, recipe, intent or provider settings. |
| `GET /api/projects/<id>/conversation/selections/<action_id>` | Read the original action's saved status/outcome for lost-response recovery. An old outcome identifies its selected source but does not assert that source is still current. |
| Existing `GET /api/projects/<id>/proposals/<proposal_id>/preview` | Reuse verified immutable PNG retrieval for modal/current display and download. No new rendering or accepted-version endpoint. |

Preserve existing strict UUID/project/proposal validation, bounded JSON,
duplicate-key/unknown-field rejection, local Host/Origin/CORS restrictions,
credential omission, no redirects, safe errors, `no-store` and `nosniff`.
Selection is model-free and available without `-Live`; it does not enable
subsequent model requests when live access is disabled.

Use explicit typed outcomes and eligibility reasons, including confirmation
required, stale revision, busy/unresolved work, abandoned preparation,
completed selection and uncertain action. Keep frontend parsers consistent
with the final DTO. Newly completed actions may return 201, known duplicates
and reads 200, and stale/conflicting/busy state 409 using existing error
conventions. Document the final route/status fields during implementation.
Do not infer success or safe abandonment from HTTP status alone.

For download, retrieve bytes from the configured API using the same validated
proposal identity and fetch policy, then initiate a browser download with a
safe filename such as `<project-id>-<proposal-id>.png`. A cross-origin
`download` attribute alone is not a reliable download implementation.
Handle binary success separately from structured error responses, expose
failure/retry feedback and release temporary object URLs.

The downloaded bytes must equal the saved proposal PNG, with the recipe's
actual width/height, regardless of CSS scaling or the currently selected
proposal. Do not download a thumbnail, screenshot or canvas capture. No
resizing, format choice, resolution selector or download-time regeneration
is included.

## Offline verification and acceptance criteria

Use fresh temporary roots, generated photos, existing offline fixtures and
controlled model clients. Never mutate `.collage-data-web`, user CLI roots,
original photos or preserved trial evidence for verification. Block external
model/network access except owned loopback services. No credential preflight,
Foundry experiment, replay allowance or Copilot live model call is authorized.

| Focus | Required evidence |
|---|---|
| Transient viewing | Open/close several historical thumbnails, including the current one; no baseline, history, names, operation or accepted-version writes. Modal keyboard/focus behavior and image errors work. |
| Durable selection | Generate at least two controlled real proposals, choose the earlier one, reopen with fresh backend objects and verify exact baseline, one correctly ordered activity and unchanged later history/names/acceptance. A subsequent controlled edit starts from that recipe. |
| Pending task abandonment | Question, naming receipt and unclaimed preparation each require confirmation; declining writes nothing. Confirming ends only that task, preserves existing names and accounting, and makes old handoffs unusable. Next Send is independent of abandoned work. |
| Concurrency and duplicates | Stale revision/confirmation, double click, same/different payload under one ID, two tabs/processes, and generation-versus-selection races cannot duplicate activity or execute retired preparation. Replayed completed actions do not reselect. |
| Failure/recovery | Storage/partial-publication failure, response loss, backend restart, malformed responses and late callbacks cannot produce optimistic success or automatic redispatch. Running/uncertain work cannot be abandoned through the local action. |
| Exact download | Compare delivered/downloaded bytes and decoded dimensions with each stored PNG, including a historical proposal different from Current collage. Reads neither render nor accept; binary/errors and object-URL cleanup work. |
| Model-free use | Selection, browsing, refresh and download work with live disabled and a model client that fails if invoked. Record zero Copilot model calls. |
| Regression | Preserve natural-language returns, task/navigation/name validation, CLI/replay acceptance, existing stage/correction budgets, project-list responsiveness, recovery, composer and image-loading UX. |

Add focused cases to existing agent/application/API/frontend test files where
the new behavior belongs; do not duplicate the whole agent capability suite.
Run targeted checks while developing, then the full existing offline Python
and API suites plus frontend tests, lint and build/type-check for the handoff:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\api\.venv\Scripts\python.exe -m pytest -q -c .\api\pytest.ini .\tests\api
npm --prefix .\web test -- --pool=threads --maxWorkers=1 --reporter=dot
npm --prefix .\web run lint
npm --prefix .\web run build
```

Also exercise the actual loopback Functions/UI connection with an isolated
offline-generated project containing real deterministic proposal PNGs.
Verify history/modal/selection/download and reopening after an owned backend
restart, rather than only mocked UI rendering or Demo. Do not expose a
test-only model injection/seed API. Use existing tools, with no new browser
test framework or global installations. Stop owned verification services
after the checks; do not manage the user's running servers.

Offline success is a handoff for the user's manual testing, not sign-off.
Any manual live conversations are user-directed and do not authorize Copilot
model calls. 018f closes only after the user accepts the resulting workflow.

## Implementation sequence, documentation and approval

1. Establish the minimal canonical local-selection/task-boundary mechanism
   and focused regression coverage, preserving ordinary CLI/replay behavior.
2. Add guarded application action persistence, pending-work retirement,
   timeline/read projection and thin HTTP routes; verify races and uncertainty.
3. Wire Current collage, lazy thumbnails, accessible modal, confirmation,
   source-action recovery and exact PNG downloads into the real workspace.
4. Complete offline suites and model-free loopback browser checks, update
   implemented-behavior docs, and hand over for manual testing.

Prefer existing dependencies; no new library, package upgrade, global tool or
Python-environment change was needed. The standing repository permission still
governs any separately necessary dependency work.

During implementation, update `architecture.md`, API/UI READMEs and the main
README's earlier future web-acceptance wording to describe the implemented
simpler workflow. Keep phase evidence and accounting in
[018f results](018f_results.md), not repeated in the index.
Discuss any new LESSONS entry separately.

The user explicitly authorized the implementation and offline verification on
2026-11-26. Initial implementation approval alone did not close the manual-review
gate; subsequent manual sign-off and the completed closeout are recorded above.
No Git writes, automatic next phase or Copilot model calls are included.
Preserve user staging/history/branches and pre-existing project/archive data.
