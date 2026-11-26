"""Local proposals, real conversation history, and explicit acceptance."""

import asyncio
import json
import re
import tempfile
from pathlib import Path
from typing import Callable, Protocol

from pydantic import ValidationError

from .requests import RequestLog, StageTimeout
from .files import canonical, child, digest, save
from .models import (
    HISTORY, INTENT, AcceptanceIntent, Controls, ConversationState, EditIntent, Exchange,
    FreshIntent, InspectNamesIntent, Intent, LayoutSource, LocalEvent, LocalSelection, MemoryIntent,
    NameReceipt, NameUpdate, NamesIntent, PhotoName, Preferences, PreparedGeneration,
    Proposal, QuestionIntent, RequestResult,
    ReceiptPointer, ResolvedIntent, ResumeIntent, RetryIntent, SelectIntent,
)
from ..engine.geometry import LayoutBoundsError, resolve_layout
from ..engine.imaging import render_layout
from ..engine.models import MAX_JSON_BYTES, CollageError, InputLayout, ResolvedLayout
from ..engine.projects import ProjectStore, parse_json, read_json
from .photo_references import (
    PhotoReferenceError, active_names, check_forgotten, conflicting_names, ground_references, memory_changes,
    memory_message, name_history, names_digest, names_message, receipt_question,
)
from .task_history import (
    TaskRecord, ordinals, retrieve, task_records, undo_steps, undo_target, validate_navigation,
)


class ModelClient(Protocol):
    async def complete(self, context: dict[str, object], requests: RequestLog, purpose: str) -> str: ...


Progress = Callable[[str, ResolvedIntent | str | None], None]


class RequestRejected(CollageError):
    """Validation exhausted before publication, with the working source verified."""

    def __init__(self, diagnostic: str, source: LayoutSource | None, *, identity: bool):
        super().__init__(f"Model correction failed: {diagnostic}")
        self.source = source
        self.identity = identity


class Conversation:
    def __init__(
        self, store: ProjectStore, project_id: str, *,
        canvas: tuple[int, int] | None = None, preferences: Path | None = None,
        read_only: bool = False,
    ):
        self.store = store
        self.project_id = project_id
        project = store.load(project_id)
        self.root = child(store.project_dir(project_id), "conversation")
        self.state_path = child(self.root, "state.json")
        self.intent_path = child(self.root, "acceptance.json")
        self.photo_digest = digest(
            json.dumps([p.model_dump() for p in project.photos], sort_keys=True).encode()
        )
        if self.state_path.exists():
            stored = read_json(self.state_path)
            if not isinstance(stored, dict) or stored.get("record_version") != ConversationState.model_fields["record_version"].default:
                raise CollageError("Unsupported conversation version; use a fresh project. Existing data is unchanged.")
            self.state = ConversationState.model_validate(stored)
            if self.state.project_id != project_id or self.state.photo_digest != self.photo_digest:
                raise CollageError("Conversation project/photo identity mismatch.")
            if preferences is not None:
                raise CollageError("Resume uses captured preferences; omit --preferences.")
            if canvas is not None and canvas != (self.state.controls.width, self.state.controls.height):
                raise CollageError("Resume canvas differs; use /canvas explicitly.")
            if read_only:
                self._fresh()
            else:
                self._recover()
        else:
            if read_only:
                raise CollageError("Saved conversation is missing; read-only access cannot initialize it.")
            if canvas is None:
                raise CollageError("A new conversation requires --canvas WIDTH HEIGHT.")
            controls = Controls(width=canvas[0], height=canvas[1])
            preferences_path = preferences or child(store.owner_dir, "preferences.json")
            if not preferences_path.exists():
                if preferences is not None:
                    raise CollageError("The selected preferences file does not exist.")
                save(preferences_path, Preferences(
                    preferences_version=1, borders="prefer", rounding="prefer", tilt="prefer"
                ))
            prefs = Preferences.model_validate(read_json(preferences_path))
            if project.current_version is not None:
                store.load_layout(project, project.current_version)
            self.state = ConversationState(
                project_id=project_id, photo_digest=self.photo_digest,
                expected_version=project.current_version, initial_version=project.current_version,
                preferences=prefs, controls=controls,
            )
            if self.root.exists() and any(self.root.iterdir()):
                raise CollageError("Incomplete conversation initialization; inspect local state.")
            save(self.state_path, self.state)
        pending = name_history(
            self.state.photo_names, dict(zip(self.state.history, self.history(), strict=True)),
            {photo.photo_id for photo in project.photos},
        )
        if pending != (self.state.pending_names.event_id if self.state.pending_names else None):
            raise CollageError("Pending naming pointer does not match its history.")
        self._check_name_writes()
        self._pending_names()
        self.baseline()
        self.tasks()

    def _commit(self, state: ConversationState) -> None:
        save(self.state_path, state)
        self.state = state

    def _fresh(self) -> None:
        current = ConversationState.model_validate(read_json(self.state_path))
        if current != self.state:
            raise CollageError("Conversation changed; restart before making further changes.")
        if self.store.load(self.project_id).current_version != self.state.expected_version:
            raise CollageError("Accepted project changed outside this conversation; inspect local state.")
        if self.intent_path.exists():
            raise CollageError("Acceptance needs reconciliation; restart the conversation.")
        self._check_name_writes()

    def _check_name_writes(self) -> None:
        referenced = set(self.state.history)
        for path in child(self.root, "events").glob("*.json"):
            if re.fullmatch(r"[0-9]{6,}", path.stem) and int(path.stem) not in referenced:
                event = HISTORY.validate_python(read_json(path))
                if isinstance(event, Exchange) and (
                    event.name_receipt is not None or event.receipt_event is not None
                    or event.name_updates
                ) or isinstance(event, LocalSelection):
                    raise CollageError(
                        "Interrupted local-selection write; inspect its preserved event/state before continuing."
                        if isinstance(event, LocalSelection) else
                        "Interrupted naming write; inspect its preserved event/state before continuing."
                    )

    def history(self) -> list[Exchange | LocalEvent | LocalSelection]:
        return [
            HISTORY.validate_python(read_json(child(self.root, "events", f"{number:06d}.json")))
            for number in self.state.history
        ]

    def _next_event(self) -> int:
        directory = child(self.root, "events")
        numbers = [
            int(path.stem) for path in directory.glob("*.json")
            if re.fullmatch(r"[0-9]{6,}", path.stem)
        ]
        return max(numbers, default=0) + 1

    def _append(self, event: Exchange | LocalEvent | LocalSelection, **updates: object) -> int:
        if ConversationState.model_validate(read_json(self.state_path)) != self.state:
            raise CollageError("Conversation changed; restart before making further changes.")
        number = self._next_event()
        if isinstance(event, Exchange):
            event = event.model_copy(update={
                "task_id": self._active_task,
                "baseline_before": self._current_source(),
            })
            if event.name_receipt is not None:
                updates["pending_names"] = ReceiptPointer(event_id=number, sha256=digest(canonical(event)))
            elif event.outcome != "inspection" and (event.receipt_event is not None or (
                event.task_id == number and event.outcome not in {"invalid", "error"}
            )):
                updates["pending_names"] = None
        save(child(self.root, "events", f"{number:06d}.json"), event)
        state = self.state.model_copy(update={
            **updates, "history": [*self.state.history, number],
        })
        self._commit(ConversationState.model_validate(state.model_dump()))
        return number

    def preview_path(self, proposal_id: str) -> Path:
        if not re.fullmatch(r"P[0-9]{3,}", proposal_id):
            raise CollageError("Invalid proposal ID.")
        return child(self.root, "proposals", proposal_id, "preview.png")

    def proposal(
        self, proposal_id: str, *, _events: dict[int, Exchange | LocalEvent | LocalSelection] | None = None,
    ) -> Proposal:
        preview = self.preview_path(proposal_id)
        history = _events if _events is not None else dict(zip(
            self.state.history, self.history(), strict=True,
        ))
        committed = {
            entry.proposal_id: (number, entry)
            for number, entry in history.items()
            if isinstance(entry, Exchange) and entry.outcome == "proposal"
        }
        if proposal_id not in committed:
            raise CollageError("Unknown or unpublished proposal ID.")
        proposal = Proposal.model_validate(read_json(child(preview.parent, "proposal.json")))
        number, event = committed[proposal_id]
        self._validate_proposal(proposal, proposal_id, number, event, history, preview)
        return proposal

    def _validate_proposal(
        self, proposal: Proposal, proposal_id: str, number: int, event: Exchange,
        history: dict[int, Exchange | LocalEvent | LocalSelection], preview: Path,
    ) -> None:
        committed = {
            entry.proposal_id: turn for turn, entry in history.items()
            if isinstance(entry, Exchange) and entry.outcome == "proposal"
        }
        project = self.store.load(self.project_id)
        expected = resolve_layout(proposal.recipe, project.photos, 1)
        task = history.get(proposal.intent.task_turn)
        # A logical task can start with an invalid attempt, then a validated correction.
        corrected_origin = isinstance(task, Exchange) and task.task_id == proposal.intent.task_turn and any(
            proposal.intent.task_turn < turn < number
            and isinstance(entry, Exchange) and entry.task_id == task.task_id
            and entry.stage == "interpretation" and entry.outcome in {"intent", "question", "name_confirmation"}
            and entry.prompt == proposal.intent.task_request
            for turn, entry in history.items()
        )
        confirmed_intent = any(
            turn < number and isinstance(entry, Exchange) and entry.task_id == event.task_id
            and entry.stage == "interpretation" and entry.outcome == "intent"
            and entry.intent == proposal.intent
            for turn, entry in history.items()
        )
        source = proposal.intent.source
        identities = [
            identity for identity in (
                source.proposal_id if source else None,
                proposal.intent.reference.proposal_id if proposal.intent.reference else None,
            ) if identity is not None
        ]
        if (
            proposal.proposal_id != proposal_id
            or proposal.turn_id != number or proposal.intent != event.intent
            or proposal.parent != event.parent
            or proposal.geometry != expected.geometry
            or proposal.recipe_digest != digest(canonical(proposal.recipe))
            or proposal.preview_digest != digest(preview.read_bytes())
            or proposal.parent != (
                proposal.intent.source.proposal_id if proposal.intent.source else None
            )
            or any(identity not in committed or committed[identity] >= number for identity in identities)
            or (
                source is not None and source.accepted_version is not None
                and source.accepted_version != self.state.initial_version
            )
            or (
                proposal.intent.reference is not None
                and proposal.intent.reference.accepted_version is not None
                and proposal.intent.reference.accepted_version != self.state.initial_version
            )
            or not isinstance(task, Exchange) or task.prompt != proposal.intent.task_request
            or task.stage != "interpretation" or not (
                task.outcome in {"intent", "question", "name_confirmation"}
                or task.outcome == "invalid" and corrected_origin
            )
            or not confirmed_intent
        ):
            raise CollageError("Proposal recipe, geometry, or preview identity mismatch.")

    def baseline(self) -> InputLayout | None:
        if self.state.baseline is not None:
            return self.proposal(self.state.baseline).recipe
        if self.state.initial_version is not None:
            return self.store.load_layout(
                self.store.load(self.project_id), self.state.initial_version
            ).recipe
        return None

    def _validate_recipe(self, recipe: InputLayout) -> ResolvedLayout:
        controls = self.state.controls
        if (recipe.canvas.width, recipe.canvas.height) != (controls.width, controls.height):
            raise CollageError("Recipe must use the current canvas dimensions.")
        if not controls.cropping and any(layer.mode != "whole" for layer in recipe.layers):
            raise CollageError("Cropping is forbidden; every layer must use whole mode.")
        return resolve_layout(recipe, self.store.load(self.project_id).photos, 1)

    def source_recipe(self, source: LayoutSource | None) -> InputLayout | None:
        if source is None:
            return None
        if source.proposal_id is not None:
            return self.proposal(source.proposal_id).recipe
        assert source.accepted_version is not None
        return self.store.load_layout(
            self.store.load(self.project_id), source.accepted_version,
        ).recipe

    def _current_source(self) -> LayoutSource | None:
        if self.state.baseline is not None:
            return LayoutSource(proposal_id=self.state.baseline)
        if self.state.initial_version is not None:
            return LayoutSource(accepted_version=self.state.initial_version)
        return None

    def context(
        self, prompt: str, feedback: str | None = None, *,
        stage: str = "interpretation", intent: ResolvedIntent | None = None,
        request_start: int | None = None,
    ) -> dict[str, object]:
        self._fresh()
        project = self.store.load(self.project_id)
        exchanges = [
            (number, event)
            for number, event in zip(self.state.history, self.history(), strict=True)
            if isinstance(event, Exchange)
        ]
        records = self.tasks()
        failure = self._pending_failure()
        pending_names = self._pending_names()
        if pending_names is not None:
            self._check_receipt(pending_names[1].name_receipt)
        prior_records = [
            record for record in records
            if request_start is None or record.task_id < request_start
        ]
        grouped: dict[int, list[tuple[int, Exchange]]] = {}
        active: list[Exchange] = []
        for number, event in exchanges:
            if request_start is not None and number >= request_start:
                active.append(event)
                continue
            grouped.setdefault(event.task_id, []).append((number, event))
        groups = list(grouped.values())
        recent = groups[-3:]
        history = [
            {
                "kind": "turn", "turn": group[0][0], "prompt": group[0][1].prompt,
                "task_id": group[0][1].task_id,
                "answers": list(dict.fromkeys(event.prompt for _, event in group[1:]
                                             if event.prompt != group[0][1].prompt)),
                "outcome": group[-1][1].outcome, "proposal_id": group[-1][1].proposal_id,
                "response": group[-1][1].response if group[-1][1].outcome == "question" else None,
            }
            for group in recent
        ]
        abandoned = {record.task_id for record in records if record.outcome == "abandoned"}
        for item in history:
            if item["task_id"] in abandoned:
                item.update(outcome="abandoned", response=None)
        published = [event.proposal_id for _, event in exchanges if event.outcome == "proposal"]
        compact = retrieve(prior_records, prompt, self._current_source(), self.state.photo_names)
        lookup = None
        count = undo_steps(prompt)
        if count is not None:
            try:
                target = undo_target(records, self._current_source(), count)
                lookup = {"kind": "undo", "steps": count, "proposal_id": target}
            except CollageError as exc:
                lookup = {"kind": "undo", "steps": count, "error": str(exc)}
        selected = {self.state.baseline}
        if published:
            selected.update((published[0], published[-1]))
        selected.update(event.proposal_id for group in recent for _, event in group)
        selected.update(record.proposal_id for record in compact)
        if lookup is not None and "proposal_id" in lookup:
            selected.add(lookup["proposal_id"])
        selected.update(re.findall(r"\bP[0-9]{3,}\b", prompt))
        positions = ordinals(prompt)
        selected.update(published[position - 1] for position in positions if 1 <= position <= len(published))
        if intent is not None:
            selected.update(
                source.proposal_id for source in (intent.source, intent.reference) if source is not None
            )
        if failure is not None:
            selected.update(
                source.proposal_id for source in (failure.intent.source, failure.intent.reference)
                if source is not None
            )
        held = pending_names[1].name_receipt.intent if pending_names else None
        if held is not None:
            selected.update(
                source.proposal_id for source in (held.source, held.reference) if source is not None
            )
        catalogue = []
        for ordinal, proposal_id in enumerate(published, 1):
            if proposal_id not in selected:
                continue
            assert proposal_id is not None
            proposal = self.proposal(proposal_id, _events=dict(exchanges))
            catalogue.append({
                "proposal_id": proposal_id, "ordinal": ordinal,
                "action": proposal.intent.action,
                "source": proposal.intent.source.model_dump(mode="json") if proposal.intent.source else None,
                "controls": proposal.controls.model_dump(mode="json"),
            })
        pending_question = self._pending_question()
        previous = pending_question[1] if pending_question else None
        context: dict[str, object] = {
            "stage": stage,
            "photos": [
                {"photo_id": p.photo_id, "width": p.width, "height": p.height,
                 "aspect_ratio": p.width / p.height} for p in project.photos
            ],
            "preferences": self.state.preferences.model_dump(),
            "photo_names": [item.model_dump(mode="json") for item in active_names(self.state.photo_names)],
            "forgotten_names": [
                {"name": item.name, "event_id": item.event_id}
                for item in self.state.photo_names if item.photo_id is None
            ],
            "compact_tasks": [record.model_dump(mode="json") for record in compact],
            "compact_tasks_omitted": max(0, len(prior_records) - len(recent) - len(compact)),
            "recent_tasks": [
                record.model_dump(mode="json", exclude={"request"}) for record in prior_records[-3:]
            ],
            "task_count": len(prior_records),
            "navigation_lookup": lookup,
            "failed_task": {
                "task_id": failure.task_id,
                "resolved_intent": failure.intent.model_dump(mode="json"),
            } if failure is not None else None,
            "reference_history": [
                {"event_id": number,
                 "references": [item.model_dump(mode="json") for item in event.references],
                 "name_updates": [item.model_dump(mode="json") for item in event.name_updates]}
                for group in recent for number, event in group
                if event.references or event.name_updates
            ],
            "trusted_controls": self.state.controls.model_dump(),
            "current_baseline": self._current_source().model_dump(mode="json")
            if self._current_source() else None,
            "original_request": exchanges[0][1].prompt if exchanges else prompt,
            "history_omitted": len(groups) - len(recent),
            "proposal_count": len(published), "proposals": catalogue,
            "pending_question": (
                {"event_id": pending_question[0], "prompt": previous.prompt,
                 "original_task": intent.task_request if intent else self._task_origin(prompt)[1],
                 "response": previous.response}
                if previous is not None and previous.outcome == "question" else None
            ),
            "pending_names": (
                {"receipt_event": pending_names[0],
                 **pending_names[1].name_receipt.model_dump(mode="json")}
                if pending_names is not None else None
            ),
            "failed_candidate": active[-1].response if active and active[-1].outcome == "invalid" else None,
            "prior_validation_feedback": [
                event.error for event in active[:-1]
                if event.outcome == "invalid" and event.stage == stage
            ],
            "history": history, "user_request": prompt, "validation_feedback": feedback,
        }
        pending = INTENT.validate_json(previous.response or "") if (
            previous is not None and previous.outcome == "question"
        ) else None
        pinned_ids = {
            evidence.task_id for evidence in (
                pending.return_confirmation.evidence
                if isinstance(pending, QuestionIntent) and pending.return_confirmation else None,
                intent.navigation if intent else None,
                held.navigation if held else None,
            ) if evidence is not None and evidence.task_id is not None
        }
        context["required_tasks"] = [
            record.model_dump(mode="json", exclude={"request", "events"})
            for record in records if record.task_id in pinned_ids
        ]
        if failure is not None:
            failure_events = {
                number for record in records if record.task_id == failure.task_id
                for number in record.events
            }
            visible_reference_ids = {item["event_id"] for item in context["reference_history"]}
            context["reference_history"].extend(
                {"event_id": number,
                 "references": [item.model_dump(mode="json") for item in event.references],
                 "name_updates": [item.model_dump(mode="json") for item in event.name_updates]}
                for number, event in exchanges if number in failure_events
                and number not in visible_reference_ids and (event.references or event.name_updates)
            )
        # Keep the supporting citations of visible evidence citable after compaction.
        reference_events = dict(exchanges)
        reference_history = {item["event_id"]: item for item in context["reference_history"]}
        pending_references = list(reference_history)
        while pending_references:
            number = pending_references.pop()
            for reference in reference_events[number].references:
                if reference.event_id is None:
                    continue
                source = reference_events.get(reference.event_id)
                if source is None or reference.event_id >= number:
                    raise CollageError("Historical photo reference has no earlier supporting event.")
                if reference.event_id not in reference_history:
                    reference_history[reference.event_id] = {
                        "event_id": reference.event_id,
                        **source.model_dump(mode="json", include={"references", "name_updates"}),
                    }
                    pending_references.append(reference.event_id)
        context["reference_history"] = [
            reference_history[number] for number in sorted(reference_history)
        ]
        active_id = getattr(self, "_active_task", None)
        task_id = intent.task_turn if intent is not None else active_id
        active_task = next(
            (record for record in records if request_start is not None
             and record.task_id == task_id), None,
        )
        task_events = {
            number for record in records if record.task_id in {task_id, active_id}
            for number in record.events
        }
        context["active_task"] = {
            "request": active_task.request if active_task else prompt,
            "answers": list(dict.fromkeys(
                [event.prompt for number, event in exchanges if active_task
                 and number in task_events and event.prompt != active_task.request]
                + ([prompt] if active_task and prompt != active_task.request else [])
            )),
        }
        if stage == "generation":
            if intent is None:
                raise CollageError("Generation requires a validated intent.")
            baseline = self.source_recipe(intent.source)
            reference = self.source_recipe(intent.reference)
            context.update({
                "resolved_intent": intent.model_dump(mode="json"),
                "original_task": intent.task_request,
                "editing_baseline": baseline.model_dump(mode="json") if baseline else None,
                "baseline_geometry": (
                    [g.model_dump(mode="json")
                     for g in resolve_layout(baseline, project.photos, 1).geometry]
                    if baseline else None
                ),
                "reference_to_avoid": reference.model_dump(mode="json") if reference else None,
            })
        else:
            baseline = self.baseline()
            context["current_layout"] = baseline.model_dump(mode="json") if baseline else None
        return context

    def tasks(self) -> list[TaskRecord]:
        events = dict(zip(self.state.history, self.history(), strict=True))
        proposals = {
            event.proposal_id: self.proposal(event.proposal_id, _events=events)
            for event in events.values()
            if isinstance(event, Exchange) and event.outcome == "proposal"
        }
        initial = None
        if self.state.initial_version is not None:
            source = LayoutSource(accepted_version=self.state.initial_version)
            recipe = self.source_recipe(source)
            assert recipe is not None
            initial = (source, recipe)
        records = task_records(events, proposals, initial)
        expected = initial[0] if initial else None
        for event in events.values():
            if (
                isinstance(event, Exchange) and event.outcome in {"proposal", "selection"}
                or isinstance(event, LocalEvent) and event.kind == "accept"
                or isinstance(event, LocalSelection)
            ):
                expected = LayoutSource(proposal_id=event.proposal_id)
        if expected != self._current_source():
            raise CollageError("Working baseline does not match recorded navigation.")
        return records

    def _pending_failure(self) -> Exchange | None:
        if getattr(self, "_independent_task", False):
            return None
        task_id = None
        for event in reversed(self.history()):
            if isinstance(event, LocalSelection):
                break
            if not isinstance(event, Exchange) or event.outcome == "inspection":
                continue
            if task_id is None:
                task_id = event.task_id
            if event.task_id != task_id:
                break
            if event.generation_timeout:
                return event
            if event.outcome not in {"invalid", "intent", "question"} and not (
                event.outcome == "error" and event.stage == "interpretation"
            ):
                break
        return None

    def _task_origin(self, prompt: str) -> tuple[int, str]:
        if getattr(self, "_independent_task", False):
            return self._next_event(), prompt
        failure = self._pending_failure()
        if failure is not None:
            history = dict(zip(self.state.history, self.history(), strict=True))
            return failure.task_id, history[failure.task_id].prompt
        receipt = self._pending_names()
        if receipt is not None:
            history = dict(zip(self.state.history, self.history(), strict=True))
            return receipt[1].task_id, history[receipt[1].task_id].prompt
        pending = self._pending_question()
        if pending is not None:
            history = dict(zip(self.state.history, self.history(), strict=True))
            event = pending[1]
            return event.task_id, history[event.task_id].prompt
        return self._next_event(), prompt

    def _pending_question(self) -> tuple[int, Exchange] | None:
        if getattr(self, "_independent_task", False):
            return None
        for number, event in reversed(list(zip(self.state.history, self.history(), strict=True))):
            if isinstance(event, LocalSelection):
                return None
            if not isinstance(event, Exchange) or event.outcome == "inspection":
                continue
            if event.outcome in {"invalid", "error"} and event.stage == "interpretation":
                continue
            return (number, event) if event.outcome == "question" else None
        return None

    def _pending_names(self) -> tuple[int, Exchange] | None:
        pointer = self.state.pending_names
        if pointer is None:
            return None
        if pointer.event_id not in self.state.history:
            raise CollageError("Pending naming receipt is outside recorded history.")
        event = HISTORY.validate_python(read_json(child(
            self.root, "events", f"{pointer.event_id:06d}.json",
        )))
        if (
            not isinstance(event, Exchange) or event.name_receipt is None
            or digest(canonical(event)) != pointer.sha256
        ):
            raise CollageError("Pending naming receipt changed; no names or edit applied.")
        return pointer.event_id, event

    def _check_receipt(self, receipt: NameReceipt) -> None:
        self._fresh()
        if (
            receipt.baseline != self._current_source()
            or receipt.controls != self.state.controls
            or receipt.names_digest != names_digest(self.state.photo_names)
        ):
            raise CollageError("Naming receipt conflicts with current state; no names or edit applied.")
        if receipt.intent is not None and receipt.intent.source is not None:
            recipe = self.source_recipe(receipt.intent.source)
            assert recipe is not None
            self._validate_recipe(recipe)

    def pending_name_question(self) -> str | None:
        pending = self._pending_names()
        return receipt_question(pending[1].name_receipt, self.state.photo_names) if pending else None

    def _name_receipt(
        self, prompt: str, raw: str, updates: list[NameUpdate],
        intent: ResolvedIntent | None, requests: RequestLog,
    ) -> RequestResult:
        if intent is not None:
            _, names = memory_changes(updates, self.state.photo_names, self._next_event())
            self._check_memory_references(intent, names)
        receipt = NameReceipt(
            updates=[item.model_copy(update={"name": " ".join(item.name.split())}) for item in updates],
            intent=intent, baseline=self._current_source(),
            controls=self.state.controls, names_digest=names_digest(self.state.photo_names),
        )
        number = self._append(Exchange(
            prompt=prompt, response=raw, outcome="name_confirmation",
            stage="interpretation", parent=self.state.baseline, run_id=None,
            attempt=len(requests.attempts()), name_receipt=receipt,
        ))
        return RequestResult(
            kind="name_confirmation", event_id=number,
            question=receipt_question(receipt, self.state.photo_names),
        )

    def _remember(
        self, prompt: str, raw: str, updates: list[NameUpdate], intent: ResolvedIntent | None,
        requests: RequestLog, progress: Progress | None, *, receipt_event: int | None = None,
    ) -> RequestResult | None:
        self._fresh()
        changes, names = memory_changes(
            updates, self.state.photo_names, self._next_event(), receipt_event,
        )
        if intent is not None:
            self._check_memory_references(intent, names)
        if intent is not None and intent.action == "select":
            result = self._select(
                prompt, raw, intent, requests, updates=changes, names=names,
                receipt_event=receipt_event,
            )
        else:
            number = self._append(Exchange(
                prompt=prompt, response=raw,
                outcome="intent" if intent is not None else "acknowledgement",
                intent=intent, stage="interpretation", parent=self.state.baseline,
                run_id=None, attempt=len(requests.attempts()), name_updates=changes,
                receipt_event=receipt_event, references=intent.references if intent else [],
            ), photo_names=names)
            result = RequestResult(
                kind="acknowledgement", event_id=number,
                acknowledgement=memory_message(updates),
            ) if intent is None else None
        if progress is not None and intent is not None:
            progress("memory", memory_message(updates))
            progress("intent", intent)
        return result

    def _select(
        self, prompt: str, raw: str, intent: ResolvedIntent, requests: RequestLog, *,
        updates: list[PhotoName] | None = None, names: list[PhotoName] | None = None,
        receipt_event: int | None = None,
    ) -> RequestResult:
        self._fresh()
        if intent.action != "select" or intent.source is None or intent.source.proposal_id is None:
            raise CollageError("Selection requires an exact preserved proposal.")
        proposal_id = intent.source.proposal_id
        number = self._append(Exchange(
            prompt=prompt, response=raw, outcome="selection", stage="interpretation", intent=intent,
            parent=self.state.baseline, run_id=None, attempt=len(requests.attempts()),
            proposal_id=proposal_id, references=intent.references,
            name_updates=updates or [], receipt_event=receipt_event,
        ), baseline=proposal_id, photo_names=names if names is not None else self.state.photo_names)
        return RequestResult(kind="selection", event_id=number, proposal_id=proposal_id)

    def selection_task(self) -> int | None:
        """Identify unfinished semantic work, without claiming HTTP preparation."""
        receipt = self._pending_names()
        question = self._pending_question()
        failure = self._pending_failure()
        if receipt or question:
            return (receipt or question)[1].task_id
        if failure is not None:
            return failure.task_id
        records = self.tasks()
        return records[-1].task_id if records and records[-1].outcome in {
            "intent", "invalid", "name_confirmation",
        } else None

    def select_proposal(self, proposal_id: str, *, abandon_pending: bool = False) -> int:
        """Record explicit local navigation, without interpreting or accepting."""
        self._fresh()
        self.proposal(proposal_id)
        task = self.selection_task()
        if task is not None and not abandon_pending:
            raise CollageError("Confirm ending the pending request before selecting a collage.")
        number = self._append(LocalSelection(
            proposal_id=proposal_id, baseline_before=self._current_source(), abandoned_task=task,
        ), baseline=proposal_id, pending_names=None)
        self.tasks()
        return number

    def _resolve_intent(self, reply: Intent, prompt: str) -> ResolvedIntent:
        failure = self._pending_failure()
        if isinstance(reply, ResumeIntent):
            if failure is None:
                raise CollageError("No confirmed generation timeout to resume.")
            if failure.intent.source is not None:
                recipe = self.source_recipe(failure.intent.source)
                assert recipe is not None
                self._validate_recipe(recipe)
            return failure.intent
        if failure is not None and not isinstance(reply, (QuestionIntent, MemoryIntent)):
            raise CollageError("Continue the timed-out task with resume, or mark a new task independent.")
        _, task_request = self._task_origin(prompt)
        task_turn = self._active_task
        source = None
        reference = None
        references = reply.references
        if isinstance(reply, EditIntent):
            source = (
                self._current_source() if reply.source == "current"
                else LayoutSource(proposal_id=reply.source)
            )
            if source is None:
                raise CollageError("No current editing source; use fresh or ask a question.")
        elif isinstance(reply, SelectIntent):
            source = LayoutSource(proposal_id=reply.proposal_id)
        elif isinstance(reply, RetryIntent):
            previous = self.proposal(reply.proposal_id)
            source = previous.intent.source
            task_turn = previous.intent.task_turn
            task_request = previous.intent.task_request
            reference = LayoutSource(proposal_id=previous.proposal_id)
            references = previous.intent.references
        elif isinstance(reply, FreshIntent):
            reference = self._current_source()
        else:
            raise CollageError("A question cannot be resolved as a generation action.")
        if source is not None:
            recipe = self.source_recipe(source)
            assert recipe is not None
            self._validate_recipe(recipe)
        return ResolvedIntent(
            action=reply.action, source=source, task_turn=task_turn,
            task_request=task_request, reference=reference, references=references,
            navigation=reply.navigation,
        )

    def _check_memory_references(
        self, intent: ResolvedIntent, names: list[PhotoName] | None = None,
    ) -> None:
        check_forgotten(
            intent.references, self.state.photo_names if names is None else names,
            {number: event for number, event in zip(self.state.history, self.history(), strict=True)
             if isinstance(event, Exchange)},
        )

    @staticmethod
    def _feedback(exc: CollageError | ValidationError) -> str:
        if isinstance(exc, ValidationError):
            errors = [
                {"field": list(item["loc"]), "error": item["type"]}
                for item in exc.errors(include_url=False, include_context=False, include_input=False)[:20]
            ]
            return json.dumps(errors)[:8192]
        if isinstance(exc, LayoutBoundsError):
            return json.dumps(exc.details)[:8192]
        return str(exc)[:2048]

    async def request(
        self, prompt: str, client: ModelClient, requests: RequestLog | None = None,
        *, progress: Progress | None = None,
    ) -> RequestResult:
        requests = requests if requests is not None else RequestLog(self.store, self.project_id)
        result = await self.interpret(prompt, client, requests, progress=progress)
        if isinstance(result, PreparedGeneration):
            return await self.generate(result, client, requests, progress=progress)
        return result

    async def interpret(
        self, prompt: str, client: ModelClient, requests: RequestLog | None = None,
        *, progress: Progress | None = None,
    ) -> RequestResult | PreparedGeneration:
        """Resolve a request, returning immediately when no layout is needed."""
        return await self._request_stage(prompt, client, requests, progress=progress)

    def _generation_digest(self, intent: ResolvedIntent) -> str:
        sources = (self._current_source(), intent.source, intent.reference)
        recipes = [self.source_recipe(source) for source in sources if source is not None]
        return digest(
            canonical(self.store.load(self.project_id)) + canonical(self.state)
            + b"".join(canonical(event) for event in self.history())
            + b"".join(canonical(recipe) for recipe in recipes if recipe is not None)
        )

    def _prepare_generation(
        self, prompt: str, intent: ResolvedIntent, request_start: int,
        calls_used: int, requests: RequestLog,
    ) -> PreparedGeneration:
        self._fresh()
        return PreparedGeneration(
            project_id=self.project_id, photo_digest=self.photo_digest,
            state_digest=self._generation_digest(intent), prompt=prompt, intent=intent,
            request_start=request_start, active_task=self._active_task,
            independent_task=self._independent_task, calls_used=calls_used,
            limits=requests.limits, generation_reasoning=requests.generation_reasoning,
            interpretation_reasoning=requests.interpretation_reasoning,
        )

    async def generate(
        self, prepared: PreparedGeneration, client: ModelClient,
        requests: RequestLog | None = None, *, progress: Progress | None = None,
    ) -> RequestResult:
        """Continue a bound interpretation without repeating its saved effects."""
        self._fresh()
        if (
            prepared.project_id != self.project_id or prepared.photo_digest != self.photo_digest
            or prepared.state_digest != self._generation_digest(prepared.intent)
        ):
            raise CollageError("Prepared generation belongs to another project or stale state/source.")
        events = [
            event for number, event in zip(self.state.history, self.history(), strict=True)
            if number >= prepared.request_start
        ]
        if (
            len(events) != prepared.calls_used
            or not isinstance(events[-1], Exchange)
            or events[-1].outcome != "intent" or events[-1].intent != prepared.intent
            or events[-1].prompt != prepared.prompt or events[-1].task_id != prepared.active_task
            or any(not isinstance(event, Exchange) or event.stage != "interpretation"
                   or event.outcome != "invalid" for event in events[:-1])
        ):
            raise CollageError("Prepared generation does not match its interpretation history.")
        if requests is None:
            requests = RequestLog(
                self.store, self.project_id,
                generation_reasoning=prepared.generation_reasoning,
                interpretation_reasoning=prepared.interpretation_reasoning,
            )
            requests.limits = prepared.limits
        if (
            requests.limits != prepared.limits
            or requests.generation_reasoning != prepared.generation_reasoning
            or requests.interpretation_reasoning != prepared.interpretation_reasoning
        ):
            raise CollageError("Prepared generation request limits/reasoning changed.")
        result = await self._request_stage(
            prepared.prompt, client, requests, progress=progress, prepared=prepared,
        )
        assert isinstance(result, RequestResult)
        return result

    async def _request_stage(
        self, prompt: str, client: ModelClient, requests: RequestLog | None,
        *, progress: Progress | None, prepared: PreparedGeneration | None = None,
    ) -> RequestResult | PreparedGeneration:
        if not prompt.strip() or len(prompt.encode("utf-8")) > MAX_JSON_BYTES // 4:
            raise CollageError("Prompt must be nonempty and at most 256 KiB UTF-8.")
        requests = requests if requests is not None else RequestLog(self.store, self.project_id)
        if requests.root != child(self.root, "requests"):
            raise CollageError("Request accounting belongs to a different project.")
        feedback = None
        intent = prepared.intent if prepared is not None else None
        request_start = prepared.request_start if prepared is not None else self._next_event()
        self._independent_task = prepared.independent_task if prepared is not None else False
        if prepared is None:
            request_task, request_origin = self._task_origin(prompt)
            self._active_task = request_task
        else:
            self._active_task = prepared.active_task
        requests.begin_stage("generation" if prepared is not None else "interpretation")
        if prepared is not None and progress is not None:
            progress("generation", intent)
        for call in range(prepared.calls_used if prepared is not None else 0, 4):
            requests.check_work_deadline()
            if prepared is None and intent is not None:
                return self._prepare_generation(prompt, intent, request_start, call, requests)
            stage = "interpretation" if intent is None else "generation"
            context = self.context(
                prompt, feedback, stage=stage, intent=intent, request_start=request_start,
            )
            attempts_before = len(requests.attempts())
            try:
                async with asyncio.timeout(requests.remaining_seconds()):
                    raw = await client.complete(context, requests, f"{self.project_id}: {stage}")
                requests.remaining_seconds()
            except (CollageError, OSError, TimeoutError) as exc:
                timed_out = isinstance(exc, (StageTimeout, TimeoutError))
                error = (
                    "Generation timed out before publication; editing baseline is unchanged. "
                    'Repeat the prompt or say "try again". Usage may be unavailable; retries are new calls.'
                    if timed_out and stage == "generation"
                    else "Interpretation timed out; no automatic retry." if timed_out
                    else str(exc) if isinstance(exc, CollageError)
                    else f"Request stopped: {type(exc).__name__}."
                )
                self._append(Exchange(
                    prompt=prompt, outcome="error", parent=self.state.baseline,
                    stage=stage, intent=intent,
                    run_id=None,
                    attempt=(
                        len(requests.attempts())
                        if len(requests.attempts()) > attempts_before else None
                    ),
                    error=error, generation_timeout=timed_out and stage == "generation",
                ))
                if timed_out:
                    raise StageTimeout(error) from exc
                raise
            try:
                data = parse_json(raw.encode("utf-8"))
                if intent is None:
                    reply = INTENT.validate_python(data)
                    history = dict(zip(self.state.history, self.history(), strict=True))
                    pending_names = self._pending_names()
                    if isinstance(reply, InspectNamesIntent):
                        self._active_task = self._next_event()
                        event_id = self._append(Exchange(
                            prompt=prompt, response=raw, outcome="inspection", stage=stage,
                            parent=self.state.baseline, run_id=None, attempt=len(requests.attempts()),
                        ))
                        return RequestResult(
                            kind="acknowledgement", event_id=event_id,
                            acknowledgement=names_message(self.state.photo_names),
                        )
                    if isinstance(reply, NamesIntent):
                        if pending_names is None or reply.receipt_event != pending_names[0]:
                            raise PhotoReferenceError("Naming decision has no matching current receipt.")
                        receipt = pending_names[1].name_receipt
                        assert receipt is not None
                        self._check_receipt(receipt)
                        if reply.decision == "reject":
                            event_id = self._append(Exchange(
                                prompt=prompt, response=raw, outcome="acknowledgement",
                                stage=stage, parent=self.state.baseline, run_id=None,
                                attempt=len(requests.attempts()), receipt_event=pending_names[0],
                            ))
                            return RequestResult(
                                kind="acknowledgement", event_id=event_id,
                                acknowledgement="Names not saved; the associated edit was not applied. "
                                "You can rephrase your request.",
                            )
                        intent = receipt.intent
                        result = self._remember(
                            prompt, raw, receipt.updates, intent, requests, progress,
                            receipt_event=pending_names[0],
                        )
                        if result is not None:
                            return result
                        feedback = None
                        continue
                    pending_question = context["pending_question"]
                    previous_number = (
                        pending_question["event_id"] if isinstance(pending_question, dict) else None
                    )
                    previous = history.get(previous_number)
                    pending_reply = (
                        INTENT.validate_json(previous.response or "")
                        if isinstance(previous, Exchange) and previous.outcome == "question" else None
                    )
                    if isinstance(pending_reply, QuestionIntent):
                        if isinstance(reply, MemoryIntent) and pending_reply.continuation == "design" and (
                            reply.continues_task
                        ):
                            raise PhotoReferenceError("The identity answer must continue the original design, not only remember names.")
                    if not reply.continues_task:
                        previous = None
                    visible_tasks = {
                        item["task_id"] for key in ("recent_tasks", "compact_tasks", "required_tasks")
                        for item in context[key]
                    }
                    visible = context["reference_history"]
                    assert isinstance(visible, list)
                    visible_ids = {item["event_id"] for item in visible}
                    updates = [] if isinstance(reply, ResumeIntent) else ground_references(
                        reply, prompt,
                        photos={photo.photo_id for photo in self.store.load(self.project_id).photos},
                        names=self.state.photo_names,
                        task_request=request_origin if reply.continues_task else prompt,
                        reference_history={
                            number: event for number, event in history.items()
                            if number in visible_ids and isinstance(event, Exchange)
                        },
                        evidence_events={
                            number: event for number, event in history.items()
                            if isinstance(event, Exchange) and event.task_id == self._active_task
                        } if reply.continues_task else {},
                        event_id=self._next_event(),
                    )
                    if not isinstance(reply, ResumeIntent):
                        validate_navigation(
                            reply, prompt,
                            request_origin if reply.continues_task else prompt,
                            self.tasks(), self._current_source(), self.state.photo_names, visible_tasks,
                            pending_reply if isinstance(pending_reply, QuestionIntent) else None,
                        )
                    if not reply.continues_task:
                        self._independent_task = True
                        self._active_task = self._next_event()
                    if updates:
                        candidate = None if isinstance(reply, MemoryIntent) else self._resolve_intent(reply, prompt)
                        if pending_names is not None and reply.continues_task:
                            held = pending_names[1].name_receipt.intent
                            if (held is None) != (candidate is None) or held is not None and (
                                candidate.action != held.action or candidate.source != held.source
                            ):
                                raise PhotoReferenceError("Naming revision must retain its original action/source.")
                        if (
                            pending_names is not None and reply.continues_task
                            or conflicting_names(updates, self.state.photo_names)
                        ):
                            if progress is not None:
                                progress("intent", None)
                            return self._name_receipt(prompt, raw, updates, candidate, requests)
                        intent = candidate
                        result = self._remember(prompt, raw, updates, intent, requests, progress)
                        if result is not None:
                            return result
                        feedback = None
                        continue
                    if pending_names is not None and reply.continues_task and not isinstance(reply, QuestionIntent):
                        raise PhotoReferenceError("Confirm, correct or reject the pending naming receipt first.")
                    if isinstance(reply, QuestionIntent):
                        event_id = self._append(Exchange(
                            prompt=prompt, response=raw, outcome="question",
                            stage=stage, parent=self.state.baseline,
                            run_id=None, attempt=len(requests.attempts()),
                            references=reply.references,
                        ))
                        if progress is not None:
                            progress("question", None)
                        return RequestResult(
                            kind="question", question=reply.question, event_id=event_id,
                            identity_question=any(
                                item.photo_id is None for item in reply.references
                            ),
                        )
                    if isinstance(reply, MemoryIntent):
                        event_id = self._append(Exchange(
                            prompt=prompt, response=raw, outcome="acknowledgement",
                            stage=stage, parent=self.state.baseline, run_id=None,
                            attempt=len(requests.attempts()), references=reply.references,
                        ))
                        return RequestResult(
                            kind="acknowledgement", acknowledgement=memory_message(reply.name_updates),
                            event_id=event_id,
                        )
                    intent = self._resolve_intent(reply, prompt)
                    self._check_memory_references(intent)
                    if isinstance(reply, SelectIntent):
                        if progress is not None:
                            progress("intent", intent)
                        return self._select(prompt, raw, intent, requests)
                    self._append(Exchange(
                        prompt=prompt, response=raw, outcome="intent", stage=stage,
                        intent=intent, parent=self.state.baseline, run_id=None,
                        attempt=len(requests.attempts()),
                        references=reply.references,
                    ))
                    if progress is not None:
                        progress("intent", intent)
                    feedback = None
                    continue
                resolved = self._validate_recipe(InputLayout.model_validate(data))
            except (CollageError, ValidationError) as exc:
                if stage == "interpretation":
                    intent = None
                    self._independent_task = False
                    self._active_task = request_task
                feedback = self._feedback(exc)
                self._append(Exchange(
                    prompt=prompt, response=(raw if len(raw.encode("utf-8")) <= MAX_JSON_BYTES // 2 else None),
                    outcome="invalid", parent=self.state.baseline,
                    stage=stage, intent=intent,
                    run_id=None, attempt=len(requests.attempts()), error=feedback,
                ))
                if call == 3 or (stage == "interpretation" and call == 1):
                    self._fresh()
                    self.baseline()
                    raise RequestRejected(
                        feedback, self._current_source(), identity=isinstance(exc, PhotoReferenceError),
                    ) from exc
                continue
            try:
                return self._publish(prompt, raw, resolved, requests, intent)
            except (CollageError, ValidationError, OSError) as exc:
                self._append(Exchange(
                    prompt=prompt,
                    response=raw if len(raw.encode("utf-8")) <= MAX_JSON_BYTES // 2 else None,
                    outcome="error", parent=self.state.baseline,
                    stage=stage, intent=intent,
                    run_id=None, attempt=len(requests.attempts()),
                    error=f"Proposal publication stopped: {type(exc).__name__}.",
                ))
                raise
        raise AssertionError("Unreachable correction loop.")

    def _publish(
        self, prompt: str, raw: str, resolved: ResolvedLayout, requests: RequestLog,
        intent: ResolvedIntent,
    ) -> RequestResult:
        requests.check_work_deadline()
        self._fresh()
        proposals = child(self.root, "proposals")
        proposals.mkdir(parents=True, exist_ok=True)
        numbers = [
            int(p.name[1:]) for p in proposals.iterdir()
            if re.fullmatch(r"P[0-9]{3,}", p.name)
        ]
        proposal_id = f"P{max(numbers, default=0) + 1:03d}"
        event_id = self._next_event()
        project = self.store.load(self.project_id)
        event = Exchange(
            prompt=prompt, response=raw, outcome="proposal",
            parent=intent.source.proposal_id if intent.source else None,
            stage="generation", intent=intent, task_id=self._active_task,
            baseline_before=self._current_source(),
            run_id=None, attempt=len(requests.attempts()), proposal_id=proposal_id,
            references=intent.references,
        )
        with tempfile.TemporaryDirectory(dir=self.root, prefix=".proposal-") as directory:
            staging = Path(directory)
            preview = staging / "preview.png"
            render_layout(resolved, project.photos, self.store.photo_paths(project), preview)
            requests.check_work_deadline()
            proposal = Proposal(
                proposal_id=proposal_id, turn_id=event_id,
                parent=intent.source.proposal_id if intent.source else None, intent=intent,
                controls=self.state.controls, recipe=resolved.recipe, geometry=resolved.geometry,
                recipe_digest=digest(canonical(resolved.recipe)),
                preview_digest=digest(preview.read_bytes()),
            )
            save(staging / "proposal.json", proposal)
            self._validate_proposal(
                Proposal.model_validate(read_json(staging / "proposal.json")),
                proposal_id, event_id, event,
                {**dict(zip(self.state.history, self.history(), strict=True)), event_id: event},
                preview,
            )
            self._fresh()
            requests.check_work_deadline()
            staging.rename(child(proposals, proposal_id))
        self._append(event, baseline=proposal_id)
        return RequestResult(kind="proposal", proposal_id=proposal_id, event_id=event_id)

    def controls(self, controls: Controls) -> None:
        self._fresh()
        if self._pending_names() is not None:
            raise CollageError("Resolve the pending naming receipt before changing controls.")
        self._append(LocalEvent(kind="controls", controls=controls), controls=controls)

    def rate(self, proposal_id: str, rating: str, note: str | None) -> None:
        self.proposal(proposal_id)
        event = LocalEvent.model_validate({
            "kind": "rating", "proposal_id": proposal_id, "rating": rating, "note": note,
        })
        self._append(event)

    def accept(self, proposal_id: str) -> int:
        self._fresh()
        if self._pending_names() is not None:
            raise CollageError("Resolve the pending naming receipt before changing the accepted source.")
        proposal = self.proposal(proposal_id)
        self._validate_recipe(proposal.recipe)
        if self.state.accepted_proposal == proposal_id:
            assert self.state.expected_version is not None
            self._append(LocalEvent(
                kind="accept", proposal_id=proposal_id, accepted_version=self.state.expected_version
            ), baseline=proposal_id)
            return self.state.expected_version
        intent = AcceptanceIntent(
            proposal_id=proposal_id, previous_version=self.state.expected_version,
            next_version=(self.state.expected_version or 0) + 1,
        )
        save(self.intent_path, intent)
        self.store.accept_recipe(
            self.project_id, proposal.recipe, expected_version=intent.previous_version,
            preview=self.preview_path(proposal_id),
        )
        self._recover()
        return intent.next_version

    def _recover(self) -> None:
        if not self.intent_path.exists():
            return
        intent = AcceptanceIntent.model_validate(read_json(self.intent_path))
        project = self.store.load(self.project_id)
        if project.current_version == intent.previous_version:
            if self.state.expected_version != intent.previous_version:
                raise CollageError("Uncommitted acceptance conflicts with conversation state.")
            layout, render = self.store.version_paths(self.project_id, intent.next_version)
            if layout.exists() or render.exists():
                raise CollageError("Partial accepted publication needs manual inspection.")
            self.intent_path.unlink()
            return
        proposal = self.proposal(intent.proposal_id)
        accepted = self.store.load_layout(project, intent.next_version)
        _, preview = self.store.version_paths(self.project_id, intent.next_version)
        if (
            project.current_version != intent.next_version
            or accepted.recipe != proposal.recipe
            or digest(preview.read_bytes()) != proposal.preview_digest
            or self.state.expected_version not in {intent.previous_version, intent.next_version}
        ):
            raise CollageError("Acceptance reconciliation conflict; inspect preserved artifacts.")
        if self.state.expected_version != intent.next_version:
            self._append(LocalEvent(
                kind="accept", proposal_id=intent.proposal_id, accepted_version=intent.next_version
            ), expected_version=intent.next_version, accepted_proposal=intent.proposal_id,
                baseline=intent.proposal_id)
        elif self.state.accepted_proposal != intent.proposal_id:
            raise CollageError("Acceptance index conflicts with its recorded intent.")
        self.intent_path.unlink()
