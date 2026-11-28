[CmdletBinding()]
param(
    [ValidateRange(1, 65535)][int]$Port = 7071,
    [string]$UiOrigin = 'http://127.0.0.1:5173',
    [ValidateSet('Local', 'Blob')][string]$StorageBackend = 'Local',
    [string]$BlobNamespace = 'web-dev',
    [string]$MetricsPath,
    [switch]$Live,
    [string]$CallBudgetPath,
    [ValidateRange(1, 200)][int]$MaxCalls = 12,
    [string]$TrialProject
)

$ErrorActionPreference = 'Stop'
$blobNames = @(
    'AI_COLLAGE_BLOB_ACCOUNT_URL', 'AI_COLLAGE_BLOB_CONTAINER',
    'AI_COLLAGE_BLOB_SUBSCRIPTION_ID', 'AI_COLLAGE_BLOB_NAMESPACE',
    'AI_COLLAGE_BLOB_PROOF_LEDGER'
)
if ($StorageBackend -ne 'Blob' -and $PSBoundParameters.ContainsKey('BlobNamespace')) {
    throw 'BlobNamespace requires -StorageBackend Blob.'
}
$blobSettings = @{}
if ($StorageBackend -eq 'Blob') {
    $target = @{
        AI_COLLAGE_BLOB_ACCOUNT_URL = 'https://stclgdevbik2twby4e2zu.blob.core.windows.net'
        AI_COLLAGE_BLOB_CONTAINER = 'collage'
        AI_COLLAGE_BLOB_SUBSCRIPTION_ID = '0c6a09a0-a933-49df-9b6b-b8f65440332f'
    }
    foreach ($name in $target.Keys) {
        $value = [Environment]::GetEnvironmentVariable($name, 'Process')
        if ($null -ne $value -and $value -cne $target[$name] -and
            -not ($name -eq 'AI_COLLAGE_BLOB_ACCOUNT_URL' -and $value -ceq "$($target[$name])/")) {
            throw 'Blob launches require the recorded development target; conflicting environment setting.'
        }
        $blobSettings[$name] = $target[$name]
    }
    if ($BlobNamespace -cnotmatch '^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$') {
        throw 'Supply a valid BlobNamespace.'
    }
    $blobSettings['AI_COLLAGE_BLOB_NAMESPACE'] = $BlobNamespace
    $ledger = $env:AI_COLLAGE_BLOB_PROOF_LEDGER
    if ($null -ne $ledger -and (
        -not $ledger -or -not [IO.Path]::IsPathRooted($ledger) -or -not (Test-Path -LiteralPath $ledger -PathType Leaf) -or
        -not $BlobNamespace.StartsWith('proof-019c-')
    )) { throw 'Invalid opt-in Blob proof ledger.' }
    $blobSettings['AI_COLLAGE_BLOB_PROOF_LEDGER'] = $ledger
}
if ($CallBudgetPath -or $TrialProject -or $PSBoundParameters.ContainsKey('MaxCalls')) {
    if (-not $Live -or -not $CallBudgetPath -or -not $TrialProject -or
        [IO.Path]::GetPathRoot($CallBudgetPath) -notmatch '^(?:[A-Za-z]:\\|\\\\)') {
        throw 'Trial configuration requires -Live, -TrialProject and an absolute -CallBudgetPath (optional -MaxCalls).'
    }
}
if ($PSBoundParameters.ContainsKey('MetricsPath')) {
    if (
        -not $MetricsPath -or
        [IO.Path]::GetPathRoot($MetricsPath) -notmatch '^(?:[A-Za-z]:\\|\\\\)' -or
        [IO.Path]::GetExtension($MetricsPath) -ne '.jsonl' -or
        -not (Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($MetricsPath)) -PathType Container) -or
        ((Test-Path -LiteralPath $MetricsPath) -and -not (Test-Path -LiteralPath $MetricsPath -PathType Leaf))
    ) { throw 'MetricsPath requires an absolute .jsonl file in an existing directory.' }
    $reservedPaths = @($CallBudgetPath, $blobSettings['AI_COLLAGE_BLOB_PROOF_LEDGER'])
    if ($blobSettings['AI_COLLAGE_BLOB_PROOF_LEDGER']) {
        $reservedPaths += [IO.Path]::ChangeExtension($blobSettings['AI_COLLAGE_BLOB_PROOF_LEDGER'], '.objects.jsonl')
    }
    foreach ($reserved in $reservedPaths) {
        if ($reserved -and [IO.Path]::GetFullPath($reserved) -eq [IO.Path]::GetFullPath($MetricsPath)) {
            throw 'MetricsPath must not share a call-budget or proof ledger.'
        }
    }
}
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
    PYTHON_SCRIPT_FILE_NAME = 'function_app.py'
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
    AI_COLLAGE_LIVE = $(if ($Live) { '1' } else { '0' })
    AI_COLLAGE_CALL_BUDGET_PATH = $(if ($CallBudgetPath) { $CallBudgetPath } else { $null })
    AI_COLLAGE_MAX_CALLS = $(if ($CallBudgetPath) { "$MaxCalls" } else { $null })
    AI_COLLAGE_TRIAL_PROJECT = $(if ($TrialProject) { $TrialProject } else { $null })
    AI_COLLAGE_STORAGE_BACKEND = $StorageBackend.ToLowerInvariant()
    AI_COLLAGE_METRICS_PATH = $(if ($MetricsPath) { $MetricsPath } else { $null })
}
foreach ($name in $blobNames) {
    $settings[$name] = if ($StorageBackend -eq 'Blob') {
        $blobSettings[$name]
    } else { $null }
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

    if ($StorageBackend -eq 'Blob') {
        Write-Host "Storage: Blob; account: $($settings['AI_COLLAGE_BLOB_ACCOUNT_URL'])"
        Write-Host "Container: $($settings['AI_COLLAGE_BLOB_CONTAINER']); namespace: $BlobNamespace"
    } else {
        Write-Host 'Storage: Local'
    }
    if ($MetricsPath) { Write-Host "Local request metrics: $MetricsPath" }
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
