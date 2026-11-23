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
Live model requests require explicit bounded authorization. A graphical UI,
image understanding, and cloud hosting remain future work.

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

## Quick start

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

## Replay a prompt sequence

Replay conversations from `examples\sequences\01_dark_portrait_adjustments.json`
or `02_landscape_staggered_adjustments.json`. **One message runs per invocation
by default; nothing is automatically accepted.**

```powershell
$sequence = '.\examples\sequences\02_landscape_staggered_adjustments.json'

# Offline: validate the sequence and source-file availability/hashes.
.\.venv\Scripts\python.exe -m ai_collage.cli.replay --sequence $sequence --check

# Live, when authorized: choose a fresh project ID.
.\.venv\Scripts\python.exe -m ai_collage.cli.replay --sequence $sequence `
  --data-dir .\.collage-data-v3 --project YOUR-NEW-PROJECT
```

Repeat the live command with `--resume` to advance that project by one message.
Add `--remaining` only to run all remaining messages without pausing. If the
sequence has four uninterrupted messages, that means at most **16 model calls**,
including validation corrections (at most four per attempt). Explicit answers
have their own bounded attempts. There is no shared allowance
to provision or replenish. A failed step needs an explicit `--resume --retry`;
questions, naming receipts and interrupted steps stop for inspection. Naming
receipts require an explicit recorded answer; replay never approves them for you.
Live execution still needs
authorization; this tooling change does not authorize service calls.

Find the cursor and execution summaries in the project's `replay\report.json`,
sequence snapshots/contexts/results in `replay\steps`, and immutable JSON/PNG
proposals in `conversation\proposals`. Unattempted messages may be edited before
resuming. See the [full syntax and safeguards](docs/cli-guide.md#repeatable-prompt-sequences).
Request usage is recorded automatically in the project's `conversation\requests`.
Interactive chat remains local-only unless started with `--live`.

Assess a saved replay **offline**, without generating or accepting anything:

```powershell
.\.venv\Scripts\python.exe -m ai_collage.cli.assess --data-dir .\.collage-data-v3 `
  --project YOUR-REPLAY-PROJECT --profile dark-portrait-adjustments
```

Omit `--profile` for evidence-integrity checks only, applicable to either
sequence. The dark portrait profile additionally checks its specific requested
edits and historical style rules. Numbered reports go in `replay\assessments`;
subjective composition review stays separate. This replaces the old evaluator.

## How the tests check images

The rendering tests create tiny temporary images in code, drawing known colours
and shapes on them. They pass these through the normal import, layout, and render
workflow, then inspect the resulting pixels. For example:

- Red, green, and blue bands reveal whether panning selects the left, middle,
  or right part of an image.
- A square drawn inside a wide image should remain square when rendered into a
  tall frame, rather than becoming stretched.
- Known border colours and transparent areas let tests check border thickness
  and which overlapping layer shows through, including at rounded corners.
- Coloured corner markers let tests check a tilted photo's angle, size, centre,
  and retention of all four corners.

Because the starting pictures are deliberately simple, the expected colours
and positions are known in advance. Checks can be exact where appropriate,
with small tolerances where resizing or JPEG compression blends pixels.
No AI judges whether the result looks right, and the tests run offline without
using your photos. Real-photo examples still help us judge the composition.

Other tests cover invalid layouts, saved versions, and failures that must leave
previous results intact. See the [CLI guide](docs/cli-guide.md#verification)
for instructions to run the tests.

## Documentation

| Document | Purpose |
|---|---|
| [Local CLI guide](docs/cli-guide.md) | Setup, commands, examples, layout rules, limits, storage, and tests |
| [Layout field guide](docs/layout-format.md) | Concise format 3 contract and adjustment examples for people and future LLMs |
| [Input JSON Schema](docs/layout.schema.json) | Generated structural schema, synchronized with the models by a test |
| [Planning and implementation history](planning/README.md) | Current direction, blueprint reconciliation, and numbered historical planning records |
| [Foundry experiments](temp-foundry-test/README.md) | Separate keyless model-connectivity examples; running them makes paid service calls |

This README is the evolving project entry point. Current usage and layout
contracts live under `docs`; the living planning index and historical phase
briefs, decisions, and execution records live under `planning`.
