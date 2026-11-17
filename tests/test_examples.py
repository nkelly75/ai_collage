from pathlib import Path

import pytest

from ai_collage.projects import ProjectStore

from .helpers import photo_file


REPO = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("recipe", sorted((REPO / "examples").glob("*.json")), ids=lambda p: p.stem)
def test_curated_recipes_render_and_reopen_with_matching_photo_mapping(tmp_path, recipe):
    paths = [
        photo_file(tmp_path / f"{number}.png", (30, 40), color)
        for number, color in enumerate(["red", "green", "blue", "yellow"], start=1)
    ]
    if "london_eye" in recipe.name:
        paths = [paths[0], paths[2], paths[3]]
    store = ProjectStore(tmp_path / "data")
    store.create("example", paths)
    saved, output = store.apply_layout("example", recipe)
    expected = output.read_bytes()
    assert {layer.photo_id for layer in saved.recipe.layers} == set(range(1, len(paths) + 1))
    reopened = ProjectStore(store.data_dir)
    assert reopened.load_layout(reopened.load("example"), 1) == saved
    reopened.render("example")
    assert output.read_bytes() == expected
