# Local CLI Guide

The current offline engine uses **layout/project format 3**. It imports original
JPEG/PNG photos and deterministically renders editable JSON recipes, without
credentials or model calls. See the [layout field guide](layout-format.md) for
syntax and the [README](../README.md) for the project story.

## Setup (PowerShell, Python 3.12+)

Run from the repository root:

```powershell
python -m venv .\.venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
```

Activation is unnecessary. If `python` is not on PATH, use your installed Python
executable's full path for environment creation. Runtime dependencies are Pillow
and Pydantic; `requirements-dev.txt` adds pytest. Installation downloads packages;
the deterministic engine and routine tests run offline. The root environment is separate from
the `temp-foundry-test` experiments, which must not run as part of this workflow.

## Fresh projects and old archives

Format 1 and 2 projects and saved snapshots are **untouched archives**, not migrated
automatically. Their PNGs remain viewable, but the new CLI rejects their format.
Do not edit their metadata or apply new recipes to them. New-format equivalents
of all seven curated recipes retain their descriptive filenames in `examples`.

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

The first recipe makes a 900x1600 (9:16) white canvas with four complete 396x528
photos at (36,224), (468,224), (36,848), and (468,848). Import order assigns
Bridge 1, breakfast 2, London Eye 3, bookshop 4. Photo numbers are identifiers,
not stacking positions or content recognition.

`create` fails if the project exists. Choose a fresh name consistently rather
than deleting a previous project. To try the second 900x1200 (3:4) arrangement:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 apply-layout --project portrait-demo --layout .\examples\portrait_3x4.json
```

The same whole photos sit at (36,48), (468,48), (36,624), and (468,624). Applying
this after the first recipe accepts version 2, leaving version 1 untouched.
Canvas aspect ratio and positions come from the JSON, not separate CLI flags.

## Commands and paths

| Command | Behavior |
|---|---|
| `create --project ID --images FILE...` | Validate/import 2-6 JPEG/PNG photos in argument order; fail if the project exists. No layout is generated. |
| `inspect --project ID` | Show photo IDs/dimensions/aspect ratios, accepted versions, current version, and paths. Works before the first layout. |
| `apply-layout --project ID --layout FILE` | Validate recipe/current state, resolve geometry, and render before accepting the next immutable snapshot and updating the current pointer. |
| `render --project ID [--version N]` | Reopen and rerender an accepted new-format version, defaulting to current. No new version or current-pointer change. |

Results are JSON on stdout; errors use stderr and nonzero exit status.
Photo records now use `photo_id`, replacing format 1's `source_image_id`.
`apply-layout` still returns `version`, `layout_path`, and `render_path`.
Saved snapshots now separate `recipe` from `geometry`.

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
Positions in authored recipes are `box.center_x` and `box.center_y`,
normalized independently on the canvas axes. Resizing keeps that centre fixed.
Derived render boxes still use top-left integer pixel coordinates.

### Saved snapshots and schema maintenance

An accepted snapshot has its own `schema_version: 3` and positive `version`,
one canonical validated input under `recipe`, and separate `geometry` ordered
like the recipe's layers. Geometry contains the `photo_id`, normalized
resolved frame, outer/inner pixel boxes, optional source window, and optional
rotated footprint. Derived fields are required even when their value is null.
The derived `geometry.box_normalized.x`/`y` are the continuous top-left
calculated from the authored centre and continuous size. Derived pixel boxes
also use top-left coordinates for rendering. Neither is an alternative authored
position or a value to feed back as `center_x`/`center_y`.

The engine recomputes geometry when reopening a snapshot and rejects
inconsistencies before rendering or accepting a later version. Edit the
original recipe and apply it again instead of changing a saved snapshot.
Format 1 and 2 recipes, projects, and snapshots are unsupported. Existing project
data remains an untouched archive; previously rendered PNGs remain viewable. No
migration or legacy loader is provided.

The generated schema is checked against the models in the tests. To regenerate
it after intentionally changing a contract, run from the repository root:

```powershell
.\.venv\Scripts\python.exe -c "import json; from pathlib import Path; from ai_collage.models import InputLayout; Path(r'docs\layout.schema.json').write_text(json.dumps(InputLayout.model_json_schema(), indent=2) + '\n', encoding='utf-8')"
```

## Conversational proposals (optional)

Natural-language requests use two stages through the same provider/model:
interpret the requested action/source and photo references, then generate a
recipe only when needed.
Ordinary edits use the selected working proposal. Rejecting a composition can
request a fresh arrangement; rejecting a targeted edit can retry its original
task/source. "Go back to the first one" selects its exact preserved PNG without
generation or acceptance; "go back ... and make photo 2 smaller" edits that
source directly. Essential ambiguity produces an interpretation-stage question.
All lifecycle branches have offline coverage. The separately authorized
[008 landscape smoke check](../planning/008_results.md#authorized-live-landscape-smoke-check)
also completed initial composition and three targeted edits with the live model;
later user-led observations are recorded in [009 results](../planning/009_results.md).

Photo references use stable numbers, explicit user-taught names, and clear
recent conversational references such as "make it bigger" after discussing one
photo. The model cannot see image contents; positional descriptions such as
"top-right" and untaught content synonyms are not resolved in this increment.
Qualitative amounts such as "a bit right" do not require exact distances.

Teach a name with "photo 2 is breakfast", or answer "2" when asked which photo
is breakfast. Naming alone produces a **Remembered** acknowledgement, without
generation, a new proposal or a baseline change; ordinary text still requires
`--live` and uses interpretation. Naming plus an edit can do both. Names are
project-local and survive compaction, restarts and returns to older proposals.
They compare case-insensitively with normalized whitespace; one photo may have
several taught names. Unknown names require clarification, not guessed synonyms.
Conflicting assignments require confirmation unless explicitly corrected, e.g.
"breakfast is actually photo 3, not photo 2"; other names do not move with it.
An unresolved target holds the whole edit until clarification is complete.
Explicit name facts are saved independently of subsequent generation success.

Model context keeps the original request, current layout/source, current task,
and up to three recent user-message exchanges, not the full event log. Older
wording is not maintained as standing instructions; its layout effects remain
in the current recipe. Full history and proposals stay on disk. Explicit older
proposal IDs and ordinals can retrieve preserved sources/tasks; unclear older
descriptions may require clarification. No model-generated memory summary or
extra compaction call is used. User-established photo names, their evidence,
recent validated reference evidence and resolved generation references are
separate essential context, not disposable rolling history. If essential input
cannot fit, the request fails explicitly rather than silently dropping names.

Conversation, proposal, event, acceptance-intent, replay and assessment records
now use **record version 3**.
Layout/project format remains **3**; sequence definitions, preferences and
request accounting retain their own unchanged versions. Old conversation/replay
records are untouched archives: use fresh projects, not a legacy loader or
migration. Existing supported deterministic recipes/snapshots remain usable.

**Format 3 prompt/context adaptation is covered offline.** The agent now edits
authored centres directly instead of calculating resize position offsets.
A single authorized four-message format 3 replay completed without corrections
or acceptance. This is exploratory evidence, not a repeated reliability assessment.
Use fresh format 3 projects; do not resume archived format 2 projects.

Live model requests require explicit authorization, not a provisioned allowance. See
[record 005's handoff](../planning/005-model-connected-layouts.md#authorized-six-round-follow-up-handoff)
for checkpoint status, evaluation evidence, and approval boundaries.

Engine-only users need no optional dependencies. To install the agent into the
root application environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-agent.txt
```

The verified offline combination is Agent Framework OpenAI provider 1.18.2,
OpenAI SDK 2.54.0, and HTTPX 0.28.1. The manifest pins the provider and constrains
the compatible SDK major version. Do not reuse or run the separate
`temp-foundry-test` environment/scripts.

Interpretation instructions live in `ai_collage\prompts\request-intent.md`.
Generation loads `ai_collage\prompts\layout-agent.md` plus the shared
[layout field guide](layout-format.md); questions and lifecycle actions are
not generation responses. Controls, resolved source/task, history and validation
feedback are supplied separately. Fresh layouts retain the previous recipe as
a reference to avoid repeating, not an editing baseline.
To print both stages' instructions offline from the repository root, without
credentials or model calls:

```powershell
.\.venv\Scripts\python.exe -c "from ai_collage.agent_provider import instruction_bundle; print(instruction_bundle())"
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

Conversation state, bounded event files, and immutable `proposals\P001`
artifacts live under the project's `conversation` directory. Per-request usage
records are saved automatically in `conversation\requests\attempt-0001.json`,
etc. They are accounting, not an allowance or a cumulative usage limit.
All experiment runtime files remain ignored by Git.

### Repeatable prompt sequences

`python -m ai_collage.replay` runs repository-owned JSON sequences through the
same conversation/provider operations as chat. It captures results, not
subjective quality or benchmark passes, and **never accepts a proposal**.
It is the single sequence-execution path; the old fixed evaluator and its live
entry point have been removed. Mechanical assessment now reads saved replays
offline, separately from execution and acceptance.

The supplied sequences are:

- `examples\sequences\01_dark_portrait_adjustments.json`: the original four messages, with
  reopening before straightening; its mechanical checks are an explicit assessment profile.
- `examples\sequences\02_landscape_staggered_adjustments.json`: an exploratory landscape
  composition and three provisional follow-ups, editable before they are attempted.

A sequence contains `record_version: 1`, a `name`, ordered `images` paths
relative to the sequence file, `canvas` width/height, and `messages`.
Each message has a unique `name`, `prompt`, and optional
`reopen_before: true`. Photo numbers follow image order. Canvas dimensions
are fixed for a replay; `canvas.cropping` defaults to false. Styling uses the
conversation's captured defaults.
The JSON `name` is a stable replay identity, not its filename. Renaming a
sequence file in the same directory does not reset or invalidate an existing replay.

Validate sequence structure and source-file availability/hashes **offline**,
without creating a project, opening credentials, or sending requests:

```powershell
.\.venv\Scripts\python.exe -m ai_collage.replay --sequence .\examples\sequences\02_landscape_staggered_adjustments.json --check
```

After separate live authorization, run **only the next message**:

```powershell
.\.venv\Scripts\python.exe -m ai_collage.replay --sequence .\examples\sequences\02_landscape_staggered_adjustments.json --data-dir .\.collage-data-v3 --project YOUR-FRESH-PROJECT
```

Repeat the same command with `--resume` to run the next message in that
project. Add `--remaining` only when authorized to run all remaining messages
without pausing after each proposal. A completed replay sends no further calls.
No `--run`, `--ledger-data-dir`, or allowance provisioning is needed. There are
at most four model calls per message, including validation corrections: a
four-message batch makes at most 16 calls, normally eight with the two-stage
flow. Interpretation gets at most two attempts; generation and its corrections
share the remaining four-call allowance. Every explicit retry
is a new bounded attempt at that message; accounting persists across invocations
without imposing a lifetime cap.

Resume verifies the source photos, canvas, instructions and
conversation state. Previously attempted messages cannot change. Unattempted
messages may be edited, appended or removed; each execution preserves its
own complete sequence snapshot. Manual chat/control/acceptance changes cause
resume to stop rather than silently adopt a different baseline.

Naming-only acknowledgements advance one scripted step without creating a
proposal, preview, source-relative layout difference or baseline change.
A question pauses without advancing the sequence or answering on your behalf.
After reviewing the question, supply a recorded supplemental answer:

```powershell
.\.venv\Scripts\python.exe -m ai_collage.replay --sequence .\examples\sequences\02_landscape_staggered_adjustments.json --data-dir .\.collage-data-v3 --project YOUR-REPLAY-PROJECT --resume --answer "Photo 2" --answer-origin user
```

Use `--answer-origin copilot` only for an answer actually authored by Copilot.
The answer, origin and preceding question execution are captured separately;
the original scripted message is not replaced. Each answer has a new four-call
attempt limit and consumes the same optional outer allowance. At most two
clarification-answer turns are allowed per scripted step. `--remaining` may
continue subsequent scripted messages after successful completion. The runner
never invents an answer. Manual chat/control changes still block replay resume;
do not bypass that check to answer a question.
A service failure stops immediately;
an explicitly authorized retry requires `--resume --retry`. The existing
bounded validation-correction loop still applies within a message. An
interrupted, pending execution requires evidence inspection, not blind retry.
Retrying a failed answer preserves its recorded answer and origin. Unsupported
old replay versions cannot resume; their evidence remains unchanged.

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

The report records the next-message cursor and every execution, including
failures/retries/questions. Per-execution results contain proposal/preview
paths, resolved source/task, previous working baseline, authored-field differences
from the actual edit source, each stage's request context path,
attempt/correction counts, cumulative project request usage before/after,
and elapsed stage time including validation/rendering. Raw model responses
remain in the normal conversation events; individual request usage remains
in the project's request records. Selection is a completed step, not a new
proposal; it has no authored changes or generation call. Both prompts are
captured in the instruction bundle and checked on resume.
No photos or local paths are added to the
model context by the runner. Existing executions and proposal files are
preserved when resuming.

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

The assessment command needs no historical ledger, credentials, original input
sequence file, or original source-photo paths. It reads the current-format saved
replay, captured contexts, local request/event records, imported photos and
immutable proposals without starting/recovering a conversation,
rendering new previews, accepting anything, or making model requests.

```powershell
# Either sequence: verify saved evidence only.
.\.venv\Scripts\python.exe -m ai_collage.assess --data-dir .\.collage-data-v3 --project YOUR-REPLAY-PROJECT

# Dark portrait sequence: also check the specific historical expectations.
.\.venv\Scripts\python.exe -m ai_collage.assess --data-dir .\.collage-data-v3 --project YOUR-REPLAY-PROJECT --profile dark-portrait-adjustments
```

The default `integrity` profile checks source/instruction hashes, proposal
identity/actual source relationships, schema/controls/recomputed geometry, saved recipe/PNG
digests, audited name-state updates, naming acknowledgements, per-execution
result consistency and sequence completion. It does
**not** check whether a move, swap or styling change followed the user's intent.

The `dark-portrait-adjustments` profile additionally preserves the old fixed
checks: dark-neutral background, photo 2 smaller than the others, subtle
white or near-white borders (each RGB channel at least 240), rounding/tilt,
an in-place shrink, border removal, straightening, and no unrelated authored
changes. These are profile-specific rules, not universal composition
requirements. It requires the four corresponding
named messages on a 1200x1800 four-photo replay, with reopening before
straightening; it is not a landscape profile.
No prompts or live execution are duplicated in the assessor.

Each invocation appends `replay\assessments\0001.json`, then `0002.json`, etc.,
with the assessed replay report's hash, profile, completion flag and per-execution
results. It never rewrites the replay or an earlier assessment. Exit code 0
means a complete replay whose applicable mechanical checks passed; failures
or incomplete sequences return 1. Questions, interruptions and service failures
have no proposal to assess and remain visible as `not_assessed`. A subsequent
explicit retry may yield an eventual pass; that is not a first-attempt success
claim, and the original failure remains recorded. Recorded clarification answers
can continue a pending step; the assessment reports `clarification_assisted: true`
rather than presenting that as an uninterrupted scripted success. Stage order,
call accounting and captured source-relative changes are checked as evidence.

Acceptance fidelity remains covered by offline conversation tests, not by an
assessment that changes the project. Composition and subjective request quality
are reviewed separately by the user or Copilot; there is no automated AI judge
or subjective scoring system. Historical evaluation reports remain untouched.

### Future authorized live use

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
allowance. Old experiment ledgers remain untouched historical evidence, not
active limits, and this simplification grants no new service-call authorization.

The transport durably records each actual outbound inference before dispatch.
The per-request limits are 50,000 input
tokens, 25,000 output tokens including reasoning, and 120 seconds. Input
preflight uses serialized UTF-8 bytes plus a reserve as a conservative token
bound; actual provider usage is recorded separately. If needed, it removes
the oldest recent exchange first until the complete outgoing request fits.
It never cuts the original/current request, required source/task, pending
question, or latest correction candidate/feedback. If essential input still
exceeds the bound, a local error reports the measured bound and limit before
dispatch, without using a call allowance or changing the baseline. Replay
captures retain the effective context after size trimming. SDK/transport retries,
tools, hosted history, response storage, and unexpected extra inference are
disabled/rejected. High reasoning effort is explicitly requested and checked
on the outbound request; reasoning tokens share the 25,000-token output cap.
Storage-off is not a promise about all service logging.

There are at most three validation-guided corrections for completed invalid
JSON or hard layout/control violations: four total attempts per user request,
stopping earlier on success, a per-request limit or an error. Numeric containment
feedback includes current outer/rotated/sampled bounds, pixel overshoot, and
conservative normalized `center_x`/`center_y` placement ranges under
`safe_box_center_normalized`. It never changes the proposed recipe automatically.
Context includes the valid baseline's authored centre coordinates and derived
geometry for size/clearance checks. Resizing in place keeps those authored
centres exactly; rounded render boxes are not replacement position anchors.
A valid clarification waits for the real
user. Service/authentication/incomplete/timeout/render-I/O failures do not
trigger model correction. Photos, filenames, local paths, and credentials are
not automatically sent: the agent receives photo numbers/dimensions, recipes,
defaults, controls, and actual conversation text. User-entered text is not
automatically scrubbed of sensitive information.

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

## Verification

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q .\tests --ignore=.\tests\test_agent.py --ignore=.\tests\test_replay.py --ignore=.\tests\test_assess.py
```

Deterministic tests are grouped into contracts, geometry, centre anchoring,
rendering, storage, CLI, and curated examples. This includes integration checks
and CLI subprocesses, not only unit tests. Optional mocked agent tests live
separately in `tests\test_agent.py`, `tests\test_replay.py` and
`tests\test_assess.py` and are excluded above. Run those separately
when working on the agent:

```powershell
.\.venv\Scripts\python.exe -m pytest -q .\tests\test_agent.py .\tests\test_replay.py .\tests\test_assess.py
```

These agent tests use fake replies and mocked HTTP; they do not call a live
model or initialize Azure credentials.
Shared fixtures/helpers remain small. Synthetic photo tests check
known pixels and shapes; they do not depend on the personal photos in `photos`.
Example tests use synthetic 3:4 sources matching the recipes' required aspect
ratios. Real-photo before/after comparisons are separate phase evidence.
Tests block network access; CLI subprocess tests also remove Azure/OpenAI
environment variables. There is no model-based aesthetic judgment.
