# Local CLI Guide

The current offline engine uses **layout/project format 3**. It imports original
JPEG/PNG photos and deterministically renders editable JSON recipes, without
credentials or model calls. See the [layout field guide](layout-format.md) for
syntax and the [README](../README.md) for the project story.
Implementation and trial history is indexed in [planning](../planning/README.md).

Jump to [chat](#conversational-proposals-optional),
[replay](#repeatable-prompt-sequences) or [assessment](#assess-saved-replay-evidence-offline).

## Setup (PowerShell, Python 3.12+)

Run from the repository root:

```powershell
python -m venv .\.venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

Activation is unnecessary. If `python` is not on PATH, use its full path.
Installation downloads packages; rendering and routine tests run offline.
Do not run the separate `temp-foundry-test` experiments as part of this workflow.

## Fresh projects and old archives

Format 1 and 2 projects and saved snapshots are **untouched archives**.
Their PNGs remain viewable, but the CLI rejects their format; there is no
migration. Do not edit their metadata or apply new recipes to them.

The default data directory remains `.collage-data`. The commands below instead
use a **fresh `.collage-data-v3` root** to avoid touching archived projects.
Both roots are ignored by Git. Put the global `--data-dir` option before the
command and use the same root for every command in a workflow.

## Render the supplied photos

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 create --project portrait-demo --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 inspect --project portrait-demo
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 apply-layout --project portrait-demo --layout .\examples\portrait_9x16.json
Invoke-Item .\.collage-data-v3\users\local-dev\projects\portrait-demo\renders\v0001.png
```

The first recipe makes a 900x1600 (9:16) white canvas. Import order assigns
Bridge 1, breakfast 2, London Eye 3, bookshop 4. Photo numbers are identifiers,
not stacking positions or content recognition.

`create` fails if the project exists. Choose a fresh name consistently rather
than deleting a previous project. To try the second 900x1200 (3:4) arrangement:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 apply-layout --project portrait-demo --layout .\examples\portrait_3x4.json
```

Applying this after the first recipe accepts version 2, leaving version 1 untouched.
Canvas aspect ratio and positions come from the JSON, not separate CLI flags.

## Commands and paths

| Command | Behavior |
|---|---|
| `create --project ID --images FILE...` | Validate/import 2-6 JPEG/PNG photos in argument order; fail if the project exists. No layout is generated. |
| `inspect --project ID` | Show photo IDs/dimensions/aspect ratios, accepted versions, current version, and paths. Works before the first layout. |
| `apply-layout --project ID --layout FILE` | Validate recipe/current state, resolve geometry, and render before accepting the next immutable snapshot and updating the current pointer. |
| `render --project ID [--version N]` | Reopen and rerender an accepted new-format version, defaulting to current. No new version or current-pointer change. |

Results are JSON on stdout; errors use stderr and nonzero exit status.
`apply-layout` returns `version`, `layout_path`, and `render_path`.

For a selected data root, files live beneath:

```text
users\local-dev\uploads\<asset-id>.jpg
users\local-dev\projects\<project-id>\project.json
users\local-dev\projects\<project-id>\layouts\v0001.json
users\local-dev\projects\<project-id>\renders\v0001.png
```

Project IDs are 1-64 lowercase letters/digits/hyphens, beginning and ending with
a letter or digit. Windows device names such as `con` and `com1` are rejected.
Imported paths resolve known UUID assets within the owner's uploads directory;
recipes cannot supply paths. `local-dev` is a namespace, not authentication.
There are no delete, reset, photo replacement/removal, or migration commands.
See the [layout field guide](layout-format.md) for recipe fields and coordinates.

### Saved snapshots and schema maintenance

Saved snapshots contain `schema_version: 3`, an accepted `version`, the authored
`recipe` and derived `geometry`. Edit and reapply the recipe, not the snapshot.
Derived top-left positions are not authored `center_x`/`center_y` values.
Reopening recomputes geometry and rejects inconsistencies.

The generated schema is checked against the models in the tests. To regenerate
it after intentionally changing a contract, run from the repository root:

```powershell
.\.venv\Scripts\python.exe -c "import json; from pathlib import Path; from ai_collage.engine.models import InputLayout; Path(r'docs\layout.schema.json').write_text(json.dumps(InputLayout.model_json_schema(), indent=2) + '\n', encoding='utf-8')"
```

## Conversational proposals (optional)

Use photo numbers or user-taught names to request layouts and edits. The agent
cannot see photo contents and asks when an essential reference is unclear.
Proposals remain separate from explicitly accepted versions.
Live model requests require explicit authorization.

Engine-only users need no optional dependencies. To install the agent into the
root application environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-agent.txt
```

Use the pinned agent requirements, not the separate `temp-foundry-test` environment.

To inspect interpretation/generation instructions offline, without credentials
or model calls:

```powershell
.\.venv\Scripts\python.exe -c "from ai_collage.agent.provider import instruction_bundle; print(instruction_bundle())"
```

Create a fresh format 3 project with `create`, using `.collage-data-v3`.
Start a new conversation by choosing its canvas:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 chat --project YOUR-NEW-PROJECT --canvas 1200 1800 --no-open
```

To resume an existing conversation locally:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 chat --project YOUR-EXISTING-PROJECT --no-open
```

Without **`--live`**, chat is local-only: it does not initialize credentials or
send model requests. `/status`, `/help`, and `/quit` are available without
proposals; `/show`, `/rate`, and `/accept` act on existing successful proposals.
A resume uses the captured preferences and effective controls. Omit
`--canvas`, or supply the same dimensions; use `/canvas` for an explicit change.

### Chat options

| Option | Behavior |
|---|---|
| `--live` | Enable model requests after authorization; otherwise chat stays local-only. |
| `--no-open` | Print preview paths without opening the OS image viewer. |
| `--preferences FILE` | Capture defaults when creating a conversation. |
| `--generation-reasoning high\|low` | Generation effort; default `low`. Also available in replay. |
| `--interpretation-reasoning high\|low` | Interpretation effort; default `high`. Also available in replay. |

Reasoning settings apply to corrections too, remain fixed for the session/run,
and never escalate automatically. Repeat nondefault flags on replay resume;
changing either selection is rejected.

### Local commands

| Local command | Behavior |
|---|---|
| `/show P001` | Print/open the immutable preview; never regenerate it. |
| `/rate P001 worked "Looks right"` | Store optional `worked`, `partly`, or `failed` feedback; no inference or acceptance. |
| `/accept P001` | Publish the selected recipe and byte-identical preview as an accepted version; no model call or replacement render. |
| `/status` | Show controls, baseline, accepted version, captured defaults, and project request usage. |
| `/canvas 1600 900` | Change future proposal dimensions, leaving existing previews unchanged. |
| `/cropping allow` or `/cropping forbid` | Change future cropping permission; whole photos are the default. |
| `/help` or `/quit` | Explain commands or exit without losing the conversation. |

Unknown commands and invalid arguments fail locally. Without `--no-open`,
Windows opens successful PNGs in the OS viewer; viewer errors retain the path.
EOF/Ctrl+C exit cleanly. Ordinary text is a model request only with `--live`;
no separately provisioned run or allowance is needed. Proposal IDs are distinct from accepted versions.
An older proposal can be accepted as the next version and becomes the editing
baseline; an already-current acceptance is idempotent. Current canvas/cropping
controls must permit the chosen proposal. External accepted-version changes,
corrupt state, and altered previews produce explicit conflicts, not silent repair.

### Natural-language requests

| Example | Behavior |
|---|---|
| "Make photo 2 smaller" | Edit the selected working proposal. |
| "Photo 2 is breakfast" | Remember a clear new name automatically. |
| `2 for breakfast and 3 for london eye` | Answer a multi-name clarification and continue its original edit. |
| "What photo names do you know?" | List active names/numbers without changing the layout or pending task. |
| "Change breakfast to photo 1" | Confirm if this reassigns an existing name. |
| "Forget the name breakfast" | Forget that label only; later use needs fresh identity evidence. |
| "Go back to the first one" | Select its exact preserved PNG, without generation or acceptance. |
| "Go back to the first one and make photo 2 smaller" | Edit that earlier source; failure leaves the current baseline unchanged. |
| "Undo the last two edits" | Follow the current proposal's editing history, skipping no-ops. |

An identity answer such as `2` or `Photo 2` also remembers the requested name.
Names survive restart and proposal returns; one photo may have several labels.
Casual references can resolve existing names without saving extra aliases.
Memory-only requests create no proposal; learned names can remain saved if a
subsequent layout edit fails.

A conflicting reassignment pauses the whole memory batch and associated edit.
Reply "Yes, remember those" or "No, that's not right"; approval uses `--live`
and may consume a call. Until resolved, canvas/cropping changes and acceptance
are blocked, but read-only commands remain available.

Essential ambiguity produces a question. Rejecting a composition can request a
fresh arrangement; rejecting a targeted edit can retry its original task/source.
Enlargement may minimally reposition resized photos to fit unless positions
are explicitly fixed. Invalid geometry is rejected, not silently repaired.

### Request recovery

| Outcome | Next action |
|---|---|
| Validation rejected before publication | Rephrase or request another change; chat identifies the unchanged baseline only after verifying it. |
| Confirmed generation timeout before publication | Repeat the prompt, say "try again", or repeat the last clarification answer; the original task/source can continue after restart. |
| Publication/I/O or integrity failure | Inspect the explicit error; the same unchanged-state assurance does not apply. |

A new independent request replaces the pending task. Retries need an explicit
message and can incur more usage; "try again" is not a universal recovery command.
Full diagnostics and raw responses remain in conversation events.

### Preferences

Defaults live in:

```text
.collage-data-v3\users\local-dev\preferences.json
```

```json
{
  "preferences_version": 1,
  "borders": "prefer",
  "rounding": "prefer",
  "tilt": "prefer"
}
```

Each effect accepts `prefer`, `avoid`, or `agent_choice`. These are overridable
design defaults, not restrictions. Edit this file explicitly for **future**
conversations, or select `--preferences FILE` when creating one. Existing
conversations retain their snapshot; requests never rewrite the defaults file.

### Conversation files and usage

State/events and immutable `proposals\P001` artifacts live under the project's
`conversation` directory. Usage records are `conversation\requests\attempt-0001.json`,
etc.; these are accounting, not a cumulative usage cap. Runtime files are ignored
by Git.

`/status` reports **Known usage** and identifies requests with missing usage.
Unknown does not mean zero consumption or no charge; missing counts are not
estimated. Machine-readable `unknown_usage_attempts` contains IDs, not a count.

Model context includes up to three recent logical tasks plus up to twelve
relevant compact task records, not the full audit log. Saved names persist separately.

Current record versions: conversation/event/proposal/acceptance intent **8**,
replay report **9**, replay step/assessment **7**, request attempt **2**.
Unsupported versions are untouched archives: use fresh conversational projects,
not a migration. Supported format-3 deterministic recipes/snapshots remain usable.

### Repeatable prompt sequences

`python -m ai_collage.cli.replay` runs repository-owned JSON sequences through the
same conversation/provider operations as chat. It captures results, not
subjective quality or benchmark passes, and **never accepts a proposal**.
Mechanical assessment reads saved replays offline, separately from execution
and acceptance.

The supplied sequences are:

- `examples\sequences\01_dark_portrait_adjustments.json`: the original four messages, with
  reopening before straightening; its mechanical checks are an explicit assessment profile.
- `examples\sequences\02_landscape_staggered_adjustments.json`: an exploratory landscape
  composition and three provisional follow-ups, editable before they are attempted.
- `examples\sequences\03_named_photo_adjustments.json`: teach two names, resume
  for a two-photo edit, then remove rounding from one named photo.
- `examples\sequences\04_exact_proposal_return.json`: remove borders, then resume
  and select the first proposal exactly.
- `examples\sequences\05_clarification_continuation.json`: request an untaught
  name; pause for the planned identity answer `2` via `--answer`, not a scripted
  third message.
- `examples\sequences\06_photo_identity_memory.json`: the ten-step learning,
  listing, reassignment, forgetting and fresh re-establishment story. Its required
  questions and conflicting-name receipt need separately recorded replies.

Sequences use `record_version: 1`, a stable `name`, ordered `images` paths
relative to the sequence file, fixed `canvas` dimensions and `messages`.
Each message has a unique `name`, `prompt` and optional `reopen_before: true`.
Photo IDs follow image order; `canvas.cropping` defaults to false. Styling uses
captured conversation defaults.

Validate sequence structure and source-file availability/hashes **offline**,
without creating a project, opening credentials, or sending requests:

```powershell
.\.venv\Scripts\python.exe -m ai_collage.cli.replay --sequence .\examples\sequences\02_landscape_staggered_adjustments.json --check
```

After separate live authorization, run **only the next message**:

```powershell
.\.venv\Scripts\python.exe -m ai_collage.cli.replay --sequence .\examples\sequences\02_landscape_staggered_adjustments.json --data-dir .\.collage-data-v3 --project YOUR-FRESH-PROJECT
```

| Option | Behavior |
|---|---|
| `--resume` | Run the next message in the same project. |
| `--remaining` | Run all remaining messages when authorized, stopping at questions/receipts/failures. |
| `--resume --retry` | Explicitly retry a failed step when authorized. |
| `--resume --answer TEXT --answer-origin user\|copilot` | Record an answer to the pending question or naming receipt. |

Resume verifies photos, canvas, instructions, reasoning settings and state.
Attempted messages cannot change; unattempted messages can. Manual chat/control/
acceptance changes block resume. Completed replays make no further calls.

Memory-only steps advance without a proposal. Questions and conflicting-name
receipts pause without advancing or answering automatically. After reviewing
the actual question/receipt, supply a recorded answer:

```powershell
.\.venv\Scripts\python.exe -m ai_collage.cli.replay --sequence .\examples\sequences\02_landscape_staggered_adjustments.json --data-dir .\.collage-data-v3 --project YOUR-REPLAY-PROJECT --resume --answer "Photo 2" --answer-origin user
```

Use `--answer-origin copilot` only for Copilot-authored answers. For a naming
receipt, use e.g. `--answer "Yes, remember those"` after reviewing every mapping.
Answers/origins are recorded separately from the script; rejection discards the
task without generating a layout. Do not bypass resume checks to answer.

Each message/retry/answer has at most four calls, with at most two interpretation
attempts; generation shares the remaining calls. Four uninterrupted messages
therefore allow at most 16 calls. Each scripted step permits at most two answer
turns. Answers/retries also consume any optional pass-wide call cap.

Service failures stop immediately. Interrupted pending executions need evidence
inspection, not blind retry. Retrying a failed answer preserves its answer/origin.
Unsupported replay versions cannot resume; their evidence remains unchanged.

Under the project's normal data directory, inspect:

```text
replay\report.json
replay\instructions.md
replay\steps\0001\sequence.json
replay\steps\0001\context-0001.json
replay\steps\0001\result.json
conversation\proposals\P001\proposal.json
conversation\proposals\P001\preview.png
conversation\requests\attempt-0001.json
```

`report.json` holds the cursor and every execution, including failures/retries.
Step results record task/source, actual recipe differences, identity snapshots,
request contexts, usage, corrections and timing. Raw responses remain in
conversation events. Resume preserves existing executions/artifacts.

### Optional Autopilot call cap

For an explicitly authorized batch, append
`--call-budget PATH --max-calls 200` to each replay command. A new path creates
a small pass-local limit/used record automatically; using that same path across
projects and invocations retains consumption and rejects limit changes.
Run the batch sequentially (single writer). Reservations are durable before
HTTP dispatch; corrections, failed HTTP requests and timeouts consume calls.
Exhaustion blocks dispatch. Token/time limits and replay stop rules still apply.

Use a fresh path only for a newly authorized pass, not to renew an exhausted
or stopped one. Ordinary replay/chat needs no call-budget file. This opt-in
guard does not add fields to model context or bind a replay to a budget path.
`--call-budget` enables the guard; `--max-calls` alone does not.

### Assess saved replay evidence offline

Assessment reads saved evidence offline, without rendering, accepting or making
model requests. It needs no credentials, original sequence file or original
source-photo paths.

```powershell
# Either sequence: verify saved evidence only.
.\.venv\Scripts\python.exe -m ai_collage.cli.assess --data-dir .\.collage-data-v3 --project YOUR-REPLAY-PROJECT

# Dark portrait sequence: also check the specific historical expectations.
.\.venv\Scripts\python.exe -m ai_collage.cli.assess --data-dir .\.collage-data-v3 --project YOUR-REPLAY-PROJECT --profile dark-portrait-adjustments
```

| Profile | Checks |
|---|---|
| `integrity` (default) | Hashes, source relationships, valid geometry/controls, audited naming changes, result consistency and completion; **not whether edits followed user intent**. |
| `dark-portrait-adjustments` | Sequence 01's 1200x1800 four-photo edits: dark background, relative size, subtle near-white borders, rounding/tilt, shrink, border removal and straightening. Not a landscape profile. |
| `photo-identity-memory` | Sequence 06's ten memory milestones, questions, listings, exact reassignment approval and fresh identity answers, plus targeted 10% width reductions without unrelated changes. |

Profile rules are sequence-specific, not universal composition requirements.
The dark portrait profile requires reopening before straightening and border
RGB channels at least 240. Identity resize tolerance is 0.000001; centres,
other authored fields and stacking must remain unchanged.

```powershell
.\.venv\Scripts\python.exe -m ai_collage.cli.assess --data-dir .\.collage-data-v3 --project YOUR-REPLAY-PROJECT --profile photo-identity-memory
```

Reports append to `replay\assessments\0001.json`, `0002.json`, etc.; previous
evidence is never rewritten. Exit **0** means complete with all applicable
mechanical checks passed; **1** means failed or incomplete. Questions,
interruptions and service failures remain `not_assessed`. A discarded task
can pass integrity without an image.

Clarification-assisted steps are marked `clarification_assisted: true`; later
retries do not erase original failures or imply first-attempt success.
Visual quality needs separate review; assessment has no automated AI judge.

### Authorized live use

These are instructions, **not permission to run paid calls**. Live use requires
a keyless Azure login with access to the configured deployment. The application
does not initiate interactive login. If Azure CLI is installed at the following
location but missing from the shell's PATH, add it for the current process:

```powershell
$env:PATH = 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin;' + $env:PATH
```

This changes only the current PowerShell process and its children, not system
configuration.

For explicitly authorized live use, add `--live` to the chat command. Replays
use their explicit execution command instead. Neither needs a shared run or
allowance.

| Limit | Value |
|---|---|
| Calls per request | At most 4, including corrections; interpretation gets at most 2 attempts. |
| Input/output | 50,000 input tokens; 25,000 output tokens including reasoning. |
| Interpretation deadline | 120 seconds shared across its attempts and validation. |
| Generation deadline | 180 seconds shared across its attempts and validation. |

Nested waits do not renew deadlines; local rendering/publication is outside them.
Only completed invalid JSON or hard layout/control violations trigger corrections,
not service/authentication, incomplete-response, timeout or render-I/O failures.
SDK/transport retries and unexpected extra inference are disabled.

Input preflight uses a conservative serialized-byte bound, separate from actual
provider usage. Optional history can be trimmed; essential task/source,
questions and correction feedback are retained. Oversized essential input fails
before dispatch without consuming a call or changing the baseline.

Photos, filenames, local paths and credentials are **not automatically sent**.
The model receives photo numbers/dimensions, recipes, defaults, controls and
conversation text. User-entered text is not scrubbed. Hosted history, tools and
response storage are disabled; storage-off does not promise no service logging.

## Emma's layered 2:3 example

`examples\emma_2x3.json` is the 1200x1800 whole-photo approximation of
[Emma's manual collage](../photos/em_manual_collage.jpg), with 15-pixel white
borders. It is not an automatic reconstruction or a pixel match of the manual
reference. Intentional overlap, not cropping, hides parts of the whole photos.

Import the same four photos into a fresh project:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 create --project emma-demo --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 apply-layout --project emma-demo --layout .\examples\emma_2x3.json
```

Back to front, the layer array contains Eye (3), bookshop (4), breakfast (2),
and Bridge (1). The larger Bridge overlaps the others.

## Emma's framed variation

`examples\emma_framed_2x3.json` retains that canvas, order, and whole-photo
Bridge/Eye placements but uses independently shaped cover frames for the
bookshop and breakfast. The bookshop uses zoom 1.05 and pan 0/0.9, revealing more
of the entrance mat, projecting sign, and foreground street.

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 apply-layout --project emma-demo --layout .\examples\emma_framed_2x3.json
```

## Emma's rounded variation

`examples\emma_rounded_2x3.json` retains the refined framed composition and
15-pixel white borders, adding a 10-pixel photo radius (25-pixel outer radius).

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 apply-layout --project emma-demo --layout .\examples\emma_rounded_2x3.json
```

## Emma's evolved tilted demo

`examples\emma_tilted_2x3.json` evolves the composition rather than trying to
match the manual reference more exactly. It uses charcoal `#282A2E`, 10-pixel
white borders, 12-pixel photo radii, and gentle tilts: Bridge -2.5 degrees,
breakfast +2, Eye -1.5, bookshop +1.25.

The bookshop is near the top-right; Bridge is enlarged to a 720-pixel outer
width near the bottom-left, with 12-pixel sampled-footprint corner clearances.
Breakfast is shifted right but retains 40 pixels of right clearance. Every
rotated frame stays on canvas, while intentional inter-photo overlaps remain.

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 apply-layout --project emma-demo --layout .\examples\emma_tilted_2x3.json
```

## Emma's London Eye background demo

`examples\emma_london_eye_3x4.json` needs a **different three-photo mapping**:
Bridge 1, London Eye 2, bookshop 3. Breakfast is not imported.

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 create --project emma-london-eye-demo --images .\photos\01_tower_bridge.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 apply-layout --project emma-london-eye-demo --layout .\examples\emma_london_eye_3x4.json
```

The 1200x1600 canvas matches the uncropped night photo, placed first in `layers`
as a borderless, untilted full-canvas whole photo. A subtly tilted bookshop sits
upper-left and the larger Bridge lower-right. The latest composition keeps the
smaller foreground photos, corner clearances, 10-pixel white borders, and
12-pixel photo radii, exposing more of the wheel.

## Input layouts and saved versions

Edit the recipe, not `layouts\v0001.json`. The recipe contains canvas/layers,
normalized boxes, mode/crop choices, and optional frame styling. A saved
snapshot contains the validated `recipe` once, a separate `geometry` array,
`schema_version: 3`, and a backend-assigned accepted `version`.

Derived geometry records outer and inset pixel boxes, resolved normalized
height, optional fractional source crop, and optional rotated footprint.
Normalized resolved boxes describe the derived top-left, not the authored centre.
Reopening recomputes these values and rejects inconsistencies. A recipe has
no paths, owner/project settings, accepted revision, or derived pixel fields.
Changing it does not change any previous snapshot or preview.

Acceptance updates the current pointer last. Invalid input, decoding/rendering
failure, or ordinary publication failure leaves the prior accepted state
intact. Rerendering replaces the PNG only after success, never the source or
snapshot. The store assumes one local writer; it is not a concurrent service
or a crash-recovery database.

## Limits and safety

Photos are limited to 25 MiB compressed and 40 million decoded pixels each.
Only single-frame JPEG/PNG files are accepted; EXIF orientation is applied.
Canvas axes are 1-4096 pixels. Recipe, project, and snapshot JSON documents are
limited to 1 MiB **in bytes**, read with a bounded read before parsing.
Malformed encoding, parser recursion failures, duplicate keys, and non-finite
numbers produce explicit errors. Unknown fields and numeric strings/booleans
are rejected by the strict models.

## Rendering rules

### Outside photo borders

`border.width_px` is outside the photo but inside its layout box. Keeping the
same outer width while adding a border makes the photo smaller, not obscured.
Transparent photo interiors remain transparent to lower layers.

### Fixed frames, pan, and zoom

Whole mode derives height; cover mode requires it. Cover crops uniformly fill
the inset frame, with zoom relative to minimum cover scale and pan selecting
source position over available travel. Moving a crop never moves its frame.

### Rounded corners

One `corner_radius_px` describes the photo edge; a positive outer border radius
adds border thickness. Zero keeps both edges square. Rounded corners reveal
lower layers rather than painting rectangular white corners.

### Tilt

`rotation_degrees` rotates the complete frame clockwise for positive values.
The authored centre is unchanged; the engine checks the expanded sampled
footprint against the canvas. It never silently crops a tilted corner.

See the [layout field guide](layout-format.md) for current units, limits, and
geometry, and the [historical design decisions](../planning/003-layout-evolution.md)
for the rationale behind the feature increments.

## Code and test organization

| Package | Responsibility | Tests |
|---|---|---|
| `ai_collage\engine` | Deterministic models, geometry, photo rendering and project storage | `tests\engine` |
| `ai_collage\agent` | Conversation, interpretation safeguards, requests/provider and prompts | `tests\agent` |
| `ai_collage\evaluation` | Callable replay execution and offline evidence assessment | `tests\evaluation` |
| `ai_collage\cli` | Argument parsing and terminal chat/presentation | `tests\cli` |

The agent depends on the engine; evaluation uses both, and CLI modules expose
their operations. Neither engine nor agent depends on evaluation or CLI.
`tests\conftest.py` and `tests\helpers.py` hold shared fixtures/helpers.
The standard `python -m ai_collage` entry point is unchanged; replay and
assessment use `python -m ai_collage.cli.replay` and
`python -m ai_collage.cli.assess`. Old module paths are not retained.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q .\tests\engine .\tests\cli
```

With the optional agent dependencies installed, run agent/evaluation tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q .\tests\agent .\tests\evaluation
```

Run the complete offline suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider
```

Tests block network access, use synthetic photos and fake model replies, and do
not initialize Azure credentials. See [image-testing notes](../LESSONS.md#2-how-the-tests-check-images)
for how the pixel checks work.
