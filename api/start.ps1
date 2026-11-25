[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$venv = Join-Path $PSScriptRoot '.venv'
if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts\python.exe') -PathType Leaf)) {
    throw 'API environment missing. Complete the user-run setup in api\README.md first.'
}

$command = Get-Command func -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
$func = if ($command) { $command.Source } else {
    $standardPath = Join-Path $env:ProgramFiles 'Microsoft\Azure Functions Core Tools\func.exe'
    if (-not (Test-Path -LiteralPath $standardPath -PathType Leaf)) {
        throw 'Azure Functions Core Tools was not found. See api\README.md for setup.'
    }
    $standardPath
}

$settings = @{
    VIRTUAL_ENV = $venv
    PATH = "$(Join-Path $venv 'Scripts');$env:PATH"
    FUNCTIONS_WORKER_RUNTIME = 'python'
    FUNCTIONS_CORE_TOOLS_TELEMETRY_OPTOUT = '1'
    AzureWebJobsSecretStorageType = 'files'
    AzureWebJobsStorage = $null
    AzureWebJobsDashboard = $null
    APPLICATIONINSIGHTS_CONNECTION_STRING = $null
    APPINSIGHTS_INSTRUMENTATIONKEY = $null
}
$previous = @{}
foreach ($name in $settings.Keys) {
    $previous[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}

Push-Location -LiteralPath $PSScriptRoot
try {
    foreach ($name in $settings.Keys) {
        $value = $settings[$name]
        # NullString removes the variable instead of creating an empty one in PowerShell 7.
        if ($null -eq $value) { $value = [NullString]::Value }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
    $versionText = (& $func --version) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw 'Core Tools version check failed.' }
    $version = $null
    if (-not [Version]::TryParse($versionText.Trim(), [ref]$version) -or
        $version.Major -ne 4 -or $version -lt [Version]'4.17.0') {
        throw 'Use Azure Functions Core Tools 4.17.0 or newer 4.x for loopback address support.'
    }

    & $func start --address 127.0.0.1 --port 7071 --cors http://127.0.0.1:5173
    if ($LASTEXITCODE -ne 0) { throw "Functions host exited with code $LASTEXITCODE." }
} finally {
    foreach ($name in $settings.Keys) {
        $value = $previous[$name]
        if ($null -eq $value) { $value = [NullString]::Value }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
    Pop-Location
}
