# AI Collage Builder

Build photo collages from explicit, editable layouts. The goal is
to describe a layout in natural language and refine it conversationally, while
keeping geometry, validation, and rendering deterministic.

**Available today:** a local Python CLI that imports JPEG/PNG photos, renders
JSON layouts to PNG, and keeps accepted layout versions. Preserve whole photos,
or opt into fixed rectangular frames with crop-to-fill, pan, and 1x-4x zoom.
Both modes avoid stretching and support different canvas aspect ratios, solid
backgrounds, optional outside photo borders, and overlapping images with
explicit stacking. Optional rounded corners work with or without borders.
Centre-based tilt supports -10 to +10 degrees, with the entire rotated frame
required to fit on the canvas. A full-canvas image layer can serve as a photo
background. Captions are not implemented yet.

The deterministic engine runs offline without credentials or model calls.
An optional metadata-only conversational agent supports natural-language layout
creation and refinement, remembered photo names, fresh arrangements, retries,
and returning to earlier proposals. Proposals are preserved separately from
explicitly accepted versions.
Clear user-supplied names and identity answers are remembered automatically.
Ask to list, correct or forget them; only conflicting reassignments pause for
confirmation. Casual references need not create additional saved aliases.
See the [conversation guide](docs/cli-guide.md#conversational-proposals-optional).
Live model requests require explicit bounded authorization. A local web UI
can create and reopen saved projects, converse through the shared Python agent
and display saved previews. Image understanding and cloud hosting remain future
work.

**Layout format 3** uses centre-anchored `center_x`/`center_y` positions,
explicit whole/cover modes, stable `photo_id` values, and a back-to-front
`layers` array. Rendering preserves authored centres; an agent enlargement may
minimally reposition resized frames to fit. See the
[layout field guide](docs/layout-format.md) and generated
[JSON Schema](docs/layout.schema.json). Format 1 and 2 projects remain
untouched archives: their PNGs are viewable, but the new CLI does not load or
migrate their histories. Use a fresh data root for the updated examples.

## Where the idea came from

The project began with a conversation between the author and their daughter,
Emma. She had made a collage in the Android app PicCollage and wanted to improve
it. Attempts to adjust the result through ChatGPT and Copilot made it worse
rather than delivering the changes she wanted.

That experience inspired the separation at the heart of this project: let an
LLM propose creative layouts and adjustments, but let deterministic code
position, resize, and composite the original photos instead of regenerating
them. [Emma's original collage](photos/em_manual_collage.jpg) is a useful
reference for exploring which layout capabilities the project needs.

## UI getting started

After the one-time [backend setup](api/README.md) and [UI setup](web/README.md),
open two PowerShell terminals at the repository root:

```powershell
# Terminal 1: backend
.\api\start.ps1 -Live
```

```powershell
# Terminal 2: UI
npm --prefix .\web run dev
```

Open **http://127.0.0.1:5173**, choose **New project**, select 2-6 JPEG/PNG photos
and a canvas, then **Create project**. Reopen saved projects from **Projects**
or their URLs, including after refresh/restart. Send a request and refine the
result by photo number. `-Live` explicitly enables potentially paid model calls
using the existing backend credentials; omit it for model-free project setup
and browsing. Refresh restores saved messages/previews, but requires **Continue
generation** for a prepared stage that has not started. See the
[API guide](api/README.md#conversation-and-recovery) for timeout/recovery limits.
New web data uses the separate `.collage-data-web` root; existing CLI projects
are not listed. Acceptance, historical thumbnail navigation and download
controls remain future work. **Demo** is a separate scripted London walkthrough,
usable without the backend. Stop each server with Ctrl+C.

## CLI quick start

Use Python 3.12+ and PowerShell from the repository root. Rendering runs offline
without credentials. These commands use `.collage-data-v3`, separate from any
old `.collage-data` archive; original photos stay unchanged.

### Setup (once)

Skip this if the project's `.venv` and dependencies are already installed.
Activation is not required. Dependency installation downloads packages;
rendering itself is offline.

```powershell
python -m venv .\.venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

### Tilted charcoal collage (four photos)

Create a project, apply `emma_tilted_2x3.json`, and open the resulting
**1200x1800 (2:3)** PNG. Import order must be Bridge 1, breakfast 2, Eye 3,
bookshop 4.

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 create --project emma-tilted-demo --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
$tilted = .\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 apply-layout --project emma-tilted-demo --layout .\examples\emma_tilted_2x3.json | ConvertFrom-Json
Invoke-Item $tilted.render_path
```

### London Eye photo background (three photos)

Use a separate project for `emma_london_eye_3x4.json`: its import order is
Bridge 1, Eye 2, bookshop 3, with **no breakfast**. The resulting PNG is
**1200x1600 (3:4)**.

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 create --project emma-london-eye-demo --images .\photos\01_tower_bridge.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
$londonEye = .\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 apply-layout --project emma-london-eye-demo --layout .\examples\emma_london_eye_3x4.json | ConvertFrom-Json
Invoke-Item $londonEye.render_path
```

Run each `create` command only once. If a project name already exists, choose
a fresh name consistently in its commands. To try recipe edits afterward,
rerun just that example's `apply-layout` assignment and `Invoke-Item` command.
Each successful application creates a new accepted version; the variable
captures its actual output path, so you open the latest result rather than
always opening `v0001.png`.

### Other layouts

For simpler whole-photo arrangements with the same four-photo import order,
use `examples\portrait_3x4.json` (**900x1200**) or
`examples\portrait_9x16.json` (**900x1600**). Canvas dimensions and positions
come from the recipe, not separate CLI aspect-ratio flags.

For an asymmetric **1200x1800 (2:3)** composition with borders and a larger
foreground photo, see [Emma's layered example](docs/cli-guide.md#emmas-layered-23-example)
and its editable recipe, `examples\emma_2x3.json`.
The separate [framed variation](docs/cli-guide.md#emmas-framed-variation) uses
`examples\emma_framed_2x3.json` to adjust the bookshop and breakfast crops without
changing that whole-photo baseline.
`examples\emma_rounded_2x3.json` adds subtle rounded corners to the refined
framed composition; see [rounded corners](docs/cli-guide.md#rounded-corners)
for the single-radius setting.
The [evolved tilted demo](docs/cli-guide.md#emmas-evolved-tilted-demo),
`examples\emma_tilted_2x3.json`, uses a charcoal background, thinner white
borders, rounded corners, and gentle tilts. It develops the composition rather
than trying to match the manual reference more closely.
The [London Eye background demo](docs/cli-guide.md#emmas-london-eye-background-demo),
`examples\emma_london_eye_3x4.json`, puts the bookshop and Bridge over the full
night-time photo, without breakfast. It uses a separate three-photo project.

## Editable recipes and saved results

Files under `examples` are **input recipes**: edit their canvas, photo positions,
widths, whole/cover modes, crop controls, corners, tilt, and layer order, then run
`apply-layout` to try the design. Photo numbers refer to the project's import
order, not image content or stacking order.

Files such as `layouts\v0001.json` under a project's working directory are
**saved snapshots**. Each contains the validated input under `recipe`, a separate
`geometry` array with pixel boxes, resolved heights, source crops and rotated
footprints, and an accepted revision number.
It accepts a version only after
validation and rendering succeed. Editing the input does not change an existing
version; applying it again creates the next version. Later renders use the
saved snapshot, not the input file.

Keep editing the recipe, not the generated snapshot. See the
[CLI guide](docs/cli-guide.md#input-layouts-and-saved-versions) for the full
relationship, storage paths, and versioning behavior.

## Replay and testing notes

The existing notes on replay, call budgets, offline assessment and pixel-testing
are collected in [LESSONS.md](LESSONS.md).

## Documentation

| Document | Purpose |
|---|---|
| [Architecture](architecture.md) | Package responsibilities, shared backend, and CLI/web/API flows |
| [Replay and testing notes](LESSONS.md) | Replay examples, call budgets, offline assessment, and how the tests check images |
| [Local CLI guide](docs/cli-guide.md) | Setup, commands, examples, layout rules, limits, storage, and tests |
| [Layout field guide](docs/layout-format.md) | Concise format 3 contract and adjustment examples for people and future LLMs |
| [Input JSON Schema](docs/layout.schema.json) | Generated structural schema, synchronized with the models by a test |
| [Planning and implementation history](planning/README.md) | Current direction, blueprint reconciliation, and numbered historical planning records |
| [Foundry experiments](temp-foundry-test/README.md) | Separate keyless model-connectivity examples; running them makes paid service calls |

This README is the evolving project entry point. Current usage and layout
contracts live under `docs`; the living planning index and historical phase
briefs, decisions, and execution records live under `planning`.
