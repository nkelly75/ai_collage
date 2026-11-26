# Collage studio: local conversation and previews

React + TypeScript + Vite, styled with Bootstrap/React-Bootstrap. Create, list
and reopen photo/canvas projects through the local Python API. Saved projects
have a real conversation and immutable, backend-rendered previews. A separate
scripted London demo works without the backend; its proposals/acceptance remain
simulated.

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
Start the [local Python API](../api/README.md) in a separate terminal. Browsing
and creation need no model access. Live conversation requires the explicit
backend opt-in `.\api\start.ps1 -Live` (from the repository root) and separately
configured Python credentials; never put provider credentials in Vite settings.
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
   photo-load failures are visible. With live requests enabled, describe a
   layout using numbered photos or saved names, then **Send**. The UI shows
   **Understanding your request**, then the saved action/source/photo summary
   and **Creating your layout** when generation is needed. The old preview
   stays visible until a saved baseline is confirmed. Questions and photo-name
   confirmations take ordinary text answers; acknowledgements and exact returns
   to earlier proposals do not invent a generation stage. The composer placeholder
   reflects a pending question or name confirmation. **Enter** sends;
   **Shift+Enter** inserts a newline (IME composition does not submit).
   Answered-question prompts and **Continue generation** are hidden while this
   tab processes its answer or automatically generates. A new baseline shows
   **Loading preview P...** until its image has actually loaded. There are no
   photo/canvas editing, delete/rename, proposal-navigation, acceptance or
   download controls in the real workspace.
5. **Demo** (`/demo`) uses its own four photos/1200x1800 canvas, even when a real
   project is named `sample-london`. Use suggested messages for first proposal,
   clarification and second proposal; other prompts fail explicitly. Baseline
   selection retains later history; acceptance is separate, and PNG download
   uses bundled assets. **Reset demo** affects only this simulation, never saved
   projects. Demo state resets on refresh.

There is no browser storage or draft autosave. Leaving setup releases temporary
photo URLs and cancels pending requests; server completion after navigation is
still possible. Leaving/refreshing may discard unsaved choices, not saved data.

## Conversation recovery

Opening/reloading reads the saved transcript, current editing baseline, pending
question/confirmation and operation status. It never makes a model request.
Prepared work found on reload requires **Continue generation**; only the
still-active original Send automatically continues its own prepared response.
One submission has one UUID, generated before Send, and at most one automatic
generation POST. Competing sends stay disabled while work is unresolved.

Confirmed `stage_failed`/`stage_timeout` responses automatically reread the
original operation and saved conversation using GETs only. Once consistent
terminal state is loaded, the composer is restored without retrying the stage.
A failed refresh retains the confirmed failure, not an unknown-outcome warning,
and offers **Check status**. Conflicting saved state stays blocked.

On a lost/malformed response or unconfirmed timeout, **Check status** reads the
original operation and saved conversation. Do not resend the prompt to discover
whether it completed. Only confirmed terminal results restore the composer;
an unknown/interrupted claim or missing request stays blocked for inspection.
A lost interpretation response reconciled to prepared work still requires
explicit **Continue generation**. A confirmed failure remains in the transcript;
sending a new prompt is a new, potentially paid attempt.

At idle, a refresh icon beside the **Conversation** title rereads saved state,
including changes made in another tab. Its tooltip/accessibility label is
**Refresh saved conversation and preview**. The heading stays outside the
scrolling transcript; the icon is disabled or hidden during this tab's request.
Recovery instead offers an explicit **Check status** button beside its message,
with an explanation that it makes no model calls.
If a completed response was received but refreshing the transcript fails, the
UI preserves that confirmed result and explains that the saved conversation
still needs refreshing, rather than calling the mutation outcome unknown.
Successful recovery of the original request is explicitly acknowledged.

Running work is observed with non-overlapping GETs, two seconds apart, for at
most 225 seconds per observation session. Connectivity failure, uncertainty or
completion stops automatic checks; **Check status** starts a fresh observation
session when appropriate. Navigation cancels browser listeners/timers and
ignores stale callbacks, not backend work. Missing/failed preview images are
shown as errors, not an empty project or a fabricated successful result.

## API configuration

The default base is `http://127.0.0.1:7071`; direct requests append `api/projects`
and its detail/photo/conversation/preview routes. Set `$env:VITE_API_BASE_URL` before starting Vite
or building to change it, then restart Vite. Values must be absolute HTTP(S)
URLs without credentials. API addresses are public configuration, never secrets.
There is no Vite proxy, credentialed fetch or redirect following.

JSON reads are bounded to 10 seconds, creation to 60 seconds, interpretation
POSTs to 160 seconds and generation POSTs to 220 seconds, including response
body parsing. These are browser deadlines, not promises of model cancellation.
The split JSON POST client sends only prompt/request identity/revision, or a
saved generation revision; strict DTO parsing rejects malformed responses.
Interpretation accepts only 201/new or 200/duplicate operation responses;
generation and reads require 200. No POST is automatically retried.
Non-JSON host errors and malformed success responses are errors,
not empty lists or saved-project success. Connection errors can mean a stopped
host, incorrect API address or mismatched exact CORS origin. Match alternate
loopback ports using the [API launcher options](../api/README.md).

## Testing and responsive layout

Vitest/Testing Library/jsdom cover real API shapes, setup/create/recovery,
navigation, real stage sequencing, non-generation results, restored Continue,
lost-response/timeout recovery, bounded polling, preview errors, stale-response
cancellation and demo behavior. API-client cases cover deadlines including
response parsing, aborts, strict DTOs, host errors and no automatic POST retries.
Workspace cases also cover contextual question/name placeholders, Enter versus
Shift+Enter/composition, preview loading/reload and confirmed-result refresh
timeouts. If fork workers fail to start on a busy local machine, the same suite
can run with `npm test -- --pool=threads --maxWorkers=1`.
Tests block unmocked fetch/XHR/WebSocket and
browser storage. These are not real browser layout checks; separate local
browser evidence is recorded in phase results, not a checked-in end-to-end suite.

Desktop real/demo conversation/preview are side by side; below 992px they stack and
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
Assets/fonts/dependencies are served locally, without external telemetry.
Model requests occur only through the explicitly live-enabled Python backend,
never through a browser provider client.
