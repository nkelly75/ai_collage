# 018: Local conversation-and-preview experience

**Status:** Tentative umbrella tracker, approved for capturing direction only.
018a is complete and closed with the user's acceptance as a starting prototype;
see [018a results](018a_results.md). Later increments remain unapproved.
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
| 018b: Local Functions tooling and skeleton | Check backend prerequisites and establish a minimal locally running Functions host, without model calls. | Tentative; not specified. |
| 018c: Local project and history API | Expose local projects, photos, history, previews, and baseline selection. | Tentative; not specified. |
| 018d: Split conversational requests | Connect interpretation and layout generation through server-held validated intent. | Tentative; not specified. |
| 018e: Connected experience and human trial | Connect the UI and API, then assess the end-to-end experience. | Tentative; not specified. |

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
  them. No dependency installation is authorized by this tracker.
- Each subphase needs agreed scope, acceptance criteria, offline checks, and
  an explicit implementation approval before bounded Autopilot work. Stop at
  its handoff for review rather than automatically continuing to the next.
- Controlled responses support offline UI/API work. Real model calls and live
  trials need separate authorization and bounded service/retry allowances.
- Preserve originals, archived projects, evaluation evidence, and user staging.
  No Git writes are authorized by this tracker.

## Cross-cutting decisions and deferred work

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
