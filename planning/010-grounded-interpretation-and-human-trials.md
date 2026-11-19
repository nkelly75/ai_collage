# 010: Grounded interpretation and continued human trials

**Status:** Initial proposed specification. The user approved writing this
brief and closing 009, not implementing 010 or making live calls.
Review the open choices and approve implementation before changing application
code, prompts, contracts or runtime settings. Live evaluation is a separate gate.

## Purpose and prerequisites

Continue the human-led feedback loop from [009](009_results.md), improving how
the application understands requests and retains useful evidence without
turning normal creative freedom into repeated clarification questions.

Build on the implemented 009 context handling and the
[008 lifecycle support](008_results.md). Preserve original photos, archived
projects, trial evidence and accepted versions. The current CLI and layout
contracts remain documented in the [CLI guide](../docs/cli-guide.md) and
[layout field guide](../docs/layout-format.md).

## Agreed scope and behaviour

### 1. Grounded interpretation, not just action classification

Before generation, establish the requested lifecycle action, the source proposal
where applicable, and the identities of referenced photos. Resolve references
from user-established names, stable numbers and available layout/history
evidence; do not infer unseen image contents.

- Ask when consequential ambiguity remains about the target, source or action.
- Do not ask for unnecessary precision: "move photo 2 a bit right" identifies
  the target and direction; generation can choose a reasonable distance.
- If breakfast is known but bookshop is not, ask only for bookshop's number.
- Keep interpretation concise and structured. It resolves meaning, not layout
  geometry. A confidence score alone is not evidence that a reference is grounded.
- Supply resolved identities to generation rather than leaving it to reinterpret
  unknown names. Validate IDs and bindings in ordinary code where possible;
  deterministic geometry validation cannot prove semantic understanding.

### 2. Compact, evidence-backed memory

Replace abrupt loss of useful meaning with a small memory structure alongside
recent conversational detail. Proposed components:

- Durable project-local bindings learned from explicit user statements or
  clarification answers, such as `breakfast -> photo 2`. Keep their origin
  distinguishable and support explicit user corrections.
- A compact task/proposal navigation ledger: originating request, action,
  source, result or failure, and links to clarification questions/answers.
  Distinguish what the user requested from what the application actually did.
- Recent fuller wording, current task/layout, outstanding clarification and
  correction evidence; retrieve exact older source recipes and relevant
  conversational detail when needed.

Keep the complete audit record on disk. A low-fidelity entry for each message is
an option, not a requirement to send the entire growing ledger on every request.
Group clarification answers with their originating task for navigation purposes.
Do not treat questions, failed attempts or exact selections as generated edits.
Retain enough selection/source history to distinguish navigation from creation
order after returning to an older proposal and branching from it.

Prefer structured interpretation output and deterministic recipe differences
over an extra summarization call after every message. Descriptions of requested
changes must not be stored as proof that those changes happened.

### 3. Reliable returns

- A pure return selects the exact preserved proposal/PNG; it does not generate,
  rerender or accept a replacement.
- Return-and-edit selects an explicit older source for the new edit.
- Resolve "undo the last two edits" from meaningful task/navigation history,
  not raw message count or proposal numbering alone.
- When one destination is clear, return directly. When plausible alternatives
  remain, confirm a candidate with its distinguishing description, for example:
  "Do you mean P007, before the thicker borders and bringing breakfast forward?"
  Do not claim certainty from an ID that merely exists.
- Subsequent edits start from the selected baseline.

### 4. Responsiveness and timeout recovery

The agreed target is **180 seconds for a generation invocation**, replacing
the current 120-second deadline. This is patience, not a speed improvement.
Keep the complete invocation bounded; do not accidentally add multiple separate
180-second waits through nested provider/transport settings. Interpretation
deadline handling remains an implementation choice below.

For a confirmed generation timeout before publication, report that no proposal
was saved, identify the unchanged baseline where available, and advise that it
is OK to repeat the previous prompt. Preserve the failed task's source and
clarification context so repeating a short answer remains meaningful.
Do not promise identical model output, free retries or zero timed-out usage.
Do not give a blanket unchanged-state assurance for unrelated publication or
I/O failures whose outcome needs reconciliation.

Retain explicit user-driven retries, no automatic service retries, durable
request accounting, and at most four actual calls per message attempt, with
at most two interpretation attempts.

## Context limits: review separately from memory selection

The current three-exchange window is a selection policy, not provider capacity.
The final preflight uses serialized UTF-8 bytes plus a reserve as a conservative
token bound against an application-chosen limit; that limit is not a verified
provider context-window ceiling.

Review whether this accounting and its threshold remain appropriate. Keep a
final bounded request-size check, preserve essential task/reference evidence,
and report explicit no-dispatch errors if essential input cannot fit.
Do not solve lost meaning solely by raising the threshold or silently truncating
essential facts. Any accounting change needs a documented safety basis covering
instructions, schemas, framing and context, with offline boundary checks.
The existing input/output limits stay unchanged until a specific revision is
reviewed and approved.

## Low-reasoning experiment: candidate, not default

The user is interested in one small exploratory low-reasoning trial to see
whether faster generation is worth any change in reliability. This is not a
decision to lower the production default, switch models or start a tuning sweep.
Initially leave interpretation's reasoning setting unchanged so the generation
change can be examined separately.

Before any service call, agree the candidate settings and a bounded live scope.
Record timings, reasoning/output usage, corrections, semantic mistakes,
clarifications and user observations. Compare against high-reasoning evidence
without claiming different exploratory prompts form a controlled comparison.
A same-case comparison, if wanted, needs explicit inclusion in that scope.
Faster output alone is not evidence of an acceptable correctness trade-off.

## Decisions to settle before implementation approval

1. The minimal interpretation output and how reference evidence/binding changes
   are checked and persisted, including conflicting or ambiguous names.
2. The ledger representation, useful per-task detail, model-facing size bound
   and retrieval mechanism. Preserve enough evidence to clarify rather than guess.
3. Whether preflight accounting needs a change at all; if so, its safety basis
   and exact threshold. No new threshold is selected in this initial brief.
4. How failed-task continuation and candidate-return confirmations persist across
   restarts, and whether interpretation retains its current 120-second deadline.
5. Any affected conversation/replay contract versions. Keep one current
   implementation, reject unsupported versions explicitly and preserve old
   evidence without migrations or compatibility shims. Layout format 3 does
   not change for these conversational improvements.

## Acceptance and evidence

Offline checks should cover the introduced behaviour, using 009 failures as
concrete regression scenarios:

- An unknown photo name leads to clarification without generation; a learned
  name survives beyond the recent window and a restart. A second unknown name
  does not cause the known name to be guessed or forgotten.
- A clear target with a qualitative amount proceeds without a pedantic question.
- Questions/answers do not count as separate edits. A descriptive return either
  resolves the intended source or asks a supported confirmation; explicit
  selection preserves the exact saved recipe/PNG, and the next edit uses it.
- Compact history distinguishes requested from observed changes, remains bounded
  as history grows, and can retrieve relevant older evidence. Essential bindings,
  pending tasks and correction context survive size fitting.
- A simulated generation timeout exercises the 180-second configuration without
  a real wait, leaves the baseline unchanged, records unknown usage honestly,
  gives repeat-prompt guidance and retains clarification/source context.
- Current offline rendering, lifecycle, replay/integrity and request-accounting
  behaviour remain intact. Record effective context and relevant instruction/
  configuration identity so evidence is attributable to the tested candidate.

Mocked responses establish orchestration and invariants, not live language
understanding, latency or user satisfaction. Report those limits explicitly.

## Human-led evaluation and approval gates

1. Review and approve the implementation scope and outstanding decisions.
2. Implement and verify offline; update directly affected guides/contracts.
3. Obtain separate authorization to start live evaluation, specifying any
   Copilot-executed smoke check or reasoning comparison and its call cap.
4. Continue exploratory human trials when the user chooses. As in 009, the user
   controls prompts, continuation and stopping; no fixed trial-wide call budget
   is proposed for that interactive session. Per-message/provider safeguards and
   usage logging still apply. Assistant-run campaigns are not covered by this.

The user sends collage prompts to the application and observations to Copilot.
Observer commentary must not be injected into model context. Label suggested
prompts as assisted when the user chooses to enter them. Do not silently repair
trial outputs or change the candidate mid-run; record interventions distinctly.
Use fresh trial projects and preserve the closed 009 evidence.

Keep outcomes, measurements, exact trial prompts, limitations and accounting in
a separate 010 results record when work begins. Scripted success is not human
sign-off, and one exploratory run cannot establish general reliability.

## Exclusions

Composition/perceived-edit-strength work and the exploratory ideas in 007 are
deferred. No vision, image uploads, UI, cloud hosting, renderer redesign,
automatic critique, hidden summarization calls, model switch or unattended
tuning campaign is included. This document authorizes no Git staging, commit,
push, live call, implementation or recovery of an old trial.
