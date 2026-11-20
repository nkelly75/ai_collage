# 010: Grounded interpretation and continued human trials

**Status:** Agreed high-level direction; umbrella for three proposed sequential
autopilot specs, **010a, 010b and 010c**.
[010a](010a-grounded-photo-references.md) is implemented and verified offline,
with a separately authorized live replay sanity follow-up;
see [010a results](010a_results.md). 010b and 010c still need detailed specs and
approval. No further live calls are authorized. Next: review the 010a handoff.

## Purpose and prerequisites

Continue the human-led feedback loop from [009](009_results.md), improving how
the application understands requests and retains useful evidence without
turning normal creative freedom into repeated clarification questions.

Build on the implemented 009 context handling and the
[008 lifecycle support](008_results.md). Preserve original photos, archived
projects, trial evidence and accepted versions. The current CLI and layout
contracts remain documented in the [CLI guide](../docs/cli-guide.md) and
[layout field guide](../docs/layout-format.md).

## Three implementation stages

Each stage should be useful and verifiable on its own, build on the preceding
stage, and stop after an offline handoff. Do not require human trials between
stages. After all three, review the integrated result before separately
authorizing another round of exploratory human trials.

### 010a: Grounded photo references

Implemented scope and guardrails: [010a](010a-grounded-photo-references.md);
evidence and limitations: [010a results](010a_results.md).

Combine structured photo-reference resolution with compact, durable
user-established names. Resolve references using stable photo numbers, user
statements and available evidence, not guesses about unseen image contents.
Pass resolved identities to generation and validate bindings in ordinary code
where possible. Keep interpretation concise; it is not another geometry stage.

Clarify consequential uncertainty, not creative latitude. "Move photo 2 a bit
right" needs no exact distance. If breakfast is known but bookshop is not, ask
only for bookshop's number. Support explicit corrections to learned names and
retain their origin. Proposal-navigation redesign belongs to 010b.

**Offline gate:** Exercise reference/binding contracts, invalid or inconsistent
interpretation responses, unknown names, user corrections and clarification
continuation. Verify names survive recent-history compaction and restarts, and
resolved identities reach generation. Controlled responses test application
behaviour, not whether the live model will interpret every request correctly.

### 010b: Compact history and reliable returns

Build on 010a with a compact task/proposal navigation ledger, recent detail and
retrieval of relevant older evidence. Preserve the full audit record on disk.
Distinguish requested changes from actual outcomes; link clarification answers
to their originating task. Questions, failed attempts and exact selections are
not generated edits. Track navigation and branching, not just creation order.

A pure return selects the exact preserved proposal/PNG without generation,
rerendering or acceptance; return-and-edit uses the selected older source.
Resolve clear returns directly. If "undo the last two edits" has plausible
alternatives, confirm a supported candidate with a useful description, for
example: "Do you mean P007, before the thicker borders and bringing breakfast
forward?" Subsequent edits use the selected baseline.

Review context selection separately from final request-size accounting. Keep
model-facing history bounded and retrieve older detail when needed; sending a
tiny entry for every message still grows indefinitely. Prefer structured records
and deterministic recipe differences over extra summarization calls. Do not
silently discard essential bindings or resolve missing evidence by guessing.

**Offline gate:** Exercise grouped tasks, bounded history/retrieval, ambiguous
return confirmations, exact selection and edits from restored/branched sources.
Include integrated cases using 010a's learned names and cases where requested
and actual outcomes differ.

### 010c: Timeout recovery and reasoning-trial preparation

Set a **180-second total deadline for a generation invocation**, rather than
stacking separate waits through provider/transport layers. This adds patience,
not speed. For a confirmed generation timeout before publication, report the
unchanged baseline and advise that it is OK to repeat the previous prompt.
Retain the task's source and clarification context, including for short answers.
Do not promise identical output, free retries or zero timed-out usage, or give
unchanged-state assurances for unrelated publication/I/O failures.

Prepare an explicitly selected and recorded generation-only low-reasoning
candidate for a later trial. **High reasoning remains the default** and
interpretation reasoning stays unchanged. No model switch, automatic tuning or
live reasoning experiment is part of this implementation stage.

**Offline gate:** Simulate timeouts without real waits; verify deadline settings,
unchanged baseline, repeat-prompt guidance, failed-task continuation and honest
usage accounting. Check the explicitly selected reasoning settings and run
accumulated integration cases from 010a and 010b.

## Verification across stages

Capture a deterministic baseline before 010a using
[`emma_tilted_2x3.json`](../examples/emma_tilted_2x3.json). After each stage,
repeat it in a fresh isolated project and compare the recipe, geometry and
decoded pixels with that baseline. This covers whole/cover framing, crop/pan/
zoom, borders, rounded corners, tilt and stacking without altering old projects.

For each stage, run focused regression checks and preserve current lifecycle,
replay/integrity, rendering and request-accounting behaviour. Use malformed and
inconsistent model responses as well as successful controlled responses.
After all three stages, run the full offline suite and review the combined
handoff before any live evaluation.

Offline tests establish orchestration, contracts and invariants, not live
language understanding, real latency, or user satisfaction. Rendering equivalence
does not validate photo-reference understanding. Human trials assess whether
clarification is helpful rather than pedantic and whether the integrated
experience is useful.

## Requirements for each autopilot spec

Write and approve a detailed spec before implementing that stage. Each should
state its scope/exclusions, dependencies, concrete acceptance cases, affected
contracts, offline verification, preservation rules and stop conditions.
Stop at a documented handoff; do not automatically start the next stage or a
live trial. Keep outcomes and evidence in a separate results record, not here.

Settle consequential choices before autopilot approval, rather than delegating
an open-ended "better memory system":

- **010a:** Interpretation/reference output, binding evidence and persistence,
  name conflicts/corrections and clarification continuation.
- **010b:** Ledger representation, useful detail, model-facing bound, retrieval
  and persistent return confirmations. Decide any preflight-accounting revision
  explicitly, with a safety basis and offline boundary checks.
- **010c:** Failed-task retry semantics, interpretation deadline and how the
  reasoning candidate is selected and recorded.

The current three-exchange window and conservative byte-based preflight are
application policies, not a verified provider context-window ceiling.
Keep existing input/output limits unless a specific revision is approved;
retain a final size guard and explicit errors if essential input cannot fit.

## Guardrails and later human trials

Implementation uses **zero live calls**. Preserve original photos, archived
evidence, accepted versions and the user's Git state. Keep one current
implementation; version only affected contracts and reject unsupported records
without migrations or compatibility shims. Layout format 3 does not change.

Retain durable usage recording, no automatic service retries, and at most four
actual calls per message attempt, including at most two interpretation attempts.
Any assistant-run live check/comparison needs separate authorization with one
explicit call cap, not nested or replenishing allowances. Human-led terminal
trials have no fixed trial-wide budget; the user controls prompts, continuation
and stopping, subject to per-message/provider safeguards.

After the three offline handoffs, seek authorization for the integrated human
trial and any small low-reasoning experiment. Use fresh projects and record the
tested implementation/settings, exact prompts, timings, usage, corrections,
semantic mistakes and observations. A low-reasoning trial does not change the
default automatically; faster output alone does not establish a good trade-off.
Different exploratory prompts are not a controlled high/low comparison.

The user sends collage prompts to the application and observations to Copilot;
do not inject observer commentary into model context. Mark user-entered suggested
prompts as assisted. Do not silently repair trial outputs or change candidates
mid-run; record interventions. Scripted success is not human sign-off.

## Exclusions

Composition/perceived-edit-strength work and the exploratory ideas in 007 remain
deferred. No vision, image uploads, UI, cloud hosting, renderer redesign, automatic
critique, hidden summarization calls, model switch or unattended tuning campaign
is included. No Git staging, commit, push or old-trial recovery is authorized.
