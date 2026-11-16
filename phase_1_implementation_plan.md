# Phase 1 Implementation Plan: Local Collage Engine

**Status: Discussion draft, not approved for implementation.**

This repository plan refines `ai_collage_builder_project_blueprint.md`.
Only plan updates are currently authorized. The initial Autopilot implementation
scope, once explicitly approved, is **Step 1 only**. Step 2 is context for later
planning, not part of that implementation brief.

## Two-step boundary

1. **Step 1: Offline foundation.** Prove that explicit layout JSON reliably
   produces the intended collage from local photos. No model or Azure calls.
2. **Step 2: Model-connected experiment.** Let an Agent Framework agent create
   and refine layouts using the same project, validation, and rendering code.
   Define and approve a separate detailed brief and paid-call budget first.

`temp-foundry-test\agent_smoke_test.py` is verified reference code for Step 2:
DefaultAzureCredential, the working OpenAI resource endpoint, the existing
deployment, explicit request limits, and a reused framework session. Its
in-memory history does not itself solve durable history across separate CLI runs.
Preserve both smoke-test scripts rather than turning them into the application.

## Step 1: Proposed scope

### CLI and local projects

- Import 2-6 user-supplied JPEG/PNG photos into a local project; report stable
  photo numbers, dimensions, and aspect ratios. Honor EXIF orientation.
- Accept a hand-authored layout JSON file referring to those photo numbers.
  Copilot will prepare its initial contents, tailored to the user-provided
  working photos and their metadata; the user need not author the first layout.
  This is a supplied fixture, not an automatic layout-generation feature.
  Supply one portrait example at **9:16 (width:height)**, not a 16:9 landscape
  example. The starter canvas is 900-by-1600 pixels, as specified below.
- The user supplied working images in `photos` with the intention of committing
  them later. Preserve them as curated repository inputs; do not ignore that
  directory automatically. Obtaining, generating, or selecting those working
  photos is not Copilot's responsibility. Do not fetch substitutes.
  Synthetic images created by automated tests are separate from these inputs.
- Validate the layout before accepting a version; render a PNG preview.
- Inspect project metadata and saved layout versions; reopen and re-render a
  saved layout in a new CLI process without reimporting photos.
- Manual JSON edits and another import/render allow offline experimentation.
  No natural-language interpreter, automatic layout algorithm, or fake LLM.
- Persist imported photos beneath the local owner and projects beneath
  `users\local-dev\projects\{project_id}`. Keep metadata, photo references,
  accepted layout versions, the current-version reference, and rendered output.
- Do not modify source photos. Invalid layouts/render failures must not replace
  the last accepted state. Layout references resolve known photo IDs, not
  arbitrary filesystem paths.
- Do not fabricate conversation turns; real prompts/responses belong to Step 2.

### Geometry and rendering

- Square, landscape, and portrait canvases via positive pixel dimensions.
- Both normalized axes remain 0.0-1.0, scaled by their respective canvas dimension.
- Show whole photos without cropping/stretching. Choose normalized width and
  derive height from both source-photo and canvas aspect ratios.
- Define the sizing input separately from the resolved layout; do not require
  users or a future LLM to calculate two independently consistent dimensions.
  Finalize this contract before implementing, rather than blindly copying the
  draft blueprint schema.
- Solid background and explicit stacking order; overlap is allowed.
- **Agreed lean baseline:** rotation is zero; defer tilt and shadows to a later
  increment. This narrows Step 1, not the blueprint's eventual capabilities.
- Defer captions/text, image backgrounds (fitting remains unresolved),
  non-neutral crop/pan/zoom, and graphical controls.
- Reject unsupported features, invalid references, duplicate element IDs,
  non-finite/out-of-range geometry, and out-of-bounds placements explicitly.
  Do not silently crop, clamp, or replace layouts to make them valid.

### Proposed implementation shape

- Small Python package with a thin CLI. Project persistence, geometry, validation,
  and rendering remain usable without the CLI and future Functions wrappers.
- Use Pillow for image inspection/rendering, as confirmed during refinement.
  Recommend standard-library argparse for the CLI. Decide on Pydantic with the
  layout contract.
- Synthetic-image automated tests plus manual previews with the supplied photos.
  Ignore environments, temporary test files, and generated runtime state, not the
  curated `photos` inputs or useful layout JSON examples.
- Finalize numeric upload-byte, decoded-image, canvas-size, and element-count
  limits before implementation, not during Autopilot.
- Use a repository-level Python package and separate app `.venv`/requirements
  file, as confirmed by the user. Preserve the temporary smoke-test environment.
  Avoid speculative storage abstractions.

## Proposed CLI and file contracts (for discussion)

The following details are proposals, not yet implementation instructions.
Use standard-library argparse and invoke a small `ai_collage` Python package.
Default data root: `.collage-data` beneath the repository when commands run
there. A global `--data-dir` option may select another explicit local root.
Use a single local process/writer; multi-process concurrency is out of Step 1.

### Commands

Run these from the repository root using the app environment's Python.
The user supplied the working photos in `photos`; preserve those source files.

```powershell
python -m ai_collage create --project portrait-demo --images .\photos\01_tower_bridge.jpg .\photos\02_breakfast.jpg .\photos\03_london_eye.jpg .\photos\04_daunt_books.jpg
python -m ai_collage inspect --project portrait-demo
python -m ai_collage apply-layout --project portrait-demo --layout .\examples\portrait_9x16.json
python -m ai_collage render --project portrait-demo --version 1
```

- `create`: Validate/import the supplied photos in argument order, assign stable
  project-visible image numbers starting at 1, and print metadata and project
  location. Fail if the project ID already exists. No layout is generated.
- `inspect`: Print selected-photo IDs/metadata, accepted versions, current version,
  and output locations. Work even before the first layout has been accepted.
- `apply-layout`: Read supplied JSON, validate/resolve dimensions, and render
  before accepting a new immutable layout version. On success save the layout
  and PNG, update the current-version reference, and print their paths.
  On failure do not change the last accepted version.
- `render`: Re-render the specified accepted version; omit `--version` to use
  current. It does not create a new layout version or change which is current.
  It may atomically replace that version's generated PNG, never its layout or
  source assets. Error clearly if no accepted version exists.
- Errors go to stderr with nonzero exit status; no partial success-shaped result.
- Project IDs are local safe slugs, not paths. Finalize validation and document it.
- No delete, reset, natural-language refine, rollback, or image replacement/removal
  commands in Step 1. History inspection is part of `inspect`.

### Hand-authored input layout

**Where are the image paths?** `create --images` imports the source files and
records their mapping in `project.json`. A layout's `source_image_id` resolves
through that project's photo records to an owner-scoped imported copy. The
layout deliberately contains IDs rather than machine-specific file paths.
Layout JSON is therefore portable between projects with the same photo-number
mapping, but is not a standalone bundle of photos.

Use the existing blueprint field names where possible, but distinguish
`schema_version` (format) from the backend-assigned `version` (saved revision).
The input requires `schema_version`, `canvas`, and `elements`; it does not
control the owner, project ID, saved revision, filesystem path, or derived height.

Proposed starter fixture, tailored to the four supplied 3:4 photos. This lives
in the plan for now; create `examples\portrait_9x16.json` during approved
implementation, using this content if the contract is confirmed:

```json
{
  "schema_version": 1,
  "canvas": {
    "width": 900,
    "height": 1600,
    "background": { "type": "color", "value": "#FFFFFF" }
  },
  "elements": [
    {
      "id": 1,
      "type": "image",
      "source_image_id": 1,
      "box_normalized": { "x": 0.04, "y": 0.14, "width": 0.44 },
      "z_index": 1
    },
    {
      "id": 2,
      "type": "image",
      "source_image_id": 2,
      "box_normalized": { "x": 0.52, "y": 0.14, "width": 0.44 },
      "z_index": 2
    },
    {
      "id": 3,
      "type": "image",
      "source_image_id": 3,
      "box_normalized": { "x": 0.04, "y": 0.53, "width": 0.44 },
      "z_index": 3
    },
    {
      "id": 4,
      "type": "image",
      "source_image_id": 4,
      "box_normalized": { "x": 0.52, "y": 0.53, "width": 0.44 },
      "z_index": 4
    }
  ]
}
```

- The fixture uses 900-by-1600 pixels, a 9:16 portrait canvas. Each photo becomes
  396-by-528 pixels, with derived normalized height 0.33. Top-left pixel
  positions are (36,224), (468,224), (36,848), and (468,848), in import order.
  This simple 2x2 baseline has no overlap, cropping, tilt, or shadows.
- Photo numbers are stable within the project, in CLI import order. Underlying
  owner-scoped uploads have separate generated asset IDs; layout JSON cannot
  provide a `src` filesystem path or relabel uploaded photos.
- Proposed Step 1 rule: each imported photo appears exactly once. Element IDs
  and `z_index` values are unique; ascending `z_index` renders back to front.
- Permit only documented fields. Reject supplied height, rotation, shadows,
  captions, non-neutral crop/pan/zoom, and image backgrounds with clear errors.
- Derived normalized height equals normalized width times canvas width divided
  by canvas height and by source-photo aspect ratio. Store it in resolved state.
- For pixels, round nonnegative normalized positions and width to nearest
  integer, with exact halves rounded upward. Derive pixel height from the rounded
  pixel width and oriented source aspect ratio using the same rounding rule.
  Validate both continuous geometry and final integer pixel bounds.
- Full-photo resizing may differ from the ideal aspect ratio by pixel rounding
  only. Never force the image into a separately chosen height or crop it.
- Starting limits: 2-6 photos/elements, 25 MiB maximum file size per photo,
  40 million decoded pixels per photo, and canvas dimensions 1-4096 pixels per
  axis. Reject a photo placement that rounds to zero pixels. The user accepted
  the image/canvas limits as a starting point, subject to reviewing the supplied
  sample images before implementation. Propose adjustments if those inputs
  require them; do not silently increase limits during Autopilot.

### Stored files

Illustrative hierarchy beneath `.collage-data`:

```text
users\local-dev\
    uploads\<asset-id>.<extension>
    projects\portrait-demo\
        project.json
        layouts\v0001.json
        renders\v0001.png
```

- `project.json`: format version, owner ID, project ID, ordered photo records
  (source image number, generated asset ID, imported path relative to the owner's
  data directory, original filename, oriented width and height), and nullable
  current layout version. For example, one photo record would look like:

  ```json
  {
    "source_image_id": 1,
    "asset_id": "<generated-asset-id>",
    "imported_path": "uploads\\<generated-asset-id>.jpg",
    "original_filename": "01_tower_bridge.jpg",
    "width": 1536,
    "height": 2048
  }
  ```

  The renderer resolves that imported path beneath
  `.collage-data\users\local-dev`, never from an arbitrary path in layout JSON.
  The stored path is generated and validated by project code and must remain
  inside that owner's uploads directory. The original source in `photos` remains
  untouched; subsequent renders use the imported working copy.
- `layouts\v0001.json`: accepted resolved layout with format/revision numbers,
  canvas, and elements including derived normalized height and exact pixel
  boxes. Pixel boxes are deterministic derived data validated against the
  source metadata, not separate design choices.
- New accepted imports get monotonically increasing layout versions. Keep
  accepted versions immutable. `project.json` is the current-version pointer;
  do not maintain a second independently mutable copy of current layout JSON.
- Prepare files before updating the current pointer. Failed imports/renders
  must not leave the project pointing at incomplete output. Document the
  single-writer assumption; do not build a database/transaction framework.
- No `conversation.json` is required until Step 2.

### Curated repository assets versus runtime state

- **Eligible for user-managed commits:** The supplied `photos` directory,
  `examples\portrait_9x16.json`, other deliberately curated working layout JSON,
  source code, tests, and documentation. Do not add blanket ignore rules for
  photos, image files, or JSON.
- **Ignore generated working state:** `.collage-data` (including imported photo
  copies, project metadata, saved runtime versions, and rendered previews), app
  environments, caches, and temporary test output.
- Keep synthetic automated-test inputs distinct from the user-supplied photos.
  The documented manual example may reference the curated `photos` inputs.
- If an experimented layout is worth keeping, retain its portable, hand-authored
  input form under `examples`, not an entire runtime project with generated
  asset IDs. No export/promote CLI command is needed for Step 1.
- Being eligible for a commit does not authorize Copilot to stage or commit it.
  All Git writes remain prohibited; the user reviews and commits independently.

## Draft acceptance criteria

1. A documented CLI workflow imports photos, accepts a supplied layout, and
   renders a PNG with exactly the requested canvas dimensions.
2. Tests cover square/non-square canvases, mixed photo aspect ratios, and EXIF
   orientation, checking full-image retention rather than merely file creation.
3. Known pixel positions/sizes and stacking match the JSON under an explicitly
   documented rounding rule. Define the rule in the final contract.
4. A new process can inspect a project's stable photo IDs and layout versions
   and render a saved version. Stacking order does not rename source photos.
5. Invalid/unsupported layouts, missing/corrupt photos, and resource-limit
   failures give clear errors without replacing the last accepted state.
6. CLI/tests need no Azure credentials, initialize no model clients, and make
   no service requests.
7. Leave reviewable edits, usage instructions, sample output locations, test
   outcomes, and retry-budget accounting.

Hand-authored layouts prove deterministic execution, not LLM design quality.

## Step 2 outline: separate approval required

- Add one Agent Framework layout agent using the existing keyless deployment.
- Request structured layouts; pass results through Step 1 validation/rendering.
- Persist real conversation turns linked to layout versions and rebuild context
  from project data across runs. Reuse sessions within a run, not as the only
  durable history.
- Evaluate generation and incremental edits with agreed photos/prompts.
- Agree input/output limits, timeouts, retry policy, maximum calls, and cost
  envelope before any paid experiment.
- No UI, Functions deployment, cloud storage integration, end-user login,
  hosted/multi-agent workflows, or visual editing in Phase 1.

## Autopilot guardrails

- **Initial implementation scope: Step 1 only.** No model integration, Agent
  Framework wiring, conversation persistence, or Step 2 experiment is included.
  Current permission is still limited to planning-document updates.
- **No Git writes:** No stage, commit, push, branch/ref changes, checkout, stash,
  reset, Git configuration changes, or other Git mutations. Read-only inspection
  is allowed. Ordinary file edits within the approved brief are allowed;
  leave the Git index/history for the user.
- **Retry budget:** Initial implementation/validation attempt plus at most two
  corrective retry cycles globally per approved step, not per command/error.
  Routine inspections and first-pass work are not retries. A cycle means a
  bounded correction and revalidation after failure; record cycles used.
- **Stop when exhausted:** Preserve work and report the blocker. Never reset
  the budget, weaken tests, expand scope, switch providers, increase limits,
  or bend the objective to obtain a passing result.
- **Step 1 service budget: zero.** No inference, token acquisition, Azure
  service calls/configuration, or execution of the live smoke tests. Dependency
  downloads after approved manifest changes are allowed; "offline" describes
  application/test execution, not package installation.
- Preserve unrelated/user-authored changes. No destructive cleanup or incidental
  changes to the smoke-test environment. No subagents/workflows needed.
- Approval for Step 1 never authorizes Step 2. Return to planning at that boundary
  or when a material unresolved design decision arises.

## Open decisions before implementation approval

- CLI commands/layout schema; pixel rounding and resource limits.
- Local data location and overwrite/version behavior.
- Exact app dependency manifest, package/test paths, and environment setup commands.

## Proposed todos

1. Refine scope and resolve open decisions together.
2. Finalize CLI, layout contract, limits, and persistence/version rules.
3. Obtain explicit Step 1 implementation approval.
4. Implement offline import, validation/geometry, rendering, persistence, and CLI.
5. Verify acceptance criteria and provide reviewable output without Git writes.
6. Review results before planning and authorizing Step 2.

## Implementation approval boundary

The discussion draft is now in the repository for user review. Further plan
refinement is allowed, but application code, dependencies, fixtures, and generated
outputs must wait for explicit Step 1 implementation approval. Keep the existing
blueprint and smoke-test code unchanged. Finishing Step 1 is a stop/review point,
not permission to continue into Step 2.

## Decisions confirmed during refinement

- Step 1 defers tilt and shadows and proves basic geometry first.
- Use Pillow for image inspection and rendering.
- Use editable example JSON rather than an automatic starter-layout algorithm.
- Copilot prepares the initial JSON; the user supplies the working input photos.
- The starter JSON uses a portrait 9:16 canvas (width:height). Automated tests
  still cover non-square and square geometry; additional demo layouts are not
  required.
- A new layout version becomes current only after validation and rendering both
  succeed. A failure preserves the previous accepted version.
- Start with 25 MiB/40-million-pixel photo limits and 4096 pixels per canvas axis;
  revisit with the user based on the provided sample images.
- Use a separate repository-level app package and environment, leaving the
  temporary smoke-test setup untouched.
- The user confirmed the simple 2x2 starter arrangement using all four supplied
  photos on the 9:16 canvas.
- Paths belong in project photo records; layout JSON uses stable photo IDs.
- The supplied photos and curated layout examples may be committed by the user;
  ignore generated working copies/state instead. No Git writes by Copilot.
- The first Autopilot implementation brief covers Step 1 only.

## Supplied working images (metadata inspected, files unchanged)

The user provided `photos` as the input directory. In order:

1. `01_tower_bridge.jpg`
2. `02_breakfast.jpg`
3. `03_london_eye.jpg`
4. `04_daunt_books.jpg`

All four are JPEGs, 1536x2048 (3:4), about 3.15 million pixels each, with
EXIF orientation 1; individual sizes are approximately 0.27-0.39 MiB.
No increase to the starting resource limits is needed for these inputs.
Use synthetic tests for aspect-ratio variety and EXIF transforms not present
in this set. Do not fetch or generate replacements for these working photos.
