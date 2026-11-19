# 009 results: User-led natural-language trial

## Closure and handoff

**009 is complete and closed as a learning iteration.** Two human-led trials
informed implemented bounded-context handling and clearer limit errors, while
exposing reference-grounding, memory, navigation and responsiveness weaknesses.
This is useful progress, not a claim of satisfactory natural-language reliability
or broader product sign-off.

The selected follow-up is drafted in
[010: Grounded interpretation and continued human trials](010-grounded-interpretation-and-human-trials.md).
That brief is proposed, not implementation or live-call authorization.
The trial evidence below remains unchanged; no further runs are authorized by 009.

## Trial 1

- Project: `p009-human-01`, 1600x900, usual four photos.
- Six requests produced P001-P006: initial composition, reposition/resize,
  enlargement/stacking, content swap, relative resizing, and straightening.
- User feedback: "I'm actually very pleasantly surprised by how that went."
- Seventh request's intent succeeded, but generation hit the local conservative
  input bound: **51,041 against 50,000**, before HTTP dispatch. P006 is preserved.
  The displayed `ChatClientException` hid the underlying guard failure.
- All seven intent responses were fresh (first message) or edit/current
  (subsequent messages). Clarification and other lifecycle branches remain
  unexplored in this trial.
- The user chose not to recover this chat. No recovery or further live calls
  were performed by Copilot.

### Prompt sequence

1. "Make an initial collage with a dark background. Try to start with photos 1 and 3 slightly larger in opposite corners. Some overlap between those two is OK." -> P001
2. "Not bad. Move photos 1 and 3 closer to their respective corners. Shrink the other two images and make them about 70% of their current size." -> P002
3. "Better. The two larger photos are well located. Make them about 20% larger. Move photos 2 and 4 closer to the center and increase their size by about 20% also. Some small overlap is OK. Ensure photo 4 is stacked above photo 2." -> P003
4. "Now try swapping photos 1 and 3. So keep the tilt, position etc of the frames and swap the content of the photos." -> P004
5. "Now shrink photo 2 to about 85% of current size and grow photo 4 to about 115% of current size." -> P005
6. "Straighten photo 4 only." -> P006
7. "Move photo 2 closer to the top of the canvas and left by about 5% of the canvas width. Move photo 4 slightly lower." -> Generation blocked; no new image.

### Shareable story

Created from saved evidence: a photo-number key, all seven exact prompts, six
preview thumbnails, and an explanation that the last request produced no image.
The separate final PNG is a byte-identical copy of P006.

Story image: [009_result_01.png](009_result_01.png).
The separate final PNG remains a session artifact:
`files\009-story\final-collage-P006.png`.
Original evidence remains under
`.collage-data-v3\users\local-dev\projects\p009-human-01\conversation`.

## Trial 2 (finished)

- Project: `p009-human-02`, 900x1600 portrait; user-led exploration, not a replay
  of Trial 1. Twelve proposals and two preserved-proposal selections; no
  acceptance. Final working proposal P012 is not a successful final design.
- User feedback: "I'm not quite as excited by the quality of the results"
  and "the main LLM stage for the layout takes a long time".
- The initial generation timed out within the 120-second deadline
  (116.828 seconds at the transport). Its input bound was 31,420, not a size
  rejection. Repeating the full prompt succeeded. No automatic or
  Copilot-initiated service retry occurred.
- Thirty actual calls: 16 interpretation, 14 generation; one timeout, one
  geometry correction, and one clarification question. Known usage:
  119,490 input + 94,973 output tokens; timeout attempt 2 has unknown usage,
  so these are not complete consumption totals.
- Completed generation calls took 3.7-80.0 seconds (median 39.2), versus
  1.4-5.5 seconds for interpretation. Slow calls were reasoning-heavy.
  High reasoning effort was unchanged; different prompts/canvases prevent
  attributing latency changes to compaction.
- Evidence: `conversation\events\000001.json` through `000030.json`,
  corresponding `requests\attempt-*.json`, and `proposals\P001` through `P012`
  under `.collage-data-v3\users\local-dev\projects\p009-human-02`.

### Prompt sequence

1. "Make an initial collage with a charcoal background. Start with photo 4 in the top right and photo 1 in the bottom left. Both should be larger than the other two photos. Photos 4 and 1 may overlap in the centre of the canvas and photo 4 should be stacked above photo 1." -> Fresh intent; generation timed out, no image.
2. "Make an initial collage with a charcoal background. Start with photo 4 in the top right and photo 1 in the bottom left. Both should be larger than the other two photos. Photos 4 and 1 may overlap in the centre of the canvas and photo 4 should be stacked above photo 1." -> P001.
3. "Grow all 4 photos. Photos 4 and 1 should reach closer towards their respective corners. Also the stacking of photos 4 and 1 was wrong last time." -> P002.
4. "Grow photo 4 by 25%. Swap the locations of photos 3 and 2." -> P003.
5. "Make photo 4 10% larger and move it closer to the top of the canvas. Make photo 1 30% larger and move it closer to the bottom of the canvas. Grow the other two images by 25% and tile photo 3 left by about 2 degrees." -> P004.
6. "Grow photo 1 by another 10% and move it sligtly further left. Shrink photo 4 by 10% and move it down a little. In case of overlap ensure photo 1 is stacked above the other photos." -> P005 after one containment correction.
7. "Move photo 4 closer to the right edge. Move photo 3 closer to the top edge. Tilt photo 2 slightly clockwise." -> P006.
8. "Tilt photo 2 some more please. I can't see the previous tilt I asked for." -> P007.
9. "Make the borders twice as thick on photos 1 and 4." -> P008.
10. "Bring the breakfast photo to the front." -> Asked "Which photo number is the breakfast photo?"; no new proposal.
11. "2" -> P009, breakfast brought forward; original task preserved.
12. "I changed my mind about the last two edits. Go back to the version where all borders were the same width." -> P010; edited current borders, failed to restore the earlier stacking.
13. "That only fixed the borders. I wanted to return to the exact collage from before both the border change and bringing breakfast forward—not make another edit to the current one." -> Selected P008, not the intended P007; breakfast behind, but thicker borders retained.
14. "Go back to P007 exactly as it was. Don’t make any further edits." -> Selected preserved P007, without generation.
15. "Remove the rounded corners from photo 3 only. Leave everything else unchanged." -> P011, correctly based on P007.
16. "Move the breakfast photo higher please so that it's closer to the bookshop photo." -> P012; incorrectly moved photo 1, without clarification.

Steps 13-15 used suggestions from Copilot in the observer conversation.
Those messages were deliberately entered by the user; observer commentary
was not injected into the collage agent.

### Findings

| Area | Evidence and outcome |
|---|---|
| Context size | Generation stayed around 35,000 after the recent window filled; final bound 35,129, actual input 6,863 tokens. Maximum bound 37,645 included correction feedback. No size rejection; stable size is not proof of adequate memory. |
| Clarification | The first breakfast request correctly asked for a number, then linked `2` to the original task. |
| Descriptive backtracking | First misclassified as edit/current; then correctly classified as selection but selected P008 instead of P007. These are separate action and source-resolution failures. |
| Exact restoration and follow-on edit | Explicit P007 selection worked. Recipe comparison confirmed P011 changed only photo 3's corner radius to zero relative to P007. |
| Lost name grounding | Before the final request, the three-exchange window no longer contained breakfast's number. The model guessed instead of clarifying. P012 moved photo 1's `center_y` from 0.7415 to 0.64; photo 2 was unchanged. No grounded bookshop mapping was supplied either. |
| Composition | Early previews left substantial empty space and prompted repeated enlargement requests. This is user/visual feedback, not a mechanical pass/fail score. |

The initial stacking complaint is retained verbatim, but P001's saved order
already placed photo 4 above photo 1. Do not count that complaint as a verified
stack-order inversion.

Read-only reconstruction also showed that clarification questions and answers
consume separate recent-history slots. This displaced useful pre-edit context
around the attempted backtrack. It may have contributed; this trial does not
isolate causation. Missing context never justifies confidently guessing a target.
All proposals and history remain preserved; no experimental fixes were applied
during observation.

### Follow-up handoff (implementation not yet approved)

The first four candidates below feed the proposed
[010 brief](010-grounded-interpretation-and-human-trials.md), which captures
subsequent scope refinements. Composition remains a separate future topic.

1. **Ground photo references before generation.** Clarify unknown names instead
   of passing an unresolved target to layout generation. Valid geometry does
   not establish that the correct photo was edited.
2. **Retain learned names compactly.** Consider a small user-confirmed photo-name
   map, separate from the rolling transcript, rather than a larger general memory.
3. **Resolve returns as returns.** Improve action/source selection and retain
   enough navigation evidence to identify earlier proposals. Count clarification
   answers as part of their originating task when interpreting "last two edits".
4. **Reduce latency without sacrificing correctness.** Consider reasoning effort
   appropriate to simple edits; retain explicit timeout handling. No automatic
   retries, longer limits, or model changes are authorized by this result.
5. **Improve composition and perceived edit strength.** Revisit canvas use and
   subtle-change expectations separately from deterministic rendering.

Compaction is a useful implemented milestone, not a solution to reference
grounding or evidence of satisfactory natural-language reliability. Follow-up
implementation and any further live work need their own approval under 010.

## Context follow-up after Trial 1

Read-only reconstruction found 13,405 UTF-8 bytes of event history in the
failed generation context, including raw response recipes and repeated
task/intent fields. A separate proposal catalogue, current recipe/geometry,
instructions, and schema add further input. These byte measurements are not
actual token counts; 51,041 is the conservative serialized-request bound.

The user approved a bounded window: original request, current layout/source,
current task and up to three recent exchanges. This is now implemented without
a generated summary or standing-instructions memory. Full audit data remains
on disk; older sources/tasks are loaded when selected. The proposal catalogue
is also bounded to relevant entries instead of growing with the transcript.

Preflight drops oldest recent exchanges if the actual serialized request still
exceeds the existing bound. Essential input is never cut; a remaining oversize
error reports the measured bound/limit rather than `ChatClientException`.

Read-only reconstruction of Trial 1's blocked turn through the real adapter
with mocked HTTP measured **34,961** for generation (previously **51,041**) and
12,853 for interpretation, both retaining three recent exchanges. These are
input bounds, not actual token usage or live model results. Evidence:
session artifact `files\009-context-offline-evidence.json`.

The full offline suite passed: **407 tests**, including bounded history growth,
older-source selection/retries, clarification/correction context, actual-payload
size trimming, clear local errors, and effective replay captures. All 885
pre-existing photo/runtime files and the user's staged index remained unchanged.
No live calls or chat recovery were performed.
