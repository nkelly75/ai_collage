import json

from PIL import Image
from pydantic import ValidationError
import pytest

from ai_collage import imaging as imaging_module, projects as project_module
from ai_collage.imaging import load_photo
from ai_collage.models import CollageError, InputLayout, MAX_FILE_BYTES, MAX_JSON_BYTES
from ai_collage.projects import ProjectStore, read_json

from .helpers import framed_layout_data, layout_data, photo_file, write_layout


def test_inconsistent_saved_border_geometry_is_rejected(store, sources, tmp_path):
    store.create("tampered-border", sources)
    data = layout_data()
    data["layers"][0]["border"] = {"width_px": 2, "color": "#FFFFFF"}
    _, output = store.apply_layout("tampered-border", write_layout(tmp_path, data))
    before = output.read_bytes()
    path = store.version_paths("tampered-border", 1)[0]
    saved = json.loads(path.read_text())
    saved["recipe"]["layers"][0]["border"]["width_px"] = 3
    path.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(CollageError, match="inconsistent"):
        store.render("tampered-border")
    assert output.read_bytes() == before


@pytest.mark.parametrize("mutation", [
    lambda d: d["geometry"][0]["source_crop"].update(left="10.0"),
    lambda d: d["geometry"][0]["source_crop"].update(left=11),
    lambda d: d["geometry"][0]["source_crop"].update(right=999),
    lambda d: d["geometry"][0].pop("source_crop"),
    lambda d: d["recipe"]["layers"][0]["crop"].update(pan_x=0),
    lambda d: d["recipe"]["layers"][0]["box"].update(height=0.25),
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


def test_invalid_saved_radius_cannot_replace_accepted_preview(store, sources, tmp_path):
    store.create("tampered-radius", sources)
    data = layout_data()
    data["layers"][0]["corner_radius_px"] = 3
    _, output = store.apply_layout("tampered-radius", write_layout(tmp_path, data))
    previous_output = output.read_bytes()
    saved_layout = store.version_paths("tampered-radius", 1)[0]
    saved = json.loads(saved_layout.read_text())
    saved["recipe"]["layers"][0]["corner_radius_px"] = 999
    saved_layout.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(CollageError, match="corner_radius_px"):
        store.render("tampered-radius")
    assert output.read_bytes() == previous_output


@pytest.mark.parametrize("framed", [False, True])
def test_tilt_keeps_framing_and_reopens_reproducibly(store, sources, tmp_path, framed):
    store.create("tilt-persist", sources)
    data = framed_layout_data() if framed else layout_data()
    for element in data["layers"]:
        element.update(
            border={"width_px": 2, "color": "#00FF00"}, corner_radius_px=2,
        )
        if framed:
            element["crop"].update(zoom=2, pan_x=0.25, pan_y=0.75)
    first, first_output = store.apply_layout("tilt-persist", write_layout(tmp_path, data))
    first_layout = store.version_paths("tilt-persist", 1)[0]
    original = (first_layout.read_bytes(), first_output.read_bytes())
    for element, angle in zip(data["layers"], [5.5, -3.25], strict=True):
        element["rotation_degrees"] = angle
    second, output = store.apply_layout("tilt-persist", write_layout(tmp_path, data))
    for old, new in zip(first.geometry, second.geometry, strict=True):
        assert old.box_pixels == new.box_pixels
        assert old.box_normalized == new.box_normalized
        assert old.photo_box_pixels == new.photo_box_pixels
        assert old.source_crop == new.source_crop
        assert new.rotated_box_pixels is not None
    assert second.recipe == InputLayout.model_validate(data)
    reopened = ProjectStore(store.data_dir)
    assert reopened.load_layout(reopened.load("tilt-persist"), 2) == second
    expected = output.read_bytes()
    reopened.render("tilt-persist", 2)
    assert output.read_bytes() == expected
    assert (first_layout.read_bytes(), first_output.read_bytes()) == original


@pytest.mark.parametrize("mutation", [
    lambda e: e["geometry"][0]["rotated_box_pixels"].update(x=99),
    lambda e: e["geometry"][0].pop("rotated_box_pixels"),
    lambda e: e["recipe"]["layers"][0].update(rotation_degrees=0),
])
def test_inconsistent_saved_tilt_geometry_preserves_preview(
    store, sources, tmp_path, mutation
):
    store.create("tampered-tilt", sources)
    data = framed_layout_data()
    data["layers"][0].update(
        rotation_degrees=5.5, corner_radius_px=2,
        border={"width_px": 2, "color": "#FFFFFF"},
        crop={"zoom": 1.5, "pan_x": 0.25, "pan_y": 0.75},
    )
    resolved, output = store.apply_layout("tampered-tilt", write_layout(tmp_path, data))
    assert resolved.recipe == InputLayout.model_validate(data)
    original_output = output.read_bytes()
    saved_layout = store.version_paths("tampered-tilt", 1)[0]
    saved = json.loads(saved_layout.read_text())
    mutation(saved)
    saved_layout.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises((CollageError, ValidationError)):
        store.render("tampered-tilt")
    assert output.read_bytes() == original_output


def test_rotation_failure_preserves_accepted_state_and_preview(
    store, sources, tmp_path, monkeypatch
):
    store.create("tilt-failure", sources)
    data = framed_layout_data()
    data["layers"][0]["rotation_degrees"] = 5.5
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
        for element in data["layers"]:
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
    data["canvas"]["background"] = "#000000"
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
    data["geometry"][0]["box_pixels"]["width"] += 1
    saved.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(CollageError, match="inconsistent"):
        store.render("versions", 1)


def test_recipe_adjustments_do_not_edit_accepted_intent(store, sources, tmp_path):
    project = store.create("adjustments", sources)
    data = framed_layout_data()
    first, first_output = store.apply_layout("adjustments", write_layout(tmp_path, data))
    saved = store.version_paths("adjustments", 1)[0]
    before = (saved.read_bytes(), first_output.read_bytes())
    front = data["layers"][0]
    front["box"].update(center_x=0.25, width=0.3, height=0.25)
    front["crop"].update(zoom=2, pan_x=1, pan_y=0)
    data["layers"].reverse()
    second, _ = store.apply_layout("adjustments", write_layout(tmp_path, data))
    assert [p.photo_id for p in project.photos] == [1, 2]
    assert [p.photo_id for p in second.recipe.layers] == [2, 1]
    assert second.geometry[0] == first.geometry[1]
    assert second.geometry[1].source_crop != first.geometry[0].source_crop
    assert second.recipe == InputLayout.model_validate(data)
    assert "box_pixels" not in second.recipe.model_dump_json()
    assert (saved.read_bytes(), first_output.read_bytes()) == before


def test_json_size_bound_is_in_bytes_and_read_is_bounded(tmp_path, monkeypatch):
    import io

    path = tmp_path / "bounded.json"
    exact = b'{"ok":true}' + b" " * (MAX_JSON_BYTES - len(b'{"ok":true}'))
    path.write_bytes(exact)
    assert read_json(path) == {"ok": True}
    path.write_bytes(exact + b" ")
    reads = []
    real_open = type(path).open

    class ObservedStream(io.BytesIO):
        def read(self, size=-1):
            reads.append(size)
            return super().read(size)

    def open_observed(self, *args, **kwargs):
        if self == path:
            return ObservedStream(exact + b" " * 100)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(type(path), "open", open_observed)
    with pytest.raises(CollageError, match="1 MiB"):
        read_json(path)
    assert reads == [MAX_JSON_BYTES + 1]


def test_invalid_encoding_is_a_domain_error(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_bytes(b"\xff")
    with pytest.raises(CollageError, match="invalid JSON"):
        read_json(path)


def test_parser_recursion_failure_is_a_domain_error(tmp_path, monkeypatch):
    path = tmp_path / "deep.json"
    path.write_text("[]", encoding="utf-8")

    def fail_parser(*args, **kwargs):
        raise RecursionError("simulated parser recursion")

    monkeypatch.setattr(project_module.json, "loads", fail_parser)
    with pytest.raises(CollageError, match="invalid JSON.*simulated parser recursion"):
        read_json(path)


@pytest.mark.parametrize("target", ["recipe", "project", "snapshot"])
def test_oversize_documents_preserve_state(store, sources, tmp_path, target):
    store.create("oversize", sources)
    recipe = write_layout(tmp_path)
    _, output = store.apply_layout("oversize", recipe)
    path = {
        "recipe": recipe,
        "project": store.project_dir("oversize") / "project.json",
        "snapshot": store.version_paths("oversize", 1)[0],
    }[target]
    path.write_bytes(b" " * (MAX_JSON_BYTES + 1))
    before = {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()}
    with pytest.raises(CollageError, match="1 MiB"):
        store.apply_layout("oversize", recipe)
    assert {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()} == before
    assert output.exists()


@pytest.mark.parametrize("command", ["inspect", "render", "apply-layout"])
def test_old_snapshot_rejected_before_publication(store, sources, tmp_path, command):
    store.create("old-snapshot", sources)
    recipe = write_layout(tmp_path)
    store.apply_layout("old-snapshot", recipe)
    saved = store.version_paths("old-snapshot", 1)[0]
    data = json.loads(saved.read_text())
    data["schema_version"] = 1
    saved.write_text(json.dumps(data), encoding="utf-8")
    before = {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()}
    with pytest.raises(ValidationError, match="Unsupported schema_version"):
        if command == "inspect":
            store.inspect("old-snapshot")
        elif command == "render":
            store.render("old-snapshot")
        else:
            store.apply_layout("old-snapshot", recipe)
    assert {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()} == before


def test_recipe_round_trip_and_zero_border_preserve_output(store, sources, tmp_path):
    store.create("legacy-border", sources)
    data = layout_data()
    resolved, output = store.apply_layout("legacy-border", write_layout(tmp_path, data))
    original_output = output.read_bytes()
    saved_layout = store.version_paths("legacy-border", 1)[0]
    immutable = saved_layout.read_bytes()
    assert store.load_layout(store.load("legacy-border"), 1).recipe == InputLayout.model_validate(data)
    for border in [None, {"width_px": 0, "color": "#FF00FF"}]:
        for element in data["layers"]:
            element["border"] = border
        accepted, output = store.apply_layout(
            "legacy-border", write_layout(tmp_path, data)
        )
        assert output.read_bytes() == original_output
        for old, new in zip(resolved.geometry, accepted.geometry, strict=True):
            assert old.box_pixels == new.box_pixels
            assert old.box_normalized == new.box_normalized
    assert [v["version"] for v in store.inspect("legacy-border")["versions"]] == [1, 2, 3]
    assert saved_layout.read_bytes() == immutable


@pytest.mark.parametrize("framed", [False, True])
@pytest.mark.parametrize("border_width", [0, 2])
def test_zero_radius_and_snapshot_round_trip_preserve_exact_output(
    store, sources, tmp_path, framed, border_width
):
    store.create("legacy-radius", sources)
    data = framed_layout_data() if framed else layout_data()
    for element in data["layers"]:
        element["border"] = {"width_px": border_width, "color": "#00FF00"}
    first, output = store.apply_layout("legacy-radius", write_layout(tmp_path, data))
    expected = output.read_bytes()
    saved_layout = store.version_paths("legacy-radius", 1)[0]
    immutable = saved_layout.read_bytes()
    assert store.load_layout(store.load("legacy-radius"), 1) == first
    store.render("legacy-radius", 1)
    assert output.read_bytes() == expected
    assert saved_layout.read_bytes() == immutable
    for element in data["layers"]:
        element["corner_radius_px"] = 0
    second, output = store.apply_layout("legacy-radius", write_layout(tmp_path, data))
    assert output.read_bytes() == expected
    for old, new in zip(first.geometry, second.geometry, strict=True):
        assert old.box_pixels == new.box_pixels
        assert old.source_crop == new.source_crop


@pytest.mark.parametrize("framed, border_width, radius", [
    (False, 0, 0), (False, 2, 2), (True, 0, 3), (True, 2, 3),
])
def test_zero_tilt_and_snapshot_round_trip_preserve_exact_output(
    store, sources, tmp_path, framed, border_width, radius
):
    store.create("legacy-tilt", sources)
    data = framed_layout_data() if framed else layout_data()
    for element in data["layers"]:
        element.update(
            border={"width_px": border_width, "color": "#00FF00"},
            corner_radius_px=radius,
        )
    first, output = store.apply_layout("legacy-tilt", write_layout(tmp_path, data))
    expected = output.read_bytes()
    saved_layout = store.version_paths("legacy-tilt", 1)[0]
    immutable = saved_layout.read_bytes()
    assert store.load_layout(store.load("legacy-tilt"), 1) == first
    store.render("legacy-tilt", 1)
    assert output.read_bytes() == expected
    assert saved_layout.read_bytes() == immutable
    for element in data["layers"]:
        element["rotation_degrees"] = 0
    second, output = store.apply_layout("legacy-tilt", write_layout(tmp_path, data))
    assert output.read_bytes() == expected
    assert first.geometry == second.geometry
