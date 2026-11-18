# 006 results: Simplification and repeatability

**Status:** First attempt stopped at its original baseline gate. The
[revised brief](006-simplification-and-repeatability.md) completed as
`006-20261118-02`: eight planned replays, 32 successful messages, one preserved
timeout and explicitly authorized retry, 33/200 calls and no development
recoveries. Results before the revised-pass section describe the first attempt, which
added the guard and captured two baselines. Landscape P002 is valid but does
not perform the requested swap. No simplification or frozen assessment followed.

## Run identity and changes

- Starting commit: `e8c4d3a8d823954d610ef020fd692e3f85d39e05`.
- Branch: `nkelly/llm-wip-1`.
- Starting staged-content SHA-256:
  `8689ef77cd987175f2a17c18ed79c2661b587273ae023237a88b9487332e3eea`.
- Starting and final HEAD: `e8c4d3a8d823954d610ef020fd692e3f85d39e05`,
  branch `nkelly/llm-wip-1`.
- Outer guard: `.collage-data-v3\users\local-dev\autopilot-runs\006-20261118-01\budget.json`;
  **8/200 calls used**, shared across both projects and command restarts.
- Budget basis: eight planned replays plus at most four recovery rechecks;
  12 replays x four messages x four calls = 192, rounded to 200.
- Development recoveries: 0/2 used; planned initial work is separate.
- Recovery notes: none. The original brief required stopping on baseline failure;
  that rule is superseded only for the revised pass.
- Baseline assembled-instruction SHA-256:
  `700eae289a68de48842a1bcd8f046f0d139c006e6aa95bfa35e64bdf2529356e`.
  Instructions, model/reasoning settings, history semantics, schemas and renderer
  remain unchanged. No candidate/frozen identity exists.
- Added only the optional outer guard: a small durable limit/used record and
  scoped reservation at the existing request-dispatch boundary, selected with
  replay's `--call-budget PATH [--max-calls 200]`. New paths start fresh; reopening
  retains usage and rejects limit changes. Normal replay/chat remains unguarded.
- Nine targeted mocked/offline boundary checks passed before any model request.
  Complete offline regression afterwards:
  `.\.venv\Scripts\python.exe -m pytest -q .\tests --tb=short`:
  **373 passed in 179.77 seconds**. No live service was involved in these tests.

Noninteractive token acquisition succeeded without exposing the token.
The first planned portrait message then verified Foundry access: one completed
request, no correction, with guard usage advancing to one. No standalone paid
connectivity probe, authentication changes or service retries were needed.

## Replay evidence

| Stage | Sequence | Fresh project / artifacts | Outcome | Calls / corrections |
|---|---|---|---|---|
| Baseline | Dark portrait | `p006-baseline-portrait` | Portrait profile passes all four steps | 4 / 0 |
| Baseline | Landscape staggered | `p006-baseline-landscape` | Integrity passes; swap instruction fails | 4 / 0 |
| Candidate check | Dark portrait | - | Not started: baseline stop | - |
| Candidate check | Landscape staggered | - | Not started: baseline stop | - |
| Frozen 1 | Dark portrait | - | Not started: baseline stop | - |
| Frozen 1 | Landscape staggered | - | Not started: baseline stop | - |
| Frozen 2 | Dark portrait | - | Not started: baseline stop | - |
| Frozen 2 | Landscape staggered | - | Not started: baseline stop | - |

Both projects are under `.collage-data-v3\users\local-dev\projects`.
Each retains `replay\report.json`, captured instructions and per-step context,
`replay\assessments\0001.json`, `replay\contact-sheet.png`, and the four immutable
`conversation\proposals\P001` through `P004` JSON/PNG pairs. These are execution
and integrity records, not independent evidence that the landscape instructions passed.

## Instruction-following and visual review

The landscape request was: "Swap the positions of photos 1 and 4. Keep their
sizes and styling unchanged."

| Photo | Required centre after swap | Actual centre after swap |
|---|---|---|
| 1 | `(0.195, 0.775)` | `(0.12, 0.600925925925926)` |
| 4 | `(0.17, 0.215)` | `(0.17, 0.215)` |

Photo 1 is 120 pixels left and about 156.67 pixels above the requested centre.
Its actual centre is consistent with copying photo 4's derived top-left
instead of its authored centre. This is a diagnosis, not access to model reasoning.
An offline exact centre swap of the original recipe validates successfully:
there was no geometry necessity for the deviation. Sizes/styles, other photos
and layer order were preserved, but that does not make the swap correct.

The later landscape move/shrink changes only photo 2's horizontal centre and
width; corner removal changes only photo 3's radius. Those later outputs remain
preserved but do not repair or excuse P002. The generic integrity assessor
correctly does not claim to evaluate direction-following.

Copilot inspected both four-stage contact sheets and the full landscape P001/P002
images. The initial landscape has the requested dominant photo 3 on the right
and staggered companions on the left. After the swap, photo 1 sits beside/behind
breakfast rather than in the former lower-left bookshop position, with that lower
slot left empty. The visual discrepancy agrees with the coordinate failure.
Portrait edits remain localized and pass the historical mechanical checks;
its overlapping layout is not a claim of polished design. No subjective judge
or new repository assessment framework was introduced.

## Accounting, preservation and handoff

| Project | Calls | Input tokens | Output tokens |
|---|---|---|---|
| Portrait baseline | 4 | 27,226 | 16,641 |
| Landscape baseline | 4 | 27,463 | 17,542 |
| Total | 8 | 54,689 | 34,183 |

Cached input is 37,632 of those input tokens; reasoning is 31,973 of those output
tokens, not additional usage. All eight HTTP outcomes completed, with no missing
usage or validation corrections. No verified pricing or monetary-cost claim.
Neither project has an accepted layout. Guard consumption matches the eight
saved project request records.

All **403 pre-existing runtime/photo files** match their starting SHA-256 hashes.
HEAD/branch and the original three staged planning-file versions are unchanged.
The whole index did change during execution: the guard's two source files and
test file were additionally staged outside this agent's Git operations.
That staging was left intact; no staging, commits, pushes or other Git writes
were performed by the agent. Final preservation evidence and raw baseline
instruction copies are also retained in session artifacts under `006-evidence`.

The first attempt remains closed at 8/200; its unused allowance is not renewed.
This finding concerns the unchanged baseline, not a simplification regression.
Checkpoint B remains outside this pass.

## Revised pass: 006-20261118-02 completed

The revised pass preserves both original baselines, including the swap failure.
Its completed work is the targeted swap prompt fix, then focused prompt/document
simplification, followed by a fixed frozen assessment batch. The known fix and
planned simplification are initial work, not additional recovery rounds.

The user explicitly authorized execution with 200 fresh calls. New guard:
`.collage-data-v3\users\local-dev\autopilot-runs\006-20261118-02\budget.json`.
Starting consumption: **0/200 calls**, **0/2 additional development recoveries**.
The old counter remains at 8/200. All new live calls, including corrections and
recovery checks, share the new guard. No resets within this pass.

Starting HEAD/branch remain `e8c4d3a8d823954d610ef020fd692e3f85d39e05` /
`nkelly/llm-wip-1`. The user's staged-content SHA-256 is
`ee92d91ecd87711d0924ee5dd27dc9318f7bf69f6ace8436e28e9be54816811d`.
Captured hashes protect all 480 pre-existing runtime/photo files, including
the first attempt. Before any new inference, all nine targeted mocked guard
checks passed. Session evidence is under `006-revised-evidence`.

Initial change: a generic swap instruction explicitly exchanges both original
authored centre pairs; it forbids substituting derived top-left coordinates,
size offsets, or changes to identities, sizes, styles and stacking.
The repair instruction hash is
`c467fb2da78fef61e76ccea49214a9681e1f85b4edc9059b18fc84b9f54c8d9a`
(20,256 characters). Its full offline suite passed: 373 tests in 75.28 seconds.
Noninteractive token acquisition succeeded without exposing the token; the first
planned repair message then successfully reached Foundry. No extra inference probe.

| Stage | Project | Outcome | Calls / corrections |
|---|---|---|---|
| Repair | `p006r2-repair-portrait` | Four steps complete; portrait profile and targeted preservation pass | 4 / 0 |
| Repair | `p006r2-repair-landscape` | Integrity and all requested edits pass, including exact centre swap | 4 / 0 |
| Candidate | `p006r2-candidate-portrait` | Four steps complete; portrait profile and targeted preservation pass | 4 / 0 |
| Candidate | `p006r2-candidate-landscape` | Integrity and requested-edit review pass | 4 / 0 |
| Frozen 1 | `p006r2-frozen1-portrait` | Four steps complete; portrait profile passes; excessive overlap noted below | 4 / 0 |
| Frozen 1 | `p006r2-frozen1-landscape` | Integrity and requested-edit review pass | 4 / 0 |
| Frozen 2 | `p006r2-frozen2-portrait` | Initial timeout preserved; explicitly authorized retry completes all four steps; portrait profile passes | 5 / 0 |
| Frozen 2 | `p006r2-frozen2-landscape` | Integrity and requested-edit review pass | 4 / 0 |

Repair review: both original centre pairs were exchanged exactly, and no sizes,
styles, identities or stacking changed. Photo 2 alone moved/shrank, reducing
its pixel-centre distance to photo 3 from 960 to 480 pixels; only photo 3's
radius changed in the final edit. Copilot viewed both four-stage contact sheets.
Landscape preserves its dominant right-hand photo and staggered left companions;
the swap now uses the correct slots. Portrait has clean separation and a larger
empty horizontal band than the original baseline. The edits are correct, not
proof that the compositions are polished.

The simplification removes repeated coordinate/resize explanations from
the prompt while retaining the swap rule, cover-resize behaviour, exact-copy
policy, composition defaults, authority rules and numeric validation feedback.
Snapshot storage/archive/schema-maintenance detail moved to the existing CLI
guide; the shared field guide retains the recipe contract and explicit warning
against copying derived origins into centres. No provider/code refactor is needed.
Candidate assembled instructions: 18,160 characters, SHA-256
`64105ad4a71ff8fd4f1ad40e7920a19935810b75576259867c278ef3c0168456`.
That is 1,762 characters (8.84%) less than the original baseline, or 2,096
(10.35%) less than the repaired prompt. This is text size, not a measured cost saving.
The simplified full offline suite passed: **373 tests in 77.86 seconds**.
Both live candidate checks completed all four messages without corrections.

Final consumption: **33/200 calls**, **0/2 additional development recoveries**.
One service retry was separately authorized; it was not a source/prompt recovery.

### Freeze and interruption

The candidate was frozen before assessment with assembled-instruction hash
`64105ad4a71ff8fd4f1ad40e7920a19935810b75576259867c278ef3c0168456`.
The session `freeze.json` records per-file hashes, provider configuration,
limits and the four predetermined assessment projects. Its sorted source-file
manifest hash is
`3db4f1409604f8ca598974a0bf0d737a2143fd32a54b8360f47700b033333074`
(excluding living planning records and the main README).
Every frozen source file remained unchanged through the final replay.
Deployment, high reasoning effort, controls, history semantics, contracts,
renderer, fixtures and assessment checks were not changed.

The initial request of frozen portrait 2 timed out after about 108 minutes of
recorded elapsed time. The user reported possible laptop sleep/Wi-Fi interruption;
the evidence does not establish a cause. Execution stopped at the service
guardrail with **25/200** calls consumed. The request has unknown provider token
usage and remains charged as one call; it was not refunded.

After inspecting the failure, the user explicitly authorized resuming that
portrait and the remaining agreed steps. The same project was resumed with
`--resume --retry --remaining`, under the unchanged guard and frozen candidate.
The four new requests completed, then the final landscape completed. No
automatic service retries, counter resets, post-freeze tuning, step skipping
or replacement projects were used. The failed execution/request and immutable
step evidence remain alongside the successful retry. The portrait assessment's
overall pass covers the successful proposals; its failed first execution is
explicitly `not_assessed`, not retrospectively successful.

### Frozen findings and subjective review

All four frozen replays reached all four successful steps. Both portrait
profiles passed, with exact authored centres retained on resize and only the
requested border/rotation edits. Both landscape integrity assessments passed.
Separate authored-field comparisons confirmed exact original centre-pair swaps,
unchanged sizes/styles/stacking, photo 2 alone becoming smaller and nearer photo
3, and only photo 3's radius being removed. Pixel-centre distance decreased from
968 to 744 in frozen landscape 1 and from 888 to 640 in frozen landscape 2.
The original baseline swap failure did not recur in the repair, candidate or
two frozen landscape replays. This small sample does not prove it cannot recur.

Copilot viewed all eight new four-stage contact sheets and the full initial
frozen portrait 1. Landscape maintains the dominant right-hand photo, staggered
left companions and correct swap slots, with varying gaps and shallow overlaps.
The candidate and second frozen portrait have separated photos, whereas frozen
portrait 1 clusters overlapping frames around the centre with substantial
background margins. Breakfast and bookshop intrude across the bridge/Eye frames:
this is an undesirable composition/visibility variation despite mechanically
correct targeted edits. It was recorded, not tuned away or rerun after freeze.
The second frozen portrait is visually cleaner, not evidence that the first
finding has been fixed. General design quality remains unresolved.

### Final usage and preservation

| Project suffix (`p006r2-`) | Calls | Known input tokens | Known output tokens |
|---|---|---|---|
| `repair-portrait` | 4 | 27,557 | 15,681 |
| `repair-landscape` | 4 | 27,766 | 22,429 |
| `candidate-portrait` | 4 | 25,566 | 12,497 |
| `candidate-landscape` | 4 | 25,836 | 20,732 |
| `frozen1-portrait` | 4 | 25,621 | 12,269 |
| `frozen1-landscape` | 4 | 25,714 | 19,334 |
| `frozen2-portrait` | 5 | 25,893 | 11,991 |
| `frozen2-landscape` | 4 | 25,896 | 21,596 |
| Total | **33** | **209,849** | **136,529** |

These are known totals, not complete billed usage: the timed-out request's
tokens are unknown. Cached input (148,480) and reasoning output (127,773) are
subsets of those totals, not additional usage. No monetary-cost claim.
There were **32 successful messages, zero validation corrections and one service
timeout**, with no pending request records. All 33 requests reconcile with the
guard. The pass is closed; unused calls/recoveries do not authorize further work.

All eight projects remain unaccepted. Each retains the ordinary replay report,
captured instructions, immutable step contexts/results, proposals/previews,
request records, `replay\assessments\0001.json` and a review contact sheet.
The first attempt's data and old 8/200 guard remain untouched. All **480 runtime/
photo files** present at the revised pass's start match their original hashes.

The user staged the frozen candidate during the interruption. The current
staged-content SHA-256 captured before resumption was
`2c066c0230c206ee052a6412e2fd0c95fc6848a9fc9c386dde178b082d3c44cc`;
that staging was preserved. HEAD/branch also remain unchanged. No agent Git
writes occurred. Detailed freeze, accounting and preservation records remain
in session artifacts under `006-revised-evidence`; only results/status
documentation changed after freeze.

The bounded experiment is complete, not a claim of consistent design quality
or user sign-off. Checkpoint B and possible conversational recovery of a bad
edit remain untested and outside this pass.
