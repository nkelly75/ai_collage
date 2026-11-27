from contextlib import ExitStack
import os
from pathlib import Path

import pytest

from ai_collage.agent.conversation import Conversation
from ai_collage.engine.projects import ProjectStore
from ai_collage.storage.contracts import ProjectExists
from ai_collage.storage.local import LocalProjectStorage


@pytest.mark.parametrize("failure", ["state", "asset", "publication"])
def test_storage_publication_failure_never_exposes_partial_project(
    store, sources, tmp_path, monkeypatch, failure,
):
    prepared = ProjectStore(tmp_path / "prepared")
    project = prepared.create("trip", sources)
    state = Conversation(prepared, "trip", canvas=(100, 100)).state
    unrelated = store.create("existing", sources)
    before = {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()}
    original_link = os.link
    original_rename = Path.rename
    assets = store.photo_paths(project)

    def fail(*args, **kwargs):
        raise OSError("injected publication failure")

    if failure == "state":
        monkeypatch.setattr("ai_collage.storage.local.save", fail)
    elif failure == "asset":
        def link(source, destination):
            if destination == assets[2]:
                assert not store.project_dir("trip").exists()
                assert "trip" not in LocalProjectStorage(store).project_ids()
                return fail()
            return original_link(source, destination)
        monkeypatch.setattr("ai_collage.storage.local.os.link", link)
    else:
        def rename(source, destination):
            if destination == store.project_dir("trip"):
                return fail()
            return original_rename(source, destination)
        monkeypatch.setattr(Path, "rename", rename)

    with ExitStack() as stack:
        streams = {n: stack.enter_context(p.open("rb")) for n, p in prepared.photo_paths(project).items()}
        with pytest.raises(OSError, match="injected"):
            LocalProjectStorage(store).publish(project, state, streams)
    assert {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()} == before
    assert LocalProjectStorage(store).project_ids() == [unrelated.project_id]
    assert not list(store.projects_dir.glob(".create-web-*"))


def test_storage_refuses_existing_assets_and_cleans_only_its_new_assets(store, sources, tmp_path):
    prepared = ProjectStore(tmp_path / "prepared")
    project = prepared.create("trip", sources)
    state = Conversation(prepared, "trip", canvas=(100, 100)).state
    assets = store.photo_paths(project)
    store.uploads_dir.mkdir(parents=True)
    assets[2].write_bytes(b"existing asset")
    with ExitStack() as stack:
        streams = {n: stack.enter_context(p.open("rb")) for n, p in prepared.photo_paths(project).items()}
        with pytest.raises(FileExistsError):
            LocalProjectStorage(store).publish(project, state, streams)
    assert assets[2].read_bytes() == b"existing asset"
    assert not assets[1].exists()
    assert not store.project_dir("trip").exists()


def test_storage_publish_rechecks_existing_project_before_consuming_assets(store, sources):
    project = store.create("trip", sources)
    state = Conversation(store, "trip", canvas=(100, 100)).state
    before = {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()}
    with pytest.raises(ProjectExists):
        LocalProjectStorage(store).publish(project, state, {})
    assert {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()} == before
