# 015: Behaviour-preserving package restructuring

**Status:** Implemented and closed offline; see [015 results](015_results.md).
All 588 existing cases were preserved; the final suite passed 592 cases.
The user's pre-refactor [014 checkpoint](014_results.md), branch and staging
were preserved. Changes remain uncommitted; stop for review before any separately
authorized live evaluation. Work stayed on `nkelly/llm-wip-1`.

## Purpose and file map

Separate the deterministic engine, reusable conversational agent, evaluation
tools and terminal interface without redesigning their behaviour. A future web
interface can use `agent`/`engine` without importing terminal or evaluation code.
Paths below are relative to `ai_collage`; add ordinary package `__init__.py`
files, not re-export layers or compatibility shims.

| Current file(s) | Destination |
|---|---|
| `models.py`, `geometry.py`, `imaging.py`, `projects.py` | Same filenames under `engine\` |
| `conversation.py`, `photo_references.py`, `task_history.py` | Same filenames under `agent\` |
| `agent_models.py` | `agent\models.py` |
| `agent_files.py` | `agent\files.py` |
| `agent_requests.py` | `agent\requests.py` |
| `agent_provider.py` | `agent\provider.py` |
| `prompts\request-intent.md`, `prompts\layout-agent.md` | Same filenames/content under `agent\prompts\` |
| `replay.py`, `assess.py`: callable operations and report/sequence models | `evaluation\replay.py`, `evaluation\assess.py` |
| Those modules' argument parsing and `main()` entry points | `cli\replay.py`, `cli\assess.py` |
| `chat.py` | `cli\chat.py` |
| `__main__.py`: existing CLI implementation | `cli\main.py` |
| Root `__main__.py` | Small standard entry point delegating to `cli.main.main` |

Keep the already separate engine/agent model definitions; agent models may
reference engine layout types. Keep evaluation-specific models with their tools.
Dependencies run `cli` -> `evaluation`/`agent`/`engine`, `evaluation` ->
`agent`/`engine`, and `agent` -> `engine`, never in reverse. Deterministic
conversation safeguards belong to `agent`, not the rendering engine.

## Behaviour and scope boundaries

Only file moves/renames, mechanical CLI extraction, import/patch-target changes,
resource-path corrections and directly dependent documentation are in scope.
Keep existing functions, safeguards, error handling, defaults and outputs.
Update prompt/field-guide loading and test repository-root discovery for their
new locations; loaded instruction content must remain identical.

`python -m ai_collage` and its existing subcommands, including `chat`, retain
their syntax and behaviour. The agreed module-command changes are:

- `python -m ai_collage.replay` -> `python -m ai_collage.cli.replay`
- `python -m ai_collage.assess` -> `python -m ai_collage.cli.assess`

Update current guides, examples of commands, schema-maintenance imports and
other active consumers together. Do not rewrite historical results/evidence.
Do not retain the old module paths, add new CLI features, split large business
modules/tests, or introduce shared-package abstractions. No prompt, schema,
record-version, persisted-data/path, dependency, model/reasoning, budget,
recovery, acceptance or rendering changes. Pause for discussion if correctness
requires anything beyond the agreed mechanical scope.

## Tests and offline execution gate

Mirror the packages by moving intact test modules:

| Destination | Existing test modules |
|---|---|
| `tests\engine\` | `test_centers`, `test_contracts`, `test_geometry`, `test_rendering`, `test_storage`, `test_examples` |
| `tests\agent\` | `test_agent`, `test_task_history`, `test_timeout_recovery` |
| `tests\evaluation\` | `test_replay`, `test_assess` |
| `tests\cli\` | `test_cli` |
| `tests\` root | Shared `conftest.py`, `helpers.py` and package initialization |

1. Confirm the user's 014 checkpoint before implementation. Record starting
   HEAD, existing changes/staging, protected photo/project/evidence fingerprints
   and runtime; use read-only Git inspection, never create the checkpoint.
2. Record pre-move collection/offline baseline. Preserve all **588 existing
   parameterized cases** from 014, accounting for their new paths; do not drop,
   skip or weaken tests. A few focused entry-point/import-boundary checks may
   be added if needed.
3. Perform the restructuring; run focused checks, then the full existing offline
   suite with the repository's network-blocking fixtures. Verify command help,
   offline CLI/mocked replay/assessment behaviour, engine independence from
   optional agent dependencies, unchanged schemas/instructions and existing
   pixel/geometry/persistence expectations. Fixtures use isolated temporary
   projects, not recovery or mutation of existing projects.
4. Re-review the final diff for accidental logic changes; verify preservation
   and report exact collection/results, command changes and any limitations.
   Offline failures authorize only in-scope offline investigation/repairs.

Use the existing environment and test runner:
`.\.venv\Scripts\python.exe -m pytest -q --tb=short -p no:cacheprovider`.
No installs/downloads or dependency changes; report missing prerequisites.
Mocked replay tests are allowed. Standalone replay commands are limited to
`--help` or `--check` against temporary fixtures; live replay is not an offline
test. Assessment may run only against isolated synthetic evidence.

## Closeout and hard stop before live evaluation

Write concise `015_results.md` with the starting checkpoint, final structure,
behaviour-preservation evidence, test accounting, preservation and remaining
concerns. Update this brief and the planning index, then **stop for review**.
No live application model/cloud calls, credentials/network probes, Git writes,
staging, commits, merges or branch changes. Preserve original photos, existing
projects/accepted versions/trials, sealed evidence and user changes/staging.

Successful offline completion does **not** authorize live replays. Only after
review may a separate explicit authorization select sequences, fresh projects,
reasoning settings and a bounded call allowance. Human-led trials follow
separately. Neither a failing test nor autopilot mode relaxes these gates.
