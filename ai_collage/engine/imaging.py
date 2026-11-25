"""Bounded photo decoding and alpha-aware frame rendering."""

import warnings
from math import cos, radians, sin
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps, UnidentifiedImageError

from .geometry import ROTATION_PADDING
from .models import (
    MAX_FILE_BYTES,
    MAX_IMAGE_PIXELS,
    Border,
    CollageError,
    Photo,
    PhotoMediaError,
    PhotoSizeError,
    PixelBox,
    ResolvedLayout,
)


def load_photo(path: Path) -> tuple[Image.Image, str]:
    """Return an oriented RGBA image and canonical extension; caller closes it."""
    if path.stat().st_size > MAX_FILE_BYTES:
        raise PhotoSizeError(f"{path}: photo exceeds the 25 MiB file limit.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as source:
                extension = {"JPEG": ".jpg", "PNG": ".png"}.get(source.format)
                if extension is None:
                    raise PhotoMediaError(f"{path}: only JPEG and PNG photos are supported.")
                if source.width * source.height > MAX_IMAGE_PIXELS:
                    raise PhotoSizeError(
                        f"{path}: photo exceeds {MAX_IMAGE_PIXELS:,} decoded pixels."
                    )
                if getattr(source, "n_frames", 1) != 1:
                    raise PhotoMediaError(f"{path}: animated/multiframe images are unsupported.")
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


def _framed_photo(
    photo: Image.Image, radius: int, border: Border | None
) -> Image.Image:
    if radius > 0:
        return _rounded_frame(photo, radius, border)
    inset = border.width_px if border is not None else 0
    frame = Image.new("RGBA", (photo.width + 2 * inset, photo.height + 2 * inset))
    if inset > 0 and border is not None:
        ImageDraw.Draw(frame).rectangle(
            (0, 0, frame.width - 1, frame.height - 1),
            outline=border.color, width=inset,
        )
    frame.paste(photo, (inset, inset))
    return frame


def _rotate_frame(
    frame: Image.Image, box: PixelBox, footprint: PixelBox, degrees: float
) -> Image.Image:
    angle = radians(degrees)
    c, s = cos(angle), sin(angle)
    dx = footprint.x - box.x - box.width / 2
    dy = footprint.y - box.y - box.height / 2
    # Map output pixel centers back around the unchanged, possibly half-pixel center.
    transform = (
        c, s, frame.width / 2 + ROTATION_PADDING + c * dx + s * dy,
        -s, c, frame.height / 2 + ROTATION_PADDING - s * dx + c * dy,
    )
    # Transparent padding lets bicubic sampling blend edges instead of clamping them.
    with ImageOps.expand(frame, border=ROTATION_PADDING, fill=(0, 0, 0, 0)) as padded:
        return padded.transform(
            (footprint.width, footprint.height), Image.Transform.AFFINE,
            transform, Image.Resampling.BICUBIC, fillcolor=(0, 0, 0, 0),
        )


def render_layout(
    layout: ResolvedLayout,
    photos: list[Photo],
    paths: dict[int, Path],
    output: Path,
) -> None:
    by_id = {photo.photo_id: photo for photo in photos}
    with Image.new(
        "RGB",
        (layout.recipe.canvas.width, layout.recipe.canvas.height),
        layout.recipe.canvas.background,
    ) as canvas:
        for layer, geometry in zip(layout.recipe.layers, layout.geometry, strict=True):
            photo = by_id[layer.photo_id]
            image, _ = load_photo(paths[photo.photo_id])
            with image:
                if image.size != (photo.width, photo.height):
                    raise CollageError(
                        f"Photo {photo.photo_id} dimensions differ from project metadata."
                    )
                box = geometry.photo_box_pixels
                crop = geometry.source_crop
                source_box = (
                    (crop.left, crop.top, crop.right, crop.bottom)
                    if crop is not None else None
                )
                with image.resize(
                    (box.width, box.height), Image.Resampling.LANCZOS, box=source_box
                ) as resized:
                    with _framed_photo(resized, layer.corner_radius_px, layer.border) as frame:
                        if layer.rotation_degrees != 0:
                            footprint = geometry.rotated_box_pixels
                            if footprint is None:
                                raise CollageError(
                                    f"Photo {layer.photo_id} lacks its rotated pixel footprint."
                                )
                            with _rotate_frame(
                                frame, geometry.box_pixels, footprint, layer.rotation_degrees
                            ) as tilted:
                                canvas.paste(tilted, (footprint.x, footprint.y), tilted)
                        else:
                            outer = geometry.box_pixels
                            canvas.paste(frame, (outer.x, outer.y), frame)
        canvas.save(output, format="PNG")
