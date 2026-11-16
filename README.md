# AI Collage Builder

Build photo collages from explicit, editable layouts. The longer-term goal is
to describe a layout in natural language and refine it conversationally, while
keeping geometry, validation, and rendering deterministic.

**Available today:** a local Python CLI that imports JPEG/PNG photos, renders
JSON layouts to PNG, and keeps accepted layout versions. It preserves whole
photos without cropping or stretching, supports different canvas aspect ratios,
solid backgrounds, and overlapping images with explicit stacking.

The collage application runs offline without credentials or model calls.
Natural-language design, a graphical UI, and Azure hosting are planned, not
implemented. Separate Foundry connectivity experiments are not part of the
collage workflow.

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

## Editable recipes and saved results

Files under `examples` are **input recipes**: edit their canvas, photo positions,
widths, and stacking, then run `apply-layout` to try the design. Photo numbers
refer to the project's import order, not image content or stacking order.

Files such as `layouts\v0001.json` under a project's working directory are
**saved snapshots**. The engine adds calculated heights, pixel boxes, and a
revision number, and accepts a version only after validation and rendering
succeed. Editing the input does not change an existing version; applying it
again creates the next version. Later renders use the saved snapshot, not the
input file.

Keep editing the recipe, not the generated snapshot. See the
[CLI guide](docs/cli-guide.md#input-layouts-and-saved-versions) for the full
relationship, storage paths, and versioning behavior.

## Documentation

| Document | Purpose |
|---|---|
| [Local CLI guide](docs/cli-guide.md) | Setup, commands, examples, layout rules, limits, storage, and tests |
| [Project blueprint](ai_collage_builder_project_blueprint.md) | Product direction, proposed architecture, and roadmap |
| [Phase 1 implementation plan](phase_1_implementation_plan.md) | Agreed scope, guardrails, and implementation records |
| [Foundry experiments](temp-foundry-test/README.md) | Separate keyless model-connectivity examples; running them makes paid service calls |

This README is the evolving project entry point. User-facing instructions live
in the CLI guide; phase-specific decisions and execution records stay in the
implementation plans.
