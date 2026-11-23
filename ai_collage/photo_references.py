"""Ground model reference claims in local user evidence, without image inference."""

import re
from collections.abc import Iterable

from .agent_models import (
    INTENT, Exchange, Intent, NameUpdate, PhotoName, QuestionIntent, RememberIntent,
)
from .models import CollageError


class PhotoReferenceError(CollageError):
    """A rejected interpretation, not a damaged name/history record."""


def affirmative(text: str) -> bool:
    return re.fullmatch(
        r"(?:yes|yes please|correct|that's correct|that is correct)[.! ]*",
        text.strip(), re.IGNORECASE,
    ) is not None


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


def short_forms(name: str) -> set[str]:
    words = name_key(name).split()
    return {
        " ".join(words[index:]) for index in range(len(words))
        if words[-1] not in {"the", "a", "an", "photo", "image", "picture"}
        and not words[-1].isdigit()
    } | {name_key(name)}


def reference_key(text: str) -> str:
    text = re.sub(r"^(?:the|a|an)\s+", "", name_key(text))
    return re.sub(r"\s+(?:photo|image|picture)$", "", text)


def name_candidates(text: str, names: list[PhotoName]) -> list[PhotoName]:
    keys = {name_key(text), reference_key(text)}
    return [item for item in names if keys & short_forms(item.name)]


def reference_names(names: list[PhotoName]) -> set[str]:
    """Include automatic short forms without turning them into taught facts."""
    return {form for item in names for form in short_forms(item.name)}


def mentioned_names(text: str, names: Iterable[str]) -> set[str]:
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
    unresolved_names = {
        name_key(item.text) for item in pending_reply.references
        if item.source in {"name", "unknown"} and item.photo_id is None
    } if isinstance(pending_reply, QuestionIntent) else set()
    asked_names = {
        key for key in unresolved_names if contains(pending_reply.question, key)
    } if isinstance(pending_reply, QuestionIntent) else set()
    bare_number = re.fullmatch(r"([1-9][0-9]{0,8})[.!]?", prompt.strip())
    answer_numbers = {int(bare_number[1])} if bare_number else numbered_photos(prompt)

    def validate_update(update: NameUpdate, *, confirmation: bool = False) -> PhotoName:
        key = name_key(update.name)
        previous = bindings.get(key)
        if update.photo_id not in photos or update.quote not in prompt:
            raise PhotoReferenceError("Name update requires a known photo and an exact user quote.")
        answered_name = (asked_names or unresolved_names) == {key}
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
            and affirmative(prompt)
        )
        candidate = (
            confirmation and isinstance(reply, QuestionIntent)
            and contains(reply.question, update.name)
            and update.photo_id in numbered_photos(reply.question)
        )
        proposed = candidate and contains(update.quote, update.name) and any(
            item.photo_id == update.photo_id and contains(reply.question, item.name)
            for item in names
        )
        if confirmation and not candidate:
            raise PhotoReferenceError("Identity confirmation must state its exact name and photo number.")
        direct = contains(update.quote, update.name) and has_number(update.quote, update.photo_id)
        answered = (
            answered_name and answer_numbers == {update.photo_id}
            and has_number(update.quote, update.photo_id)
        )
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
            raise PhotoReferenceError("Name correction requires unambiguous visible name evidence.")
        if not (direct or answered or confirmed or corrected or proposed):
            raise PhotoReferenceError("Name update is not supported by this statement or pending answer.")
        if previous is not None and previous.photo_id != update.photo_id:
            if update.replaces_photo_id != previous.photo_id or not (
                confirmation or confirmed or correction_wording
            ):
                raise PhotoReferenceError("Conflicting name assignment needs user clarification or explicit correction.")
        elif update.replaces_photo_id is not None:
            raise PhotoReferenceError("Name correction does not match an existing binding.")
        aliases = [name_key(alias) for alias in update.aliases]
        if (
            len(set(aliases)) != len(aliases)
            or any(alias not in short_forms(update.name) or alias == key for alias in aliases)
        ):
            raise PhotoReferenceError("Automatic aliases must be distinct shortened taught wording; confirm broader names.")
        return PhotoName(
            name=" ".join(update.name.split()), photo_id=update.photo_id,
            event_id=event_id, quote=update.quote,
            question_event=pending[0] if pending and (answered or confirmed) else None,
            aliases=aliases,
        )

    updates = []
    seen = set()
    for update in reply.name_updates:
        key = name_key(update.name)
        if key in seen:
            raise PhotoReferenceError("Duplicate or contradictory photo-name updates.")
        seen.add(key)
        binding = validate_update(update)
        updates.append(binding)
        bindings[key] = binding
    if isinstance(reply, QuestionIntent) and reply.confirmation is not None:
        confirmation = reply.confirmation
        if name_key(confirmation.name) in seen:
            raise PhotoReferenceError("A pending name confirmation cannot also update that name.")
        validate_update(confirmation, confirmation=True)
    if isinstance(reply, RememberIntent) and not updates:
        raise PhotoReferenceError("Naming-only acknowledgement requires a validated name update.")
    if isinstance(pending_reply, QuestionIntent) and pending_reply.confirmation is not None:
        candidate = pending_reply.confirmation
        if affirmative(prompt) and not isinstance(reply, QuestionIntent) and not any(
            name_key(item.name) == name_key(candidate.name) and item.photo_id == candidate.photo_id
            and item.question_event == pending[0] for item in updates
        ):
            raise PhotoReferenceError("An affirmative identity answer must use its exact pending confirmation.")
        if re.fullmatch(
            r"(?:no|no thanks|not that one)[.! ]*", prompt.strip(), re.I,
        ) and not isinstance(reply, QuestionIntent):
            raise PhotoReferenceError("A rejected identity confirmation must clarify, not change the layout.")

    unresolved = False
    claims: dict[str, int | None] = {}
    explicit_numbers = numbered_photos(prompt) | numbered_photos(task_request)
    explicit_numbers.update(
        item.photo_id for item in updates if pending and item.question_event == pending[0]
    )
    for reference in reply.references:
        key = name_key(reference.text)
        if key in claims and claims[key] != reference.photo_id:
            raise PhotoReferenceError("Contradictory identities for the same photo reference.")
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
            raise PhotoReferenceError(
                "Photo reference text is absent from the current task/answer. "
                "Bind only individually identified photos; keep collective instructions "
                "in the task rather than enumerating group members."
            )
        if reference.photo_id is None:
            if reference.source not in {"name", "unknown"} or reference.event_id is not None:
                raise PhotoReferenceError("Unresolved photo reference has contradictory evidence.")
            candidates = name_candidates(reference.text, list(bindings.values()))
            if len({item.photo_id for item in candidates}) == 1:
                raise PhotoReferenceError("Known photo name must not be presented as unknown.")
            unresolved = True
            continue
        if reference.photo_id not in photos:
            raise PhotoReferenceError("Photo reference uses an unknown photo number.")
        if reference.source != "history" and reference.event_id is not None:
            raise PhotoReferenceError("Only conversational references may cite a prior event.")
        if reference.source == "number":
            if not has_number(reference.text, reference.photo_id):
                raise PhotoReferenceError("Photo number is not present in the reference text.")
        elif reference.source == "name":
            candidates = name_candidates(reference.text, list(bindings.values()))
            answered_targets = {
                item.photo_id for item in updates if pending and item.question_event == pending[0]
                and name_key(item.name) in {key, reference_key(reference.text)}
            }
            if (
                {item.photo_id for item in candidates} != {reference.photo_id}
                and answered_targets != {reference.photo_id}
            ):
                raise PhotoReferenceError("Photo name has no unique matching user-established binding.")
        elif reference.source == "history":
            if re.fullmatch(
                r"(?:it|this|that|(?:this|that|the|the same|that same) (?:one|photo|picture|image))",
                name_key(reference.text),
            ) is None:
                raise PhotoReferenceError("History evidence resolves conversational wording, not unknown photo names.")
            event = reference_history.get(reference.event_id)
            targets = (
                {item.photo_id for item in event.references if item.photo_id is not None}
                | {item.photo_id for item in event.name_updates}
            ) if event else set()
            if targets != {reference.photo_id}:
                raise PhotoReferenceError("Conversational reference needs an unambiguous visible prior target.")
        else:
            raise PhotoReferenceError(
                "A resolved photo reference needs number, name or history evidence. "
                "Unknown requires a null photo_id. Keep collective instructions in the "
                "task rather than encoding group members as individual references."
            )
    if unresolved and not isinstance(reply, QuestionIntent):
        raise PhotoReferenceError("Unresolved photo references require clarification before generation.")
    if not isinstance(reply, QuestionIntent):
        for key in mentioned_names(prompt, reference_names(list(bindings.values()))):
            if key in seen:
                continue
            targets = {item.photo_id for item in name_candidates(key, list(bindings.values()))}
            if len(targets) != 1:
                raise PhotoReferenceError("A mentioned name is ambiguous; ask which photo.")
            target = next(iter(targets))
            adjacent_numbers = re.findall(
                r"(?<!\w)" + re.escape(key)
                + r"\s*\(\s*(?:photo|image|picture)\s+([1-9][0-9]*)\s*\)",
                name_key(prompt),
            )
            if any(int(number) != target for number in adjacent_numbers):
                raise PhotoReferenceError("The adjacent photo number conflicts with the learned name.")
            matching = [
                item for item in reply.references if item.photo_id == target and (
                    item.source == "name" and (
                        contains(item.text, key) or contains(key, reference_key(item.text))
                    )
                    or item.source == "number" and target in numbered_photos(prompt)
                )
            ]
            if not matching:
                raise PhotoReferenceError("A mentioned learned name is missing its resolved reference.")
    return updates
