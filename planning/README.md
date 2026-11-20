# Planning and Implementation History

This is the living index of project direction and planning records.
The [project README](../README.md) is the user entry point; `docs` contains
current usage and contract documentation. Numbered records preserve how the
plans evolved, not competing current specifications.

## Current status

The deterministic local engine uses **layout format 3**. The optional
metadata-only agent supports natural-language proposals and iteration, with
saved replay evidence and offline assessment. See the
[CLI guide](../docs/cli-guide.md) and [layout field guide](../docs/layout-format.md)
for current behavior and contracts.

[008](008-project-lifecycle-and-interactive-iteration.md) is complete and closed;
see [008 results](008_results.md) for evidence and limitations. Records 005,
006, and the 008 smoke-check allowance are closed, not permission for more calls.
Scripted success is not user sign-off.
[007](007-image-understanding-and-interactive-design.md) remains
exploratory; vision, UI, and cloud hosting are not authorized by these records.
[009](009-user-led-natural-language-trial.md) is complete and closed as a learning
iteration; see [009 results](009_results.md).
[010](010-grounded-interpretation-and-human-trials.md) proposes grounded
interpretation, compact memory/navigation and timeout recovery with continued
human-led trials. [010a](010a-grounded-photo-references.md) is implemented and
verified offline, with a separately authorized live replay sanity follow-up;
see [010a results](010a_results.md). Later stages and further live evaluation
need separate approval.
The blueprint's broader Phase 1 is not complete.

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
| [005: Model-connected layouts](005-model-connected-layouts.md) | Closed implementation/evaluation record. See the [checkpoint A handoff](005-model-connected-layouts.md#authorized-six-round-follow-up-handoff); checkpoint B remains unstarted and unapproved. | New planning record. |
| [006: Simplification and repeatability](006-simplification-and-repeatability.md) | Closed revised pass: swap fix and prompt simplification. See [006 results](006_results.md) for replay evidence and limitations. | New planning record. |
| [007: Vision for photos and collage feedback](007-image-understanding-and-interactive-design.md) | Exploratory vision ideas: preview understanding plus human feedback, photo descriptions and subjects; colour/contrast analysis lower priority. No implementation authorized. | New discussion record. |
| [008: Project lifecycle and interactive iteration](008-project-lifecycle-and-interactive-iteration.md) | Complete and closed. See [008 results](008_results.md) for implementation and verification evidence. | New planning record. |
| [009: User-led natural-language trial](009-user-led-natural-language-trial.md) | Complete and closed as a learning iteration; see [009 results](009_results.md). Follow-up proposed in 010. | New planning record. |
| [010: Grounded interpretation and continued human trials](010-grounded-interpretation-and-human-trials.md) | Three-stage umbrella; 010a verified with live sanity follow-up, later stages and further live evaluation await approval. | New planning record. |
| [010a: Grounded photo references](010a-grounded-photo-references.md) | Implemented and closed with live sanity follow-up; see [010a results](010a_results.md). | First 010 stage. |

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
| Phase 1 included model-generated layouts and durable conversations. | Offline foundation, durable conversations, and fixed checkpoint A layout/refinement/acceptance cases now pass. User-led trials have taken place; reliability improvements and subjective sign-off remain outstanding. |
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

Close an implemented brief with its final status and a link to a separate
results record for evidence, outputs, limitations and budget accounting, then
retain it as a snapshot. Older records may contain their execution history inline.
Later phases update the
current guides and this index rather than rewriting earlier plans to match
new behavior. Neither an unapproved outline nor a previous phase's unused
allowance grants permission to start the next phase.
