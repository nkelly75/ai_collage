# Repository entry point

Build natural-language collage design around deterministic rendering of original
photos, not AI image regeneration. The offline Python engine/CLI and layout
format 2 are implemented; application LLM integration, UI, and cloud hosting
remain future work.

Read first:
- [README](../README.md): overview, Quick start, and examples.
- [Planning index](../planning/README.md): current status, vision, historical
  decisions, and future-phase approval conventions.
- [CLI guide](../docs/cli-guide.md): workflows, storage, limits, and verification.
- [Layout field guide](../docs/layout-format.md) and
  [JSON Schema](../docs/layout.schema.json): current layout contract.

Working rules:
- Stay within the approved scope and retry/service budgets. Historical plans
  are records, not authorization for new work or current format specifications.
- No Git writes without explicit approval; preserve the user's staging,
  history, and branches.
- Run application code/tests offline unless separately authorized. Do not run
  Foundry experiments or access cloud services implicitly. Preserve original
  photos and pre-existing archived project data.
