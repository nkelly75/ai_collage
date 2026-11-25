# Local Python health Function

An HTTP-only placeholder: `GET /api/health` returns HTTP 200 and
`{"status":"ok"}`. It does not import the collage engine or access projects,
photos, models, storage or Azure credentials. The route is anonymous and is
for loopback-only development, not deployment.

## Start in PowerShell

Prerequisites: Core Tools 4.17.0, Python 3.12 and the packages from
`requirements-dev.txt` installed in `api\.venv`. Initial installation steps are
in the [tooling guide](../planning/018b_tooling.md).

Use a **separate PowerShell window** from Vite:

```powershell
.\api\start.ps1
```

Run from the repository root; the launcher locates the API relative to itself.
It selects `api\.venv`, disables Core Tools telemetry, keeps host secrets local
and clears inherited storage/telemetry connections for the host. It finds Core
Tools on PATH or in the standard Windows MSI location and checks that it supports
the loopback-address option. It never installs/restores packages or changes
global settings. Temporary environment and working-directory changes are
restored when it exits, including on failure. No venv activation is needed.
No `local.settings.json`, connection string, extension bundle or emulator is
needed; local settings files are ignored to avoid committing future secrets.

Keep the Vite UI at `http://127.0.0.1:5173`. CORS allows exactly that origin,
not `http://localhost:5173` or another port. Do not replace it with `*`.
`--address` controls actual binding; the host's printed `localhost` URL is not
proof that it is local-only.

From another PowerShell window:

```powershell
Invoke-RestMethod http://127.0.0.1:7071/api/health
Get-NetTCPConnection -State Listen -LocalPort 7071,5173 |
    Select-Object LocalAddress,LocalPort,OwningProcess
```

Expect `status: ok` and loopback addresses (`127.0.0.1`), not `0.0.0.0`/`::`.
Stop Functions with **Ctrl+C** in its terminal; stop Vite separately in its own
terminal.
Do not terminate unrelated processes if a port is already occupied.

## Offline tests

From the repository root:

```powershell
Set-Location api
.\.venv\Scripts\python.exe -m pytest -q
```

The tests call the handler directly and inspect route registration. Launcher
tests use a fake Core Tools command, not a running host; they exercise installed
Windows PowerShell/PowerShell 7 hosts. No Azure account or network is required.
API pytest configuration uses its own
tests/environment. Root pytest selects the existing `tests` directory so the
CLI environment does not collect API tests requiring the separate SDK.

## Runtime storage-probe warning

The runtime can report `Unable to create client for AzureWebJobsStorage` even
when storage is intentionally absent. This matches the acknowledged upstream
[Azure/azure-functions-host#11636](https://github.com/Azure/azure-functions-host/issues/11636).
The HTTP placeholder works without storage; its response does **not** certify
all internal host health probes. Do not add a storage account/emulator or
disable health monitoring merely to silence this warning.
