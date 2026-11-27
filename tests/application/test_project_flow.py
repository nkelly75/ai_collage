from contextlib import ExitStack
import os
from pathlib import Path
import subprocess
import sys

import pytest

from ai_collage.agent.conversation import Conversation
from ai_collage.application.projects import ProjectFlow, ProjectSetup, configured_store
from ai_collage.engine.projects import ProjectStore
from ai_collage.storage import LocalProjectStorage, ProjectExists


def test_default_data_root_is_checkout_relative_and_independent_of_cwd(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_COLLAGE_DATA_DIR", raising=False)
    monkeypatch.chdir(tmp_path)
    assert configured_store().data_dir == Path(__file__).resolve().parents[2] / ".collage-data-web"
    assert list(tmp_path.iterdir()) == []


def test_competing_creates_from_processes_publish_once(tmp_path, sources):
    source = sources[0]
    code = """
import sys
from pathlib import Path
from ai_collage.engine.projects import ProjectStore
from ai_collage.application.projects import FlowError, ProjectFlow, ProjectSetup
try:
    with open(sys.argv[2], 'rb') as a, open(sys.argv[2], 'rb') as b:
        ProjectFlow(ProjectStore(Path(sys.argv[1]))).create(
            ProjectSetup(project_id='race', canvas={'width':100,'height':100}), [a,b])
    print('created')
except FlowError as error:
    print(error.code)
"""
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])}
    processes = [subprocess.Popen([sys.executable, "-c", code, str(tmp_path / "data"), str(source)],
                 env=env, stdout=subprocess.PIPE, text=True) for _ in range(2)]
    outcomes = [p.communicate(timeout=30)[0].strip() for p in processes]
    assert outcomes.count("created") == 1
    assert set(outcomes) <= {"created", "project_busy", "project_exists"}
    assert len(ProjectStore(tmp_path / "data").load("race").photos) == 2


def test_initialized_project_lifecycle_uses_storage_and_reopens_without_writes(store, sources, tmp_path):
    guard_store = ProjectStore(tmp_path / "guards")
    flow = ProjectFlow(guard_store, LocalProjectStorage(store))
    with sources[0].open("rb") as a, sources[1].open("rb") as b:
        detail = flow.create(ProjectSetup(
            project_id="trip", canvas={"width": 1200, "height": 1800},
        ), [a, b])
    assert not guard_store.projects_dir.exists()
    before = {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()}
    reopened = ProjectStore(store.data_dir)
    flow = ProjectFlow(guard_store, LocalProjectStorage(reopened))
    assert flow.detail("trip") == detail
    assert flow.list() == [{
        "project_id": "trip", "canvas": {"width": 1200, "height": 1800}, "photo_count": 2,
    }]
    for number, source in enumerate(sources, 1):
        assert flow.photo("trip", number) == (source.read_bytes(), "image/png")
    conversation = Conversation(reopened, "trip", read_only=True)
    assert conversation.state.history == []
    assert (conversation.state.controls.width, conversation.state.controls.height) == (1200, 1800)
    assert {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()} == before


def test_existing_initialized_project_reopens_through_storage_without_rewriting(store, sources):
    project = store.create("existing", sources)
    conversation = Conversation(store, "existing", canvas=(900, 1600))
    before = {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()}
    flow = ProjectFlow(ProjectStore(store.data_dir))
    assert flow._load("existing") == (project, conversation.state)
    assert flow.list() == [{
        "project_id": "existing", "canvas": {"width": 900, "height": 1600}, "photo_count": 2,
    }]
    assert flow.photo("existing", 2) == (sources[1].read_bytes(), "image/png")
    assert {p: p.read_bytes() for p in store.data_dir.rglob("*") if p.is_file()} == before


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
        monkeypatch.setattr("ai_collage.storage.save", fail)
    elif failure == "asset":
        def link(source, destination):
            if destination == assets[2]:
                assert not store.project_dir("trip").exists()
                assert "trip" not in LocalProjectStorage(store).project_ids()
                return fail()
            return original_link(source, destination)
        monkeypatch.setattr("ai_collage.storage.os.link", link)
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
