"""Photo decoding, deterministic frame/crop geometry, and rendering."""

import warnings
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps, UnidentifiedImageError

from .models import (
    MAX_FILE_BYTES,
    MAX_IMAGE_PIXELS,
    Border,
    CollageError,
    Framing,
    InputLayout,
    Photo,
    ResolvedLayout,
    SourceCrop,
)


def load_photo(path: Path) -> tuple[Image.Image, str]:
    """Return an oriented RGBA image and canonical extension; caller closes it."""
    if path.stat().st_size > MAX_FILE_BYTES:
        raise CollageError(f"{path}: photo exceeds the 25 MiB file limit.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as source:
                extension = {"JPEG": ".jpg", "PNG": ".png"}.get(source.format)
                if extension is None:
                    raise CollageError(f"{path}: only JPEG and PNG photos are supported.")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise CollageError(
                        f"{path}: photo exceeds {MAX_IMAGE_PIXELS:,} decoded pixels."
                    )
                if getattr(source, "n_frames", 1) != 1:
                    raise CollageError(f"{path}: animated/multiframe images are unsupported.")
                source.load()
                with ImageOps.exif_transpose(source) as oriented:
                    return oriented.convert("RGBA"), extension
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as exc:
        raise CollageError(f"{path}: cannot decode photo: {exc}") from exc


def round_half_up(value: Fraction) -> int:
    return (2 * value.numerator + value.denominator) // (2 * value.denominator)


def resolve_source_crop(
    photo: Photo, width: int, height: int, framing: Framing
) -> SourceCrop:
    scale = max(Fraction(width, photo.width), Fraction(height, photo.height))
    scale *= Fraction(str(framing.zoom))
    crop_width, crop_height = Fraction(width) / scale, Fraction(height) / scale
    left = (photo.width - crop_width) * Fraction(str(framing.pan_x))
    top = (photo.height - crop_height) * Fraction(str(framing.pan_y))
    return SourceCrop(
        left=float(left),
        top=float(top),
        right=float(left + crop_width),
        bottom=float(top + crop_height),
    )


def resolve_layout(
    layout: InputLayout, photos: list[Photo], version: int
) -> ResolvedLayout:
    by_id = {photo.source_image_id: photo for photo in photos}
    elements = layout.elements
    if {element.source_image_id for element in elements} != set(by_id) or len(
        elements
    ) != len(photos):
        raise CollageError("Each imported photo must appear exactly once in the layout.")
    if len({element.id for element in elements}) != len(elements):
        raise CollageError("Element IDs must be unique.")
    if len({element.z_index for element in elements}) != len(elements):
        raise CollageError("z_index values must be unique.")

    resolved = []
    canvas = layout.canvas
    for element in elements:
        photo = by_id[element.source_image_id]
        box = element.box_normalized
        x, y, width = (Fraction(str(value)) for value in (box.x, box.y, box.width))
        border_width = element.border.width_px if element.border is not None else 0
        photo_width = width * canvas.width - 2 * border_width
        if photo_width <= 0:
            raise CollageError(f"Element {element.id} border leaves no positive photo area.")
        if element.framing is None:
            height = (
                photo_width * photo.height / photo.width + 2 * border_width
            ) / canvas.height
        else:
            if box.height is None:
                raise CollageError(f"Element {element.id} cover mode requires an outer height.")
            height = Fraction(str(box.height))
            if height * canvas.height - 2 * border_width <= 0:
                raise CollageError(f"Element {element.id} border leaves no positive photo area.")
        if x + width > 1 or y + height > 1:
            raise CollageError(f"Element {element.id} extends beyond the canvas.")
        pixel_width = round_half_up(width * canvas.width)
        photo_pixel_width = pixel_width - 2 * border_width
        if photo_pixel_width <= 0:
            raise CollageError(f"Element {element.id} rounds to zero photo pixels.")
        if element.framing is None:
            photo_pixel_height = round_half_up(
                Fraction(photo_pixel_width * photo.height, photo.width)
            )
        else:
            photo_pixel_height = round_half_up(height * canvas.height) - 2 * border_width
        pixel_height = photo_pixel_height + 2 * border_width
        pixel_x = round_half_up(x * canvas.width)
        pixel_y = round_half_up(y * canvas.height)
        if photo_pixel_height <= 0:
            raise CollageError(f"Element {element.id} rounds to zero photo pixels.")
        if (
            pixel_x + pixel_width > canvas.width
            or pixel_y + pixel_height > canvas.height
        ):
            raise CollageError(f"Element {element.id} exceeds the pixel canvas bounds.")
        max_radius = min(photo_pixel_width, photo_pixel_height) // 2
        if element.corner_radius_px > max_radius:
            raise CollageError(
                f"Element {element.id} corner_radius_px exceeds half the smaller "
                f"photo dimension (maximum {max_radius}px)."
            )
        resolved.append(
            {
                **element.model_dump(),
                "box_normalized": {**box.model_dump(), "height": float(height)},
                "box_pixels": {
                    "x": pixel_x,
                    "y": pixel_y,
                    "width": pixel_width,
                    "height": pixel_height,
                },
                "source_crop": (
                    resolve_source_crop(
                        photo, photo_pixel_width, photo_pixel_height, element.framing
                    ).model_dump()
                    if element.framing is not None
                    else None
                ),
            }
        )
    return ResolvedLayout.model_validate(
        {
            "schema_version": layout.schema_version,
            "version": version,
            "canvas": canvas.model_dump(),
            "elements": resolved,
        }
    )


def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 255)
    scale = 4
    # Supersample only one corner, not an enlarged full-frame image.
    with Image.new("L", (radius * scale, radius * scale), 0) as large_corner:
        ImageDraw.Draw(large_corner).ellipse(
            (0, 0, 2 * radius * scale - 1, 2 * radius * scale - 1), fill=255
        )
        with large_corner.resize((radius, radius), Image.Resampling.LANCZOS) as corner:
            width, height = size
            mask.paste(corner, (0, 0))
            for operation, position in [
                (Image.Transpose.FLIP_LEFT_RIGHT, (width - radius, 0)),
                (Image.Transpose.FLIP_TOP_BOTTOM, (0, height - radius)),
                (Image.Transpose.ROTATE_180, (width - radius, height - radius)),
            ]:
                with corner.transpose(operation) as mirrored:
                    mask.paste(mirrored, position)
    return mask


def _rounded_frame(
    photo: Image.Image, radius: int, border: Border | None
) -> Image.Image:
    inset = border.width_px if border is not None else 0
    size = (photo.width + 2 * inset, photo.height + 2 * inset)
    photo_bounds = (inset, inset, inset + photo.width, inset + photo.height)
    with (
        _rounded_mask(size, radius + inset) as outer_mask,
        Image.new("L", size, 0) as inner_mask,
        Image.new("RGBA", size, border.color if border is not None else (0, 0, 0, 0)) as layer,
    ):
        with _rounded_mask(photo.size, radius) as photo_mask:
            inner_mask.paste(photo_mask, (inset, inset))
        with ImageChops.darker(inner_mask, outer_mask) as contained_inner:
            with (
                contained_inner.crop(photo_bounds) as photo_mask,
                photo.getchannel("A") as alpha,
                ImageChops.multiply(alpha, photo_mask) as clipped_alpha,
            ):
                photo.putalpha(clipped_alpha)
            with ImageChops.subtract(outer_mask, contained_inner) as border_mask:
                layer.putalpha(border_mask)
        # Add complementary premultiplied coverage; compositing it would leave a seam.
        with layer.convert("RGBa") as frame, photo.convert("RGBa") as foreground:
            with (
                frame.crop(photo_bounds) as border_corner,
                ImageChops.add(border_corner, foreground) as combined,
            ):
                frame.paste(combined, (inset, inset))
            return frame.convert("RGBA")


def render_layout(
    layout: ResolvedLayout,
    photos: list[Photo],
    paths: dict[int, Path],
    output: Path,
) -> None:
    by_id = {photo.source_image_id: photo for photo in photos}
    with Image.new(
        "RGB",
        (layout.canvas.width, layout.canvas.height),
        layout.canvas.background.value,
    ) as canvas:
        draw = ImageDraw.Draw(canvas)
        for element in sorted(layout.elements, key=lambda item: item.z_index):
            photo = by_id[element.source_image_id]
            image, _ = load_photo(paths[photo.source_image_id])
            with image:
                if image.size != (photo.width, photo.height):
                    raise CollageError(
                        f"Photo {photo.source_image_id} dimensions differ from project metadata."
                    )
                if (
                    element.corner_radius_px == 0
                    and element.border is not None
                    and element.border.width_px > 0
                ):
                    outer = element.box_pixels
                    draw.rectangle(
                        (
                            outer.x,
                            outer.y,
                            outer.x + outer.width - 1,
                            outer.y + outer.height - 1,
                        ),
                        outline=element.border.color,
                        width=element.border.width_px,
                    )
                box = element.photo_box_pixels
                crop = element.source_crop
                source_box = (
                    (crop.left, crop.top, crop.right, crop.bottom)
                    if crop is not None else None
                )
                with image.resize(
                    (box.width, box.height), Image.Resampling.LANCZOS, box=source_box
                ) as resized:
                    if element.corner_radius_px > 0:
                        with _rounded_frame(
                            resized, element.corner_radius_px, element.border
                        ) as rounded:
                            outer = element.box_pixels
                            canvas.paste(rounded, (outer.x, outer.y), rounded)
                    else:
                        canvas.paste(resized, (box.x, box.y), resized)
        canvas.save(output, format="PNG")
