# Development Azure infrastructure

Development storage infrastructure for
[019b](../planning/019-storage-abstraction-and-blob-persistence.md#sequence-and-status).
These files do not integrate Blob storage into the application. CLI/replay and
today's Functions/web persistence remain local.

The [019b infrastructure record](../planning/019b-initial-blob-integration.md#deployed-development-target)
records the deployed account and verified settings. Application integration
has a [separate draft specification](../planning/019b-blob-storage-implementation.md)
and remains unapproved.

## Scope and security

`main.bicep` creates the **ai-collage-dev** resource group in **East US**.
Its small resource-group-scoped `storage.bicep` module creates:

- One `StorageV2` account, `Standard_LRS`, Hot tier. The name is
  `stclgdev` plus a deterministic suffix from the subscription and resource group.
- One private `collage` container.
- **Storage Blob Data Contributor** for the signed-in developer, scoped to that
  container, not the account or subscription.

HTTPS-only, minimum TLS 1.2, anonymous blob access disabled, Shared Key access
disabled, OAuth default, and cross-tenant replication disabled. Azure encrypts
storage at rest using Microsoft-managed keys by default.
The public service endpoint is intentionally enabled without an IP firewall,
VNet or private endpoint: requests still require Entra authentication and the
appropriate role. The browser will not receive storage credentials.

No production resources, Function App, Functions host storage, monitoring stack,
or Foundry changes. The existing `ai_nk_2026` group is outside this deployment.
Future deployed resources belong in a separate production resource group/account.
Host storage and managed-identity permissions will be decided with that work.

## Prerequisites

Use Azure CLI and its Bicep compiler from PowerShell (Windows PowerShell 5.1 or
PowerShell 7). The wrapper does not install tools, log in, change the default
subscription, register providers, or retrieve account keys.

Check tooling with `az version` and `az bicep version`. If the compiler is missing,
install it explicitly with `az bicep install` after approving the tooling change.
Use `az login` interactively if needed. The selected subscription must be enabled
and accessible to that signed-in user.

Deployment and what-if require sufficient management permissions at subscription
scope to create the resource group, plus storage/deployment permissions and
`Microsoft.Authorization/roleAssignments/write` for the scoped grant.
Subscription Owner satisfies these; Contributor alone cannot grant the role.
The CLI must also be able to resolve your own user object in the target tenant.
No directory role is granted by these templates.

## Preview, then deploy

From the repository root, supply the intended subscription explicitly:

```powershell
$subscription = '<subscription-id>'
.\infra\deploy.ps1 -SubscriptionId $subscription
```

This performs **what-if only**, including the resource group. Review the printed
subscription, tenant, developer object ID, region and all proposed resources.
Do not proceed if Azure reports ignored resources, incomplete expansion or
unexpected changes. What-if is a preview, not a guarantee of deployment success.
It can also flag undeclared service/container defaults as property removals;
the 019b record notes the post-deployment predictions observed here. These are
not resource deletions, but still inspect the differences rather than treating
all modifications as harmless.
If the provider is unregistered or permissions are insufficient, stop and resolve
that explicitly rather than weakening storage settings.

After review, explicitly request deployment:

```powershell
.\infra\deploy.ps1 -SubscriptionId $subscription -Deploy
```

The wrapper compiles fresh templates, reruns what-if, then prompts for deployment
confirmation. `-Deploy -WhatIf` suppresses the actual deployment.
Do not suppress confirmation unless the displayed target and changes have been
explicitly approved. Deployment outputs contain resource identifiers and the Blob
endpoint, never keys.

`dev.bicepparam` owns the development group/location. The wrapper supplies
`AI_COLLAGE_INFRA_DEVELOPER_OBJECT_ID` only while compiling, restores its previous
value, and deletes its own temporary compiled JSON. No developer object ID or
subscription is committed in the parameters file.

Azure deployments are incremental: rerunning with the same parameters reuses the
account and role assignment; it does not migrate or delete application data.
Running as a different developer adds a grant rather than revoking the old one.
Review existing access explicitly if changing identities. Changing the resource
group/subscription changes the generated account name; it is not a data migration.
Use a new deployment name if intentionally changing the subscription deployment's
metadata region, since Azure binds an existing deployment name to its location.

## Verify after deployment

Set `$account` to the storage account name printed in deployment outputs:

```powershell
$account = '<storage-account-name>'
az storage account show --subscription $subscription --resource-group ai-collage-dev --name $account --query "{httpsOnly:enableHttpsTrafficOnly,tls:minimumTlsVersion,anonymousBlobs:allowBlobPublicAccess,sharedKey:allowSharedKeyAccess,oauthDefault:defaultToOAuthAuthentication,publicEndpoint:publicNetworkAccess}"
az storage container-rm show --subscription $subscription --resource-group ai-collage-dev --storage-account $account --name collage --query publicAccess
az storage blob list --subscription $subscription --account-name $account --container-name collage --auth-mode login --num-results 1 --query "[].name" --output json
```

Expect HTTPS-only `true`, TLS `TLS1_2`, anonymous blobs and Shared Key `false`,
OAuth default `true`, public endpoint `Enabled`, container access `None`, and a
successful authenticated list (initially `[]`). Newly assigned RBAC permissions may
take several minutes to propagate. Investigate an authorization error or allow
propagation; do not enable keys or anonymous access to bypass it.

These are management/read checks, not the later application Blob proof. They do
not upload photos or invoke models. Keep actual deployment details in the 019b
infrastructure record; application-code approval remains separate.
