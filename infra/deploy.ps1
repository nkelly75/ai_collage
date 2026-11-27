[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)][guid]$SubscriptionId,
    [switch]$Deploy
)

$ErrorActionPreference = 'Stop'
if ($SubscriptionId -eq [guid]::Empty) { throw 'SubscriptionId must not be empty.' }

$command = Get-Command az -CommandType Application -ErrorAction SilentlyContinue |
    Select-Object -First 1
if (-not $command) { throw 'Azure CLI was not found. See infra\README.md for prerequisites.' }
$az = $command.Source

function Invoke-AzureCli {
    param([string[]]$Arguments)
    & $az @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI '$($Arguments[0..1] -join ' ')' exited with code $LASTEXITCODE."
    }
}

# Check first so subsequent build commands cannot implicitly install a missing compiler.
Invoke-AzureCli -Arguments @('bicep', 'version') | Out-Host
$subscription = $SubscriptionId.ToString()
$account = (Invoke-AzureCli -Arguments @(
    'account', 'show', '--subscription', $subscription, '--output', 'json'
)) -join "`n" | ConvertFrom-Json
if ($account.id -ne $subscription -or $account.state -ne 'Enabled' -or
    $account.user.type -ne 'user') {
    throw 'Use an enabled target subscription and a signed-in Azure CLI user, not a service principal.'
}
$principalText = ((Invoke-AzureCli -Arguments @(
    'rest', '--method', 'get', '--url', 'https://graph.microsoft.com/v1.0/me?$select=id',
    '--subscription', $subscription, '--query', 'id', '--output', 'tsv'
)) -join "`n").Trim()
$principal = [guid]::Empty
if (-not [guid]::TryParse($principalText, [ref]$principal) -or $principal -eq [guid]::Empty) {
    throw 'Could not resolve the signed-in developer object ID in the target tenant.'
}

$variableName = 'AI_COLLAGE_INFRA_DEVELOPER_OBJECT_ID'
$previous = [Environment]::GetEnvironmentVariable($variableName, 'Process')
$scratch = Join-Path ([IO.Path]::GetTempPath()) "collage-infra-$([guid]::NewGuid().ToString('N'))"
$templateFile = Join-Path $scratch 'main.json'
$parametersFile = Join-Path $scratch 'dev.parameters.json'
[IO.Directory]::CreateDirectory($scratch) | Out-Null
try {
    [Environment]::SetEnvironmentVariable($variableName, $principal.ToString(), 'Process')
    Invoke-AzureCli -Arguments @(
        'bicep', 'build', '--file', (Join-Path $PSScriptRoot 'main.bicep'), '--outfile', $templateFile
    ) | Out-Host
    Invoke-AzureCli -Arguments @(
        'bicep', 'build-params', '--file', (Join-Path $PSScriptRoot 'dev.bicepparam'),
        '--outfile', $parametersFile
    ) | Out-Host
    $parameters = (Get-Content -LiteralPath $parametersFile -Raw | ConvertFrom-Json).parameters
    $group = $parameters.resourceGroupName.value
    $location = $parameters.location.value
    Write-Host "Subscription: $($account.name) ($subscription)"
    Write-Host "Tenant: $($account.tenantId)"
    Write-Host "Resource group: $group; region: $location"
    Write-Host "Developer object ID: $principal; role: Storage Blob Data Contributor on the collage container"

    $deploymentArguments = @(
        '--subscription', $subscription, '--name', 'ai-collage-dev-storage',
        '--location', $location, '--template-file', $templateFile,
        '--parameters', "@$parametersFile"
    )
    Invoke-AzureCli -Arguments (@('deployment', 'sub', 'what-if') + $deploymentArguments) | Out-Host
    if ($Deploy -and $PSCmdlet.ShouldProcess(
        "$subscription / $group",
        "Deploy development storage and grant container access to $principal"
    )) {
        Invoke-AzureCli -Arguments (
            @('deployment', 'sub', 'create') + $deploymentArguments +
            @('--query', 'properties.outputs', '--output', 'json')
        ) | Out-Host
    }
} finally {
    if ($null -eq $previous) { $previous = [NullString]::Value }
    [Environment]::SetEnvironmentVariable($variableName, $previous, 'Process')
    foreach ($path in @($templateFile, $parametersFile)) {
        if ([IO.File]::Exists($path)) { [IO.File]::Delete($path) }
    }
    [IO.Directory]::Delete($scratch)
}
