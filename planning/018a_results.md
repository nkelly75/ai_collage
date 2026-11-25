# 018a results: Frontend tooling and UI skeleton

**Status:** Complete and closed with the user's acceptance on 2026-11-25 as a
good-enough starting prototype. The [brief](018a-frontend-tooling-and-ui-skeleton.md)
and user-feedback revision are implemented and verified locally. This is
acceptance of the bounded frontend prototype, not production readiness or
approval to start 018b.

## Delivered

- One React + TypeScript + Vite application under `web`, using Bootstrap and
  React-Bootstrap. Node 24.22.3 is pinned in `web\.nvmrc`; dependencies and the
  npm lockfile are project-local. The current Vite template supplies Oxlint.
- Setup controls for 2-6 JPEG/PNG files, numbered browser-only thumbnails, and
  canvas shape. Validation reports invalid count/type/size or unreadable images.
- An explicit action opens the self-contained sample London workspace rather
  than pretending to render the selected files/settings.
- Conversation and active preview panels, a fixed three-message walkthrough,
  simulated interpretation/layout progress, clarification, and two proposals.
  Unsupported prompts get an explanation, not a fabricated model response.
- Thumbnail baseline selection retains later history. Acceptance is separately
  simulated; downloads return the displayed bundled PNG. Reset/refresh clears
  all state. Pending timers and local object URLs are cleaned up.
- Responsive layout, labelled controls, keyboard focus styling, progress
  announcements, and reduced-motion styling.

## Assets and isolation

Four small thumbnails were derived from the tracked numbered `photos` files.
Two 1200x1800 previews were rendered offline from
`examples\emma_tilted_2x3.json` in a temporary new project, with warm cream
(`#F4EEE4`) and charcoal (`#282A2E`) backgrounds and otherwise identical recipes.
Original-photo SHA-256 hashes were unchanged. No existing project directories
or trial stores were read or altered.

The browser uses only in-memory fixtures/state and bundled assets. No runtime
engine, API client/server, persistence, uploads, authentication, or model/cloud
calls were added. Vite's normal local development/HMR traffic is not an
application backend. Project dependency downloads were the only service access
used for implementation; no global tools or manager settings were changed.

## Initial verification

| Check | Result |
|---|---|
| `npm run build` | Passed; production output generated in ignored `web\dist`. |
| `npm run typecheck` | Passed with strict application and tooling TypeScript checks. |
| `npm run lint` | Passed. |
| `npm test` | 8 interaction tests passed: file validation/numbering/cleanup, decode-error feedback, sample isolation, stage/clarification progression, unsupported prompts, navigation versus acceptance, reset cancellation, and fresh remount. Tests block service calls and browser-storage reads/writes. |
| Local browser | Setup and scripted walkthrough exercised; warm/charcoal previews, clarification, older-baseline selection, and independent acceptance confirmed. Reload returned to empty demo state. |
| Layout/assets | Checked a 328px viewport and a 1366px same-origin iframe viewport; stacked/two-column layouts had no horizontal overflow. Sample images loaded; no observed application errors or failed resources. |
| Host | HTTP 200 from Vite on `127.0.0.1:5173`; listener confirmed loopback-only. |

No Python behavior changed, so no Python regression suite or paid replay was
run. User staging fingerprint remained unchanged during implementation.

## User handoff

The local preview is available at <http://127.0.0.1:5173/> while the dev server is
running. The Browser panel also opens this app. To restart from repository root:

```powershell
Set-Location web
npm run dev
```

See the [frontend README](../web/README.md) for setup/check commands and sample
limitations. This is a frontend-only prototype, not a functioning collage
service. Stop here for user review; Functions tooling, real APIs, model
integration, and all later increments remain unstarted and separately gated.

## Initial user feedback and frontend revision

The user found the first pass usable but asked for less decorative copy,
navigation organized around projects, custom pixel canvases, more chat space,
proposal thumbnails beside messages, and faithful numbered photo thumbnails.
The [brief amendment](018a-frontend-tooling-and-ui-skeleton.md#user-feedback-amendment)
records this separately authorized frontend-only follow-up.

The revision adds a Projects home (`/`), New project (`/new`) and individual
`/projects/<id>` paths, including browser back/forward and a useful missing-draft
message after refresh. Browser drafts retain their selected photos/canvas while
switching projects; the sample retains its conversation, baseline and acceptance.
Drafts show photo details rather than empty, unconnected chat/render panels.
They remain distinctly labelled, with no Python import or persistence claim.

Project IDs use the existing Python validation rules; seven portrait/square/
landscape presets and editable pixel fields use the existing 1-4096 integer
per-axis canvas contract. No layout version change or backend change was needed.
Project headings use only their IDs; proposal controls use P001/P002; photo
strips contain only numbered, uncropped, proportionally scaled original images.
Decorative headings, invented titles, repeated explanations and the footer were
removed. The conversation takes more desktop width and viewport height, with
compact proposal cards to the right of messages, also in narrow layouts.

No dependencies were added. Native History API routing remains frontend-local;
URLs do not make tab-only drafts durable. A shared photo library is deferred.
Original assets and previous evidence remain unchanged. The user's updated
staging was fingerprinted again before this pass and is preserved independently
of these working-tree edits.

### Revision verification

| Check | Result |
|---|---|
| Build, strict type-check, lint | All documented npm scripts passed; no lint warnings. |
| Interaction tests | 12 passed. Added draft creation/switching/resource lifetime, custom dimensions and presets, invalid/duplicate/reserved IDs, pixel boundary/fraction checks, history retention across pages, back/forward and missing deep-link coverage. |
| Desktop browser | At 1366x768, conversation/preview columns were approximately 835px/464px; proposal cards sat to the right of their messages and the complete active preview fitted. No horizontal document overflow or failed resources. |
| Narrow browser | At 328px, setup, the full sample conversation and a 2048x1024 browser draft were exercised without horizontal document overflow. Proposal cards remained beside messages. |
| Photo proportions | All four sample images were 210x280 and displayed at 72x96: the original 3:4 portrait shape, not cropped landscape tiles. Selected-file draft thumbnails had the same preserved ratio. |
| Navigation/isolation | Returning through Projects retained sample P001 baseline/P002 acceptance and the separate draft. A full navigation to the draft URL cleared tab state and explicitly reported the unavailable draft. No backend requests, persistence or real-store access. |

Temporary desktop-check iframes were removed. The loopback server and project
deep link returned HTTP 200; no Git writes or staging changes were made.
These checks alone did not establish sign-off; the subsequent user acceptance
is recorded below.

## User acceptance and closeout

On 2026-11-25 the user accepted the revised UI as a sufficient starting point,
explicitly recognizing that it is a prototype. This closes
018a with no remaining implementation work within its agreed scope.

Browser-only drafts, scripted responses and bundled previews remain intentional
limits. Backend integration, durable project loading, a shared photo library,
authentication and deployment are later work, not unfinished 018a requirements.
The SPA fallback requirement is recorded in the blueprint for deployment.

018b remains unstarted and requires separate scoping and approval. No Git
writes are authorized by this closeout; staging and commits remain user-managed.
