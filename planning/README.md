# Planning and Implementation History

This is the living index of project direction and planning records.
The [project README](../README.md) is the user entry point; `docs` contains
current usage and contract documentation. Numbered records preserve how the
plans evolved, not competing current specifications.

## Current status

The offline foundation, subsequent layout capabilities, and format 2 engine
refactoring are implemented. The local Python CLI imports photos, validates and
renders editable recipes, and persists accepted versions for later rendering.
See the [Quick start](../README.md#quick-start),
[CLI guide](../docs/cli-guide.md), [layout field guide](../docs/layout-format.md),
and generated [JSON Schema](../docs/layout.schema.json) for current behavior.

Application LLM integration and conversational refinement are not implemented.
The model-connected experiment outlined as Step 2 in record 002 still requires
a separately approved brief and paid-call budget. Completing the offline
foundation does not complete the original blueprint's broader Phase 1.
Separate [Foundry experiments](../temp-foundry-test/README.md) are reference
work, not application integration; running them makes paid service calls.

## Planning records

Numbering is reading order, not phase numbering. These records are snapshots
as retained here: some already include execution notes and later clarifications,
and record 003 spans several feature increments.

| Record | Status and role | Original location |
|---|---|---|
| [001: Project blueprint](001-project-blueprint.md) | Historical product vision and target architecture; implementation details and roadmap partly superseded. | `ai_collage_builder_project_blueprint.md` |
| [002: Phase 1 offline foundation](002-phase-1-offline-foundation.md) | Step 1 completed; Step 2 outlined but unapproved. Preserves the original format 1 contract and guardrails. | `phase_1_implementation_plan.md` |
| [003: Layout evolution](003-layout-evolution.md) | Implemented borders, cover framing, rounded corners, and tilt, plus format 2 reconciliation and visual-demo decisions. | `docs\layout-decisions.md` |
| [004: Engine refactoring](004-engine-refactoring.md) | Completed format 2 brief, verification, example-equivalence evidence, reviewer outcomes, and retry accounting. | `docs\engine-refactoring-spec.md` |

Historical status statements, instructions, and budgets apply only to their
recorded increments. They do not authorize new implementation, service calls,
or additional retries. Historical commands and JSON examples are not current
usage instructions; use the current guides linked above.

## Blueprint reconciliation

Keep the original blueprint intact as a record of intent. The important changes
since that proposal are:

| Original proposal or assumption | Current position |
|---|---|
| Pillow was a proposed renderer. | Pillow is implemented, with strict Pydantic contracts and deterministic geometry/rendering. |
| One master layout JSON with element IDs, `source_image_id`, `src`, `z_index`, and reserved `crop_pan`. | Format 2 recipes use stable `photo_id`, back-to-front `layers`, explicit whole/cover modes, and cover-only `crop`. Saved snapshots separate authored `recipe` from derived `geometry`; asset paths belong to project metadata. |
| Independently shaped frames and pan/zoom waited for a future graphical UI. | Cover frames and pan/zoom already work through JSON recipes. Graphical controls remain future work; outside borders and rounded corners are also implemented. |
| Image-background fitting was unresolved, and the draft used `expand=True` for rotation. | An ordinary lowest photo layer supplies an image background. Tilt uses centre-preserving rotation and validated sampled footprints; angles are -10 to +10 degrees, not the draft schema's -15 to +15. |
| Phase 1 included model-generated layouts and durable conversations. | Only its offline foundation and subsequent engine increments are complete. No application model calls or conversation persistence have been added. |
| Captions, shadows, UI, and authenticated cloud deployment were envisioned. | These remain unimplemented; historical model names, hosting details, and cost estimates are not verified current selections or prices. |

Format 1 saved projects remain untouched archives, not loadable or migrated by
the current CLI. Their PNGs remain viewable. Current reproduction instructions
use a fresh data root and the converted example recipes.

## Retained direction

The product goal remains natural-language layout creation and refinement
without regenerating source photos. One metadata-only Microsoft Agent Framework
for Python agent calling a Microsoft Foundry model is the intended experiment;
ordinary code retains validation, geometry, rendering, and project persistence.
Final model selection and supported structured-output behavior need confirmation
for that experiment.

React + TypeScript + Vite remains the intended UI, with backend-rendered
previews. Azure Functions and private Blob Storage remain the target deployment,
initially with backend-mediated image transfers. These are directions, not
implemented components. Authentication and per-user authorization are gates
before sharing a cloud deployment; the local development-owner namespace is
not authentication.

## Future phases

Add a new numbered brief for each substantial phase, keeping its path stable
through proposal, approval, implementation, and completion. Each brief should
state its status, scope and exclusions, prerequisites and decisions, acceptance
criteria, guardrails, retry/service budgets, and links to relevant earlier
records and current documentation. Approval boundaries must be explicit.

Close an implemented brief with its execution record, results, limitations,
and budget accounting, then retain it as a snapshot. Later phases update the
current guides and this index rather than rewriting earlier plans to match
new behavior. Neither an unapproved outline nor a previous phase's unused
allowance grants permission to start the next phase.
