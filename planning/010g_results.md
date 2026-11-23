# 010g: Human-led trial observations

**Status:** Trial 03 stopped by the user; findings await review, not product
sign-off. No further run has been started. Trial instructions:
[010g](010g-user-led-natural-language-trial.md). No implementation fixes or
Copilot-initiated live calls were made while observing this run.

## Trial 03: p010g-human-03

1200x1800 (2:3), usual four photos, high interpretation / low generation.
Evidence remains under
`.collage-data-v3\users\local-dev\projects\p010g-human-03\conversation`.
Final observation snapshot for this run: events and requests 1-33.

The user reported that the first three design requests worked pretty well.
The recorded sequence so far:

1. "Make an initial collage with a navy background. Put photo 1 in the bottom left and photo 4 in the top right. Make them bigger than the other photos." -> P001.
2. "Swap the locations of the breakfast and london eye photos" -> Identity question; user answered "2 for breakfast and 3 for london eye" -> Learned both names and produced P002.
3. "Good. Now make each photo about 40% larger. Keep the rough locations but adjust to ensure they don't fall off the edge." -> P003.
4. "Good. Grow each photo by another 20%. Also change the tilt of the breakfast photo it's rotated more clockwise." -> Interpretation succeeded; all three generation responses failed geometry validation. No proposal published; baseline remained P003 at this stop.

### Reliability defect: unsuccessful geometry correction

Record as a generation/correction reliability issue, not an interpretation
identity failure, service error or demonstrated renderer bug:

- Event/request 9 enlarged the photos but photo 1's sampled rotated footprint
  extended 4px below the canvas. Feedback supplied a safe vertical centre range.
- Event/request 10 used the supplied safe centre for photo 1 but left photo 4
  extending 49px beyond the right edge. That response restored photo 4's old
  horizontal centre instead of its preceding attempted inward adjustment.
- Event/request 11 moved photo 4 inward but reset photo 1's vertical centre
  to 0.77, repeating the first 4px overshoot. The bounded call allowance was
  exhausted without a valid proposal.

The model failed to retain earlier geometry corrections across attempts.
Validation protected the saved baseline; this was not a partial applied edit.
All requests completed at the service; the issue was invalid layout output.
The first failed generation also changed breakfast's rotation from -2 to -4
degrees, opposite the requested clockwise direction (positive is clockwise).
Later rejected responses used 0 and +1 respectively. None was published.
These observations do not establish whether high generation would behave better.

### Assisted continuation: P004

Copilot suggested this next message, explicitly allowing inward repositioning
and making the desired tilt unambiguous:

> From P003, make all four photos 20% larger, moving them inward wherever needed
> so the entire rotated frames stay inside the canvas. Set breakfast (photo 2)
> to a clockwise tilt of 3 degrees. Keep the background, borders, corners and
> stacking unchanged.

The user entered the suggested message. Events/requests 12-13 produced P004
without a correction: all four widths increased by 20%, centres moved inward,
and breakfast's rotation became +3 degrees. Background, borders, corners and
stacking were preserved. The user reported, "That went better."
This was a user-entered assisted continuation, not a Copilot-run retry.

### Identity-answer typo and lost continuation

The next user request was "Stack the london bridge photo so it overlaps the
bookshop." Neither name had been taught, so event 14 asked:
"Which photo numbers are the london bridge photo and the bookshop photo?"

The user answered "the bridge is photo 1 and the bookshop is both 4", later
identifying "both 4" as a typo. Both interpretation attempts (events 15-16)
were rejected with "Name update is not supported by this statement or pending
answer." No generation occurred; neither new binding was saved, and baseline
remained P004. Do not classify the mistyped answer itself as an application
bug; whether the conversation recovers cleanly is a separate observation.

Copilot suggested answering with the exact pending names and unambiguous
bindings (assisted):

> Photo 1 is london bridge. Photo 4 is bookshop.

The user entered this answer. Event/request 17 learned both names but returned
`remember` with `continues_task: false`: an acknowledgement, not completion of
the original overlap request. Baseline remained P004. Record this as a
clarification-recovery issue: the intended supplemental correction was treated
as an independent naming task. The preceding typo alone does not explain away
this later failure to continue.

### Reference-text mismatch and user-facing diagnostic

The user then wrote "Now try my stacking request again. Remember, I want the
bridge to be overlapped above the bookshop."

Both interpretation attempts (events/requests 18-19) emitted reference text
"london bridge", although the new request says "bridge". The local grounding
guard requires reference text to occur in the current request/task; it rejected
both responses with:

> Photo reference text is absent from the current task/answer. Bind only
> individually identified photos; keep collective instructions in the task
> rather than enumerating group members.

The correction repeated the same mismatch. No generation occurred and baseline
remained P004. This is a separate interpretation/grounding recovery defect,
not another occurrence of the user's typo or a missing saved photo identity.
The name "london bridge" is saved as photo 1, but the shorter alias "bridge"
has not independently been taught.

The user questioned exposing this internal diagnostic and suggested a simpler
message that makes clear they can continue. Track a presentation improvement:
retain full diagnostics in evidence, but explain the actionable problem and
known state to the user. For this verified pre-generation rejection, wording
could be "I couldn't resolve the photo references. Your collage is unchanged;
try using photo numbers or the exact names you taught me." Do not generalize
the unchanged-state assurance to unrelated publication/I/O failures. No
presentation or validation changes were made during the trial.

Copilot suggested this assisted next message:

> Go back to P003 exactly as it was. Don't make any further edits.

### Exact return and further editing

The user entered the suggested return. Event/request 20 selected preserved
P003 from P004 without generation. This is a successful exact-ID navigation
observation.

The user then repeated the assisted enlargement/tilt request from P003.
Event/request 21 was rejected because it supplied only numbered reference
"photo 2", omitting a resolved reference for the mentioned learned name
"breakfast". The permitted interpretation correction supplied the name
reference (22), and generation produced P005 (23).

"Move the breakfast towards the bottom right corner" then produced P006
(24-25): only photo 2's centre changed, from (0.69, 0.69) to (0.78, 0.80).
Direct learned-name editing worked here; user satisfaction with this particular
result has not separately been stated.

### Yes/no question without an actionable confirmation

The user requested "Grow the bridge photo by 10% ensuring it stays within the
canvas. Also stack it above photo 4."

Event/request 26 was rejected for an untaught name reference "bridge photo".
The interpretation correction (27) asked:

> Do you mean photo 1 (london bridge) when you say the bridge photo?

The user reasonably answered "Yes." Both interpretation attempts failed:

- Event/request 28 supplied numbered reference "photo 1", but neither the
  original task nor "Yes." explicitly supplied that number for the bridge.
  Without a validated identity confirmation, the grounding guard rejected it.
- Event/request 29 instead tried to teach "bridge photo" = 1 with quote "Yes.",
  rejected as an unsupported name update.

The question's response JSON contained no structured `confirmation`, although
its prose invited confirmation of a specific identity. Existing grounding
requires that structured evidence to validate a yes-answer name binding.
This is a mismatch between the question the model asks and what the application
can safely act on, not an unreasonable answer or another user typo.
Both failed answer requests used high interpretation; their HTTP durations
totalled 46.16s. No generation occurred, no alias was saved and actual baseline
remained P006. This failure cannot be attributed to low generation.

Track as a clarification-protocol/recovery defect in addition to the previously
recorded internal-error presentation issue. Friendlier wording alone would not
make the invited "Yes" actionable. No implementation changes were made.

Overall observation so far: exact-ID restoration and several direct edits
work, but alias handling and continuation through clarification remain brittle.
Copilot suggested this explicit-number workaround as an assisted replacement
request:

> Starting from P006, grow photo 1 by 10%, moving it inward if needed to keep
> its entire rotated frame inside the canvas. Place photo 1 above photo 4 in
> the stacking order. Leave everything else unchanged.

### Final successful edits and stopping point

The user entered the assisted replacement request. Events/requests 30-31
produced P007 without a correction: photo 1's width increased from 0.504 to
0.5544 (10%) and its layer moved above photo 4; other authored fields were
preserved.

The user's final request was "Move the london eye closer to the top and tilt
it to the left (anticlockwise) instead of its current tilt to the right."
Events/requests 32-33 produced P008 without a correction: only photo 3's
vertical centre changed from 0.31 to 0.24 and its rotation from +2 to -2 degrees.
The user reported that the last message "worked pretty well" and chose to stop
for discussion of next steps.

Final working baseline: **P008**, unaccepted. Eight proposals and one preserved
proposal selection are recorded. No trial data was repaired, no application
code changed and no live calls were made by Copilot. The key follow-up findings
are geometry-correction retention, alias/clarification continuity, actionable
yes/no confirmation and user-facing error presentation; these are recorded
issues, not authorization to implement fixes.
