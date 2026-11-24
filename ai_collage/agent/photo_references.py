"""Validate binding/data facts; language interpretation belongs to the model."""

import hashlib
import json
import re
from collections.abc import Iterable

from .models import (
    INTENT, Exchange, InspectNamesIntent, Intent, MemoryIntent, NameReceipt, NameUpdate,
    NamesIntent, PhotoName, PhotoReference, QuestionIntent,
)
from ..engine.models import CollageError


class PhotoReferenceError(CollageError):
    """A rejected interpretation, not a damaged name/history record."""


def name_key(text: str) -> str:
    return " ".join(text.split()).casefold()


def active_names(names: list[PhotoName]) -> list[PhotoName]:
    return [item for item in names if item.photo_id is not None]


def memory_changes(
    updates: list[NameUpdate], names: list[PhotoName], number: int,
    receipt_event: int | None = None,
) -> tuple[list[PhotoName], list[PhotoName]]:
    changes = [
        PhotoName(name=" ".join(item.name.split()), photo_id=item.photo_id,
                  event_id=number, quote=item.quote, receipt_event=receipt_event)
        for item in updates
    ]
    current = {name_key(item.name): item for item in names}
    current.update({name_key(item.name): item for item in changes})
    return changes, list(current.values())


def memory_message(updates: list[NameUpdate] | list[PhotoName]) -> str:
    parts = []
    for label, items in (
        ("Remembered", [f"{item.name} = photo {item.photo_id}" for item in updates if item.photo_id is not None]),
        ("Forgot", [item.name for item in updates if item.photo_id is None]),
    ):
        if items:
            parts.append(label + ": " + "; ".join(items) + ".")
    return " ".join(parts) or "Photo names unchanged."


def names_message(names: list[PhotoName]) -> str:
    current = active_names(names)
    if not current:
        return "No photo names learned yet. You can refer to photos by number."
    return "Names I know: " + "; ".join(
        f"{item.name} = photo {item.photo_id}"
        for item in sorted(current, key=lambda item: (item.photo_id, name_key(item.name)))
    ) + "."


def conflicting_names(updates: list[NameUpdate], names: list[PhotoName]) -> bool:
    current = {name_key(item.name): item.photo_id for item in active_names(names)}
    return any(item.photo_id is not None and name_key(item.name) in current
               and current[name_key(item.name)] != item.photo_id for item in updates)


def names_digest(names: list[PhotoName]) -> str:
    return hashlib.sha256(json.dumps(
        [item.model_dump(mode="json") for item in names], sort_keys=True,
    ).encode("utf-8")).hexdigest()


def receipt_question(receipt: NameReceipt, names: list[PhotoName]) -> str:
    previous = {name_key(item.name): item.photo_id for item in active_names(names)}
    lines = [
        (f"{item.name} = photo {item.photo_id}" if item.photo_id is not None else f"forget {item.name}")
        + (f" (was photo {previous[name_key(item.name)]})"
           if name_key(item.name) in previous else "")
        for item in receipt.updates
    ]
    suffix = " The requested layout action is paused until you confirm." if receipt.intent else ""
    return "Remember these names: " + "; ".join(lines) + "? Please confirm or tell me what to correct." + suffix


def contains(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(name_key(phrase)) + r"(?!\w)", name_key(text)) is not None


def numbered_photos(text: str) -> set[int]:
    number = r"[0-9]{1,9}(?!\w|\.[0-9]|%)"
    lists = re.finditer(
        r"\b(?:photos?|images?|pictures?)\s+(" + number
        + r"(?:\s*(?:,\s*(?:and\b\s*)?|\band\b|&)\s*" + number + r")*)",
        text, re.IGNORECASE,
    )
    return {int(value) for match in lists for value in re.findall(r"[0-9]+", match[1])}


def number_identity(text: str) -> int | None:
    match = re.fullmatch(r"(?:photo\s+|image\s+|picture\s+)?([0-9]{1,9})", name_key(text))
    return int(match[1]) if match is not None else None


def name_candidates(text: str, names: list[PhotoName]) -> list[PhotoName]:
    return [item for item in active_names(names) if name_key(text) == name_key(item.name)]


def reference_names(names: list[PhotoName]) -> set[str]:
    return {name_key(item.name) for item in active_names(names)}


def mentioned_names(text: str, names: Iterable[str]) -> set[str]:
    spans: list[tuple[int, int]] = []
    found = set()
    for key in sorted(names, key=len, reverse=True):
        for match in re.finditer(r"(?<!\w)" + re.escape(key) + r"(?!\w)", name_key(text)):
            if not any(match.start() < end and start < match.end() for start, end in spans):
                found.add(key)
                spans.append(match.span())
    return found


def name_history(names: list[PhotoName], events: dict[int, object], photos: set[int]) -> int | None:
    recorded: dict[str, PhotoName] = {}
    pending: tuple[int, Exchange] | None = None

    def proposed(number: int, event: Exchange) -> list[NameUpdate]:
        reply = INTENT.validate_json(event.response or "")
        origin = events.get(event.task_id)
        if not isinstance(origin, Exchange):
            raise CollageError("Photo-name write has no task origin.")
        return ground_references(
            reply, event.prompt, task_request=origin.prompt if reply.continues_task else event.prompt,
            photos=photos, names=list(recorded.values()),
            reference_history={turn: entry for turn, entry in events.items()
                               if turn < number and isinstance(entry, Exchange)},
            evidence_events={turn: entry for turn, entry in events.items()
                             if turn < number and isinstance(entry, Exchange)
                             and entry.task_id == event.task_id},
            event_id=number,
        )

    for number, event in events.items():
        if not isinstance(event, Exchange):
            continue
        if event.outcome == "inspection":
            reply = INTENT.validate_json(event.response or "")
            if (
                not isinstance(reply, InspectNamesIntent) or event.name_updates or event.receipt_event
                or event.intent is not None or event.references or event.name_receipt is not None
            ):
                raise CollageError("Photo-name inspection changed memory.")
            continue
        if pending is not None and event.task_id != pending[1].task_id:
            pending = None
        if event.name_receipt is not None:
            receipt = event.name_receipt
            origin = events.get(receipt.intent.task_turn) if receipt.intent is not None else None
            if (
                event.outcome != "name_confirmation" or event.stage != "interpretation"
                or event.name_updates or event.receipt_event is not None
                or receipt.baseline != event.baseline_before
                or receipt.intent is not None and (
                    receipt.intent.task_turn > number or not isinstance(origin, Exchange)
                    or origin.prompt != receipt.intent.task_request
                )
                or receipt.names_digest != names_digest(list(recorded.values()))
                or any(
                    update.photo_id is not None and update.photo_id not in photos
                    or number_identity(update.name) is not None and number_identity(update.name) != update.photo_id
                    or not contains(update.quote, update.name)
                    or not any(
                        isinstance(origin, Exchange) and origin.task_id == event.task_id
                        and turn <= number and update.quote in origin.prompt
                        for turn, origin in events.items()
                    )
                    for update in receipt.updates
                )
            ):
                raise CollageError("Naming receipt has invalid user/photo evidence.")
            if proposed(number, event) != receipt.updates:
                raise CollageError("Naming receipt differs from its proposed user evidence.")
            if receipt.intent is not None:
                _, effective = memory_changes(receipt.updates, list(recorded.values()), number)
                check_forgotten(receipt.intent.references, effective, {
                    turn: entry for turn, entry in events.items()
                    if turn < number and isinstance(entry, Exchange)
                })
            pending = (number, event)
            continue
        if event.receipt_event is not None:
            decision = INTENT.validate_json(event.response or "")
            if (
                pending is None or pending[0] != event.receipt_event
                or not isinstance(decision, NamesIntent)
                or decision.receipt_event != event.receipt_event
                or pending[1].name_receipt.baseline != event.baseline_before
                or (decision.decision == "approve") != bool(event.name_updates)
            ):
                raise CollageError("Naming decision has no current exact receipt.")
        if event.outcome not in {"question", "invalid"} and not (
            event.stage == "interpretation" and event.outcome == "error"
        ):
            pending = None
        if event.stage != "interpretation" or event.outcome not in {"intent", "selection", "acknowledgement"}:
            if event.name_updates:
                raise CollageError("Photo-name write has no successful interpretation.")
            continue
        reply = INTENT.validate_json(event.response or "")
        if isinstance(reply, NamesIntent):
            receipt_event = events.get(event.receipt_event)
            if reply.decision == "reject":
                if event.name_updates:
                    raise CollageError("Rejected names were saved.")
                continue
            if (
                not isinstance(receipt_event, Exchange) or receipt_event.name_receipt is None
                or event.receipt_event is None or event.receipt_event >= number
                or receipt_event.task_id != event.task_id
            ):
                raise CollageError("Photo-name approval has no matching receipt.")
            updates = receipt_event.name_receipt.updates
        else:
            updates = proposed(number, event)
            if conflicting_names(updates, list(recorded.values())):
                raise CollageError("Photo-name reassignment has no approved receipt.")
        expected, effective = memory_changes(updates, list(recorded.values()), number, event.receipt_event)
        if event.name_updates != expected:
            raise CollageError("Photo-name updates differ from their user evidence or approved receipt.")
        if event.intent is not None:
            check_forgotten(event.intent.references, effective, {
                turn: entry for turn, entry in events.items()
                if turn < number and isinstance(entry, Exchange)
            })
        for update in event.name_updates:
            recorded[name_key(update.name)] = update
    if len({name_key(item.name) for item in names}) != len(names) or {
        name_key(item.name): item for item in names
    } != recorded:
        raise CollageError("Photo-name state does not match its recorded updates.")
    return pending[0] if pending is not None else None


def check_forgotten(
    references: list[PhotoReference], names: list[PhotoName], history: dict[int, Exchange],
) -> None:
    forgotten = {name_key(item.name): item.event_id for item in names if item.photo_id is None}
    bindings = {name_key(item.name): item.photo_id for item in active_names(names)}
    for reference in references:
        if reference.photo_id is None:
            continue
        if mentioned_names(reference.text, forgotten):
            raise PhotoReferenceError("That name was forgotten; ask the user which photo it means now.")
        if any(bindings[key] == reference.photo_id for key in mentioned_names(reference.text, bindings)):
            continue
        pending = [reference.event_id] if reference.event_id is not None else []
        seen = set()
        while pending:
            number = pending.pop()
            if number in seen or number not in history:
                continue
            seen.add(number)
            source = history[number]
            for item in (*source.references, *source.name_updates):
                if item.photo_id != reference.photo_id:
                    continue
                label = item.text if isinstance(item, PhotoReference) else item.name
                if any(number < forgotten[key] for key in mentioned_names(label, forgotten)):
                    raise PhotoReferenceError("That historical identity was forgotten; ask for its current photo.")
                if isinstance(item, PhotoReference) and item.event_id is not None:
                    pending.append(item.event_id)


def ground_references(
    reply: Intent, prompt: str, *, task_request: str, photos: set[int], names: list[PhotoName],
    reference_history: dict[int, Exchange], evidence_events: dict[int, Exchange] | None = None,
    event_id: int | None = None,
) -> list[NameUpdate]:
    bindings = {name_key(item.name): item.photo_id for item in active_names(names)}
    forgotten = {name_key(item.name): item for item in names if item.photo_id is None}
    previous = evidence_events or {}
    existing = {name_key(item.name): item for item in names}
    teaching_evidence = (prompt, task_request, *(event.prompt for event in previous.values()))
    updates: dict[str, NameUpdate] = {}
    seen: set[str] = set()
    for update in reply.name_updates:
        key = name_key(update.name)
        if key in seen:
            raise PhotoReferenceError("Duplicate or contradictory proposed names.")
        seen.add(key)
        if update.photo_id is not None and update.photo_id not in photos or not any(
            update.quote in text for text in teaching_evidence
        ) or not contains(update.quote, update.name):
            raise PhotoReferenceError("Proposed name needs a known photo and actual user label/quote.")
        if number_identity(update.name) is not None and number_identity(update.name) != update.photo_id:
            raise PhotoReferenceError("A photo-number label contradicts its stable photo ID.")
        if update.photo_id is not None:
            cutoff = forgotten[key].event_id if key in forgotten else 0
            fresh = [prompt, *(event.prompt for turn, event in previous.items() if turn > cutoff)]
            supplied = set().union(*(numbered_photos(text) for text in fresh))
            supplied.update(int(text.strip()) for text in fresh if re.fullmatch(r"[0-9]{1,9}", text.strip()))
            supplied.update(bindings[label] for text in fresh
                            for label in mentioned_names(text, bindings))
            question = next((
                event for turn, event in reversed(list(previous.items()))
                if turn > cutoff and event.outcome == "question"
            ), None)
            if question is not None:
                supplied.update(
                    int(match[1]) for text in fresh for match in re.finditer(
                        r"(?<![\w.,+/-])([0-9]{1,9})\s+for\s+"
                        + re.escape(key) + r"(?!\w)", name_key(text),
                    )
                )
                supplied.update(
                    item.photo_id for item in question.references
                    if name_key(item.text) == key and item.photo_id is not None
                )
            if update.photo_id not in supplied or not any(update.quote in text for text in fresh):
                raise PhotoReferenceError("Remembering needs fresh user identity evidence; ask which photo if unclear.")
        if key not in existing or existing[key].photo_id != update.photo_id:
            updates[key] = update
    if isinstance(reply, QuestionIntent) and updates:
        raise PhotoReferenceError("Resolve essential questions before proposing a naming receipt.")
    if isinstance(reply, MemoryIntent) and not reply.name_updates:
        raise PhotoReferenceError("Naming-only acknowledgement requires a proposed user name.")
    if isinstance(reply, MemoryIntent) and (
        reply.action == "forget" and any(item.photo_id is not None for item in reply.name_updates)
        or reply.action == "remember" and all(item.photo_id is None for item in reply.name_updates)
    ):
        raise PhotoReferenceError("Memory operation contradicts its proposed assignments/removals.")
    targets = {**bindings, **{key: item.photo_id for key, item in updates.items()}}
    number = event_id if event_id is not None else max(
        [*reference_history, *previous, *(item.event_id for item in names)], default=0,
    ) + 1
    _, effective = memory_changes(list(updates.values()), names, number)
    check_forgotten(reply.references, effective, reference_history)
    claims: dict[str, int | None] = {}
    explicit = numbered_photos(prompt) | numbered_photos(task_request)
    if re.fullmatch(r"[0-9]{1,9}", prompt.strip()):
        explicit.add(int(prompt.strip()))
    for index, reference in enumerate(reply.references):
        key = name_key(reference.text)
        if key in claims and claims[key] != reference.photo_id:
            raise PhotoReferenceError("Contradictory identities for the same photo reference.")
        claims[key] = reference.photo_id
        number = number_identity(reference.text)
        normalized = number is not None and number in explicit
        if not normalized and not any(
            contains(text, reference.text) for text in (prompt, task_request)
        ):
            raise PhotoReferenceError("Photo reference text is absent from the current task/answer.")
        if reference.photo_id is None:
            if reference.event_id is not None or not isinstance(reply, QuestionIntent):
                raise PhotoReferenceError("Unresolved identities require clarification, not generation.")
            continue
        if reference.photo_id not in photos:
            raise PhotoReferenceError("Photo reference uses an unknown photo number.")
        if number is not None and number != reference.photo_id:
            raise PhotoReferenceError("Explicit photo number contradicts its binding.")
        if number is not None and number not in explicit:
            raise PhotoReferenceError("Numeric binding lacks an explicit photo number or numeric answer.")
        if numbered_photos(reference.text) - {reference.photo_id}:
            raise PhotoReferenceError("Explicit photo number contradicts its binding.")
        if any(targets[label] != reference.photo_id for label in mentioned_names(reference.text, targets)):
            raise PhotoReferenceError("Exact confirmed label contradicts its binding.")
        if reference.event_id is not None:
            event = reference_history.get(reference.event_id)
            if event is None or reference.photo_id not in {
                item.photo_id for item in event.references if item.photo_id is not None
            } | {item.photo_id for item in event.name_updates}:
                raise PhotoReferenceError(
                    f"Cited reference evidence is invalid at references[{index}].event_id: "
                    f"event {reference.event_id} does not establish photo {reference.photo_id} "
                    "in the supplied reference_history. For an explicit photo number in the "
                    "current message/original task or a numeric clarification answer, omit "
                    "event_id instead of citing the question. If relying on historical evidence, "
                    "cite a supplied reference_history event establishing that photo; "
                    "do not invent evidence."
                )
    return [item.model_copy(update={"name": " ".join(item.name.split())}) for item in updates.values()]
