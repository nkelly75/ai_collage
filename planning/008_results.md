# 008 results: Natural-language lifecycle support

## Status and authorization

Implementation and offline verification are complete under
[008](008-project-lifecycle-and-interactive-iteration.md).
The initial implementation/offline checks used no live model requests,
credentials or cloud services. On 2026-11-19 the user separately authorized the
bounded landscape smoke check. It completed successfully using **8/32 actual
calls**, with no corrections, clarifications, retries or code/prompt fixes.
The remaining 24 calls are unused and this allowance is now closed.
No human trial was started or authorized by this smoke check.

## Implemented

- Separate interpretation and recipe-only generation prompts/schemas through the
  same guarded provider/model. Questions belong to interpretation, not generation.
- Application-resolved fresh/edit/retry/select actions, including older-source
  edits and compound return-and-edit. Fresh generation retains the previous
  proposal or initial accepted recipe as a reference to avoid, not an edit source.
- Durable originating task/source and rejected-reference provenance. Repeated
  edit retries retain the original source/task; clarification answers retain
  the preceding real request/question. Failed generation leaves the baseline
  unchanged. Selection displays the preserved PNG without generation, rerender
  or acceptance.
- Typed terminal outcomes; replay/assessment now distinguish generation,
  selection and clarification. Source-relative authored differences do not
  pretend fresh/older-source work is a linear edit of the preceding output.
- Explicit replay `--answer` / `--answer-origin user|copilot` continuation,
  preserving the script and recording supplemental answers separately. A question
  keeps its step pending; successful completion advances it once. At most two
  answers per scripted step; failed answer attempts can be explicitly retried.
  Assessment identifies clarification-assisted completion.
- Four actual calls per message attempt, at most two interpretation attempts;
  remaining calls cover generation/corrections. Service failures do not retry
  automatically. Existing input/output/time guards and the shared durable outer
  cap remain in use across explicit retries, resumes and fresh projects.
- Both prompts in replay instruction identity/captures. Integrity checks cover
  source relationships, actual stage order, durable request accounting, recorded
  outcomes and baseline/state identity. The offline assessor now reads current
  request/event/context records; it still initializes no conversation/provider.

Conversation, proposal, event, acceptance-intent, replay and assessment contracts
advance to record version 2. Layout/project format remains 3. Sequence definitions,
controls, preferences, request logs and call-budget contracts keep their unchanged
versions. Unsupported old conversation/replay records are rejected, not migrated,
reinterpreted or supported through a second implementation.

## Offline evidence

The final full offline suite passed: **401 tests**. A separate targeted run of
all **26** assessment and shipped-landscape integration checks also passed after
the replay-state identity checks were added. Tests prohibit network connections; provider integration
uses the real installed Agent Framework/OpenAI adapter with mocked HTTP.

Coverage includes source/task fidelity for repeated retries, fresh arrangements,
initial accepted sources, exact selection, subsequent edits, older-source compound
edits, clarification/restart, control incompatibility, invalid IDs/contracts,
generation failure, concurrent-state preservation, four-call exhaustion, shared
outer accounting and immutable acceptance fidelity.

The unchanged four-message
`examples\sequences\02_landscape_staggered_adjustments.json` passed `--check`
and ran through the updated replay path with controlled two-stage responses:
four proposals, eight mocked requests, no validation corrections or acceptance.
The offline integrity assessment passed. Actual guarded conservative input bounds
for those mocked HTTP requests were 9,278; 30,905; 12,243; 35,607; 14,679; 38,235;
17,273; and 40,505, all below 50,000.
These responses were authored test inputs, **not evidence that the live model
understands the requests or produces good layouts**. Mock token usage is
synthetic, not measured model consumption or billing.

Persistent session evidence is beneath
`C:\Users\nkell\.copilot\session-state\621a42a9-2ec6-4af0-a2d9-fde02d818692\files`:

- `008-final-offline-evidence\test_shipped_landscape_sequenc0\data\users\local-dev\projects\demo\replay\report.json`
  and `assessments\0001.json`: the controlled landscape replay and its saved
  integrity assessment, with contexts, request records and previews alongside.
- `008-deterministic-evidence.json`: deterministic comparison results and PNG paths.
- `008-preservation.json`: hashes for 791 pre-existing photo/runtime files, all
  verified unchanged after implementation. This includes pre-existing archived
  project data and closed-run evidence/counters.

## Tilted deterministic example

Before code changes, the public CLI imported the original four photos into a
fresh isolated session project and applied `examples\emma_tilted_2x3.json`.
After implementation, another fresh project applied the unchanged recipe,
then reopened/rerendered its accepted version through the public CLI.

The before/after 1200x1800 RGB images have identical decoded pixels, recipes
and geometry. Repeat rerendering preserves PNG bytes and project metadata,
with only accepted version 1 present. Photo order `[3, 4, 2, 1]`, whole/cover
modes, pan/zoom, white borders, rounded corners and centre-based tilts are
unchanged. The resulting PNG was visually inspected; no rendering regression
was observed. Source photos and the example recipe remain unchanged.

- Decoded-pixel SHA-256:
  `b01a65a9203b7f943c9dff43ff7bb4fda88e05e84c98a7e8a33654fc0e40adc0`
- PNG SHA-256:
  `29ef87fd9cbe7be2936d9c88211e3fc920430c15c4a367fd803a9efae53f8638`
- PNGs under the session evidence root:
  `008-baseline-data\users\local-dev\projects\tilted-before\renders\v0001.png`
  and `008-after-data\users\local-dev\projects\tilted-after\renders\v0001.png`.

The accepted versions above belong only to isolated deterministic test projects,
not replay proposals or pre-existing user projects.

## Authorized live landscape smoke check

The user staged the implementation and requested the next landscape smoke check.
Pass `008-20261119-01` used the unchanged four-message
`examples\sequences\02_landscape_staggered_adjustments.json`, a fresh project
`p008-landscape-smoke-01`, and one new durable 32-call outer guard.
The source/instruction candidate was unchanged throughout.

Preflight revalidated the sequence offline and passed 14 targeted mocked-HTTP
and outer-cap checks. The live replay then completed all four scripted messages
without supplemental answers or failures. Each message used one interpretation
and one generation call; no validation corrections, service retries, development
recoveries, acceptance or version publication occurred.

The saved offline integrity assessment passed all four cases, and separate
authored-field checks and preview inspection established:

| Proposal / step | Observed result |
|---|---|
| P001 / initial | Light `#F5F2EA` background; photo 3 is the largest photo on the right, with the other three staggered down the left. |
| P002 / swap | Photos 1 and 4 exchange their exact original authored centre pairs; sizes, styling, order and all unrelated fields are unchanged. |
| P003 / move-and-shrink | Photo 2 is smaller and closer to photo 3; centre distance falls from 928 to 544 pixels. Only photo 2's authored box changes. |
| P004 / square-corners | Only photo 3's corner radius changes, from 12 to 0; all other authored fields are preserved. |

This is an uninterrupted four-message success, not clarification-assisted
completion. Visual review also found considerable empty space through the centre,
especially in the initial composition. This is a useful quality observation,
not a reason to spend the remaining allowance on aesthetic tuning or claim
subjective design sign-off.

### Saved intent-model responses

The four interpretation calls returned the following exact response bodies,
extracted from existing event files without rerunning the replay or making
additional model calls:

| Scripted message | Raw model response | Application-resolved source |
|---|---|---|
| Use a light background. Make photo 3 the main picture on the right. Arrange the other three down the left, slightly staggered from side to side. Size them to fit comfortably, with clear separation or only shallow overlap. | `{"action":"fresh"}` | None: new arrangement |
| Swap the positions of photos 1 and 4. Keep their sizes and styling unchanged. | `{"action":"edit","source":"current"}` | P001 |
| Move photo 2 closer to photo 3 and make photo 2 a bit smaller. It's fine if there is no overlap. Leave everything else alone. | `{"action":"edit","source":"current"}` | P002 |
| Remove the rounded corners from photo 3 only. | `{"action":"edit","source":"current"}` | P003 |

Evidence is in `conversation\events\000001.json`, `000003.json`, `000005.json`,
and `000007.json` under the live project listed below. Each event preserves the
original message in `prompt`, the raw model output in `response`, and the
application-resolved provenance in `intent`. Corresponding usage records are
`conversation\requests\attempt-0001.json`, `attempt-0003.json`,
`attempt-0005.json`, and `attempt-0007.json`.

The model chose the lifecycle action and, for edits, the symbolic source
`current`. The application resolved that source to a concrete proposal and
retained the original message as the generation task. The larger event `intent`
object is application-built provenance, not additional model output. None of
these responses asked a clarification or specified geometry. This demonstrates
the intended separation for this simple sequence, not live coverage of the
other lifecycle actions.

### Accounting and preservation

- Durable guard:
  `.collage-data-v3\users\local-dev\autopilot-runs\008-20261119-01\budget.json`:
  **8 used / 32 maximum**, matching all eight project request records.
- Reported usage: **37,430 input + 26,664 output = 64,094 total tokens**.
  Cached input 14,592 and reasoning output 25,479 are subsets, not additional
  tokens. No request has unknown usage; no monetary-cost claim is made.
- Maximum observed conservative input bound: 41,853, below the unchanged 50,000
  per-request bound. Per-request output/time guards were unchanged.
- All 790 pre-existing photo/runtime files in this pass's preservation manifest
  are unchanged. The 19 captured candidate files, both-prompt instruction identity,
  staged-index identity, HEAD and branch are unchanged.
- Both the project's accepted version and conversation's accepted proposal remain
  null. Live spending stopped after success; no extra inference or human trial
  used the remaining capacity.

### Live evidence locations

Under `.collage-data-v3\users\local-dev\projects\p008-landscape-smoke-01`:

- `replay\report.json`, `replay\instructions.md`, and `replay\steps\0001` through
  `0004`: script snapshots, captured contexts and per-execution results.
- `replay\assessments\0001.json`: complete passing integrity assessment,
  `clarification_assisted: false`.
- `conversation\requests\attempt-0001.json` through `attempt-0008.json`: actual
  stage-labelled request records and usage.
- `conversation\proposals\P001` through `P004`: immutable recipes, geometry and
  previews. The final image is `conversation\proposals\P004\preview.png`.

The replay report SHA-256 is
`bf189887a007cf44667128fe847a36056738a2201dc5d64a13d660778c8462ff`.
The unchanged both-prompt instruction identity is
`26ee6bcb160768cef040e0322f4fe238b96c01fc54819030178feccad69cee2a`.
Additional preservation, authored-edit and accounting evidence is under the
session evidence root's `008-live-20261119-01` directory: `baseline.json`,
`review.json`, `preservation-final.json` and `replay-initial-cli.txt`.

## Remaining gate and limitations

The landscape smoke check is complete; its unused allowance is not permission
for more runs. Human trials remain a later separately agreed activity.
This one replay covers initial composition and the three scripted targeted edits,
not live reliability of exact return, retry/fresh feedback, compound older-source
edits or clarification-answer continuation. Those behaviours retain offline
coverage and remain relevant to the human trial.

Neither offline success nor this single smoke check establishes broad reference
resolution, repeatability, substantial composition variation or subjective
quality. Long histories can still hit the existing conservative input bound;
no silent truncation, automatic budget extension, new memory subsystem, vision
or UI was added.

The user staged the implementation before this live pass. Subsequent result/status
documentation updates are unstaged; no Git staging, commits, pushes, branch
changes or history writes were performed.
