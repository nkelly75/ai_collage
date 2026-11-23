# 015 live replay follow-up: 01-05

**Status:** Executed and closed. All five replays completed and passed their
offline assessments and requested authored-edit checks. This is a bounded
post-restructure regression result, not human sign-off or general reliability.
The [015 offline restructuring results](015_results.md) remain a separate record.

## Authorization and freeze

After reviewing the offline restructuring and staging its changes, the user
authorized one pass of unchanged replays 01-05 under a fresh shared **72-call
ceiling**. The user also preauthorized the same two expected supplemental
answers as before, conditional on reviewing the actual naming receipt/question.
Unexpected gates or failures would stop the affected replay; the other
independently authorized sequences could continue once.
No replay-level retries, tuning, fixes, effort escalation, extra answers or
acceptance were authorized.

Fresh evidence root:

`C:\Users\nkell\.copilot\session-state\621a42a9-2ec6-4af0-a2d9-fde02d818692\files\015-replays-01`

Fresh projects `p015-replay-01` through `p015-replay-05` were created beneath
its `data` directory. No previous project was resumed. The freeze captured the
actual staged/working implementation, not HEAD alone. Branch remained
`nkelly/llm-wip-1`, HEAD
`a40d77874b6e7370e780105bfea1c0b4d7a5aca9`.

Freeze SHA-256:

`e758afb04ca1e8e0be0d79eb085d623580e25352ad41bb638aa423263e3c7c05`

Deployment was **`gpt-5.4-mini`**, with explicit **high interpretation / low
generation**, including supplemental answers. All five definitions passed
offline `--check`; their normalized sequences and source-photo hashes match
the [previous five-replay pass](012_replay_results.md). Sequence 02 used
1600x900; the others used 1200x1800. Cropping remained forbidden, with captured
`prefer` borders/rounding/tilt. Instructions, response formats, dependencies
and request/correction/deadline/token limits remained frozen throughout.
Execution used the new `ai_collage.cli.replay` entry point.

## Outcomes

| Replay | Outcome | Calls | Final baseline |
|---|---|---:|---|
| 01: dark portrait | Four proposals; existing mechanical profile passed. | 8 | P004 |
| 02: landscape | Four proposals; integrity and requested edits passed. | 9 | P004 |
| 03: named edits | Reviewed naming receipt, then three proposals; integrity and requested edits passed. | 7 | P003 |
| 04: exact return | Two proposals, then exact P001 selection; integrity and return checks passed. | 5 | P001 |
| 05: clarification | Initial proposal, reviewed question, original resize after answer `2`; integrity and requested edit passed. | 5 | P002 |

Authored checks compared complete saved recipes, allowing only each requested
field change, independently of the general integrity assessments:

**01:** Only photo 2 width changed **0.24 -> 0.21**, preserving its centre.
The next edit removed only the four borders; the final edit set only the four
rotation angles to zero. The existing `dark-portrait-adjustments` profile
passed all four steps.

**02:** Photos 1 and 4 exchanged centres, preserving sizes and styles. Their
horizontal centres already matched, so only their vertical centres changed.
The next edit changed only photo 2's `center_x` **0.185 -> 0.29** and width
**0.16 -> 0.14**, reducing its pixel-space centre distance to photo 3. The final
edit changed only photo 3's corner radius **12 -> 0**.

The initial landscape generation needed **one internal validation correction**:
photo 1's sampled rotated footprint extended five pixels above the canvas.
The corrected proposal validated and the sequence continued normally.
This was the existing bounded correction loop, not a replay retry or a code/
prompt change; the rejected response and geometry feedback remain preserved.

**03:** The actual receipt proposed exactly **bridge = 1; breakfast = 2**.
The pending state had no learned names or baseline, and its held action was the
original combined teaching/design task. After inspection, Copilot supplied
**"Yes, remember those"**, recorded with `answer_origin: "copilot"`. Approval
saved exactly those mappings and generated the original requested collage.
The next edit changed only photo 1's `center_x` **0.28 -> 0.33** and photo 2's
width **0.36 -> 0.34**; the final edit changed only photo 2's corner radius
**14 -> 0**.

**04:** Removing borders changed only the four border fields. "Go back to the
first proposal." then selected P001 on its **first interpretation**, with
ordinal evidence `first proposal`. It reused the same saved proposal and PNG
paths; the PNG matches P001's published digest:

`4ba872625c03c730ffbeef7d41938706b12456336f4db7c4ab50ea79bc28f785`

The return used one interpretation call, no generation call, created no third
proposal, and left P001 as the working baseline without accepting it.

**05:** The actual question asked which of photos 1-4 was breakfast, while the
original resize remained pending against P001. After inspection, Copilot
supplied the planned **`2`**, recorded as Copilot-authored. Continuation retained
the complete original task/source and changed only photo 2's width
**0.38 -> 0.34**. No durable name or naming receipt was introduced.

## Accounting, preservation and closure

Total: **34/72 calls**, **18 interpretation + 16 generation**, including the
one internal generation correction. All 34 request records completed; known
usage was **205,257 input / 17,533 output tokens**, with no missing usage.
Recorded HTTP duration sums were **73.453s interpretation / 49.360s generation**;
these are descriptive, not a controlled performance comparison.

All 15 generated proposals passed integrity checks. All five scripts reached
their final cursor, and only the two preauthorized supplemental answers were
used. No replay retries, acceptances, application/prompt/input changes, installs,
Git writes, or archived-project recovery occurred.

Fresh before/after fingerprints preserved the user's index and staged diff,
HEAD/branch, implementation/runtime, **4,565 existing files** across original
photos, project/trial data and the separate Foundry directory, and **3,319 prior
session evidence files**, including the completed 015 restructuring evidence.
Only this results record and its planning-index link were added/updated for the
handoff; they remain unstaged for the user.

The fresh evidence root retains authorization/freeze, offline input checks,
invocation captures, pre-answer state and reviewed gates, canonical events,
contexts, proposals/PNGs, request records, offline assessments, full-recipe edit
verification, measurements, preservation/closure records and a sealed hash
manifest. The unused **38 calls are closed**, not permission for more work.
Human-led trials, further replays, fixes, commits and branch integration remain
separately gated. Scripted success does not establish subjective composition
quality or approve merging to `main`.
