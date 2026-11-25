# 018d: Behavior-preserving stage extraction

**Status:** Complete and closed with the user's acceptance on 2026-11-25;
see [results and limits](018d_results.md). The offline gate and bounded live
pass are finished; their unused allowance is closed. 018e remains unapproved.
This brief follows the closed
[018c](018c_results.md); the [018 tracker](018-local-conversation-and-preview.md)
retains the tentative sequence through 018g.

## Outcome and scope

Expose interpretation and generation as separately callable capabilities of
the existing Python agent, while keeping `Conversation.request()` as the
ordinary composed operation used by CLI chat and replay. Establish a verified
backend baseline before returning to Functions/UI work in 018e.

This is one implementation with two ways to drive it, not parallel old/new
agents or a compatibility shim:

```text
CLI / replay -> Conversation.request()
                    |
                    v
               interpretation -> generation, only when needed
                    ^                  ^
                    |                  |
             separately callable shared stages
```

In scope: the stage interface, explicit handoff state, behavior-preserving
extraction, focused offline coverage, full offline Python regression, and the
bounded post-extraction live replay pass in the same coordinated run.

Out of scope: Functions endpoints, browser changes, durable web-operation
records/IDs, HTTP-specific deadlines, new concurrency infrastructure, Blob,
deployment, authentication, background jobs and any new conversation feature.
Do not tune prompts, reference resolution, retry policy or composition quality
as part of this refactor.

## Existing seams and preservation contract

Start with [conversation handling](../ai_collage/agent/conversation.py),
[agent models](../ai_collage/agent/models.py) and
[request accounting](../ai_collage/agent/requests.py). The current request loop
already switches stages, records validated intent and publishes proposals
through existing helpers, but carries request-local bookkeeping in local
variables and instance attributes.

The existing consumers remain [CLI chat](../ai_collage/cli/chat.py) and
[replay](../ai_collage/evaluation/replay.py). Keep their composed request
interface and ordinary experience; do not make either consumer manage web
operation tokens, call HTTP endpoints or persist a second request workflow.

| Area | Preserve |
|---|---|
| Entry points | Existing CLI/replay commands, flags, `Conversation.request()` arguments/result kinds, model-client interface and progress notifications. |
| Model-facing behavior | Prompt/instruction files, layout guide/schema, stage contexts and feedback, reasoning defaults and explicit overrides. Interpretation remains high; generation remains low by default. |
| Outcomes | Questions, naming confirmations, acknowledgements and selection can finish without generation. Layout-producing outcomes use existing validation, rendering and publication. |
| State | Task/source identity, original requests and clarification continuity, automatic naming and conflict confirmation, baseline/accepted-version distinctions and proposal numbering. |
| History and evidence | Existing record formats, meaningful event order/content, request logs, replay reports/resume/assessment behavior, and original photo bytes. No extra event merely because stages are called separately. |
| Limits and failures | At most four model calls per composed attempt, with at most two interpretation attempts; generation shares the remaining allowance. Existing validation-correction behavior, explicit failures and timeout recovery remain intact. |
| Deadlines | Interpretation keeps its existing 120-second stage budget; generation keeps 180 seconds. Corrections share their stage's deadline rather than renewing it. |

No existing saved-format change is planned, and this work does not require a
layout-format bump. If preservation proves to require a contract change, stop
and explain it for review rather than silently changing records, weakening
assertions or introducing a migration/dual path.

## Stage interface and handoff

Use the smallest typed interface that expresses:

- Interpretation returns either an existing final `RequestResult`, or a typed
  prepared-generation value.
- Generation consumes that value and the ordinary model/request dependencies,
  returning the existing proposal result through the existing publication path.
- `Conversation.request()` composes these same operations and returns early
  when interpretation has completed the user's request without generation.

Choose names consistent with the existing module; no generic workflow engine,
provider abstraction or HTTP terminology is needed in the core.

The prepared value must carry, or verifiably identify in existing records,
everything generation previously inherited from the running request. Include
validated intent, project/photo identity, the post-interpretation state/source,
original prompt/task information, request-start boundary and the correction
allowance already consumed. Do not infer the logical correction count solely
from provider-attempt files: preflight failures and controlled clients are not
interchangeable with completed model dispatches.

Make the handoff strict, data-only and JSON-round-trippable. A new
`Conversation` and `RequestLog` must be able to continue it without retaining
the original conversation object, client, callback or process-local attributes.
Do not serialize live clients, open files, locks or monotonic-clock deadlines.
The generation deadline begins when generation starts, as it does today;
the stage split must not renew correction/call allowances or reinterpret the
same prompt.

Validate project/state/source binding before another model call or mutation.
Reject a handoff for another project or one made stale by intervening state,
including sequential reuse after publication. Do not replay interpretation
events or naming updates during continuation. Preserve the existing semantic
effects of interpretation: it may already have saved names or an intent, so
this is not a new all-or-nothing transaction across both stages.

This handoff is an internal backend contract, not authority to trust
browser-supplied intent. Durable operation storage, identifiers, atomic
execution claims, concurrent-request guards and uncertain HTTP outcomes belong
in 018e. Do not add a persistent web-operation record to ordinary CLI projects
to implement this extraction.

## Implementation boundaries

Keep changes principally in `agent\conversation.py` and the small related
types/helpers it actually needs. Change `agent\requests.py` only where needed
to preserve existing accounting/deadline behavior. Reuse the current
interpretation, naming, context, validation and publication helpers.

CLI/replay callers should continue using the composed operation. Any necessary
caller adjustment must be mechanical and explained, not a feature redesign.
Avoid unrelated file moves, a broad module rewrite or engine/storage changes.
No new dependency, installation, environment change or toolchain is expected.
If one appears necessary, hand off the exact issue before proceeding.

After implementation, update the [architecture map](../architecture.md) and
directly affected current documentation to describe the actual interface.
Keep existing LESSONS references valid; propose any new lesson separately.

## Offline verification gate

Use generated photos and fresh temporary roots, block external network access,
and reuse existing controlled model clients/fixtures. No credentials or model
service are needed for this gate.

Before extraction, establish the relevant existing agent/replay baseline and
capture focused expectations where needed. Existing assertions are the anchor:
comparing two newly refactored paths alone could bless the same defect twice.
Do not regenerate expectations just to make the refactor pass.

Exercise composed and split execution with identical controlled responses.
Round-trip the handoff through JSON and reconstruct the conversation/request
objects between stages; include a focused fresh-process continuation case.
Compare semantic contexts, results, histories, names, sources, accepted versions,
request/correction accounting and deterministic recipes/previews. Normalize
only genuinely incidental differences such as temporary root paths and timing,
not IDs, event order, references or model-facing content.

| Focused case | Required evidence |
|---|---|
| Fresh proposal and edit | Same interpreted action, generation context, rendered result, publication and baseline through composed/split execution. |
| Non-generation outcomes | Clarification, naming confirmation, acknowledgement and exact selection return directly, with no generation call or fabricated proposal. |
| Continued work | Identity answers, naming receipt decisions and timeout continuation retain the original task/source and perform memory changes only once. |
| Corrections and accounting | Invalid interpretation/generation replies retain the existing shared four-call ceiling, interpretation ceiling, stage deadlines, reasoning and outer call-budget enforcement. |
| Bound handoff | Fresh-object/process continuation works; wrong-project, changed-state/source and already-used handoffs fail before a model call without modifying the saved project. |
| Failures and replay | Preflight, timeout and publication failures remain explicit; saved state, request logs, replay resume and offline assessment retain their existing meaning. |

Add a few focused cases in existing agent tests or one focused stage-extraction
test module; do not duplicate the whole agent suite or add a new test framework.
Once focused checks pass, run both existing Python suites from the checkout:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\api\.venv\Scripts\python.exe -m pytest -q -c .\api\pytest.ini .\tests\api
```

The API suite is an unchanged-consumer regression, not permission to start a
Functions host. No frontend rebuild or browser trial is required for unchanged
UI code. Record existing/new case counts and any failures honestly.

## Bounded post-extraction live verification

**No intermediate approval pause:** once implementation of this brief is
explicitly approved, proceed directly from successful offline verification to
the three sequential replay scenarios below, without waiting for another user
response, provided all required checks pass and no blocker or unexpected
behavior remains. This is one coordinated pass, not one CLI invocation; the
existing stop rules and per-case/total call caps still apply. The user approved
execution of this brief on 2026-11-25; the completed pass is recorded in the
results, not renewed authorization for another pass.

No fresh paid pre-extraction baseline is proposed. Historical
evidence stays untouched and is not renewed authorization or a claim that
nondeterministic live output must be pixel-identical.

Run one sequential pass through these existing, unchanged sequences, using
the ordinary composed replay CLI so the original tooling is exercised:

| Sequence | Coverage | Allowed executions | Hard model-call cap |
|---|---|---|---|
| [03: Named photo adjustments](../examples/sequences/03_named_photo_adjustments.json) | Initial generation, automatic explicit-name learning, resumed multi-photo edit and named corner change. | Its three scripted messages, once each. | 12 |
| [04: Exact proposal return](../examples/sequences/04_exact_proposal_return.json) | Generation, refinement and exact selection after reopening, without a new proposal or acceptance on return. | Its three scripted messages, once each. | 12 |
| [05: Clarification continuation](../examples/sequences/05_clarification_continuation.json) | Unknown-name question, recorded identity answer and continuation of the original resize. | Its two scripted messages plus at most one planned answer, once each. | 12 |

**Maximum: 36 model calls total**, including internal corrections, failed
dispatches and timeouts. Enforce each case's 12-call cap with the existing
`--call-budget PATH --max-calls 12` guard, using one fresh ledger per named case
and reusing that ledger on every resume/answer. Only these three ledgers are
allowed for this pass; do not replace them, create rerun projects or borrow
unused allowance from another case. This is a ceiling, not a spending target.

Use fresh, isolated session-artifact data roots and project IDs, never
`.collage-data-web`, CLI user stores or archived replay projects. Keep existing
model/deployment, prompts, defaults and per-attempt limits unchanged. Advance
one scripted message per invocation and inspect its outcome before continuing.

For sequence 05 only, if the actual question unambiguously asks which photo is
breakfast, the proposed pass may record `Photo 2` with
`--resume --answer "Photo 2" --answer-origin copilot`. This is a proposed
scenario-specific allowance, not permission to answer arbitrary questions.
Do not guess other mappings, automatically approve naming receipts or edit the
sequences. An unexpected question/receipt, failed step, timeout, interrupted
execution, cap exhaustion or unexpected behavior stops the pass for handoff.
There are **no failed-step retries, whole-sequence reruns or prompt-tuning
allowances**. Internal validator-guided corrections remain as implemented.

Run the existing offline integrity assessment on each resulting replay and
inspect saved intents, recipe changes and identity snapshots for the named
objectives. For exact return, verify the original proposal/preview identity
and unchanged accepted version, not visual similarity. These checks are
bounded regression evidence, not proof of general model reliability.

If a defect is exposed, preserve the evidence and report whether it appears
related to the extraction. A regression caused by the refactor may be repaired
offline within scope; no further live calls or unrelated agent improvement is
authorized without a new decision.

## Handoff and approval gates

Drafting this document authorizes neither code changes nor live execution.
Explicit approval to implement this brief covers extraction, offline
verification and the specified bounded live replay pass as one coordinated
run. Record the offline results, then continue directly to live verification
while everything remains green; no intermediate user approval or handoff
pause is required. Any blocker or unexpected outcome stops progression for
handoff under the rules above.

Create `018d_results.md` only once execution produces evidence. Keep baseline,
commands/results, preservation comparisons, actual call accounting, limitations
and any stopped-run evidence there; link it from this brief and the tracker/
index. Do not create a results placeholder or repeat accounting in usage docs.

Stop for the user's review/sign-off after the authorized work. Do not close
018d based on automated success alone or begin 018e automatically. No Git
writes, installs, original-photo edits or changes to pre-existing project/
archive data are authorized. Preserve the user's staging, history and branches.
