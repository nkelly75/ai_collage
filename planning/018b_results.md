# 018b results: local Functions connectivity

**Status:** Complete and closed following the user's manual UI-to-backend
verification on 2026-11-25. This closes the bounded placeholder-connectivity
phase, not real collage integration or authorization for 018c.

## Authorization and setup

The user first authorized inventory/setup handoff only, completed the
[user-run installation](018b_tooling.md), then explicitly authorized resuming
[the brief](018b-local-functions-tooling-and-skeleton.md) at stage B.
No agent-run installation or restore was needed.

Verified setup: Core Tools 4.17.0, runtime 4.1055.300.26527, Python 3.12.10 x64,
azure-functions 1.26.0 and pytest 9.2.0 in the separate `api\.venv`.
Core Tools was invoked through its installed executable because this app's
inherited PATH had not refreshed.

## Delivered

- One Python v2-model Function under `api`: anonymous `GET /api/health`
  returns HTTP 200 and exactly `{"status":"ok"}` as JSON. No engine import,
  extension bundle, storage binding or Azure connection is configured.
- A compact **Check backend** control in the existing prototype notice.
  It requests the configured `VITE_API_BASE_URL` directly, without a Vite proxy,
  credentials, redirects, automatic requests/retries or mock success.
  A five-second timeout covers both headers and body; timeout/unmount abort
  pending work and late success cannot replace an error.
- The diagnostic is independent of sample/draft state. Project and chat
  features remain explicitly browser-only; no new API functionality is implied.
  Desktop workspace height now accounts for the notice's actual height rather
  than a fixed pixel offset, so the new control does not push panels offscreen.
- Separate API tests/configuration. Root `pytest.ini` selects the existing
  `tests` directory, preventing the CLI environment from collecting API tests
  that require the separately installed Functions SDK.
- Repeatable local startup, configuration and stop instructions in
  [api README](../api/README.md) and [web README](../web/README.md).

## Verification

| Check | Result |
|---|---|
| API offline tests | 2 passed: handler status/JSON and GET-only anonymous route registration. |
| Frontend build, lint and offline tests | Build including strict TypeScript passed; lint passed; 22 tests passed. New coverage includes manual/configured requests, malformed/error responses, unavailable host, slow headers/body, abort/cleanup, late responses and independent sample use. |
| Existing Python discovery | All 631 existing tests collected in the root environment, without API tests. This was collection, not a new full Python regression run; engine/CLI code was unchanged. |
| Real Functions request | PowerShell received HTTP 200, `application/json`, exact `{"status":"ok"}`. POST returned 404 rather than invoking the GET handler. |
| CORS | The configured `http://127.0.0.1:5173` origin received its exact allow-origin header; `http://127.0.0.1:5174` received none. CORS is not authentication. |
| Actual listener addresses | Vite remained on `127.0.0.1:5173`. Functions HTTP on `127.0.0.1:7071` and its additional host listener were loopback-only, using the supported `--address 127.0.0.1` option. |
| Real browser, backend available | Manual click showed **Health check passed**. Resource Timing recorded a browser `fetch` from origin `http://127.0.0.1:5173` directly to `http://127.0.0.1:7071/api/health`. |
| Real browser, backend stopped | After confirming port 7071 was clear, another click showed **Health check failed: Failed to fetch**. The sample still produced/displayed P001 without a backend. |
| Responsive browser checks | Temporary 1280x900 and 1000x900 frames fit the desktop workspace within the viewport, including the error state and a sample proposal. At 320px the control/error remained usable with no horizontal page overflow and the normal stacked layout. Frames were removed. This is not a physical-phone test. |

## Known runtime limitation

The host periodically logged `Unable to create client for AzureWebJobsStorage`
from its internal storage health probe while the HTTP route continued to work.
This matches acknowledged upstream
[Azure/azure-functions-host#11636](https://github.com/Azure/azure-functions-host/issues/11636):
the probe incorrectly treats intentionally absent storage as unhealthy.

The placeholder's success means its specific HTTP/JSON contract was reached,
not that every internal host health probe is healthy. No emulator/account was
added, no storage connection was invented and no warnings/health monitoring were
suppressed. This remains visible in normal host logs and the API usage guide.

## Handoff boundary

The temporary Functions host and its worker tree were stopped and port 7071
confirmed clear. The pre-existing Vite server was left running and unchanged.
Use the API README to run the backend for manual review.

No project/photo/history API, uploads, rendering, engine refactor, model requests,
real project-store use, cloud deployment, authentication or persistence was added.
Originals, archives and sample assets were not modified. The existing root
environment and user staging were preserved; no Git mutation was performed.
018c and later increments remain separately scoped and unapproved.

## User verification and startup follow-up

The user independently started both servers from terminals and successfully
called the backend with **Check backend**, completing the phase's human check.

At the user's request, `api\start.ps1` now encapsulates the existing local-only
startup settings. It selects the API environment, resolves/checks Core Tools
and restores the caller's environment/location after normal exit or failure.
It performs no installs or global configuration changes. The top-level README
has concise two-terminal startup commands; operational details stay in the API
and web READMEs. The parent 018 tracker records removal of temporary connectivity
scaffolding as real Functions are connected.

Follow-up verification: all 14 API-suite cases passed, including launcher checks
under both installed PowerShell hosts. Controlled Core Tools shims verified
arguments, environment isolation/restoration (including originally absent
variables), working-directory restoration, nonzero exits, missing environments
and unsupported tool versions. No real host was started for these checks;
the user's manually managed servers were not started, stopped or reconfigured.
