# Planning and Implementation History

This is the living index of project direction and planning records.
The [project README](../README.md) is the user entry point; `docs` contains
current usage and contract documentation. Numbered records preserve how the
plans evolved, not competing current specifications.

## Current status

The offline foundation, subsequent layout capabilities, and engine refactoring
are implemented. The deterministic engine now uses **format 3**, with normalized
`center_x`/`center_y` anchors for resizing and rotation. The local Python CLI imports photos, validates and
renders editable recipes, and persists accepted versions for later rendering.
See the [Quick start](../README.md#quick-start),
[CLI guide](../docs/cli-guide.md), [layout field guide](../docs/layout-format.md),
and generated [JSON Schema](../docs/layout.schema.json) for current behavior.
Formats 1 and 2 are unsupported untouched archives, not migrated or loaded.
The agent prompt and context now use authored centres directly, with offline
coverage. Live requests remain paused pending user review of the revised prompt.
The checkpoint A results below describe
the preceding format 2 implementation, not a format 3 agent evaluation.

The optional model-connected terminal and durable proposal workflow from
[record 005](005-model-connected-layouts.md) are implemented with offline
coverage. **Checkpoint A now passes all four fixed live cases and exact
acceptance**, including shrinking photo 2 with zero centre drift. The separately
authorized follow-up used 4/6 meaningful development rounds and 17/50 fresh
requests, then halted after success. Numeric containment feedback, the bounded
three-correction loop, explicit pixel-centre context, and high reasoning effort
are implemented. This is trial-ready under the scripted checks, not a broader
reliability claim or the user's final sign-off. Checkpoint B still needs separate
authorization. See the [latest handoff](005-model-connected-layouts.md#authorized-six-round-follow-up-handoff).
The earlier 6/6-cycle result, three-attempt allowance, excluded diagnostics, and
all failed evaluation reports remain preserved; no old counts were refunded.
Record 005 is now closed as a historical implementation/evaluation record,
not an active work plan. This does not signify user acceptance, stabilized
code, or commit readiness: staging captures progress pending further work.
No successor plan has been created; checkpoint B remains unstarted.
Completing the offline foundation does not complete the blueprint's broader Phase 1.
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
| [005: Model-connected layouts](005-model-connected-layouts.md) | Closed historical implementation/evaluation record. Checkpoint A scripted checks and exact acceptance passed: 4/6 follow-up rounds, 17/50 fresh requests. Not user sign-off or commit readiness; checkpoint B unstarted and unapproved. | New planning record. |

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
| One master layout JSON with element IDs, `source_image_id`, `src`, `z_index`, and reserved `crop_pan`. | Format 3 recipes use centre coordinates, stable `photo_id`, back-to-front `layers`, explicit whole/cover modes, and cover-only `crop`. Saved snapshots separate authored `recipe` from derived `geometry`; asset paths belong to project metadata. |
| Independently shaped frames and pan/zoom waited for a future graphical UI. | Cover frames and pan/zoom already work through JSON recipes. Graphical controls remain future work; outside borders and rounded corners are also implemented. |
| Image-background fitting was unresolved, and the draft used `expand=True` for rotation. | An ordinary lowest photo layer supplies an image background. Tilt uses centre-preserving rotation and validated sampled footprints; angles are -10 to +10 degrees, not the draft schema's -15 to +15. |
| Phase 1 included model-generated layouts and durable conversations. | Offline foundation, durable conversations, and fixed checkpoint A layout/refinement/acceptance cases now pass. The user-led trial and subjective sign-off remain outstanding. |
| Captions, shadows, UI, and authenticated cloud deployment were envisioned. | These remain unimplemented; historical model names, hosting details, and cost estimates are not verified current selections or prices. |

Format 1 and 2 saved projects remain untouched archives, not loadable or migrated by
the current CLI. Their PNGs remain viewable. Current reproduction instructions
use a fresh data root and the converted example recipes.

## Retained direction

The product goal remains natural-language layout creation and refinement
without regenerating source photos. One metadata-only Microsoft Agent Framework
for Python agent calling a Microsoft Foundry model is the intended experiment;
ordinary code retains validation, geometry, rendering, and project persistence.
Checkpoint A uses the existing `gpt-5.4-mini` deployment; native schema transport
is verified, but model-generated geometry still needs a separately bounded follow-up.

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
