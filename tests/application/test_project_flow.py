import os
from pathlib import Path
import subprocess
import sys

from ai_collage.application.projects import configured_store
from ai_collage.engine.projects import ProjectStore


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
