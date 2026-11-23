# 016: Trial 06 observations and evidence-handoff repair

**Status:** The human-led trial is paused at P008, not closed. Its separately
approved surgical repair is implemented and verified offline.
No post-repair live continuation or phase
sign-off is claimed. See the [user-run guide](016-user-led-natural-language-trial.md).

## Trial observations

The user ran `p15-human-06` with high interpretation / low generation.
Eight proposals were published, with no explicit acceptance or confirmed
durable names. Numbered clarification answers remained task-local.
The user reported that the early trial went well and was satisfied with recovery
from the breakfast/stacking blip. P006 changed only the stacking order, placing
breakfast and Eye behind Bridge and bookshop.

After P008, bringing Bridge forward and enlarging bookshop failed during
interpretation: the first response cited event 12, which was no longer permitted
evidence; its correction timed out. Repeating only the stacking sentence then
produced two more rejected event-12 citations. P008 remained unchanged.

The displayed **197,780 input / 33,873 output tokens** were cumulative across
28 requests, not a single growing model context. The largest reported input was
9,918 tokens; the latest two completed calls each used about 7,600. There was no
recorded token-limit rejection. Request 26 timed out without usage figures;
its cause remains unknown and is not repaired by this change.

## Diagnosis and approved repair

The three-task window had dropped event 12 from `reference_history`, while
newer visible references still pointed to that real earlier binding. The model
identified photo 1 correctly but reused a citation the validator could no longer
check. Offline reconstruction reproduced the rejection; making the genuine
supporting record available made the same response pass.

The user explicitly approved a surgical repair while retaining **three recent
tasks**. Context assembly now follows citations from already-visible reference
evidence and includes the real earlier supporting records, transitively.
It carries only `event_id`, `references` and `name_updates`, not older raw
messages, layout recipes or entire task histories. Unrelated old records are
not made citable merely because they exist on disk.

Both the model and existing validator use this same exposed evidence.
Missing or non-earlier supporting events fail explicitly. The validator itself,
three-task/twelve-record selection policy, durable-name confirmation semantics,
persisted formats, prompts, reasoning settings and request limits are unchanged.
Supporting metadata can extend beyond those windows only along actual visible
citations; existing input-size guards still apply.

## Offline verification and preservation

Two regression cases reproduced the missing evidence before repair. They cover
a source just outside the detailed window and a longer citation chain whose
source is outside both detailed and compact task selection, including restart.
They check that the oldest real citation remains usable in interpretation and
generation, while wrong-photo, nonexistent and unrelated historical citations
remain rejected. They also retain the three-task/twelve-record windows, preserve
saved evidence and create no durable names or accepted versions.

Focused offline checks passed **14 cases**, including existing bounded-context,
confirmed-name, payload-fitting and retry/clarification recovery checks.
The complete offline suite passed **594 cases**: all 592 existing cases plus the
two added regressions, with no failures or skipped cases.

Fresh fingerprints preserve the user's staged 016 guide/index, HEAD/branch,
runtime, instructions/contracts, **4,643 existing files** across original
photos/project/trial data and the separate Foundry directory, and **3,588 prior
session evidence files**. The live trial remains at P008 with the same 28 events
and 28 requests. No model calls, installs, archived-project recovery, acceptance,
Git writes or timeout-policy changes were made.

Session evidence: `files\016-evidence-handoff`, containing authorization,
baseline/preservation fingerprints, before-repair failures and offline test logs.
Changes remain unstaged for the user alongside their untouched staging.
Human-led continuation requires quitting/restarting chat to load the repair,
then resuming the same project rather than recreating it. Any Copilot-led live
replay/retest remains separately gated; the human trial has no final sign-off.
