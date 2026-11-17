# Layout Design Decisions

Short records of layout capability decisions and their implementation status.
This is not a new phase plan or permission to implement future extensions.

## Photo borders

**Status: implemented following explicit user approval for the feature and
tests.** An image element accepts an optional `border` object with required
`width_px` and `color` fields. See the [CLI guide](cli-guide.md#outside-photo-borders)
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

The border and photo form one element at one `z_index`. Foreground elements may
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
[CLI guide](cli-guide.md#emmas-layered-23-example) for reproduction commands.

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

The existing no-Git-write, zero-service-call, and two-corrective-retry guardrails
still apply to any subsequent approved implementation.

## Fixed frames and photo framing

**Status: implemented following explicit approval.** This increment covers
fixed frames, crop-to-fill, pan/zoom, tests, and a separate framed Emma example.
Rounded corners and model-generated layouts remain later, separately approved
steps. See the [CLI guide](cli-guide.md#fixed-frames-pan-and-zoom) for syntax.

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

The explicit input contract uses an optional per-image `framing` object with
required `mode: "cover"` and optional `zoom`, `pan_x`, and `pan_y`. Defaults are
1, 0.5, and 0.5 respectively. Cover mode requires `box_normalized.height` for the
outer frame; supplying height without cover mode remains invalid. Omitting
`framing` or setting it to `null` retains whole-photo mode and its derived height.
Resolved snapshots additionally store a derived `source_crop` rectangle in
oriented source pixels; fractional edges allow proportional sampling without
allocating a full enlarged photo.

The original files remain unchanged. Cropping here means selecting a source
region during deterministic rendering, not modifying or regenerating photos.
Preserve the first Emma example as a whole-photo baseline when trying a later
framed approximation.

`examples\emma_framed_2x3.json` is that separate approximation, retaining the
Bridge/Eye placements while reframing the bookshop and breakfast. It does not
reconstruct the reference's original settings or change the whole-photo baseline.

## Subsequent increment: rounded corners

**Status: radius model agreed in discussion; not implemented.** Add this after
the fixed-frame geometry is settled.

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

Each increment gets its own approval, focused tests, and visual review before
proceeding. These notes record decisions, not a combined implementation
authorization.
