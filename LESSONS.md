# Project lessons, tips and tricks

Practical techniques and reusable development/testing patterns picked up while
building this project. Entries explain how an approach works, illustrate it
with concrete examples, and note its limitations.

The [CLI guide](docs/cli-guide.md) contains the full command reference;
[planning](planning/README.md) contains phase results.

## 1. Replay and offline assessment

Replay conversations from `examples\sequences\01_dark_portrait_adjustments.json`
or `02_landscape_staggered_adjustments.json`. **One message runs per invocation
by default; nothing is automatically accepted.**

```powershell
$sequence = '.\examples\sequences\02_landscape_staggered_adjustments.json'

# Offline: validate the sequence and source-file availability/hashes.
.\.venv\Scripts\python.exe -m ai_collage.cli.replay --sequence $sequence --check

# Live, when authorized: choose a fresh project ID.
.\.venv\Scripts\python.exe -m ai_collage.cli.replay --sequence $sequence `
  --data-dir .\.collage-data-v3 --project YOUR-NEW-PROJECT
```

### Call budgets and stop rules

Repeat the live command with `--resume` to advance that project by one message.
Add `--remaining` only to run all remaining messages without pausing. If the
sequence has four uninterrupted messages, that means at most **16 model calls**,
including validation corrections (at most four per attempt). Explicit answers
have their own bounded attempts. There is no shared allowance
to provision or replenish. A failed step needs an explicit `--resume --retry`;
questions, naming receipts and interrupted steps stop for inspection. Naming
receipts require an explicit recorded answer; replay never approves them for you.
Live execution still needs
authorization; this tooling change does not authorize service calls.

### Saved evidence

Find the cursor and execution summaries in the project's `replay\report.json`,
sequence snapshots/contexts/results in `replay\steps`, and immutable JSON/PNG
proposals in `conversation\proposals`. Unattempted messages may be edited before
resuming. See the [full syntax and safeguards](docs/cli-guide.md#repeatable-prompt-sequences).
Request usage is recorded automatically in the project's `conversation\requests`.
Interactive chat remains local-only unless started with `--live`.

### Assess a saved replay offline

Assess a saved replay **offline**, without generating or accepting anything:

```powershell
.\.venv\Scripts\python.exe -m ai_collage.cli.assess --data-dir .\.collage-data-v3 `
  --project YOUR-REPLAY-PROJECT --profile dark-portrait-adjustments
```

Omit `--profile` for evidence-integrity checks only, applicable to either
sequence. The dark portrait profile additionally checks its specific requested
edits and historical style rules. Numbered reports go in `replay\assessments`;
subjective composition review stays separate.

## 2. How the tests check images

The rendering tests create tiny temporary images in code, drawing known colours
and shapes on them. They pass these through the normal import, layout, and render
workflow, then inspect the resulting pixels. For example:

- Red, green, and blue bands reveal whether panning selects the left, middle,
  or right part of an image.
- A square drawn inside a wide image should remain square when rendered into a
  tall frame, rather than becoming stretched.
- Known border colours and transparent areas let tests check border thickness
  and which overlapping layer shows through, including at rounded corners.
- Coloured corner markers let tests check a tilted photo's angle, size, centre,
  and retention of all four corners.

Because the starting pictures are deliberately simple, the expected colours
and positions are known in advance. Checks can be exact where appropriate,
with small tolerances where resizing or JPEG compression blends pixels.
No AI judges whether the result looks right, and the tests run offline without
using your photos. Real-photo examples still help us judge the composition.

Other tests cover invalid layouts, saved versions, and failures that must leave
previous results intact. See the [CLI guide](docs/cli-guide.md#verification)
for instructions to run the tests.

Implementation examples: [rendering tests](tests/engine/test_rendering.py),
especially `test_cover_pan_selects_source_regions_without_moving_frame` and
`test_tilt_preserves_corners_size_center_and_physical_angle`.

## 3. Pattern: offline-first testing around a model boundary

**Test the surrounding application offline, evaluate the model live, and turn
discovered failures into repeatable regression tests.**

For agent issues, offline tests substitute controlled model responses while
exercising real application code. Responses can represent a valid interpretation,
invalid JSON, a clarification question or a timeout. The application still has
to validate references, update memory, preserve the editing source, render and
save proposals, and enforce retry limits.

| Technique | Purpose |
|---|---|
| Fake model / mocked responses | Supply predictable outputs and failures without calling the service. |
| Monkeypatching | Temporarily replace functions during a test, such as an HTTP operation or network connection function. |
| Network blocking | Make unintended network attempts fail rather than accidentally incur live usage. |
| Temporary projects and synthetic photos | Exercise storage and rendering without altering existing projects or originals. |

A repair can start with a regression test that reproduces an existing defect.
Confirm that it fails, fix the relevant code, then check that it passes alongside
the other applicable tests. This makes the failure repeatable and guards against
reintroducing it; it does not mean deliberately breaking working functionality.

For example, the numeric-name clarification repair supplied a correct model
interpretation of "2 for breakfast and 3 for london eye". The test checked that
our code remembered both identities and continued the original swap. It isolated
the question: **given this model response, does the application behave correctly?**

| Layer | What it tells us |
|---|---|
| Offline tests | Whether the application handles specified situations correctly and preserves its safeguards. |
| Bounded live replay | How the real model and application behave on a known sequence. |
| Exploratory human trial | What happens with unexpected phrasing, user expectations and unplanned combinations. |

Passing mocked responses through the code cannot establish that the real model
will produce those responses, or that a change to `request-intent.md` improves
its understanding. That still needs live evaluation. A live failure can, in
turn, become another focused offline regression case.

This pattern is useful when a costly or unpredictable external service sits
inside an application with substantial testable logic. It enables meaningful
autonomous progress without granting permission for live calls, but does not
replace testing the real integration.

Implementation examples: `FakeModel` in the [agent tests](tests/agent/test_agent.py)
supplies controlled responses; `forbid_network` in
[test fixtures](tests/conftest.py) blocks unintended connections.

## 4. Pattern: validator-guided correction

**Let deterministic validation explain failed constraints so the model can
revise its proposal, then check every revision against the same rules.**

The loop is: **propose, validate, return feedback, revise, validate again**.
Error messages become part of the model-facing interface, not just diagnostics
for logs or developers.

For example, suppose the user asks, "Make photo 2 twenty percent larger."
The model enlarges a tilted photo near the canvas edge, keeping its centre
unchanged. Geometry validation discovers that a rotated corner would extend
beyond the canvas. Instead of just "photo outside canvas", it returns:

| Feedback | What the model can use it for |
|---|---|
| Photo number | Identify the offending layer. |
| Rotated/sampled bounds and pixel overshoot | Understand precisely what does not fit. |
| Safe centre-coordinate ranges, when available | Propose another placement using measured constraints rather than guessing. |

Where the request permits minimal repositioning, the model can move the enlarged
photo slightly inward. The revised layout must pass validation again. The
validator does not move the photo itself, and the model must not quietly shrink
it or enable cropping merely to pass. Feedback can also report that no safe
placement range is available at that size.

| Property | Why it matters |
|---|---|
| Specific, factual feedback | Identify the violated constraint, relevant field or missing evidence, rather than only saying "invalid". |
| Unchanged acceptance rules | A correction must pass validation; feedback does not waive the constraint. |
| Bounded retries and explicit failure | Prevent endless loops, hidden spending and success claims after exhaustion. |

Code calculates the constraints; the model proposes a revision; code checks
again. This is not the model grading its own output, but passing validation only
establishes what the validator checks. Valid geometry does not prove a good
composition or complete understanding of the request.

The previous pattern complements this one: offline tests exercise the validator
and correction machinery; live trials show whether the real model uses the
feedback effectively.

Implementation examples: `_bounds_error` in
[geometry](ai_collage/engine/geometry.py) builds the structured feedback;
`Conversation._feedback` and `Conversation.request` in
[conversation handling](ai_collage/agent/conversation.py) pass it into bounded
correction attempts.
