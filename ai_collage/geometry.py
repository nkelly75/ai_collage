"""Pure frame, crop, and rotation geometry from authored intent and metadata."""

from fractions import Fraction
from math import ceil, cos, floor, radians, sin

from .models import (
    Canvas,
    CollageError,
    Crop,
    FrameBox,
    InputLayout,
    Layer,
    LayerGeometry,
    Photo,
    PixelBox,
    ResolvedLayout,
    SourceCrop,
)

ROTATION_PADDING = 2


class LayoutBoundsError(CollageError):
    """Containment failure with metadata-only, candidate-specific diagnostics."""

    def __init__(self, message: str, details: dict[str, object]):
        super().__init__(message)
        self.details = details


def round_half_up(value: Fraction) -> int:
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


def resolve_source_crop(
    photo: Photo, width: int, height: int, crop: Crop
) -> SourceCrop:
    scale = max(Fraction(width, photo.width), Fraction(height, photo.height))
    scale *= Fraction(str(crop.zoom))
    crop_width, crop_height = Fraction(width) / scale, Fraction(height) / scale
    left = (photo.width - crop_width) * Fraction(str(crop.pan_x))
    top = (photo.height - crop_height) * Fraction(str(crop.pan_y))
    return SourceCrop(
        left=float(left),
        top=float(top),
        right=float(left + crop_width),
        bottom=float(top + crop_height),
    )


def _rotated_bounds(
    x: float, y: float, width: float, height: float, degrees: float, padding: int = 0
) -> tuple[float, float, float, float]:
    angle = radians(degrees)
    c, s = abs(cos(angle)), abs(sin(angle))
    half_width = ((width + 2 * padding) * c + (height + 2 * padding) * s) / 2
    half_height = ((width + 2 * padding) * s + (height + 2 * padding) * c) / 2
    center_x, center_y = x + width / 2, y + height / 2
    return (
        center_x - half_width, center_y - half_height,
        center_x + half_width, center_y + half_height,
    )


def _pixel_frame(
    layer: Layer, photo: Photo, canvas: Canvas, height: Fraction,
) -> tuple[int, int, int, int, int, int]:
    border = layer.border.width_px if layer.border is not None else 0
    width = round_half_up(Fraction(str(layer.box.width)) * canvas.width)
    photo_width = width - 2 * border
    photo_height = (
        round_half_up(Fraction(photo_width * photo.height, photo.width))
        if layer.mode == "whole"
        else round_half_up(height * canvas.height) - 2 * border
    )
    return (
        round_half_up(Fraction(str(layer.box.x)) * canvas.width),
        round_half_up(Fraction(str(layer.box.y)) * canvas.height),
        width, photo_height + 2 * border, photo_width, photo_height,
    )


def _bounds_error(
    message: str, layer: Layer, photo: Photo, canvas: Canvas, height: Fraction,
) -> LayoutBoundsError:
    width = Fraction(str(layer.box.width))
    x, y = Fraction(str(layer.box.x)), Fraction(str(layer.box.y))
    outer = (
        float(x * canvas.width), float(y * canvas.height),
        float((x + width) * canvas.width), float((y + height) * canvas.height),
    )
    rotated = _rotated_bounds(
        outer[0], outer[1], float(width * canvas.width),
        float(height * canvas.height), layer.rotation_degrees,
    )
    px, py, pw, ph, photo_width, photo_height = _pixel_frame(layer, photo, canvas, height)
    if layer.rotation_degrees:
        sampled = _rotated_bounds(
            px, py, pw, ph, layer.rotation_degrees, padding=ROTATION_PADDING,
        )
        sampled = (
            floor(sampled[0]), floor(sampled[1]), ceil(sampled[2]), ceil(sampled[3]),
        )
        relative = _rotated_bounds(
            0, 0, pw, ph, layer.rotation_degrees, padding=ROTATION_PADDING,
        )
    else:
        sampled = (px, py, px + pw, py + ph)
        relative = (0, 0, pw, ph)
    continuous = _rotated_bounds(
        0, 0, float(width * canvas.width), float(height * canvas.height),
        layer.rotation_degrees,
    )
    ranges = {}
    for axis, extent, size, lower, upper in (
        ("x", width, canvas.width, 0, 2),
        ("y", height, canvas.height, 1, 3),
    ):
        # Integer-origin intervals conservatively include half-up rounding;
        # intersect them with authored and continuous rotated containment.
        minimum = max(0, -continuous[lower] / size, ceil(-relative[lower]) / size)
        maximum = min(
            float(1 - extent), (size - continuous[upper]) / size,
            floor(size - relative[upper]) / size,
        )
        minimum, maximum = ceil(minimum * 1e9) / 1e9, floor(maximum * 1e9) / 1e9
        ranges[axis] = [minimum, maximum]
    fits = photo_width > 0 and photo_height > 0 and all(
        lower <= upper for lower, upper in ranges.values()
    )
    bounds = (outer, rotated, sampled)
    return LayoutBoundsError(message, {
        "error": message, "photo_id": layer.photo_id,
        "outer_bounds_px": outer, "rotated_outer_bounds_px": rotated,
        "sampled_footprint_bounds_px": sampled,
        "bounds_order": ["left", "top", "right", "bottom"],
        "canvas_limits_px": [0, 0, canvas.width, canvas.height],
        "overshoot_px": {
            "left": max(0, -min(box[0] for box in bounds)),
            "top": max(0, -min(box[1] for box in bounds)),
            "right": max(0, max(box[2] for box in bounds) - canvas.width),
            "bottom": max(0, max(box[3] for box in bounds) - canvas.height),
        },
        "safe_box_position_normalized": ranges if fits else None,
        "range_note": (
            "Conservative inclusive x/y ranges for this size, border and rotation, "
            "including pixel rounding and rotation sampling clearance. "
            "Null means no safe positive-pixel placement at this size."
        ),
    })


def resolve_layout(
    layout: InputLayout, photos: list[Photo], version: int
) -> ResolvedLayout:
    by_id = {photo.photo_id: photo for photo in photos}
    if {layer.photo_id for layer in layout.layers} != set(by_id) or len(
        layout.layers
    ) != len(photos):
        raise CollageError("Each imported photo must appear exactly once in the layout.")

    resolved = []
    canvas = layout.canvas
    for layer in layout.layers:
        photo = by_id[layer.photo_id]
        box = layer.box
        x, y, width = (Fraction(str(value)) for value in (box.x, box.y, box.width))
        border_width = layer.border.width_px if layer.border is not None else 0
        photo_width = width * canvas.width - 2 * border_width
        if photo_width <= 0:
            raise CollageError(f"Photo {layer.photo_id} border leaves no positive photo area.")
        if layer.mode == "whole":
            height = (
                photo_width * photo.height / photo.width + 2 * border_width
            ) / canvas.height
        else:
            height = Fraction(str(layer.box.height))
            if height * canvas.height - 2 * border_width <= 0:
                raise CollageError(
                    f"Photo {layer.photo_id} border leaves no positive photo area."
                )
        if x + width > 1 or y + height > 1:
            raise _bounds_error(
                f"Photo {layer.photo_id} extends beyond the canvas.",
                layer, photo, canvas, height,
            )
        (
            pixel_x, pixel_y, pixel_width, pixel_height,
            photo_pixel_width, photo_pixel_height,
        ) = _pixel_frame(layer, photo, canvas, height)
        if photo_pixel_width <= 0:
            raise CollageError(f"Photo {layer.photo_id} rounds to zero photo pixels.")
        if photo_pixel_height <= 0:
            raise CollageError(f"Photo {layer.photo_id} rounds to zero photo pixels.")
        if (
            pixel_x + pixel_width > canvas.width
            or pixel_y + pixel_height > canvas.height
        ):
            raise _bounds_error(
                f"Photo {layer.photo_id} exceeds the pixel canvas bounds.",
                layer, photo, canvas, height,
            )
        max_radius = min(photo_pixel_width, photo_pixel_height) // 2
        if layer.corner_radius_px > max_radius:
            raise CollageError(
                f"Photo {layer.photo_id} corner_radius_px exceeds half the smaller "
                f"photo dimension (maximum {max_radius}px)."
            )
        rotated_box = None
        if layer.rotation_degrees != 0:
            left, top, right, bottom = _rotated_bounds(
                float(x * canvas.width), float(y * canvas.height),
                float(width * canvas.width), float(height * canvas.height),
                layer.rotation_degrees,
            )
            if left < 0 or top < 0 or right > canvas.width or bottom > canvas.height:
                raise _bounds_error(
                    f"Photo {layer.photo_id} rotated frame extends beyond the canvas. "
                    "Explicitly move or resize its untilted box.",
                    layer, photo, canvas, height,
                )
            left, top, right, bottom = _rotated_bounds(
                pixel_x, pixel_y, pixel_width, pixel_height,
                layer.rotation_degrees, padding=ROTATION_PADDING,
            )
            rotated_x, rotated_y = floor(left), floor(top)
            rotated_right, rotated_bottom = ceil(right), ceil(bottom)
            if (
                rotated_x < 0 or rotated_y < 0
                or rotated_right > canvas.width or rotated_bottom > canvas.height
            ):
                raise _bounds_error(
                    f"Photo {layer.photo_id} rotated pixel footprint, including its "
                    "sampling margin, exceeds the canvas bounds. "
                    "Explicitly move or resize its untilted box.",
                    layer, photo, canvas, height,
                )
            rotated_box = PixelBox(
                x=rotated_x, y=rotated_y,
                width=rotated_right - rotated_x, height=rotated_bottom - rotated_y,
            )
        resolved.append(
            LayerGeometry(
                photo_id=layer.photo_id,
                box_normalized=FrameBox(x=box.x, y=box.y, width=box.width, height=float(height)),
                box_pixels=PixelBox(
                    x=pixel_x, y=pixel_y, width=pixel_width, height=pixel_height,
                ),
                photo_box_pixels=PixelBox(
                    x=pixel_x + border_width, y=pixel_y + border_width,
                    width=photo_pixel_width, height=photo_pixel_height,
                ),
                source_crop=(
                    resolve_source_crop(photo, photo_pixel_width, photo_pixel_height, layer.crop)
                    if layer.mode == "cover" else None
                ),
                rotated_box_pixels=rotated_box,
            )
        )
    return ResolvedLayout(
        schema_version=2, version=version, recipe=layout, geometry=resolved,
    )
