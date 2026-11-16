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
- Borders occupy a ring outside the photo. They must not paint over photo
  pixels, crop content, or stretch the source to a different aspect ratio.
- Pixels are resolution-specific: doubling the canvas dimensions requires
  doubling border thickness to preserve its proportional appearance. Automatic
  export-resolution scaling is not part of this extension.

### The layout box includes the border

The normalized x/y position and width describe the **outer box**, including
the border. This makes positioning and canvas-boundary checks account for the
whole element, rather than treating the border as an invisible extra footprint.

Resolve the outer pixel width using the existing rounding rule, then subtract
twice the border thickness to obtain the photo's pixel width. Derive the photo's
height from its oriented source aspect ratio using the existing rounding rule.
Add the top and bottom border thicknesses to obtain the outer height. The photo
starts one border thickness inward from the outer box's top-left corner.
Normalized height remains derived, not an independent input.

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

No engine changes were needed for the example. Cropping, panning, zooming,
independently shaped frames, and model-generated layouts remain outside this
increment.

The existing no-Git-write, zero-service-call, and two-corrective-retry guardrails
still apply to any subsequent approved implementation.
