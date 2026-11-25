# 018: Local conversation-and-preview experience

**Status:** Tentative umbrella tracker, approved for capturing direction only.
018a is complete and closed with the user's acceptance as a starting prototype;
see [018a results](018a_results.md). Separately authorized 018b is complete and
closed following the user's manual connectivity verification;
see [018b results](018b_results.md).
[018c](018c-persistent-project-flow.md) is complete and closed following the
user's manual testing and explicit sign-off; see [results and limits](018c_results.md).
Later increments remain unapproved.
The subphase boundaries and sequence below may change as we learn; they are
not a fixed delivery plan or authorization to implement all stages.

## Purpose and boundaries

Expose the existing engine and conversational capabilities through a usable
local web experience. Follow the [blueprint](001-project-blueprint.md) for
architectural direction and the [CLI guide](../docs/cli-guide.md) and
[layout field guide](../docs/layout-format.md) for existing behavior/contracts.

Use React + TypeScript + Vite, with thin local Python Azure Functions endpoints
over the existing application logic. Display backend-rendered previews rather
than build another renderer in the browser. Begin with local directories and
the fixed development-user identity; keep CLI and replay workflows useful.

Cloud deployment, end-user authentication, Blob implementation, vision, and
graphical layout editing are outside the initial local experience.

## Initial UI direction

- **Project setup:** Select photos, show their stable numbers, and choose the
  canvas shape.
- **Workspace:** Conversation on the left and a larger active preview on the
  right, with prompt entry beneath the conversation.
- **History and navigation:** Show messages, clarification questions, and
  proposal thumbnails inline. "Continue from here" selects an editing baseline
  without deleting later history or rolling back photo-name memory.
- **Actions and feedback:** Keep acceptance/download controls distinct from
  baseline selection, identify the active proposal, and show understanding
  versus layout-generation progress along with busy/error/recovery states.

This is enough shared design direction to produce a rough version for user
feedback; no pixel-level design exercise is required. Styling/component tooling
is open: Bootstrap is acceptable, as is a suitable React alternative. Choose a
simple approach when specifying the skeleton, not a separate design-system
project.

## Tentative subphases

| Increment | Intended outcome | Status |
|---|---|---|
| [018a: Frontend tooling and UI skeleton](018a-frontend-tooling-and-ui-skeleton.md) | Build the rough workspace with self-contained sample conversation and previews, without a backend or Functions tooling. | Complete and closed with user acceptance as a starting prototype; [results](018a_results.md). |
| [018b: Local Functions tooling and connectivity](018b-local-functions-tooling-and-skeleton.md) | Inventory prerequisites, hand over user-run setup, then prove a placeholder Function can be called from the web prototype. | Complete and closed following user verification; [results and limits](018b_results.md). |
| [018c: Persistent project flow](018c-persistent-project-flow.md) | Connect UI project creation, listing and reopening to local persistence for selected photos and canvas settings, without model calls. | Complete and closed following manual testing and user sign-off; [results and limits](018c_results.md). |
| 018d: Saved history and local actions | Connect saved conversation/proposal history, backend previews/downloads, baseline selection and explicit acceptance, without generating new proposals. | Tentative; not specified. |
| 018e: Split conversational requests | Connect interpretation/clarification and layout generation through server-held validated intent, with visible progress and recovery. | Tentative; not specified. |
| 018f: End-to-end trial and refinement | Assess the complete create/resume/converse/preview/accept flow and address observed issues. | Tentative; not specified. |

Each increment includes its usable UI/API connection rather than postponing
all UI wiring to a final integration phase. The placement of history/local
actions remains revisable when the next increment is separately specified.

Only detail the next increment when ready. Add stable links to its brief and
results as they are created; do not create placeholder briefs for later stages.

## Tooling and execution gates

- Start with a read-only inventory of local tooling. Provide the user with
  installation instructions for missing prerequisites such as Node.js/npm;
  do not install toolchains or global tools without explicit approval.
- Scope tooling checks to the current increment: 018a needs only the frontend
  toolchain. Defer Azure Functions Core Tools and other Functions-specific
  setup until 018b; neither Functions nor Azurite blocks the first UI review.
- Select and document project dependencies in the next brief before installing
  them. Small task-related UI changes follow the standing
  [repository dependency permission](../.github/copilot-instructions.md);
  other installations require explicit approval.
- Each subphase needs agreed scope, acceptance criteria, offline checks, and
  an explicit implementation approval before bounded Autopilot work. Stop at
  its handoff for review rather than automatically continuing to the next.
- Controlled responses support offline UI/API work. Real model calls and live
  trials need separate authorization and bounded service/retry allowances.
- Preserve originals, archived projects, evaluation evidence, and user staging.
  No Git writes are authorized by this tracker.

## Cross-cutting decisions and deferred work

**Retire the connectivity scaffold:** As real Functions are wired into the UI,
remove the temporary **Check backend** control and diagnostic-only wiring/tests
once real requests provide connection/error feedback. Keep `/api/health` only
if there is a deliberate ongoing health-check need, not as leftover demo plumbing.

The split API must keep validated intent on the server, reject stale prepared
operations and duplicate execution, and bound each stage below the hosting HTTP
limit. Reject overlapping project mutations on the backend, including requests
from different tabs; collaborative editing and conflict-resolution UX are not
requirements. Detailed mechanics belong in the relevant subphase brief.

**Persistence follow-up remains explicit:** Local-directory support is not
cloud readiness. Before shared deployment, implement and verify private
Blob-backed persistence, safe publication, revision checks, and a cross-instance
project mutation guard while retaining local-directory CLI/replay operation.
Review existing filesystem assumptions during API planning, but limit initial
storage changes to what the local slice needs. Reconsider Azurite when working
on the Blob path, not as a prerequisite for the skeleton.

Authentication/ownership isolation, deployment automation and operational cost
controls remain gates before sharing the app. Their detailed design, and any
vision or graphical-editing work, will be scoped separately.
