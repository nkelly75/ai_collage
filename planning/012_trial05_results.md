# 012 human-led trial 05 and phase closeout

**Status:** Successful; phase 012 closed at the user's request on
23 November 2026. This is human feedback and sign-off for the bounded phase,
not just an inference from scripted success.

## Trial and feedback

The user ran `p012-human-05` with the four original London photos. Saved events
contain **15 user messages**, including three clarification answers and the
closing compliment, producing **11 proposals through P011**.
See the [collage story](012_result_05.png) for exact prompts, clarifications and
the original saved intermediate images.

The user reported:

> That human led trial went really well.

> I think we have a more reliable solution that feels more predictable in how it works.

The interaction covered numbered edits, contextual references such as breakfast,
bridge and Eye, resizing, positioning, stacking, swapping and reduced tilt.
Identity questions for breakfast/London Eye, Tower Bridge and book shop continued
their original edits after the user's answers. No durable names were saved;
these were task-local clarifications, not implicit teaching or repeated naming
approval gates.

Two rejected layout attempts during enlargement and one rejected reference-evidence
attempt were corrected within their original tasks and still produced proposals.
The user judged the overall interaction successful: useful, recoverable progress
remains the aim, rather than error-free model responses.

## Accepted compliment blip

The final message, **"That's perfect!"**, produced two rejected interpretation
responses rather than an acknowledgement. It made no new image or acceptance;
the last good working collage remained P011.
The user explicitly accepted this blip:

> I'm fine with the last blip - I was just curious how it would handle a compliment.

It is recorded as a limitation, not a blocker or authorization for another fix.
The user's phase sign-off is distinct from the application's explicit proposal
acceptance: this project has no accepted proposal/version.

## Evidence and closure

Trial evidence remains in
`.collage-data-v3\users\local-dev\projects\p012-human-05`: project metadata,
conversation events, proposal recipes/previews, request records and final state.
The story was extracted offline from these files; preview digests and the
unchanged trial/source-photo hashes were checked during its creation.
Its extraction record is in session artifacts at
`files\012-human-05-story\evidence.json`.

The [offline implementation](012_results.md),
[original replay pass](012_replay_results.md) and
[return repair/retest](012_return_repair_results.md) retain their separate
evidence, outcomes and closed budgets. Together with this human trial, they
support closing 012 as a successful, more coherent and predictably usable
improvement. Multiple-label, four-beach and other broader semantic scenarios
are not established by this trial; general reliability and broader Phase 1
completion remain unclaimed.

The user requested tracker closure and will handle the commit. This documentation
closeout adds no model calls, fixes, dependency changes or Git operations.
Further trials, refactoring, branch changes, PRs and merges need separate approval.
