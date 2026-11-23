"""Deterministic task evidence and navigation; no generated memory summaries."""

import re

from pydantic import BaseModel, Field

from .models import (
    EditIntent, Exchange, FreshIntent, Intent, LayoutSource, LocalEvent, NavigationEvidence,
    PhotoName, Proposal, QuestionIntent, RetryIntent, SelectIntent,
)
from ..engine.models import CollageError, InputLayout
from .photo_references import (
    contains, mentioned_names, name_candidates, numbered_photos, reference_names,
)


class RecipeChange(BaseModel):
    field: str
    before: object
    after: object


def recipe_changes(before: InputLayout, after: InputLayout) -> list[RecipeChange]:
    def keyed(recipe: InputLayout) -> dict:
        value = recipe.model_dump(mode="json")
        value["stacking"] = [layer["photo_id"] for layer in value["layers"]]
        value["photos"] = {str(layer["photo_id"]): layer for layer in value.pop("layers")}
        return value

    def compare(old: object, new: object, path: str) -> list[RecipeChange]:
        if isinstance(old, dict) and isinstance(new, dict):
            return [change for key in sorted(old.keys() | new.keys())
                    for change in compare(old.get(key), new.get(key), f"{path}.{key}")]
        return [] if old == new else [RecipeChange(field=path, before=old, after=new)]

    return compare(keyed(before), keyed(after), "recipe")


class TaskRecord(BaseModel):
    task_id: int
    events: list[int]
    request: str
    outcome: str
    baseline_before: LayoutSource | None
    source: LayoutSource | None = None
    proposal_id: str | None = None
    predecessor: LayoutSource | None = None
    changed: bool = False
    changes: list[RecipeChange] = Field(default_factory=list)


def task_records(
    events: dict[int, Exchange | LocalEvent], proposals: dict[str, Proposal],
    initial: tuple[LayoutSource, InputLayout] | None = None,
) -> list[TaskRecord]:
    records: dict[int, TaskRecord] = {}
    published: dict[str, TaskRecord] = {}
    baseline = initial[0] if initial else None
    for number, event in events.items():
        if isinstance(event, LocalEvent):
            if event.kind == "accept":
                baseline = LayoutSource(proposal_id=event.proposal_id)
            continue
        if event.baseline_before != baseline:
            raise CollageError("Task baseline evidence does not match navigation history.")
        if event.outcome in {"proposal", "selection"} and event.proposal_id not in proposals:
            raise CollageError("Task outcome references an unpublished proposal.")
        if event.task_id not in records:
            if event.task_id != number:
                raise CollageError("Task has no originating event.")
            records[event.task_id] = TaskRecord(
                task_id=number, events=[], request=event.prompt, outcome="pending",
                baseline_before=baseline,
            )
        task = records[event.task_id]
        receipt = next((
            turn for turn in reversed(task.events)
            if isinstance(events[turn], Exchange) and events[turn].name_receipt is not None
        ), None)
        pending_receipt = receipt is not None and not any(
            isinstance(events[turn], Exchange) and events[turn].receipt_event == receipt
            for turn in task.events
        )
        unfinished = next((
            previous for previous in (events[turn] for turn in reversed(task.events))
            if isinstance(previous, Exchange) and not (
                previous.stage == "interpretation" and previous.outcome in {"invalid", "error"}
            )
        ), None)
        resumable = unfinished is not None and (
            unfinished.generation_timeout or unfinished.outcome == "question"
        ) or task.events and isinstance(events[task.events[-1]], Exchange) and (
            events[task.events[-1]].stage == "interpretation" and pending_receipt and (
                event.outcome in {"invalid", "error", "question", "name_confirmation"}
                or event.receipt_event == receipt
            )
        )
        if task.outcome in {"proposal", "selection", "acknowledgement", "inspection", "error"} and not resumable:
            raise CollageError("A completed task cannot acquire unrelated events.")
        task.events.append(number)
        task.outcome = event.outcome
        task.source = event.intent.source if event.intent else None
        task.proposal_id = event.proposal_id
        if event.outcome == "proposal":
            proposal = proposals[event.proposal_id]
            predecessor = proposal.intent.source
            if proposal.intent.action == "fresh":
                predecessor = task.baseline_before
            elif predecessor is None and proposal.intent.reference is not None:
                rejected = published.get(proposal.intent.reference.proposal_id)
                predecessor = rejected.predecessor if rejected else None
            task.predecessor = predecessor
            previous = (
                proposals[predecessor.proposal_id].recipe if predecessor and predecessor.proposal_id
                else initial[1] if predecessor and initial and predecessor == initial[0] else None
            )
            task.changes = recipe_changes(previous, proposal.recipe) if previous else []
            task.changed = previous != proposal.recipe
            published[proposal.proposal_id] = task
            baseline = LayoutSource(proposal_id=proposal.proposal_id)
        elif event.outcome == "selection":
            baseline = LayoutSource(proposal_id=event.proposal_id)
    return list(records.values())


def undo_target(records: list[TaskRecord], current: LayoutSource | None, steps: int) -> str:
    if steps <= 0:
        raise CollageError("Undo needs a positive change count.")
    by_proposal = {record.proposal_id: record for record in records if record.outcome == "proposal"}
    while steps and current and current.proposal_id:
        record = by_proposal.get(current.proposal_id)
        if record is None:
            break
        current = record.predecessor
        if record.changed:
            steps -= 1
    if steps or current is None or current.proposal_id is None:
        raise CollageError("Undo reaches beyond the available proposal history; clarify the destination.")
    return current.proposal_id


_ORDINALS = dict(zip(
    ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"),
    range(1, 11),
))
_COUNTS = {**_ORDINALS, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
           "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def ordinals(text: str) -> set[int]:
    words = re.findall(r"\b[a-z]+\b", text.lower())
    return {_ORDINALS[word] for word in words if word in _ORDINALS} | {
        int(value) for value in re.findall(r"\b([0-9]{1,9})(?:st|nd|rd|th)\b", text.lower())
    }


def undo_steps(text: str) -> int | None:
    match = re.search(
        r"\bundo\s+(?:(?:the|my)\s+)?(?:last\s+)?(?:(\d{1,9}|" +
        "|".join(_COUNTS) + r")\s+)?(?:edits?|changes?|steps?)\b", text.lower(),
    )
    if not match:
        return None
    token = match[1]
    return _COUNTS.get(token, int(token) if token and token.isdigit() else 1)


def navigation_request(text: str) -> bool:
    return re.search(r"\b(?:undo|return to|go back|back to|revert to)\b", text, re.I) is not None


def followup_edit(text: str) -> bool:
    return re.search(
        r"(?:\b(?:and|then|but|to)\s+|[,;]\s*)(?:please\s+)?(?:make|move|resize|remove|add|change|"
        r"bring|send|straighten|rotate|shrink|enlarge|edit)\b", text, re.I,
    ) is not None


def change_matches(
    text: str, change: RecipeChange, names: list[PhotoName], photo_ids: set[int] | None = None,
) -> bool:
    """Conservative vocabulary links to actual fields, not promises in old prompts."""
    field = change.field
    match = re.search(r"\.photos\.(\d+)\.", field)
    numbers = numbered_photos(text) | (photo_ids or set())
    for key in mentioned_names(text, reference_names(names)):
        targets = {item.photo_id for item in name_candidates(key, names)}
        if len(targets) != 1:
            return False
        numbers.update(targets)
    if match and numbers and int(match[1]) not in numbers:
        return False
    category = next((key for key in ("border", "corner", "crop") if key in field), None)
    if category and not re.search(
        {"border": r"\bborders?|\bfram", "corner": r"\bround|\bcorners?",
         "crop": r"\bcrop|\bzoom|\bpan"}[category], text, re.I,
    ):
        return False
    if isinstance(change.before, (int, float)) and isinstance(change.after, (int, float)):
        if re.search(r"\b(?:thicker|thicken\w*|bigger|larger|wider|increas\w*)\b", text, re.I):
            if change.after <= change.before:
                return False
        if re.search(r"\b(?:thinner|smaller|narrower|shrink\w*|decreas\w*)\b", text, re.I):
            if change.after >= change.before:
                return False
        if "center_y" in field:
            if re.search(r"\bhigher\b|\bup\b", text, re.I) and change.after >= change.before:
                return False
            if re.search(r"\blower\b|\bdown\b", text, re.I) and change.after <= change.before:
                return False
        if "center_x" in field:
            if re.search(r"\bleft\b", text, re.I) and change.after >= change.before:
                return False
            if re.search(r"\bright\b", text, re.I) and change.after <= change.before:
                return False
    vocabulary = {
        "border": r"\bborders?|\bfram",
        "corner": r"\bround|\bcorners?",
        "rotation": r"\btilt|\bstraight|\brotat",
        "center_x": r"\bleft\b|\bright\b|\bmov|\bposition",
        "center_y": r"\bhigher\b|\blower\b|\bup\b|\bdown\b|\bmov|\bposition",
        "width": r"\bsmall|\bbigg|\blarg|\bshrink|\bresiz|\bwidth|\bwider|\bnarrow",
        "height": r"\bsmall|\bbigg|\blarg|\bresiz|\bheight|\btall|\bshort",
        "stacking": r"\bfront|\bforward|\bbehind|\bback\b|\bstack|\boverlap",
        "background": r"\bbackground",
        "crop": r"\bcrop|\bzoom|\bpan",
    }
    return any(key in field and re.search(pattern, text, re.I)
               for key, pattern in vocabulary.items())


def ancestry(records: list[TaskRecord], current: LayoutSource | None) -> set[str]:
    result = set()
    by_proposal = {r.proposal_id: r for r in records if r.outcome == "proposal"}
    cursor = current
    while cursor and cursor.proposal_id in by_proposal and cursor.proposal_id not in result:
        result.add(cursor.proposal_id)
        cursor = by_proposal[cursor.proposal_id].predecessor
    return result


def matching_records(
    text: str, records: list[TaskRecord], current: LayoutSource | None, names: list[PhotoName],
    photo_ids: set[int] | None = None,
) -> list[TaskRecord]:
    matches = [
        record for record in records if record.outcome == "proposal"
        and any(change_matches(text, change, names, photo_ids) for change in record.changes)
    ]
    latest = re.search(r"\b(?:last|latest|most recent)\b", text, re.I) is not None
    if latest or re.search(r"\b(?:current|this)\s+(?:branch|lineage)\b", text, re.I):
        chain = ancestry(records, current)
        matches = [record for record in matches if record.proposal_id in chain]
    if latest:
        return matches[-1:]
    return matches


def retrieve(
    records: list[TaskRecord], prompt: str, current: LayoutSource | None, names: list[PhotoName],
) -> list[TaskRecord]:
    tokens = set(re.findall(r"[a-z]{3,}", prompt.lower())) - {
        "the", "and", "that", "please", "photo", "before", "after", "back", "return",
    }
    chain = ancestry(records, current)
    matches = {record.task_id for record in matching_records(prompt, records, current, names)}

    def score(record: TaskRecord) -> tuple[int, int]:
        actual = sum(change_matches(prompt, change, names) for change in record.changes)
        overlap = len(tokens & set(re.findall(r"[a-z]{3,}", record.request.lower())))
        return (int(record.task_id in matches) * 100 + actual * 10 + overlap * 2
                + int(record.proposal_id in chain), record.task_id)

    recent = {record.task_id for record in records[-3:]}
    return sorted(
        (record for record in records if record.task_id not in recent), key=score, reverse=True,
    )[:12]


def navigation_target(
    evidence: NavigationEvidence, text: str, records: list[TaskRecord],
    current: LayoutSource | None, names: list[PhotoName], visible: set[int],
    photo_ids: set[int] | None = None,
) -> str:
    if not contains(text, evidence.text):
        raise CollageError(
            "Navigation quote is absent from the task/answer. Quote the actual user wording, "
            "not the resolved proposal ID. For creation-ordinal wording such as 'first proposal', "
            "use kind 'ordinal' with that wording; keep the resolved ID in proposal_id/source."
        )
    published = [record for record in records if record.outcome == "proposal"]
    if evidence.kind == "id":
        ids = re.findall(r"\bP[0-9]{3,}\b", evidence.text)
        if len(set(ids)) != 1 or ids[0] not in {record.proposal_id for record in published}:
            raise CollageError(
                "Navigation requires one explicit published proposal ID. Use kind 'id' only "
                "when the quoted user wording contains that ID. For creation-ordinal wording "
                "such as 'first proposal', use kind 'ordinal', not 'id'."
            )
        target = ids[0]
    elif evidence.kind == "ordinal":
        positions = ordinals(evidence.text)
        if len(positions) != 1 or not 1 <= next(iter(positions)) <= len(published):
            raise CollageError("Navigation ordinal has no unique published destination.")
        target = published[next(iter(positions)) - 1].proposal_id
    elif evidence.kind == "undo":
        count = undo_steps(evidence.text)
        if count is None or count <= 0 or count != evidence.steps:
            raise CollageError("Undo count does not match the user's wording.")
        target = undo_target(records, current, count)
    else:
        record = next((record for record in records if record.task_id == evidence.task_id), None)
        if record is None or record.task_id not in visible or record.outcome != "proposal":
            raise CollageError("Descriptive navigation requires visible task evidence.")
        changes = [change for change in record.changes if change.field == evidence.field]
        if not changes or not any(change_matches(text, change, names, photo_ids) for change in changes):
            raise CollageError("Navigation field evidence does not support this description.")
        if record not in matching_records(text, records, current, names, photo_ids):
            raise CollageError("Navigation evidence contradicts the requested branch/recency.")
        if not re.search(rf"\b{evidence.kind}\b", evidence.text, re.I):
            raise CollageError("Navigation before/after relationship is absent from the quote.")
        source = record.predecessor
        target = record.proposal_id if evidence.kind == "after" else source.proposal_id if source else None
    if target is None:
        raise CollageError("Navigation has no preserved proposal destination; clarify.")
    return target


def validate_navigation(
    reply: Intent, prompt: str, task_request: str, records: list[TaskRecord],
    current: LayoutSource | None, names: list[PhotoName], visible: set[int],
    pending: QuestionIntent | None,
) -> None:
    confirmation = pending.return_confirmation if pending and reply.continues_task else None
    affirmative = re.fullmatch(
        r"(?:yes|yes please|correct|that's correct|that is correct)[.! ]*", prompt.strip(), re.I,
    ) is not None
    negative = re.fullmatch(r"(?:no|no thanks|not that one)[.! ]*", prompt.strip(), re.I) is not None
    candidate = reply.return_confirmation if isinstance(reply, QuestionIntent) else None
    target = (
        candidate.proposal_id if candidate else reply.proposal_id if isinstance(reply, SelectIntent)
        else reply.source if isinstance(reply, EditIntent) and reply.source != "current" else None
    )
    evidence = candidate.evidence if candidate else reply.navigation
    if confirmation and not isinstance(reply, QuestionIntent):
        if not affirmative or target != confirmation.proposal_id or reply.action != confirmation.action:
            raise CollageError("Pending return needs its exact confirmed destination/action.")
        if evidence != confirmation.evidence:
            raise CollageError("Confirmed return evidence changed.")
        return
    if pending and pending.return_confirmation and negative and not isinstance(reply, QuestionIntent):
        raise CollageError("A rejected return must clarify, not change the layout.")
    text = task_request + "\n" + prompt
    if navigation_request(text) and isinstance(reply, (FreshIntent, RetryIntent)):
        raise CollageError("A return is selection or an older-source edit, not fresh/retry.")
    if (
        navigation_request(text) and not followup_edit(text)
        and (isinstance(reply, EditIntent) or candidate and candidate.action != "select")
    ):
        raise CollageError("A pure return must select its preserved proposal without generation.")
    if isinstance(reply, QuestionIntent) and not candidate:
        return
    needs_evidence = target is not None or (
        navigation_request(text) and isinstance(reply, EditIntent)
    )
    if not needs_evidence:
        if evidence is not None:
            raise CollageError("Navigation evidence has no target action.")
        return
    count = undo_steps(text)
    if count is not None and undo_target(records, current, count) != target:
        raise CollageError("Navigation target contradicts the requested undo count.")
    if evidence is None:
        # Literal IDs are already exact user evidence; descriptive references are not.
        if target and re.search(r"\b" + re.escape(target) + r"\b", text):
            return
        raise CollageError("A return/older-source edit requires grounded destination evidence.")
    photo_ids = {item.photo_id for item in reply.references if item.photo_id is not None}
    resolved = navigation_target(evidence, text, records, current, names, visible, photo_ids)
    if resolved != target:
        raise CollageError("Navigation destination contradicts its cited evidence.")
    if evidence.kind in {"before", "after"} and not candidate:
        alternatives = set()
        for record in matching_records(text, records, current, names, photo_ids):
            source = record.predecessor
            alternative = record.proposal_id if evidence.kind == "after" else source.proposal_id if source else None
            if alternative:
                alternatives.add(alternative)
        if len(alternatives) > 1:
            raise CollageError("Several preserved changes match; ask to confirm a concrete destination.")
