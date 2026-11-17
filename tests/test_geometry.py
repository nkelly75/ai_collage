from PIL import Image, ImageDraw
import pytest

from ai_collage.geometry import resolve_layout
from ai_collage.models import CollageError, InputLayout

from .helpers import framed_layout_data, layout_data, photo_file, write_layout


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
        for element in data["layers"]:
            element["border"] = {"width_px": border_width, "color": "#00FF00"}
    resolved, output = store.apply_layout("corners", write_layout(tmp_path, data))
    with Image.open(output) as image:
        assert image.size == canvas
        assert image.getpixel((0, 0)) == (255, 255, 255)
        for element, photo in zip(resolved.geometry, project.photos, strict=True):
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


def test_border_rounding_uses_outer_width_before_photo_ratio(store, tmp_path):
    sources = [photo_file(tmp_path / f"{n}.png", (4, 3)) for n in (1, 2)]
    project = store.create("border-rounding", sources)
    data = layout_data(10, 10)
    data["layers"][0]["box"] = {"x": 0.05, "y": 0.05, "width": 0.45}
    data["layers"][0]["border"] = {"width_px": 1, "color": "#FFFFFF"}
    resolved = resolve_layout(InputLayout.model_validate(data), project.photos, 1)
    element = resolved.geometry[0]
    assert element.box_normalized.height == 0.3875
    assert element.box_pixels.model_dump() == {
        "x": 1, "y": 1, "width": 5, "height": 4
    }
    assert element.photo_box_pixels.model_dump() == {
        "x": 2, "y": 2, "width": 3, "height": 2
    }


@pytest.mark.parametrize("canvas", [(100, 100), (200, 100), (100, 200)])
def test_cover_frames_resolve_on_each_canvas_shape(store, sources, tmp_path, canvas):
    store.create("frame-canvas", sources)
    data = framed_layout_data(*canvas)
    data["layers"][0]["box"]["height"] = 0.3
    data["layers"][0]["border"] = {"width_px": 2, "color": "#00FF00"}
    resolved, output = store.apply_layout("frame-canvas", write_layout(tmp_path, data))
    element = resolved.geometry[0]
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


@pytest.mark.parametrize("framed, border_width, maximum", [
    (False, 0, 5), (False, 2, 4), (True, 0, 10), (True, 2, 8),
])
def test_corner_radius_limit_uses_actual_inset_photo_dimensions(
    store, sources, tmp_path, framed, border_width, maximum
):
    store.create("radius-limit", sources)
    data = framed_layout_data() if framed else layout_data()
    element = data["layers"][0]
    element["border"] = {"width_px": border_width, "color": "#FFFFFF"}
    element["corner_radius_px"] = maximum
    store.apply_layout("radius-limit", write_layout(tmp_path, data))
    directory = store.project_dir("radius-limit")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    element["corner_radius_px"] += 1
    with pytest.raises(CollageError, match="half the smaller photo dimension"):
        store.apply_layout("radius-limit", write_layout(tmp_path, data))
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before


def test_half_up_rounding_and_continuous_bounds(store, tmp_path):
    paths = [photo_file(tmp_path / f"{number}.png", (4, 3)) for number in (1, 2)]
    project = store.create("rounding", paths)
    data = layout_data(10, 10)
    for element in data["layers"]:
        element["box"]["width"] = 0.25
        element["box"]["y"] = 0.05
    resolved = resolve_layout(InputLayout.model_validate(data), project.photos, 1)
    assert resolved.geometry[0].box_pixels.model_dump() == {
        "x": 1, "y": 1, "width": 3, "height": 2
    }
    data["layers"][1]["box"]["x"] = 0.751
    with pytest.raises(CollageError, match="beyond the canvas"):
        resolve_layout(InputLayout.model_validate(data), project.photos, 1)


def test_rounded_pixel_bounds_are_checked_separately(store, tmp_path):
    sources = [photo_file(tmp_path / f"{n}.png", (4, 4)) for n in (1, 2)]
    project = store.create("pixel-bounds", sources)
    data = layout_data(10, 10)
    data["layers"][0]["box"] = {"x": 0.75, "y": 0, "width": 0.25}
    # Continuous x + width is exactly 1, but rounding gives x=8 and width=3.
    with pytest.raises(CollageError, match="pixel canvas bounds"):
        resolve_layout(InputLayout.model_validate(data), project.photos, 1)
