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

### Emma's framed variation

`examples\emma_framed_2x3.json` keeps the same canvas, stacking, borders, and
whole-photo Bridge/Eye placements. It independently shapes the bookshop and
breakfast frames: a small bookshop zoom and left-aligned crop exclude more of
the right-hand window, while a narrower breakfast frame reframes the plate
instead of letting the Bridge hide so much of its left side. The horizontal
bookshop/breakfast seam is also lower than in the first approximation.

```powershell
.\.venv\Scripts\python.exe -m ai_collage create --project emma-framed-demo --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage apply-layout --project emma-framed-demo --layout .\examples\emma_framed_2x3.json
Invoke-Item .\.collage-data\users\local-dev\projects\emma-framed-demo\renders\v0001.png
```

Use a fresh name if that project exists. This deliberately separate example
does not change `emma_2x3.json` or `emma-demo`. The bookshop uses 1.05x zoom and
vertical pan 0.9 to show more of the entrance mat, projecting sign, and
foreground street. These are example-specific framing choices, not an
automatic reconstruction feature; this is still an approximation, including
the uniform white outer rim and square corners.

To try the current recipe in an existing `emma-framed-demo`, run only
`apply-layout` again, not `create`. Open the new render path printed by that
command; earlier saved versions remain unchanged.

### Emma's rounded variation

`examples\emma_rounded_2x3.json` keeps the refined framed composition and
15-pixel white borders, adding a 10-pixel photo-edge corner radius to every
image. The derived outer radius is 25 pixels; neither placement nor crop changes.

```powershell
.\.venv\Scripts\python.exe -m ai_collage apply-layout --project emma-framed-demo --layout .\examples\emma_rounded_2x3.json
```

This creates the next accepted version (version 3 if that project has just the
two earlier framed versions). Open the new render path printed by the command.
Square-corner recipes and prior snapshots are unchanged. A fresh project can
also use this recipe with the same four-photo import order.

### Emma's evolved tilted demo

`examples\emma_tilted_2x3.json` evolves the rounded composition into a feature
demonstration, rather than another attempt to reproduce the manual reference.
It retains the 1200x1800 canvas, photo mapping, stacking, and cover pan/zoom
settings, with smaller, inset frames to leave room for rotation.

The background is charcoal (`#282A2E`), with 10-pixel white borders and
12-pixel photo-edge radii (22 pixels at the outer border). Gentle tilts are
-2.5 degrees for Tower Bridge, +2 for breakfast, -1.5 for the London Eye, and
+1.25 for the bookshop. Every complete rotated frame, including its sampling
margin, fits inside the canvas; intentional inter-photo overlaps remain.

The bookshop sits near the top-right and Tower Bridge stays anchored near the
bottom-left, with 12 pixels of sampled-footprint clearance at those canvas edges.
The current recipe enlarges Bridge to a 720-pixel outer width (about 6.5% wider)
for a stronger overlap with the bookshop, and shifts breakfast 30 pixels right.
Breakfast retains 40 pixels of right clearance, compared with the bookshop's 12.
London Eye and bookshop placements, all tilts, styling, framing settings, and
stacking remain unchanged.

```powershell
.\.venv\Scripts\python.exe -m ai_collage apply-layout --project emma-framed-demo --layout .\examples\emma_tilted_2x3.json
```

This creates the next accepted version. In the evolving `emma-framed-demo`,
version 4 is the first tilted demo, version 5 refines the corner positions, and
version 6 enlarges Bridge and shifts breakfast right.
Open the new render path printed by the command. Other example recipes and
earlier saved versions remain unchanged. A fresh project can also use this
recipe with the same four-photo import order.

### Emma's London Eye background demo

`examples\emma_london_eye_3x4.json` uses the full London Eye night-time photo
behind a tilted bookshop at the upper-left and a larger Tower Bridge at the
lower-right, leaving the blue wheel visible between them. The 1200x1600 (3:4)
canvas matches the background photo's aspect ratio, so that photo is uncropped.
Foreground frames retain 10-pixel white borders and 12-pixel photo-edge radii.
The current recipe makes both foreground photos about 10% smaller while
preserving their corner clearances, tilts, and framing, revealing more of the
background.

No engine or schema changes are needed: the background is an ordinary,
borderless, untilted image element at `(0, 0)` with width `1.0` and the lowest
`z_index`. Its derived height fills the canvas. The solid canvas background
remains underneath; this is not a new `canvas.background` type.

Use a **new three-photo project**, importing **Bridge = 1, London Eye = 2,
bookshop = 3**. Breakfast is not imported. This differs from the four-photo
examples' numbering, so do not apply this recipe to those projects.

```powershell
.\.venv\Scripts\python.exe -m ai_collage create --project emma-london-eye-demo --images .\photos\01_tower_bridge.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage apply-layout --project emma-london-eye-demo --layout .\examples\emma_london_eye_3x4.json
Invoke-Item .\.collage-data\users\local-dev\projects\emma-london-eye-demo\renders\v0001.png
```

Choose another fresh name consistently if that project exists. Every imported
photo appears once, including the full-canvas background. Earlier Emma projects,
recipes, and accepted versions remain unchanged.
To update an existing project, run only `apply-layout` and use its printed render
path. In `emma-london-eye-demo`, version 1 keeps the original foreground sizes;
version 2 uses the smaller photos.

## Input layouts and saved versions

The input layout is an editable **design recipe**. A file such as
`.collage-data\users\local-dev\projects\portrait-demo\layouts\v0001.json` is the
project's accepted, fully calculated **snapshot** of that design.

| Input recipe, such as `examples\portrait_3x4.json` | Saved snapshot, such as `layouts\v0001.json` |
|---|---|
| Authored and edited by you; a future model could produce it | Generated by the engine |
| Canvas, photo IDs, normalized placement, stacking, optional borders/framing/corners/tilt, and explicit height only for cover mode | Same design plus exact outer pixel boxes, derived whole-photo height or source crop, rotated footprints for tilted frames, and a revision number |
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

See `examples\portrait_9x16.json` for the whole-photo baseline. Its shown fields
are required; optional `border`, `framing`, `corner_radius_px`, and
`rotation_degrees` settings are described below.
Unknown fields are rejected, including `rotation`, shadow, path, caption, a
standalone `crop` object, or a native image-valued canvas background. Pan/zoom belong inside
`framing`, not at element level. Backgrounds use `type: "color"` and a six-digit
`#RRGGBB` value; photographic backgrounds use a full-canvas image layer as
demonstrated above. PNG alpha shows the background or lower layers.
Animated/multiframe images are unsupported.

Both axes use 0-1 coordinates regardless of canvas shape. An image supplies
`x`, `y`, and positive `width` for its outer box, including any border; code
derives its height from the oriented photo's aspect ratio, border thickness,
and canvas dimensions in default whole-photo mode. Only explicit cover mode
accepts an independent normalized `height`. Every imported photo must occur
exactly once. Element
IDs are positive integers, independent of photo numbers and stacking.
`z_index` is an integer; higher values draw later/on top. Element IDs and
stacking indices must each be unique.

Normalized geometry is checked before rounding. In whole-photo mode, pixel
positions and width round to nearest integer, with exact halves upward.
Subtract the left/right border
from the rounded outer width to find the photo width, derive and round its
height using the oriented photo ratio, then add the top/bottom border. Integer
bounds are checked again. Without corner rounding, photos retain their entire
source rectangle, with aspect-ratio differences limited to pixel rounding;
placements that leave no photo area or
round its width/height to zero pixels fail. No invalid placement is silently
clamped or clipped. Cover mode uses the independent-height sequence below
instead of deriving height from the source.

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

The normalized box specifies the **outside of the border**. The photo is inset
on all four sides. In whole-photo mode it is resized without cropping and
retains its source aspect ratio: height remains derived. At a fixed outer
width, adding a border makes that photo smaller; increase the outer width to
preserve its size. In cover mode, both outer dimensions stay fixed and the
inset defines the photo's display area.

Whole-photo continuous bounds use the unrounded outer width and border-aware
derived height. Exact pixel boxes use the rounding sequence above, so saved
normalized height and pixel height divided by canvas height may differ by
rounding.
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

### Fixed frames, pan, and zoom

Opt an image into crop-to-fill with these fields inside its element:

```json
{
  "box_normalized": { "x": 0.05, "y": 0.1, "width": 0.4, "height": 0.3 },
  "framing": { "mode": "cover", "zoom": 1.25, "pan_x": 0.0, "pan_y": 0.5 },
  "border": { "width_px": 15, "color": "#FFFFFF" }
}
```

The usual ID, type, photo number, and stacking fields are still required.
`mode: "cover"` requires `box_normalized.height`, independently of the source
aspect ratio. Width and height describe the **outer frame**, including borders;
each scales against its own canvas axis. Frames may be wide, tall, or square.

Only `mode` is required within `framing`. Defaults are `zoom: 1.0`,
`pan_x: 0.5`, and `pan_y: 0.5`:

| Setting | Meaning |
|---|---|
| `zoom` | 1-4 inclusive, relative to the minimum uniform scale needed to cover the inset photo area |
| `pan_x` | 0 = leftmost source region, 0.5 = centered, 1 = rightmost |
| `pan_y` | 0 = topmost source region, 0.5 = centered, 1 = bottommost |

Pan selects a position along the **available crop travel at the current zoom**,
not the direction to move the photo. If an axis has no surplus at 1x, panning
that axis does nothing; zooming may create travel on both axes. Values must be
finite numbers within their ranges; invalid values are rejected, not clamped.
Centering is geometric, not subject detection.

After checking continuous frame bounds, round both outer dimensions and the
position independently with exact halves upward. Inset the rounded frame by
the border width; reject zero/negative photo area or any pixel overflow.
Calculate the source window from that actual inner pixel size, uniformly scale
it to fill the area, and render it directly with subpixel sampling. Pan/zoom
never move the frame, change its border thickness, or stretch the photo.
No geometric empty strips are exposed; transparent source pixels still show
underlying layers normally.

Omitting `framing` or setting it to `null` retains whole-photo mode. In that
mode, supplying height (even `null`) is invalid. Whole-photo and cover elements
may coexist in one layout, as in the framed Emma example. Existing recipes and
snapshots need no migration.

### Rounded corners

Each image element may contain:

```json
"corner_radius_px": 10
```

This is one nonnegative integer radius in output-canvas pixels at the
**photo's edge**, not the outside of its border. For a positive radius, add
the border width to obtain the outer radius: photo radius 10 with border 15
gives outer radius 25. The curves share corner centers, so both edges are
rounded and border thickness is maintained around the bend.

Omitting the setting or supplying zero keeps **both** edges square and retains
the previous rendering exactly. `null`, fractional values, and negative values
are invalid. A positive radius must be no larger than half the smaller actual
photo dimension, after pixel rounding and border inset. Oversized values fail
explicitly rather than being clamped.

The same setting works in whole-photo and cover modes, with or without a
border. It does not change the outer box, source window, pan/zoom, or stacking.
Corner edges are smoothly antialiased. Outside the curved outer boundary,
lower layers show through; the curved border remains an outside ring, not an
opaque backing behind transparent photo pixels.

Rounding intentionally masks small photo-corner regions in the render, without
modifying the original files. Radius is resolution-specific, like border
thickness. Saved snapshots retain the single radius and old snapshots default
to zero without migration. Text/captions remain unsupported.

### Tilt

Each image element may contain:

```json
"rotation_degrees": 3.5
```

Angles are finite numbers from **-10 to +10 degrees**, inclusive; fractional
degrees are supported. Positive means clockwise, negative counterclockwise.
Strings, booleans, `null`, and out-of-range values are rejected. Zero or an
omitted angle preserves the existing untilted rendering exactly.

`box_normalized` and `box_pixels` still describe the **untilted outer frame**,
including its border. The whole finished photo, border, and rounded corners
rotate together about that frame's unchanged centre, at unchanged size.
Rotation happens in output-pixel space, so angles are correct on nonsquare
canvases. Whole-photo sizing and cover pan/zoom run before tilt; tilt does not
change the selected crop or stretch the photo.

The renderer calculates an expanded footprint rather than squeezing the
rotated frame back inside its original box. Both ideal geometry and actual
pixel bounds must fit entirely inside the canvas. Pixel bounds conservatively
include a two-pixel transparent margin around the frame before rotation,
then round the expanded bounds outward. This margin permits smooth bicubic
edge sampling without cutting off pixels or creating dark fringes; allow a
little more clearance than the ideal geometric rectangle alone.

An overflowing layout fails explicitly. Move or resize its untilted box in the
recipe; the engine does not automatically move, shrink, crop, or clip it.
Intentional canvas-edge clipping is not supported. Photos may still overlap
according to `z_index`; photo and border remain one complete stacking layer.
Original photo files stay untouched.

Saved tilted elements retain `rotation_degrees` and a derived
`rotated_box_pixels` rectangle (`x`, `y`, `width`, `height`) for the complete
sampled layer. This backend-generated rectangle is not accepted in input
recipes. Zero-angle snapshots use `null`; old snapshots missing both fields
default to no tilt without migration. Reopening checks the footprint against
the untilted box, angle, and source metadata before rendering.

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

Saved layout JSON includes its backend-assigned version, resolved normalized
outer height, exact outer pixel boxes, and border/framing/corner-radius/tilt
settings. Whole-photo height is derived; cover-mode height is retained from the input. Cover-mode
elements also store a derived `source_crop` with `left`, `top`, `right`, and
`bottom` edges in oriented source-image pixels, potentially fractional.
Loading rechecks the geometry and source window against the design settings
and photo metadata; later renders use that accepted window. The snapshot is an
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
geometry on square/landscape/portrait canvases, whole-image retention,
non-stretching crop-to-fill, pan endpoints, fractional sampling, 1x-4x zoom, EXIF,
transparency, border pixels and bounds, concentric antialiased corner masks,
centre-based tilt and corner retention, expanded sampled bounds, stacking, strict validation,
failure-safe publication, legacy snapshots, and reopening projects across
separate CLI processes without Azure credentials.

Implementation scope, approval boundaries, and execution-budget records belong
in the [Phase 1 implementation plan](../phase_1_implementation_plan.md), not in
the user workflow. This guide describes the existing offline engine; it does
not require or authorize running the separate paid connectivity experiments.
