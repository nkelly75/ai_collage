import math

from PIL import Image, ImageDraw
import pytest

from ai_collage.models import CollageError

from .helpers import framed_layout_data, layout_data, photo_file, rounded_layout_data, write_layout


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
    data["layers"][0]["box"]["center_y"] = 0.5
    data["layers"][0]["border"] = {"width_px": border_width, "color": "#00FF00"}
    resolved, output = store.apply_layout("exif", write_layout(tmp_path, data))
    box = resolved.geometry[0].photo_box_pixels
    with Image.open(output) as rendered:
        assert rendered.getpixel((box.x + box.width // 2, box.y + box.height // 8))[0] > 240
        assert rendered.getpixel((box.x + box.width // 2, box.y + box.height * 7 // 8))[2] > 240
    assert path.read_bytes() == original


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
    for element, color, center_y in zip(data["layers"], colors, [0.16, 0.28], strict=True):
        element["border"] = {"width_px": 2, "color": color}
        element["box"]["center_y"] = center_y
    resolved, output = store.apply_layout("borders", write_layout(tmp_path, data))
    assert resolved.geometry[0].box_pixels.model_dump() == {
        "x": 5, "y": 10, "width": 20, "height": 12
    }
    assert resolved.geometry[0].photo_box_pixels.model_dump() == {
        "x": 7, "y": 12, "width": 16, "height": 8
    }
    assert resolved.geometry[1].box_pixels.model_dump() == {
        "x": 50, "y": 10, "width": 20, "height": 36
    }
    with Image.open(output) as image:
        for element, photo_color, border_color in zip(
            resolved.geometry, [(255, 0, 0), (0, 0, 255)],
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


def test_border_may_touch_canvas_edges_without_clipping(store, sources, tmp_path):
    store.create("edge-borders", sources)
    data = layout_data()
    for element, center_y in zip(data["layers"], [0.94, 0.82], strict=True):
        element["box"] = {"center_x": 0.9, "center_y": center_y, "width": 0.2}
        element["border"] = {"width_px": 2, "color": "#00FF00"}
    resolved, output = store.apply_layout("edge-borders", write_layout(tmp_path, data))
    for element in resolved.geometry:
        outer = element.box_pixels
        assert outer.x + outer.width == 100
        assert outer.y + outer.height == 100
    with Image.open(output) as image:
        assert image.getpixel((99, 99)) == (0, 255, 0)


@pytest.mark.parametrize(
    "box, message",
    [
        ({"center_x": 0.15, "center_y": 0.95, "width": 0.2}, "beyond the canvas"),
        ({"center_x": 0.95, "center_y": 0.5, "width": 0.205}, "beyond the canvas"),
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
    data["layers"][0]["box"] = box
    data["layers"][0]["border"] = {"width_px": 2, "color": "#FFFFFF"}
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
    data["layers"][0]["box"]["width"] = width
    data["layers"][0]["border"] = {"width_px": border_width, "color": "#FFFFFF"}
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
    data["layers"][0]["border"] = {"width_px": 2, "color": "#00FF00"}
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
    data["layers"][0]["box"] = {"center_x": 0.35, "center_y": 0.35, "width": 0.5}
    data["layers"][0]["border"] = {"width_px": 3, "color": "#00FF00"}
    data["layers"][1]["box"] = {"center_x": 0.55, "center_y": 0.45, "width": 0.3}
    data["layers"][1]["border"] = {"width_px": 2, "color": "#FFFF00"}
    for element in data["layers"]:
        element["corner_radius_px"] = radius
    if foreground == 1:
        data["layers"].reverse()
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
    data["layers"][0]["border"] = {"width_px": 2, "color": "#123456"}
    data["layers"][0]["crop"].update(
        zoom=zoom,
        pan_x=pan if axis == "x" else 1 - pan,
        pan_y=pan if axis == "y" else 1 - pan,
    )
    resolved, output = store.apply_layout("pan", write_layout(tmp_path, data))
    element = resolved.geometry[0]
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
    data["layers"][0]["crop"]["zoom"] = zoom
    resolved, output = store.apply_layout("zoom", write_layout(tmp_path, data))
    element = resolved.geometry[0]
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
    data["layers"][0]["box"]["height"] = 0.3
    resolved, output = store.apply_layout("aspect", write_layout(tmp_path, data))
    box = resolved.geometry[0].photo_box_pixels
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
    data["layers"][0]["crop"].update(zoom=1.5, pan_x=0.25, pan_y=0.75)
    resolved, output = store.apply_layout("fractional", write_layout(tmp_path, data))
    crop = resolved.geometry[0].source_crop
    assert crop.left == pytest.approx(20 / 3)
    assert crop.top == 20
    assert crop.right == 60
    assert crop.bottom == pytest.approx(220 / 3)
    with Image.open(output) as image:
        actual = image.getpixel((15, 20))
    assert all(abs(a - b) <= 3 for a, b in zip(actual, (103, 143, 0), strict=True))


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
    element = resolved.geometry[1]
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
    data["canvas"]["background"] = "#000000"
    element, other = data["layers"]
    x, y = (canvas[0] - width) // 2, (canvas[1] - height) // 2
    element["box"] = {
        "center_x": (x + width / 2) / canvas[0],
        "center_y": (y + height / 2) / canvas[1], "width": width / canvas[0],
    }
    if framed:
        element["box"]["height"] = height / canvas[1]
    other["box"] = {"center_x": 0.05, "center_y": 0.05, "width": 0.05}
    if framed:
        other["box"]["height"] = 0.05
    element["rotation_degrees"] = angle
    resolved, output = store.apply_layout("tilt-markers", write_layout(tmp_path, data))
    front = resolved.geometry[0]
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
    front = data["layers"][0]
    front.update(border={"width_px": 2, "color": "#FFFFFF"}, corner_radius_px=4)
    front["box"].update(center_x=0.4, center_y=0.4)
    if side in {"left", "right"}:
        front["box"]["center_x"] = 0.1 if side == "left" else 0.9
    else:
        margin = 0.1 if framed else 0.06
        front["box"]["center_y"] = margin if side == "top" else 1 - margin
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
    front = data["layers"][0]
    front["box"] = {
        "center_x": 0.2149, "center_y": 0.3, "width": 0.4, "height": 0.2,
    }
    front["rotation_degrees"] = 10
    # Ideal left edge is just positive; rounding x down puts the tilted corner outside.
    with pytest.raises(CollageError, match="rotated pixel footprint.*sampling margin"):
        store.apply_layout("tilt-pixels", write_layout(tmp_path, data))
    assert store.load("tilt-pixels").current_version is None
    front["box"]["center_x"] = 0.24
    resolved, _ = store.apply_layout("tilt-pixels", write_layout(tmp_path, data))
    assert resolved.geometry[0].rotated_box_pixels.x == 0


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
    front = data["layers"][1]
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
    data["layers"].reverse()
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
    data["canvas"]["background"] = background
    front, other = data["layers"]
    front["box"] = {"center_x": 0.4, "center_y": 0.4, "width": 0.4, "height": 0.4}
    front["rotation_degrees"] = -3.5
    other["box"] = {"center_x": 0.035, "center_y": 0.035, "width": 0.05, "height": 0.05}
    resolved, output = store.apply_layout("tilt-smooth", write_layout(tmp_path, data))
    box = resolved.geometry[0].rotated_box_pixels
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


def test_overlap_uses_layer_order_without_renaming_photos(store, sources, tmp_path):
    store.create("overlap", sources)
    data = layout_data()
    data["layers"][1]["box"] = {"center_x": 0.15, "center_y": 0.3, "width": 0.2}
    data["layers"].reverse()
    resolved, output = store.apply_layout("overlap", write_layout(tmp_path, data))
    assert [element.photo_id for element in resolved.geometry] == [2, 1]
    with Image.open(output) as image:
        assert image.getpixel((10, 15)) == (255, 0, 0)
        assert image.getpixel((10, 40)) == (0, 0, 255)
