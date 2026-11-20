"""Ground model reference claims in local user evidence, without image inference."""

import re

from .agent_models import (
    INTENT, Exchange, Intent, NameUpdate, PhotoName, QuestionIntent, RememberIntent,
)
from .models import CollageError


def name_key(text: str) -> str:
    return " ".join(text.split()).casefold()


def contains(text: str, phrase: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(name_key(phrase)) + r"(?!\w)", name_key(text)) is not None


def has_number(text: str, photo_id: int) -> bool:
    return re.search(rf"(?<!\d){photo_id}(?!\d)", text) is not None


def numbered_photos(text: str) -> set[int]:
    number = r"[1-9][0-9]{0,8}(?!\w|\.[0-9]|%)"
    lists = re.finditer(
        r"\b(?:photos?|images?|pictures?)\s+(" + number
        + r"(?:\s*(?:,\s*(?:and\b\s*)?|\band\b|&)\s*" + number + r")*)",
        text, re.IGNORECASE,
    )
    return {int(value) for match in lists for value in re.findall(r"[0-9]+", match[1])}


def mentioned_names(text: str, names: dict[str, PhotoName]) -> set[str]:
    spans: list[tuple[int, int]] = []
    found = set()
    for key in sorted(names, key=len, reverse=True):
        for match in re.finditer(r"(?<!\w)" + re.escape(key) + r"(?!\w)", name_key(text)):
            if not any(match.start() < end and start < match.end() for start, end in spans):
                found.add(key)
                spans.append(match.span())
    return found


def name_history(names: list[PhotoName], events: dict[int, object], photos: set[int]) -> None:
    recorded: dict[str, PhotoName] = {}
    for number, event in events.items():
        if not isinstance(event, Exchange):
            continue
        for update in event.name_updates:
            question = events.get(update.question_event)
            if (
                update.event_id != number or update.photo_id not in photos
                or update.quote not in event.prompt or event.outcome not in {
                    "intent", "question", "acknowledgement", "selection",
                }
                or (update.question_event is not None and (
                    update.question_event >= number or not isinstance(question, Exchange)
                    or question.outcome != "question"
                ))
            ):
                raise CollageError("Photo-name evidence does not match conversation history.")
            recorded[name_key(update.name)] = update
    if len({name_key(item.name) for item in names}) != len(names) or {
        name_key(item.name): item for item in names
    } != recorded:
        raise CollageError("Photo-name state does not match its recorded updates.")


def ground_references(
    reply: Intent, prompt: str, *, task_request: str, photos: set[int], names: list[PhotoName],
    event_id: int, pending: tuple[int, Exchange] | None,
    reference_history: dict[int, Exchange],
) -> list[PhotoName]:
    bindings = {name_key(item.name): item for item in names}
    pending_reply = INTENT.validate_json(pending[1].response or "") if pending else None
    if pending_reply is not None and not isinstance(pending_reply, QuestionIntent):
        raise CollageError("Pending clarification has no question response.")

    def validate_update(update: NameUpdate, *, confirmation: bool = False) -> PhotoName:
        key = name_key(update.name)
        previous = bindings.get(key)
        if update.photo_id not in photos or update.quote not in prompt:
            raise CollageError("Name update requires a known photo and an exact user quote.")
        answered_name = (
            isinstance(pending_reply, QuestionIntent) and any(
                item.source == "name" and item.photo_id is None
                and name_key(item.text) == key for item in pending_reply.references
            )
        )
        confirmed = (
            isinstance(pending_reply, QuestionIntent)
            and pending_reply.confirmation is not None
            and (
                key, update.photo_id, update.replaces_photo_id
            ) == (
                name_key(pending_reply.confirmation.name),
                pending_reply.confirmation.photo_id,
                pending_reply.confirmation.replaces_photo_id,
            )
            and re.fullmatch(r"(?:yes|yes please|correct|that's correct|that is correct)[.! ]*",
                             prompt.strip(), re.IGNORECASE) is not None
        )
        direct = contains(update.quote, update.name) and has_number(update.quote, update.photo_id)
        answered = answered_name and has_number(update.quote, update.photo_id)
        evidence = reference_history.get(update.evidence_event)
        history_names = (
            {name_key(item.name) for item in evidence.name_updates}
            | {name_key(item.text) for item in evidence.references if item.source == "name"}
        ) if evidence else set()
        correction_wording = re.search(
            r"\b(?:meant|correction|instead|actually|not|rather)\b", update.quote, re.IGNORECASE
        ) is not None
        corrected = (
            history_names == {key} and previous is not None
            and has_number(update.quote, update.photo_id) and correction_wording
        )
        if update.evidence_event is not None and not corrected:
            raise CollageError("Name correction requires unambiguous visible name evidence.")
        if not (direct or answered or confirmed or corrected):
            raise CollageError("Name update is not supported by this statement or pending answer.")
        if previous is not None and previous.photo_id != update.photo_id:
            if update.replaces_photo_id != previous.photo_id or not (
                confirmation or confirmed or correction_wording
            ):
                raise CollageError("Conflicting name assignment needs user clarification or explicit correction.")
        elif update.replaces_photo_id is not None:
            raise CollageError("Name correction does not match an existing binding.")
        return PhotoName(
            name=" ".join(update.name.split()), photo_id=update.photo_id,
            event_id=event_id, quote=update.quote,
            question_event=pending[0] if pending and (answered or confirmed) else None,
        )

    updates = []
    seen = set()
    for update in reply.name_updates:
        key = name_key(update.name)
        if key in seen:
            raise CollageError("Duplicate or contradictory photo-name updates.")
        seen.add(key)
        binding = validate_update(update)
        updates.append(binding)
        bindings[key] = binding
    if isinstance(reply, QuestionIntent) and reply.confirmation is not None:
        confirmation = reply.confirmation
        if name_key(confirmation.name) in seen:
            raise CollageError("A pending name confirmation cannot also update that name.")
        validate_update(confirmation, confirmation=True)
    if isinstance(reply, RememberIntent) and not updates:
        raise CollageError("Naming-only acknowledgement requires a validated name update.")

    unresolved = False
    claims: dict[str, int | None] = {}
    explicit_numbers = numbered_photos(prompt) | numbered_photos(task_request)
    for reference in reply.references:
        key = name_key(reference.text)
        if key in claims and claims[key] != reference.photo_id:
            raise CollageError("Contradictory identities for the same photo reference.")
        claims[key] = reference.photo_id
        normalized_number = re.fullmatch(r"(?:photo|image|picture)\s+([1-9][0-9]*)", key)
        numbered_evidence = (
            reference.source == "number" and normalized_number is not None
            and int(normalized_number[1]) == reference.photo_id
            and reference.photo_id in explicit_numbers
        )
        if not numbered_evidence and not any(
            contains(text, reference.text) for text in (prompt, task_request)
        ):
            raise CollageError(
                "Photo reference text is absent from the current task/answer. "
                "Bind only individually identified photos; keep collective instructions "
                "in the task rather than enumerating group members."
            )
        if reference.photo_id is None:
            if reference.source not in {"name", "unknown"} or reference.event_id is not None:
                raise CollageError("Unresolved photo reference has contradictory evidence.")
            if name_key(reference.text) in bindings:
                raise CollageError("Known photo name must not be presented as unknown.")
            unresolved = True
            continue
        if reference.photo_id not in photos:
            raise CollageError("Photo reference uses an unknown photo number.")
        if reference.source != "history" and reference.event_id is not None:
            raise CollageError("Only conversational references may cite a prior event.")
        if reference.source == "number":
            if not has_number(reference.text, reference.photo_id):
                raise CollageError("Photo number is not present in the reference text.")
        elif reference.source == "name":
            binding = bindings.get(name_key(reference.text))
            if binding is None or binding.photo_id != reference.photo_id:
                raise CollageError("Photo name has no matching user-established binding.")
        elif reference.source == "history":
            if re.fullmatch(
                r"(?:it|this|that|(?:this|that|the|the same|that same) (?:one|photo|picture|image))",
                name_key(reference.text),
            ) is None:
                raise CollageError("History evidence resolves conversational wording, not unknown photo names.")
            event = reference_history.get(reference.event_id)
            targets = (
                {item.photo_id for item in event.references if item.photo_id is not None}
                | {item.photo_id for item in event.name_updates}
            ) if event else set()
            if targets != {reference.photo_id}:
                raise CollageError("Conversational reference needs an unambiguous visible prior target.")
        else:
            raise CollageError(
                "A resolved photo reference needs number, name or history evidence. "
                "Unknown requires a null photo_id. Keep collective instructions in the "
                "task rather than encoding group members as individual references."
            )
    if unresolved and not isinstance(reply, QuestionIntent):
        raise CollageError("Unresolved photo references require clarification before generation.")
    if not isinstance(reply, QuestionIntent):
        for key in mentioned_names(prompt, bindings):
            if key not in seen and not any(
                item.source == "name" and name_key(item.text) == key for item in reply.references
            ):
                raise CollageError("A mentioned learned name is missing its resolved reference.")
    return updates
