# 010g: User-led natural-language trial

**Status:** Human-led trial 03 stopped for review; see [observations](010g_results.md).
No trial run by Copilot.
Follow-up to [010f results](010f_results.md), using high interpretation and low
generation. This record is intended for a separate commit from 010d-f.

## Start

In PowerShell at the repository root, create a fresh project **once**, then
start chat on a **1200x1800 (2:3)** canvas:

```powershell
$project = "p010g-human-03"

.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 create --project $project --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg

.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 chat --project $project --canvas 1200 1800 --live --generation-reasoning low --interpretation-reasoning high
```

The canvas is established when chat first starts, not by `create`.
Photo numbers: **1 Bridge, 2 breakfast, 3 London Eye, 4 bookshop**.
For another independent trial, change `$project` to `p010g-human-04`, then
`p010g-human-05`, and so on. Never recreate or overwrite an existing project.

## Explore and resume

Type collage requests and clarification answers at the terminal's `You:` prompt.
Previews open automatically; `/show P003` reopens a saved preview without a model
call or baseline change. No acceptance command is needed to keep iterating.
Use `/quit` to pause. Resume without recreating the project or resetting its
canvas:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 chat --project p010g-human-03 --live --generation-reasoning low --interpretation-reasoning high
```

Use the actual project name when resuming later runs.

## Trial boundaries

The user controls prompts, continuation and stopping; there is no fixed
trial-wide call budget. Existing per-message call/token/time guards and usage
recording remain in force. This is human-led exploration, not an unattended
replay, reasoning comparison or authorization for Copilot-initiated live calls.

Send observations **to Copilot here**, not as observer commentary to the collage
model. Record the project/proposal IDs, visible results, delays, corrections and
failures; mark Copilot-suggested prompts as assisted. Keep the reasoning settings
fixed within a run. Do not silently repair outputs or tune implementation during
the trial; fixes require separate agreement. Preserve original photos and prior
evidence. User satisfaction, not scripted success, determines trial feedback.
