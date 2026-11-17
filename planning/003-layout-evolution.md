# Layout Design Decisions

> **Historical decision record:** Layout feature increments and their subsequent
> format 2 reconciliation, retained at the close of the offline refactoring.
> Approvals and retry budgets below belong to those completed increments, not
> future work. See the [planning index](README.md) for current direction and the
> [layout field guide](../docs/layout-format.md) for the current contract.

Short records of layout capability decisions and their implementation status.
This is not a new phase plan or permission to implement future extensions.

## Format 2 refactoring

The approved [refactoring brief](004-engine-refactoring.md) preserves these
capabilities with a cleaner contract; see the current
[field guide](../docs/layout-format.md). Recipes now use `layers` back to front,
`photo_id` for identity, `box` for placement, and explicit `mode: "whole"` or
`mode: "cover"` with cover-only `crop` controls. There is no separate element ID,
constant image type, or z-value. The solid canvas background is a hex string.

Snapshots separate the canonical `recipe` from typed derived `geometry`.
Project metadata and snapshots use `schema_version: 2`; old saved projects
remain untouched archives, not loadable through a compatibility layer.
All seven example recipes were converted while retaining their compositions.
References below to preserving earlier saved versions describe the historical
feature increments; current guarantees apply to new-format versions.

## Photo borders

**Status: implemented following explicit user approval for the feature and
tests.** An image element accepts an optional `border` object with required
`width_px` and `color` fields. See the [CLI guide](../docs/cli-guide.md#outside-photo-borders)
for the input syntax and current behavior. No dependencies or schema-version
migration were needed.

### Units and appearance

- Border thickness is a nonnegative integer in output-canvas pixels, not a
  normalized proportion. Colour uses a six-digit hex value, such as `#FFFFFF`.
- A uniform border has the same pixel thickness on all four sides. Zero, `null`,
  or an omitted border means no border; existing layouts retain their appearance.
- Borders occupy a ring outside the photo. The border itself must not paint
  over photo pixels, crop content, or stretch the source to a different aspect
  ratio.
- Pixels are resolution-specific: doubling the canvas dimensions requires
  doubling border thickness to preserve its proportional appearance. Automatic
  export-resolution scaling is not part of this extension.

### The layout box includes the border

The normalized x/y position and width describe the **outer box**, including
the border. This makes positioning and canvas-boundary checks account for the
whole element, rather than treating the border as an invisible extra footprint.

In default whole-photo mode, resolve the outer pixel width using the existing
rounding rule, then subtract twice the border thickness to obtain the photo's
pixel width. Derive the photo's height from its oriented source aspect ratio
using the existing rounding rule.
Add the top and bottom border thicknesses to obtain the outer height. The photo
starts one border thickness inward from the outer box's top-left corner.
Normalized height remains derived, not an independent input in that mode.
Cover mode below instead specifies both outer dimensions before insetting.

Continuous bounds and normalized height use the unrounded outer width, with
the border subtracted before applying the photo ratio and added back afterward.
Pixel bounds use the rounding sequence above. This preserves existing
border-free geometry and checks both ideal and actual rendered bounds.

Consequently, adding a border while keeping the same outer width makes the
photo slightly smaller. This is resizing the whole photo, not covering its
edges. To preserve its previous pixel size, the outer box must grow instead.
With a zero-width border, the outer box and photo box coincide, matching the
current behavior.

Reject geometry that leaves no positive photo area or puts any part of the outer
box outside the canvas. Do not silently crop or clip an out-of-bounds border.
A photo whose border touches the canvas edge therefore sits inward by the
border thickness.

The border and photo form one layer in the back-to-front array. Foreground layers may
obscure a background element's photo and border together. This intentional
occlusion is separate from cropping the source photo.

### Reference and first approximation

[Emma's manual collage](../photos/em_manual_collage.jpg) is a 1200x1800 (2:3)
reference, with approximately 15-pixel white separators and a larger foreground
Tower Bridge photo. Narrow visible portions of other photos may result from
overlap; the flattened JPEG does not establish their original frame/crop setup.

Following separate user approval, `examples\emma_2x3.json` now approximates that
composition with the existing border feature, whole photos, and stacking. The
separate `emma-demo` project holds its generated snapshot and preview, leaving
the earlier demo projects unchanged. See the
[CLI guide](../docs/cli-guide.md#emmas-layered-23-example) for reproduction commands.

The first render captures the main composition, including the bookshop over the
London Eye and the larger foreground bridge. It is not a pixel match: its
bookshop/breakfast split is higher, and its uniform outside borders add a white
outer rim where the reference is flush with the canvas edges. This makes
per-edge border control or intentional canvas clipping possible future topics,
not features silently introduced by this example. Framing differences alone
do not establish the reference's original crop/pan settings.

No engine changes were needed for that first example. Cropping, panning,
zooming, independently shaped frames, and model-generated layouts were outside
its scope; the separately approved framing increment follows below.

The no-Git-write and zero-application-service-call guardrails still apply.
The refactoring brief defines the current local/macro retry allowances and
shared six-cycle ceiling; it supersedes the earlier two-cycle phase budget.

## Fixed frames and photo framing

**Status: implemented following explicit approval.** This increment covers
fixed frames, crop-to-fill, pan/zoom, tests, and a separate framed Emma example.
Rounded corners were a separately approved follow-up, described below;
model-generated layouts remain deferred. See the
[CLI guide](../docs/cli-guide.md#fixed-frames-pan-and-zoom) for syntax.

- Preserve the existing whole-photo mode and its derived height. Existing input
  recipes, saved versions, and examples must keep their current behavior.
- Add an explicit crop-enabled mode with independently shaped rectangular
  frames, rather than restricting frames to the source photo's aspect ratio.
  The outer frame includes the border; its inset is the photo display area.
- Keep frame placement separate from photo framing. Panning or zooming changes
  which part of the original appears inside the frame without moving its border
  or changing stacking order.
- Always cover the entire photo display area without stretching or exposing
  empty strips. Pan positions must stay within the available crop travel.
- Pan identifies the source region to show, not the direction the photo moves.
  Use normalized positions along the available crop travel: 0 means left/top,
  0.5 means centered, and 1 means right/bottom at the selected zoom. An axis
  with no crop travel has no visible pan effect; the frame itself stays fixed.
- Zoom ranges from **1x to 4x**, inclusive. At 1x, use the minimum uniform scale
  needed to cover the display area; higher values multiply that scale. This is
  not zoom relative to the original file's pixel dimensions.
- Default: geometric centering at 1x. This does not automatically identify or
  center a subject such as the breakfast plate.

The current input contract requires each layer's `mode: "whole"` or `"cover"`.
Cover mode requires `box.height` and permits a `crop` object with `zoom`,
`pan_x`, and `pan_y`. Defaults are 1, 0.5, and 0.5 respectively; omitting `crop`
uses defaults, but explicit null is invalid. Whole mode forbids both input
height and crop controls. Snapshot geometry stores a derived `source_crop`
rectangle in oriented source pixels; fractional edges allow proportional
sampling without allocating a full enlarged photo.

The original files remain unchanged. Cropping here means selecting a source
region during deterministic rendering, not modifying or regenerating photos.
Preserve the first Emma example as a whole-photo baseline when trying a later
framed approximation.

`examples\emma_framed_2x3.json` is that separate approximation, retaining the
Bridge/Eye placements while reframing the bookshop and breakfast. It does not
reconstruct the reference's original settings or change the whole-photo baseline.

## Rounded corners

**Status: implemented following explicit approval.** An image element accepts
`corner_radius_px`, a nonnegative integer in output pixels, defaulting to zero.
See the [CLI guide](../docs/cli-guide.md#rounded-corners) for syntax and examples.

- Specify one corner radius in pixels at the **photo's edge**, not two
  independently adjustable radii.
- For a positive radius, derive the outer border radius by adding border
  thickness to the photo radius. A 10-pixel photo radius with a 15-pixel border
  therefore produces a 25-pixel outer radius. The curves share corner centers
  and maintain the border's thickness around the bend.
- Zero or an omitted radius explicitly preserves square corners on both
  boundaries, matching existing layouts.
- Keep the outer layout box inclusive of the border. Rounding does not require
  reversing that decision.
- Outside the rounded outer boundary, show underlying layers rather than
  painting a white rectangular corner. Between the two curved boundaries, draw
  the border. Inside the photo boundary, draw the framed photo.
- Rounded photo corners intentionally mask small corner regions in the render;
  they do not alter source files. This is distinct from a border accidentally
  painting over the photo.
- Reject a radius larger than half the smaller actual photo dimension after
  rounding and border inset. Do not silently clamp invalid values.
- Smoothly antialias both edges while preserving photo alpha and avoiding a
  compositing seam between the photo and border.

`examples\emma_rounded_2x3.json` adds a 10-pixel photo radius to the refined
framed composition without changing its crops, borders, or placement. The
square-corner recipes and accepted versions remain unchanged.

The separately approved tilt implementation follows. Text/captions, including
polaroid-style captions, remain postponed. Each implementation increment needs
its own approval, focused tests, and visual review.

## Tilt

**Status: implemented following explicit approval for implementation and
testing.** A photo layer accepts `rotation_degrees`, defaulting to zero.
Snapshot geometry stores a derived `rotated_box_pixels` for tilted layers;
untilted layers store explicit `null`. See the [CLI guide](../docs/cli-guide.md#tilt)
for syntax. Earlier examples remain unchanged; the separately approved evolved
Emma demonstration below uses a new recipe.

### Angle and finished frame

- Accept finite angles from **-10 to +10 degrees**, inclusive. Fractional degrees,
  such as 2.5, are allowed.
- Positive angles rotate clockwise; negative angles rotate counterclockwise.
- Zero or an omitted angle means no tilt. Explicit zero and omission retain
  the same new-format output; old snapshots remain unsupported archives.
- Rotate the finished photo, border, and rounded corners together as one
  transparent layer. Resolve whole-photo sizing or cover framing first, then
  apply borders and rounding before rotation. Tilt does not change the selected
  source crop or pan/zoom settings, stretch the photo, or modify source files.

### Untilted frame versus rotated footprint

The recipe's `box` describes the **untilted outer frame**, including
its border. Its x/y coordinates locate that frame's top-left corner, not the
top-left corner of the rotated footprint. Whole-photo mode still derives height;
cover mode still supplies an independent height.

Rotate around the frame's centre without changing its size or moving that
centre. Perform rotation in output-pixel space, not directly on the independently
normalized axes, so the angle is physically correct on portrait and landscape
canvases alike.

The renderer derives the rotated footprint separately. That footprint generally
needs more space than the untilted box, so an otherwise valid layout may need
extra clearance before tilt can be added. Do not squeeze the rotated photo back
inside its original box.

Use the rotated outer rectangle, including its border, for conservative
canvas-boundary checks. Rounded or transparent corners do not provide an
exception to the containment rule. Account for pixel rounding and rotation
sampling as well as ideal geometry so no visible edge pixels are lost.
The implementation adds two transparent pixels around the finished frame for
bicubic sampling, rotates that padded layer, and rounds its footprint outward.
This intentionally reserves slightly more clearance than ideal geometry alone.
An explicit inverse affine transform keeps the original centre fixed even
when source or output dimensions have different odd/even pixel counts.

### Canvas containment and layout responsibility

- Initially, every rotated frame must fit entirely inside the canvas. Losing a
  corner at a canvas edge is not an acceptable default.
- Reject an overflowing layout with a clear error. Do not silently move,
  shrink, crop, clip, or clamp the frame to make it fit. The layout author or
  future LLM must explicitly adjust its position or size.
- Preserve the existing acceptance rule: an invalid layout must not replace the
  current accepted snapshot or preview.
- Intentional off-canvas placement is deferred entirely, rather than exposed
  through a clipping opt-in in the first tilt feature.
- Canvas containment is separate from inter-photo overlap. Existing intentional
  overlaps and layer-order behavior remain valid; each complete rotated layer
  participates in stacking as one element. This is not a guarantee that every
  photo is unobscured by other photos.

Focused tests cover angle limits and direction, centre-based
rotation on nonsquare canvases, expanded-footprint rejection at canvas edges,
border/rounding/alpha composition, overlap, and zero-angle compatibility in
addition to saved-state consistency, reproducible rendering, and failure-safe
publication. The separate evolved visual example follows below.

### Evolved Emma demonstration

**Status: example created following separate approval.**
`examples\emma_tilted_2x3.json` starts from the latest rounded layout,
`examples\emma_rounded_2x3.json`, and evolves it to showcase new features rather
than keep reproducing Emma's manual collage exactly. Earlier example recipes
and accepted versions remain unchanged as reference points.

The visual direction is:

- A charcoal background (`#282A2E`).
- Subtle 10-pixel white borders and 12-pixel photo-edge corner radii.
- Restrained tilts: Bridge -2.5 degrees, breakfast +2, Eye -1.5, bookshop +1.25.

Frame positions and sizes are explicitly inset and reduced to leave room for
rotation, keeping every complete frame on the canvas. The photo mapping,
stacking, and cover pan/zoom settings are retained. These visual values are
example-specific choices, not renderer defaults or new limits.
