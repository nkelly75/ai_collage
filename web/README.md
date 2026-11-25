# Collage studio: local web prototype

A local React + TypeScript + Vite app, styled with Bootstrap/React-Bootstrap.
Projects and conversation remain **browser-only, with no AI connection**.
An optional manual check can call the local Python health Function.
All interactions reset on refresh.

## Run in PowerShell

Use Node **24.22.3** (pinned in `.nvmrc`, supported by nvm-windows) and its bundled
npm. From the repository root:

```powershell
Set-Location web
npm ci
npm run dev
```

`npm ci` downloads the locked project dependencies; skip it when they are already
installed and the lockfile has not changed. Vite binds to **127.0.0.1:5173** and
refuses an occupied port instead of silently choosing another. Stop it with
Ctrl+C. No global frontend packages or cloud credentials are needed. Functions
tools are required only for the optional backend check.

```powershell
npm run build
npm run typecheck
npm run lint
npm test
```

`npm run build` checks TypeScript, then bundles optimized HTML, JavaScript,
CSS and assets into `dist`. `npm run dev` serves source with live updates;
`npm run preview` serves the production build on loopback for inspection,
not as a production server.

## Optional backend check

Start the [local Python Function](../api/README.md) in a separate terminal, then
click **Check backend** in the prototype notice. It directly requests
`http://127.0.0.1:7071/api/health`, requiring HTTP 200 and JSON with `status: "ok"`.
It shows checking, success or failure, with a five-second timeout covering the
response body too. There are no automatic checks, retries or mock successes.
The sample and drafts still work when the host is stopped.

To change the API base address, set `$env:VITE_API_BASE_URL = 'http://127.0.0.1:7071'`
before starting Vite (or building for deployment); the app appends `/api/health`.
Restart Vite after changing configuration. Invalid configuration is reported,
not replaced with another address. Requests do not use a Vite proxy, credentials
or redirects. Browser connection failures can mean a stopped host, incorrect
address or mismatched CORS origin.

## Testing

`npm test` uses Vitest (runner/assertions), React Testing Library (component
interactions), and jsdom (a simulated DOM in Node). These cover behavior such as
validation, navigation and state changes, not real browser layout. They
complement rather than replace Playwright/Selenium browser tests. The browser
checks recorded in the results are separate, not a checked-in end-to-end suite.
Tests and lint are **not run by `npm run build`**; a deployment pipeline should
run `npm test`, `npm run lint` and `npm run build` before publishing.

## Responsive layout

Desktop shows conversation and main preview side by side. Below 992px they
stack, conversation first; setup becomes one column. Below 576px navigation
wraps and spacing/proposal cards shrink. Small proposal thumbnails remain
beside messages; photo strips scroll horizontally without cropping images.
Narrow browser viewports were checked, not physical phones.

## What to try

1. The home page (`/`) lists the bundled `sample-london` project and browser
   drafts created in this tab. Project pages use `/projects/<project-id>`.
   Normal navigation and browser back/forward retain this tab's project state.
2. **New project** (`/new`) lets you enter a project ID, select 2-6 JPEG/PNG files
   and choose a canvas preset or custom dimensions. IDs follow the Python rules
   in `engine.models.validate_project_id`; dimensions are integer **1-4096
   pixels per side**, matching `Canvas`. Selecting/editing presets updates the
   actual pixel fields. Photo thumbnails keep the original proportions and
   display only import-order numbers, not invented titles.
3. **Create browser draft** adds an in-memory project with those photos and
   dimensions. It does not import photos into Python, render a collage or
   enable chat. Drafts have their own URLs and remain available from Projects
   until reset/refresh. No shared photo library is implemented.
4. Open **sample-london** for the separate scripted conversation. Click a
   suggested message, then **Send**. Follow the first proposal, clarification,
   and second proposal. Other prompts receive an explicit unsupported-message
   notice. The sample always uses its own four photos and 1200x1800 canvas.
5. Proposal thumbnails sit beside messages. **Use P001/P002** changes the active
   baseline while retaining later history. **Accept proposal** is separately
   simulated. **Download PNG** downloads the displayed bundled sample image.
6. **Reset prototype** clears all drafts/history, cancels simulated work and
   releases local photo-preview URLs. Refresh also clears state; a sample deep
   link starts fresh, while a vanished draft URL explains that it is unavailable.
   There is no browser storage or project-store persistence.

## Hosting notes

Deploy the contents of `dist` to a static host, not the Vite development server.
React runs in the browser; this frontend needs no permanent Node server.
Azure Static Web Apps is a candidate, with separate Python Functions called
through a configurable API address, restricted CORS and authentication.
This keeps long API requests outside SWA's shorter integrated proxy limit.
Vite environment values are normally public, build-time configuration: API
addresses are suitable; credentials are not.

Project URLs need an **SPA fallback to `index.html`** so direct visits and
refreshes load React, which then handles the route. This does not make browser
drafts persistent. The [blueprint hosting section](../planning/001-project-blueprint.md#target-serverless-direction)
records the deployment requirement; hosting configuration is still deferred.

## Sample assets and boundaries

`public\demo` contains metadata-free thumbnails derived from the four numbered
repository photos and two fixed 1200x1800 PNGs. The previews were generated
offline using the existing engine in a temporary new project, based on
`examples\emma_tilted_2x3.json`: warm cream (`#F4EEE4`) and charcoal (`#282A2E`)
backgrounds, with identical photo geometry/style. No pre-existing project
directory was read or changed. Source photos remain unchanged.

`src\demo.ts` holds the fixtures/scripted responses; `useDemo.ts` manages their
in-memory progression and cancellable timers. The app session owns browser
drafts/photo URLs so navigation does not discard them; abandoned setup selections
are released on leaving setup. Native History API navigation needs no router
package. This is not a production API
contract, language parser, second renderer, or persistence layer.
Dependencies and assets are served locally, with no external fonts, images or
telemetry. The only runtime service request is the explicitly triggered health
check; project/photo/model traffic is not implemented. Tests block unmocked
fetch/XHR/WebSocket and browser-storage access while exercising interactions.

