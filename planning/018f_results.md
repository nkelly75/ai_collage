# 018f results: Current collage, history and download

**Status:** Successfully completed and closed on 2026-11-26 with the user's
manual sign-off and requested Demo retirement. Final smoke testing and commit
remain user-managed. No Copilot model calls were made; earlier live allowances
remain closed. 018g remains separate and unapproved.

Scope and stop rules: [018f brief](018f-current-collage-history-and-download.md).
On 2026-11-26 the user authorized: "Go ahead with the scope agreed in
planning/018f-current-collage-history-and-download.md Stick to the guardrails."

## Implemented slice

| Area | Outcome |
|---|---|
| Workspace | **Current collage** identifies the saved editing baseline and explains that edits start there. It retains the existing loading/reload behavior and can be older than the latest generated result. |
| Historical viewing | Lazy inline thumbnails open a separate accessible modal with the exact stored proposal, dimensions, download and **Edit from this collage**. Viewing/closing is transient; redundant current selection is disabled unless pending work needs ending. |
| Local selection | Public deterministic `Conversation.select_proposal()` appends a distinct version-1 `local_selection` event and keeps baseline, task/navigation and naming-history invariants consistent. No fake model response, proposal, request reservation or accepted snapshot. |
| Application/API | UUID-bound, revision-checked local actions use the existing OS-held project guard. Additive version-1 `web-selections` records reference canonical events and any retired preparation. New selection POST/status GET routes use the existing HTTP boundaries and threaded dispatcher. |
| Pending work | Explicit confirmation ends a pending question/name receipt or valid never-claimed preparation. Original names/history/accounting stay saved; retired preparation becomes terminal `abandoned`, so an old generation POST cannot dispatch it. Running/interrupted/uncertain work stays blocked. |
| Activity/recovery | Saved choices project distinct chronologically ordered user activity. Identical duplicates return the original outcome without reselecting. Partial claims fail closed; lost responses are reconciled by original-action/status reads, not another POST. |
| Download | Historical and current actions fetch the exact verified full-resolution PNG through the existing preview route, use a safe project/proposal filename and release temporary browser object URLs. No rendering, resizing, selection or acceptance. |

No web acceptance/finalization, engine/layout contract change, second renderer,
queue, cancellation of running work, migration, agent-prompt tuning or new
dependency was introduced. Existing CLI/replay acceptance and ordinary
natural-language returns remain intact. Usage guides and the implemented
architecture map were updated; no new LESSONS entry was added.

## Offline verification

| Gate | Actual outcome |
|---|---|
| Focused application suite | **26 passed** against the final implementation, including the reproduced read-race regression. |
| Root suite | **687 passed** against the final implementation. Initial run: 684 passed, 2 naming-wording failures; the naming-fix rerun passed all 686 cases before the final snapshot-coherence fix and added regression case. |
| Separate API suite | **74 passed** against the final snapshot-coherence implementation. |
| Frontend | 76 passed; clean lint and successful build/type-check. |
| Real loopback browser and restart | Historical/current PNGs, repeatable source choices, saved activity, no browsing mutation, fresh-backend reopen, current-modal/Escape/focus behavior and preservation checks passed with live disabled. |

Application coverage includes next-edit source, name/question/preparation
abandonment, stale confirmation, duplicate/conflicting identities, a
generation/selection guard race, invalid targets, interrupted claims,
retirement/state/completion failure windows, preserved PNG/history/names and
CLI acceptance after local selection. A focused read-race case verifies that
a choice completing after snapshot capture cannot add newer activity to that
older baseline/revision. HTTP coverage includes disabled-live
selection, strict bodies, status/idempotency, retirement and exact PNG delivery.
UI/client cases cover temporary viewing/focus, three confirmation types,
visible rejection, unknown outcome/read-only recovery, viewing/downloading
during uncertainty, binary errors and filename/object-URL cleanup.

The first frontend gate exposed unexpected extra action GETs in four new-test
mocks, a blob mock typing error and a state-setting modal effect. Normal
success now uses the confirmed POST outcome; unknown recovery still reads the
original action. A stable success callback closes the modal, and the blob
mock's parameter typing was corrected. The final frontend gate is
green. The root naming failures above were a diagnostic-wording regression,
not a relaxation of interrupted-write protection; preserved evidence still
blocks further dispatch.

Final implementation review reproduced a snapshot-projection race: the
transcript reread local actions after capturing the canonical snapshot, so a
concurrent choice could add newer activity to an older baseline/revision.
The private snapshot now returns its validated action records alongside
conversation/operations/revision; projection uses that same set. A focused
case failed before this surgical fix and passes in the final application and
full root suites. No DTO or persisted contract changed.

## Actual model-free browser evidence

An isolated `offline-history` project used two generated test photos and three
real deterministic proposals at **1200x1800**, seeded through existing
application operations with controlled model clients. There was no test-only
HTTP seed route, provider access or real-image trial.

Owned Functions on loopback port 7088 and Vite on 5188 served the real UI/API
with live disabled. Browser actions opened historical P001 while Current
collage stayed P003, downloaded it, selected P001, then selected P003 again.
Exactly two selection POSTs and no generation POST were observed. Both choices
closed the modal on confirmed success and retained correctly ordered activity.
The initial backend projection was unchanged by historical browsing/download.

| Download | Exact bytes | SHA-256 |
|---|---:|---|
| `offline-history-P001.png` | 37,028 | `024a63cda0f110e274d53929c719043f93f2ed594546f2af343417bb687a4b09` |
| `offline-history-P003.png` | 38,791 | `326febaeedb11cab5251614f5eaaea3a1bba5da2c93d9ee7b77712077a474d9d` |

Both delivered blobs were PNGs and matched the seed's stored proposal hashes.
Browser images decoded at the actual 1200x1800 dimensions. The narrow Browser
panel was exercised; a same-origin 1280x900 app iframe additionally confirmed
the two-column layout and unchanged rendered aspect ratio.

After a fresh owned Functions process started against the same isolated root,
the entire backend projection matched the pre-restart projection. A fresh
browser reopen showed Current P003, both saved activities and no open modal
or mutation redispatch. Opening the current thumbnail showed the original
dimensions and disabled redundant selection; Escape restored thumbnail focus.
Generated source hashes, all proposal PNG hashes, original message entries and
the three original operation records were preserved. Accepted version stayed
null. Removing only the two local history events from the read-only
verification object reproduced the seed's original snapshot digest, including
the original canonical state, proposal metadata and operation accounting.

Evidence remains in this session's
`files\018f-evidence\offline-workflow`: seed manifest, before/after restart
projections and `browser-checks.json`; seed/verification helpers are alongside
that directory. Owned verification services were stopped and ports 7088/5188
were confirmed released. Core Tools/Vite left children after their launcher
stops; only the identified owned PIDs were cleaned up. No other services were
stopped.

## Manual-feedback UI refinements

On 2026-11-26 the user reported that `project-02` was working quite well,
including the historical modal. Feedback identified unclear right-panel
feedback after generation completed and an overly prominent modal explanation.
Preview speed was explicitly acceptable; performance work was not added.

Two presentation changes were applied:

- A confirmed result awaiting its conversation refresh now dims the old
  Current collage with **Updating current collage...**. The incoming image
  retains that prominent overlay style with **Loading preview P...** until
  its actual load event. Failed refresh/image reads stop the updating
  feedback and expose existing Check status/Reload preview recovery.
- The general modal-body sentence was removed. Smaller helper text directly
  beneath and accessibly associated with **Edit from this collage** explains
  its effect; **Already current** has no such helper. Viewing/downloading
  remain transient/read-only.

The frontend gate passed **81 tests**, clean lint and build/type-check.
Five added cases cover current-action helper hiding, delayed post-generation
refresh through image load/error/reload, the first-collage handoff and failed
refresh/read-only recovery. Existing historical-view coverage now checks the
button's accessible description. Python/API code, persistence, preview fetch
policy, model budgets and dependencies were unchanged; their earlier
687/74-case baselines were not rerun for these UI-only changes.

The real isolated UI/API also verified the modal helper below its button at
12px versus the button's 16px. Browser-only controlled operation responses
simulated the completed-stage handoff without dispatching generation: the
overlay covered the preview stage and retained the already decoded P003
under its translucent background. Reload restored the real saved P003 with
no controlled messages or modal. Original snapshot/source/PNG preservation
checks passed again; no live access or real model calls. Evidence:
`files\018f-evidence\ui-feedback-checks.json`.

The user had staged the initial implementation before this follow-up. That
new staging was preserved unchanged at
`1738d0da3597f18ad1764a32d0e38d0dbcc00738`; no Git writes were made.
At that handoff, the refinements awaited the user's review and did not close
the phase.

### Modal alignment and viewport follow-up

The user confirmed that the new spinner overlay looked great, then identified
unequal modal button alignment and outer-page scrolling to reach Send/photo
labels. Both modal actions now use the same small button size. The desktop
grid no longer forces a 460px minimum into a smaller available viewport; its
row is explicitly bounded and the preview can shrink around its controls.
Very short desktop windows retain page scrolling instead of clipping
controls; narrow layouts remain stacked. Overlay behavior is unchanged.

Read-only browser verification reproduced a 598px document in a 1280x500
viewport before the sizing change; afterward the document was exactly 500px,
with Send and photo labels visible. Five desktop sizes from 1024x768 to
1440x900, including 1280x600/500, passed viewport-bound checks and preserved
the preview aspect ratio. A 1280x400 fallback kept controls reachable by page
scrolling. Tablet/phone layouts stayed free of horizontal page overflow.
Controlled DOM-only stress with six photo tiles and a longer transcript
confirmed that scrolling remains inside the appropriate regions. The
scripted demo also fit its 1440x900 viewport with a loaded proposal.

Historical/current modal actions had identical top positions and 30.2px
heights. The history helper remained below its button (12px text versus the
button's 14px), and was absent for Already current. The frontend's 81 cases,
lint and build/type-check passed; no backend or model behavior changed.
Evidence: `files\018f-evidence\modal-viewport-checks.json`.

The user had staged the preceding refinements. The current follow-up preserved
that staging at `e1e35333471d3b4161083f38ba790be3c91dad1b`, without Git writes.
Saved fixture state/source/PNG checks passed again. Owned verification services
were stopped; no user project or server was changed. At that handoff, 018f
remained open for manual review.

## Demo retirement and phase closeout

The user accepted the workflow: **"018f looks good to me."** Their final
request authorized removing the original fixed-message Demo and closing the
phase after that cleanup, with one more user-managed test before committing.

Removed the Demo navigation/list entry, `/demo` implementation, mock
`Workspace.tsx`, `demo.ts`, `useDemo.ts`, frontend sample-project definition
and discriminator, six Demo-only copied images, and their dedicated styling.
Shared photo strips, real workspace/modal/composer styling and responsive
rules remain. The shared local-storage notice now has a non-sample class
name. Backend data/contracts, source photos, archived evidence and package
dependencies were untouched. The fresh production build contains no Demo
assets; `/demo` uses the ordinary not-found page with no API request or
compatibility alias. Real project IDs, including `sample-london`, remain valid.

The final frontend gate passed **80 cases**, lint and build/type-check.
Four obsolete scripted-demo cases were removed and three focused
route/real-workspace/navigation regressions added; real conversation, history,
selection and download coverage remains. The prior Python/API baselines above
were not rerun for this frontend-only retirement.

Model-disabled loopback browser checks confirmed only Projects/New project
navigation, saved P003 at 1200x1800, numbered photos and the unchanged
desktop/mobile layout. Historical P001 still opened without changing Current
P003; modal buttons remained aligned. The actual download handler returned
the same 37,028-byte P001 PNG and filename and released its object URL.
Only the final save-click was intercepted for inspection. Saved
snapshot/source/PNG preservation checks passed again. Evidence:
`files\018f-evidence\demo-retirement-checks.json`.

User staging remained at `15f0584a7b28d72f04120a05e528b50deb6c6670`.
No Git writes, model calls, user-project changes or new installations.
Owned verification services were stopped. This completes the user-approved
closeout; 018f is closed, not a general quality certification or authorization
for 018g. The user's final smoke test and commit are not performed by Copilot.

## Guardrails and manual-review gate

**Zero external/Copilot model calls.** Test/model responses were controlled;
the browser host never enabled live access. No Foundry experiment, credential
preflight, dependency installation, Git write or user-project mutation.
Verification used generated photos and an isolated data root, not
`.collage-data-web`, user CLI roots, original photos or archived trial data.
At the initial handoff, the user's staging fingerprint was unchanged:
`b507d8b417baa34a9f42719f6651bf48bebfc7ca`.

At the initial handoff, manual review was required before phase closure:
inspect an older thumbnail without switching, choose it and then another
saved collage, check activity/current-source explanations, download at the
agreed dimensions and check pending-work confirmation where relevant.
The subsequent user acceptance and closeout above satisfy that phase gate.
Any future live human trial remains the user's explicitly chosen activity,
not a renewed Copilot allowance.

Offline evidence alone does not establish real-photo/model quality or user
acceptance. The recorded user sign-off closes this bounded phase; 018g and
further features/model calls still require separate approval.
