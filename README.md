# AI Collage Builder

Build photo collages from explicit, editable layouts. The longer-term goal is
to describe a layout in natural language and refine it conversationally, while
keeping geometry, validation, and rendering deterministic.

**Available today:** a local Python CLI that imports JPEG/PNG photos, renders
JSON layouts to PNG, and keeps accepted layout versions. Preserve whole photos,
or opt into fixed rectangular frames with crop-to-fill, pan, and 1x-4x zoom.
Both modes avoid stretching and support different canvas aspect ratios, solid
backgrounds, optional outside photo borders, and overlapping images with
explicit stacking. Rounded corners are not implemented yet.

The collage application runs offline without credentials or model calls.
Natural-language design, a graphical UI, and Azure hosting are planned, not
implemented. Separate Foundry connectivity experiments are not part of the
collage workflow.

## Where the idea came from

The project began with a conversation between the author and their daughter,
Emma. She had made a collage in the Android app PicCollage and wanted to improve
it. Attempts to adjust the result through ChatGPT and Copilot made it worse
rather than delivering the changes she wanted.

That experience inspired the separation at the heart of this project: let an
LLM propose creative layouts and adjustments, but let deterministic code
position, resize, and composite the original photos instead of regenerating
them. [Emma's original collage](photos/em_manual_collage.jpg) is a useful
reference for exploring which layout capabilities the project needs.

## Quick start

Use Python 3.12+ and PowerShell from the repository root:

```powershell
python -m venv .\.venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe -m ai_collage create --project my-collage --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
.\.venv\Scripts\python.exe -m ai_collage apply-layout --project my-collage --layout .\examples\portrait_3x4.json
Invoke-Item .\.collage-data\users\local-dev\projects\my-collage\renders\v0001.png
```

Activation is not required. The commands create a new project and a **900x1200
(3:4)** collage using the supplied photos. If `my-collage` already exists,
choose another project name consistently. The original photos stay unchanged;
working copies and outputs live in the ignored `.collage-data` directory.
Dependency installation downloads packages; rendering itself is offline.

Use `examples\portrait_9x16.json` instead for a **900x1600 (9:16)** canvas.
Canvas dimensions and positions are defined in the JSON, not separate CLI
aspect-ratio flags.

For an asymmetric **1200x1800 (2:3)** composition with borders and a larger
foreground photo, see [Emma's layered example](docs/cli-guide.md#emmas-layered-23-example)
and its editable recipe, `examples\emma_2x3.json`.
The separate [framed variation](docs/cli-guide.md#emmas-framed-variation) uses
`examples\emma_framed_2x3.json` to adjust the bookshop and breakfast crops without
changing that whole-photo baseline.

## Editable recipes and saved results

Files under `examples` are **input recipes**: edit their canvas, photo positions,
widths, optional frames/framing, and stacking, then run `apply-layout` to try the
design. Photo numbers refer to the project's import order, not image content or
stacking order.

Files such as `layouts\v0001.json` under a project's working directory are
**saved snapshots**. The engine adds pixel boxes, derived whole-photo heights
or source crops, and a revision number. It accepts a version only after
validation and rendering succeed. Editing the input does not change an existing
version; applying it again creates the next version. Later renders use the
saved snapshot, not the input file.

Keep editing the recipe, not the generated snapshot. See the
[CLI guide](docs/cli-guide.md#input-layouts-and-saved-versions) for the full
relationship, storage paths, and versioning behavior.

## How the tests check images

The rendering tests create tiny temporary images in code, drawing known colours
and shapes on them. They pass these through the normal import, layout, and render
workflow, then inspect the resulting pixels. For example:

- Red, green, and blue bands reveal whether panning selects the left, middle,
  or right part of an image.
- A square drawn inside a wide image should remain square when rendered into a
  tall frame, rather than becoming stretched.
- Known border colours and transparent areas let tests check border thickness
  and which overlapping layer shows through.

Because the starting pictures are deliberately simple, the expected colours
and positions are known in advance. Checks can be exact where appropriate,
with small tolerances where resizing or JPEG compression blends pixels.
No AI judges whether the result looks right, and the tests run offline without
using your photos. Real-photo examples still help us judge the composition.

Other tests cover invalid layouts, saved versions, and failures that must leave
previous results intact. See the [CLI guide](docs/cli-guide.md#verification)
for instructions to run the tests.

## Documentation

| Document | Purpose |
|---|---|
| [Local CLI guide](docs/cli-guide.md) | Setup, commands, examples, layout rules, limits, storage, and tests |
| [Layout design decisions](docs/layout-decisions.md) | Discussed extensions, including outside borders and their layout-box semantics; implementation status is explicit |
| [Project blueprint](ai_collage_builder_project_blueprint.md) | Product direction, proposed architecture, and roadmap |
| [Phase 1 implementation plan](phase_1_implementation_plan.md) | Agreed scope, guardrails, and implementation records |
| [Foundry experiments](temp-foundry-test/README.md) | Separate keyless model-connectivity examples; running them makes paid service calls |

This README is the evolving project entry point. User-facing instructions live
in the CLI guide; phase-specific decisions and execution records stay in the
implementation plans.
