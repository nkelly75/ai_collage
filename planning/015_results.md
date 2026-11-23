# 015 results: Behaviour-preserving package restructuring

**Status:** Implemented and closed offline. The agreed mechanical restructuring
and verification are complete; no live evaluation was run.
Scope: [015 brief](015-behaviour-preserving-package-restructure.md).
Changes remain uncommitted for the user; stop here for review.

## Starting checkpoint and structure

Branch `nkelly/llm-wip-1`, HEAD
`a40d77874b6e7370e780105bfea1c0b4d7a5aca9`
(`phase 014 review and fix`). The user's 014 checkpoint was already committed.
The only pre-existing changes were the staged 015 brief and planning index;
their index contents were preserved.

| Package | Contents |
|---|---|
| `ai_collage\engine` | Existing layout/project models, geometry, imaging and project storage |
| `ai_collage\agent` | Conversation, references, task history, agent models/files/requests/provider and both prompts |
| `ai_collage\evaluation` | Callable replay/assessment operations and their report/sequence models |
| `ai_collage\cli` | Existing argument parsing/main functions, terminal chat and presentation |

Tests mirror those four packages; shared fixtures/helpers stay at `tests` root.
The engine and agent retain their separate model files. Existing functions and
large test modules were moved intact, except the agreed CLI entry-point
extraction. No compatibility modules or re-export layers were added.

`python -m ai_collage` and its subcommands, including chat, are unchanged.
The intentional module-command changes are:

- `python -m ai_collage.replay` -> `python -m ai_collage.cli.replay`
- `python -m ai_collage.assess` -> `python -m ai_collage.cli.assess`

Current README/CLI documentation, imports, patch targets and resource/root
lookups now use the new locations. Historical records and evidence were not
rewritten. See [code/test organization](../docs/cli-guide.md#code-and-test-organization).

## Verification and behaviour preservation

The pre-move full offline suite passed **588 tests**. All 588 existing collected
parameterized cases remain, with only their paths remapped. Four focused cases
were added: three command-entry-point help checks and one isolated engine-import
check blocking agent/CLI/evaluation and optional model dependencies.

The focused run passed **113 tests**; the final full offline suite passed
**592 tests**, with no skipped/dropped original cases. Existing tests exercise
pixel/geometry/storage expectations, task/source/naming/acceptance safeguards,
mocked HTTP/replay execution and assessment of synthetic evidence. Counts overlap
and are not additive.

Structural re-review compared all **399 existing top-level function/class
definitions** and 31 global assignments across the moved modules/tests.
Bodies are unchanged after accounting for imports/module references and the
necessary resource/test-fixture location adjustments; extracted CLI `main()`
bodies match their originals. Static import checks enforce the approved
dependency direction: engine has no agent/evaluation/CLI imports, and agent has
no evaluation/CLI imports.

All three command-help outputs match the originals exactly. Both prompt files
are byte-identical; assembled instructions, the generated layout schema and
both native provider response formats match the captured checkpoint exactly.
No schema/record-version, reasoning/default, budget, recovery, acceptance,
rendering or persisted-data/path changes were made. Current consumers have no
stale old module/test paths; documentation links and diff whitespace were checked.

No unresolved implementation findings remain. This is offline equivalence
evidence, not a live reliability claim or a new broad security audit.

## Preservation and hard stop

Fingerprints preserved **4,565 existing files** across original photos, project/
trial data and the separate Foundry experiment directory, plus **1,672 prior
evidence files** including 014. HEAD/branch, staging/index fingerprints,
dependencies and runtime are unchanged. Only the agreed moves/extractions,
import/resource updates, four boundary cases and directly related documentation
changed; existing projects were not recovered or mutated.

Session evidence is under `files\015-refactor`: baseline/source snapshots,
move map, pre/post collection and full-suite logs, focused results, structural
comparison, command-help captures and final preservation/scope/link checks.
No Git writes, installs/downloads, credentials/network probes or live
application model/cloud calls occurred.

015 stops here. Live replay requires a separately approved bounded allowance,
sequences, fresh projects and reasoning settings after review. Human-led trials
follow separately; neither this closeout nor unused historical budgets grants
permission for them, a commit or branch integration.
