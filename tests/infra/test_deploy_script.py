import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows deployment wrapper")

SUBSCRIPTION = "11111111-1111-1111-1111-111111111111"
PRINCIPAL = "22222222-2222-2222-2222-222222222222"
IDENTITY_VARIABLE = "AI_COLLAGE_INFRA_DEVELOPER_OBJECT_ID"


@pytest.fixture(params=["powershell.exe", "pwsh.exe"])
def shell(request):
    executable = shutil.which(request.param)
    if executable is None:
        pytest.skip(f"{request.param} is not installed")
    return executable


@pytest.fixture
def deployment(tmp_path):
    infra = tmp_path / "test infra"
    infra.mkdir()
    shutil.copyfile(Path(__file__).parents[2] / "infra" / "deploy.ps1", infra / "deploy.ps1")
    tools = tmp_path / "tools"
    tools.mkdir()
    shim = tools / "fake_az.py"
    shim.write_text(
        """import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with Path(os.environ["TEST_CAPTURE"]).open("a") as capture:
    capture.write(json.dumps(args) + "\\n")
operation = " ".join(args[:3] if args[0] == "deployment" else args[:2])
if operation == os.environ.get("TEST_FAIL"):
    print("simulated Azure CLI failure", file=sys.stderr)
    sys.exit(9)
if args[:2] == ["bicep", "version"]:
    print("Bicep CLI version test")
elif args[:2] == ["account", "show"]:
    print(json.dumps({
        "id": os.environ.get("TEST_ACCOUNT_ID", os.environ["TEST_SUBSCRIPTION"]),
        "state": "Enabled", "name": "Test subscription", "tenantId": "test-tenant",
        "user": {"type": os.environ.get("TEST_USER_TYPE", "user")},
    }))
elif args[:2] == ["rest", "--method"]:
    assert args[args.index("--url") + 1] == "https://graph.microsoft.com/v1.0/me?$select=id"
    assert args[args.index("--method") + 1] == "get"
    print(os.environ.get("TEST_PRINCIPAL", os.environ["TEST_EXPECTED_PRINCIPAL"]))
elif args[:2] == ["bicep", "build"]:
    Path(args[args.index("--outfile") + 1]).write_text("{}")
elif args[:2] == ["bicep", "build-params"]:
    Path(args[args.index("--outfile") + 1]).write_text(json.dumps({"parameters": {
        "resourceGroupName": {"value": "ai-collage-dev"},
        "location": {"value": "eastus"},
        "developerObjectId": {"value": os.environ["AI_COLLAGE_INFRA_DEVELOPER_OBJECT_ID"]},
    }}))
elif args[:3] in [["deployment", "sub", "what-if"], ["deployment", "sub", "create"]]:
    parameters = json.loads(Path(args[args.index("--parameters") + 1][1:]).read_text())
    assert parameters["parameters"]["developerObjectId"]["value"] == os.environ["TEST_EXPECTED_PRINCIPAL"]
    print("{}")
else:
    raise AssertionError(args)
""",
        encoding="utf-8",
    )
    (tools / "az.cmd").write_text(
        f'@"{sys.executable}" "{shim}" %*\n@exit /b %errorlevel%\n',
        encoding="utf-8",
    )
    return infra, tools, tmp_path / "capture.jsonl"


def run_deployment(shell, deployment, *, arguments=None, clear_identity=False, **overrides):
    infra, tools, capture = deployment
    env = os.environ.copy()
    env.update(
        PATH=f"{tools};{os.environ['PATH']}",
        TEST_SCRIPT=str(infra / "deploy.ps1"),
        TEST_CAPTURE=str(capture),
        TEST_SUBSCRIPTION=SUBSCRIPTION,
        TEST_EXPECTED_PRINCIPAL=PRINCIPAL,
        TEST_ARGUMENTS=json.dumps({"SubscriptionId": SUBSCRIPTION, **(arguments or {})}),
    )
    env[IDENTITY_VARIABLE] = "original-test-value"
    if clear_identity:
        env.pop(IDENTITY_VARIABLE)
    env.update(overrides)
    result = subprocess.run(
        [shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", """
$variable = 'AI_COLLAGE_INFRA_DEVELOPER_OBJECT_ID'
$before = [Environment]::GetEnvironmentVariable($variable, 'Process')
$location = (Get-Location).Path
$failure = $null
$arguments = @{}
($env:TEST_ARGUMENTS | ConvertFrom-Json).PSObject.Properties | ForEach-Object {
    $arguments[$_.Name] = $_.Value
}
try { & $env:TEST_SCRIPT @arguments } catch { $failure = $_.Exception.Message }
@{
    restoredEnvironment = ([Environment]::GetEnvironmentVariable($variable, 'Process') -ceq $before)
    restoredLocation = ((Get-Location).Path -eq $location)
    error = $failure
} | ConvertTo-Json -Compress
if ($failure) { exit 1 }
"""],
        cwd=infra.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.stdout.strip(), result.stderr
    state = json.loads(result.stdout.strip().splitlines()[-1])
    assert state["restoredEnvironment"] is True
    assert state["restoredLocation"] is True
    calls = [json.loads(line) for line in capture.read_text().splitlines()]
    for call in calls:
        if call[0] != "bicep":
            assert call[call.index("--subscription") + 1] == SUBSCRIPTION
        if "--outfile" in call:
            assert not Path(call[call.index("--outfile") + 1]).parent.exists()
    return result.returncode, state["error"], calls


@pytest.mark.parametrize("arguments,applies", [
    ({}, False),
    ({"Deploy": True, "WhatIf": True}, False),
    ({"Deploy": True, "Confirm": False}, True),
])
@pytest.mark.parametrize("clear_identity", [False, True])
def test_preview_is_default_and_apply_requires_explicit_request(shell, deployment, arguments, applies, clear_identity):
    code, error, calls = run_deployment(
        shell, deployment, arguments=arguments, clear_identity=clear_identity,
    )
    assert (code, error) == (0, None)
    deployments = [call[:3] for call in calls if call[0] == "deployment"]
    assert deployments == (
        [["deployment", "sub", "what-if"], ["deployment", "sub", "create"]]
        if applies else [["deployment", "sub", "what-if"]]
    )


@pytest.mark.parametrize("operation", [
    "bicep version", "account show", "rest --method",
    "bicep build", "bicep build-params", "deployment sub what-if", "deployment sub create",
])
def test_cli_failure_stops_without_retry_or_deploying_past_failed_preview(shell, deployment, operation):
    code, error, calls = run_deployment(
        shell, deployment, arguments={"Deploy": True, "Confirm": False},
        TEST_FAIL=operation,
    )
    assert code == 1 and error
    last = calls[-1]
    assert " ".join(last[:3] if last[0] == "deployment" else last[:2]) == operation
    assert len({tuple(call) for call in calls}) == len(calls)


@pytest.mark.parametrize("overrides", [
    {"TEST_ACCOUNT_ID": "33333333-3333-3333-3333-333333333333"},
    {"TEST_USER_TYPE": "servicePrincipal"},
    {"TEST_PRINCIPAL": "invalid-user"},
])
def test_unexpected_identity_or_subscription_stops_before_preview(shell, deployment, overrides):
    code, error, calls = run_deployment(shell, deployment, **overrides)
    assert code == 1 and error
    assert not any(call[0] == "deployment" for call in calls)


def test_noninteractive_apply_cannot_skip_confirmation(shell, deployment):
    code, error, calls = run_deployment(shell, deployment, arguments={"Deploy": True})
    assert code == 1 and error
    assert [call[:3] for call in calls if call[0] == "deployment"] == [
        ["deployment", "sub", "what-if"],
    ]
