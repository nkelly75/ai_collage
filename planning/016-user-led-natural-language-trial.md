# 016: Human-led trial 06

**Status:** The user ran `p15-human-06` through P008, then paused for a separately
approved offline evidence-handoff repair; see [observations and repair](016_results.md).
The trial is not closed or an Autopilot assignment. This guide follows the committed
[015 restructuring](015_results.md) and [01-05 replays](015_replay_results.md).

## Create and start

The PowerShell syntax is unchanged: create/chat still use `python -m ai_collage`.
From the repository root, create the fresh project **once**, then start live
chat on a **1200x1800 (2:3)** canvas:

```powershell
$project = "p15-human-06"

.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 create --project $project --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
if ($LASTEXITCODE -ne 0) { throw "Project creation failed; stop here." }

.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 chat --project $project --canvas 1200 1800 --live --generation-reasoning low --interpretation-reasoning high
```

Canvas dimensions are set by chat, not `create`. Photo numbers are
**1 Bridge, 2 breakfast, 3 London Eye, 4 bookshop**; the model cannot see their
contents. Previews open automatically. If the project already exists, resume
it intentionally or choose a fresh name; do not recreate or overwrite it.

## Three suggested starter prompts

Type these at chat's `You:` prompt, one at a time, inspecting each result:

1. Make a collage using all four photos, with a navy background and thin white borders. Make photo 2 smaller than the others.
2. Make photo 2 a bit smaller. Keep it in the same spot and leave the rest alone.
3. Remove the borders. Leave everything else alone.

These are Copilot-suggested prompts, not a required script. Afterward, react
naturally to the results and answer any genuine clarifications yourself.

## Pause, resume and boundaries

Use `/status` for usage/state, `/show P001` to reopen a saved preview, and
`/quit` to pause. No acceptance is needed to keep iterating. Resume without
running `create` again:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 chat --project p15-human-06 --live --generation-reasoning low --interpretation-reasoning high
```

After a code repair, quit the existing chat process and restart it with the
resume command to load the updated implementation. Do not recreate the project.

The user controls continuation and stopping; there is no fixed trial-wide call
allowance. Existing per-message call/token/deadline guards and usage recording
remain in force. Keep high interpretation / low generation throughout.
This guide authorizes no Copilot-initiated live calls, automated answers,
replays, fixes, installs or Git writes. Preserve original photos and prior data.

Send observations to Copilot here, not as observer commentary to the collage
model: include project/proposal IDs, exact requests and what worked or failed.
Do not silently repair outputs or tune implementation during the trial.
Human feedback, explicit application acceptance and approval to merge to `main`
remain separate decisions.
