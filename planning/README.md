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
[010](010-grounded-interpretation-and-human-trials.md) is **complete and closed
as a bounded improvement phase**: grounded names/references, compact task history
and reliable returns, timeout recovery, independent reasoning settings, and
friendlier clarification/error recovery with enlargement fitting. Generation
defaults **low**; interpretation remains **high**, with explicit overrides.

Implementation and evaluation evidence stays in the results records:
[010a](010a_results.md), [010b](010b_results.md), [010c](010c_results.md),
[010d](010d_results.md), [010e](010e_results.md),
[010e third-freeze follow-up](010e_third_freeze_results.md),
[010f](010f_results.md), [010h](010h_results.md) and the separately authorized
[010h replay follow-up](010h_replay_results.md). Those passes are closed;
earlier evidence remains unchanged.

[Trial 03](010g_results.md) exposed recovery problems.
[Human-led trial 04](010g_trial04_results.md) stopped for the phase handoff after
accepting P007 and continuing through P010. It demonstrated useful progress,
including clarification continuation and editing an older proposal, while
retaining evidence of naming friction and an unintended spatial edit.
A final approved prompt-only depth/position clarification has not been
live-retested. Further work needs separate approval; neither an accepted image
nor phase closure establishes general reliability. The blueprint's broader
Phase 1 is not complete.

[011: Interpretation and naming reassessment](011-interpretation-and-naming-reassessment.md)
is reviewed and closed; see [011 results](011_results.md).
The recommendation keeps separate interpretation and layout stages, with
task-local model-led binding and deliberately confirmed durable labels.
The selected direction was separately approved and implemented in 012;
the review itself did not authorize implementation or live evaluation.

[012: Model-led references and confirmed names](012-model-led-references-and-confirmed-names.md)
is **successfully completed and closed with the user's sign-off**.
One natural-language confirmation gate precedes durable teaching and any
associated edit; ordinary resolvable edits proceed directly.
See [012 results](012_results.md) for verification and the simplicity trade-off.
The [replay follow-up](012_replay_results.md) and
[return repair/retest](012_return_repair_results.md) retain their separate
outcomes and closed budgets. [Human-led trial 05 / phase closeout](012_trial05_results.md)
records the user's positive reliability/predictability feedback and acceptance
of the final compliment blip; see its [collage story](012_result_05.png).
This closes the bounded phase, not general reliability or broader Phase 1.
The user will handle the commit; further trials, refactoring and branch
integration are not initiated by this closeout.

[013: Branch correctness and security review](013-branch-correctness-and-security-review.md)
is **executed and closed**. It compared committed
`nkelly/plan-010` with `nkelly/llm-wip-1` as a traditional correctness/security
review, not another design reassessment. [013 results](013_results.md) record
one repaired/re-reviewed correctness defect and no confirmed security
vulnerabilities. The user subsequently committed and merged that work onto
`nkelly/llm-wip-1`; further work needs separate approval.

[014: Correctness and security review before main](014-main-readiness-review.md)
is **executed and closed**. It compared committed `nkelly/llm-wip-1` against
`main`; [014 results](014_results.md) record two surgically repaired/re-reviewed
correctness defects and no confirmed security vulnerabilities. The user committed
that work before 015. Mechanical package refactoring was excluded from 014
and completed separately in 015; no merge was performed as part of that review.

[015: Behaviour-preserving package restructuring](015-behaviour-preserving-package-restructure.md)
is **implemented and closed offline**. The structure separates `engine`,
`agent`, `evaluation` and `cli`, with corresponding test directories.
[015 results](015_results.md) record preservation of all 588 existing cases,
four added boundary checks and unchanged instructions/contracts/command help.
The separately authorized [01-05 replay follow-up](015_replay_results.md)
is also complete and closed; all five completed with their requested edits
and exact-return behavior verified. The user committed this checkpoint.

[016: Human-led trial 06](016-user-led-natural-language-trial.md) is a short
user-run guide with create/chat/resume commands and three suggested starter
prompts. The user reached P009 after a separately approved offline
evidence-handoff repair; see [016 observations and repair](016_results.md).
The three-task policy is unchanged. The trial is not closed or an Autopilot
assignment; further Copilot-initiated live work requires separate authorization.

[017: Conversational photo identity memory](017-conversational-photo-identity-memory.md)
is **successfully completed and closed with the user's sign-off**.
The latest separately authorized replay completed all ten
objectives after a focused assessment repair. The subsequently authorized full
offline regression passed; earlier stopped runs are preserved.
Human-led `p17-human-07` then exposed a numeric multi-mapping validation defect;
its narrow offline repair and full regression passed. The user-led trial
reached P012 with live confirmation of the repair, listing, confirmed
reassignment, forgetting and fresh re-learning without stale-name reuse.
See [017 results](017_results.md).
It adds automatic learning of clear user-supplied identities, natural-language
listing/correction/forgetting, and protection against forgotten names resurfacing
from old evidence. All replay passes and their unused allowances are closed; further fixes
or Copilot-initiated live evaluation require separate authorization. This closes
the bounded phase, not general reliability or broader Phase 1.
The user subsequently merged `nkelly/llm-wip-1` into `main`; see the
[integration note](017_results.md#integration-into-main).

[018: Local conversation-and-preview experience](018-local-conversation-and-preview.md)
is **complete and closed for the agreed local workflow**. It records the UI
direction, completed subphases, tooling approval gates and separately deferred
cloud-persistence work; it is not blanket authorization for that follow-up.
[018a](018a-frontend-tooling-and-ui-skeleton.md) is complete and closed with the
user's acceptance as a starting prototype; see [018a results](018a_results.md).
[018b](018b-local-functions-tooling-and-skeleton.md) is complete and closed
following the user's manual connectivity verification;
see [results and limits](018b_results.md).
[018c](018c-persistent-project-flow.md) is **successfully completed and closed
with the user's manual testing and sign-off** for the agreed create/save/list/reopen flow;
see [results and limits](018c_results.md).
[018d: Behavior-preserving stage extraction](018d-behavior-preserving-stage-extraction.md)
is **successfully completed and closed with the user's acceptance** following
the full offline gate and approved bounded live replay pass;
see [results and limits](018d_results.md).
The replay allowance, including unused calls, is closed.
[018e: Real conversation and previews](018e-real-conversation-and-previews.md)
is **successfully completed and closed with the user's manual testing and sign-off**;
see [results and limits](018e_results.md). Its live allowance is closed.
[018f: Current collage, history and download](018f-current-collage-history-and-download.md)
is **successfully completed and closed with the user's manual testing and
sign-off**, including the requested retirement of the scripted prototype.
Historical viewing, editing-source selection and PNG download use real saved
projects, without web acceptance. See [018f results](018f_results.md).
[018g](018g_results.md) is **satisfied and closed by the accumulated testing
and user's acceptance**, without an additional trial. This closes the bounded
018 local experience; storage/cloud work requires a separate scope and approval.

## Planning records

Numbering is reading order, not phase numbering. These records are snapshots
as retained here: some already include execution notes and later clarifications,
and record 003 spans several feature increments.

| Record | Status and role | Original location |
|---|---|---|
| [001: Project blueprint](001-project-blueprint.md) | Living product vision, architectural direction, and broad sequencing; not an incremental progress tracker. | `ai_collage_builder_project_blueprint.md` |
| [002: Phase 1 offline foundation](002-phase-1-offline-foundation.md) | Step 1 completed; Step 2 outlined but unapproved. Preserves the original format 1 contract and guardrails. | `phase_1_implementation_plan.md` |
| [003: Layout evolution](003-layout-evolution.md) | Implemented borders, cover framing, rounded corners, and tilt, plus format 2 reconciliation and visual-demo decisions. | `docs\layout-decisions.md` |
| [004: Engine refactoring](004-engine-refactoring.md) | Completed format 2 brief, verification, example-equivalence evidence, reviewer outcomes, and retry accounting. | `docs\engine-refactoring-spec.md` |
| [005: Model-connected layouts](005-model-connected-layouts.md) | Closed implementation/evaluation record. See the [checkpoint A handoff](005-model-connected-layouts.md#authorized-six-round-follow-up-handoff); checkpoint B remains unstarted and unapproved. | New planning record. |
| [006: Simplification and repeatability](006-simplification-and-repeatability.md) | Closed revised pass: swap fix and prompt simplification. See [006 results](006_results.md) for replay evidence and limitations. | New planning record. |
| [007: Vision for photos and collage feedback](007-image-understanding-and-interactive-design.md) | Exploratory vision ideas: preview understanding plus human feedback, photo descriptions and subjects; colour/contrast analysis lower priority. No implementation authorized. | New discussion record. |
| [008: Project lifecycle and interactive iteration](008-project-lifecycle-and-interactive-iteration.md) | Complete and closed. See [008 results](008_results.md) for implementation and verification evidence. | New planning record. |
| [009: User-led natural-language trial](009-user-led-natural-language-trial.md) | Complete and closed as a learning iteration; see [009 results](009_results.md). Follow-up proposed in 010. | New planning record. |
| [010: Grounded interpretation and continued human trials](010-grounded-interpretation-and-human-trials.md) | Complete and closed as a bounded improvement phase; tracker links implementation, evaluation and human feedback. | New planning record. |
| [010a: Grounded photo references](010a-grounded-photo-references.md) | Implemented and closed with live sanity follow-up; see [010a results](010a_results.md). | First 010 stage. |
| [010b: Compact history and reliable returns](010b-compact-history-and-reliable-returns.md) | Implemented and closed with live sanity follow-up; see [010b results](010b_results.md). | Second 010 stage. |
| [010c: Timeout recovery and reasoning-trial preparation](010c-timeout-recovery-and-reasoning-trials.md) | Implemented and closed offline; see [010c results](010c_results.md). Integrated review and separate authorization precede live trials. | Third 010 stage. |
| [010d: Bounded reasoning evaluation](010d-bounded-reasoning-evaluation.md) | Executed and closed; see [010d results](010d_results.md). Low generation promising; interpretation issues remain. No default change. | Evaluation follow-up, before exploratory human trials. |
| [010e: Interpretation fixes and frozen comparisons](010e-interpretation-fixes-and-second-freeze.md) | Both passes closed; see [first results](010e_results.md) and [third-freeze results](010e_third_freeze_results.md). Low generation recommended for review; no default change or further calls. | Follow-up to 010d; later interpretation comparison remains separate. |
| [010f: Interpretation efficiency and reasoning comparison](010f-interpretation-reasoning-comparison.md) | Executed and closed; see [010f results](010f_results.md). Generation defaults low with high override; interpretation remains high. | Follow-up to 010e; further trials/default changes need approval. |
| [010g: User-led natural-language trial](010g-user-led-natural-language-trial.md) | Trials [03](010g_results.md) and [04](010g_trial04_results.md) stopped; trial 04 includes accepted P007 and later challenges. | Human-led evidence; further trials require separate approval. |
| [010h: Useful, recoverable progress](010h-useful-recoverable-progress.md) | Implemented and verified offline; [results](010h_results.md), [live replay follow-up](010h_replay_results.md) and [human feedback](010g_trial04_results.md) recorded separately. | Bounded pass and replay follow-up closed. |
| [011: Interpretation and naming reassessment](011-interpretation-and-naming-reassessment.md) | Review complete; [results](011_results.md) recommend a simpler boundary and explicit durable naming. | Selected direction separately approved and implemented in 012. |
| [012: Model-led references and confirmed names](012-model-led-references-and-confirmed-names.md) | Successfully completed and closed with user sign-off; see [results](012_results.md). | Separate [replay](012_replay_results.md), [return repair/retest](012_return_repair_results.md) and [human-led trial 05 / closeout](012_trial05_results.md) evidence; commit remains user-managed. |
| [013: Branch correctness and security review](013-branch-correctness-and-security-review.md) | Executed and closed; see [results](013_results.md). | Full branch delta reviewed; one correctness repair/re-review, no confirmed security vulnerabilities. Subsequently committed/merged by the user. |
| [014: Correctness and security review before main](014-main-readiness-review.md) | Executed and closed; see [results](014_results.md). | Full main-to-target delta reviewed; two correctness repairs/re-review, no confirmed security vulnerabilities. Subsequently committed by the user; no merge during the review. |
| [015: Behaviour-preserving package restructuring](015-behaviour-preserving-package-restructure.md) | Implemented and closed offline; see [results](015_results.md). | Engine/agent/evaluation/CLI and mirrored tests; separate [01-05 replay follow-up](015_replay_results.md) also complete and closed. Checkpoint committed by the user. |
| [016: Human-led trial 06](016-user-led-natural-language-trial.md) | User reached P009 after the repair; not an Autopilot assignment. | [Observations and separately approved offline evidence-handoff repair](016_results.md); three-task policy unchanged. Human-led continuation remains separate. |
| [017: Conversational photo identity memory](017-conversational-photo-identity-memory.md) | Successfully completed and closed with user sign-off; replay and offline regression passed, including the numeric-mapping repair. | See [017 results](017_results.md); human-led `p17-human-07` reached P012 with the repair and memory lifecycle live-confirmed. Copilot replay allowances stay closed; subsequently merged into `main` by the user. |
| [018: Local conversation-and-preview experience](018-local-conversation-and-preview.md) | Complete and closed for the agreed local workflow; 018g satisfied by accumulated testing and user acceptance. | See the [018 tracker](018-local-conversation-and-preview.md); storage/cloud readiness remains separately scoped. |
| [018f: Current collage, history and download](018f-current-collage-history-and-download.md) | Successfully completed and closed with manual sign-off and user-approved Demo retirement; [results](018f_results.md). | Simplified real-project workflow; future trials and Git writes remain separately authorized. |
| [018g: Accumulated end-to-end validation](018g_results.md) | Satisfied and closed by existing user testing, focused fixes and acceptance; no repeated trial. | Closeout record, not a new implementation brief or model allowance. |

Historical status statements, instructions, and budgets apply only to their
recorded increments. They do not authorize new implementation, service calls,
or additional retries. Historical commands and JSON examples are not current
usage instructions; use the current guides linked above.

## Blueprint reconciliation

The blueprint evolves when architectural direction changes; this index and
the numbered briefs/results track incremental work. The important changes
from the original proposal are:

| Original proposal or assumption | Current position |
|---|---|
| Pillow was a proposed renderer. | Pillow is implemented, with strict Pydantic contracts and deterministic geometry/rendering. |
| One master layout JSON with element IDs, `source_image_id`, `src`, `z_index`, and reserved `crop_pan`. | Format 3 recipes use centre coordinates, stable `photo_id`, back-to-front `layers`, explicit whole/cover modes, and cover-only `crop`. Saved snapshots separate authored `recipe` from derived `geometry`; asset paths belong to project metadata. |
| Independently shaped frames and pan/zoom waited for a future graphical UI. | Cover frames and pan/zoom already work through JSON recipes. Graphical controls remain future work; outside borders and rounded corners are also implemented. |
| Image-background fitting was unresolved, and the draft used `expand=True` for rotation. | An ordinary lowest photo layer supplies an image background. Tilt uses centre-preserving rotation and validated sampled footprints; angles are -10 to +10 degrees, not the draft schema's -15 to +15. |
| Phase 1 included model-generated layouts and durable conversations. | Offline foundation, durable conversations, and fixed checkpoint A layout/refinement/acceptance cases now pass. Phase 010 improved grounding, navigation and recovery; human trial 04 produced an accepted image. General reliability and broader Phase 1 sign-off remain outstanding. |
| Captions, shadows, UI, and authenticated cloud deployment were envisioned. | The local React UI and Functions-backed project persistence are implemented; captions, shadows and authenticated cloud deployment remain unimplemented. Historical model names, hosting details, and cost estimates are not verified current selections or prices. |

Format 1 and 2 saved projects remain untouched archives, not loadable or migrated by
the current CLI. Their PNGs remain viewable. Current reproduction instructions
use a fresh data root and the converted example recipes.

## Retained direction

The product goal remains natural-language layout creation and refinement
without regenerating source photos. One metadata-only Microsoft Agent Framework
for Python agent calling a Microsoft Foundry model is the intended experiment;
ordinary code retains validation, geometry, rendering, and project persistence.
The current agent uses the existing `gpt-5.4-mini` deployment; native schema
transport and validated proposals have been exercised in bounded evaluations
and human-led trials. Model-generated geometry can still require corrections;
future evaluation needs separate approval.

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
