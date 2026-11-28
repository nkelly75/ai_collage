# 019c implementation and verification

**Status:** Complete, explicitly accepted by the user and closed.
Implementation was approved, implemented and verified offline.
The renewed, separately approved model-free real-account proof passed, including
fresh-root restart and exact owned cleanup. The first attempt's startup failure
and offline repair remain recorded below. User-led web testing and acceptance
are complete. Closure does not authorize further service calls.
See the [approved brief](019c-complete-web-persistence.md) and
[019 tracker](019-storage-abstraction-and-blob-persistence.md).

## Implemented outcome

The complete existing local Functions/web workflow now supports explicit Blob
persistence: create/list/reopen/originals, conversation state/history/names,
prepared generation, attempts and HTTP operations, proposals/rendered PNGs,
Current collage selections and downloads. Local remains the default; CLI/replay
remain local. No frontend runtime changes, migrations, accepted-version import,
image understanding, cloud hosting or new authentication were added.

The shared agent/application algorithms use typed logical persistence sessions.
Local retains ordinary records/paths and acceptance. Blob uses one strict
storage-only version-2 head with immutable typed references, digests and sizes.
Project/layout format 3, conversation version 8 and HTTP DTOs remain unchanged.
Unsupported Blob versions are rejected; historical 019b evidence is untouched.

Mutations hold a finite renewable head lease and update with both lease ID and
expected ETag. Claims and attempt reservations precede dispatch. Event/state,
proposal/PNG/event/baseline and completed selection/preparation abandonment use
atomic publication checkpoints. Lost ownership/publication cannot authorize
paid replay. Ambiguous outcomes preserve potentially referenced objects and
durable claims; only confirmed never-published candidates receive conditional
cleanup. Readers bind immutable snapshots; old committed objects remain.

Photo decoding/rendering uses owned temporary files, not a durable local copy.
Validated bytes are reused in a request-local cache bounded at 128 MiB.
JSON/head IO stays at 1 MiB, originals at 25 MiB and encoded PNGs at 128 MiB;
canvas axes remain at most 4096. Preview reads use the open file's bounded size
rather than allocating the full ceiling for every small historical PNG.
Work-deadline checks also guard proposal staging before its head publication.
After durable attempt reservation and renewed ownership, the stage/work deadline
is rechecked before returning control to the provider's actual dispatch.

## Offline evidence

| Check | Result |
|---|---|
| Final combined API/launcher/Blob gate | 177 passed. |
| Focused Local deadline/publication/selection regression | 67 passed, 234 deselected. |
| Full root/core/application regression | 728 passed. |
| Local request/deadline gate after the final pre-dispatch deadline recheck | 46 passed, 195 deselected; final combined API/Blob gate also includes the new reservation-window regression. |
| Full proof journey with HTTP transport/SDK boundaries replaced | Passed: normal multipart/JSON handlers, four scripted stages, history/selection, fresh-root restart, exact photos/PNGs and owned inventory cleanup. |
| Real SDK serialization with transport replaced | Conditional create and leased `If-Match`/`x-ms-lease-id` head updates verified offline. |
| Maximum-supported render | Actual 4096x4096 PNG produced by the normal renderer fits the 128 MiB encoded ceiling. |

Focused failures include interpretation/generation claim, reservation, event,
prepared handoff, proposal and final-operation head writes, both rejected/lost
responses and successful publication followed by a lost response. Selection
claim/final checkpoint windows exercise both committed and uncommitted outcomes.
Coverage includes lease conflicts/expiration/renewal loss, helper shutdown,
different-project independence, deadlines crossed during PNG staging,
unclaimed preparation abandonment, immutable old readers, corrupt/unsupported
heads, bounded actual reads, short-read photo streams and factory isolation.

The fixture permits only the four expected replies and never falls back to
Foundry on missing/exhausted responses. Attempt reservations/finalizations are
real application writes; paid token usage remains unknown, not fabricated.
Original archived `project-02` data was read only for its small recipe subset;
four synthetic 3:4 photos replace its originals in every fixture.

Final command output is retained in this session's
`files\019c-root-final.txt`, `files\019c-api-blob-final.txt` and
`files\019c-request-deadline-final.txt`. The full root run preceded the final
single pre-dispatch deadline recheck; the focused Local gate and combined
API/Blob gate verified that final change.
The ordinary commands are:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider
.\api\.venv\Scripts\python.exe -m pytest -q -c .\api\pytest.ini .\tests\api .\tests\storage\test_blob.py --tb=short -p no:cacheprovider
```

Earlier focused runs exposed a proposal-lookup ordering issue, an incorrect
fixture context key, and obsolete proof assumptions; these were corrected.
Earlier slow full-root runs were stopped during iteration and are not passes.
The user's staged diff remained unchanged, with hash
`88f05642f20698d8cd05ffa78cc63a327844427e`; implementation/documentation edits
were left unstaged. No LESSONS entries were added.

## Live proof and remaining acceptance gate

**No Azure/model calls, credential acquisition, dependency installation,
infrastructure changes or Git writes were performed during offline implementation.**
The development target and consumed 019b allowance remain unchanged.

### First separately approved real-account attempt

The user approved one model-free attempt with ceilings of **50 local HTTP
requests and 1,200 Blob sends**, including leases, readback and successful owned
cleanup. That attempt stopped at its first project-list request with HTTP 503
`storage_unavailable`; it did not reach project creation.

| Evidence | Actual outcome |
|---|---|
| Namespace | `proof-019c-77fb29bebacd46dab61f23419c33b07a` |
| Local HTTP requests | 1 of 50. |
| Blob sends | 0 of 1,200; rejected before the send ledger/network boundary. |
| Model calls | 0; no Foundry fallback. |
| Storage authentication | Azure CLI token acquisition succeeded. Blob access/permissions were not exercised. |
| Uploads and cleanup | No uploads were dispatched; no cleanup was attempted. Inventory/cleanup completeness flags remain false. |
| Processes | The runner stopped its owned Functions process tree. |
| Proof result | Incomplete; no workflow or real lease/restart checks completed. |

The proof transport permitted the exact owner-root listing used by cleanup,
but wrongly rejected `BlobProjectStorage.project_ids()` listing that same
owner's narrower `published/` prefix. This is a harness scope defect, not an
authentication failure. The offline full-journey double bypassed this actual
SDK/transport combination.

The repair permits exactly the existing owner-root or its `published/` prefix;
account, container, namespace, owned-key and request-budget restrictions remain.
A regression using the real SDK with network transport replaced reproduced
the original refusal, then passed after the repair. Related proof/configuration
and full normal-handler journey checks passed together: **37 passed**.
This repair was offline only, not another live attempt.

Unchanged live evidence is in this session's `files\019c-live-proof-01`
(`report.json`, empty `requests.jsonl`, limits and host logs). Offline repair
output is in `files\019c-proof-prefix-repair.txt`. The absence of uploads follows
from the pre-send failure before creation, not merely an empty incomplete
inventory. No further Azure inspection, guessed cleanup or retry occurred under
that failed-run allowance.

The user changed staging after implementation. The fresh baseline immediately
before this attempt was `36251ccc0edb7bd4ba14c67e6df4ebae71f486be`, and it remained
unchanged through that attempt and offline repair; their edits were unstaged.
No dependency installation, infrastructure changes or Git writes occurred.

### Renewed separately approved real-account proof

The user explicitly renewed approval for **one fresh attempt with the same
50 local HTTP / 1,200 Blob-send ceilings**, not reuse of the failed attempt's
unused budget. The repaired runner executed once against the same development
account/container, using only synthetic photos and scripted model responses.

| Evidence | Actual outcome |
|---|---|
| Result | Passed; runner exited successfully. |
| Namespace/project | `proof-019c-744e380d559c48279b07d6fe0223a04b` / `proof`. |
| Local HTTP requests | 32 of 50. |
| Blob sends | 937 of 1,200, including lease operations, readback and owned cleanup; matches the send ledger. |
| Model calls | 0; four scripted interpretation/generation replies, no Foundry fallback. |
| Initialization | Fresh namespace empty; create/list/detail/original-byte readback and duplicate rejection passed. |
| Conversation | Two proposals, complete history, selection of P001 as Current collage, full-resolution PNG retrieval and action/status observation passed. |
| Restart | New owned Functions host and different empty local root restored identical conversation, completed requests/selection, original photos and saved PNG bytes. No durable local project copy was created. |
| Cleanup | Exact inventory verified and publication head deleted first after owned hosts stopped; all 39 owned keys deleted, none remaining. |
| PUT inventory | 61 confirmed PUTs across 39 unique keys, including repeated conditional head publications. |

This exercises real storage authentication, permitted Blob access and leased
publication/readback for the agreed scripted journey. Live fault injection,
concurrent-writer stress and performance tuning were not added; their offline
coverage and the optional 019d boundary are unchanged.

Evidence is retained unchanged in this session's `files\019c-live-proof-02`:
`report.json`, the request/limits/PUT-inventory ledgers, both host logs and
downloaded P001/P002 PNGs. Local verification checked report/ledger counts,
matching owned/deleted inventories, both completeness flags and zero remaining
owned objects; it made no additional Azure requests.

The user changed staging again before this attempt. Its fresh baseline was
`170f243c96aaefc9ae073b0ae4887205eeedc984`; it remained unchanged through that
attempt and its results/tracker updates. The user subsequently staged those
updates. No installations, infrastructure changes, Git writes, extra live
inspection or automatic retry occurred during that proof attempt.

The renewed allowance is consumed; it does not authorize further Azure/model
calls. Future proof runs still require explicit opt-in, a fresh evidence
directory/namespace and agreed caps, with owned inventory cleanup and no
automatic retry on failure.
The [API guide](../api/README.md#separately-approved-real-account-proof) describes
the invocation and evidence.

### User-led web acceptance and closeout

The user performed the real local API/Vite trial with fresh photos and Blob
persistence, including restart with a different empty local root while retaining
the same namespace and external model-budget ledger. The user reported the
procedure functionally successful, then explicitly requested:
"Let's mark 019c as accepted." This user result, not the scripted proof alone,
closes 019c.

| Evidence | Outcome |
|---|---|
| Manual namespace/project | `web-019c-6458c99495bd462995718e3db4751fcc` / `web-019c-test`. |
| Saved history | P001 creation, P002 revision, explicit selection from P002 back to P001, then post-restart P003 generation. |
| Restored editing context | P003's parent and resolved source are P001; the saved name `hero` resolves to photo 1. |
| Model-direction observation | Hero rotation increased from clockwise 2.5 degrees in P001 to clockwise 4.5 degrees in P003 despite the request to tilt left. The raw model response already contained 4.5; other photo angles were unchanged. This is separate model-quality feedback, not a persistence/source-selection failure or a blocker to the user's acceptance. |
| Separately approved inspection | 30 read-only Blob requests in that exact project's JSON scope, no photo/PNG downloads, Azure writes or model calls. State, proposal and history records were read with the normal digest validation. |

The read-only inspection evidence is retained in this session's
`files\019c-user-rotation-inspection.json`. Its saved history shows completed
attempts 1-6; the external trial-budget ledger was not inspected, so no independent
ledger accounting is claimed. The browser checks themselves are user-reported,
not independently observed by the agent.

The manual trial's Blob data and local budget/evidence directory are preserved;
no cleanup was requested or performed. Local trial directories do not make
project data authoritative on disk: the external budget remains local by design,
while project/conversation/proposal data remains in Blob. Stable Blob launch
configuration is a possible separate usability follow-up; no launcher changes
or additional scope were approved or implemented as part of closeout.

Acceptance updates are documentation-only and unstaged. The user's staging,
original photos, archived projects and earlier proof evidence are untouched.
019c is accepted and closed. At closeout, optional 019d was deferred;
subsequent development-launch/measurement scope is tracked in
[019](019-storage-abstraction-and-blob-persistence.md).
