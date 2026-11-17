# Local CLI Guide

The current offline engine uses **layout/project format 2**. It imports original
JPEG/PNG photos and deterministically renders editable JSON recipes, without
credentials or model calls. See the [layout field guide](layout-format.md) for
syntax and the [README](../README.md) for the project story.

## Setup (PowerShell, Python 3.12+)

Run from the repository root:

```powershell
python -m venv .\.venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

Activation is unnecessary. If `python` is not on PATH, use your installed Python
executable's full path for environment creation. Runtime dependencies are Pillow
and Pydantic; `requirements-dev.txt` adds pytest. Installation downloads packages;
the application and tests run offline. The root environment is separate from
the `temp-foundry-test` experiments, which must not run as part of this workflow.

## Fresh projects and old archives

Format 1 projects and saved snapshots are **untouched archives**, not migrated
automatically. Their PNGs remain viewable, but the new CLI rejects their format.
Do not edit their metadata or apply new recipes to them. New-format equivalents
of all seven curated recipes retain their descriptive filenames in `examples`.

The default data directory remains `.collage-data`. The commands below instead
use a **fresh `.collage-data-v2` root** to avoid touching archived projects.
Both roots are ignored by Git. Put the global `--data-dir` option before the
command and use the same root for every command in a workflow.

## Render the supplied photos

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 create --project portrait-demo --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 inspect --project portrait-demo
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 apply-layout --project portrait-demo --layout .\examples\portrait_9x16.json
Invoke-Item .\.collage-data-v2\users\local-dev\projects\portrait-demo\renders\v0001.png
```

The first recipe makes a 900x1600 (9:16) white canvas with four complete 396x528
photos at (36,224), (468,224), (36,848), and (468,848). Import order assigns
Bridge 1, breakfast 2, London Eye 3, bookshop 4. Photo numbers are identifiers,
not stacking positions or content recognition.

`create` fails if the project exists. Choose a fresh name consistently rather
than deleting a previous project. To try the second 900x1200 (3:4) arrangement:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 apply-layout --project portrait-demo --layout .\examples\portrait_3x4.json
```

The same whole photos sit at (36,48), (468,48), (36,624), and (468,624). Applying
this after the first recipe accepts version 2, leaving version 1 untouched.
Canvas aspect ratio and positions come from the JSON, not separate CLI flags.

## Commands and paths

| Command | Behavior |
|---|---|
| `create --project ID --images FILE...` | Validate/import 2-6 JPEG/PNG photos in argument order; fail if the project exists. No layout is generated. |
| `inspect --project ID` | Show photo IDs/dimensions/aspect ratios, accepted versions, current version, and paths. Works before the first layout. |
| `apply-layout --project ID --layout FILE` | Validate recipe/current state, resolve geometry, and render before accepting the next immutable snapshot and updating the current pointer. |
| `render --project ID [--version N]` | Reopen and rerender an accepted new-format version, defaulting to current. No new version or current-pointer change. |

Results are JSON on stdout; errors use stderr and nonzero exit status.
Photo records now use `photo_id`, replacing format 1's `source_image_id`.
`apply-layout` still returns `version`, `layout_path`, and `render_path`.
Saved snapshots now separate `recipe` from `geometry`.

For a selected data root, files live beneath:

```text
users\local-dev\uploads\<asset-id>.jpg
users\local-dev\projects\<project-id>\project.json
users\local-dev\projects\<project-id>\layouts\v0001.json
users\local-dev\projects\<project-id>\renders\v0001.png
```

Project IDs are 1-64 lowercase letters/digits/hyphens, beginning and ending with
a letter or digit. Windows device names such as `con` and `com1` are rejected.
Imported paths resolve known UUID assets within the owner's uploads directory;
recipes cannot supply paths. `local-dev` is a namespace, not authentication.
There are no delete, reset, photo replacement/removal, migration, or
natural-language commands.

## Emma's layered 2:3 example

`examples\emma_2x3.json` is the 1200x1800 whole-photo approximation of
[Emma's manual collage](../photos/em_manual_collage.jpg), with 15-pixel white
borders. It is not an automatic reconstruction or a pixel match of the manual
reference. Intentional overlap, not cropping, hides parts of the whole photos.

Import the same four photos into a fresh project:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 create --project emma-demo --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 apply-layout --project emma-demo --layout .\examples\emma_2x3.json
```

Back to front, the layer array contains Eye (3), bookshop (4), breakfast (2),
and Bridge (1). The larger Bridge overlaps the others.

## Emma's framed variation

`examples\emma_framed_2x3.json` retains that canvas, order, and whole-photo
Bridge/Eye placements but uses independently shaped cover frames for the
bookshop and breakfast. The bookshop uses zoom 1.05 and pan 0/0.9, revealing more
of the entrance mat, projecting sign, and foreground street.

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 apply-layout --project emma-demo --layout .\examples\emma_framed_2x3.json
```

## Emma's rounded variation

`examples\emma_rounded_2x3.json` retains the refined framed composition and
15-pixel white borders, adding a 10-pixel photo radius (25-pixel outer radius).

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 apply-layout --project emma-demo --layout .\examples\emma_rounded_2x3.json
```

## Emma's evolved tilted demo

`examples\emma_tilted_2x3.json` evolves the composition rather than trying to
match the manual reference more exactly. It uses charcoal `#282A2E`, 10-pixel
white borders, 12-pixel photo radii, and gentle tilts: Bridge -2.5 degrees,
breakfast +2, Eye -1.5, bookshop +1.25.

The bookshop is near the top-right; Bridge is enlarged to a 720-pixel outer
width near the bottom-left, with 12-pixel sampled-footprint corner clearances.
Breakfast is shifted right but retains 40 pixels of right clearance. Every
rotated frame stays on canvas, while intentional inter-photo overlaps remain.

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 apply-layout --project emma-demo --layout .\examples\emma_tilted_2x3.json
```

## Emma's London Eye background demo

`examples\emma_london_eye_3x4.json` needs a **different three-photo mapping**:
Bridge 1, London Eye 2, bookshop 3. Breakfast is not imported.

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 create --project emma-london-eye-demo --images .\photos\01_tower_bridge.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v2 apply-layout --project emma-london-eye-demo --layout .\examples\emma_london_eye_3x4.json
```

The 1200x1600 canvas matches the uncropped night photo, placed first in `layers`
as a borderless, untilted full-canvas whole photo. A subtly tilted bookshop sits
upper-left and the larger Bridge lower-right. The latest composition keeps the
smaller foreground photos, corner clearances, 10-pixel white borders, and
12-pixel photo radii, exposing more of the wheel.

## Input layouts and saved versions

Edit the recipe, not `layouts\v0001.json`. The recipe contains canvas/layers,
normalized boxes, mode/crop choices, and optional frame styling. A saved
snapshot contains the validated `recipe` once, a separate `geometry` array,
`schema_version: 2`, and a backend-assigned accepted `version`.

Derived geometry records outer and inset pixel boxes, resolved normalized
height, optional fractional source crop, and optional rotated footprint.
Reopening recomputes these values and rejects inconsistencies. A recipe has
no paths, owner/project settings, accepted revision, or derived pixel fields.
Changing it does not change any previous snapshot or preview.

Acceptance updates the current pointer last. Invalid input, decoding/rendering
failure, or ordinary publication failure leaves the prior accepted state
intact. Rerendering replaces the PNG only after success, never the source or
snapshot. The store assumes one local writer; it is not a concurrent service
or a crash-recovery database.

## Limits and safety

Photos are limited to 25 MiB compressed and 40 million decoded pixels each.
Only single-frame JPEG/PNG files are accepted; EXIF orientation is applied.
Canvas axes are 1-4096 pixels. Recipe, project, and snapshot JSON documents are
limited to 1 MiB **in bytes**, read with a bounded read before parsing.
Malformed encoding, parser recursion failures, duplicate keys, and non-finite
numbers produce explicit errors. Unknown fields and numeric strings/booleans
are rejected by the strict models.

## Rendering rules

### Outside photo borders

`border.width_px` is outside the photo but inside its layout box. Keeping the
same outer width while adding a border makes the photo smaller, not obscured.
Transparent photo interiors remain transparent to lower layers.

### Fixed frames, pan, and zoom

Whole mode derives height; cover mode requires it. Cover crops uniformly fill
the inset frame, with zoom relative to minimum cover scale and pan selecting
source position over available travel. Moving a crop never moves its frame.

### Rounded corners

One `corner_radius_px` describes the photo edge; a positive outer border radius
adds border thickness. Zero keeps both edges square. Rounded corners reveal
lower layers rather than painting rectangular white corners.

### Tilt

`rotation_degrees` rotates the complete frame clockwise for positive values.
The untilted box retains its meaning; the engine checks the expanded sampled
footprint against the canvas. It never silently crops a tilted corner.

See the [layout field guide](layout-format.md) for current units, limits, and
geometry, and the [historical design decisions](../planning/003-layout-evolution.md)
for the rationale behind the feature increments.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q .\tests
```

Tests are grouped into contracts, geometry, rendering, storage, CLI, and curated
examples. Shared fixtures/helpers remain small. Synthetic photo tests check
known pixels and shapes; they do not depend on the personal photos in `photos`.
Example tests use synthetic 3:4 sources matching the recipes' required aspect
ratios. Real-photo before/after comparisons are separate phase evidence.
Tests block network access; CLI subprocess tests also remove Azure/OpenAI
environment variables. There is no model-based aesthetic judgment.
