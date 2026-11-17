# Offline Engine and Layout Refactoring Spec

**Status: implemented and verified following user approval of this brief.
Independent final review complete; changes remain for the user to commit.**

## Purpose and boundaries

Make the existing offline engine easier to maintain and its layout JSON easier
for an LLM to generate and adjust, without losing current capabilities. This
is one bounded refactoring pass, not a rewrite or a feature-development phase.

The user accepts incompatible JSON syntax and simplifications, provided new
layouts can produce similar results. Existing saved project histories remain
untouched archives. Supply new-format equivalents of all seven current example
recipes as part of the implementation diff.

The latest recorded test baseline is 226 passing cases, not a measured coverage
percentage or a fresh result for this phase. Establish the baseline again at
the start of approved implementation.

## Capabilities to preserve

| Area | Required behavior |
|---|---|
| Sources and identity | Import 2-6 JPEG/PNG photos, honor EXIF orientation, preserve alpha and source files, and assign stable import-order photo numbers. Numbers do not describe content or stacking. Each imported photo still appears exactly once per layout. |
| Canvas and placement | Support square, landscape, and portrait canvases. Independently normalize x/width to canvas width and y/height to canvas height, each on a 0-1 scale. Placement describes the untilted, border-inclusive outer frame. |
| Whole photos | Specify outer width and derive height from the oriented photo's aspect ratio after border inset. Do not require independently consistent width and height, crop, or stretch. |
| Cover frames | Specify both outer dimensions; uniformly fill the inset photo area without empty strips. Preserve fractional source-window sampling, zoom 1-4 relative to minimum cover scale, and normalized pan over available crop travel. Defaults remain zoom 1 and pan 0.5/0.5. |
| Borders | Optional uniform outside border, integer output-pixel thickness, six-digit hex colour. Do not paint over the photo or fill transparent photo interiors. Zero thickness means no visible border. |
| Corners | One nonnegative integer photo-edge radius. Positive outer radius equals photo radius plus border thickness; zero keeps both boundaries square. Reject excessive radii rather than clamping. Preserve smooth alpha-aware edges without seams or halos. |
| Tilt | Finite -10 to +10 degrees, including fractions; positive clockwise. Rotate the finished photo/frame around its unchanged centre in output-pixel space. Zero means no rotation. |
| Bounds and overlap | Check continuous geometry and rounded/sampled pixel footprints, including tilt sampling clearance. Reject overflow; never silently move, shrink, stretch, crop, or clip to fit. Inter-photo overlap remains intentional and allowed. |
| Backgrounds and stacking | Solid canvas colour plus ordered photo layers. A borderless full-canvas photo can be the background; no special image-background feature is necessary. A photo and its frame always share one layer. |
| Versions and persistence | Validate, resolve, and render before accepting an immutable snapshot. Update the current pointer last. Invalid input, rendering failure, or ordinary publication failure must preserve the previous accepted state. Reopen/rerender new-format saved versions in another process without reimporting. |
| Strictness and offline use | Reject unsupported fields/features, invalid references, non-finite numbers, duplicate JSON keys, inconsistent snapshots, and invalid geometry with explicit errors. Preserve the thin CLI, nonzero error exit status, and offline execution. |

Keep the existing numeric limits: 25 MiB per photo, 40 million decoded pixels
per image, canvas axes 1-4096 pixels, and 2-6 photos/layers. Keep safe project-ID
rules, owner-scoped imported assets, and the single-local-writer assumption.
Do not silently expand product rules such as photo omission/reuse.

Preserve `create`, `inspect`, `apply-layout`, and `render`, including the existing
`--data-dir`, `--project`, `--layout`, and `--version` workflows. Rerendering an
accepted new-format version must not create another version or make an older
version current. JSON result field names may follow the revised contract, but
document those changes. Keep strict numeric types: booleans and numeric strings
are not substitutes for numbers.

## Proposed input contract

The approved contract below is now implemented.

- Use `schema_version: 2`; make unsupported old formats fail clearly.
- Keep `canvas.width` and `canvas.height` in output pixels. Simplify the solid
  background to `canvas.background: "#RRGGBB"` rather than a constant type tag.
- Replace `elements` with `layers`, ordered **back to front**. Array order is the
  sole stacking rule; remove `z_index`.
- Use `photo_id` as the stable photo reference and layer identity. Remove the
  redundant element `id` and constant `type: "image"` fields. This is safe within
  the retained exactly-once-per-photo rule; reusing photos remains out of scope.
- Require an explicit `mode: "whole"` or `mode: "cover"` on each layer.
  Represent these as a discriminated union of strict typed models, so the
  generated schema describes the alternatives instead of relying on a
  cross-field presence check.
- Both modes use `box` with normalized `x`, `y`, and `width`. Whole mode forbids
  `height`, even `null`, and forbids crop controls. Cover mode requires a
  positive `height` and accepts optional `crop` with `zoom`, `pan_x`, and `pan_y`.
  An omitted cover `crop` uses defaults; explicit `crop: null` is invalid.
- Retain optional `border`, `corner_radius_px`, and `rotation_degrees`, including
  their current units and limits. Omitted/null border means none; an omitted
  radius/angle means zero. Do not introduce aliases or multiple spellings.
- Use `photo_id` consistently in new project metadata, snapshots, CLI results,
  and tests. Mark changed persisted contracts with the new format version;
  saved layout revision numbers remain a separate concept.
  New project metadata and snapshot envelopes both use `schema_version: 2`.

For example, the current three-photo London Eye composition could be expressed
as follows. Its project import order is Bridge 1, London Eye 2, bookshop 3.
The photo IDs remain unchanged when their layer order changes.

```json
{
  "schema_version": 2,
  "canvas": {
    "width": 1200,
    "height": 1600,
    "background": "#282A2E"
  },
  "layers": [
    {
      "photo_id": 2,
      "mode": "whole",
      "box": { "x": 0.0, "y": 0.0, "width": 1.0 }
    },
    {
      "photo_id": 3,
      "mode": "cover",
      "box": { "x": 0.049167, "y": 0.044375, "width": 0.361667, "height": 0.38375 },
      "crop": { "zoom": 1.05, "pan_x": 0.0, "pan_y": 0.9 },
      "border": { "width_px": 10, "color": "#FFFFFF" },
      "corner_radius_px": 12,
      "rotation_degrees": -2.0
    },
    {
      "photo_id": 1,
      "mode": "whole",
      "box": { "x": 0.513333, "y": 0.523125, "width": 0.4425 },
      "border": { "width_px": 10, "color": "#FFFFFF" },
      "corner_radius_px": 12,
      "rotation_degrees": 2.0
    }
  ]
}
```

Generate a reviewable input JSON Schema from the Pydantic models at
`docs\layout.schema.json`. Describe field units, mode rules, defaults, pan
direction, and rotation sign in the model/schema descriptions. Add a concise
LLM-facing field guide at `docs\layout-format.md`, including how to move/resize
a photo, change its crop, or bring it forward without renumbering photos.
No live LLM integration or generation-quality experiment is included.

The schema documents structural constraints; project membership, complete
photo usage, geometry, and source-dependent limits still require engine
validation. Do not claim that JSON Schema alone guarantees a renderable layout.
Keep the checked-in JSON Schema synchronized with the models through a test.

## Internal refactoring

1. **Separate authored intent from computed geometry.** Store the validated
   input recipe once inside the new versioned snapshot, alongside separate
   typed derived geometry and the accepted revision number. Do not inherit
   input models merely to override field meanings, or reconstruct recipes by
   dumping a snapshot and deleting fields. Recompute and compare derived
   geometry when reopening a snapshot to retain consistency checks.
2. **Extract pure geometry from image I/O.** Put placement, half-up rounding,
   border inset, cover source-window calculations, and rotated footprint
   calculations in `ai_collage\geometry.py`, depending on metadata/contracts
   rather than Pillow or filesystem operations.
3. **Simplify rendering where safe.** Prefer shared helpers for source
   resize/crop, complete frame construction, optional rotation, and compositing.
   Keep purposeful square/rounded or zero-angle branches where they genuinely
   help correctness or cost; do not build a generic effects/plugin framework.
   Preserve alpha behavior and avoid giant zoomed/supersampled intermediates.
4. **Keep storage and CLI small.** Retain `projects.py` for local persistence and
   a thin `__main__.py`. Update dependent call sites consistently, without a new
   repository abstraction or public API invented for future cloud work.

Keep the existing rounding order and crop/rotation mathematics unless a
demonstrated defect requires a focused correction. Private helper names and
the exact typed snapshot representation are implementation details; changing
the agreed product semantics is not.

## Examples and archive protection

Convert the following seven active recipes **in place** to the new input
format. Keeping the descriptive filenames makes each old-to-new equivalent
visible directly in the diff; do not keep duplicate legacy recipes as active
examples or substitute one generic demonstration.

| Example under `examples` | Composition to retain |
|---|---|
| `portrait_9x16.json` | 900x1600, four whole photos in the existing two-by-two arrangement. |
| `portrait_3x4.json` | 900x1200, the corresponding whole-photo arrangement with its existing spacing. |
| `emma_2x3.json` | 1200x1800 layered whole-photo approximation, 15-pixel white borders and larger foreground Bridge. |
| `emma_framed_2x3.json` | Refined bookshop and breakfast cover crops, including the bookshop's 1.05 zoom and 0.9 vertical pan. |
| `emma_rounded_2x3.json` | The framed composition with 10-pixel photo radii and 15-pixel borders. |
| `emma_tilted_2x3.json` | Latest charcoal composition: enlarged lower-left Bridge, breakfast shifted right, near-corner bookshop, current tilts, 10-pixel borders and 12-pixel radii. |
| `emma_london_eye_3x4.json` | Latest full-photo night background with smaller foreground bookshop/Bridge, current corner clearances/crops, and no breakfast. |

The first six retain the four-photo mapping Bridge 1, breakfast 2, Eye 3,
bookshop 4. The last retains its separate three-photo mapping above. Preserve
visual layer order when translating explicit z-values into array order.

Before changing the engine or recipes, generate reference renders of all seven
current recipes using fresh isolated verification projects. After refactoring,
render their equivalents into separate fresh projects. Keep before/after
outputs and verification notes in the session artifact directory, not in the
tracked source tree or existing project histories. Use the existing `--data-dir`
option; do not add a migration command.

Treat all pre-existing `.collage-data` files and `photos` inputs as read-only.
Do not rerender, rewrite, migrate, delete, rename, or update current pointers in
those old projects, even if a replacement would be byte-identical. Record
before/after file inventories and hashes to verify they stayed unchanged.
Old PNGs remain viewable; the new CLI need not reopen old-format project
histories. Document that boundary and show fresh-root reproduction commands.

For example equivalence, compare canvas size, source selection, placement,
crop, layer order, styling, tilt, and resulting images. Prefer the same resolved
geometry and source windows; record and explain any deviations. PNG byte
identity is not required, and small justified sampling/antialiasing differences
need not preserve a redundant legacy rendering path. Changed crops,
stretching, lost overlaps/corners, halos, or different styling are not excused
by an overall resemblance. Supply actual before/after previews for review,
not only hashes or bounding-box claims.

## Tests and verification

- Reorganize `tests\test_offline.py` by responsibility, for example contracts,
  geometry, rendering, storage, and CLI, with small shared fixtures/helpers.
  Avoid a test framework of our own.
- Preserve meaningful existing assertions and edge cases, especially synthetic
  pixel tests, alpha, shapes/aspect ratios, crop extremes/subpixels, rounding,
  rotation direction/centre/corner retention, strict bounds, immutable versions,
  saved-state tampering, publication rollback, and subprocess persistence.
- Adapt old-format-only assertions intentionally. Replace obsolete legacy
  loading expectations with new-contract round trips and explicit unsupported
  version errors, while retaining the zero-border/radius/angle rendering checks.
  Test count may change; reducing behavior coverage to obtain green tests is
  prohibited.
- Add focused tests for the discriminated modes, stable photo identity under
  layer reordering, recipe/snapshot separation, new hardening, and converted
  example validation/rendering. Exercise representative layout adjustments
  without adding a patch language or calling an LLM.
- Keep network-blocking protections and credential-free subprocess checks.
  Use the existing environment and pytest; do not add coverage/lint frameworks
  merely for this pass.
- Run relevant targeted tests during development, then the full suite
  sequentially to avoid unnecessary contention. Do not relax the existing
  subprocess timeouts to hide failures.

The full-suite command remains:

```powershell
.\.venv\Scripts\python.exe -m pytest -q .\tests
```

Update the README, CLI guide, and layout-decision notes to match the implemented
contract, examples, archive boundary, and any changed module/test structure.
Retain the original phase plan as a historical record, not a competing current
format guide.

## Focused security review and hardening

Review the local CLI with potentially malformed images, JSON, or saved state.
`local-dev` is a storage namespace, not authentication. Hosted multi-tenant
authorization, concurrent hostile filesystem writers, and crash-recovery
transactions are not features of this phase.

- Preserve byte/pixel/format/frame-count image checks, EXIF handling, path
  containment, imported asset naming, safe project IDs, and no layout-supplied
  filesystem paths. Check decoding/resource lifetimes and bounded rendering
  allocations, not just validation after allocation.
- Bound recipe, project, and snapshot JSON reads to **1 MiB per document** before
  full decoding/parsing, using a bounded read rather than only a racy size check.
  This is a new hardening limit, comfortably above the six-photo formats.
  Reject oversize/invalid encoding/duplicate keys/non-finite constants and
  parser recursion failures with clear domain/CLI errors. Do not raise the
  interpreter's recursion limit or write a custom JSON parser.
- Check saved-state fields that influence paths, allocations, iteration, or
  overwrite decisions. Retain derived-geometry revalidation and failure-safe
  publication. Never turn malformed state into a silent default/success.
- Review dependency usage and record evidence-backed significant concerns.
  Do not claim a current dependency-advisory audit or absence of vulnerabilities
  without having verified it.

Apply small, demonstrable hardening fixes within this scope and add focused
regressions. If a serious finding requires a materially broader design change,
stop and report it rather than silently expanding the phase. This section is
review scope, not a claim that the security review has already happened.

## Execution order and acceptance

Following explicit implementation approval:

1. Capture the read-only Git/index state, protected-file inventories, baseline
   tests, and seven isolated reference renders before implementation changes.
2. Have one rubber-duck reviewer challenge this spec before code changes,
   concentrating on capability loss, schema clarity, and acceptance gaps.
   Resolve only in-scope findings; return material contract changes to the user.
3. Implement the contract and geometry/rendering separation, reorganize tests,
   and make the scoped hardening changes.
4. Convert all seven recipes and update schema/field-guide/current usage docs.
5. Run targeted/full verification, reopen/rerender new snapshots, compare all
   seven compositions, and confirm the protected inputs/archives/index.
6. Obtain one independent final code review covering correctness, maintainability,
   and significant local-engine security concerns. Address concrete findings
   only within the shared retry budget and revalidate affected behavior.
7. Leave the reviewable diff and give a concise handoff: changes, test outcomes,
   example preview locations, remaining findings/limitations, reviewer results,
   and retry accounting by work package, macro round, and phase total. Stop;
   do not start the next feature phase.

Acceptance requires all preserved capabilities, all seven new-format example
equivalents and their visual evidence, passing applicable tests, consistent
new-format snapshots across processes, unchanged protected files/Git state,
accurate documentation, and no unresolved significant regression or security
finding. If a required check/review cannot be completed, report that plainly;
do not label the phase fully verified.

## Non-negotiable Autopilot guardrails

- **Approval boundary:** This is documentation only until the user explicitly
  authorizes this refactoring brief. Switching modes alone is not permission
  to broaden scope or execute paid experiments.
- **No Git writes of any sort:** No stage, commit, push, branch/ref changes,
  checkout, worktree creation, stash, reset, amend, configuration changes, or
  other Git mutations. Ordinary approved source-file edits are allowed.
  Read-only inspection is allowed; use `git --no-optional-locks --no-pager`
  where applicable. Preserve the user's index, history, branch, and unrelated
  edits. The user reviews and commits independently.
- **Local debugging allowance:** After initial implementation/validation, allow
  at most **two focused correction/recheck cycles per agreed work package**.
  The fixed packages are contracts/schema, geometry/rendering, storage/hardening,
  tests, and examples/docs. A missed field rename in one helper is local even
  if discovered by the full suite. Assign a correction to the package being
  fixed, not merely the test that exposed it. Do not split, rename, or create
  packages to refresh an allowance.
- **Macro recovery allowance:** Allow at most **two coordinated recovery
  rounds** for integration or review findings requiring broader rework, such
  as disagreement between geometry and persistence. A localized failed check
  does not itself consume a macro round. Macro rounds do not refresh local
  allowances, authorize extra reviews, or bypass a local limit by relabelling
  the same small issue as broader rework.
- **Shared phase ceiling and accounting:** Allow at most **six corrective
  cycles total for the entire approved phase**, shared across all commands,
  failures, reviewers, and agents. This includes coordinated macro corrections
  and every local cycle inside a macro round; the allowances are not additive.
  A cycle is a bounded group of corrections followed by revalidation after a
  failure or actionable review finding. Each macro round uses at least one
  cycle; further correction/recheck cycles consume additional slots from the
  same six. Local cycles also consume their package's allowance. A rerun after
  failure counts even without code changes. Routine inspection and planned
  first-pass work are not retries. Record each cycle's package(s), macro round
  if applicable, trigger, hypothesis, changes, outcome, and remaining allowances.
  No counter resets per command, error, reviewer, agent, or session.
- **Evidence and stopping:** Each retry needs a concrete hypothesis, a bounded
  correction, and an appropriate check. Do not repeat an unchanged failing
  command without evidence of a transient cause. Stop early if the same failure
  recurs without new evidence, or if recovery requires a scope/contract change.
  If another correction would exceed any applicable package, macro, or total
  limit, preserve work and report the blocker. Never weaken assertions,
  regenerate expected results blindly, relax limits/timeouts, expand scope,
  switch providers, or bend the objective to obtain a pass. Complete scoped
  revalidation after the last permitted correction, but do not enter another
  corrective cycle without renewed user approval.
- **Bounded reviewers:** One preimplementation rubber-duck review and one
  independent final code review, in separate reviewer contexts. No fleet,
  nested agents, autonomous workflow, extra review rounds, or new worktrees.
  Use configured reviewer/model preferences; no model override is specified by
  this brief. Report the reviewers actually used; do not imply distinct models
  without evidence. Reviewer-driven corrections obey the same local/macro
  limits and shared phase ceiling; delegation never grants extra permissions.
- **Zero application service budget:** No Azure/Foundry/OpenAI calls, token
  acquisition, model-client integration, service configuration, or execution
  of `temp-foundry-test` scripts. Do not modify that experiment directory.
  The two approved Copilot code/spec reviews are distinct from application
  inference; they consume normal Copilot usage, not a new experiment allowance.
- **Dependencies:** No new runtime dependency is planned. Use existing tools;
  install/restore only after a required manifest change or a missing-dependency
  failure, and only for this brief. No opportunistic upgrades, new toolchains,
  secret access, or uploading source/photos to external services.
- **Filesystem safety:** Archive/source protection above applies throughout,
  including to agents. Use isolated verification roots, preserve unrelated
  changes, and clean up only specifically identified disposable files created
  by this phase. Never delete or reset an existing data root to make a run pass.
- **No feature creep:** No captions/text, shadows, intentional off-canvas
  clipping, photo omission/reuse, graphical UI, natural-language execution,
  patch DSL, authentication, deployment, cloud storage, migration, or concurrent
  writer support. Similar results and maintainable internals are the objective,
  not exact old JSON or PNG bytes.

## Execution record

Implementation approval: **given for this brief and guardrails**.
Implementation/review runs: **implementation and verification complete;
spec challenge and independent final review complete**.
Local corrective cycles: **examples/docs 1, tests 2; other packages 0
(maximum 2 each)**.
Macro recovery rounds: **0 of 2**.
Total corrective cycles: **3 of 6 across the phase, including macro recovery**.
Git writes and application service calls: **none**.

The user explicitly approved implementation after reviewing the revised retry
budget. The fresh baseline passed all 226 tests; seven isolated reference
renders reopened/rerendered identically, and 60 protected files were recorded.

Spec challenge: the rubber-duck reviewer found no blocking issue. Its
non-blocking clarifications are covered by explicit v2 project/snapshot
versions, omitted-but-not-null cover crop defaults, schema synchronization,
photo-usage/old-archive rejection tests, and exact baseline-geometry comparison.
Cycle 1 (examples/docs) records these clarifications; no contract or scope
expansion was required. Geometry baselines were already captured before review.

Verification after implementation: **252 tests passed**. All seven converted
examples have identical resolved geometry, source windows, pixels, and PNG
bytes compared with their isolated old-format references. New snapshots
reopened and rerendered identically; all 60 protected files, including the Git
index and archived inputs/state, remained unchanged.

Cycles 2 and 3 (tests) corrected one new recursion-error fixture. The first
fixture assumed depth 2000 must fail; the second assumed the Python recursion
limit controlled the JSON scanner. A read-only probe confirmed CPython 3.12's
C scanner has a separate threshold (2000 accepted, 4000/10000 rejected).
The final test deterministically injects the parser's `RecursionError` to
verify its translation to a domain error, without testing interpreter internals
or changing recursion limits. Both targeted error tests and the full suite
then passed; no engine correction or macro recovery was necessary.

The independent final code-review context reported **no significant issues**
after reviewing the implementation. It did not independently rerun the supplied
verification or perform a current dependency-advisory audit. The configured
rubber-duck and code-review agents were used once each; their underlying model
IDs were not reported, so distinct models are not claimed.

Evidence is retained in the session artifacts under `refactor-evidence`:
`protected.json`, `before.json`, `after.json`, `comparison.json`, isolated
before/after projects, full-resolution renders, and overview PNGs for visual
comparison. No generated personal-photo renders or runtime projects were added
to the tracked source tree. No significant unresolved local-engine finding was
identified; this is not a claim of security against concurrent hostile writers
or an advisory-clean dependency set.
