# Layout Format 3

This is the authored recipe contract for people and future layout-generating
LLMs. The engine is deterministic; it does not understand photo contents or
currently call an LLM. The generated [JSON Schema](layout.schema.json) describes
the structural alternatives. Project-specific checks still happen at runtime.

## The mental model

1. Pick a pixel canvas size and solid background colour.
2. Refer to photos by their stable import-order `photo_id`, not filenames or
   guessed descriptions. Use the project's oriented dimensions/aspect ratios
   when planning whole-photo placement.
3. List photo layers **back to front**. The last layer is on top. Moving a layer
   in this array never changes its photo number.
4. Choose `whole` for the entire photo or `cover` for an independently shaped,
   filled rectangular frame.
5. Apply optional border, corner rounding, and tilt to the completed frame.

Every imported photo must appear exactly once; projects have 2-6 photos.
An ordinary full-canvas image can be the lowest layer for a photo background.
There is no special background-photo field, element ID, image-type tag, or
`z_index`.

## Fields and units

| Field | Meaning |
|---|---|
| `schema_version` | Required integer `3`; unrelated to an accepted layout's revision number. |
| `canvas.width`, `canvas.height` | Required integers, 1-4096 output pixels each; any aspect ratio. |
| `canvas.background` | Required solid `#RRGGBB` colour under all photo layers. |
| `layers` | Required array of 2-6 layers, back to front. |
| `photo_id` | Required positive integer referring to a known imported photo. |
| `mode` | Required `whole` or `cover`; never inferred from missing fields. |
| `box.center_x`, `box.center_y` | Required outer frame centre. Horizontal position is a fraction of canvas width; vertical position is a fraction of canvas height. This is also the rotation anchor. |
| `box.width` | Required positive border-inclusive outer width / canvas width. |
| `box.height` | Required positive border-inclusive outer height / canvas height in cover mode; forbidden in whole mode, including null. |
| `crop` | Cover only: optional object; omission means centred at 1x. Null is invalid. Whole mode forbids this key. |
| `crop.zoom` | 1-4 inclusive, default 1, relative to the minimum uniform scale needed to cover the inset photo area. |
| `crop.pan_x`, `crop.pan_y` | 0-1 inclusive, default 0.5. Select left/top at 0 or right/bottom at 1 along available crop travel, not the direction to move the photo. |
| `border` | Optional/null for none; otherwise requires integer `width_px >= 0` and `color: "#RRGGBB"`. Zero thickness is invisible. |
| `corner_radius_px` | Nonnegative integer, default 0, at the photo edge. A positive outer radius adds border thickness; zero keeps both edges square. |
| `rotation_degrees` | -10 to +10 inclusive, default 0, fractions allowed. Positive clockwise, negative counterclockwise, around the untilted outer frame's centre. |

All box values are normalized independently on their axes, from 0 to 1.
Normalized 0.5 width and 0.5 height therefore do not imply a square on a
non-square canvas. Colours are six hex digits, not colour names or alpha hex.
Booleans, strings masquerading as numbers, non-finite numbers, duplicate JSON
keys, and unknown fields are invalid.
The old `box.x`/`box.y` fields are not accepted or reinterpreted.

## Whole-photo example

This is one layer inside a complete recipe:

```json
{
  "photo_id": 1,
  "mode": "whole",
  "box": { "center_x": 0.3, "center_y": 0.35, "width": 0.35 },
  "border": { "width_px": 10, "color": "#FFFFFF" },
  "corner_radius_px": 12,
  "rotation_degrees": -2.5
}
```

The engine subtracts the left/right border from the outer width, derives the
photo height from its oriented aspect ratio, and adds the top/bottom border.
It preserves the whole photo without stretching. Do not supply a height to
try to make this mode fit; use cover mode when an independent height is wanted.

## Cover-frame example

```json
{
  "photo_id": 3,
  "mode": "cover",
  "box": { "center_x": 0.7, "center_y": 0.35, "width": 0.35, "height": 0.4 },
  "crop": { "zoom": 1.05, "pan_x": 0.0, "pan_y": 0.9 },
  "border": { "width_px": 10, "color": "#FFFFFF" }
}
```

The frame stays fixed while crop controls choose its source window. At zoom 1,
use the largest source window with the inset frame's aspect ratio. Higher zoom
uses a smaller window; pan positions it over the available source travel.
An axis without crop travel has no visible pan effect. Original photos are
never edited, and the renderer samples the fractional window directly rather
than allocating a huge zoomed image.

## Adjustments and constraints

- **Move photo 3:** locate `photo_id: 3` and change its `box.center_x`/`box.center_y`; leave
  its identity, crop, style, and array position alone.
- **Resize a whole photo:** `box.width` controls size; height follows the source
  ratio and border rules. Keep `box.center_x`/`box.center_y` unchanged to
  preserve the centre; no position-offset calculation is needed.
- **Resize/reframe a cover photo:** change its outer box dimensions for a
  different frame shape around its unchanged centre, or change only `crop` to
  pan/zoom within the same frame.
- **Bring photo 1 forward:** move its existing layer later in `layers`; do not
  renumber photos, duplicate the layer, or add a z-value.
- **Add tilt:** retain the untilted frame's meaning and reserve extra room
  around its centre. Rotate the photo, border, and rounding together.
- **Remove borders:** change only `border`. A whole photo's derived height
  can change around its centre; the top edge is no longer the anchor.

The complete frame, including a tilted sampling footprint, must fit on the
canvas. Rounded/transparent corners do not waive this check. Border inset must
leave positive photo pixels; radius must not exceed half the smaller actual
inset dimension. The engine checks both continuous and rounded pixel bounds.
It rejects invalid layouts rather than silently moving, shrinking, clipping,
or clamping. Explicit overlap with other layers is allowed.

### Pixel rounding

The engine first resolves the continuous frame about the authored centre for
containment checks. For rendering, it rounds the outer width half-up to whole
pixels. Whole mode derives the inset height from that rounded width and rounds
it half-up before adding borders; cover mode rounds its explicit outer height.
It then subtracts half the rounded size from the authored pixel centre and
rounds that origin half-up on each axis. Ties go toward the larger coordinate.
The resulting raster centre is at most half an output pixel from the authored
centre on each axis. Repeated resizes use the unchanged authored centre, not
the previous raster origin, so rounding does not accumulate drift.

Actual output pixel boxes contain integers. Normalized coordinates and
fractional source crops retain their precision; there is no new decimal-place
limit or automatic rounding of authored JSON in format 3. Rotation still uses
the raster frame centre and the same sampling margin and footprint checks.

These are complete recipes demonstrating the contract:
[tilted Emma composition](../examples/emma_tilted_2x3.json) and
[London Eye background](../examples/emma_london_eye_3x4.json). Their photo
mappings differ; see the [CLI guide](cli-guide.md).

## Saved snapshots are not recipes

An accepted snapshot has its own `schema_version: 3` and positive `version`,
one canonical validated input under `recipe`, and separate `geometry` ordered
like the recipe's layers. Geometry contains the `photo_id`, normalized
resolved frame, outer/inner pixel boxes, optional source window, and optional
rotated footprint. Derived fields are required even when their value is null.
The derived `geometry.box_normalized.x`/`y` are the continuous top-left
calculated from the authored centre and continuous size. Derived pixel boxes
also use top-left coordinates for rendering. Neither is an alternative authored
position or a value to feed back as `center_x`/`center_y`.

The engine recomputes geometry when reopening a snapshot and rejects
inconsistencies before rendering or accepting a later version. Edit the
original recipe and apply it again instead of changing a saved snapshot.
Format 1 and 2 recipes, projects, and snapshots are unsupported. Existing project
data remains an untouched archive; previously rendered PNGs remain viewable. No
migration or legacy loader is provided.

The generated schema is checked against the models in the tests. To regenerate
it after intentionally changing a contract, run from the repository root:

```powershell
.\.venv\Scripts\python.exe -c "import json; from pathlib import Path; from ai_collage.models import InputLayout; Path(r'docs\layout.schema.json').write_text(json.dumps(InputLayout.model_json_schema(), indent=2) + '\n', encoding='utf-8')"
```
