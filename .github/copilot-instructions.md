# Repository entry point

Build natural-language collage design around deterministic rendering of original
photos, not AI image regeneration. Read the planning index for current status,
approval gates, and links to phase results; scripted/offline success is not
user sign-off.

Read first:
- [README](../README.md): overview, Quick start, and examples.
- [Planning index](../planning/README.md): current status, vision, historical
  decisions, and future-phase approval conventions.
- [CLI guide](../docs/cli-guide.md): workflows, storage, limits, and verification.
- [Layout field guide](../docs/layout-format.md) and
  [JSON Schema](../docs/layout.schema.json): current layout contract.

Working rules:
- Keep documentation focused: the main README is an approachable overview,
  the planning index summarizes status and links, and these instructions hold
  durable rules and references. Keep phase evidence, metrics, and accounting
  in the relevant results record; link rather than repeat them elsewhere.
- Stay within the approved scope and retry/service budgets. Historical plans
  are records, not authorization for new work or current format specifications.
- No Git writes without explicit approval; preserve the user's staging,
  history, and branches.
- Run application code/tests offline unless separately authorized. Do not run
  Foundry experiments or access cloud services implicitly. Preserve original
  photos and pre-existing archived project data.
- Prefer simplicity and one current implementation over backward compatibility:
  there are no existing users requiring legacy support. When an approved change
  benefits from breaking a contract, version it explicitly and move affected
  code, features, tests, examples and documentation forward together. Do not add
  compatibility shims, dual paths or migrations unless explicitly required.
  Preserve old data/evidence as untouched archives; clearly reject unsupported
  versions rather than silently reinterpret them. Bump only affected contracts
  when needed; do not introduce a new layout format for unrelated agent changes.
