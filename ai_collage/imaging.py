"""Whole-photo decoding, deterministic geometry, and rendering."""

import warnings
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

from .models import (
    MAX_FILE_BYTES,
    MAX_IMAGE_PIXELS,
    CollageError,
    InputLayout,
    Photo,
    ResolvedLayout,
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
        height = width * canvas.width * photo.height / (canvas.height * photo.width)
        if x + width > 1 or y + height > 1:
            raise CollageError(f"Element {element.id} extends beyond the canvas.")
        pixel_width = round_half_up(width * canvas.width)
        pixel_height = round_half_up(Fraction(pixel_width * photo.height, photo.width))
        pixel_x = round_half_up(x * canvas.width)
        pixel_y = round_half_up(y * canvas.height)
        if pixel_width == 0 or pixel_height == 0:
            raise CollageError(f"Element {element.id} rounds to zero pixels.")
        if (
            pixel_x + pixel_width > canvas.width
            or pixel_y + pixel_height > canvas.height
        ):
            raise CollageError(f"Element {element.id} exceeds the pixel canvas bounds.")
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
        for element in sorted(layout.elements, key=lambda item: item.z_index):
            photo = by_id[element.source_image_id]
            image, _ = load_photo(paths[photo.source_image_id])
            with image:
                if image.size != (photo.width, photo.height):
                    raise CollageError(
                        f"Photo {photo.source_image_id} dimensions differ from project metadata."
                    )
                box = element.box_pixels
                with image.resize(
                    (box.width, box.height), Image.Resampling.LANCZOS
                ) as resized:
                    canvas.paste(resized, (box.x, box.y), resized)
        canvas.save(output, format="PNG")
