"""Validate binding/data facts; language interpretation belongs to the model."""

import hashlib
import json
import re
from collections.abc import Iterable

from .agent_models import INTENT, Exchange, Intent, NameReceipt, NameUpdate, NamesIntent, PhotoName, QuestionIntent, RememberIntent
from .models import CollageError


class PhotoReferenceError(CollageError):
    """A rejected interpretation, not a damaged name/history record."""


def name_key(text: str) -> str:
    return " ".join(text.split()).casefold()


def names_digest(names: list[PhotoName]) -> str:
    return hashlib.sha256(json.dumps(
        [item.model_dump(mode="json") for item in names], sort_keys=True,
    ).encode("utf-8")).hexdigest()


def receipt_question(receipt: NameReceipt, names: list[PhotoName]) -> str:
    previous = {name_key(item.name): item.photo_id for item in names}
    lines = [
        f"{item.name} = photo {item.photo_id}"
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
    return [item for item in names if name_key(text) == name_key(item.name)]


def reference_names(names: list[PhotoName]) -> set[str]:
    return {name_key(item.name) for item in names}


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
    for number, event in events.items():
        if not isinstance(event, Exchange):
            continue
        if pending is not None and event.task_id != pending[1].task_id:
            pending = None
        if event.name_receipt is not None:
            receipt = event.name_receipt
            origin = events.get(receipt.intent.task_turn) if receipt.intent is not None else None
            if (
                receipt.baseline != event.baseline_before
                or receipt.intent is not None and (
                    receipt.intent.task_turn > number or not isinstance(origin, Exchange)
                    or origin.prompt != receipt.intent.task_request
                )
                or receipt.names_digest != names_digest(list(recorded.values()))
                or any(
                    update.photo_id not in photos
                    or number_identity(update.name) not in {None, update.photo_id}
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
        if not event.name_updates:
            continue
        receipt_event = events.get(event.receipt_event)
        approval = INTENT.validate_json(event.response or "")
        if (
            not isinstance(receipt_event, Exchange) or receipt_event.name_receipt is None
            or event.receipt_event is None or event.receipt_event >= number
            or receipt_event.task_id != event.task_id
            or event.outcome not in {"intent", "selection", "acknowledgement"}
            or not isinstance(approval, NamesIntent) or approval.decision != "approve"
            or approval.receipt_event != event.receipt_event
        ):
            raise CollageError("Photo-name approval has no matching receipt.")
        expected = [
            PhotoName(
                name=" ".join(update.name.split()), photo_id=update.photo_id,
                event_id=number, quote=update.quote, receipt_event=event.receipt_event,
            )
            for update in receipt_event.name_receipt.updates
        ]
        if event.name_updates != expected:
            raise CollageError("Photo-name updates differ from the approved receipt.")
        for update in event.name_updates:
            recorded[name_key(update.name)] = update
    if len({name_key(item.name) for item in names}) != len(names) or {
        name_key(item.name): item for item in names
    } != recorded:
        raise CollageError("Photo-name state does not match its approved updates.")
    return pending[0] if pending is not None else None


def ground_references(
    reply: Intent, prompt: str, *, task_request: str, photos: set[int], names: list[PhotoName],
    reference_history: dict[int, Exchange], evidence_prompts: Iterable[str] = (),
) -> list[NameUpdate]:
    bindings = {name_key(item.name): item.photo_id for item in names}
    teaching_evidence = (prompt, task_request, *evidence_prompts)
    updates: dict[str, NameUpdate] = {}
    seen: set[str] = set()
    for update in reply.name_updates:
        key = name_key(update.name)
        if key in seen:
            raise PhotoReferenceError("Duplicate or contradictory proposed names.")
        seen.add(key)
        if update.photo_id not in photos or not any(
            update.quote in text for text in teaching_evidence
        ) or not contains(update.quote, update.name):
            raise PhotoReferenceError("Proposed name needs a known photo and actual user label/quote.")
        if number_identity(update.name) not in {None, update.photo_id}:
            raise PhotoReferenceError("A photo-number label contradicts its stable photo ID.")
        if bindings.get(key) != update.photo_id:
            updates[key] = update
    if isinstance(reply, QuestionIntent) and updates:
        raise PhotoReferenceError("Resolve essential questions before proposing a naming receipt.")
    if isinstance(reply, RememberIntent) and not reply.name_updates:
        raise PhotoReferenceError("Naming-only acknowledgement requires a proposed user name.")
    targets = {**bindings, **{key: item.photo_id for key, item in updates.items()}}
    claims: dict[str, int | None] = {}
    explicit = numbered_photos(prompt) | numbered_photos(task_request)
    if re.fullmatch(r"[0-9]{1,9}", prompt.strip()):
        explicit.add(int(prompt.strip()))
    for reference in reply.references:
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
                raise PhotoReferenceError("Cited reference evidence does not contain this photo.")
    return list(updates.values())
