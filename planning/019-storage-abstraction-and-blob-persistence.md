# 019: Storage abstraction and Blob persistence

**Status:** High-level direction only, not an implementation specification or
authorization. Granular briefs and approval will precede implementation.
019a is complete and closed following offline verification and user acceptance;
see [results](019a_results.md). Initial development
[infrastructure](../infra/README.md) has been deployed with separate approval;
019b's separately approved API-only implementation has offline evidence in
[results](019b_results.md), including its successful separately approved live
application proof and explicit user acceptance. 019b is complete and closed;
the user waived the manual repetition. [019c](019c-complete-web-persistence.md)
is complete and closed after offline verification, its separately approved
model-free real-account proof and successful user-led web testing with explicit
acceptance; see [019c results](019c_results.md).

## Goal and boundaries

Build on the completed [018 local workflow](018-local-conversation-and-preview.md)
and the [blueprint's persistence direction](001-project-blueprint.md#persistence-evolution):
separate durable storage from local filesystem assumptions without a generic
filesystem framework or wholesale agent rewrite.

**Success criterion:** Deploy a private single-owner collage application,
preserving offline CLI/replay and existing correctness safeguards.
General-purpose hosting, tenancy and scalability are not goals.

This is the overall delivery target, not deployment scope for 019 itself.
Reduce supported capabilities rather than security: authenticated, explicitly
permitted access and server-enforced workspace access remain required before
sharing. Keep 019a narrow and informed by a concrete Blob design, not speculative
extensibility.

| Workflow | Intended application storage |
|---|---|
| CLI/replay | Local filesystem; preserve offline operation. |
| Local Functions + web | Private Azure Blob Storage in a development account. |
| Deployed Functions + web | Private Azure Blob Storage in a separate account. |

Use developer identity for local backend access and managed identity when
deployed; keep service credentials out of the browser. Blob-backed local web
requires network access, with explicit failures rather than silent local fallback.
Azurite is not a prerequisite.

## Sequence and status

| Increment | Scope | Working outcome |
|---|---|---|
| [019a: Initial local extraction](019a-initial-local-storage-extraction.md) | Extract create/list/reopen/photo persistence behind a narrow storage boundary. Entirely offline. | Complete and closed following offline verification and the user's successful local smoke check. |
| [019b: Initial Blob integration](019b-blob-storage-implementation.md) | Implement and verify that same slice against the development Azure storage account through an opt-in API-only mode, using Azure CLI authentication. Do not extend into conversation editing yet. | Complete and closed after offline/real-account verification and explicit user acceptance, with the manual repeat waived. See [results](019b_results.md). The full conversational workflow is not yet cloud-ready. |
| [019c: Complete web persistence](019c-complete-web-persistence.md) | Extend the boundary and Blob implementation together across conversation state/history, proposals/previews, request records and source selections, including required concurrency safeguards. | Complete and closed after offline/real-account verification and successful user-led web testing with explicit acceptance; [results](019c_results.md). |
| 019d: Optional performance work | Measure the complete Blob-backed workflow and fix demonstrated bottlenecks. | Deferred and unapproved. Target: measured improvements without expanding product scope. |

The sequence is small local extraction, real Blob proof, then extension of both
together; do not abstract all persistence before testing Blob. CLI/replay retain
local storage throughout. 019b runs local Functions against Azure in an API-only
proof mode; 019c extends Blob support to the complete locally hosted web workflow.
Functions deployment and end-user authentication remain separate work.

Detailed boundaries remain subject to each brief's approval. Storage abstraction
is not itself a performance improvement or proof of cloud readiness.

## Guardrails

Preserve original photos, existing local projects/archives, deterministic
rendering and uncertain-outcome/no-automatic-paid-retry behavior. Temporary
local rendering files are acceptable; they are not authoritative Blob-backed
state. No automatic migration of existing projects.

Keep regression testing offline where possible; real-account integration
checks require explicit authorization and need not invoke models. This document
authorizes no Azure access/provisioning, installations, model calls or Git writes.

Deployment, end-user authentication/ownership enforcement, and new product
features remain outside 019. Authentication and ownership checks are required
before shared deployment.
