# Temporary Foundry smoke test

Standalone connectivity test for the existing `gpt-5.4-mini` deployment.
This intentionally uses the OpenAI SDK directly, not the Phase 1 Agent Framework integration.

## Setup

Python 3.12 and Azure CLI are required. After installing, open a fresh PowerShell
terminal if the commands are not yet on PATH.

From the repository root:

```powershell
python -m venv .\temp-foundry-test\.venv
.\temp-foundry-test\.venv\Scripts\python.exe -m pip install -r .\temp-foundry-test\requirements.txt
```

Activation is not required; invoking the environment's Python directly also
avoids PowerShell activation-script execution-policy issues.

## Sign in and authorize

```powershell
az login --tenant "<directory-tenant-id>"
az account set --subscription "<subscription-id>"
az account show --query "{subscription:name, tenant:tenantId}" --output table
```

Use the tenant containing the Foundry resource. A personal Microsoft account
must sign in to that directory, where its resource role assignment applies.
An existing suitable developer credential may also work: `DefaultAzureCredential`
tries its standard credential chain, not exclusively Azure CLI.

In the Azure portal, open the **nkfoundry26 Foundry resource** (not merely the
project), then **Access control (IAM) -> Add role assignment**. Assign
**Cognitive Services OpenAI User** to your user at that resource's scope.
Creating role assignments requires appropriate Azure RBAC permissions;
Global Administrator alone does not grant resource access.
Allow several minutes for a new assignment to propagate.

No API key is needed. The SDK parameter is named `api_key`, but receives a
refreshable Entra bearer-token provider using the `https://ai.azure.com/.default`
scope. Never paste tokens or credentials into source files.

For this direct Azure OpenAI Responses API test, use the resource's OpenAI
endpoint, `https://nkfoundry26.openai.azure.com/openai/v1/`, rather than the
general Foundry `services.ai.azure.com` endpoint from the generated sample.
The latter returned HTTP 401 `PermissionDenied` despite the correct user,
tenant, and resource role assignment.

## Run

From the repository root:

```powershell
.\temp-foundry-test\.venv\Scripts\python.exe .\temp-foundry-test\smoke_test.py
```

Each invocation makes one paid Responses API request, with automatic retries
disabled and a 256-token output allowance (including reasoning tokens).
The input is a fixed short question. This is a per-request bound, not an
account-wide spending cap. The request uses `store=False`; this is not a
guarantee that all service-side logging or retention is disabled.

A successful run prints the answer and reported input/output token usage.
Authentication and service errors are surfaced rather than hidden.
An incomplete response is reported as an error, not success; if the model
exhausts its allowance on reasoning, inspect that error before choosing to
increase the limit and make another paid request.

- Credential unavailable: check Azure CLI installation and tenant-specific login.
- HTTP 401: check the endpoint and the credential's tenant/token audience.
- HTTP 403: check your resource role, role propagation, and resource network restrictions.
- HTTP 404: check the endpoint and exact deployment name.
- HTTP 429: check available quota and rate limits; this sample does not retry.

The `.venv` and Python caches are ignored by Git. Leave this directory in place
while experimenting; it contains no Azure credentials.

Reference: [Microsoft's keyless authentication guidance](https://learn.microsoft.com/en-us/azure/foundry-classic/openai/how-to/managed-identity).
