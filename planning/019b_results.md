# 019b: Implementation and verification results

**Status:** Complete and closed on 2026-11-27 following offline verification,
the separately approved real-account application proof and explicit user
acceptance. The user waived the additional manual repetition of the API checks;
no manual smoke-test execution is claimed. The single agent-run live allowance
is consumed; further agent-run live work requires renewed approval.

Scope and guardrails are in the
[implementation specification](019b-blob-storage-implementation.md).
Actual deployment details and the resource-group link remain in the
[infrastructure record](019b-initial-blob-integration.md).

## Implemented

The same initialized-project storage boundary now has an isolated Blob adapter:
create/list/reopen/original-photo delivery, with unchanged DTOs, strict models,
canvas/photo identity and format versions. Unique candidates become visible only
through conditional completion publication. Definite failure/losing-attempt
cleanup is ETag-bound; ambiguous completion preserves its candidates.
Bounded reads and explicit service/missing/invalid/uncertain errors do not fall
back to local persistence.

Functions selects Local/default or explicit API-only development Blob mode,
using subscription-scoped Azure CLI authentication with finite timeouts and
disabled SDK retries. Unsupported conversation operations fail before local
conversation access or provider initialization. Launcher environment isolation,
loopback/Host/Origin checks and existing request limits are preserved.

An explicit opt-in proof module owns its Functions processes, generates its own
tiny photos, switches empty local roots across restart, checks original bytes,
and conditionally cleans only its exact successful-run inventory. Its local
HTTP/Blob request caps and cross-restart request ledger are proof-only.
Usage and the separate user smoke procedure are in the
[API guide](../api/README.md#api-only-development-blob-mode).

## Offline evidence

| Check | Result |
|---|---|
| Focused existing storage/application regressions | 66 passed. |
| Full root offline suite | 728 passed, including existing engine/application and infrastructure tests. |
| Complete API offline suite, explicitly selecting `tests\api` with `api\pytest.ini` | 139 passed. |
| Module-based proof `--help` and missing opt-in | Help succeeds; ordinary tests verify refusal before evidence/credential creation without opt-in. |
| Actual SDK upload contract, with HTTP transport replaced | All five uploads return usable ETags through `BlobClient.upload_blob`, with create-if-absent headers; no Azure calls. |
| Proof process lifecycle | Disposable loopback listeners verify owned-tree checks, refusal of another process's listener, and stopping only owned processes. |

Focused failure cases cover publication races, partial uploads, lost completion
response, strict records/envelope versions, bounded actual chunks, missing or
invalid photos, service/auth/container failures, conditional cleanup failure,
unsupported dispatch, Local isolation and launcher restoration in installed
Windows PowerShell/PowerShell 7.

Offline checks caught and corrected a convenience-method SDK return mismatch
and a Windows shutdown race where stopping a virtualenv child also exits its
launcher. Unexpected launcher exit now fails closed rather than permitting
cleanup with uncertain process ownership.

## Dependencies and service accounting

The user separately approved adding/installing `azure-storage-blob` in
`api\.venv`. Version 12.31.1 and its required `isodate` dependency were installed
there; the root environment and global toolchain were not changed.
Implementation and offline testing made no application Azure calls. The
separately approved proof below performed bounded Blob writes/readback/cleanup.
No model requests, provisioning or RBAC changes were performed.

The single approved real-account run is complete within its limits: fresh
namespace, one project, two generated photos totaling at most 1 MiB,
at most 30 local HTTP and 200 Blob HTTP sends including readback/cleanup.
No further agent-run proof is authorized by that allowance.

## Real-account application proof

The user explicitly approved this run on 2026-11-27 after offline verification.
The real local Functions HTTP routes used the recorded development target and
subscription-scoped Azure CLI identity, with SDK retries disabled.

| Check / accounting | Observed result |
|---|---|
| Evidence directory | This Copilot session's `files\019b-live-proof-01`: `report.json`, `requests.jsonl`, both host logs and the two generated photo downloads. |
| Namespace | `proof-019b-ff4bfb7514864a598793baabc46adccd` |
| Fresh namespace | Empty before creation. |
| Create/list/detail/original-photo delivery | Passed; project `proof`, canvas 900x1600, EXIF-oriented photo dimensions 10x20 and 12x24, exact original bytes and response headers. |
| Duplicate / unsupported conversation | 409 `project_exists` and 501 `blob_slice_only`, as specified. |
| Restart with a different empty local root | List/detail/downloads passed again; no durable local project tree in either root. Owned Functions hosts stopped. |
| Local HTTP requests | 12 of 30 allowed. |
| Blob HTTP sends, including readback and cleanup | 115 of 200 allowed. |
| Generated photo bytes | 761 bytes total; no user photos or archives uploaded. |
| Cleanup | Exact five-object inventory verified; completion deleted first, followed by its four referenced objects, all ETag-conditioned. All five deletions confirmed; no remaining owned objects. |

Downloaded fixture SHA-256 hashes match the generated originals:

```text
download-1.jpg  b594b70fd43bf31687443b573884c0768dae5f9674516b4457628ae25b2898a0
download-2.png  8648ec0f004c3b171bf811048c45a3a9d5e89f793c8959e61a2f948385d1d714
```

The local downloads remain available as generated fixtures; the proof's Azure
objects have been removed. There was one run and no rerun.

## User acceptance and closeout

After clarifying that the planned manual smoke check would repeat the same API
checks already exercised against Azure, the user explicitly selected:
"Accept 019b; waive the repeated manual check and update the trackers".
This is user sign-off on the completed proof, not an inference from automated
success or a claim that the user ran a second test.

019b is closed for its initialized-project API slice. 019c is next to specify:
extend persistence across the existing full web workflow and its concurrency/
uncertain-outcome safeguards. Its implementation, service budgets and any
dependency changes require their own approved scope. No frontend or 019c
conversation-persistence work is included in this closeout.
Git staging/history/branches remain user-managed.

## User-approved structural cleanup

Storage now lives in `ai_collage\storage`, with separate `contracts.py`,
`local.py` and `blob.py` and an import-light package initializer. Call sites use
the current modules directly; no legacy modules or compatibility paths remain.
Persistence behavior, formats, configuration and approval gates are unchanged.

Adapter tests now live under `tests\storage`. Direct Local publication tests
moved out of the application workflow file; orchestration cases remain under
`tests\application`. Blob adapter tests moved out of `tests\api`; HTTP
configuration/dispatch, launcher and API proof tooling tests stay there.
The default root suite explicitly selects Local adapter tests, while the API
suite explicitly selects its API tests and SDK-dependent Blob adapter tests.
No environments or dependencies were changed for this cleanup.

Cleanup verification: 104 focused Local-storage/application/engine-storage/CLI
tests and all 139 combined API/Blob-adapter tests passed offline. The extracted
Local adapter's class AST matches the pre-extraction implementation, and Local
imports load no Blob SDK modules. Default collection remains 728 root tests,
with all five moved Local cases included and Blob cases excluded; the API
directory defaults collect 139 API/Blob cases. Repository-root API commands
must still supply both explicit test paths, as documented.
The proof module's `--help` succeeds. During this structural cleanup, user
staging was unchanged and no live proof or Git writes were performed.
