# 012 live replay follow-up: 01-05

**Status:** Executed and closed. Separately authorized on 23 November 2026,
after [012's offline implementation](012_results.md). Four replays completed;
04 stopped at its exact-return request. This is not a clean all-pass regression
result or human sign-off.

## Authorization and freeze

The user requested the previous reasoning configuration, then selected all five
unchanged sequences and approved a fresh shared **72-call ceiling**: 16 scripted
messages plus the expected naming confirmation in 03 and identity answer in 05,
each with the existing four-call maximum. No replay retries, tuning, effort
escalation, extra answers or acceptance were authorized.

Fresh evidence root:

`C:\Users\nkell\.copilot\session-state\621a42a9-2ec6-4af0-a2d9-fde02d818692\files\012-replays-01`

Projects `p012-replay-01` through `p012-replay-05` were created under its `data`
directory; no archived project was resumed. The freeze captures the user's newly
staged implementation and actual working files, not HEAD alone. HEAD remained
`ae9086e6f409cd5dd244b54cf74f9509ff66121c`, branch `nkelly/plan-010`.

Freeze SHA-256:

`77b20077a1ecebc8d10d81133bf0a7320d3625389eb5bfbb69b3644ac305b71f`

Deployment remained `gpt-5.4-mini`, with explicit **high interpretation / low
generation**, including supplemental answers. Sequence 02 used 1600x900;
the others used 1200x1800. Cropping was forbidden, with captured `prefer`
borders/rounding/tilt. Instructions, dependencies and request/correction/deadline/
token limits remained frozen. All five definitions passed offline `--check`.

## Outcomes

| Replay | Outcome | Calls | Final baseline |
|---|---|---:|---|
| 01: dark portrait | Four proposals; existing mechanical profile passed. | 8 | P004 |
| 02: landscape | Four proposals; integrity passed. | 8 | P004 |
| 03: named edits | Reviewed naming gate, then three proposals; integrity passed. | 7 | P003 |
| 04: exact return | Two proposals; return failed after the allowed interpretation correction. Incomplete. | 6 | P002 |
| 05: clarification | Initial proposal, reviewed question, original resize after answer `2`; integrity passed. | 5 | P002 |

Authored changes were checked separately from general integrity:

**01:** Photo 2 width **0.28 -> 0.24**, with its centre unchanged; then only the
four borders were removed; then only the four rotation angles were set to zero.
The existing `dark-portrait-adjustments` assessment passed all four steps.

**02:** Only the centres of photos 1 and 4 were exchanged, preserving sizes and
styles. The next edit changed only photo 2's `center_x` **0.185 -> 0.24** and width
**0.17 -> 0.15**. The final edit changed only photo 3's corner radius **14 -> 0**.

**03:** The actual code-rendered receipt proposed **bridge = 1; breakfast = 2**.
Its preserved pending state had no names and no baseline. After reviewing the
exact batch and original combined task, Copilot supplied **"Yes, remember those"**
with `answer_origin: "copilot"`. Approval saved exactly those names and generated
the original requested collage, not an interpretation of "Yes" as a new design.
The subsequent edit changed only photo 1's `center_x` **0.285 -> 0.315** and photo
2's width **0.36 -> 0.32**; the final edit changed only photo 2's corner radius
**14 -> 0**.

**05:** The saved question asked which of photos 1-4 was the breakfast photo.
After reviewing it, Copilot supplied
the planned **`2`**, recorded as Copilot-authored. The original resize retained
source P001 and changed only photo 2's width **0.34 -> 0.30**. **No durable name
was learned**, and no naming gate or naming-only detour was introduced.
The terminal capture of the question had a Windows encoding artefact; canonical
project events preserve the actual text, and subsequent captures used UTF-8.

## 04: Exact-return failure

For "Go back to the first proposal.", both interpretation responses selected
P001 but supplied `navigation.kind: "id"` evidence:

- First quote: `P001`, which was absent from the user's wording.
- Correction quote: `first proposal`, which contained no explicit proposal ID.

The validator rejected both. This request needed ordinal evidence rather than
an ID quote. No selection, generation or acceptance followed; the verified
working baseline remained P002. The replay stopped without a retry or prompt/
code change. Independently authorized 05 was then run once.

Assessment truthfully marks 04 incomplete, while its two published proposals
pass integrity checks. The failed return is `not_assessed`, not a successful
restoration. Unlike the previous [010h replay pass](010h_replay_results.md), this
run did not complete exact return. It warrants focused review; this single
observation does not establish whether prompt changes or model variability
caused the difference.

## Accounting, preservation and interpretation

Total: **34/72 calls**, **19 interpretation + 15 generation**, with one internal
interpretation correction call in 04 and two rejected interpretation responses.
All 34 HTTP request records completed; the failure was interpretation validation,
not a service failure. Known usage: **202,232 input / 15,546 output tokens**,
with no missing usage. Recorded HTTP duration sums were **66.765s interpretation /
46.658s generation**, descriptive rather than a performance comparison.

No replay retries, acceptances, application/prompt/input changes, dependency
installs or Git writes occurred. The user's staging, HEAD/branch, **1,154**
pre-existing photo/project files, **1,248** files in seven prior sealed roots
and the saved 012 offline evidence matched the fresh freeze at closure.
Current guide/index status updates are documentation-only handoff changes.

The live naming gate and task-local numeric continuation provide encouraging
evidence for clearer memory ownership and recoverable progress. Ordinary numbered
edits in 01/02 acquired no extra naming stops. However, 04 is a genuine failed
interaction; retaining the last good collage is not equivalent to fulfilling it.
These scripts do not directly establish multiword paraphrase quality, multiple
labels/four-beach descriptions, or how recovery feels to a human.

Evidence includes the freeze and authorization, invocation captures, pending
receipt/question snapshots, original events/contexts/proposals/request records,
offline assessments, `measurements.json`, `closure.json` and the sealed hash
manifest. **The unused 38 calls are not permission for further work.**
No additional replay, fix/retest pass or human-led trial was started.

The sealed manifest covers **264 evidence files** and has SHA-256
`865bbf4bf0f6f8d9f3468d969e82e90c22bfdafeebd75d8b6472943e92648e70`.
