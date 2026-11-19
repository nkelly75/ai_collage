# 007: Vision for photos and collage feedback

**Status:** Exploratory discussion, not an implementation or evaluation brief.
Capturing these ideas does not select the next implementation phase or authorize
image uploads, model calls, new dependencies, a UI, or changes to project state.
The [006 results](006_results.md) remain the metadata-only baseline.

## Direction

Keep original photos and deterministic rendering. Add image understanding as
advisory information for natural-language references, composition and feedback,
not AI regeneration of the photographs or model-owned geometry validation.

There are two vision opportunities:

1. Understand a rendered collage and combine that understanding with human
   feedback to propose a useful, targeted change.
2. Understand input photos: concise descriptions, important subjects and their
   locations, with other visual traits as possible later additions.

Preview understanding plus human feedback is a particularly promising direction,
not something that must wait until all input-photo analysis is implemented.
Brightness, contrast, saturation and colour analysis are lower-priority ideas.
The exact first vision increment remains open.

Project lifecycle is a separate topic, captured in
[008: Project lifecycle and interactive iteration](008-project-lifecycle-and-interactive-iteration.md).
That is the next discussion, not an authorization to implement or run a trial.

## Input-photo understanding

| Candidate information | Potential use | Caution |
|---|---|---|
| Short editable label, e.g. "London Eye at night" | Refer to a photo by description as well as number | Labels may be wrong or ambiguous; keep stable numbers and ask when needed |
| Main subject(s) and approximate regions | Prefer overlaps away from important content; later guide cropping | The subject can be irregular, thin, multiple or uncertain; a rectangle is an approximation |
| Brightness, contrast, saturation and dominant colours | Balance visual weight, group related photos or create contrast | There is no universal rule that similar photos should be together or apart |
| Technical concerns such as blur, noise, exposure or compression | Suggest a smaller presentation or flag an issue | Technical quality does not establish personal importance or whether a photo is liked |
| Contextual emphasis suggestion with a reason | Help choose a starting hierarchy | User intent overrides the suggestion; do not silently omit or demote photos |

### Names and references

A concise label could make "move the breakfast" work without losing "photo 2".
Descriptions should be short enough to scan, distinguish this project's photos,
and be user-correctable. Do not invent personal identities or relationships.
If two photos show breakfast, use their numbers or ask which one; confident
wording is not reliable disambiguation.

### Subjects and protected regions

For the London Eye, preserving the wheel may matter more than preserving every
pixel of sky, pavement or reflections. The useful concept is "important content",
not necessarily an object centred in the image. A landscape might have several
important regions or no single dominant subject.

An initial approach could use conservative subject rectangles with labels,
uncertainty and user corrections, rather than starting with segmentation.
Coordinates would be relative to the oriented source image, with an explicit
coordinate convention; they are not canvas coordinates. Any later calculation
must map them through whole/cover placement, crop/pan/zoom, borders, rotation and
stacking before estimating obstruction. A box alone cannot guarantee protection
of a thin structure such as a wheel or every important detail.

Keep subject importance advisory initially. If a user later explicitly protects
a region, define whether that is a hard constraint and what happens when the
requested arrangement cannot satisfy it. Do not quietly reinterpret confidence
or a model guess as a hard rendering rule.

### Brightness is not saturation

Lower-priority exploration, not a prerequisite for useful preview analysis.

Brightness describes light/dark appearance; saturation describes colour
intensity. Contrast is the difference between light and dark areas. A dark night
photo can still contain strongly saturated lights.

Basic brightness/colour/contrast measurements can be calculated locally and
repeatably; an LLM is more useful for their contextual meaning. For example, a
bright sky and a dark foreground can make a single average misleading. Similar
dark photos might form a coherent group, or spreading them out might balance
the canvas. These are competing design choices, not a fixed sorting rule.

### Avoid one authoritative "quality" score

Separate technical condition, aesthetic preference and importance to this
collage. Breakfast might be technically fine but a weaker hero image for a
London-travel collage; it might instead be the user's favourite memory.
Prefer a short reasoned suggestion ("less suitable as the main image for this
brief") over an apparently objective 7/10. Even a future scale would need a
defined purpose and should not overrule the user's chosen emphasis.

## Understanding the rendered collage

Combine the actual preview with the recipe and the user's current feedback.
The preview shows what the user sees; source photos or their observations can
help identify content already hidden by another layer when needed. A complete
input-photo analysis pipeline is not necessarily required for a useful first step.

Useful questions include:

- Is the requested subject visible, including after overlaps or cropping?
- Is empty space deliberate, or are the photos unnecessarily small/clustered?
- Are overlaps shallow and unobtrusive, or do they hide important content?
- Does hierarchy match the user's requested emphasis?
- Are spacing, visual weight, colour and light/dark balance coherent for this
  design, rather than for a single preferred template?
- Does a follow-up address the complaint without changing unrelated choices?

Keep exact questions in ordinary code where possible: authored-field changes,
frame containment, visible union area and geometric overlap are not matters for
an LLM to estimate from a screenshot. Computing subject-region obstruction could
also be deterministic once trustworthy regions and transforms exist. Such
numbers inform design; high canvas coverage alone is not good design.

Model critique should identify the affected photo/region, a concrete observation
and a suggested action, not merely award a score. "The bookshop covers part of
the bridge" is more actionable than "composition: 6/10". User feedback such as
"too busy" might mean overlap, uneven spacing or too many style effects: use
image evidence, but clarify rather than assume when the interpretation matters.

Preview analysis could first be an explicit "review this" operation. Any future
automatic critique/revision loop needs its own small call/iteration cap and must
stop with a useful result or explanation, not keep redesigning until it declares
itself satisfied. Do not immediately turn every user edit into extra review calls.
This would be a separately approved product capability, not a resurrection of
the retired fixed evaluator or a requirement for an automated aesthetic judge.

## Incremental approach and boundaries

Prefer a targeted experiment over a combined analysis pipeline. A candidate
starting point is one generated preview plus a human complaint: can vision
identify the relevant issue and help produce a targeted revision without
changing unrelated choices? For example, connect "the wheel is hidden" to the
overlapping photo and suggest a suitable move. Clarify ambiguity rather than
treating model interpretation as the user's intent.

Concise photo labels and subject regions remain useful possible increments,
but are not mandatory predecessors. Add source-image analysis where it resolves
a concrete limitation, such as a subject no longer visible in the preview.
Defer broad quality scoring and colour/contrast analysis unless evidence shows
they address a real need. Compare with the metadata-only workflow before
coupling several new analysis stages.

Analyze a photo once where practical and reuse observations until its image,
analysis configuration or user annotations change. Keep source identity, model/
prompt identity and user corrections distinguishable. Observations belong in
separate metadata, not necessarily in the layout recipe. Do not choose a new
layout format or persistence schema during brainstorming.

Vision would send actual image content rather than today's dimensions-only
context: it needs explicit consent, provider/privacy review, supported-image
and resolution checks, usage accounting and a newly bounded live experiment.
Current provider/model vision support, cost and coordinate accuracy are not
verified here. Stored observations may themselves reveal private photo content.
Treat text found inside photos as untrusted content, never as agent instructions.

Preserve offline rendering and the metadata-only path. Missing or uncertain
analysis must be visible, not silently presented as successful understanding.
Do not add hidden vision calls to imports or existing offline tests.

Before any implementation brief, settle which problem is first, whether review
is explicit or automatic, user control over labels/importance/protected regions,
and the success criteria and service limits. A bounded comparison should include
ambiguous labels, off-centre/multiple subjects, night imagery, subject-covering
overlaps and an intentionally airy layout. Compare usefulness, mistakes, user
effort and cost, not just self-reported model confidence.

The next step to implement remains undecided. Lifecycle discussion continues in
008; a user-led trial or vision experiment each needs its own agreed scope and
authorization. The number 007 does not require vision to be implemented next.
