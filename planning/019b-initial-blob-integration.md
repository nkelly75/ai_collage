# 019b: Development storage infrastructure record

**Status:** Infrastructure prerequisite deployed and verified with explicit user
approval. Application implementation remains unapproved. This records the actual
development target, not an application implementation specification. See the
separate [code specification](019b-blob-storage-implementation.md).

## Deployed development target

| Item | Value |
|---|---|
| Subscription | `0c6a09a0-a933-49df-9b6b-b8f65440332f` |
| Resource group | [ai-collage-dev](https://portal.azure.com/#@nkelly75gmail.onmicrosoft.com/resource/subscriptions/0c6a09a0-a933-49df-9b6b-b8f65440332f/resourceGroups/ai-collage-dev/overview) |
| Region | `eastus` (East US) |
| Storage account | `stclgdevbik2twby4e2zu` |
| Blob endpoint | `https://stclgdevbik2twby4e2zu.blob.core.windows.net/` |
| Private container | `collage` |
| Account type | `StorageV2`, `Standard_LRS`, Hot tier |
| Developer access | Signed-in Azure CLI user; Storage Blob Data Contributor at container scope |
| Subscription deployment | `ai-collage-dev-storage`; `Succeeded` |

Provisioning and verification completed on 2026-11-27. The
[infrastructure files and operating instructions](../infra/README.md) reproduce
this configuration. No production resources or Function App were created; the
existing Foundry group `ai_nk_2026` was not changed.

Management readback confirmed HTTPS-only, minimum TLS 1.2, anonymous blob access
and Shared Key access disabled, OAuth default enabled, cross-tenant replication
disabled, and Microsoft-managed encryption. The authenticated public endpoint is
enabled without a firewall, VNet or private endpoint, as agreed.

The container reports public access `None`. The developer role assignment was
read back at the exact container scope. Entra-authenticated data-plane listing
with `--auth-mode login` succeeded and returned an empty list. No keys were
retrieved, blobs uploaded, user photos accessed, or models invoked. This proves
infrastructure/read access, not application Blob publication or write recovery.

A subsequent what-if kept the resource group, account and role assignment
unchanged. It predicted removal of undeclared service/container defaults
(`deleteRetentionPolicy`, `defaultEncryptionScope`,
`denyEncryptionScopeOverride`); no second deployment was applied. Review these
default-property predictions separately from actual resource/security changes.

## Application follow-up

The separate [019b code specification](019b-blob-storage-implementation.md) bounds
the API-only Blob proof and its approval gates. Today's application still uses
local persistence; this infrastructure deployment does not make the full web
workflow cloud-ready. No application SDK dependency, storage integration or
future infrastructure work is authorized by this record.
