import copy
import json
import math
import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw
from pydantic import ValidationError

from ai_collage import imaging as imaging_module
from ai_collage import projects as project_module
from ai_collage.imaging import load_photo, resolve_layout
from ai_collage.models import MAX_FILE_BYTES, CollageError, InputLayout
from ai_collage.projects import ProjectStore, read_json

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def forbid_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Offline tests must not open network connections.")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)


@pytest.fixture
def store(tmp_path):
    return ProjectStore(tmp_path / "data")


def photo_file(path, size=(40, 20), color="red", **save_options):
    with Image.new("RGB", size, color) as image:
        image.save(path, **save_options)
    return path


@pytest.fixture
def sources(tmp_path):
    return [
        photo_file(tmp_path / "one.png", (40, 20), "red"),
        photo_file(tmp_path / "two.png", (20, 40), "blue"),
    ]


def layout_data(width=100, height=100):
    return {
        "schema_version": 1,
        "canvas": {
            "width": width,
            "height": height,
            "background": {"type": "color", "value": "#FFFFFF"},
        },
        "elements": [
            {
                "id": 10,
                "type": "image",
                "source_image_id": 1,
                "box_normalized": {"x": 0.05, "y": 0.1, "width": 0.2},
                "z_index": 1,
            },
            {
                "id": 20,
                "type": "image",
                "source_image_id": 2,
                "box_normalized": {"x": 0.5, "y": 0.1, "width": 0.2},
                "z_index": 2,
            },
        ],
    }


def write_layout(tmp_path, data=None):
    path = tmp_path / "input.json"
    path.write_text(json.dumps(data if data is not None else layout_data()), encoding="utf-8")
    return path


def framed_layout_data(width=100, height=100):
    data = layout_data(width, height)
    for element in data["elements"]:
        element["box_normalized"]["height"] = 0.2
        element["framing"] = {"mode": "cover"}
    return data


def rounded_layout_data(framed=False, border_width=5):
    data = framed_layout_data() if framed else layout_data()
    front, back = data["elements"]
    front["box_normalized"] = {"x": 0.2, "y": 0.2, "width": 0.6}
    back["box_normalized"] = {"x": 0.1, "y": 0.1, "width": 0.8}
    if framed:
        front["box_normalized"]["height"] = 0.6
        back["box_normalized"]["height"] = 0.8
    front.update(z_index=2, corner_radius_px=10)
    back["z_index"] = 1
    if border_width:
        front["border"] = {"width_px": border_width, "color": "#FFFFFF"}
    return data


@pytest.mark.parametrize("canvas", [(100, 100), (200, 100), (100, 200)])
@pytest.mark.parametrize("border_width", [0, 2])
def test_geometry_and_whole_photo_corners(
    store, sources, tmp_path, canvas, border_width
):
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    for path in sources:
        with Image.open(path) as source:
            image = source.copy()
        with image:
            draw = ImageDraw.Draw(image)
            w, h = image.size
            for rectangle, color in zip(
                [(0, 0, 9, 9), (w - 10, 0, w - 1, 9),
                 (0, h - 10, 9, h - 1), (w - 10, h - 10, w - 1, h - 1)],
                colors,
                strict=True,
            ):
                draw.rectangle(rectangle, fill=color)
            image.save(path)
    project = store.create("corners", sources)
    data = layout_data(*canvas)
    if border_width:
        for element in data["elements"]:
            element["border"] = {"width_px": border_width, "color": "#00FF00"}
    resolved, output = store.apply_layout("corners", write_layout(tmp_path, data))
    with Image.open(output) as image:
        assert image.size == canvas
        assert image.getpixel((0, 0)) == (255, 255, 255)
        for element, photo in zip(resolved.elements, project.photos, strict=True):
            outer = element.box_pixels
            box = element.photo_box_pixels
            assert outer.width == canvas[0] // 5
            assert box.width == outer.width - 2 * border_width
            assert box.height == box.width * photo.height // photo.width
            assert outer.height == box.height + 2 * border_width
            assert element.box_normalized.height == pytest.approx(
                outer.height / canvas[1]
            )
            points = [(box.x + 1, box.y + 1),
                      (box.x + box.width - 2, box.y + 1),
                      (box.x + 1, box.y + box.height - 2),
                      (box.x + box.width - 2, box.y + box.height - 2)]
            for point, expected in zip(points, colors, strict=True):
                actual = image.getpixel(point)
                assert all(abs(a - b) <= 15 for a, b in zip(actual, expected, strict=True))


@pytest.mark.parametrize("border_width", [0, 2])
@pytest.mark.parametrize("framed", [False, True])
def test_exif_orientation_is_used_for_metadata_and_rendering(
    store, tmp_path, border_width, framed
):
    path = tmp_path / "rotated.jpg"
    with Image.new("RGB", (40, 20), "red") as image:
        ImageDraw.Draw(image).rectangle((20, 0, 39, 19), fill="blue")
        exif = Image.Exif()
        exif[274] = 6
        image.save(path, exif=exif, quality=100, subsampling=0)
    original = path.read_bytes()
    project = store.create("exif", [path, photo_file(tmp_path / "other.png")])
    assert (project.photos[0].width, project.photos[0].height) == (20, 40)
    data = framed_layout_data() if framed else layout_data()
    data["elements"][0]["border"] = {"width_px": border_width, "color": "#00FF00"}
    resolved, output = store.apply_layout("exif", write_layout(tmp_path, data))
    box = resolved.elements[0].photo_box_pixels
    with Image.open(output) as rendered:
        assert rendered.getpixel((box.x + box.width // 2, box.y + box.height // 8))[0] > 240
        assert rendered.getpixel((box.x + box.width // 2, box.y + box.height * 7 // 8))[2] > 240
    assert path.read_bytes() == original


def test_overlap_uses_z_order_without_renaming_photos(store, sources, tmp_path):
    store.create("overlap", sources)
    data = layout_data()
    data["elements"][1]["box_normalized"] = {"x": 0.05, "y": 0.1, "width": 0.2}
    data["elements"][0]["z_index"] = 9
    data["elements"][1]["z_index"] = -2
    resolved, output = store.apply_layout("overlap", write_layout(tmp_path, data))
    assert [element.source_image_id for element in resolved.elements] == [1, 2]
    with Image.open(output) as image:
        assert image.getpixel((10, 15)) == (255, 0, 0)
        assert image.getpixel((10, 40)) == (0, 0, 255)


def test_transparent_png_is_composited_over_solid_background(store, tmp_path):
    path = tmp_path / "alpha.png"
    with Image.new("RGBA", (40, 20), (255, 0, 0, 128)) as image:
        image.save(path)
    store.create("alpha", [path, photo_file(tmp_path / "opaque.png")])
    _, output = store.apply_layout("alpha", write_layout(tmp_path))
    with Image.open(output) as image:
        assert image.getpixel((10, 15)) == (255, 127, 127)


def test_border_outer_geometry_and_exact_ring_pixels(store, sources, tmp_path):
    store.create("borders", sources)
    data = layout_data()
    colors = ["#00FF00", "#FFFF00"]
    for element, color in zip(data["elements"], colors, strict=True):
        element["border"] = {"width_px": 2, "color": color}
    resolved, output = store.apply_layout("borders", write_layout(tmp_path, data))
    assert resolved.elements[0].box_pixels.model_dump() == {
        "x": 5, "y": 10, "width": 20, "height": 12
    }
    assert resolved.elements[0].photo_box_pixels.model_dump() == {
        "x": 7, "y": 12, "width": 16, "height": 8
    }
    assert resolved.elements[1].box_pixels.model_dump() == {
        "x": 50, "y": 10, "width": 20, "height": 36
    }
    with Image.open(output) as image:
        for element, photo_color, border_color in zip(
            resolved.elements, [(255, 0, 0), (0, 0, 255)],
            [(0, 255, 0), (255, 255, 0)], strict=True,
        ):
            outer = element.box_pixels
            for y in range(outer.height):
                for x in range(outer.width):
                    is_photo = 2 <= x < outer.width - 2 and 2 <= y < outer.height - 2
                    assert image.getpixel((outer.x + x, outer.y + y)) == (
                        photo_color if is_photo else border_color
                    )
            for point in [
                (outer.x - 1, outer.y), (outer.x, outer.y - 1),
                (outer.x + outer.width, outer.y), (outer.x, outer.y + outer.height),
            ]:
                assert image.getpixel(point) == (255, 255, 255)


def test_border_rounding_uses_outer_width_before_photo_ratio(store, tmp_path):
    sources = [photo_file(tmp_path / f"{n}.png", (4, 3)) for n in (1, 2)]
    project = store.create("border-rounding", sources)
    data = layout_data(10, 10)
    data["elements"][0]["box_normalized"] = {"x": 0.05, "y": 0.05, "width": 0.45}
    data["elements"][0]["border"] = {"width_px": 1, "color": "#FFFFFF"}
    resolved = resolve_layout(InputLayout.model_validate(data), project.photos, 1)
    element = resolved.elements[0]
    assert element.box_normalized.height == 0.3875
    assert element.box_pixels.model_dump() == {
        "x": 1, "y": 1, "width": 5, "height": 4
    }
    assert element.photo_box_pixels.model_dump() == {
        "x": 2, "y": 2, "width": 3, "height": 2
    }


def test_border_may_touch_canvas_edges_without_clipping(store, sources, tmp_path):
    store.create("edge-borders", sources)
    data = layout_data()
    for element, y in zip(data["elements"], [0.88, 0.64], strict=True):
        element["box_normalized"] = {"x": 0.8, "y": y, "width": 0.2}
        element["border"] = {"width_px": 2, "color": "#00FF00"}
    resolved, output = store.apply_layout("edge-borders", write_layout(tmp_path, data))
    for element in resolved.elements:
        outer = element.box_pixels
        assert outer.x + outer.width == 100
        assert outer.y + outer.height == 100
    with Image.open(output) as image:
        assert image.getpixel((99, 99)) == (0, 255, 0)


@pytest.mark.parametrize(
    "box, message",
    [
        ({"x": 0.05, "y": 0.89, "width": 0.2}, "beyond the canvas"),
        ({"x": 0.795, "y": 0, "width": 0.205}, "pixel canvas bounds"),
    ],
)
def test_border_bounds_failures_preserve_accepted_state(
    store, sources, tmp_path, box, message
):
    store.create("border-bounds", sources)
    path = write_layout(tmp_path)
    store.apply_layout("border-bounds", path)
    directory = store.project_dir("border-bounds")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    data = layout_data()
    data["elements"][0]["box_normalized"] = box
    data["elements"][0]["border"] = {"width_px": 2, "color": "#FFFFFF"}
    with pytest.raises(CollageError, match=message):
        store.apply_layout("border-bounds", write_layout(tmp_path, data))
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize(
    "size, width, border_width",
    [((40, 20), 0.201, 10), ((40, 1), 0.05, 2)],
)
def test_border_rejects_photo_area_that_rounds_to_zero(
    store, tmp_path, size, width, border_width
):
    sources = [
        photo_file(tmp_path / "thin.png", size),
        photo_file(tmp_path / "other.png"),
    ]
    store.create("tiny-border", sources)
    data = layout_data()
    data["elements"][0]["box_normalized"]["width"] = width
    data["elements"][0]["border"] = {"width_px": border_width, "color": "#FFFFFF"}
    with pytest.raises(CollageError, match="zero photo pixels"):
        store.apply_layout("tiny-border", write_layout(tmp_path, data))
    assert store.load("tiny-border").current_version is None


@pytest.mark.parametrize("alpha, expected", [(0, (255, 255, 255)), (128, (255, 127, 127))])
@pytest.mark.parametrize("framed", [False, True])
def test_border_does_not_fill_transparent_photo_interior(
    store, tmp_path, alpha, expected, framed
):
    path = tmp_path / "alpha-border.png"
    with Image.new("RGBA", (40, 20), (255, 0, 0, alpha)) as image:
        image.save(path)
    store.create("alpha-border", [path, photo_file(tmp_path / "other.png")])
    data = framed_layout_data() if framed else layout_data()
    data["elements"][0]["border"] = {"width_px": 2, "color": "#00FF00"}
    _, output = store.apply_layout("alpha-border", write_layout(tmp_path, data))
    with Image.open(output) as image:
        assert image.getpixel((5, 10)) == (0, 255, 0)
        assert image.getpixel((10, 15)) == expected


@pytest.mark.parametrize("foreground", [1, 2])
@pytest.mark.parametrize("radius", [0, 2])
def test_photo_and_border_share_one_stacking_layer(store, tmp_path, foreground, radius):
    sources = [
        photo_file(tmp_path / "back.png", (20, 20), "red"),
        photo_file(tmp_path / "front.png", (20, 20), "blue"),
    ]
    store.create("layered-borders", sources)
    data = layout_data()
    data["elements"][0]["box_normalized"] = {"x": 0.1, "y": 0.1, "width": 0.5}
    data["elements"][0]["border"] = {"width_px": 3, "color": "#00FF00"}
    data["elements"][1]["box_normalized"] = {"x": 0.4, "y": 0.3, "width": 0.3}
    data["elements"][1]["border"] = {"width_px": 2, "color": "#FFFF00"}
    for element in data["elements"]:
        element["corner_radius_px"] = radius
    if foreground == 1:
        data["elements"][0]["z_index"] = 3
    _, output = store.apply_layout("layered-borders", write_layout(tmp_path, data))
    with Image.open(output) as image:
        assert image.getpixel((10, 15)) == (0, 255, 0)
        assert image.getpixel((20, 20)) == (255, 0, 0)
        assert image.getpixel((65, 40)) == (0, 0, 255)
        if foreground == 2:
            assert image.getpixel((40, 40)) == (255, 255, 0)
            assert image.getpixel((58, 40)) == (0, 0, 255)
            assert image.getpixel((58, 30)) == (255, 255, 0)
        else:
            assert image.getpixel((40, 40)) == (255, 0, 0)
            assert image.getpixel((58, 40)) == (0, 255, 0)


def test_legacy_and_zero_border_snapshots_preserve_output(store, sources, tmp_path):
    store.create("legacy-border", sources)
    data = layout_data()
    resolved, output = store.apply_layout("legacy-border", write_layout(tmp_path, data))
    original_output = output.read_bytes()
    saved_layout = store.version_paths("legacy-border", 1)[0]
    legacy = json.loads(saved_layout.read_text())
    for element in legacy["elements"]:
        element.pop("border", None)
        element.pop("framing", None)
        element.pop("source_crop", None)
        element.pop("corner_radius_px", None)
    saved_layout.write_text(json.dumps(legacy), encoding="utf-8")
    legacy_bytes = saved_layout.read_bytes()
    store.render("legacy-border", 1)
    assert output.read_bytes() == original_output
    assert saved_layout.read_bytes() == legacy_bytes
    for border in [None, {"width_px": 0, "color": "#FF00FF"}]:
        for element in data["elements"]:
            element["border"] = border
        accepted, output = store.apply_layout(
            "legacy-border", write_layout(tmp_path, data)
        )
        assert output.read_bytes() == original_output
        for old, new in zip(resolved.elements, accepted.elements, strict=True):
            assert old.box_pixels == new.box_pixels
            assert old.box_normalized == new.box_normalized
    assert [v["version"] for v in store.inspect("legacy-border")["versions"]] == [1, 2, 3]
    assert saved_layout.read_bytes() == legacy_bytes


def test_inconsistent_saved_border_geometry_is_rejected(store, sources, tmp_path):
    store.create("tampered-border", sources)
    data = layout_data()
    data["elements"][0]["border"] = {"width_px": 2, "color": "#FFFFFF"}
    _, output = store.apply_layout("tampered-border", write_layout(tmp_path, data))
    before = output.read_bytes()
    path = store.version_paths("tampered-border", 1)[0]
    saved = json.loads(path.read_text())
    saved["elements"][0]["border"]["width_px"] = 3
    path.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(CollageError, match="inconsistent"):
        store.render("tampered-border")
    assert output.read_bytes() == before


@pytest.mark.parametrize("axis", ["x", "y"])
@pytest.mark.parametrize("zoom", [1, 4])
@pytest.mark.parametrize("pan, expected_color", [
    (0, (255, 0, 0)), (0.5, (0, 255, 0)), (1, (0, 0, 255)),
])
def test_cover_pan_selects_source_regions_without_moving_frame(
    store, tmp_path, axis, zoom, pan, expected_color
):
    source = tmp_path / "bands.png"
    size = (60, 20) if axis == "x" else (20, 60)
    with Image.new("RGB", size) as image:
        draw = ImageDraw.Draw(image)
        for index, color in enumerate(["red", "lime", "blue"]):
            rectangle = (
                (20 * index, 0, 20 * index + 19, 19)
                if axis == "x" else (0, 20 * index, 19, 20 * index + 19)
            )
            draw.rectangle(rectangle, fill=color)
        image.save(source)
    store.create("pan", [source, photo_file(tmp_path / "other.png")])
    data = framed_layout_data()
    data["elements"][0]["border"] = {"width_px": 2, "color": "#123456"}
    data["elements"][0]["framing"].update(
        zoom=zoom,
        pan_x=pan if axis == "x" else 1 - pan,
        pan_y=pan if axis == "y" else 1 - pan,
    )
    resolved, output = store.apply_layout("pan", write_layout(tmp_path, data))
    element = resolved.elements[0]
    assert element.box_pixels.model_dump() == {
        "x": 5, "y": 10, "width": 20, "height": 20
    }
    crop_size = 20 / zoom
    offset = (60 - crop_size) * pan
    other_offset = (20 - crop_size) * (1 - pan)
    expected_crop = (
        {
            "left": offset, "top": other_offset,
            "right": offset + crop_size, "bottom": other_offset + crop_size,
        }
        if axis == "x"
        else {
            "left": other_offset, "top": offset,
            "right": other_offset + crop_size, "bottom": offset + crop_size,
        }
    )
    assert element.source_crop.model_dump() == expected_crop
    with Image.open(output) as image:
        assert image.getpixel((15, 20)) == expected_color
        assert image.getpixel((5, 10)) == (18, 52, 86)
        inner = element.photo_box_pixels
        for y in range(inner.y, inner.y + inner.height):
            for x in range(inner.x, inner.x + inner.width):
                assert image.getpixel((x, y)) != (255, 255, 255)


@pytest.mark.parametrize("zoom, inset, color", [
    (1, 0, (255, 0, 0)), (2, 10, (0, 255, 0)), (4, 15, (0, 0, 255)),
])
def test_cover_zoom_uses_centered_minimum_fill_scale(
    store, tmp_path, zoom, inset, color
):
    source = tmp_path / "target.png"
    with Image.new("RGB", (40, 40), "red") as image:
        draw = ImageDraw.Draw(image)
        draw.rectangle((10, 10, 29, 29), fill="lime")
        draw.rectangle((15, 15, 24, 24), fill="blue")
        image.save(source)
    store.create("zoom", [source, photo_file(tmp_path / "other.png")])
    data = framed_layout_data()
    data["elements"][0]["framing"]["zoom"] = zoom
    resolved, output = store.apply_layout("zoom", write_layout(tmp_path, data))
    element = resolved.elements[0]
    assert element.source_crop.model_dump() == {
        "left": inset, "top": inset, "right": 40 - inset, "bottom": 40 - inset,
    }
    assert element.box_pixels.width == element.box_pixels.height == 20
    with Image.open(output) as image:
        assert image.getpixel((7, 12)) == color


def test_cover_preserves_shapes_in_an_independently_shaped_frame(store, tmp_path):
    source = tmp_path / "square-marker.png"
    with Image.new("RGB", (40, 20), "black") as image:
        ImageDraw.Draw(image).rectangle((15, 5, 24, 14), fill="red")
        image.save(source)
    store.create("aspect", [source, photo_file(tmp_path / "other.png")])
    data = framed_layout_data()
    data["elements"][0]["box_normalized"]["height"] = 0.3
    resolved, output = store.apply_layout("aspect", write_layout(tmp_path, data))
    box = resolved.elements[0].photo_box_pixels
    assert (box.width, box.height) == (20, 30)
    with Image.open(output) as image:
        points = [
            (x, y) for y in range(box.y, box.y + box.height)
            for x in range(box.x, box.x + box.width)
            if image.getpixel((x, y))[0] >= 128
        ]
    marker_width = max(x for x, _ in points) - min(x for x, _ in points) + 1
    marker_height = max(y for _, y in points) - min(y for _, y in points) + 1
    assert 14 <= marker_width <= 16
    assert 14 <= marker_height <= 16
    assert abs(marker_width - marker_height) <= 1


def test_cover_fractional_pan_and_zoom_use_subpixel_sampling(store, tmp_path):
    source = tmp_path / "gradient.png"
    with Image.new("RGB", (80, 80)) as image:
        image.putdata([(x * 3, y * 3, 0) for y in range(80) for x in range(80)])
        image.save(source)
    store.create("fractional", [source, photo_file(tmp_path / "other.png")])
    data = framed_layout_data()
    data["elements"][0]["framing"].update(zoom=1.5, pan_x=0.25, pan_y=0.75)
    resolved, output = store.apply_layout("fractional", write_layout(tmp_path, data))
    crop = resolved.elements[0].source_crop
    assert crop.left == pytest.approx(20 / 3)
    assert crop.top == 20
    assert crop.right == 60
    assert crop.bottom == pytest.approx(220 / 3)
    with Image.open(output) as image:
        actual = image.getpixel((15, 20))
    assert all(abs(a - b) <= 3 for a, b in zip(actual, (103, 143, 0), strict=True))


@pytest.mark.parametrize("canvas", [(100, 100), (200, 100), (100, 200)])
def test_cover_frames_resolve_on_each_canvas_shape(store, sources, tmp_path, canvas):
    store.create("frame-canvas", sources)
    data = framed_layout_data(*canvas)
    data["elements"][0]["box_normalized"]["height"] = 0.3
    data["elements"][0]["border"] = {"width_px": 2, "color": "#00FF00"}
    resolved, output = store.apply_layout("frame-canvas", write_layout(tmp_path, data))
    element = resolved.elements[0]
    assert element.box_pixels.width == canvas[0] // 5
    assert element.box_pixels.height == canvas[1] * 3 // 10
    inner, crop = element.photo_box_pixels, element.source_crop
    assert (crop.right - crop.left) / (crop.bottom - crop.top) == pytest.approx(
        inner.width / inner.height
    )
    assert 0 <= crop.left < crop.right <= 40
    assert 0 <= crop.top < crop.bottom <= 20
    with Image.open(output) as image:
        assert image.size == canvas


@pytest.mark.parametrize("mutation", [
    lambda d: d["elements"][0]["box_normalized"].pop("height"),
    lambda d: d["elements"][0].update(framing=None),
    lambda d: d["elements"][0]["box_normalized"].update(height=None),
    lambda d: d["elements"][0]["box_normalized"].update(height=0),
    lambda d: d["elements"][0]["box_normalized"].update(height=True),
    lambda d: d["elements"][0]["box_normalized"].update(height=0.00001),
    lambda d: d["elements"][0]["box_normalized"].update(y=0.9),
    lambda d: d["elements"][0]["box_normalized"].update(y=0.795, height=0.205),
    lambda d: d["elements"][0].update(border={"width_px": 10, "color": "#FFFFFF"}),
    lambda d: d["elements"][0].update(border={"width_px": 2, "color": "#FFFFFF"})
    or d["elements"][0]["box_normalized"].update(height=0.04),
    lambda d: d["elements"][0].update(border={"width_px": 2, "color": "#FFFFFF"})
    or d["elements"][0]["box_normalized"].update(height=0.041),
    lambda d: d["elements"][0]["framing"].update(mode="contain"),
    lambda d: d["elements"][0]["framing"].update(zoom=0.99),
    lambda d: d["elements"][0]["framing"].update(zoom=4.01),
    lambda d: d["elements"][0]["framing"].update(zoom=True),
    lambda d: d["elements"][0]["framing"].update(zoom="2"),
    lambda d: d["elements"][0]["framing"].update(zoom=float("nan")),
    lambda d: d["elements"][0]["framing"].update(zoom=float("inf")),
    lambda d: d["elements"][0]["framing"].update(pan_x=-0.01),
    lambda d: d["elements"][0]["framing"].update(pan_y=1.01),
    lambda d: d["elements"][0]["framing"].update(pan_x=True),
    lambda d: d["elements"][0]["framing"].update(pan_y="0.5"),
    lambda d: d["elements"][0]["framing"].update(pan_y=float("nan")),
    lambda d: d["elements"][0]["framing"].update(unknown=0),
    lambda d: d["elements"][0].update(source_crop={"left": 0, "top": 0, "right": 1, "bottom": 1}),
])
def test_invalid_cover_settings_preserve_accepted_state(
    store, sources, tmp_path, mutation
):
    store.create("invalid-cover", sources)
    store.apply_layout("invalid-cover", write_layout(tmp_path))
    directory = store.project_dir("invalid-cover")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    data = framed_layout_data()
    mutation(data)
    with pytest.raises((CollageError, ValidationError)):
        store.apply_layout("invalid-cover", write_layout(tmp_path, data))
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("mutation", [
    lambda d: d["elements"][0]["source_crop"].update(left=11),
    lambda d: d["elements"][0]["source_crop"].update(right=999),
    lambda d: d["elements"][0].pop("source_crop"),
    lambda d: d["elements"][0]["framing"].update(pan_x=0),
    lambda d: d["elements"][0]["box_normalized"].update(height=0.25),
])
def test_inconsistent_saved_cover_geometry_is_rejected(
    store, sources, tmp_path, mutation
):
    store.create("tampered-cover", sources)
    _, output = store.apply_layout(
        "tampered-cover", write_layout(tmp_path, framed_layout_data())
    )
    original_output = output.read_bytes()
    saved_layout = store.version_paths("tampered-cover", 1)[0]
    saved = json.loads(saved_layout.read_text())
    mutation(saved)
    saved_layout.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises((CollageError, ValidationError)):
        store.render("tampered-cover")
    assert output.read_bytes() == original_output


def test_whole_photo_mode_rejects_even_null_input_height(store, sources, tmp_path):
    store.create("null-height", sources)
    data = layout_data()
    data["elements"][0]["box_normalized"]["height"] = None
    with pytest.raises(ValidationError, match="supplied height requires"):
        store.apply_layout("null-height", write_layout(tmp_path, data))


@pytest.mark.parametrize("framed", [False, True])
@pytest.mark.parametrize("border_width", [0, 5])
def test_rounded_corners_reveal_lower_layer_and_keep_concentric_border(
    store, tmp_path, framed, border_width
):
    sources = [
        photo_file(tmp_path / "front.png", (40, 40), "red"),
        photo_file(tmp_path / "back.png", (40, 40), "blue"),
    ]
    original = sources[0].read_bytes()
    store.create("rounded", sources)
    data = rounded_layout_data(framed, border_width)
    resolved, output = store.apply_layout("rounded", write_layout(tmp_path, data))
    element = resolved.elements[0]
    assert element.box_pixels.model_dump() == {
        "x": 20, "y": 20, "width": 60, "height": 60
    }
    assert store.load_layout(store.load("rounded"), 1) == resolved
    with Image.open(output) as image:
        for point in [(20, 20), (79, 20), (20, 79), (79, 79)]:
            assert image.getpixel(point) == (0, 0, 255)
        assert image.getpixel((50, 20)) == (
            (255, 255, 255) if border_width else (255, 0, 0)
        )
        assert image.getpixel((50, 50)) == (255, 0, 0)
        if border_width:
            for point in [(26, 26), (73, 26), (26, 73), (73, 73)]:
                assert all(channel >= 250 for channel in image.getpixel(point))
            inner_edge = [
                image.getpixel((x, y))
                for y in range(27, 34) for x in range(27, 34)
            ]
            assert all(red == 255 and green == blue for red, green, blue in inner_edge)
            assert any(0 < green < 255 for _, green, _ in inner_edge)
            outer_edge = [
                image.getpixel((x, y))
                for y in range(20, 35) for x in range(20, 25)
            ]
            assert any(0 < red < 255 for red, _, _ in outer_edge)
            assert all(red == green and blue == 255 for red, green, blue in outer_edge)
    previous_output = output.read_bytes()
    store.render("rounded")
    assert output.read_bytes() == previous_output
    assert sources[0].read_bytes() == original


@pytest.mark.parametrize("alpha, expected", [
    (0, (0, 0, 255)), (128, (128, 0, 127)),
])
@pytest.mark.parametrize("border_width", [0, 5])
def test_rounded_photo_retains_source_transparency(
    store, tmp_path, alpha, expected, border_width
):
    source = tmp_path / "transparent.png"
    with Image.new("RGBA", (40, 40), (255, 0, 0, alpha)) as image:
        image.save(source)
    store.create("rounded-alpha", [
        source, photo_file(tmp_path / "back.png", (40, 40), "blue")
    ])
    _, output = store.apply_layout(
        "rounded-alpha", write_layout(tmp_path, rounded_layout_data(True, border_width))
    )
    with Image.open(output) as image:
        assert image.getpixel((50, 50)) == expected
        assert image.getpixel((20, 20)) == (0, 0, 255)
        if border_width:
            assert image.getpixel((50, 20)) == (255, 255, 255)


def test_borderless_rounded_edges_are_smooth_and_symmetric(store, tmp_path):
    store.create("rounded-smooth", [
        photo_file(tmp_path / "front.png", (40, 40), "white"),
        photo_file(tmp_path / "back.png", (40, 40), "black"),
    ])
    data = rounded_layout_data(border_width=0)
    _, output = store.apply_layout("rounded-smooth", write_layout(tmp_path, data))
    with Image.open(output) as image:
        pixels = []
        for y in range(10):
            for x in range(10):
                pixel = image.getpixel((20 + x, 20 + y))
                assert pixel == image.getpixel((79 - x, 20 + y))
                assert pixel == image.getpixel((20 + x, 79 - y))
                assert pixel == image.getpixel((79 - x, 79 - y))
                assert pixel[0] == pixel[1] == pixel[2]
                pixels.append(pixel[0])
        assert 0 in pixels and 255 in pixels
        assert any(0 < value < 255 for value in pixels)


@pytest.mark.parametrize("framed", [False, True])
@pytest.mark.parametrize("border_width", [0, 2])
def test_zero_radius_and_legacy_snapshots_preserve_exact_output(
    store, sources, tmp_path, framed, border_width
):
    store.create("legacy-radius", sources)
    data = framed_layout_data() if framed else layout_data()
    for element in data["elements"]:
        element["border"] = {"width_px": border_width, "color": "#00FF00"}
    first, output = store.apply_layout("legacy-radius", write_layout(tmp_path, data))
    expected = output.read_bytes()
    saved_layout = store.version_paths("legacy-radius", 1)[0]
    legacy = json.loads(saved_layout.read_text())
    for element in legacy["elements"]:
        del element["corner_radius_px"]
    saved_layout.write_text(json.dumps(legacy), encoding="utf-8")
    legacy_bytes = saved_layout.read_bytes()
    store.render("legacy-radius")
    assert output.read_bytes() == expected
    assert saved_layout.read_bytes() == legacy_bytes
    for element in data["elements"]:
        element["corner_radius_px"] = 0
    second, output = store.apply_layout("legacy-radius", write_layout(tmp_path, data))
    assert output.read_bytes() == expected
    for old, new in zip(first.elements, second.elements, strict=True):
        assert old.box_pixels == new.box_pixels
        assert old.source_crop == new.source_crop


@pytest.mark.parametrize("radius, error", [
    (-1, ValidationError), (1.5, ValidationError), (True, ValidationError),
    ("10", ValidationError), (None, ValidationError),
    (float("nan"), CollageError), (float("inf"), CollageError),
])
def test_invalid_corner_radius_preserves_accepted_state(
    store, sources, tmp_path, radius, error
):
    store.create("invalid-radius", sources)
    store.apply_layout("invalid-radius", write_layout(tmp_path))
    directory = store.project_dir("invalid-radius")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    data = layout_data()
    data["elements"][0]["corner_radius_px"] = radius
    with pytest.raises(error):
        store.apply_layout("invalid-radius", write_layout(tmp_path, data))
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("framed, border_width, maximum", [
    (False, 0, 5), (False, 2, 4), (True, 0, 10), (True, 2, 8),
])
def test_corner_radius_limit_uses_actual_inset_photo_dimensions(
    store, sources, tmp_path, framed, border_width, maximum
):
    store.create("radius-limit", sources)
    data = framed_layout_data() if framed else layout_data()
    element = data["elements"][0]
    element["border"] = {"width_px": border_width, "color": "#FFFFFF"}
    element["corner_radius_px"] = maximum
    store.apply_layout("radius-limit", write_layout(tmp_path, data))
    directory = store.project_dir("radius-limit")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    element["corner_radius_px"] += 1
    with pytest.raises(CollageError, match="half the smaller photo dimension"):
        store.apply_layout("radius-limit", write_layout(tmp_path, data))
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before


def test_invalid_saved_radius_cannot_replace_accepted_preview(store, sources, tmp_path):
    store.create("tampered-radius", sources)
    data = layout_data()
    data["elements"][0]["corner_radius_px"] = 3
    _, output = store.apply_layout("tampered-radius", write_layout(tmp_path, data))
    previous_output = output.read_bytes()
    saved_layout = store.version_paths("tampered-radius", 1)[0]
    saved = json.loads(saved_layout.read_text())
    saved["elements"][0]["corner_radius_px"] = 999
    saved_layout.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(CollageError, match="corner_radius_px"):
        store.render("tampered-radius")
    assert output.read_bytes() == previous_output


@pytest.mark.parametrize("canvas, size, framed", [
    ((240, 160), (80, 40), False),
    ((160, 240), (81, 41), True),
    ((240, 160), (81, 40), True),
    ((160, 240), (80, 41), False),
])
@pytest.mark.parametrize("angle", [-10, 2.5, 10])
def test_tilt_preserves_corners_size_center_and_physical_angle(
    store, tmp_path, canvas, size, framed, angle
):
    width, height = size
    markers = [(4, 4), (width - 5, 4), (4, height - 5), (width - 5, height - 5)]
    source = tmp_path / "tilt-markers.png"
    with Image.new("RGB", size, "black") as image:
        draw = ImageDraw.Draw(image)
        for (x, y), color in zip(markers, ["red", "lime", "blue", "yellow"], strict=True):
            draw.rectangle((x - 4, y - 4, x + 4, y + 4), fill=color)
        image.save(source)
    original = source.read_bytes()
    store.create("tilt-markers", [source, photo_file(tmp_path / "other.png", color="black")])
    data = framed_layout_data(*canvas) if framed else layout_data(*canvas)
    data["canvas"]["background"]["value"] = "#000000"
    element, other = data["elements"]
    x, y = (canvas[0] - width) // 2, (canvas[1] - height) // 2
    element["box_normalized"] = {
        "x": x / canvas[0], "y": y / canvas[1], "width": width / canvas[0],
    }
    if framed:
        element["box_normalized"]["height"] = height / canvas[1]
    other["box_normalized"] = {"x": 0.02, "y": 0.02, "width": 0.05}
    if framed:
        other["box_normalized"]["height"] = 0.05
    element["rotation_degrees"] = angle
    resolved, output = store.apply_layout("tilt-markers", write_layout(tmp_path, data))
    front = resolved.elements[0]
    assert front.box_pixels.model_dump() == {
        "x": x, "y": y, "width": width, "height": height,
    }
    footprint = front.rotated_box_pixels
    assert footprint.x < x and footprint.y < y
    assert footprint.width > width and footprint.height > height
    with Image.open(output) as image:
        pixels = [
            (px + 0.5, py + 0.5, image.getpixel((px, py)))
            for py in range(footprint.y, footprint.y + footprint.height)
            for px in range(footprint.x, footprint.x + footprint.width)
        ]
    weights = [
        lambda r, g, b: max(0, r - max(g, b)),
        lambda r, g, b: max(0, g - max(r, b)),
        lambda r, g, b: max(0, b - max(r, g)),
        lambda r, g, b: max(0, min(r, g) - b),
    ]
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    for (marker_x, marker_y), weight in zip(markers, weights, strict=True):
        samples = [(px, py, weight(*color)) for px, py, color in pixels]
        mass = sum(value for _, _, value in samples)
        assert mass / 255 == pytest.approx(81, abs=3)
        dx, dy = marker_x + 0.5 - width / 2, marker_y + 0.5 - height / 2
        expected = (x + width / 2 + c * dx - s * dy,
                    y + height / 2 + s * dx + c * dy)
        actual = (sum(px * value for px, _, value in samples) / mass,
                  sum(py * value for _, py, value in samples) / mass)
        assert actual == pytest.approx(expected, abs=0.2)
    assert source.read_bytes() == original


@pytest.mark.parametrize("framed", [False, True])
@pytest.mark.parametrize("side", ["left", "top", "right", "bottom"])
def test_tilt_rejects_all_canvas_edges_without_changing_accepted_state(
    store, sources, tmp_path, framed, side
):
    store.create("tilt-bounds", sources)
    data = framed_layout_data() if framed else layout_data()
    front = data["elements"][0]
    front.update(border={"width_px": 2, "color": "#FFFFFF"}, corner_radius_px=4)
    front["box_normalized"].update(x=0.3, y=0.3)
    if side in {"left", "right"}:
        front["box_normalized"]["x"] = 0 if side == "left" else 0.8
    else:
        front["box_normalized"]["y"] = (
            0 if side == "top" else (0.8 if framed else 0.88)
        )
    store.apply_layout("tilt-bounds", write_layout(tmp_path, data))
    directory = store.project_dir("tilt-bounds")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    front["rotation_degrees"] = 10
    with pytest.raises(CollageError, match="rotated frame.*beyond the canvas"):
        store.apply_layout("tilt-bounds", write_layout(tmp_path, data))
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before


def test_tilt_checks_pixel_rounding_and_sampling_margin_after_continuous_bounds(
    store, sources, tmp_path
):
    store.create("tilt-pixels", sources)
    data = framed_layout_data()
    front = data["elements"][0]
    front["box_normalized"] = {"x": 0.0149, "y": 0.2, "width": 0.4, "height": 0.2}
    front["rotation_degrees"] = 10
    # Ideal left edge is just positive; rounding x down puts the tilted corner outside.
    with pytest.raises(CollageError, match="rotated pixel footprint.*sampling margin"):
        store.apply_layout("tilt-pixels", write_layout(tmp_path, data))
    assert store.load("tilt-pixels").current_version is None
    front["box_normalized"]["x"] = 0.04
    resolved, _ = store.apply_layout("tilt-pixels", write_layout(tmp_path, data))
    assert resolved.elements[0].rotated_box_pixels.x == 0


@pytest.mark.parametrize("alpha, expected", [
    (0, (0, 0, 255)), (128, (128, 0, 127)), (255, (255, 0, 0)),
])
@pytest.mark.parametrize("border_width", [0, 5])
@pytest.mark.parametrize("radius", [0, 10])
def test_tilt_rotates_complete_frame_and_preserves_alpha_and_stacking(
    store, tmp_path, alpha, expected, border_width, radius
):
    source = tmp_path / "tilted-alpha.png"
    with Image.new("RGBA", (40, 40), (255, 0, 0, alpha)) as image:
        image.save(source)
    store.create("tilt-alpha", [
        source, photo_file(tmp_path / "back.png", (40, 40), "blue"),
    ])
    data = rounded_layout_data(framed=True, border_width=border_width)
    front = data["elements"][0]
    front.update(rotation_degrees=10, corner_radius_px=radius)
    _, output = store.apply_layout("tilt-alpha", write_layout(tmp_path, data))
    with Image.open(output) as image:
        assert image.getpixel((50, 50)) == expected
        assert image.getpixel((27, 17)) == (
            (0, 0, 255) if radius else ((255, 255, 255) if border_width else expected)
        )
        if border_width:
            assert image.getpixel((56, 23)) == (255, 255, 255)
        assert image.getpixel((12, 50)) == (0, 0, 255)
    front["z_index"] = 0
    _, output = store.apply_layout("tilt-alpha", write_layout(tmp_path, data))
    with Image.open(output) as image:
        assert all(
            image.getpixel(point) == (0, 0, 255)
            for point in [(50, 50), (27, 17), (56, 23)]
        )


@pytest.mark.parametrize("background", ["#000000", "#FFFFFF"])
def test_tilt_antialiases_edges_without_dark_fringes(store, tmp_path, background):
    store.create("tilt-smooth", [
        photo_file(tmp_path / "white.png", (40, 40), "white"),
        photo_file(tmp_path / "black.png", (40, 40), "black"),
    ])
    data = framed_layout_data(200, 150)
    data["canvas"]["background"]["value"] = background
    front, other = data["elements"]
    front["box_normalized"] = {"x": 0.2, "y": 0.2, "width": 0.4, "height": 0.4}
    front["rotation_degrees"] = -3.5
    other["box_normalized"] = {"x": 0.01, "y": 0.01, "width": 0.05, "height": 0.05}
    resolved, output = store.apply_layout("tilt-smooth", write_layout(tmp_path, data))
    box = resolved.elements[0].rotated_box_pixels
    with Image.open(output) as image:
        pixels = [
            image.getpixel((x, y))
            for y in range(box.y, box.y + box.height)
            for x in range(box.x, box.x + box.width)
        ]
        assert all(r == g == b for r, g, b in pixels)
        if background == "#FFFFFF":
            assert set(pixels) == {(255, 255, 255)}
        else:
            assert (0, 0, 0) in pixels and (255, 255, 255) in pixels
            assert any(0 < r < 255 for r, _, _ in pixels)


@pytest.mark.parametrize("framed, border_width, radius", [
    (False, 0, 0), (False, 2, 2), (True, 0, 3), (True, 2, 3),
])
def test_zero_tilt_and_legacy_snapshots_preserve_exact_output(
    store, sources, tmp_path, framed, border_width, radius
):
    store.create("legacy-tilt", sources)
    data = framed_layout_data() if framed else layout_data()
    for element in data["elements"]:
        element.update(
            border={"width_px": border_width, "color": "#00FF00"},
            corner_radius_px=radius,
        )
    first, output = store.apply_layout("legacy-tilt", write_layout(tmp_path, data))
    expected = output.read_bytes()
    saved_layout = store.version_paths("legacy-tilt", 1)[0]
    legacy = json.loads(saved_layout.read_text())
    for element in legacy["elements"]:
        del element["rotation_degrees"]
        del element["rotated_box_pixels"]
    saved_layout.write_text(json.dumps(legacy), encoding="utf-8")
    legacy_bytes = saved_layout.read_bytes()
    store.render("legacy-tilt", 1)
    assert output.read_bytes() == expected
    assert saved_layout.read_bytes() == legacy_bytes
    for element in data["elements"]:
        element["rotation_degrees"] = 0
    second, output = store.apply_layout("legacy-tilt", write_layout(tmp_path, data))
    assert output.read_bytes() == expected
    assert first.elements == second.elements


@pytest.mark.parametrize("framed", [False, True])
def test_tilt_keeps_framing_and_reopens_reproducibly(store, sources, tmp_path, framed):
    store.create("tilt-persist", sources)
    data = framed_layout_data() if framed else layout_data()
    for element in data["elements"]:
        element.update(
            border={"width_px": 2, "color": "#00FF00"}, corner_radius_px=2,
        )
        if framed:
            element["framing"].update(zoom=2, pan_x=0.25, pan_y=0.75)
    first, first_output = store.apply_layout("tilt-persist", write_layout(tmp_path, data))
    first_layout = store.version_paths("tilt-persist", 1)[0]
    original = (first_layout.read_bytes(), first_output.read_bytes())
    for element, angle in zip(data["elements"], [5.5, -3.25], strict=True):
        element["rotation_degrees"] = angle
    second, output = store.apply_layout("tilt-persist", write_layout(tmp_path, data))
    for old, new in zip(first.elements, second.elements, strict=True):
        assert old.box_pixels == new.box_pixels
        assert old.box_normalized == new.box_normalized
        assert old.photo_box_pixels == new.photo_box_pixels
        assert old.source_crop == new.source_crop
        assert new.rotated_box_pixels is not None
    assert second.as_input() == InputLayout.model_validate(data)
    reopened = ProjectStore(store.data_dir)
    assert reopened.load_layout(reopened.load("tilt-persist"), 2) == second
    expected = output.read_bytes()
    reopened.render("tilt-persist", 2)
    assert output.read_bytes() == expected
    assert (first_layout.read_bytes(), first_output.read_bytes()) == original


@pytest.mark.parametrize("angle, error", [
    (-10.001, ValidationError), (10.001, ValidationError),
    ("5", ValidationError), (True, ValidationError), (None, ValidationError),
    (float("nan"), CollageError), (float("inf"), CollageError),
    (float("-inf"), CollageError),
])
def test_invalid_tilt_preserves_accepted_state(store, sources, tmp_path, angle, error):
    store.create("invalid-tilt", sources)
    store.apply_layout("invalid-tilt", write_layout(tmp_path))
    directory = store.project_dir("invalid-tilt")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    data = layout_data()
    data["elements"][0]["rotation_degrees"] = angle
    with pytest.raises(error):
        store.apply_layout("invalid-tilt", write_layout(tmp_path, data))
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("mutation", [
    lambda e: e["rotated_box_pixels"].update(x=99),
    lambda e: e.pop("rotated_box_pixels"),
    lambda e: e.update(rotation_degrees=0),
])
def test_inconsistent_saved_tilt_geometry_preserves_preview(
    store, sources, tmp_path, mutation
):
    store.create("tampered-tilt", sources)
    data = framed_layout_data()
    data["elements"][0].update(
        rotation_degrees=5.5, corner_radius_px=2,
        border={"width_px": 2, "color": "#FFFFFF"},
        framing={"mode": "cover", "zoom": 1.5, "pan_x": 0.25, "pan_y": 0.75},
    )
    resolved, output = store.apply_layout("tampered-tilt", write_layout(tmp_path, data))
    assert resolved.as_input() == InputLayout.model_validate(data)
    original_output = output.read_bytes()
    saved_layout = store.version_paths("tampered-tilt", 1)[0]
    saved = json.loads(saved_layout.read_text())
    mutation(saved["elements"][0])
    saved_layout.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises((CollageError, ValidationError)):
        store.render("tampered-tilt")
    assert output.read_bytes() == original_output


def test_rotation_failure_preserves_accepted_state_and_preview(
    store, sources, tmp_path, monkeypatch
):
    store.create("tilt-failure", sources)
    data = framed_layout_data()
    data["elements"][0]["rotation_degrees"] = 5.5
    path = write_layout(tmp_path, data)
    store.apply_layout("tilt-failure", path)
    directory = store.project_dir("tilt-failure")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}

    def fail_rotation(*args):
        raise OSError("simulated rotation failure")

    monkeypatch.setattr(imaging_module, "_rotate_frame", fail_rotation)
    with pytest.raises(OSError, match="simulated rotation failure"):
        store.apply_layout("tilt-failure", path)
    with pytest.raises(OSError, match="simulated rotation failure"):
        store.render("tilt-failure")
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before
    assert not list(directory.glob(".apply-*"))
    assert not list(directory.glob(".render-*"))


def test_half_up_rounding_and_continuous_bounds(store, tmp_path):
    paths = [photo_file(tmp_path / f"{number}.png", (4, 3)) for number in (1, 2)]
    project = store.create("rounding", paths)
    data = layout_data(10, 10)
    for element in data["elements"]:
        element["box_normalized"]["width"] = 0.25
        element["box_normalized"]["y"] = 0.05
    resolved = resolve_layout(InputLayout.model_validate(data), project.photos, 1)
    assert resolved.elements[0].box_pixels.model_dump() == {
        "x": 1, "y": 1, "width": 3, "height": 2
    }
    data["elements"][1]["box_normalized"]["x"] = 0.751
    with pytest.raises(CollageError, match="beyond the canvas"):
        resolve_layout(InputLayout.model_validate(data), project.photos, 1)


def test_rounded_pixel_bounds_are_checked_separately(store, tmp_path):
    sources = [photo_file(tmp_path / f"{n}.png", (4, 4)) for n in (1, 2)]
    project = store.create("pixel-bounds", sources)
    data = layout_data(10, 10)
    data["elements"][0]["box_normalized"] = {"x": 0.75, "y": 0, "width": 0.25}
    # Continuous x + width is exactly 1, but rounding gives x=8 and width=3.
    with pytest.raises(CollageError, match="pixel canvas bounds"):
        resolve_layout(InputLayout.model_validate(data), project.photos, 1)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(schema_version=True),
        lambda d: d["canvas"].update(width=True),
        lambda d: d["canvas"].update(width=4097),
        lambda d: d["canvas"].update(height=0),
        lambda d: d["canvas"]["background"].update(type="image", value="file.png"),
        lambda d: d["elements"][0].update(src="secret.jpg"),
        lambda d: d["elements"][0].update(rotation=0),
        lambda d: d["elements"][0].update(
            rotated_box_pixels={"x": 0, "y": 0, "width": 20, "height": 10}
        ),
        lambda d: d["elements"][0].update(shadow=False),
        lambda d: d["elements"][0].update(crop={}),
        lambda d: d["elements"][0].update(type="text"),
        lambda d: d["elements"][0].update(source_image_id=99),
        lambda d: d["elements"][1].update(source_image_id=1),
        lambda d: d["elements"][1].update(id=10),
        lambda d: d["elements"][1].update(z_index=1),
        lambda d: d["elements"].pop(),
        lambda d: d["elements"][0]["box_normalized"].update(height=0.1),
        lambda d: d["elements"][0]["box_normalized"].update(width=0),
        lambda d: d["elements"][0]["box_normalized"].update(width=0.00001),
        lambda d: d["elements"][0]["box_normalized"].update(width="0.2"),
        lambda d: d["elements"][0]["box_normalized"].update(x=True),
        lambda d: d["elements"][0]["box_normalized"].update(x=-0.1),
        lambda d: d["elements"][0]["box_normalized"].update(x=0.99),
        lambda d: d["elements"][0]["box_normalized"].update(y=0.99),
        lambda d: d["elements"][0]["box_normalized"].update(x=float("nan")),
        lambda d: d["elements"][0]["box_normalized"].update(width=float("inf")),
        lambda d: d["elements"][0].update(border={"width_px": -1, "color": "#FFFFFF"}),
        lambda d: d["elements"][0].update(border={"width_px": 1.5, "color": "#FFFFFF"}),
        lambda d: d["elements"][0].update(border={"width_px": True, "color": "#FFFFFF"}),
        lambda d: d["elements"][0].update(border={"width_px": "2", "color": "#FFFFFF"}),
        lambda d: d["elements"][0].update(border={"width_px": 2, "color": "#FFF"}),
        lambda d: d["elements"][0].update(border={"width_px": 2, "color": "white"}),
        lambda d: d["elements"][0].update(border={"width_px": 2, "color": "#GG0000"}),
        lambda d: d["elements"][0].update(border={"width_px": 2}),
        lambda d: d["elements"][0].update(border={"width_px": 2, "color": "#FFFFFF", "inside": True}),
        lambda d: d["elements"][0].update(border={"width_px": 10, "color": "#FFFFFF"}),
        lambda d: d["elements"][0].update(border={"width_px": 11, "color": "#FFFFFF"}),
    ],
)
def test_invalid_layout_preserves_accepted_state(store, sources, tmp_path, mutation):
    store.create("invalid", sources)
    path = write_layout(tmp_path)
    _, output = store.apply_layout("invalid", path)
    directory = store.project_dir("invalid")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    data = layout_data()
    mutation(data)
    path = write_layout(tmp_path, data)
    with pytest.raises((CollageError, ValidationError)):
        store.apply_layout("invalid", path)
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before
    assert output.exists()


@pytest.mark.parametrize("problem", ["missing", "corrupt", "different-size"])
def test_unusable_imported_photo_preserves_state(store, sources, tmp_path, problem):
    project = store.create("damaged", sources)
    path = write_layout(tmp_path)
    _, output = store.apply_layout("damaged", path)
    original_output = output.read_bytes()
    metadata = (store.project_dir("damaged") / "project.json").read_bytes()
    imported = store.photo_paths(project)[1]
    if problem == "missing":
        imported.unlink()
    elif problem == "corrupt":
        imported.write_bytes(b"not an image")
    else:
        photo_file(imported, (5, 5))
    with pytest.raises((CollageError, OSError)):
        store.apply_layout("damaged", path)
    with pytest.raises((CollageError, OSError)):
        store.render("damaged")
    assert output.read_bytes() == original_output
    assert (store.project_dir("damaged") / "project.json").read_bytes() == metadata
    assert len(list((store.project_dir("damaged") / "layouts").glob("*.json"))) == 1


@pytest.mark.parametrize("failure", ["render", "pointer"])
@pytest.mark.parametrize("framed", [False, True])
def test_failed_publication_rolls_back_new_files(
    store, sources, tmp_path, monkeypatch, failure, framed
):
    store.create("rollback", sources)
    path = write_layout(tmp_path)
    store.apply_layout("rollback", path)
    directory = store.project_dir("rollback")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    if framed:
        data = framed_layout_data()
        for element in data["elements"]:
            element["corner_radius_px"] = 2
        path = write_layout(tmp_path, data)

    def fail_render(layout, photos, paths, output):
        output.write_bytes(b"partial image")
        raise OSError("simulated render failure")

    def fail_replace(source, target):
        raise OSError("simulated metadata publication failure")

    if failure == "render":
        monkeypatch.setattr(project_module, "render_layout", fail_render)
    else:
        monkeypatch.setattr(project_module.os, "replace", fail_replace)
    with pytest.raises(OSError, match="simulated"):
        store.apply_layout("rollback", path)
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before
    assert not list(directory.glob(".apply-*"))


def test_partial_rerender_cannot_replace_accepted_preview(
    store, sources, tmp_path, monkeypatch
):
    store.create("rerender", sources)
    _, output = store.apply_layout("rerender", write_layout(tmp_path))
    before = output.read_bytes()

    def fail_render(layout, photos, paths, output):
        output.write_bytes(b"partial image")
        raise OSError("simulated render failure")

    monkeypatch.setattr(project_module, "render_layout", fail_render)
    with pytest.raises(OSError, match="simulated"):
        store.render("rerender")
    assert output.read_bytes() == before
    assert store.load("rerender").current_version == 1
    assert not list(store.project_dir("rerender").glob(".render-*"))


def test_failed_create_does_not_publish_partial_project(store, sources, tmp_path):
    broken = tmp_path / "bad.jpg"
    broken.write_bytes(b"corrupt")
    with pytest.raises(CollageError, match="cannot decode"):
        store.create("failed", [sources[0], broken])
    assert not store.project_dir("failed").exists()
    assert list(store.uploads_dir.iterdir()) == []
    assert list(store.projects_dir.iterdir()) == []


def test_image_limits_and_unsupported_formats(store, sources, tmp_path):
    too_large = tmp_path / "large.png"
    with too_large.open("wb") as stream:
        stream.truncate(MAX_FILE_BYTES + 1)
    with pytest.raises(CollageError, match="25 MiB"):
        store.create("large", [sources[0], too_large])
    # A PNG header exercises the decoded-pixel guard without allocating 40M pixels.
    import struct
    import zlib

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data))
        )

    huge = tmp_path / "huge.png"
    huge.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 8000, 5001, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b""))
        + chunk(b"IEND", b"")
    )
    with pytest.raises(CollageError, match="40,000,000 decoded pixels"):
        load_photo(huge)
    gif = photo_file(tmp_path / "other.gif")
    with pytest.raises(CollageError, match="only JPEG and PNG"):
        store.create("gif", [sources[0], gif])
    animated = tmp_path / "animated.png"
    with Image.new("RGB", (10, 10), "red") as first:
        with Image.new("RGB", (10, 10), "blue") as second:
            first.save(animated, save_all=True, append_images=[second], duration=100)
    with pytest.raises(CollageError, match="animated/multiframe"):
        load_photo(animated)
    for count in (1, 7):
        with pytest.raises(CollageError, match="between 2 and 6"):
            store.create("count", (sources * 4)[:count])
    assert InputLayout.model_validate(layout_data(4096, 4096)).canvas.width == 4096


@pytest.mark.parametrize("project_id", ["../escape", "a\\b", "A", "-a", "a-", "con", "com1", "x" * 65])
def test_project_ids_cannot_be_paths_or_windows_devices(store, sources, project_id):
    with pytest.raises(CollageError):
        store.create(project_id, sources)


def test_project_cannot_redirect_photo_paths(store, sources):
    project = store.create("paths", sources)
    path = store.project_dir("paths") / "project.json"
    data = project.model_dump()
    data["photos"][0]["imported_path"] = "..\\outside.jpg"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CollageError, match="Invalid imported path"):
        store.load("paths")


def test_no_layout_yet_duplicate_create_and_version_selection(store, sources, tmp_path):
    store.create("versions", sources)
    assert store.inspect("versions")["versions"] == []
    with pytest.raises(CollageError, match="already exists"):
        store.create("versions", sources)
    with pytest.raises(CollageError, match="no accepted layout"):
        store.render("versions")
    first, _ = store.apply_layout("versions", write_layout(tmp_path))
    saved = store.project_dir("versions") / "layouts" / "v0001.json"
    immutable = saved.read_bytes()
    data = layout_data()
    data["canvas"]["background"]["value"] = "#000000"
    second, _ = store.apply_layout("versions", write_layout(tmp_path, data))
    assert (first.version, second.version) == (1, 2)
    assert saved.read_bytes() == immutable
    store.render("versions", 1)
    assert store.load("versions").current_version == 2
    assert [v["version"] for v in store.inspect("versions")["versions"]] == [1, 2]
    for bad_version in (0, -1, 3):
        with pytest.raises(CollageError):
            store.render("versions", bad_version)
    data = json.loads(saved.read_text())
    data["elements"][0]["box_pixels"]["width"] += 1
    saved.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CollageError, match="inconsistent"):
        store.render("versions", 1)


def test_duplicate_json_fields_are_rejected(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
    with pytest.raises(CollageError, match="Duplicate JSON field"):
        read_json(path)


def run_cli(data_dir, *arguments):
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(("AZURE_", "OPENAI_"))
    }
    script = (
        "import runpy,socket\n"
        "def blocked(*args,**kwargs):\n"
        "    raise AssertionError('Network calls forbidden')\n"
        "socket.socket.connect=blocked\n"
        "socket.create_connection=blocked\n"
        "runpy.run_module('ai_collage',run_name='__main__')\n"
    )
    return subprocess.run(
        [sys.executable, "-c", script, "--data-dir", str(data_dir), *map(str, arguments)],
        cwd=REPO, env=environment, capture_output=True, text=True, timeout=30,
    )


@pytest.mark.parametrize("border_width", [0, 2])
@pytest.mark.parametrize("framed", [False, True])
@pytest.mark.parametrize("angle", [0, 5.5])
def test_cli_persists_across_processes_without_credentials_or_network(
    tmp_path, sources, border_width, framed, angle
):
    data_dir = tmp_path / "cli-data"
    created = run_cli(data_dir, "create", "--project", "cli", "--images", *sources)
    assert created.returncode == 0, created.stderr
    assert json.loads(created.stdout)["current_version"] is None
    data = framed_layout_data() if framed else layout_data()
    for element in data["elements"]:
        element["rotation_degrees"] = angle
    if framed:
        for element in data["elements"]:
            element["framing"].update(zoom=2, pan_x=0.25, pan_y=0.75)
            element["corner_radius_px"] = 2
    if border_width:
        for element in data["elements"]:
            element["border"] = {"width_px": border_width, "color": "#00FF00"}
    path = write_layout(tmp_path, data)
    applied = run_cli(data_dir, "apply-layout", "--project", "cli", "--layout", path)
    assert applied.returncode == 0, applied.stderr
    assert json.loads(applied.stdout)["version"] == 1
    saved = json.loads(Path(json.loads(applied.stdout)["layout_path"]).read_text())
    assert all(element["rotation_degrees"] == angle for element in saved["elements"])
    assert all(
        (element["rotated_box_pixels"] is not None) == (angle != 0)
        for element in saved["elements"]
    )
    if framed:
        assert all(element["source_crop"] is not None for element in saved["elements"])
        assert all(element["framing"]["zoom"] == 2 for element in saved["elements"])
        assert all(element["corner_radius_px"] == 2 for element in saved["elements"])
    for source in sources:
        source.unlink()
    inspected = run_cli(data_dir, "inspect", "--project", "cli")
    assert inspected.returncode == 0, inspected.stderr
    state = json.loads(inspected.stdout)
    assert [p["source_image_id"] for p in state["photos"]] == [1, 2]
    assert state["current_version"] == 1
    output = Path(state["versions"][0]["render_path"])
    original_output = output.read_bytes()
    output.unlink()
    rendered = run_cli(data_dir, "render", "--project", "cli", "--version", "1")
    assert rendered.returncode == 0, rendered.stderr
    assert output.read_bytes() == original_output
    invalid = copy.deepcopy(layout_data())
    invalid["elements"][0]["source_image_id"] = 99
    failed = run_cli(
        data_dir, "apply-layout", "--project", "cli",
        "--layout", write_layout(tmp_path, invalid),
    )
    assert failed.returncode == 1
    assert failed.stdout == ""
    assert "exactly once" in failed.stderr
    assert json.loads(run_cli(data_dir, "inspect", "--project", "cli").stdout)[
        "current_version"
    ] == 1
