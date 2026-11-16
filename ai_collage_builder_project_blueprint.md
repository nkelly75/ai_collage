# AI Collage Builder — Project Blueprint & Architecture

## 1. Executive Summary & Vision

Traditional AI image generation tools (diffusion models) struggle with spatial layouts, precise text alignment, and strict image proportions because they render images as probabilities of pixels rather than structured objects. Conversely, rigid template apps (like PicCollage) trap users in inflexible grids where AI feels like a flaky bolt-on.

The **AI Collage Builder** solves this by adopting a **hybrid architecture**:
- **LLM as the "Spatial Designer":** Handles human intent, layout archetypes, and normalized percentage placement.
- **Deterministic Code as the "Brawn":** Uses Python (`Pillow`) to execute exact pixel math, aspect-ratio-safe cropping, rotations, drop shadows, and text rendering on original high-res assets.

---

## 2. System Requirements & V1 Scope Guardrails

### Core Functional Requirements
1. **Multi-Image Upload & Inspection (Capped at 6 Images for V1):** 
   - Accept $2 \le N \le 6$ user photos.
   - Extract metadata (width, height, aspect ratio, orientation) without passing expensive raw image binaries to a vision model.
2. **Natural Language Layout Engine (Normalized Coordinates):**
   - Translate plain text prompts into a structured layout JSON using **normalized decimal coordinates (`0.0` to `1.0`)** rather than raw pixels to eliminate LLM arithmetic errors.
   - Respect image aspect ratios (preventing tall portraits from being crammed into wide boxes).
3. **Layering, Overlap & Image Backgrounds:**
   - Support `z_index` stacking order so photos can intentionally overlap like a physical scrapbook.
   - Support either a solid color or a user-selected **background image** (rendered full-bleed with `cover` fit underneath all elements).
4. **Scrapbook Styling & Geometry:**
   - Support subtle tilt angles ($-10^\circ$ to $+10^\circ$) per image.
   - Expand element bounding boxes dynamically during rotation (`expand=True`) in Pillow so corners never clip.
   - Support optional drop shadows and localized text captions.
5. **Conversational Refinement:**
   - Maintain layout state across turns to handle incremental tweaks (e.g., *"Space them out more"*, *"Tilt the beach photo to the left"*).
6. **Pan & Zoom (Deferred to Graphical UI in V2):**
   - *Design Decision:* Panning and zooming inside an image frame will **not** be handled via natural language prompts. Crop/pan offsets (`crop_offset_x`, `crop_offset_y`, `zoom`) will be controlled via graphical drag handles in V2, which update the same JSON state.

---

## 3. System Architecture

```
┌─────────────────┐       1. Upload Images        ┌───────────────────────┐
│                 ├──────────────────────────────►│                       │
│  Client / Web   │                               │  Azure Blob Storage   │
│  (React / App)  │◄──────────────────────────────┤  (Uploads & Session)  │
│                 │   4. Fetch Output Image       └───────────▲───────────┘
└────────┬────────┘                                           │
         │                                                    │ 3. Read/Write
         │ 2. Submit Prompt & Session IDs                     │    Images & State
         ▼                                                    │
┌─────────────────────────────────────────────────────────────┴───────────┐
│                     Azure Function App (Python)                         │
│                                                                         │
│   ┌─────────────────────┐    Prompt & Metadata    ┌─────────────────┐   │
│   │  JSON State Manager ├────────────────────────►│ Azure AI Foundry│   │
│   └──────────┬──────────┘  (Text/JSON Only)       │ (GPT-4o-mini)   │   │
│              │                                    └────────┬────────┘   │
│              │ Updated Normalized JSON                     │ JSON Plan  │
│              ▼                                             ▼            │
│   ┌─────────────────────────────────────────────────────────────────┐   │
│   │                  Pillow Rendering Engine                        │   │
│   │   - In-memory processing via io.BytesIO()                       │   │
│   │   - Converts 0.0–1.0 decimals -> exact canvas pixels            │   │
│   │   - Draws background -> sorts by z_index -> rotates & pastes    │   │
│   └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Master Layout JSON Schema (Normalized)

The single source of truth (SSOT) passed between the backend, LLM, UI, and renderer:

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
        "width": { "type": "integer", "default": 1200 },
        "height": { "type": "integer", "default": 1200 },
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
          "id": { "type": "integer" },
          "type": { "type": "string", "enum": ["image", "text"] },
          "src": { "type": "string" },
          "box_normalized": {
            "type": "object",
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
            "description": "Used in V2 graphical editor for pan/zoom within frame",
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
        "required": ["id", "type", "box_normalized", "z_index"]
      }
    }
  },
  "required": ["version", "canvas", "elements"]
}
```

---

## 5. LLM System Prompt Strategy

To ensure reliable layout generation without pixel hallucinations:
- **Metadata-Only Input:** Pass only `{id, src, aspect_ratio, orientation}` to keep token counts and latency negligible.
- **Boundary Algebra:** Explicitly instruct the LLM to keep elements within `0.03 <= x`, `x + width <= 0.97` (unless full-bleed is requested).
- **Unified Create/Edit Loop:** Pass `current_layout: null` for initial creation, or pass the active JSON state for incremental edits.

---

## 6. Cloud Infrastructure & Azure Hosting Strategy

### Zero-Secret Serverless Architecture
- **Azure Functions (Python / Linux Consumption Plan):** Free-tier grants up to 1 million executions per month.
- **Azure Blob Storage:** Stores uploads, state JSONs, and rendered outputs without needing a database.
- **Azure AI Foundry (Serverless Pay-As-You-Go):** Deploy lightweight text models (`gpt-4o-mini` or `gpt-4.1-mini`). **Strictly avoid Provisioned Throughput Units (PTU)** to ensure $0.00 idle cost.
- **Security & IAM:** Authenticate using **System-Assigned Managed Identity** (`DefaultAzureCredential`) with `Storage Blob Data Contributor` RBAC role. **No connection strings or SAS tokens required.**

### Storage Path Conventions
```text
collages-container/
└── users/
    └── {user_id}/
        ├── uploads/
        │   ├── photo_1.jpg
        │   └── photo_2.jpg
        └── sessions/
            └── {session_id}/
                ├── current_state.json   <-- Current SSOT
                ├── v1_layout.json        <-- History (Undo support)
                ├── v2_layout.json
                └── output_latest.png     <-- Rendered preview
```

---

## 7. Phased Maturity Roadmap

```
  Phase 1: MVP Layout Engine (Local Python Script)
  ├── Metadata extractor (dimensions, aspect ratios, max 6 images)
  └── Pillow renderer: normalized decimals -> pixels, z_index sorting,
      background image/color support, rotation (expand=True), drop shadows

  Phase 2: LLM Integration & Azure Serverless Backend
  ├── Azure AI Foundry PAYG endpoint (gpt-4o-mini + Structured JSON Outputs)
  ├── Azure Function HTTP Endpoint + Managed Identity RBAC
  └── Stateless session & version management via Azure Blob Storage

  Phase 3: Conversational Refinement (V1 Release)
  ├── Iterative JSON modification ("Space them out", "Overlap top two")
  └── Version rollback (pointing current_state.json back to v1_layout.json)

  Phase 4: Hybrid Visual Editor (V2 Interactive Canvas)
  ├── Web UI (React + HTML5 Canvas / Konva)
  ├── Graphical corner dragging, rotation handles, and z-index layer toggles
  └── In-frame graphical Pan & Zoom controls updating `crop_pan` in JSON
```

---

## 8. Cost & Billing Guardrails

| Resource | Service Tier & Safeguard | Estimated Monthly Cost |
| :--- | :--- | :--- |
| **Compute** | Azure Functions (Consumption Plan — 1M free requests) | $0.00 |
| **Storage** | Azure Blob Storage (< 5 GB) | < $0.10 / month |
| **Security** | Azure Managed Identity | $0.00 |
| **LLM Inference** | Azure AI Foundry PAYG (`gpt-4o-mini`, metadata-only) | ~$0.05 / 1,000 layouts |
| **Billing Safety** | Azure Cost Management Budget Alert set at **$10.00** | Hard visibility cap |
| **Total** | | **< $0.50 / month** |