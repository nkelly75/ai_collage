# 011 results: Interpretation and naming reassessment

**Status:** Review complete; stopped for a human design decision. No
implementation or live evaluation. Scope: [011](011-interpretation-and-naming-reassessment.md).
Baseline: `ae9086e6f409cd5dd244b54cf74f9509ff66121c`, branch `nkelly/plan-010`.
The spec/index were already staged at entry; application files matched HEAD.

## Recommendation

**Keep separate interpretation and layout stages, but simplify the boundary:
model-led task-local reference resolution, a small explicitly confirmed durable
label table, and deterministic lifecycle/data integrity.**

Do not remove names merely because their implementation grew complicated.
[Trial 04](010g_trial04_results.md) demonstrates their convenience, not the
necessity of the current synonym machinery. Do not replace that machinery with
blanket trust either: an existing guard can accept an incorrectly learned mapping.

The important additional separation is **using a label for this task versus
remembering it for future tasks**. A clarification should resolve and continue
the edit without necessarily installing another lasting synonym. Durable naming
should be optional and deliberate, with a code-rendered exact mapping approved
before writing it. This trades some automatic learning convenience for a simpler,
more accountable memory policy. Ordinary image acceptance must not approve names
implicitly.

This is a proposed direction, not a demonstrated improvement. If an explicit
durable-naming step feels too cumbersome, retaining 010 is defensible; numbers-only
is also viable, but would sacrifice convenience the user actually exercised.

## Diagnosis: where complexity earns its place

| Responsibility | Evidence and assessment |
|---|---|
| Language recognition and memory writes | [`ground_references`](../ai_collage/photo_references.py) combines quote/number recognition, suffix matching, pronouns, collisions, corrections, confirmation and missing-reference checks. Some checks protect identities; others duplicate model language judgement. |
| Durable facts versus inferred aliases | [`PhotoName`/`NameUpdate`](../ai_collage/agent_models.py) store optional aliases, but matching derives suffixes from `name`, not the stored alias list. The list adds validation/evidence without controlling matching. Multiple taught names per ID are useful; derived forms need not be persisted. |
| Clarification and source authority | [`Conversation.request`, `_pending_question`, `_resolve_intent`](../ai_collage/conversation.py) retain tasks across failures and separate questions, naming, selection and generation. Keep this behaviour: trial 03 lost an edit after naming; trial 04 recovered it. It is not disposable naming overhead. |
| Navigation and provenance | [`task_history`](../ai_collage/task_history.py) records actual recipe changes and source ancestry: valuable. Its phrase/verb checks also gate navigation, so naming simplification alone will not remove all interpretation brittleness. |
| Publication and acceptance | [`_publish`, `_validate_proposal`, `accept`, `_recover`](../ai_collage/conversation.py) verify real sources, recipe/preview identity and accepted versions. These checks establish data facts, not language meaning, and should remain. |
| Interpretation transport/context | [`response_format`](../ai_collage/agent_provider.py) adapts a seven-action local union to provider schema; [`context`](../ai_collage/conversation.py) supplies names, pending tasks and bounded evidence. Simplifying bindings must update dependent schemas/context coherently, not merely shorten a prompt. |

**Observed live evidence:** trial 04 used taught/shortened names successfully,
but padded IDs failed despite correctly identified photos; the initial swap
answer required two interpretation calls totalling about 45.3 seconds.
The later skyline clarification and P005-source edit succeeded.
[Replays 03-05](010h_replay_results.md) completed with 16 calls and no corrections.
These support retaining useful behaviour, not general reliability or a new design.

**Offline counterexamples:** six pure-function probes exercised the current code:

| Input/model claim | Actual result |
|---|---|
| Correct IDs from `Photo 01 is Tower Bridge. Photo 04 is bookshop.` | Rejected as unsupported naming evidence. |
| `Photo 1 is bridge. Photo 2 is breakfast.`; model swaps the mappings and quotes the whole message for each | Accepted: each name and claimed number occurs somewhere in the quote. Co-occurrence does not prove their relationship. |
| `book shop` bound to taught `bookshop` | Rejected by literal name matching. |
| `bridge` with two different taught bridge photos | Rejected appropriately; removing all ambiguity checks would lose protection. |
| `Tower Bridge` with/without stored alias `bridge` | Same matching IDs; suffix derivation supplies the match in both cases. |
| `Return to P001 and move photo 2 slightly left` versus the same with `nudge` | `move` passes the navigation wording check; `nudge` is rejected as a pure return. This probe does not publish or check source existence. |

The swapped-mapping probe is an interpretation-integrity concern for the design
decision, not a demonstrated live occurrence or disk-corruption defect. No repair
was attempted. Keep evidence checks, but do not describe substring checks as proof
that an assignment matches the user's meaning.

The P009 unwanted downward movement was a generation-semantic failure after
successful identity resolution. It is not evidence that removing names fixes
layout adherence. The final depth/position prompt change remains live-untested.

## Alternatives considered

| Design | Benefit | Main cost or risk |
|---|---|---|
| Retain 010 | Existing tested recovery and demonstrated convenience; no redesign risk. | Known language-gate friction and imperfect semantic protection remain. |
| Numbers-only interpretation | Removes durable naming and alias/confirmation paths. | Users remember IDs; contextual references and lifecycle interpretation can still be wrong. No guaranteed call saving. |
| Exact taught names with minor normalization | A smaller deterministic vocabulary, predictable constraints. | Still asks users to accommodate a grammar; does not address interpretation/navigation phrase policing. |
| Broad model-led binding and automatic name learning | Flexible wording, fewer linguistic vetoes. | Incorrect interpretations can become durable facts. Known-ID/schema checks alone are inadequate. |
| Recommended: task-local interpretation plus deliberate durable labels | Uses model language capability without automatically promoting inference into memory; removes derived-alias bookkeeping. | Adds a visible approval step when users choose durable naming; task-local semantic errors remain possible. |
| Combine interpretation and generation | One initial model interaction in some cases. | Entangles questions/navigation with layout output and risks regenerating exact returns; no evidence it improves this workflow. |

A focused rubber-duck challenge highlighted the persistent-write risk and proposed
confirmation of every new mapping. The recommendation adopts that protection
**when durable learning is requested**, not an extra naming confirmation after
every ordinary clarification. Numbers-only is not ruled out by successful name
use; it simply has a documented usability trade-off.

## Proposed responsibilities and walkthroughs

**Model:** interpret task wording, contextual references, whether an answer
continues a task, and whether an essential clarification is needed. Use known
labels and visible task evidence; do not infer unseen image contents. Return
structured candidate bindings/actions, not invented application state.

**Code:** validate schema, known IDs, straightforward explicit-number/exact-label
contradictions and real cited records; normalize simple numeric tokens rather
than build a sentence parser. Keep the task/source, catalogue, ancestry, immutable
publication, acceptance, deadlines, accounting and restart recovery authoritative.
Treat retrieval vocabulary as a heuristic, not proof of semantic understanding.

**Memory:** confirmed label-to-ID assignments with their real user event and
approval record; no stored generated synonym lists. For a durable addition or
replacement, code displays the exact proposed mapping batch, including previous
assignments, and commits only that user-approved batch. Approval must be tied to
the current pending batch and recorded locally, not inferred from arbitrary prose
or ordinary layout acceptance. This is a proposed interaction change requiring
implementation design, not an existing local command.

| Request/situation | Recommended handling |
|---|---|
| Known `Tower Bridge`, later `bridge photo` | Model can bind to 1 from labels/context; no persistent alias write. An exact label bound to another ID is a contradiction, not permission to reinterpret it. |
| Unfamiliar `skyline photo` | Ask for identity rather than guess image contents. `Photo 3` binds this task and continues it; durable naming is optional, separately approved. |
| Two plausible bridge photos | Clarify unless visible context or an explicit number distinguishes the target. A task-specific answer does not redefine either global label. |
| `01`/`04`, multi-name answer, or explicit correction | Interpret numeric tokens and relationships; validate IDs. Use task-local bindings for the edit. Any requested durable mapping is displayed for exact batch approval, rather than treating name/number co-occurrence as approval. Users can still approve a mistaken mapping. |
| Rejected/invalid clarification answer | Keep the original edit and source through restart. Reworded answers supplement it; independent replacement must be explicit. |
| P005 return versus P005 return-and-edit | Model distinguishes the actions; code loads the exact real source. Pure selection never generates; compound edits generate from P005, not the latest recipe. |
| Proposed memory update rejected or changed meanwhile | Do not write it. Retain the prior labels and a truthful task/baseline status; retry or replacement must not silently approve a stale batch. |

Task-local mistakes can still target the wrong real photo. Preserve previews and
explicit acceptance, record resolved IDs, and make bindings inspectable; previews
are recovery opportunities, not guarantees that users notice every error.
The model's capability with broader references is a hypothesis, not validated
by these walkthroughs. No confidence-score threshold, verifier model call,
semantic-search service or hidden summarizer is recommended.

## Smallest later scope and validation

### Post-review clarifications for the implementation draft

The user confirmed these intended behaviours after discussing the recommendation:

- Several explicitly taught labels can identify one photo. Adding
  `Daunt Books -> 4` preserves `bookshop -> 4`; replacement/reassignment must
  be explicit and displayed for approval.
- `bridge` for `tower bridge`, or `book shop` for `bookshop`, can be interpreted
  per request without storing those variations or requiring literal suffix matches.
- User descriptions such as "Photo 4 is the one with the sand castle" can propose
  a useful durable label. This is supplied knowledge, not recognition of unseen
  image contents. Similar beach photos remain usable by number; the model uses
  distinguishing labels/context and clarifies when those are insufficient.
- A numeric answer to an identity question resolves the pending task; it does
  not automatically teach a lasting name. Explicit teaching requests use the
  durable confirmation gate.
- **Prefer one gate:** when durable teaching accompanies an edit, pause both
  until the exact mapping batch is confirmed. Do not introduce separate
  pending-name/completed-edit flows merely for smoother UX. Ordinary task-local
  clarification without durable teaching does not require this additional gate.
- Natural-language confirmation is the expected user interaction. Slash-command
  tooling may help verification, but users should not need commands or batch IDs.
  Interpretation can classify the reply; code applies only its current displayed
  receipt. This trades command-level determinism for language convenience and can
  require model calls; it is not an entirely local confirmation guarantee.
- Clear edits without new/changed durable names proceed without the naming gate.
  Preserve deterministic layout tests. Retire interpretation tests for deliberately
  removed rules, while retaining essential lifecycle/integrity coverage and focused
  tests for the new design; maximizing test count is not a goal.
- Less complex deterministic interpretation, fewer niche rules and clearer
  responsibilities are explicit goals, not line-count acceptance thresholds.
  Moving complexity into a large prompt or cumbersome workflow is not success.

These are design decisions for [the 012 draft](012-model-led-references-and-confirmed-names.md),
not evidence that the proposed model behaviour works or approval to implement it.
The review findings and original verification above/below remain unchanged.

If approved, first simplify **naming/binding and durable-memory policy only**:
remove derived-alias state and linguistic source/pronoun policing, introduce the
explicit memory gate, and keep existing task/source/publication machinery.
Do not combine this with package moves, reasoning changes or a navigation rewrite.
Record the navigation vocabulary limitation for a separate decision.

Update dependent interpretation schemas, context, chat presentation, replay/
assessment evidence and tests together. Current conversation records are 6 and
replay reports 7; a changed persisted shape needs affected-contract versioning,
fresh projects and explicit rejection of old contracts, not migrations.
Layout format 3 need not change.

Offline gates must cover wrong/swapped durable candidates, unapproved/negative/
stale approvals, transient synonyms that do not become names, exact-label/number
conflicts, ambiguous multi-target answers and retained tasks after restart.
Retain existing exact-selection, older-source, timeout, acceptance, accounting
and preservation regressions. A later authorized live pass must compare convenience,
wrong-target errors, clarification loops and unnoticed name drift against the
saved baseline; lower code size or tokens alone do not establish improvement.

## Verification and preservation

The code trace and evidence review were direct; one rubber-duck challenge assessed
the alternative boundary without duplicating the trace. Six network-blocked,
in-memory probes passed their expected outcomes, including accepted wrong mappings.
Eleven selected existing offline integrity/clarification/source/acceptance tests
passed. No full-suite rerun was needed for a review with unchanged application code.

Reproducible probe helper in this session's `files`:
`011-review-probes.py`. It instantiates neither Conversation nor a provider and
writes no application/project data. Existing tests use temporary generated photos.

Entry/final preservation fingerprints match:

- Staging: `1f980f016a965cb0db9cf2a8e7574a90b8ab938a`.
- Non-planning tracked-file fingerprint: `ec7a0d97032c91649db59971b5d7c63eff20415f`.
- Original/project files: 1,154, aggregate SHA-256
  `5F862C0C9C16BC99D960FA8B8B1CA83AA23C97734CC79083328344D27CB3565A`.

No application/prompt/test/dependency edits, cloud calls, Git writes, original/
accepted/archive data writes or sealed-evidence writes occurred. Only this new
results record and 011/index status are changed in the repository. Stop here:
the recommendation does not authorize simplification, merges, refactoring or runs.
