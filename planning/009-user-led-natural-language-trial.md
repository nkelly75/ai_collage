# 009: User-led natural-language trial

**Status:** Complete and closed as a learning iteration; see
[009 results](009_results.md) for outcomes, evidence and unresolved issues.
Bounded context and clearer limit errors are implemented and verified offline,
but natural-language reliability and user satisfaction need further work.
The proposed follow-up is
[010: Grounded interpretation and continued human trials](010-grounded-interpretation-and-human-trials.md).
Closing 009 is not product sign-off or authorization for further calls.

## Recorded trial workflow

The commands and workflow below describe the closed trials, not instructions
to start another run under 009. The user controlled continuation and stopping;
there was no fixed trial-wide call budget. Per-message limits, token/time
guards and usage recording remained in force.

### Start

In PowerShell at the repository root, create a fresh project **once**:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 create --project p009-human-01 --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
```

Photo numbers: **1 Bridge, 2 breakfast, 3 London Eye, 4 bookshop**.
If that project name exists, choose another in all commands below.

Start chat (this example uses a 16:9 landscape canvas; change dimensions if desired):

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 chat --project p009-human-01 --canvas 1600 900 --live
```

### Explore

1. Type your initial design request at the terminal's `You:` prompt.
2. Inspect the preview, then give natural-language feedback until you like the
   design or decide to stop. If asked a clarification, answer in the same terminal.
3. Later, ask Copilot here for ambiguous-message ideas and try those separately.
   Ambiguity need not produce a question when context makes the intent clear.

Previews **open automatically in Windows** after generation or restoration.
To reopen one, type `/show P003`, replacing `P003` with the printed proposal ID.
Viewing makes no model call and does not change your editing baseline.
No acceptance command is needed to keep iterating.

Type `/quit` to pause. Resume without recreating the project:

```powershell
.\.venv\Scripts\python.exe -m ai_collage --data-dir .\.collage-data-v3 chat --project p009-human-01 --live
```

### Observations

Collage requests went to the terminal; observations went **to Copilot**.
The [results](009_results.md) capture observations and follow-up issues.
Observer commentary was not forwarded to the collage model.

This was user-led exploration, not unattended replay or tuning. Vision, UI and
cloud hosting remained out of scope.
