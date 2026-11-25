# 018b: Local Functions tooling and connectivity

**Status:** Stages A-C executed under separate user authorizations on 2026-11-25,
with user-run installation between A and B. **Complete and closed** following
the user's manual UI-to-Function verification; see [results and limits](018b_results.md).
This does not authorize 018c or later work. The original
[tooling handoff](018b_tooling.md) remains the setup reference.

## Outcome and scope

Prove that the React prototype can call a real, local Python Azure Function,
without involving collages. Vite and Functions run separately from PowerShell.

- Use a minimal Python Functions app under `api`, with one HTTP endpoint:
  `GET /api/health` returns HTTP 200 and JSON `{"status":"ok"}`.
- Add a compact, manually triggered backend check to the web prototype.
  Show checking/success/failure, including a bounded timeout. Never substitute
  mock success, retry automatically or poll in the background.
- Use a configurable `VITE_API_BASE_URL` and direct browser requests, not a Vite
  proxy, so the smoke check proves cross-origin connectivity. Configure Functions
  CORS for the actual local UI origin, initially `http://127.0.0.1:5173`, not `*`.
- Keep this diagnostic separate from sample project state. The existing scripted
  conversation and drafts remain unchanged and work when Functions is stopped.

The initial dependencies are Azure Functions Core Tools 4.x, a compatible Python
runtime/environment, and the `azure-functions` Python package. Reuse the existing
pytest/Vitest testing approaches; no new web dependency is expected. Choose
compatible versions and an environment strategy after inventory, not by guessing
or upgrading the existing environment.

## Execution stages and installation pause

| Stage | Work and boundary |
|---|---|
| A. Inventory and setup handoff | When requested, inspect resolved Python/virtual-environment/Core Tools commands and versions read-only. Check current official compatibility/install guidance. Prepare `planning\018b_tooling.md` with findings, chosen versions/environment, exact user-run installation/verification steps and official links, plus minimal dependency manifests needed for restore. No installs or application code. |
| **Pause for the user** | **End the run after handing over the setup guide.** The user performs installations. Do not leave an agent waiting, schedule retries, poll for tools or start the Functions host. |
| B. Verify and implement | Resume only after the user confirms setup and explicitly approves implementation. Recheck commands in a fresh PowerShell process, then implement only this brief. An installation-complete message alone permits verification, not implementation. |
| C. Handoff and stop | Record checks/limits in `018b_results.md`, link from the tracker, and hand off the local connectivity check. Stop for user review; do not continue to 018c. |

For example, the user can resume with: "Setup is complete; here is the
verification output. Please verify it and implement 018b."

All installations are user-run unless separately authorized, including Python
package restores. Include tools and package/environment setup in the same
handoff, with dependency manifests prepared before the user-run restore.
Do not silently run pip/npm/global installs during B. If another installation
is needed later, stop and hand over that step too.

## Verification

- Test the handler's HTTP status/JSON and the frontend check's success, failure
  and timeout behavior offline, with service calls controlled in tests.
- Start the actual Functions host and confirm the endpoint from PowerShell.
  In a real browser, prove the UI calls that host directly and handles it being
  unavailable. A mocked fetch alone is not the connectivity acceptance check.
- Both servers must remain local-only. Check actual listener addresses rather
  than trusting an advertised localhost URL. If safe local binding needs extra
  tooling/settings, stop and discuss rather than exposing the host or changing
  firewall rules silently.
- Run the existing frontend checks; preserve CLI/engine behavior and use the
  smallest Python checks covering any touched code. No paid replay is required.
- Document repeatable startup/stop commands and configuration, without secrets.
  Health/connectivity success is not authorization for real model requests.

## Guardrails and exclusions

No project/photo/history API, uploads, engine changes/refactoring, rendering,
model requests, real project-store access, authentication implementation,
Blob storage, deployment or infrastructure work. No Azure credentials should be
needed for this HTTP-only local check. Azurite, Docker, Aspire and SWA tooling
are not prerequisites; stop for unexpected runtime requirements.

Preserve the existing Python environment, originals, archives, sample assets
and user staging. No changes to global PATH/settings, branches, staging, commits
or pushes by the agent without explicit approval. Temporary diagnostic fixtures
must not reference real project stores. Later APIs remain separately scoped.
