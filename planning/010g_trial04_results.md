# 010g: Human-led trial 04 observations

**Status:** Stopped for the phase 010 handoff at the user's direction.
Observation snapshot: events
**1-32**, requests **1-31**, working baseline **P010**. The user accepted
**P007** as project version 1 before continuing. Acceptance approves that
proposal, not general reliability or completion of the trial.
Trial instructions: [010g](010g-user-led-natural-language-trial.md).
Prior trial observations remain unchanged in [trial 03](010g_results.md).

## Trial 04: p010g-human-04

Started by the user on 23 November 2026 after the
[010h offline changes](010h_results.md) and
[03-05 replay follow-up](010h_replay_results.md).
1200x1800 (2:3), usual four photos, high interpretation / low generation.
Evidence is saved under
`.collage-data-v3\users\local-dev\projects\p010g-human-04\conversation`.
Copilot observes saved JSON read-only, without loading/recovering a conversation,
sending live requests, rewriting trial evidence or tuning implementation.
The separately approved prompt-only refinement after these observations is
recorded below; it is not part of the tested candidate.

The user reused trial 03's initial prompts and intends to choose later prompts
according to progress. Their initial feedback: going OK so far; the swap took
longer but appears correct.

1. "Make an initial collage with a navy background. Put photo 1 in the bottom left and photo 4 in the top right. Make them bigger than the other photos." -> P001, no correction.
2. "Swap the locations of the breakfast and london eye photos" -> Asked which photo numbers identify both names.
3. User answered "2 for breakfast and 3 for london eye" -> One internal interpretation correction, then learned breakfast = 2 and london eye = 3 and produced P002.
4. "Good. Now grow each photo by about 40%." -> One internal geometry correction, then P003. The user reported that the growth worked.
5. "Good. Now stack the Tower Bridge photo above the bookshop." -> Asked which photo identifies each name. The user's identity answer exhausted interpretation correction; P003 remained unchanged. The user found the reassuring recovery message "not bad" and intends to continue.
6. "Photo 01 is the tower bridge. Photo 04 is the book shop." -> Both interpretation attempts again failed name grounding; P003 and learned names stayed unchanged.
7. Assisted clarification: "Photo 1 is Tower Bridge. Photo 4 is bookshop." -> Learned both names and resumed the original stacking request, producing P004 without corrections. The user reported that it worked and described the continuation as "Not bad."
8. "Grow the London Eye by 20% and move it closer to the top left corner. Keep it stacked under the bookshop." -> P005 without corrections.
9. "Grow the bridge photo by 15%." -> Shortened name resolved immediately; one geometry correction, then P006.
10. "Move the breakfast closer to the bottom right." -> P007 without corrections. The user is reasonably happy with this image and asked about selection/acceptance.

### Swap correctness and recovered interpretation friction

A read-only comparison of the saved recipes confirms an exact swap of authored
centres: photo 2 moved **(0.32, 0.28) -> (0.69, 0.72)** and photo 3 moved
**(0.69, 0.72) -> (0.32, 0.28)**. All other authored values, including sizes,
styles, stacking, background and the other photos, remained unchanged.

The first interpretation of the answer used normalized numeric references
`photo 2` and `photo 3`. Grounding rejected those reference texts because this
multi-name answer did not supply the required normalized-number evidence.
The correction instead bound the actual taught names, retaining the original
swap task and P001 source. There was no naming-only detour, geometry correction
or failed user-facing request.

The two interpretation HTTP calls for the answer took **21.968s + 23.360s =
45.328s**. Generation took **2.453s**. The extra delay was primarily interpretation
and its correction, not rendering/layout generation. These are request durations,
not a measurement of the user's entire interaction.

Record this as successfully recovered grounding friction with a noticeable
latency cost, not proof that interpretation is now consistently flexible.
No fix is being applied during the trial.

### Growth and necessary edge adjustment

P003 increased every authored frame width by 40%. Only photo 4's position
changed: its horizontal centre moved **0.72 -> 0.714**, about **7 pixels left**
on the 1200px canvas. Its vertical centre and all other photos' centres stayed
unchanged. Background, stacking, borders, rounding and tilts were preserved.

The first generation candidate kept photo 4 at its old centre. Its tilted
frame crossed the right edge; the sampled footprint extended **6px** beyond
the canvas. Feedback reported a safe horizontal centre range ending at
**0.715833333**. The corrected candidate moved photo 4 inward to 0.714 and
published P003 without reducing the requested enlargement.

This request did not explicitly ask for inward movement. It therefore exercises
the intended ordinary-enlargement fit permission and successful local correction,
without establishing that larger/more complex enlargements will always succeed.

### Stacking clarification: zero-padded numbers and failed correction

Tower Bridge and bookshop were not yet taught names, so the initial identity
question was appropriate. The user answered:

> The Tower Bridge is 01 and the bookshop is 04

The first interpretation tried to learn both names and apply the original
stacking edit, but grounding rejected the name update. Its zero-padded `01`/`04`
wording did not satisfy the current numeric-evidence checks for photo IDs 1/4.
The next interpretation dropped the name updates and used normalized `photo 1`
and `photo 4` references that lacked supporting current-task/answer wording;
grounding rejected that too.

Both interpretation attempts were recorded as invalid. Generation did not run,
no proposal was created and neither new name was learned. P003 and the previously
learned breakfast = 2 / london eye = 3 mappings remained intact. The failure
followed a pending design clarification, not a rejected geometry candidate.

Track this as identity-answer grounding rigidity plus an unsuccessful correction,
not a stacking/rendering defect or user misuse. The user explicitly reported
that the reassuring message was reasonably helpful and plans to continue:
positive feedback on recovery presentation, while interpretation still failed.
No prompt suggestion or implementation change was made at this observation.

### Reworded identity statement still blocked

The user described the next message as clarifying the names without asking for
edits. Both interpretations nevertheless retained the pending stacking task
(task 10) as `edit/current`, rather than losing its original operation. Neither
reached generation: zero-padded `01`/`04` again failed the name-evidence check,
even when the correction preserved those exact number strings in its references.

No new mappings or proposal were saved. The current photo names remain
breakfast = 2 and london eye = 3, and the collage remains P003.

Copilot's suggested next clarification uses unpadded IDs and the original label
spelling: "Photo 1 is Tower Bridge. Photo 4 is bookshop." This is advice only;
any subsequent use must be marked assisted. Copilot also notes that a valid
answer can continue the still-pending stacking edit without the user repeating
it; a naming-shaped answer is not automatically an independent naming-only task.
No application change or live call was made.

### Assisted clarification succeeds and retains the pending edit

The user used Copilot's proposed clarification verbatim. Interpretation learned
Tower Bridge = 1 and bookshop = 4 from the explicit statement, and generation
continued the original stacking task from P003. Both events remained on task 10,
after the four earlier invalid interpretation events; no correction was needed
for this answer.

P004 changed only layer order, **[2, 1, 3, 4] -> [2, 3, 4, 1]**, putting photo 1
above photo 4. A raw-recipe comparison confirms all photo fields and the canvas
were unchanged.

The earlier model responses had already identified IDs 1/4 correctly from
`01`/`04`; rejection came from the local evidence rules, not demonstrated
confusion about which photos the user meant. Zero padding remains a usability
limitation to track, not user misuse. Recovery successfully retained the task
through multiple failed answers, but this success was assisted and also restored
the original `bookshop` spelling, so it is not an isolated zero-padding experiment.

### Later edits and positive feedback on P007

The next three user-chosen edits retained unrelated authored fields:

- P005 changed only photo 3: width **0.364 -> 0.4368**, centre
  **(0.32, 0.28) -> (0.27, 0.22)**. It remained below photo 4 in the unchanged
  layer order.
- P006 changed only photo 1: width **0.518 -> 0.5957**, horizontal centre
  **0.29 -> 0.33**. The shortened reference **"bridge photo"** resolved to the
  taught Tower Bridge/photo 1 without an identity question or interpretation
  correction. The first enlargement candidate's sampled footprint exceeded the
  left edge by 1px; a generation correction produced a valid inward position.
- P007 changed only photo 2's centre, **(0.69, 0.72) -> (0.75, 0.78)**.

This provides live evidence of the conservative-shortening path as well as
further targeted edits and successful resize-fit correction. It is still one
human trial, not proof of general reliability.

At the earlier events 1-23 snapshot P007 was the selected working baseline, but
`accepted_proposal` and `expected_version` are null. The user's positive image
feedback is not itself an acceptance operation. Copilot explained the existing
local `/accept P007` command; no acceptance was executed on the user's behalf.
The trial remains in progress until the user chooses to stop.

### Acceptance and three Copilot-suggested challenges

The user accepted P007 locally (event 24, version 1). The saved accepted recipe
matches P007 exactly. Acceptance remained P007/version 1 while the following
edits advanced the working baseline; Copilot did not execute the acceptance.

These three requests were suggested by Copilot and run by the user, so this
portion is assisted rather than independently user-authored:

1. "Grow the bridge photo by another 10%. Move it inward only if needed to keep it inside the canvas. Leave the other photos unchanged" -> P008 after one generation correction.
2. "Make the skyline photo 10% larger and keep it stacked below the bookshop." -> Asked "Which photo is the skyline photo?" The user's answer "Photo 3" learned skyline photo = 3 and continued the original task from P008, producing P009 without corrections.
3. "Go back to P005, then move breakfast closer to the bottom right. Keep everything else as it was in P005." -> P010 from P005 without corrections.

Raw-recipe comparisons confirm:

- P008 changed only photo 1: width **0.5957 -> 0.65527** (+10%) and centre
  **(0.33, 0.72) -> (0.36, 0.68)**, about 36px right and 72px up. The first
  candidate retained its old centre and exceeded sampled bounds by 22px left
  and 36px bottom. Correction retained the requested size and moved inward.
  This was a valid fit adjustment, not a claim of mathematically minimal motion.
- P009 changed only photo 3: width **0.4368 -> 0.48048** (+10%) and vertical
  centre **0.22 -> 0.345**, **225px down**. Layer order remained
  **[2, 3, 4, 1]**, already placing photo 3 behind photo 4.
- P010 changed only breakfast/photo 2 relative to P005: centre
  **(0.69, 0.72) -> (0.75, 0.78)**. All other recipe values match P005,
  rather than carrying the later bridge or skyline changes forward.

The user noticed possible unwanted downward movement from "stacked below the
bookshop." The saved centres confirm actual movement, not an optical effect
of enlargement. An offline, in-memory geometry check of P009 with photo 3
restored to its old vertical centre **0.22** succeeds, including tilted
containment: movement was not needed to fit the enlarged frame.

Record the second challenge as successful clarification/task retention and
requested enlargement, but with an unintended spatial edit. The wording was
intended to preserve depth order, and the result is consistent with also treating
"below" as spatial placement; saved evidence does not prove the model's internal
reason. Copilot's suggested wording contributed ambiguity. No code/prompt fix,
live call, rerender or trial-evidence modification was made by Copilot.

### Approved prompt refinement and phase handoff

After reviewing P009's unintended downward movement, the user approved a
general-purpose paragraph in `ai_collage\prompts\layout-agent.md`. It asks the
generator to distinguish depth order from canvas position using the whole
request and current layout, not a fixed dictionary of words. It preserves
unrelated properties and permits only necessary fit movement during resizing.

This was a separately authorized prompt-only change after the observed trial
requests, not a silent repair or part of the earlier frozen replay candidate.
The focused offline prompt-loading test passed; no live retest, new proposal,
rerender or code change was performed. The P009 failure remains recorded as
observed, not reclassified as fixed.

The user considers phase 010 to have gone far enough with decent improvements.
Stop these observations for the phase handoff: P007 remains the accepted
version 1, and P010 is the last observed working baseline. No application
session was terminated or data altered by this documentation closeout.

Useful progress includes exact targeted edits, conservative name shortening,
retention of the stacking task through failed identity answers, a short numeric
answer completing the skyline edit, enlargement fitting, explicit acceptance
and an exact older-source edit. Remaining limitations include zero-padded
numeric grounding, literal spelling variants, interpretation-correction latency
and unintended spatial movement in a layering request. Some recovery and
challenge prompts were assisted. This is positive human feedback on a bounded
iteration, not a controlled comparison or comprehensive reliability sign-off.
Further trial, implementation or live evaluation requires separate approval.
