# 018b tooling: user-run Windows setup

**Status:** The user completed this setup and it was verified on 2026-11-25.
Separately approved implementation is recorded in [018b results](018b_results.md).
No agent-run installation was performed. The inventory and user-run setup
instructions below are retained as the installation reference.

## Inventory before user installation and selected setup

| Item | Found in the current PowerShell environment | Action |
|---|---|---|
| Python | 3.12.10, 64-bit AMD64; `py -0p` lists this runtime. | Keep it; no Python install/upgrade. |
| Existing root `.venv` | Python 3.12.10, pip 25.0.1, pytest 9.2.0; no `azure-functions` package. | Leave untouched. Create a separate `api\.venv`. |
| Functions Core Tools | Not resolved on PATH; no matching standard Windows uninstall entry or executable at the two standard Program Files locations checked. | Install the official **4.17.0 x64 MSI**. If you know of another installation, resolve that before installing a second copy. |
| Node/npm | Resolve through the existing Windows nvm-managed path. | No frontend setup/change needed. |
| Azure CLI / .NET | Commands already resolve. | No login, upgrade or additional SDK installation prescribed. |

The base Python is
`C:\Users\nkell\AppData\Local\Programs\Python\Python312\python.exe`.
Ignore the additional WindowsApps aliases; use `py -3.12` below to select the
verified interpreter explicitly.

Python 3.12 is [supported by Functions](https://learn.microsoft.com/en-us/azure/azure-functions/supported-languages#languages-by-runtime-version).
The implementation uses the Python **v2 decorator programming model**.
That model is distinct from the SDK package major version:
[`azure-functions==1.26.0`](https://pypi.org/pypi/azure-functions/1.26.0/json)
declares Python `>=3.10,<3.13`; the current 2.4.0 SDK requires Python `>=3.13`.
Do not install an unpinned SDK or upgrade Python just to obtain the newest SDK.

Prepared manifests: `api\requirements.txt` pins the plain SDK (no dev extras);
`api\requirements-dev.txt` adds pytest 9.2.0, matching the existing test-runner
version and supporting Python 3.12. No engine/model packages are needed for the
collage-agnostic placeholder. Transitive packages are resolved by pip; installed
versions and actual host checks are recorded in [018b results](018b_results.md).

## 1. Install Core Tools (user action)

Use the official
[Core Tools 4.17.0 release](https://github.com/Azure/azure-functions-core-tools/releases/tag/4.17.0)
and download **[func-cli-4.17.0-x64.msi](https://github.com/Azure/azure-functions-core-tools/releases/download/4.17.0/func-cli-4.17.0-x64.msi)**.
This follows Microsoft's
[Windows MSI installation guidance](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local#install-the-azure-functions-core-tools)
and keeps Core Tools independent of nvm/Node version switching.

Install that MSI only, not a second npm/VS Code-managed copy. Do not select the
new Functions CLI v5 preview, which also uses the `func` command. Stop for
unexpected prerequisite or replacement prompts rather than removing other tools.

Open a **new PowerShell window**, then verify:

```powershell
Get-Command func -All | Format-List Name,Source
func --version
```

Expect one intended installation and version `4.17.0`. If it is missing, resolves
multiple installations or reports another major version, stop and share the
output. The Copilot app may also need restarting to inherit the installer-updated
PATH; do not make manual global PATH or execution-policy changes to compensate.

## 2. Create and populate the API environment (user action)

From PowerShell:

```powershell
Set-Location C:\dev\git\2026\ai_collage
py -3.12 --version
if (Test-Path -LiteralPath '.\api\.venv') {
    throw 'api\.venv already exists; inspect it rather than overwrite it.'
}
py -3.12 -m venv .\api\.venv
if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed.' }
.\api\.venv\Scripts\python.exe -m pip install -r .\api\requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed; stop and share the error.' }
```

This downloads packages into the new API environment only. The existing
`.venv/` ignore rule covers the nested environment. No activation, pip upgrade,
global package installation or change to the original `.venv` is needed.

Verify the new environment without running a host:

```powershell
.\api\.venv\Scripts\python.exe -B -c "import sys, struct, azure.functions; from importlib.metadata import version; print(sys.executable); print(sys.version); print('bits:', struct.calcsize('P') * 8); print('azure-functions:', version('azure-functions')); print('pytest:', version('pytest'))"
.\api\.venv\Scripts\python.exe -m pip check
```

Expect the executable beneath `api\.venv`, Python 3.12.10/64-bit,
azure-functions 1.26.0, pytest 9.2.0 and no broken package requirements.

## Installation approval boundary

After initial setup, share the verification output above. Before separate
implementation approval, do not run `func init`, `func new`, `func start`,
deployment commands or Azure sign-in.
No Azurite, Docker, Aspire, SWA tooling or Azure account is needed for this setup.

Installation confirmation permits verification only. To also authorize the next
stage, say, for example: "Setup is complete; here is the verification output.
Please verify it and implement 018b."

Stage A ended at that handoff, without a waiting worker, polling or automatic
continuation. The user subsequently approved stage B explicitly; actual hosting,
binding, CORS and browser checks are recorded in [018b results](018b_results.md).
Current startup/stop instructions are in the [API README](../api/README.md).
