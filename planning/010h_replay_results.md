# 010h live replay follow-up: 03-05

**Status:** Executed and closed. Separately authorized on 23 November 2026,
after [010h's offline implementation](010h_results.md). One pass of unchanged
03-05, high interpretation / low generation, then hand back for a fresh
human-led trial. This is not a reasoning comparison or subjective sign-off.

## Authorization and freeze

User request:

> OK. Go ahead with replays 03-05 sticking to our agreed reasoning levels.

The pass used a shared **36-call ceiling**, mechanically derived from eight
scripted messages plus one possible reviewed identity answer for 05, at the
existing four-call limit per turn. No extra retry pass, second answer, effort
escalation, code/prompt tuning or further sequences were included.

Fresh evidence root:

`C:\Users\nkell\.copilot\session-state\621a42a9-2ec6-4af0-a2d9-fde02d818692\files\010h-replays-01`

All three projects were created under that root's `data` directory:
`p010h-replay-03`, `p010h-replay-04`, `p010h-replay-05`. No archived project was
resumed. HEAD remained `ee88d22093dd15dc310b01cb8f73c89916ec4acf`, branch
`nkelly/plan-010`; the freeze captures the current staged/working implementation,
not HEAD alone.

Freeze SHA-256:

`3ca28eee97c2aa88f4a235c9e3480855a28eaf3b97d06b91267913bc4dbea000`

The freeze covers 52 application/test/input/documentation files, source photos,
installed runtime/dependencies, instructions, deployment, limits and the exact
Git staged entries. Every invocation and the final handoff reverified those
inputs. Controls were 1200x1800, cropping forbidden, with captured `prefer`
borders/rounding/tilt. Deployment remained `gpt-5.4-mini`. Explicit flags kept
interpretation **high** and generation **low**, including the clarification
answer. No request/correction/time/token limits were increased.

## Outcomes

| Replay | Result | Calls | Corrections | Final baseline |
|---|---|---:|---:|---|
| 03: named edits | Three proposals; both targeted follow-ups changed only the requested fields. | 6 | 0 | P003 |
| 04: exact return | Two proposals, then exact P001 selection without generation. | 5 | 0 | P001 |
| 05: clarification continuation | Initial proposal, expected identity question, then the original resize after answer `2`. | 5 | 0 | P002 |

**03:** Learned bridge = 1 and breakfast = 2. The multi-photo edit changed
only photo 1's `center_x` **0.29 -> 0.32** and photo 2's width
**0.36 -> 0.33**. The final edit changed only photo 2's corner radius
**16 -> 0**. No unrelated styles, positions, sizes or stacking changed.

**04:** Removed only the four border fields, previously white and 8px wide.
The final request selected the preserved P001; it used one interpretation
call, no generation, no authored changes and no acceptance.

**05:** The actual question was **"Which photo is breakfast?"**, with an
unresolved breakfast reference and `continuation: "design"`. The runner paused
normally; its question exit code is not a service failure. The question-state
snapshot was preserved before answering.

After reviewing that question, Copilot supplied the planned numeric answer
**`2`**, recorded with **`answer_origin: "copilot"`**, not attributed to the user.
It learned breakfast = 2 with quote `2` and the preceding question's event
pointer, retained the original task/source P001, and changed only photo 2's
width **0.36 -> 0.31**. There was no naming-only detour or unrelated edit.

Initial backgrounds were captured in `measurements.json`; qualitative spacing,
overlap and visual appeal were not scored as mechanical passes.

## Assessment and accounting

All three default **integrity** assessments were complete and passed. The
intermediate question in 05 is `not_assessed`, as expected; the completed case is
marked clarification-assisted. Assessment files are saved both in the fresh
projects and the pass root. These offline assessments sent no additional calls.

A separate read-only extraction checked the actual authored-field differences,
directions, name/question evidence, original task/source, exact selection,
completion cursors and lack of acceptance. It also verified every recorded
request's actual stage/reasoning against the frozen selections.

Total: **16/36 calls**, **9 interpretation + 7 generation**, all complete,
**zero validation corrections**, no failed requests and no replay retries.
Known usage: **96,992 input / 10,012 output tokens**; no missing usage records.
HTTP duration sums: interpretation **47.408s**, generation **22.313s**.
These are descriptive measurements, not a speed comparison or billing estimate.

The unused 20-call headroom is **not authorization for further work**.
`closure.json` closes this pass; a new replay, retry, trial or comparison needs
its own approval. No proposal was accepted.

## Preservation and evidence

Exact user staging, HEAD/branch, frozen implementation/runtime, **1,063**
pre-existing photo/project files, closed results records and all six prior
sealed artifact roots were unchanged. This includes the old 010g trial and
the sealed 010h offline pass. No application/prompt/input/dependency edits,
Git writes, original-photo edits or modifications to prior evidence occurred.

Current-index updates and this new results record are separate from those
closed records. Detailed evidence consists of `freeze.json`, the offline input
checks, invocation stdout/stderr, the question-state snapshot, captured project
events/contexts/proposals/request logs, assessments, `measurements.json`,
`closure.json` and preservation checks.

The closed pass contains **140 sealed evidence files**. Its
`evidence-sha256.json` manifest has SHA-256:

`75f8dfe5880473ce70a3cd9a6f1ab850eebd750aeec94240b62e881e93a4ec0e`

## Handoff

This is a clean baseline smoke pass. Move to a **fresh human-led project** next,
using the current conversation contracts rather than the old trial's records.
No human trial has been started here.

These sequences do not directly test shortened multiword names, near-edge
enlargement or whether a recoverable error feels understandable in conversation.
They also do not establish overall design quality or consistent reliability.
The next human trial remains the appropriate test of those 010h improvements;
there is no reason from this pass to expand into another replay/tuning campaign.
