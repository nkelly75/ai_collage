# Local CLI Guide

This guide covers the currently implemented offline import, layout, and render
workflow. For the project overview and planned capabilities, see the
[root README](../README.md). Run all commands from the repository root, not from
`docs`.

## Setup (PowerShell, Python 3.12+)

Run from the repository root:

```powershell
python -m venv .\.venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

Activation is unnecessary. If `python` is not on PATH, invoke your installed
Python executable by its full path for the first command. `requirements.txt`
contains only runtime dependencies (Pillow and Pydantic); the development
manifest adds pytest. Installation downloads packages; the engine itself is
offline. The root `.venv` is independent of the smoke-test environment.

## Render the supplied photos

```powershell
.\.venv\Scripts\python.exe -m ai_collage create --project portrait-demo --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage inspect --project portrait-demo
.\.venv\Scripts\python.exe -m ai_collage apply-layout --project portrait-demo --layout .\examples\portrait_9x16.json
.\.venv\Scripts\python.exe -m ai_collage render --project portrait-demo --version 1
```

The starter is a 900x1600 (9:16) white canvas, with four complete 396x528 photos
in a 2x2 arrangement at (36,224), (468,224), (36,848), and (468,848).
The preview is at
`.collage-data\users\local-dev\projects\portrait-demo\renders\v0001.png`.
Commands print JSON metadata/paths; errors use stderr and a nonzero exit code.

`create` fails if the project already exists. Import order assigns stable image
numbers. Edit/copy the example JSON and run `apply-layout` again to create the
next version; do not re-create the project. `render` without `--version` uses the
current version. Rendering an old version does not make it current.

### Alternative 3:4 canvas

The four supplied photos are each 1536x2048 (3:4). The second example uses
a 900x1200 (3:4) canvas with the same uncropped 396x528 photos. Its row positions
are adjusted to (36,48), (468,48), (36,624), and (468,624), giving balanced
margins and no overlap.

```powershell
.\.venv\Scripts\python.exe -m ai_collage apply-layout --project portrait-demo --layout .\examples\portrait_3x4.json
```

After the 9:16 example, this produces version 2 at
`.collage-data\users\local-dev\projects\portrait-demo\renders\v0002.png`,
leaving version 1 untouched. If other layouts have already been applied, the
version number will be higher; use the paths printed by the command.
Canvas dimensions and positions come from the selected JSON, not separate CLI
aspect-ratio flags. No engine changes or photo reimport are needed.

Default storage is `.collage-data` in the current working directory. To use
another local root, put the global option **before** the command, consistently
for every invocation:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir C:\collage-working-data inspect --project portrait-demo
```

Project IDs are 1-64 lowercase letters/digits/hyphens, starting and ending with
a letter or digit. Windows device names such as `con` and `com1` are rejected.
There are no delete, reset, image replacement, or natural-language commands.

### Emma's layered 2:3 example

`examples\emma_2x3.json` is a first approximation of
[Emma's manual collage](../photos/em_manual_collage.jpg), using the same four
original photos, a 1200x1800 (2:3) canvas, and 15-pixel white borders.
It is a hand-authored input recipe, not automatic reconstruction from an image.

```powershell
.\.venv\Scripts\python.exe -m ai_collage create --project emma-demo --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage apply-layout --project emma-demo --layout .\examples\emma_2x3.json
Invoke-Item .\.collage-data\users\local-dev\projects\emma-demo\renders\v0001.png
```

Use another fresh project name consistently if `emma-demo` already exists.
Import only the four individual photos, not the flattened reference collage.
Back to front, the layers are London Eye (photo 3), bookshop (photo 4),
breakfast (photo 2), and Tower Bridge (photo 1). The larger bridge overlaps the
other layers; the bookshop hides the Eye's right-hand portion. Photos are
resized whole, with no crop, pan, or zoom operation, although layering obscures
parts of them.

This is deliberately not a pixel-identical reproduction. The reference reaches
the canvas edges, whereas the current uniform outside borders remain fully
inside the canvas and create a white outer rim. The bookshop/breakfast split is
higher in this approximation, and visible framing differs. Exact crop or
off-canvas placement settings cannot be recovered from the flattened reference;
this example does not introduce either feature to force a match.

## Input layouts and saved versions

The input layout is an editable **design recipe**. A file such as
`.collage-data\users\local-dev\projects\portrait-demo\layouts\v0001.json` is the
project's accepted, fully calculated **snapshot** of that design.

| Input recipe, such as `examples\portrait_3x4.json` | Saved snapshot, such as `layouts\v0001.json` |
|---|---|
| Authored and edited by you; a future model could produce it | Generated by the engine |
| Canvas, photo IDs, normalized x/y/width, stacking, and optional borders | Same design plus derived normalized height, exact outer pixel boxes, and a revision number |
| Reusable with a compatible photo-number mapping | Part of one project's immutable layout history |
| Supplied to `apply-layout --layout` | Read by `render --version` |

`apply-layout` validates the recipe against the imported photos, calculates
geometry, and renders a PNG. Only after success does it save the snapshot and
make that version current in `project.json`.

Later `render` calls use the saved snapshot and imported photo copies, not the
original input JSON. There is no live link back to the recipe: changing it does
not alter a saved version or regenerate a preview. To try an edit, change the
input recipe and run `apply-layout` again. This creates the next version, even
if you reuse the same input filename. Version numbers belong to each project,
so the same recipe can become version 1 in a fresh project and version 2 in
another.

Do not edit snapshots or pass them directly to `apply-layout`: their generated
fields are deliberately rejected by the input contract. Keep useful editable
recipes under `examples`. Photo IDs resolve through the receiving project's
`project.json`; neither kind of layout embeds the photo files.

## Layout contract

See `examples\portrait_9x16.json`. All shown fields are required; unknown fields
are rejected, including a supplied height, rotation, shadow, path, caption,
crop/pan/zoom setting, or image background. Backgrounds use `type: "color"` and
a six-digit `#RRGGBB` value. PNG alpha is composited over this background.
Animated/multiframe images are unsupported. An optional per-image `border` is
described below; the existing border-free examples remain valid.

Both axes use 0-1 coordinates regardless of canvas shape. An image supplies
`x`, `y`, and positive `width` for its outer box, including any border; code
derives its height from the oriented photo's aspect ratio, border thickness,
and canvas dimensions. Every imported photo must occur exactly once. Element
IDs are positive integers, independent of photo numbers and stacking.
`z_index` is an integer; higher values draw later/on top. Element IDs and
stacking indices must each be unique.

Normalized geometry is checked before rounding. Pixel positions and width round
to nearest integer, with exact halves upward. Subtract the left/right border
from the rounded outer width to find the photo width, derive and round its
height using the oriented photo ratio, then add the top/bottom border. Integer
bounds are checked again. Photos retain their entire frame, with aspect-ratio
differences limited to pixel rounding; placements that leave no photo area or
round its width/height to zero pixels fail. No invalid placement is silently
clamped or cropped.

Limits: 2-6 JPEG/PNG photos and elements, 25 MiB per photo, 40 million decoded
pixels per photo, and 1-4096 pixels per canvas axis. EXIF orientation is applied
for both metadata and rendering. Input files are never modified.

### Outside photo borders

Each image element may contain:

```json
"border": { "width_px": 15, "color": "#FFFFFF" }
```

Both fields are required when supplying a border object. `width_px` is a
nonnegative integer in output-canvas pixels; `color` is a six-digit hex colour.
Omitting `border`, setting it to `null`, or choosing zero width draws no border.
Existing border-free inputs and saved snapshots continue to work unchanged.

The normalized position and width specify the **outside of the border**. The
photo is inset on all four sides, resized without cropping, and retains its
source aspect ratio. At a fixed outer width, adding a border makes the photo
smaller; increase the outer width if you want to preserve the photo's size.
Height remains derived, not a second independently controlled dimension.

Continuous bounds use the unrounded outer width and border-aware derived
height. Exact pixel boxes use the rounding sequence above, so saved normalized
height and pixel height divided by canvas height may differ by rounding.
`box_pixels` in a saved snapshot is the outer box; its photo rectangle is
calculated by insetting that box by `width_px`. No snapshot migration is needed.

The border is only an outside ring, not a fill behind transparent photo pixels.
Photo transparency therefore continues to show the background or lower layers.
Photo and border share one stacking layer, so a foreground element can cover
both parts of a background element.

The whole outer box must fit the canvas, including its border. A border can
touch a canvas edge, but cannot extend past it; no implicit clipping occurs.
Borders are resolution-specific: double their pixel thickness when doubling
canvas dimensions if you want the same proportional appearance.

## Stored state and version control

```text
.collage-data\users\local-dev\
    uploads\<generated-asset-id>.jpg
    projects\portrait-demo\
        project.json
        layouts\v0001.json
        renders\v0001.png
```

`project.json` maps `source_image_id` to an asset ID and owner-relative
`imported_path`, such as `uploads\<generated-asset-id>.jpg`, plus original filename
and oriented dimensions. Source filenames/extensions need not determine the
imported extension: decoding identifies JPEG/PNG content. Rendering uses these
imported copies, not the originals in `photos`. Generated paths are restricted
to the owner's uploads directory. The fixed local owner is `local-dev`, not an
authentication system.

Saved layout JSON includes its backend-assigned version, derived normalized
outer height, exact outer pixel boxes, and optional border settings. It is an
immutable resolved record, **not** a hand-authored input file. For further edits,
use the original input under `examples`, not a resolved runtime file. Layout
portability assumes the same photo-number mapping in the destination project.

A version becomes current only after validation and rendering succeed. Files
are prepared locally, then metadata is replaced atomically as the final publish
step. Ordinary failures remove that attempt's new files and leave the prior
accepted state intact. `render` replaces only a successfully generated PNG,
never layout JSON or source assets. Missing/corrupt photos and inconsistent
saved geometry fail explicitly.

This is a **single-process/single-writer** store, not a transactional database or
a crash-recovery system. Do not edit runtime metadata or run writers
concurrently. If abrupt termination leaves next-version files behind, the engine
refuses to overwrite them and reports the need for local inspection.

The supplied `photos` and curated JSON in `examples` are eligible for your own
commits. `.collage-data`, `.venv`, caches, and temporary test output are ignored.
No blanket ignore applies to photos or JSON. No commands stage, commit, push,
or otherwise change Git state.

## Verification

Install the additional test dependency, then run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q .\tests
```

Tests generate temporary synthetic inputs, block network connections, and cover
geometry on square/landscape/portrait canvases, whole-image retention, EXIF,
transparency, border pixels and bounds, stacking, strict validation,
failure-safe publication, legacy snapshots, and reopening projects across
separate CLI processes without Azure credentials.

Implementation scope, approval boundaries, and execution-budget records belong
in the [Phase 1 implementation plan](../phase_1_implementation_plan.md), not in
the user workflow. This guide describes the existing offline engine; it does
not require or authorize running the separate paid connectivity experiments.
