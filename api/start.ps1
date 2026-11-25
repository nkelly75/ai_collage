[CmdletBinding()]
param(
    [ValidateRange(1, 65535)][int]$Port = 7071,
    [string]$UiOrigin = 'http://127.0.0.1:5173'
)

$ErrorActionPreference = 'Stop'
$origin = $null
if (-not [Uri]::TryCreate($UiOrigin, [UriKind]::Absolute, [ref]$origin) -or
    $origin.Scheme -ne 'http' -or $origin.Host -ne '127.0.0.1' -or
    $origin.AbsolutePath -ne '/' -or $origin.Query -or $origin.Fragment -or $origin.UserInfo -or
    $UiOrigin -ne $origin.GetLeftPart([UriPartial]::Authority)) {
    throw 'UiOrigin must be an exact http://127.0.0.1:<port> origin.'
}
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
    PYTHONPATH = "$(Split-Path -Parent $PSScriptRoot);$env:PYTHONPATH"
    AI_COLLAGE_API_AUTHORITY = "127.0.0.1:$Port"
    AI_COLLAGE_UI_ORIGIN = $UiOrigin
    FUNCTIONS_REQUEST_BODY_SIZE_LIMIT = '167772160'
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

    & $func start --address 127.0.0.1 --port $Port --cors $UiOrigin
    if ($LASTEXITCODE -ne 0) { throw "Functions host exited with code $LASTEXITCODE." }
} finally {
    foreach ($name in $settings.Keys) {
        $value = $previous[$name]
        if ($null -eq $value) { $value = [NullString]::Value }
        [Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
    Pop-Location
}
