# 018d execution results

## Status and authorization

Execution was approved on 2026-11-25 against the
[018d brief](018d-behavior-preserving-stage-extraction.md). The approved scope
is a behavior-preserving backend extraction, offline verification and one
bounded pass through replay sequences 03, 04 and 05. Green offline checks lead
directly into that pass without another approval pause. Work on 018e requires
separate approval.

Implementation, the full offline gate and all three bounded live replays have
passed. The user accepted the outcome on 2026-11-25; **018d is complete and
closed**. No additional manual UI trial was claimed or required for this
backend-only extraction. This is bounded regression evidence, not a claim of
general model reliability or permission to begin 018e.

## Implementation and preservation

- `Conversation.request()` keeps its signature and composes `interpret()` with
  `generate()` only when interpretation returns `PreparedGeneration`.
  Both entry paths reuse the existing `_request_stage` correction, validation
  and publication implementation; there is no copied agent or legacy path.
- The strict, versioned, JSON-round-trippable handoff retains the prompt,
  resolved intent, request boundary, active/independent task state, consumed
  logical calls, request limits and stage reasoning settings. Its binding
  includes project/photo metadata, saved conversation state/history and layout
  sources. Wrong-project, stale and sequentially reused handoffs fail before
  another model call or mutation.
- Fresh conversation/request objects or another process can continue the
  handoff without repeating interpretation or naming writes. Generation
  starts its normal stage deadline; interpretation corrections still consume
  the shared four-call allowance. Logical calls are not reconstructed from
  provider-attempt counts.
- CLI/replay callers, Functions/UI code, request-provider integration, prompts,
  engine, existing saved formats and dependencies are unchanged. No durable
  web-operation record or layout-format bump was introduced.
- Updated the current architecture map and the existing LESSONS code reference;
  no new lesson was added.

## Offline evidence

Commands ran from the repository root in the existing environments. Tests use
synthetic photos and temporary projects; the existing fixtures block network
access. The fresh-process continuation also blocks network connections after
initializing its Windows asyncio wakeup machinery.

| Check | Command / evidence | Result |
|---|---|---|
| Pre-extraction agent/replay baseline | `.\.venv\Scripts\python.exe -m pytest -q .\tests\agent .\tests\evaluation` | 341 passed. Launched before source edits; the collected modules supplied the existing baseline assertions. |
| Initial focused extraction/deadline/progress selection | Targeted stage, timeout and existing agent cases | 36 passed, two new assertions failed because they read an outdated conversation object's history rather than reopening saved state. The assertions were corrected. A subsequent temporary indentation error in that test edit was corrected before the successful focused rerun below. |
| Focused new stage module | `.\.venv\Scripts\python.exe -m pytest -q .\tests\agent\test_stages.py` | 23 passed before adding the additional in-place photo-metadata binding case. |
| Full root regression | `.\.venv\Scripts\python.exe -m pytest -q` | 661 passed: all 637 existing root cases plus 24 new stage/handoff cases, including the in-place photo-metadata binding case. |
| API consumer regression | `.\api\.venv\Scripts\python.exe -m pytest -q -c .\api\pytest.ini .\tests\api` | Final rerun: 47 passed. The first run had 46 passes and one failure in the unchanged cross-process lock-release test (409 instead of 201 after terminating the writer); that case passed alone, then the whole API suite passed. No lock/API code was changed; the initial failure's cause was not established. |
| Replay input preflight | Existing replay CLI `--check` for sequences 03, 04 and 05 | All three succeeded offline; captured source hashes before live execution. |

The new focused coverage compares composed and reconstructed split execution
for fresh generation, edits, corrections, identity answers, receipt approval,
timeout continuation and independent replacement. It compares model-facing
contexts, results, histories, names, tasks, source identity, proposal records,
progress notifications, request accounting and deterministic PNG bytes.
Branches copy the same synthetic project, preserving meaningful IDs; only
incidental request timing is excluded. Existing assertions remain the
pre-extraction anchor, rather than relying solely on two new paths agreeing.

Other cases cover non-generation outcomes, binding rejection without writes,
logical correction limits with a client that makes no provider reservations,
the existing outer budget, preflight failure evidence, settings/deadlines and
fresh-process continuation. No browser build or Functions host is needed for
the unchanged UI/API integration.

## Bounded replay evidence

Session-local evidence directory:
`C:\Users\nkell\.copilot\session-state\621a42a9-2ec6-4af0-a2d9-fde02d818692\files\018d-evidence`.

The approved ceiling is 12 model calls per scenario, 36 total, using exactly one
ledger per scenario and reusing it for every resume/answer. No failed-step
retries, whole-sequence reruns, replacement ledgers or prompt tuning are allowed.
The only planned answer is `Photo 2` with origin `copilot` if sequence 05
unambiguously asks which photo is breakfast. All other unexpected outcomes
stop the entire pass.

The ordinary composed replay CLI ran sequentially, one message per invocation,
using these fresh session-local roots and ledgers:

| Sequence / project | Root under the evidence directory | Ledger | Calls / cap | Outcome |
|---|---|---|---|---|
| 03 / `p18d-03` | `data-03` | `03-call-budget.json` | 6 / 12 | Three proposals; naming and both targeted edits verified. |
| 04 / `p18d-04` | `data-04` | `04-call-budget.json` | 5 / 12 | Two proposals, then exact selection of P001 after reopening. |
| 05 / `p18d-05` | `data-05` | `05-call-budget.json` | 5 / 12 | Initial proposal, expected identity question, then resumed edit with the authorized answer. |

**Total: 16 / 36 model calls**, with zero validation corrections, failed
steps, timeouts, retries or reruns. All attempts completed with known usage:
99,539 input tokens and 6,389 output tokens in total. Output totals already
include reported reasoning tokens; do not add them again. Existing stage
defaults remained interpretation high / generation low, with no escalation.
All three reports capture the same instruction-bundle SHA-256:
`5a079cc903ccb9bec518628352df8fa83c147d5551fa98a152df2f475dac6ade`.

Command shape used, with each named case's unchanged sequence, root, project
and ledger repeated on resumes:

```powershell
.\.venv\Scripts\python.exe -m ai_collage.cli.replay --sequence .\examples\sequences\03_named_photo_adjustments.json --data-dir "$e\data-03" --project p18d-03 --call-budget "$e\03-call-budget.json" --max-calls 12
# Subsequent scripted messages add --resume; never --remaining or --retry.
```

For 05 only, the second scripted message returned exactly
`Which photo is breakfast?`, with one interpretation call and no generation or
memory write. Its expected question exit status was 1, not a failed replay
step. One invocation with `--resume --answer "Photo 2" --answer-origin copilot`
continued the same step, using the same ledger. No other answer or naming
confirmation was supplied.

The existing offline assessment command ran once per completed case, with
`--profile` omitted (the `integrity` default). Each passed and preserved its
numbered report at `replay\assessments\0001.json`. The separate objective checks
inspected saved intents, recipe diffs, memory snapshots and source identities:

| Objective | Observed evidence |
|---|---|
| 03: automatic names | Initial interpretation saved `bridge -> 1` and `breakfast -> 2`; those exact memory records remained unchanged after both edits. |
| 03: resumed multi-photo edit | P002 changed only bridge's `center_x` from 0.285 to 0.325 and breakfast's width from 0.35 to 0.31. |
| 03: named corners | P003 changed only breakfast's corner radius from 14 to 0. |
| 04: remove borders | P002 removed all four 8px white borders, with no other authored change. |
| 04: exact return | Reopening selected original P001 in one interpretation call; no generation, replacement proposal or acceptance occurred. Original proposal JSON and preview SHA-256 values were byte-identical to their pre-return captures. |
| 05: clarification continuity | The answer retained task 3, its original resize request and source P001; saved `breakfast -> 2` once; P002 changed only photo 2's width from 0.34 to 0.30. |
| All cases | Accepted version remained null; all ledgers matched actual attempt counts, stayed within 12 calls, and all four original source-photo hashes still matched offline preflight. |

Evidence includes `03/04/05-preflight.json`, each
`03/04/05-execution-01/02/03.json` stdout capture, the three `*-integrity.json`
and `*-objectives.json` checks, `04-original-identity.json`, and
`accounting.json`. Each project's `replay\report.json`, steps, conversation
events, request records and immutable proposal/preview files retain the
underlying evidence.

The authorized pass has ended. Its unused 20 calls are not permission for
further trials, repairs, reruns or 018e work.

## Preservation and handoff limits

No agent Git writes, installs, original-photo edits or changes to pre-existing
data or archives were performed. The implementation-entry staging fingerprint was
`3765d7aa7dd92eb57b51cd5900dcc09ccadf4393` and remained unchanged after the
live pass. This is a historical staged-diff fingerprint, not a commit identifier
or the current staging state. The agent left its changes unstaged at the
implementation handoff; the user subsequently staged the work. Documentation
closeout preserves that staging and leaves the commit to the user.

The handoff is an internal single-writer backend contract. It does not supply
browser trust, durable HTTP operation claims, concurrent execution protection
or crash recovery for a web workflow; those remain 018e concerns.
