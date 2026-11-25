# AI Collage Builder — Project Blueprint & Architecture

> **Living blueprint:** Product vision, major architectural boundaries, and broad
> sequencing. Current implementation status, approved work, and execution evidence
> are tracked in the [planning index](README.md). Update this blueprint when the
> direction changes, not for incremental progress or individual phase outcomes.

> **Direction:** Build on the existing Python engine and metadata-only conversational
> agent with a local React + TypeScript + Vite UI and thin Python Azure Functions
> endpoints. Begin with conversation and backend-rendered previews using local
> directories. Private Blob Storage, authenticated sharing, and Azure deployment
> follow separately; vision and graphical editing remain future capabilities.

## 1. Executive Summary & Vision

Traditional AI image generation tools (diffusion models) struggle with spatial layouts, precise text alignment, and strict image proportions because they render images as probabilities of pixels rather than structured objects. Conversely, rigid template apps (like PicCollage) trap users in inflexible grids where AI feels like a flaky bolt-on.

The **AI Collage Builder** solves this by adopting a **hybrid architecture**:
- **LLM as the "Spatial Designer":** Handles human intent, layout archetypes, and normalized percentage placement.
- **Deterministic Code as the "Brawn":** Executes pixel geometry, aspect-ratio-preserving photo placement, borders, rounded corners, and rotations on original high-res assets using Pillow. LLM interactions use Microsoft Agent Framework for Python. Drop shadows and captions remain possible additions, not implemented features.

---

## 2. System Requirements & V1 Scope Guardrails

### Core Functional Requirements
1. **Multi-Image Upload & Inspection (Capped at 6 Images for V1):** 
   - Accept 2-6 user photos.
   - Extract metadata (width, height, aspect ratio, orientation) without passing expensive raw image binaries to a vision model.
   - Show numbered thumbnails so users can refer to "image 1", "image 2", or "image 3" without the system understanding photo content.
   - Assign each source photo a stable numeric identifier, independent of placement, stacking order, or filename. Photo removal/replacement is outside the initial web slice.
2. **Natural Language Layout Engine (Normalized Coordinates):**
   - Translate plain text prompts into a structured layout JSON using **normalized decimal coordinates (`0.0` to `1.0`) on both axes**, for square, landscape, and portrait canvases alike.
   - Offer canvas aspect-ratio options such as 16:9, 4:3, 3:2, square, and portrait equivalents, plus custom dimensions. Canvas width and height define its shape independently of the normalized coordinate ranges.
   - Horizontal positions and widths are fractions of canvas width; vertical positions and heights are fractions of canvas height. Equal normalized width and height do not imply a square photo frame on a non-square canvas.
   - Give the LLM the canvas dimensions/aspect ratio. Normalization makes placement resolution-independent but does not remove the need for deterministic geometry validation.
   - Preserve whole photos by default. Existing explicit cover frames also support crop-to-fill, pan, and zoom without stretching.
   - In whole-photo mode, choose position and width; derive height in code from the source aspect ratio and border rules. Cover frames have independent width and height.
3. **Layering, Overlap & Image Backgrounds:**
   - Use a back-to-front layer array so photos can intentionally overlap like a physical scrapbook.
   - Support a solid background; an ordinary lowest photo layer can provide a full-canvas image background, with explicit cover fitting where needed.
   - Overlap may obscure part of a photo even when the photo itself is not cropped. Rotation must leave enough room to keep the photo within the canvas; expanding an intermediate image alone does not ensure this.
4. **Scrapbook Styling & Geometry:**
   - Support subtle tilt angles (-10 to +10 degrees) per image, outside borders, and rounded corners.
   - Validate the complete rotated frame and sampled footprint against the canvas; do not silently move, shrink, or crop an invalid layout in the renderer.
   - Defer drop shadows and localized text captions.
5. **Conversational Refinement:**
   - Maintain layout state across turns to handle incremental tweaks (e.g., *"Space them out more"*, *"Tilt image 3 to the left"*, *"Make image 2 the largest"*).
   - Reuse clarification, remembered photo names, proposal navigation, and explicit acceptance rather than designing a separate web conversation model.
6. **Pan & Zoom:**
   - Existing cover-mode recipes support cropping, panning, and zooming. These are not dependent on a graphical editor.
   - Dedicated graphical controls remain deferred; the first UI focuses on prompts and previews.

### Initial UI and Frontend

- **Stack:** React + TypeScript + Vite. Next.js is not needed for the initial client-rendered application; Azure Functions supplies the target backend.
- **Initial controls:** Photo uploads with stable numbered thumbnails, canvas aspect-ratio selection, natural-language prompt entry, a rendered preview, and follow-up prompts against the current layout.
- **Conversation history:** Show messages, clarification questions, and proposal thumbnails. A "Continue from here" action selects a proposal as the editing baseline without deleting later history; explicit acceptance remains a separate action. Selecting an older proposal does not roll back remembered names.
- **Progress:** Distinguish understanding the request from creating the layout, with clear busy, error, and recovery states.
- **Preview:** Display the backend-rendered image rather than implementing a second layout renderer in the browser.
- **Deferred:** Drag handles, crop/pan/zoom controls, layer panels, and a polished visual editor.
- **Tooling:** Start with the frontend and Functions development tools needed for the slice. Aspire is optional, not an initial dependency; reconsider orchestration if managing local services becomes troublesome.

### Collage Projects and Ownership

- A **collage project** is a persistent, user-owned workspace containing references to its selected photos, current layout, layout history, natural-language conversation history, and generated results. It is not a login session.
- Uploads and collage projects, including their layouts, conversations, and results, belong to a user.
- Initially use a fixed development-user identity while running locally. No end-user login is needed for this local-only proof of concept.
- Partition persisted data by owner from the start, including local files: use the same logical user/project hierarchy with a fixed identity such as `local-dev`, not an unowned shared data directory. This does not require implementing login or automatically mapping local data to a future signed-in account.
- Before sharing a deployment, require authenticated access and enforce ownership on every operation. Users must be able to access their own uploads, projects, and results, but not another user's.
- Projects have one owner; collaborative editing and conflict-resolution UX are not requirements. Reject overlapping project mutations on the backend, including requests from multiple tabs, rather than relying only on disabled UI controls.

---

## 3. System Architecture

### Local Conversation-and-Preview Experience

Expose the existing capabilities through a usable local slice before investing
in cloud deployment or richer model capabilities:

```text
React + TypeScript + Vite UI
    -> local Python Azure Functions endpoints
    -> existing interpretation, layout generation, validation, and rendering
    -> local project directories
    -> conversation history + proposal previews

Model stages -> deployed Microsoft Foundry model (metadata/state only)
```

- Live interpretation/generation uses the deployed Foundry model; a deployed Azure Function App is not required. Controlled responses support offline UI/API development without model calls.
- The Agent Framework code runs locally against that model endpoint. Using the framework does not require deploying a hosted Foundry Agent Service agent.
- Keep Functions as HTTP adapters over ordinary Python capabilities, not a second implementation. The CLI and replay tooling remain useful entry points for offline work and future model evaluation.
- Load persistent project/conversation state across requests and process restarts; do not make a running Function worker the sole owner of state.
- Start with enough storage work to support this slice. Local directories are acceptable; Blob Storage implementation and emulation are not prerequisites.
- Keep Foundry credentials and calls on the local backend/runner, never in the browser.

### Split Interpretation and Layout Requests

- Use separate UI/API calls for interpretation and layout generation, making stage progress visible and giving each stage its own bounded HTTP time budget.
- Interpretation may finish with a clarification or a non-layout action. Only layout-producing requests need the second call.
- Keep validated intent on the server; the second call references that prepared operation rather than trusting browser-supplied intent.
- Reject stale prepared operations if project state changed between calls, and guard against duplicate execution as well as overlapping mutations.
- Keep each call comfortably below the Azure HTTP response limit, with headroom for validation, rendering, storage, and response delivery. Choose exact deadlines during the implementation brief; do not simply carry forward independent CLI stage limits.
- No Durable Functions or background job system initially. Do not automatically retry paid operations from the browser; support reloading saved state after an uncertain response.

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
- **Upload performance and priority:** Keep Function-mediated uploads for the
  expected one/two-user use. They add buffering, memory use and storage-transfer
  work; measure hosted behavior before optimizing. Local success does not
  establish Internet upload performance. Direct uploads are not a short-term
  priority.
- **Optional later optimization:** The backend could authorize direct Blob
  uploads using short-lived, blob-specific [user delegation SAS URLs](https://learn.microsoft.com/en-us/azure/storage/common/storage-sas-overview#when-to-use-a-shared-access-signature).
  This removes the Function from the bulk-transfer path and can support
  chunked uploads and per-file retries, at the cost of more upload-lifecycle
  logic. Authenticate/authorize upload grants, use private storage and HTTPS,
  restrict permissions and protect these bearer credentials. Enforce quotas,
  clean up abandoned uploads, and validate file bytes/decoded dimensions before
  publishing a project; bind publication to the validated immutable bytes, not
  a still-writable upload. Storage CORS is not authorization.

---

## 4. Layout Contract (Normalized)

The authored recipe is shared by the backend, model, and renderer. Ownership,
asset paths, conversation state, and execution details belong outside it.
The [layout field guide](../docs/layout-format.md) and generated
[JSON Schema](../docs/layout.schema.json) define the current contract; this
blueprint does not maintain a second schema.

- Both normalized axes span `0.0` to `1.0`; canvas dimensions determine the aspect ratio. Equal normalized width and height need not describe a square in pixels.
- Recipes use centre-anchored positions, stable `photo_id` values, and back-to-front `layers`, not filenames or array positions as photo identities.
- Whole-photo height is derived from width and source proportions; cover frames explicitly permit cropping and independent dimensions.
- Saved snapshots separate authored recipes from derived geometry. Rendering preserves originals and validates the complete frame, including rotation and sampling.

---

## 5. LLM System Prompt Strategy

### Agent Framework and Model Choice

- **Framework:** Use [Microsoft Agent Framework for Python](https://learn.microsoft.com/en-us/agent-framework/agents/structured-outputs) for the existing interpretation and layout-generation stages. Both support creation and refinement; multi-agent orchestration and hosted agent deployment are not required.
- **Structured output:** Use a compatible chat client with a Pydantic model or JSON schema to request typed layout output. Keep the model-facing schema compatible with the selected provider's supported schema subset; application-level layout and geometry validation still runs in ordinary Python code.
- **Separation of responsibilities:** The framework organizes instructions, context, model invocation, and structured responses. Ordinary Python code owns project persistence, ownership checks, derived dimensions, geometry validation, and rendering.
- **Durable state:** Project files remain the authoritative conversation and layout record. Reconstruct framework session/context from project data across CLI runs rather than relying solely on framework-specific or provider-maintained session state.
- **Model direction:** Retain the existing GPT-5.4 mini deployment as the baseline, not a permanent model commitment. Future comparisons should use bounded replay and human evaluation rather than block the first web experience.
- **Deployment checks:** Before manual deployment, confirm model availability and quota in the intended subscription/region, pay-as-you-go pricing, and structured-output compatibility with the chosen Agent Framework client/API. Keep the deployment name configurable so comparisons do not require changes to layout logic.
- **Measure actual cost:** Record the deployed model/version, token usage (including reasoning usage where reported), and latency for generation attempts. Estimate cost from the selected deployment's pricing rather than carrying forward the original GPT-4o-mini estimate.

### Layout Instructions

To guide layout generation while leaving geometry validation to code:
- **Metadata-Only Input:** Pass stable photo numbers, dimensions/aspect ratios, canvas details, and relevant project state. Visual understanding of photo content is not required.
- **Stable Photo References:** Resolve "image 3" through `photo_id`, never through array position or stacking order. User-taught names supplement numbers; do not infer photo contents.
- **Aspect-Ratio-Safe Sizing:** Use the existing whole/cover contract, preserving whole photos unless cropping is requested.
- **Geometry Validation:** Validate bounds on both axes after deriving frame dimensions and accounting for rotation. Normalized coordinates alone do not guarantee a valid layout.
- **Create/Edit State:** Supply the selected editing baseline and validated intent, distinguishing a fresh arrangement from an incremental edit.

### Project Conversation History and Model Context

- **Persist the conversation:** Store an ordered project-level conversation record (illustratively `conversation.json`) alongside the layout history, including user prompts and model responses with roles and timestamps. Associate each generation attempt with its input layout version and, when successful, the resulting saved layout version.
- **Do not confuse history with state:** The current validated layout remains authoritative for what is on the canvas. Conversation history preserves intent and explains how the project reached that state; rejected or failed model responses must not become the current layout.
- **Build context explicitly:** For each model call, provide system instructions, source-photo metadata, canvas details, the current layout, relevant prior conversation turns, and the newest user message. A project can be resumed without relying on an in-memory process or a provider-maintained conversation session.
- **Bound the request, not the archive:** Short conversations can be sent in full. As they grow, select recent/relevant turns or include a summary of earlier intent to control context size and cost; retain the full stored history. Avoid resending every historical layout JSON when the current state and version references suffice.
- **Navigation:** Retain the conversation and later proposals when selecting an earlier layout, record that selection, and use it as the editing baseline on the next call. Photo-name memory does not roll back with proposal selection.

### Deferred Vision Capabilities

Vision is not a prerequisite for the local UI. A promising later increment is
an explicit preview review combined with human feedback, rather than automatic
critique on every edit. Source-photo labels and subject regions remain possible
follow-ups where they solve demonstrated problems. Observations are advisory;
original photos and deterministic validation remain authoritative.

Image-bearing calls require separate consent, privacy review, and bounded
evaluation. No hidden vision calls on import, and no broad image-analysis
pipeline or automated aesthetic scoring as part of the first web slice.

---

## 6. Cloud Infrastructure & Azure Hosting Strategy

### Target Serverless Direction

- **Azure Functions:** Target Python backend for uploads, projects, layout generation/refinement, rendering, and image delivery, using Agent Framework for LLM interactions. Exact hosting plan remains to be selected.
- **Frontend hosting (tentative):** Azure Static Web Apps is a candidate for the Vite static build; Storage static website hosting is an alternative. SWA's integrated API proxy has a [45-second request limit](https://learn.microsoft.com/en-us/azure/static-web-apps/apis-overview), so initially plan for a configurable API address and direct Functions calls, allowing only intended UI origins through CORS. Authentication remains a separate requirement before sharing. Sibling UI/API subdomains would still be different browser origins; a shared-origin gateway is optional. Defer custom domains, HTTPS/SPA delivery details, Front Door, and API Management until deployment planning; any future proxy must accommodate model-stage durations and route API calls without SWA's shorter limit. Use Vite locally; no SWA or gateway tooling is required for 018a.
- **SPA routing (deployment requirement):** Serve `index.html` for client-side page routes such as `/projects/<id>` so direct visits and refreshes work. For SWA, configure [navigation fallback](https://learn.microsoft.com/en-us/azure/static-web-apps/configuration#fallback-routes); keep missing assets and API requests out of the HTML fallback. Verify direct project links and refreshes when hosting is implemented. This is routing, not project persistence; configuration remains deferred.
- **Azure Blob Storage:** Private storage for uploads, project metadata, conversation and layout history, and rendered outputs. A separate database is not initially required.
- **Microsoft Foundry:** Retain the existing deployment for authorized live requests. Prefer pay-as-you-go rather than provisioned throughput for this low-volume application; offline development and rendering must remain possible.
- **Backend-to-service identity:** Use managed identity and least-privilege RBAC for deployed backend access to storage and the selected Foundry endpoint where supported. `DefaultAzureCredential` is the proposed Python credential mechanism, allowing an authorized developer identity locally and managed identity in Azure.
- **No browser service credentials:** Do not expose storage account keys, connection strings, or Foundry credentials in the frontend. The initial backend-proxy design does not require browser SAS tokens.
- **Deployment tooling:** Bicep and PowerShell are the tentative automation approach. Defer infrastructure implementation and frontend hosting selection until the local slice clarifies requirements.

### Local Development and Future User Authentication

- **Local-only mode:** Assume one developer and use a fixed development-user identity as the ownership context. Defer login screens and Entra integration during the proof of concept. Local mode must not be exposed as a shared/public service.
- **Deployment gate:** The local authentication bypass must not be enabled in a shared deployment. Require authentication and ownership enforcement before making the application available to other users.
- **Future sign-in:** Support Google/Gmail sign-in without app-managed passwords, initially for explicitly permitted users. Microsoft Entra External ID is the customer-identity candidate; compare it with workforce-tenant guest access for a small invited pilot before selecting the tenant and integration. Do not start a new Azure AD B2C setup.
- **Authorization:** Derive the owner from a verified, stable identity mapping, not a browser-supplied user ID or email address. Check ownership for uploads, project listing/access, conversation and layout history, edits, and preview/download requests. Validate that asset references belong to the authorized user.
- **Isolation:** User-prefixed storage paths organize data but do not enforce access control on their own. Keep blobs private and enforce per-user access in the backend.
- **Separate concerns:** End-user authentication establishes who may access a collage project; managed identity authorizes the backend to access Azure services. One does not replace the other.

### Persistence Evolution

- **First slice:** Retain local owner/project directories and existing durable history. Keep photos, project state, conversation, names, proposals, accepted layouts, and previews separate from replay/assessment evidence; inspect apparently unused directories before removing anything.
- **Application boundary:** Keep storage decisions out of HTTP handlers and UI code. Introduce only the project/artifact operations needed by the slice, not a general filesystem abstraction or a wholesale storage rewrite.
- **Before cloud sharing:** Implement private Blob-backed persistence with safe publication, revision checks, and a cross-instance project mutation guard. Local file replacement/rename semantics do not automatically transfer to blobs; Function-local disk is not durable shared storage.
- **Local workflows:** Preserve local-directory operation for the CLI and replay tooling. The UI can replace CLI-led human trials without making offline regression or replay obsolete.
- **Emulation:** Reconsider Azurite when implementing/testing the Blob path. It is an option, not an initial Functions prerequisite.
- **Tracking:** The next implementation tracker must carry Blob persistence and cloud-safe mutation/publication semantics as explicit follow-up work, not describe local-directory support as cloud readiness.

---

## 7. Phased Maturity Roadmap

These are broad product stages, not approval of implementation or service calls.
Numbered implementation records subdivide them without requiring blueprint
updates for each step.

### Phase 1: Local Engine and Conversational Foundation

- Build on the existing deterministic engine, durable proposals, conversational refinement, and evaluation tooling.
- Keep offline rendering/regression and bounded live evaluation distinct. This foundation supports the next UI increment, not a claim of general language reliability.

### Phase 2: Minimal Local UI

- Add the React + TypeScript + Vite interface: numbered uploads, canvas-shape selection, prompt entry, backend-rendered previews, and follow-up prompts.
- Reuse the local layout/rendering logic; introduce the local Functions wrapper without requiring cloud deployment.
- Show conversation history and proposal thumbnails, with "Continue from here" distinct from acceptance, under the fixed development-user identity.
- Split interpretation and generation with server-held validated intent and visible stage progress. Include the small backend mutation guard and enough local persistence work to support the slice.
- Deliver bite-sized increments rather than build the whole API first. A frontend skeleton with controlled responses and a tooling check is a possible first increment; the implementation brief will select the breakdown.
- Keep visual editing and polished UI work out of this phase.

### Phase 3: Authenticated Cloud Deployment

- Deploy Azure Functions and private Blob Storage with backend-mediated image transfers and backend managed identity.
- Integrate Entra-based sign-in with Google/Gmail support; disable the local authentication bypass.
- Enforce and verify per-user isolation for uploads, projects, conversation/layout history, and results before sharing access.
- Confirm upload limits, the hosting plan, model selection, and operational cost controls.
- Complete the tracked persistence follow-up before sharing; verify safe publication and ownership isolation rather than assuming a change of storage root is sufficient.

### Phase 4: Richer Visual Editing

- Add graphical movement/resizing, rotation handles, and layer controls.
- Add graphical controls for the existing independently shaped frames and crop/pan/zoom capabilities.
- Choose any browser-canvas/editor library when needed; the earlier Konva suggestion is not a confirmed dependency.
- Vision may be selected separately when user feedback identifies a useful bounded experiment; it need not precede the UI or follow a fixed editing roadmap.

---

## 8. Cost & Billing Guardrails

Recalculate costs for the selected hosting plan, model, region, usage, and
identity configuration before deployment. Local live requests still incur
Foundry inference charges; local Functions do not make those calls free.
Do not treat free allowances or budget alerts as spending caps.

| Resource | Service Tier & Safeguard | Estimated Monthly Cost |
| :--- | :--- | :--- |
| **Compute and frontend** | Functions hosting plan and static frontend hosting to be selected | To be estimated |
| **Storage and identity** | Private Blob Storage, requests/transfers, and chosen Entra configuration | To be estimated |
| **LLM Inference** | Microsoft Foundry PAYG, initially the existing metadata-only model | Use deployment pricing and actual usage |
| **Billing Safety** | Proposed Azure Cost Management budget alert at **$10.00** | Notification only; not a hard spending cap |
| **Total** | | To be recalculated after model/hosting selection and usage measurements |