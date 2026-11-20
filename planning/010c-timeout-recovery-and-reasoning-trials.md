# 010c: Timeout recovery and reasoning-trial preparation

**Status:** Implemented and verified offline under the user's approval.
See [010c results](010c_results.md) for evidence, contract versions and limitations.
Closed and stopped for integrated review; further live evaluation needs separate
authorization. The approved scope and guardrails below are retained as the
implementation record.
Third stage of [010](010-grounded-interpretation-and-human-trials.md), building
on [010a](010a_results.md) and [010b](010b_results.md).

## Scope and agreed behaviour

- Use one **120-second interpretation deadline** and one **180-second generation
  deadline** per message attempt. Each stage shares its deadline across its
  initial call and any permitted validation corrections; corrections and nested
  provider/transport waits do not restart the clock. Generation gets its own
  budget when that stage begins. Local rendering/publication is outside these
  model-stage deadlines. Preserve the existing four-call per-message cap,
  at most two interpretation attempts and no automatic service retries.
- On a confirmed generation timeout before publication, report that the editing
  baseline is unchanged and that the user can repeat the prompt or say "try
  again". Do not promise identical output, free retries or zero timed-out usage.
  Do not give the same assurance for unrelated publication or I/O failures.
- Retain the failed task's original request, resolved source and clarification
  answers across restart and optional-history compaction. An explicit "try
  again", repeated original prompt or repeated short answer such as "2" can
  continue that task through the existing interpretation stage. Keep the
  original source rather than substituting a rejected result or current source.
  A clearly independent request supersedes it; do not attach stale answers or
  confirmations. No automatic retry or extra interpretation stage.
- Add an explicit command-line generation-reasoning option for chat and replay:
  **high** remains the default; **low** is an opt-in trial candidate.
  Fix the selection for the chat session/replay run and record the actual
  settings in request/run evidence. Resuming a replay must not silently switch
  candidates. Interpretation remains high. No model switch, automatic tuning,
  live comparison or default change is included.

## Lightweight terminal progress and usage

- After interpretation is grounded and validated, show a concise deterministic
  action/source/target summary, for example
  `Intent: edit current proposal P003; target photo 2.`
  Announce `Generating layout...` before awaiting generation. Returns,
  acknowledgements and clarification questions must not announce generation.
  Invalid interpretations must not appear as settled decisions; corrections
  must not be presented as completed stages.
- Use a small optional notification hook with terminal formatting in chat.
  Keep progress separate from model context, authoritative records and
  machine-readable replay output. No extra model-generated explanation,
  streaming, UI framework or general event system.
- Replace raw request-summary JSON in human-facing chat output, including
  `/status`, with readable usage labels. Existing `unknown_usage_attempts` is a
  list of attempt IDs lacking input or output usage, not a count or zero usage.
  For example: `Usage unavailable for 1 request (attempt 2); totals are incomplete.`
  Label token sums as **known usage**, show unknown counts/IDs only when present,
  and retain project-wide accounting rather than implying per-message totals.
- Preserve the machine-readable accounting fields and durable attempt evidence.
  Never invent token counts, erase timed-out attempts or imply that unavailable
  usage was not billed. Explain the distinction in the CLI guide.

## Implementation boundary

Keep CLI, conversation recovery, provider deadlines, replay/assessment evidence
and directly related documentation consistent. Reuse existing task and audit
records; no separate memory system. Version only affected persisted contracts,
reject unsupported versions without migrations or compatibility shims, and
preserve old projects as untouched archives. Layout/project format 3 is unchanged.

Keep the current deployment, serialized-byte-plus-reserve input guard, input/
output limits and durable usage recording. No semantic search, new intent
heuristics campaign, composition changes, vision, renderer changes, graphical
UI, cloud work, new dependencies or retry-budget infrastructure.

## Offline acceptance

Use controlled responses and a simulated clock/timeouts, not real deadline
waits or service calls. Demonstrate:

- Corrections consume the same stage deadline; provider/transport nesting cannot
  extend it. Exhaustion prevents another dispatch. Interpretation and generation
  have independent budgets and retain the existing call caps.
- Confirmed generation timeout preserves the baseline, proposals/PNGs and
  acceptance. Recovery guidance is accurate; unrelated publication/I/O failures
  do not receive unsupported unchanged-state assurances.
- Explicit retry, repeated prompt and repeated short answer retain original
  source/task/answers after clarification, compaction and restart. Include an
  older-source return-and-edit timeout and independent-task supersession.
- Default and opt-in outgoing requests use the recorded reasoning choice;
  interpretation stays high, and replay resume rejects a candidate mismatch.
- Progress appears after validation and before generation finishes, names only
  supported actions/sources/targets, and does not announce generation for
  non-generation outcomes. No progress leaks into model or replay payloads.
- Chat usage is readable with complete, missing and partially missing usage.
  Totals remain known-only; missing usage retains its attempt IDs and honest
  incomplete-total warning, including after timeout/restart.

Run the full offline suite, including accumulated 010a/010b lifecycle,
grounding/navigation, replay/integrity and request-accounting cases. Repeat the
umbrella's tilted-example comparison in fresh isolated projects: recipe,
geometry and decoded pixels must match the captured deterministic baseline.
Offline success is not live interpretation, latency or human-trial sign-off.

## Autopilot guardrails and handoff

- **Zero live calls. No Git writes:** no staging, commits, pushes, branch changes,
  stashes, resets or history edits. Preserve user changes, photos and archived data.
- **Simple retry bound:** at most three unsuccessful targeted fix-and-verify
  cycles on the same blocker. Try materially different fixes where justified;
  do not repeat unchanged commands or reset the count by relabelling the problem.
  Stop sooner when evidence is conclusive. No retry-budget machinery.
- Stay within scope. Do not weaken tests, change requirements, relax limits or
  add fallbacks to make progress. If a necessary scope/design change blocks work,
  stop with evidence and the smallest decision needed.
- Finish with directly related documentation and concise `010c_results.md`:
  changes, contract versions, checks, deterministic comparison and limitations.
  Stop for review of the integrated 010 result. Further live sanity checks,
  human trials and reasoning comparisons need separate authorization.
