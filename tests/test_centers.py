import json

from PIL import Image
from pydantic import ValidationError
import pytest

from ai_collage.geometry import LayoutBoundsError, resolve_layout
from ai_collage.models import CollageError, InputLayout, ResolvedLayout

from .helpers import framed_layout_data, layout_data, photo_file, write_layout


@pytest.mark.parametrize("cover", [False, True])
@pytest.mark.parametrize("canvas", [(100, 100), (200, 100), (100, 200)])
def test_resize_preserves_center_with_at_most_half_pixel_raster_error(
    store, sources, canvas, cover
):
    project = store.create("center-resize", sources)
    data = framed_layout_data(*canvas) if cover else layout_data(*canvas)
    layer = data["layers"][0]
    layer["box"].update(center_x=0.3, center_y=0.5)
    layer["border"] = {"width_px": 2, "color": "#00FF00"}
    for width in [0.2, 0.19, 0.21, 0.18, 0.2]:
        layer["box"]["width"] = width
        if cover:
            layer["box"]["height"] = width * 1.5
        untilted = None
        for angle in [0, -5, 5]:
            layer["rotation_degrees"] = angle
            result = resolve_layout(InputLayout.model_validate(data), project.photos, 1)
            box = result.geometry[0].box_pixels
            assert abs(box.x + box.width / 2 - 0.3 * canvas[0]) <= 0.5
            assert abs(box.y + box.height / 2 - 0.5 * canvas[1]) <= 0.5
            assert result.recipe.layers[0].box.center_x == 0.3
            assert result.recipe.layers[0].box.center_y == 0.5
            if untilted is None:
                untilted = box
            assert box == untilted


def test_border_removal_changes_height_around_same_center(store, sources):
    project = store.create("center-border", sources)
    data = layout_data()
    layer = data["layers"][0]
    layer["box"].update(center_x=0.3, center_y=0.5)
    layer["border"] = {"width_px": 2, "color": "#FFFFFF"}
    before = resolve_layout(InputLayout.model_validate(data), project.photos, 1)
    layer["border"] = None
    after = resolve_layout(InputLayout.model_validate(data), project.photos, 1)
    assert before.geometry[0].box_pixels.model_dump() == {
        "x": 20, "y": 44, "width": 20, "height": 12,
    }
    assert after.geometry[0].box_pixels.model_dump() == {
        "x": 20, "y": 45, "width": 20, "height": 10,
    }
    assert before.recipe.layers[0].box == after.recipe.layers[0].box
    assert before.geometry[1] == after.geometry[1]


def test_full_canvas_whole_photo_background(store, tmp_path):
    store.create("background", [
        photo_file(tmp_path / f"{n}.png", (4, 3)) for n in (1, 2)
    ])
    data = layout_data(100, 75)
    data["layers"][0]["box"] = {"center_x": 0.5, "center_y": 0.5, "width": 1.0}
    result, output = store.apply_layout("background", write_layout(tmp_path, data))
    assert result.geometry[0].box_pixels.model_dump() == {
        "x": 0, "y": 0, "width": 100, "height": 75,
    }
    with Image.open(output) as image:
        assert image.getpixel((99, 74)) == (255, 0, 0)


@pytest.mark.parametrize("mutation", [
    lambda d: d["layers"][0]["box"].update(x=0.1),
    lambda d: d["layers"][0]["box"].update(y=0.1),
    lambda d: d["layers"][0]["box"].pop("center_x"),
    lambda d: d["layers"][0]["box"].pop("center_y"),
    lambda d: d["layers"][0]["box"].update(center_y="0.5"),
    lambda d: d["layers"][0]["box"].update(center_y=1.1),
])
def test_center_contract_rejects_missing_mixed_or_invalid_coordinates(mutation):
    data = layout_data()
    mutation(data)
    with pytest.raises(ValidationError):
        InputLayout.model_validate(data)


@pytest.mark.parametrize("old_version", [1, 2])
@pytest.mark.parametrize("target", ["recipe", "project", "snapshot"])
def test_old_formats_rejected_without_writing_saved_data(
    store, sources, tmp_path, old_version, target
):
    store.create("archive", sources)
    path = write_layout(tmp_path)
    store.apply_layout("archive", path)
    selected = {
        "recipe": path,
        "project": store.project_dir("archive") / "project.json",
        "snapshot": store.version_paths("archive", 1)[0],
    }[target]
    data = json.loads(selected.read_text())
    data["schema_version"] = old_version
    selected.write_text(json.dumps(data), encoding="utf-8")
    before = {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()}
    with pytest.raises(ValidationError, match="Unsupported schema_version"):
        store.apply_layout("archive", path)
    assert {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()} == before


def test_changed_center_in_saved_recipe_cannot_replace_preview(store, sources, tmp_path):
    store.create("center-tamper", sources)
    saved, output = store.apply_layout("center-tamper", write_layout(tmp_path))
    assert saved.schema_version == 3
    original = output.read_bytes()
    data = saved.model_dump()
    data["recipe"]["layers"][0]["box"]["center_x"] = 0.31
    store.version_paths("center-tamper", 1)[0].write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CollageError, match="inconsistent"):
        store.render("center-tamper")
    assert output.read_bytes() == original
    data["schema_version"] = 2
    with pytest.raises(ValidationError, match="Unsupported schema_version"):
        ResolvedLayout.model_validate(data)


@pytest.mark.parametrize("cover", [False, True])
@pytest.mark.parametrize("axis", ["center_x", "center_y"])
def test_positive_center_can_still_put_frame_past_left_or_top(
    store, sources, tmp_path, cover, axis
):
    store.create("near-origin", sources)
    data = framed_layout_data() if cover else layout_data()
    path = write_layout(tmp_path, data)
    store.apply_layout("near-origin", path)
    directory = store.project_dir("near-origin")
    before = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    data["layers"][0]["box"][axis] = 0.01
    with pytest.raises(LayoutBoundsError) as caught:
        store.apply_layout("near-origin", write_layout(tmp_path, data))
    side = "left" if axis == "center_x" else "top"
    assert caught.value.details["overshoot_px"][side] > 0
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before
