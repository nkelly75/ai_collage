# 018a tooling: user-run Windows setup

**Status:** Prerequisite setup complete. The user installed nvm-windows under
`C:\dev\tools\nvm` and confirmed Node **24.22.3** and npm **11.19.1** in
PowerShell. Read-only agent inspection also resolved `node.exe` and `npm.exe`
through the Windows-managed path. UI implementation remains separately gated.

This guide covers prerequisites only. It does not authorize agent-run installs
or UI implementation. See the [018a brief](018a-frontend-tooling-and-ui-skeleton.md)
for the separate frontend work.

## Existing setup and proposed choice

The read-only inventory found Bash-based nvm 0.39.1 with Node 14.20.0.
Its installation includes Windows `node.exe` and `npm.cmd`, but is not on the
agent PowerShell PATH. Preserve it for old workflows; do not reuse its directory
as the Windows version manager's root.

Use **nvm-windows and Node 24 LTS** for the new PowerShell workflow. Node 24 is a
supported LTS line, rather than the old Node 14 or a prerelease. npm comes with
Node; no separate npm installation is needed. Record the resolved patch version
after setup and pin the project's tooling during implementation.

## 1. Install the Windows version manager

Open the official [nvm-windows stable releases page](https://github.com/nvm-windows/nvm/releases/latest)
and download the Windows setup executable matching your machine architecture.
The older `coreybutler/nvm-windows` address redirects to this project.
Use the stable release, not a beta, and follow its installer instructions.
References: [official documentation](https://docs.nvm-windows.com/) and
[Microsoft's Windows Node guide](https://learn.microsoft.com/en-us/windows/dev-environment/javascript/nodejs-on-windows).

Keep its installation separate from the existing `$HOME\.nvm` Bash setup.
If prompted to adopt/replace an existing Node installation, or if an installation
path is already occupied, stop and inspect rather than delete folders or accept
a migration blindly. We have not authorized cleanup of the older toolchain.

After installation, open a **new PowerShell window**. If commands remain missing,
restart the terminal application so it picks up the installer-updated PATH.
Confirm that the Windows executable is found:

```powershell
Get-Command nvm -All | Select-Object Name,Source
nvm version
nvm --help
```

## 2. Install and select Node

The following are user-run commands that download Node and change the selected
Windows version. The current nvm-windows documentation supports major-version
selection; see [command workflows](https://docs.nvm-windows.com/guide/command-workflows/).
If your installed release reports different syntax, stop and check its help.

```powershell
nvm install 24
nvm use 24
node --version
npm --version
Get-Command node,npm -All | Select-Object Name,Source
node -p "process.execPath"
```

Expect Node `v24.x` and command paths belonging to the Windows-managed setup,
not the older Bash installation. This setup exposes `npm.exe`; plain `npm`
works and `npm.cmd` need not resolve. Do not relax machine execution policy
just to run npm.

Version switching can affect other terminals using the Windows manager.
Leave Bash startup files and the old Node installation unchanged for now.
The Copilot app may also need restarting before its tools inherit the new PATH.

## Stop here for now

No Azure Functions Core Tools, Azurite, Docker, SWA CLI, or Aspire is needed for
018a. Do not install global frontend packages or scaffold the application yet.
Once Node/npm resolve correctly, tooling is ready for the separately approved
frontend step. Package restore will require downloads; the sample UI itself
will not call model or cloud services.
