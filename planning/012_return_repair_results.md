# 012 exact-return repair and focused retest

**Status:** Implemented, verified and closed. Replay 04 completed in all three
fresh runs, with each exact return succeeding on its first interpretation call.
This follows the failure recorded in the [earlier replay pass](012_replay_results.md);
that closed evidence remains unchanged.

## Narrow repair

Two existing navigation rejection messages now distinguish the resolved
destination from evidence actually present in the user's wording. One compact
prompt example contrasts ordinal wording (`first proposal`) with a literal ID
(`P001`), and explains that correction must repair both the quote and its kind.
Validation conditions, destination resolution and retry limits are unchanged:
there is no silent conversion or weakened evidence check.

Two parameterized offline regressions reproduce the earlier bad ID-evidence
responses and verify that correction selects the original PNG without rendering,
accepting or losing the other proposal. **34 focused offline tests passed**,
including existing navigation and replay safeguards. The unchanged sequence 04
also passed its offline definition check before live execution.

## Authorized fresh runs

The user authorized one fresh replay 04 and, only if it succeeded, two fresh
repeats. The shared **36-call ceiling** came from three runs, three scripted
messages per run and the existing four-call maximum. Runs were serial, with
no replay retries, extra answers or tuning between runs.

Deployment remained `gpt-5.4-mini`, with **high interpretation / low generation**.
All runs used the unchanged sequence, 1200x1800 canvas, forbidden cropping and
the existing `prefer` borders/rounding/tilt preferences.

| Fresh project | Outcome | Calls | Exact-return calls | Corrections |
|---|---|---:|---:|---:|
| `p012-return-01` | Two proposals, then selection of P001. | 5 | 1 | 0 |
| `p012-return-02` | Two proposals, then selection of P001. | 5 | 1 | 0 |
| `p012-return-03` | Two proposals, then selection of P001. | 5 | 1 | 0 |

Each return supplied `kind: ordinal`, quoting `first proposal`. It reused that
run's original P001 preview path and byte-identical PNG, with no generation or
rendering for the return. P002 remained preserved, the baseline became P001 and
no proposal was accepted. Integrity assessments passed; the preceding edit
removed exactly the four borders, with no other authored changes. All four
original photo IDs remained present. No names or naming gate were introduced.

Total: **15/36 calls**, **9 interpretation + 6 generation**, with **zero
correction calls**. All request records completed without service errors or
missing usage. Known usage was **84,452 input / 6,004 output tokens**.
The unused **21 calls are not authorized for further work**.

## Preservation and limits

The repaired application, prompt and test inputs were frozen before calls and
unchanged throughout the evaluation. Dependencies, configuration, **1,154**
pre-existing photo/project files, **1,513** files in eight prior archived
evidence roots and the saved 012 offline evidence matched the freeze at closure.
No dependencies were installed and no Git inspection or writes occurred;
staging remains entirely user-managed.

The earlier comparison found that both bad responses were rejected identically
before and after 012. These three successes strengthen confidence in this
narrow repair, but do not prove what caused the original failure or establish
general semantic reliability. The clearer guidance preserves the useful,
recoverable-progress approach without accepting unsupported evidence.
Human-led evaluation and branch integration remain separately gated.

Evidence root:

`C:\Users\nkell\.copilot\session-state\621a42a9-2ec6-4af0-a2d9-fde02d818692\files\012-return-repair-01`

It contains authorization, pre-repair baseline, repaired freeze, offline test
and sequence-check captures, fresh projects, invocation captures, assessments,
per-run exact-selection verification, accounting and closure.
Freeze SHA-256:
`22715df37a25c2b930d366a340bec13e3d4a447864c375926cf37a9782b58efb`.
The sealed manifest covers **133 evidence files**, with SHA-256
`f26bcd23095d4c1e313ad08b83d0fb168bab370e2dabaaa50c9ac18c050887b1`.
