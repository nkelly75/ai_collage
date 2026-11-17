from pathlib import Path
import json

from pydantic import ValidationError
import pytest

from ai_collage.models import CollageError, InputLayout
from ai_collage.projects import read_json

from .helpers import framed_layout_data, layout_data, write_layout


@pytest.mark.parametrize("mutation", [
    lambda d: d["layers"][0]["box"].pop("height"),
    lambda d: d["layers"][0].update(crop=None),
    lambda d: d["layers"][0]["box"].update(height=None),
    lambda d: d["layers"][0]["box"].update(height=0),
    lambda d: d["layers"][0]["box"].update(height=True),
    lambda d: d["layers"][0]["box"].update(height=0.00001),
    lambda d: d["layers"][0]["box"].update(y=0.9),
    lambda d: d["layers"][0]["box"].update(y=0.795, height=0.205),
    lambda d: d["layers"][0].update(border={"width_px": 10, "color": "#FFFFFF"}),
    lambda d: d["layers"][0].update(border={"width_px": 2, "color": "#FFFFFF"})
    or d["layers"][0]["box"].update(height=0.04),
    lambda d: d["layers"][0].update(border={"width_px": 2, "color": "#FFFFFF"})
    or d["layers"][0]["box"].update(height=0.041),
    lambda d: d["layers"][0].update(mode="contain"),
    lambda d: d["layers"][0]["crop"].update(zoom=0.99),
    lambda d: d["layers"][0]["crop"].update(zoom=4.01),
    lambda d: d["layers"][0]["crop"].update(zoom=True),
    lambda d: d["layers"][0]["crop"].update(zoom="2"),
    lambda d: d["layers"][0]["crop"].update(zoom=float("nan")),
    lambda d: d["layers"][0]["crop"].update(zoom=float("inf")),
    lambda d: d["layers"][0]["crop"].update(pan_x=-0.01),
    lambda d: d["layers"][0]["crop"].update(pan_y=1.01),
    lambda d: d["layers"][0]["crop"].update(pan_x=True),
    lambda d: d["layers"][0]["crop"].update(pan_y="0.5"),
    lambda d: d["layers"][0]["crop"].update(pan_y=float("nan")),
    lambda d: d["layers"][0]["crop"].update(unknown=0),
    lambda d: d["layers"][0].update(source_crop={"left": 0, "top": 0, "right": 1, "bottom": 1}),
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


def test_whole_photo_mode_rejects_even_null_input_height(store, sources, tmp_path):
    store.create("null-height", sources)
    data = layout_data()
    data["layers"][0]["box"]["height"] = None
    with pytest.raises(ValidationError, match="Extra inputs"):
        store.apply_layout("null-height", write_layout(tmp_path, data))


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
    data["layers"][0]["corner_radius_px"] = radius
    with pytest.raises(error):
        store.apply_layout("invalid-radius", write_layout(tmp_path, data))
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before


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
    data["layers"][0]["rotation_degrees"] = angle
    with pytest.raises(error):
        store.apply_layout("invalid-tilt", write_layout(tmp_path, data))
    assert {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(schema_version=True),
        lambda d: d["canvas"].update(width=True),
        lambda d: d["canvas"].update(width=4097),
        lambda d: d["canvas"].update(height=0),
        lambda d: d["canvas"].update(background={"type": "image", "value": "file.png"}),
        lambda d: d["layers"][0].update(src="secret.jpg"),
        lambda d: d["layers"][0].update(rotation=0),
        lambda d: d["layers"][0].update(
            rotated_box_pixels={"x": 0, "y": 0, "width": 20, "height": 10}
        ),
        lambda d: d["layers"][0].update(shadow=False),
        lambda d: d["layers"][0].update(crop={}),
        lambda d: d["layers"][0].update(type="text"),
        lambda d: d["layers"][0].update(photo_id=99),
        lambda d: d["layers"][1].update(photo_id=1),
        lambda d: d["layers"][1].update(id=10),
        lambda d: d["layers"][1].update(z_index=1),
        lambda d: d["layers"].pop(),
        lambda d: d["layers"][0]["box"].update(height=0.1),
        lambda d: d["layers"][0]["box"].update(width=0),
        lambda d: d["layers"][0]["box"].update(width=0.00001),
        lambda d: d["layers"][0]["box"].update(width="0.2"),
        lambda d: d["layers"][0]["box"].update(x=True),
        lambda d: d["layers"][0]["box"].update(x=-0.1),
        lambda d: d["layers"][0]["box"].update(x=0.99),
        lambda d: d["layers"][0]["box"].update(y=0.99),
        lambda d: d["layers"][0]["box"].update(x=float("nan")),
        lambda d: d["layers"][0]["box"].update(width=float("inf")),
        lambda d: d["layers"][0].update(border={"width_px": -1, "color": "#FFFFFF"}),
        lambda d: d["layers"][0].update(border={"width_px": 1.5, "color": "#FFFFFF"}),
        lambda d: d["layers"][0].update(border={"width_px": True, "color": "#FFFFFF"}),
        lambda d: d["layers"][0].update(border={"width_px": "2", "color": "#FFFFFF"}),
        lambda d: d["layers"][0].update(border={"width_px": 2, "color": "#FFF"}),
        lambda d: d["layers"][0].update(border={"width_px": 2, "color": "white"}),
        lambda d: d["layers"][0].update(border={"width_px": 2, "color": "#GG0000"}),
        lambda d: d["layers"][0].update(border={"width_px": 2}),
        lambda d: d["layers"][0].update(border={"width_px": 2, "color": "#FFFFFF", "inside": True}),
        lambda d: d["layers"][0].update(border={"width_px": 10, "color": "#FFFFFF"}),
        lambda d: d["layers"][0].update(border={"width_px": 11, "color": "#FFFFFF"}),
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


def test_duplicate_json_fields_are_rejected(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
    with pytest.raises(CollageError, match="Duplicate JSON field"):
        read_json(path)


def test_generated_schema_matches_models():
    path = Path(__file__).resolve().parents[1] / "docs" / "layout.schema.json"
    assert json.loads(path.read_text(encoding="utf-8")) == InputLayout.model_json_schema()


@pytest.mark.parametrize("photo_id", [True, "1"])
def test_photo_ids_are_strict_integers(photo_id):
    data = layout_data()
    data["layers"][0]["photo_id"] = photo_id
    with pytest.raises(ValidationError):
        InputLayout.model_validate(data)


@pytest.mark.parametrize("count", [1, 7])
def test_layer_count_is_bounded(count):
    data = layout_data()
    data["layers"] = (data["layers"] * 4)[:count]
    with pytest.raises(ValidationError):
        InputLayout.model_validate(data)


def test_cover_defaults_and_whole_mode_forbid_crop_controls():
    data = framed_layout_data()
    for layer in data["layers"]:
        del layer["crop"]
    recipe = InputLayout.model_validate(data)
    assert recipe.layers[0].crop.model_dump() == {
        "zoom": 1.0, "pan_x": 0.5, "pan_y": 0.5,
    }
    data = layout_data()
    data["layers"][0]["crop"] = None
    with pytest.raises(ValidationError, match="Extra inputs"):
        InputLayout.model_validate(data)


def test_missing_project_photo_is_rejected(store, sources, tmp_path):
    project = store.create("missing-photo", sources + [sources[0]])
    assert len(project.photos) == 3
    with pytest.raises(CollageError, match="exactly once"):
        store.apply_layout("missing-photo", write_layout(tmp_path))
    assert store.load("missing-photo").current_version is None
