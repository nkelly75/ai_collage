from pathlib import Path
import copy
import json

import pytest

from ai_collage.projects import ProjectStore

from .helpers import framed_layout_data, layout_data, run_cli, write_layout


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
    for element in data["layers"]:
        element["rotation_degrees"] = angle
    if framed:
        for element in data["layers"]:
            element["crop"].update(zoom=2, pan_x=0.25, pan_y=0.75)
            element["corner_radius_px"] = 2
    if border_width:
        for element in data["layers"]:
            element["border"] = {"width_px": border_width, "color": "#00FF00"}
    path = write_layout(tmp_path, data)
    applied = run_cli(data_dir, "apply-layout", "--project", "cli", "--layout", path)
    assert applied.returncode == 0, applied.stderr
    assert json.loads(applied.stdout)["version"] == 1
    saved = json.loads(Path(json.loads(applied.stdout)["layout_path"]).read_text())
    assert all(element["rotation_degrees"] == angle for element in saved["recipe"]["layers"])
    assert all(
        (element["rotated_box_pixels"] is not None) == (angle != 0)
        for element in saved["geometry"]
    )
    if framed:
        assert all(element["source_crop"] is not None for element in saved["geometry"])
        assert all(element["crop"]["zoom"] == 2 for element in saved["recipe"]["layers"])
        assert all(element["corner_radius_px"] == 2 for element in saved["recipe"]["layers"])
    for source in sources:
        source.unlink()
    inspected = run_cli(data_dir, "inspect", "--project", "cli")
    assert inspected.returncode == 0, inspected.stderr
    state = json.loads(inspected.stdout)
    assert [p["photo_id"] for p in state["photos"]] == [1, 2]
    assert state["current_version"] == 1
    output = Path(state["versions"][0]["render_path"])
    original_output = output.read_bytes()
    output.unlink()
    rendered = run_cli(data_dir, "render", "--project", "cli", "--version", "1")
    assert rendered.returncode == 0, rendered.stderr
    assert output.read_bytes() == original_output
    invalid = copy.deepcopy(layout_data())
    invalid["layers"][0]["photo_id"] = 99
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


def test_old_archive_commands_fail_without_writes(tmp_path, sources):
    data_dir = tmp_path / "old-data"
    store = ProjectStore(data_dir)
    project = store.create("archive", sources)
    metadata = project.model_dump()
    metadata["schema_version"] = 1
    for photo in metadata["photos"]:
        photo["source_image_id"] = photo.pop("photo_id")
    path = store.project_dir("archive") / "project.json"
    path.write_text(json.dumps(metadata), encoding="utf-8")
    before = {p: p.read_bytes() for p in data_dir.rglob("*") if p.is_file()}
    recipe = write_layout(tmp_path)
    for command, extra in [
        ("create", ["--images", *sources]),
        ("inspect", []),
        ("apply-layout", ["--layout", recipe]),
        ("render", []),
    ]:
        result = run_cli(data_dir, command, "--project", "archive", *extra)
        assert result.returncode == 1
        assert result.stdout == ""
        assert (
            "already exists" if command == "create" else "Unsupported schema_version"
        ) in result.stderr
        assert {p: p.read_bytes() for p in data_dir.rglob("*") if p.is_file()} == before
