# Collage studio: local project flow

React + TypeScript + Vite, styled with Bootstrap/React-Bootstrap. Create, list
and reopen photo/canvas projects through the local Python API. Conversation and
collage generation are **not connected yet**. A separate scripted London demo
works without the backend; its proposals/acceptance remain simulated.

## Run in PowerShell

Use Node **24.22.3** (pinned in `.nvmrc`, supported by nvm-windows) and its bundled
npm. From the repository root:

```powershell
Set-Location web
npm ci
npm run dev
```

`npm ci` downloads locked dependencies; skip it when already installed and the
lockfile is unchanged. No global frontend packages are needed.
Start the [local Python API](../api/README.md) in a separate terminal.
Vite binds **127.0.0.1:5173**, refusing an occupied port instead of silently
choosing another. Stop each server with Ctrl+C.

```powershell
npm test
npm run lint
npm run build
```

Build includes TypeScript checking, then bundles into `dist`.
Tests/lint are separate. `npm run dev` serves source with live updates;
`npm run preview` serves the production build on loopback for inspection,
not as a production server.

## What to try

1. **Projects** (`/`) loads saved IDs, photo counts and canvas dimensions from
   Python. Loading, empty and failed states are distinct; failures offer manual
   retry. **London demo** remains separate and available when the API fails.
2. **New project** (`/new`): enter a unique ID, select 2-6 JPEG/PNG photos
   (25 MiB each maximum), and choose one of seven presets or integer custom
   dimensions of 1-4096 pixels per side. IDs match Python's lowercase/digit/hyphen
   rules, including reserved Windows-name rejection. Numbered previews retain
   photo proportions. Nothing is uploaded until **Create project**.
3. Creation disables changes/duplicate submission while pending, then navigates
   only after confirmed persistence. Files/settings remain selected on failure
   while setup stays open. Duplicates and uncertain outcomes offer an explicit
   saved-project lookup. A timeout/lost response does not prove rollback:
   check the saved ID before retrying. No automatic POST retries or offline
   success are fabricated.
4. **Saved project** (`/projects/<id>`) independently reloads photos/settings on
   refresh/direct visits, including after backend restart. Default data is in
   `.collage-data-web`, separate from CLI stores. Missing/invalid state and
   photo-load failures are visible. No photo/canvas editing, delete/rename,
   chat, generation, acceptance or download controls are enabled here.
5. **Demo** (`/demo`) uses its own four photos/1200x1800 canvas, even when a real
   project is named `sample-london`. Use suggested messages for first proposal,
   clarification and second proposal; other prompts fail explicitly. Baseline
   selection retains later history; acceptance is separate, and PNG download
   uses bundled assets. **Reset demo** affects only this simulation, never saved
   projects. Demo state resets on refresh.

There is no browser storage or draft autosave. Leaving setup releases temporary
photo URLs and cancels pending requests; server completion after navigation is
still possible. Leaving/refreshing may discard unsaved choices, not saved data.

## API configuration

The default base is `http://127.0.0.1:7071`; direct requests append `api/projects`
and its detail/photo routes. Set `$env:VITE_API_BASE_URL` before starting Vite
or building to change it, then restart Vite. Values must be absolute HTTP(S)
URLs without credentials. API addresses are public configuration, never secrets.
There is no Vite proxy, credentialed fetch or redirect following.

JSON reads are bounded to 10 seconds, creation to 60 seconds, including response
body handling. Non-JSON host errors and malformed success responses are errors,
not empty lists or saved-project success. Connection errors can mean a stopped
host, incorrect API address or mismatched exact CORS origin. Match alternate
loopback ports using the [API launcher options](../api/README.md).

## Testing and responsive layout

Vitest/Testing Library/jsdom cover real API shapes, setup/create/recovery,
navigation, stale-response cancellation and demo behavior. API-client cases
cover deadlines including response parsing, aborts, malformed DTOs, host errors
and no automatic create retries. Tests block unmocked fetch/XHR/WebSocket and
browser storage. These are not real browser layout checks; separate local
browser evidence is recorded in phase results, not a checked-in end-to-end suite.

Desktop demo conversation/preview are side by side; below 992px they stack and
setup becomes one column. Below 576px navigation wraps. Numbered photo strips
scroll horizontally without cropping. Narrow viewports are not physical-phone
certification.

## Hosting and sample assets

A future static host serves `dist`, not Vite; React needs no permanent Node
server. Project URLs require an SPA fallback to `index.html`, then React loads
the saved project through the API. Azure Static Web Apps with separate Python
Functions remains a candidate; deployment, authentication and private Blob
persistence are deferred.

`public\demo` contains metadata-free thumbnails of the four repository photos
and two offline-generated fixed PNGs based on `examples\emma_tilted_2x3.json`:
cream (`#F4EEE4`) and charcoal (`#282A2E`) with identical photo geometry/style.
Original photos and pre-existing stores are untouched.
`src\demo.ts`/`useDemo.ts` contain the isolated script and cancellable timers.
Native History API navigation needs no router package.
The UI has no language parser, second renderer or shared photo library.
Assets/fonts/dependencies are served locally, without external telemetry or
model requests.
