import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows launcher")

ENV_NAMES = (
    "PATH", "VIRTUAL_ENV", "FUNCTIONS_WORKER_RUNTIME",
    "FUNCTIONS_CORE_TOOLS_TELEMETRY_OPTOUT", "AzureWebJobsSecretStorageType",
    "AzureWebJobsStorage", "AzureWebJobsDashboard",
    "APPLICATIONINSIGHTS_CONNECTION_STRING", "APPINSIGHTS_INSTRUMENTATIONKEY",
    "PYTHONPATH", "AI_COLLAGE_API_AUTHORITY", "AI_COLLAGE_UI_ORIGIN",
    "FUNCTIONS_REQUEST_BODY_SIZE_LIMIT",
)


@pytest.fixture(params=["powershell.exe", "pwsh.exe"])
def shell(request):
    executable = shutil.which(request.param)
    if executable is None:
        pytest.skip(f"{request.param} is not installed")
    return executable


@pytest.fixture
def launcher(tmp_path):
    api = tmp_path / "test api"
    scripts = api / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").touch()
    shutil.copyfile(Path(__file__).parents[2] / "api" / "start.ps1", api / "start.ps1")
    tools = tmp_path / "tools"
    tools.mkdir()
    shim = tools / "fake_func.py"
    shim.write_text(
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "if sys.argv[1:] == ['--version']:\n"
        "    print(os.environ.get('TEST_FUNC_VERSION', '4.17.0'))\n"
        "    sys.exit(0)\n"
        "Path(os.environ['TEST_CAPTURE']).write_text(json.dumps({\n"
        "    'args': sys.argv[1:], 'cwd': os.getcwd(),\n"
        "    'env': {name: os.environ.get(name) for name in os.environ['TEST_ENV_NAMES'].split(',')}\n"
        "}))\n"
        "sys.exit(int(os.environ.get('TEST_FUNC_EXIT', '0')))\n",
        encoding="utf-8",
    )
    (tools / "func.cmd").write_text(
        f'@"{sys.executable}" "{shim}" %*\n@exit /b %errorlevel%\n',
        encoding="utf-8",
    )
    return api, tools, tmp_path / "capture.json"


def run_launcher(shell, launcher, *, unset=(), arguments=None, **overrides):
    api, tools, capture = launcher
    env = os.environ.copy()
    env.update({name: "original-test-value" for name in ENV_NAMES})
    env.update(
        PATH=f"{tools};{os.environ['PATH']}",
        TEST_START_SCRIPT=str(api / "start.ps1"),
        TEST_CAPTURE=str(capture),
        TEST_ENV_NAMES=",".join(ENV_NAMES),
        TEST_START_ARGUMENTS=json.dumps(arguments or {}),
    )
    env.update(overrides)
    for name in unset:
        env.pop(name, None)
    result = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", """
$names = $env:TEST_ENV_NAMES -split ','
$before = @{}
foreach ($name in $names) { $before[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$location = (Get-Location).Path
$failure = $null
$startArguments = @{}
($env:TEST_START_ARGUMENTS | ConvertFrom-Json).PSObject.Properties | ForEach-Object {
    $startArguments[$_.Name] = $_.Value
}
try { & $env:TEST_START_SCRIPT @startArguments } catch { $failure = $_.Exception.Message }
$changed = @($names | Where-Object {
    [Environment]::GetEnvironmentVariable($_, 'Process') -cne $before[$_]
})
@{ changed = $changed; restoredLocation = ((Get-Location).Path -eq $location); error = $failure } |
    ConvertTo-Json -Compress
if ($failure) { exit 1 }
"""],
        cwd=api.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout.strip(), result.stderr
    state = json.loads(result.stdout.strip().splitlines()[-1])
    assert state["changed"] == []
    assert state["restoredLocation"] is True
    return result.returncode, state["error"]


@pytest.mark.parametrize("exit_code,clear_previous", [(0, False), (9, False), (0, True)])
def test_launcher_configures_only_child_host_and_restores_caller(shell, launcher, exit_code, clear_previous):
    api, tools, capture = launcher
    code, error = run_launcher(
        shell, launcher,
        unset=ENV_NAMES[1:] if clear_previous else (),
        TEST_FUNC_EXIT=str(exit_code),
    )
    assert code == (0 if exit_code == 0 else 1)
    if exit_code == 0:
        assert error is None
    else:
        assert "exited with code 9" in error
    child = json.loads(capture.read_text())
    assert child["args"] == [
        "start", "--address", "127.0.0.1", "--port", "7071",
        "--cors", "http://127.0.0.1:5173",
    ]
    assert Path(child["cwd"]) == api
    assert child["env"]["VIRTUAL_ENV"] == str(api / ".venv")
    child_path = child["env"]["PATH"].split(";")
    assert child_path[0] == str(api / ".venv" / "Scripts")
    assert str(tools) in child_path[1:]
    assert child["env"]["FUNCTIONS_WORKER_RUNTIME"] == "python"
    assert child["env"]["FUNCTIONS_CORE_TOOLS_TELEMETRY_OPTOUT"] == "1"
    assert child["env"]["AzureWebJobsSecretStorageType"] == "files"
    assert child["env"]["PYTHONPATH"].split(";")[0] == str(api.parent)
    assert child["env"]["AI_COLLAGE_API_AUTHORITY"] == "127.0.0.1:7071"
    assert child["env"]["AI_COLLAGE_UI_ORIGIN"] == "http://127.0.0.1:5173"
    assert child["env"]["FUNCTIONS_REQUEST_BODY_SIZE_LIMIT"] == "167772160"
    for name in (
        "AzureWebJobsStorage", "AzureWebJobsDashboard",
        "APPLICATIONINSIGHTS_CONNECTION_STRING", "APPINSIGHTS_INSTRUMENTATIONKEY",
    ):
        assert child["env"][name] is None


def test_launcher_reports_missing_environment_without_starting_host(shell, launcher):
    api, _, capture = launcher
    (api / ".venv" / "Scripts" / "python.exe").unlink()
    code, error = run_launcher(shell, launcher)
    assert code == 1
    assert "API environment missing" in error
    assert not capture.exists()


def test_launcher_matches_alternate_loopback_port_pair(shell, launcher):
    _, _, capture = launcher
    code, error = run_launcher(shell, launcher, arguments={
        "Port": 7072, "UiOrigin": "http://127.0.0.1:5174",
    })
    assert (code, error) == (0, None)
    child = json.loads(capture.read_text())
    assert child["args"][-4:] == ["--port", "7072", "--cors", "http://127.0.0.1:5174"]
    assert child["env"]["AI_COLLAGE_API_AUTHORITY"] == "127.0.0.1:7072"
    assert child["env"]["AI_COLLAGE_UI_ORIGIN"] == "http://127.0.0.1:5174"


@pytest.mark.parametrize("origin", ["http://foreign.example:5173", "http://127.0.0.1:5173/path"])
def test_launcher_rejects_nonlocal_or_nonorigin_cors(shell, launcher, origin):
    _, _, capture = launcher
    code, error = run_launcher(shell, launcher, arguments={"UiOrigin": origin})
    assert code == 1
    assert "UiOrigin must be an exact" in error
    assert not capture.exists()


@pytest.mark.parametrize("version", ["4.16.0", "5.0.0"])
def test_launcher_rejects_unsupported_tools_before_starting_host(shell, launcher, version):
    _, _, capture = launcher
    code, error = run_launcher(shell, launcher, TEST_FUNC_VERSION=version)
    assert code == 1
    assert "4.17.0 or newer 4.x" in error
    assert not capture.exists()
