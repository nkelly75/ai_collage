# AI Collage Builder — Project Blueprint & Architecture

> **Historical snapshot:** Original product and architecture proposal, subsequently
> refined by implementation. The status, schema, roadmap, and estimates below
> describe that planning record, not the current engine contract. See the
> [planning index](README.md) for reconciliation and the
> [layout field guide](../docs/layout-format.md) for current syntax.

> **Status:** Working blueprint. Confirmed directions include Azure Functions and Azure Blob Storage, React + TypeScript + Vite, Microsoft Agent Framework for Python to organize LLM interactions, an early local proof of concept using a deployed Microsoft Foundry model, and backend-mediated image transfers. GPT-5.4 mini is the tentative starting model. Initial development is local and single-user; authentication and per-user isolation are required before sharing a cloud deployment. Final model selection, rendering-library choice, hosting-plan details, and cost estimates remain provisional.

## 1. Executive Summary & Vision

Traditional AI image generation tools (diffusion models) struggle with spatial layouts, precise text alignment, and strict image proportions because they render images as probabilities of pixels rather than structured objects. Conversely, rigid template apps (like PicCollage) trap users in inflexible grids where AI feels like a flaky bolt-on.

The **AI Collage Builder** solves this by adopting a **hybrid architecture**:
- **LLM as the "Spatial Designer":** Handles human intent, layout archetypes, and normalized percentage placement.
- **Deterministic Code as the "Brawn":** Executes exact pixel math, aspect-ratio-preserving photo placement, rotations, drop shadows, and text rendering on original high-res assets. LLM interactions use Microsoft Agent Framework for Python; `Pillow` remains the proposed rendering library, not a confirmed choice.

---

## 2. System Requirements & V1 Scope Guardrails

### Core Functional Requirements
1. **Multi-Image Upload & Inspection (Capped at 6 Images for V1):** 
   - Accept $2 \le N \le 6$ user photos.
   - Extract metadata (width, height, aspect ratio, orientation) without passing expensive raw image binaries to a vision model.
   - Show numbered thumbnails so users can refer to "image 1", "image 2", or "image 3" without the system understanding photo content.
   - Assign each source photo a stable numeric identifier, independent of placement, stacking order, or filename. Moving or removing another photo must not renumber it.
2. **Natural Language Layout Engine (Normalized Coordinates):**
   - Translate plain text prompts into a structured layout JSON using **normalized decimal coordinates (`0.0` to `1.0`) on both axes**, for square, landscape, and portrait canvases alike.
   - Offer canvas aspect-ratio options such as 16:9, 4:3, 3:2, square, and portrait equivalents, plus custom dimensions. Canvas width and height define its shape independently of the normalized coordinate ranges.
   - Horizontal positions and widths are fractions of canvas width; vertical positions and heights are fractions of canvas height. Equal normalized width and height do not imply a square photo frame on a non-square canvas.
   - Give the LLM the canvas dimensions/aspect ratio. Normalization makes placement resolution-independent but does not remove the need for deterministic geometry validation.
   - Initially, make each photo's frame match the source photo's aspect ratio: show the entire photo without cropping, distortion, or empty space inside its frame.
   - For image placement, choose position and one size dimension (for example, normalized width); derive the other dimension in code from the source photo's aspect ratio and canvas dimensions. The resolved JSON may retain both dimensions, but they are not independent choices.
3. **Layering, Overlap & Image Backgrounds:**
   - Support `z_index` stacking order so photos can intentionally overlap like a physical scrapbook.
   - Support either a solid color or a user-selected **background image** underneath all elements. Full-bleed `cover` fitting was an earlier proposal; background fitting remains to be discussed because it can crop a photo.
   - Overlap may obscure part of a photo even when the photo itself is not cropped. Rotation must leave enough room to keep the photo within the canvas; expanding an intermediate image alone does not ensure this.
4. **Scrapbook Styling & Geometry:**
   - Support subtle tilt angles ($-10^\circ$ to $+10^\circ$) per image.
   - Expand element bounding boxes dynamically during rotation (`expand=True`) in Pillow so corners never clip.
   - Support optional drop shadows and localized text captions.
5. **Conversational Refinement:**
   - Maintain layout state across turns to handle incremental tweaks (e.g., *"Space them out more"*, *"Tilt image 3 to the left"*, *"Make image 2 the largest"*).
6. **Pan & Zoom (Deferred to Graphical UI in V2):**
   - Initial photo frames follow source aspect ratios, so no cropping, panning, or zooming is needed.
   - The JSON already anticipates later in-frame editing through optional `crop_pan` fields (`offset_x`, `offset_y`, `zoom`). Initially omit this object or use neutral values: zoom `1.0`, offsets `0.0`.
   - Later, independently shaped frames could allow cropping, panning, and zooming within the frame. The existing proposal is to expose these through graphical controls rather than natural language; exact interaction details remain provisional.

### Initial UI and Frontend

- **Stack:** React + TypeScript + Vite. Next.js is not needed for the initial client-rendered application; Azure Functions supplies the target backend.
- **Initial controls:** Photo uploads with stable numbered thumbnails, canvas aspect-ratio selection, natural-language prompt entry, a rendered preview, and follow-up prompts against the current layout.
- **Preview:** Display the backend-rendered image rather than implementing a second layout renderer in the browser.
- **Deferred:** Drag handles, crop/pan/zoom controls, layer panels, and a polished visual editor.

### Collage Projects and Ownership

- A **collage project** is a persistent, user-owned workspace containing references to its selected photos, current layout, layout history, natural-language conversation history, and generated results. It is not a login session.
- Uploads and collage projects, including their layouts, conversations, and results, belong to a user.
- Initially use a fixed development-user identity while running locally. No end-user login is needed for this local-only proof of concept.
- Partition persisted data by owner from the start, including local files: use the same logical user/project hierarchy with a fixed identity such as `local-dev`, not an unowned shared data directory. This does not require implementing login or automatically mapping local data to a future signed-in account.
- Before sharing a deployment, require authenticated access and enforce ownership on every operation. Users must be able to access their own uploads, projects, and results, but not another user's.

---

## 3. System Architecture

### Local Proof of Concept

Prove the layout loop before investing in cloud backend deployment:

```text
Local Python runner (then minimal React UI + local backend)
    -> photos + metadata + prompt + current layout
    -> Agent Framework layout-design agent (metadata/state only)
    -> deployed Microsoft Foundry model (metadata/state only)
    -> layout JSON
    -> validation + derived frame dimensions
    -> local renderer
    -> preview image + updated layout
```

- Access to a deployed Foundry model is needed for this approach; a deployed Azure Function App is not.
- The Agent Framework code runs locally against that model endpoint. Using the framework does not require deploying a hosted Foundry Agent Service agent.
- Keep model interaction, layout validation, rendering, and project logic independent of the Functions entry point. Use a small local runner first, then expose the same logic through the minimal UI and local backend.
- Phase 1 uses command-line tooling, not a web UI: create a project from local image files and an initial prompt, refine an existing project with another prompt, inspect its history, and re-render a saved layout without another model call. Save layout JSON and preview image files for inspection in an ordinary image viewer.
- Commands must load and save the user-scoped project and conversation so refinement works across separate process runs. Exact command names and arguments remain to be designed.
- Functions can run locally before being deployed. Cloud storage deployment is not a prerequisite for the first layout experiment.
- Keep Foundry credentials and calls on the local backend/runner, never in the browser.

### Target Deployed Architecture

```text
React + TypeScript + Vite UI
    |
    | Authenticated API requests:
    | uploads, projects, prompts, previews, downloads
    v
Azure Functions
    |-- Verify user identity and resource ownership
    |-- Validate uploads and layout geometry
    |-- Manage projects, layout history, and rendering
    |
    |-- Agent Framework layout agent
    |       Metadata + state + prompt --> Microsoft Foundry
    |<----------------------------- Layout JSON
    |
    |-- Managed identity ----------> Private Azure Blob Storage
    |<----------------------------- Photos, project state, outputs
    |
    +-- Return project data and preview/download image bytes to UI
```

- **Uploads:** Browser -> Function -> private Blob Storage.
- **Generate/refine:** Browser -> Function -> Foundry -> validation/rendering -> private Blob Storage.
- **Preview/download:** Browser -> Function -> private stored output -> Function -> browser.
- Initially, the browser does not access Blob Storage directly or directly write stored layout state. Set explicit upload-byte and decoded-image-dimension limits; validate images before processing.
- **Optional later optimization:** The backend could authorize short-lived, blob-specific user delegation SAS URLs for direct image transfers. Restrict permissions to the operation, protect these bearer credentials, and validate direct uploads before processing. Storage CORS is not authorization. This optimization is not required initially.

---

## 4. Master Layout JSON Schema (Normalized)

The single source of truth (SSOT) for a project's layout, passed between the backend, LLM, UI, and renderer. Ownership and other project metadata are managed separately by the backend, not generated by the LLM.

### Coordinate, Sizing, and Identifier Semantics

- Both normalized axes always span `0.0` to `1.0`; landscape and portrait canvases do not use different coordinate ranges.
- On a 1600-by-900 canvas, a 450-by-450 square photo occupies `0.28125` of the canvas width and `0.5` of its height. Its unequal normalized dimensions preserve its square shape in pixels.
- For image elements, code derives height from the chosen width (or vice versa), accounting for both source-photo and canvas aspect ratios. Store the resulting unrotated frame dimensions in `box_normalized`; position is relative to the canvas, not the source image.
- Initially the frame has the source photo's aspect ratio, with the entire photo visible inside it. The optional `crop_pan` object reserves space for future editing, not permission to crop initial layouts. Future frame-fitting and pan/zoom semantics still need to be specified before enabling those features.
- `source_image_id` is the stable, user-visible upload number used in prompts such as "image 3". `id` identifies a layout element, and `z_index` controls stacking. Neither changes the source-photo number.
- `src` resolves the underlying asset; it is not the user-facing photo identifier. Each image element must reference an uploaded source photo. Multiple placements, if supported later, can have distinct element IDs while sharing a source-photo ID.

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CollageLayoutState",
  "type": "object",
  "properties": {
    "version": { "type": "integer" },
    "canvas": {
      "type": "object",
      "properties": {
        "width": { "type": "integer", "default": 1200, "description": "Canvas width in pixels; the default is not a square-only restriction" },
        "height": { "type": "integer", "default": 1200, "description": "Canvas height in pixels; may differ from width for landscape or portrait output" },
        "background": {
          "type": "object",
          "properties": {
            "type": { "type": "string", "enum": ["color", "image"] },
            "value": { "type": "string", "description": "Hex color code or blob src filename" }
          },
          "required": ["type", "value"]
        }
      },
      "required": ["width", "height", "background"]
    },
    "elements": {
      "type": "array",
      "maxItems": 6,
      "items": {
        "type": "object",
        "properties": {
          "id": { "type": "integer", "description": "Layout element identifier, independent of source-photo numbering and stacking" },
          "type": { "type": "string", "enum": ["image", "text"] },
          "source_image_id": { "type": "integer", "minimum": 1, "description": "Stable upload number used by the user, for example image 3" },
          "src": { "type": "string" },
          "box_normalized": {
            "type": "object",
            "description": "Unrotated frame: x and width are fractions of canvas width; y and height are fractions of canvas height. Initially image frames preserve source aspect ratio, with one size dimension derived in code.",
            "properties": {
              "x": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "y": { "type": "number", "minimum": 0.0, "maximum": 1.0 },
              "width": { "type": "number", "minimum": 0.05, "maximum": 1.0 },
              "height": { "type": "number", "minimum": 0.05, "maximum": 1.0 }
            },
            "required": ["x", "y", "width", "height"]
          },
          "crop_pan": {
            "type": "object",
            "description": "Reserved for future in-frame editing. Initially omit or use zoom 1.0 and zero offsets; show the entire source photo without cropping.",
            "properties": {
              "zoom": { "type": "number", "default": 1.0 },
              "offset_x": { "type": "number", "default": 0.0 },
              "offset_y": { "type": "number", "default": 0.0 }
            }
          },
          "rotation": { "type": "number", "minimum": -15.0, "maximum": 15.0 },
          "z_index": { "type": "integer", "minimum": 1 },
          "caption": {
            "type": "object",
            "properties": {
              "text": { "type": "string" },
              "font_size": { "type": "integer" },
              "color": { "type": "string" }
            }
          }
        },
        "required": ["id", "type", "box_normalized", "z_index"],
        "allOf": [
          {
            "if": {
              "properties": { "type": { "const": "image" } },
              "required": ["type"]
            },
            "then": { "required": ["source_image_id"] }
          }
        ]
      }
    }
  },
  "required": ["version", "canvas", "elements"]
}
```

---

## 5. LLM System Prompt Strategy

### Agent Framework and Tentative Model Choice

- **Framework:** Use [Microsoft Agent Framework for Python](https://learn.microsoft.com/en-us/agent-framework/agents/structured-outputs) for one layout-design agent handling both creation and refinement. Multi-agent orchestration, autonomous tool loops, and hosted agent deployment are not required.
- **Structured output:** Use a compatible chat client with a Pydantic model or JSON schema to request typed layout output. Keep the model-facing schema compatible with the selected provider's supported schema subset; application-level layout and geometry validation still runs in ordinary Python code.
- **Separation of responsibilities:** The framework organizes instructions, context, model invocation, and structured responses. Ordinary Python code owns project persistence, ownership checks, derived dimensions, geometry validation, and rendering.
- **Durable state:** Project files remain the authoritative conversation and layout record. Reconstruct framework session/context from project data across CLI runs rather than relying solely on framework-specific or provider-maintained session state.
- **Tentative starting model:** Evaluate [GPT-5.4 mini in Microsoft Foundry](https://ai.azure.com/catalog/models/gpt-5.4-mini) first. Prefer establishing useful compositions and reliable edits with a mini model before comparing cheaper options such as GPT-5.4 nano on the same sample projects. Neither is a final selection or an automatic fallback.
- **Deployment checks:** Before manual deployment, confirm model availability and quota in the intended subscription/region, pay-as-you-go pricing, and structured-output compatibility with the chosen Agent Framework client/API. Keep the deployment name configurable so comparisons do not require changes to layout logic.
- **Measure actual cost:** Record the deployed model/version, token usage (including reasoning usage where reported), and latency for generation attempts. Estimate cost from the selected deployment's pricing rather than carrying forward the original GPT-4o-mini estimate.

### Layout Instructions

To guide layout generation while leaving geometry validation to code:
- **Metadata-Only Input:** Pass source-photo metadata such as `{source_image_id, src, width, height, aspect_ratio, orientation}`, plus canvas dimensions/aspect ratio and current layout state. Visual understanding of photo content is not required.
- **Stable Photo References:** Resolve "image 3" through `source_image_id`, never through array position, layout element ID, or `z_index`. Do not assume knowledge of subjects such as "the sunset".
- **Aspect-Ratio-Safe Sizing:** Request position and one size dimension for each photo; derive the other dimension in code before storing the resolved frame. Preserve the entire photo without cropping in initial layouts.
- **Boundary Algebra:** Explicitly instruct the LLM to keep elements within `0.03 <= x`, `x + width <= 0.97` (unless full-bleed is requested).
- **Geometry Validation:** Validate bounds on both axes after deriving frame dimensions and accounting for rotation. Normalized coordinates alone do not guarantee a valid layout.
- **Unified Create/Edit Loop:** Pass `current_layout: null` for initial creation, or pass the active JSON state for incremental edits.

### Project Conversation History and Model Context

- **Persist the conversation:** Store an ordered project-level conversation record (illustratively `conversation.json`) alongside the layout history, including user prompts and model responses with roles and timestamps. Associate each generation attempt with its input layout version and, when successful, the resulting saved layout version.
- **Do not confuse history with state:** The current validated layout remains authoritative for what is on the canvas. Conversation history preserves intent and explains how the project reached that state; rejected or failed model responses must not become the current layout.
- **Build context explicitly:** For each model call, provide system instructions, source-photo metadata, canvas details, the current layout, relevant prior conversation turns, and the newest user message. A project can be resumed without relying on an in-memory process or a provider-maintained conversation session.
- **Bound the request, not the archive:** Short conversations can be sent in full. As they grow, select recent/relevant turns or include a summary of earlier intent to control context size and cost; retain the full stored history. Avoid resending every historical layout JSON when the current state and version references suffice.
- **Rollback:** Retain the conversation when selecting an earlier layout, record that selection, and supply the selected layout as current state on the next call so later messages do not imply that discarded edits are still active.

---

## 6. Cloud Infrastructure & Azure Hosting Strategy

### Confirmed Serverless Direction

- **Azure Functions:** Target Python backend for uploads, projects, layout generation/refinement, rendering, and image delivery, using Agent Framework for LLM interactions. Exact hosting plan remains to be selected.
- **Azure Blob Storage:** Private storage for uploads, project metadata, conversation and layout history, and rendered outputs. A separate database is not initially required.
- **Microsoft Foundry:** Use a deployed model from local development onward, tentatively GPT-5.4 mini subject to the checks in Section 5. Prefer pay-as-you-go rather than provisioned throughput for this low-volume application. The original GPT-4o-mini/GPT-4.1-mini suggestions are superseded as the starting recommendation.
- **Backend-to-service identity:** Use managed identity and least-privilege RBAC for deployed backend access to storage and the selected Foundry endpoint where supported. `DefaultAzureCredential` is the proposed Python credential mechanism, allowing an authorized developer identity locally and managed identity in Azure.
- **No browser service credentials:** Do not expose storage account keys, connection strings, or Foundry credentials in the frontend. The initial backend-proxy design does not require browser SAS tokens.

### Local Development and Future User Authentication

- **Local-only mode:** Assume one developer and use a fixed development-user identity as the ownership context. Defer login screens and Entra integration during the proof of concept. Local mode must not be exposed as a shared/public service.
- **Deployment gate:** The local authentication bypass must not be enabled in a shared deployment. Require authentication and ownership enforcement before making the application available to other users.
- **Future sign-in:** Support a Google/Gmail identity through Microsoft Entra. Choose the exact Entra offering, federation configuration, and application integration when preparing the authenticated deployment.
- **Authorization:** Derive the owner from a verified, stable identity mapping, not a browser-supplied user ID or email address. Check ownership for uploads, project listing/access, conversation and layout history, edits, and preview/download requests. Validate that asset references belong to the authorized user.
- **Isolation:** User-prefixed storage paths organize data but do not enforce access control on their own. Keep blobs private and enforce per-user access in the backend.
- **Separate concerns:** End-user authentication establishes who may access a collage project; managed identity authorizes the backend to access Azure services. One does not replace the other.

### Storage Path Conventions

Illustrative organization; `{user_id}` is the backend's owner identifier and `{project_id}` identifies a collage project, not a login session:

Apply this logical hierarchy to local persistence as well as Blob Storage, using the fixed development-user identifier locally. Conversation history is private project data with the same ownership rules as photos and outputs.

```text
collages-container/
└── users/
    └── {user_id}/
        ├── uploads/
        │   ├── photo_1.jpg
        │   └── photo_2.jpg
        └── projects/
            └── {project_id}/
                ├── project.json         <-- Project metadata and selected-photo references
                ├── conversation.json    <-- Ordered prompts/responses and layout-version references
                ├── current_state.json   <-- Current SSOT
                ├── v1_layout.json        <-- History (Undo support)
                ├── v2_layout.json
                └── output_latest.png     <-- Rendered preview
```

---

## 7. Phased Maturity Roadmap

### Phase 1: Local Layout Experiment

- Provide command-line create, refine, history inspection, and saved-layout rendering operations; no UI or local HTTP server is required.
- Extract source-photo metadata and stable identifiers; use one Agent Framework for Python layout-design agent from the local runner to call a deployed Foundry model, tentatively GPT-5.4 mini.
- Validate the JSON, derive aspect-ratio-safe dimensions, and render the composition locally.
- Persist user-partitioned projects, conversation history, layout versions, and previews locally so a later command can resume a project. Saved layouts can be re-rendered without a model call.
- Exercise the create/edit loop early, without a cloud Function App or end-user authentication.
- Evaluate visual quality, square/landscape/portrait canvases, mixed photo proportions, bounds/overlap, and whether targeted edits preserve unrelated choices. Valid structured JSON alone is not evidence of a good composition.

### Phase 2: Minimal Local UI

- Add the React + TypeScript + Vite interface: numbered uploads, canvas-shape selection, prompt entry, backend-rendered previews, and follow-up prompts.
- Reuse the local layout/rendering logic; introduce the local Functions wrapper without requiring cloud deployment.
- Expose the existing persistent projects and conversation/layout history through the UI; add rollback under the fixed development-user identity.
- Keep visual editing and polished UI work out of this phase.

### Phase 3: Authenticated Cloud Deployment

- Deploy Azure Functions and private Blob Storage with backend-mediated image transfers and backend managed identity.
- Integrate Entra-based sign-in with Google/Gmail support; disable the local authentication bypass.
- Enforce and verify per-user isolation for uploads, projects, conversation/layout history, and results before sharing access.
- Confirm upload limits, the hosting plan, model selection, and operational cost controls.

### Phase 4: Richer Visual Editing

- Add graphical movement/resizing, rotation handles, and layer controls.
- Introduce independently shaped frames and crop/pan/zoom controls updating the layout state.
- Choose any browser-canvas/editor library when needed; the earlier Konva suggestion is not a confirmed dependency.

---

## 8. Cost & Billing Guardrails

The remaining numeric figures below are unverified estimates from the original discussion, not confirmed pricing or a guaranteed monthly total. Recalculate for the selected hosting plan, model, region, usage, and future identity configuration before deployment. Local layout experiments still incur Foundry inference charges. The original GPT-4o-mini inference estimate and derived total no longer apply to the tentative GPT-5.4 mini choice.

| Resource | Service Tier & Safeguard | Estimated Monthly Cost |
| :--- | :--- | :--- |
| **Compute** | Azure Functions (Consumption Plan — 1M free requests) | $0.00 |
| **Storage** | Azure Blob Storage (< 5 GB) | < $0.10 / month |
| **Security** | Azure Managed Identity | $0.00 |
| **LLM Inference** | Microsoft Foundry PAYG (tentatively GPT-5.4 mini, metadata-only) | To be measured using deployment pricing and actual usage |
| **Billing Safety** | Proposed Azure Cost Management budget alert at **$10.00** | Notification only; not a hard spending cap |
| **Total** | | To be recalculated after model/hosting selection and usage measurements |