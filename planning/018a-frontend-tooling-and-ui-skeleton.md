# 018a: Frontend tooling and UI skeleton

**Status:** Complete and closed with the user's acceptance on 2026-11-25 as a
good-enough starting prototype, following implementation and the user-feedback
revision below; see [018a results](018a_results.md#user-acceptance-and-closeout).
This accepts the bounded frontend prototype, not production readiness or
permission to start 018b. The original agreed scope below is retained as the
implementation record. Prerequisite details remain in the
[tooling guide](018a_tooling.md).

## User-feedback amendment

The user's first UI review authorized another frontend-only pass: remove cute
copy and invented project captions/photo titles, use project IDs and photo
numbers, preserve thumbnail proportions, reclaim chat space, and place proposal
thumbnails to the right of their messages.

This supersedes the original two-view navigation/setup below: add a compact
Projects home, separate New project form, project-specific URLs, browser
back/forward, and switching between the sample and in-memory drafts. New drafts
use selected photos and canvas settings without pretending to import/render
through Python. Preserve draft photos and sample history when navigating;
reset/refresh still discards them. Report missing draft deep links explicitly.
Offer additional portrait/landscape presets and custom integer canvas dimensions
within the existing Python 1-4096-pixel-per-axis bounds. Project IDs follow the
existing Python rules.

A reusable photo library remains a possible later direction, not implemented
in this pass. No backend, persistence, real project-store access, new renderer,
new dependencies or 018b work is authorized by this revision.

## Outcome

Produce one rough, locally running React + TypeScript + Vite application for
user feedback, using self-contained mocked data and bundled preview images.
Follow the
[018 umbrella](018-local-conversation-and-preview.md) for the agreed UI direction.
This is a clickable frontend prototype, not a working collage application.
No Functions host, real API, model calls, authentication, or cloud storage.

## Scope and user journey

| Area | Behavior in this increment |
|---|---|
| Setup | Select 2-6 JPEG/PNG files, show import-order numbered thumbnails, and choose a canvas shape. Files stay in the browser; this does not create a real project or render a collage. |
| Enter workspace | An explicit "Open sample London project" action opens fixed sample photos, canvas, history, and previews. Explain that locally selected photos/settings are not used by the sample workspace. |
| Workspace | Conversation on the left, larger active preview on the right, prompt entry beneath the conversation. Show stable photo numbers, active proposal, and a persistent sample-data notice. Stack the panels sensibly in a narrow window. |
| Scripted conversation | Offer suggested prompts for a short fixed sequence: create a proposal, request an adjustment that triggers a clarification, answer it, and display another proposal. Simulate "Understanding your request" and "Creating your layout" as applicable. |
| Other typed prompts | Explain that only the sample sequence is supported. Do not invent a successful response or imply arbitrary language understanding. No keyword-based imitation of the real agent is needed. |
| Navigation | Proposal thumbnails appear with their messages. "Continue from here" changes the active baseline/preview while retaining later history. Do not imply it regenerated a collage. |
| Acceptance/download | Simulate explicit acceptance separately from baseline selection. A download control can download the displayed bundled image, clearly as a sample; no server save occurs. |
| Reset | Refresh or an explicit reset returns to initial demo state. No browser storage or persisted projects. |

This is one application with setup and workspace views, not separate demo
applications. Use clear labels and natural wording; the user need not understand
internal proposal IDs or the implementation of the scripted sequence.

Disable conflicting actions during simulated work and show useful feedback for
invalid file selection. Simulations must be bounded and clean up timers/object
URLs when reset or unmounted. Keep controls keyboard-accessible, label inputs,
give images useful alternative text, and announce progress without relying on
colour alone. No pixel-level design approval or polished visual editor is needed.

## Sample data and asset boundary

- Bundle fixed typed conversation/proposal fixtures and a small set of matching
  London photo thumbnails/previews under the frontend. They may take inspiration
  from earlier trials, but must not load or reference real project directories.
- Use copies of repository-supplied sample photos and suitable tracked previews.
  If matching previews need generating, use the existing offline engine with
  temporary synthetic project state and example recipes, then bundle the outputs.
  Do not inspect archived or live project stores to obtain fixtures.
- Keep original assets unchanged. No runtime engine import, backend connection,
  photo upload, cloud/model request, external image URL, CDN dependency, or
  telemetry. Serving bundled assets through the local Vite server is expected.
- Sample responses, selected baseline, simulated acceptance, and selected local
  files live only in browser memory. Do not use localStorage, IndexedDB, or a
  mock server that might be mistaken for production persistence.

## Implementation boundaries and dependencies

- Put the application in `web`, separate from the Python packages and tests.
  Use React + TypeScript + Vite with Bootstrap and React-Bootstrap, plus modest
  local CSS. Use React state rather than a state-management framework.
- Keep fixtures/scripted responses behind a small frontend-local module, not
  spread through presentation components. Do not prescribe future HTTP endpoint
  shapes or implement an unused production API client.
- Use project-local tooling: TypeScript, Vite's React integration and standard
  lint setup; Vitest, React Testing Library, jest-dom, and jsdom for focused
  interaction tests. No global frontend packages, router, icon framework, or
  additional component system is required for this slice.
- On implementation approval, scaffold with supported stable versions compatible
  with Node 24, record dependencies in `package.json`, retain the npm lockfile,
  and record/pin the verified Node version using the Windows manager's supported
  project mechanism. Use PowerShell and npm; do not alter global npm settings,
  PATH, execution policy, or either installed Node manager.
- Approval to implement this brief includes the necessary project-local package
  downloads from the normal npm registry, not toolchain/global installs or live
  application service calls. Stop for unexpected prerequisites or substantially
  different dependencies rather than expanding installation scope.
- Update ignore rules only as needed for frontend dependencies/build outputs.
  Add a short `web` README covering setup, scripts, sample behavior, and limits.
  Do not overhaul the root README or change Python/layout contracts.

## Verification and acceptance

| Check | Expected evidence |
|---|---|
| Build and static checks | Production build, TypeScript checking, and lint pass using documented project scripts. |
| Focused interaction tests | File-selection feedback/numbering; scripted clarification/proposal progression; unsupported-prompt feedback; baseline navigation preserving history; separate acceptance and reset behavior. Test observable behavior, not fixture constants. |
| Browser check | Setup and workspace load from the local dev server, the fixed walkthrough is usable, previews match bundled samples, and the narrow-window layout remains usable. Check for broken assets and console errors. |
| Isolation | No real project-store access or backend/model/cloud calls. Refresh clears state; local file choices are not misrepresented as inputs to canned previews. |

Use the smallest checks covering this frontend change. No Python regression
suite or paid replay is required unless implementation unexpectedly changes
Python behavior, which is outside the planned scope.

## Autopilot handoff and stop

After explicit approval, implement and verify only 018a. Hand off a local preview,
the PowerShell run commands, concise evidence/limitations, and an
`018a_results.md` record linked from the umbrella/index. If leaving a dev server
running for user review, bind it to loopback and report its actual URL.

Stop for the user's reaction to the rough UI. Passing automated checks is not
visual sign-off or approval to start 018b. Do not install Functions tooling,
Azurite, SWA tooling, Docker, or Aspire; do not create an API or connect a model.
Preserve original photos, archived projects, and user staging. No branch changes,
staging, commits, pushes, or other Git writes without explicit approval.
