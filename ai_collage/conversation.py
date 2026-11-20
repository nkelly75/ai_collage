"""Local proposals, real conversation history, and explicit acceptance."""

import asyncio
import json
import re
import tempfile
from pathlib import Path
from typing import Callable, Protocol

from pydantic import ValidationError

from .agent_requests import RequestLog, StageTimeout
from .agent_files import canonical, child, digest, save
from .agent_models import (
    HISTORY, INTENT, AcceptanceIntent, Controls, ConversationState, EditIntent, Exchange,
    FreshIntent, Intent, LayoutSource, LocalEvent, Preferences, Proposal, QuestionIntent,
    RememberIntent, RequestResult, ResolvedIntent, ResumeIntent, RetryIntent, SelectIntent,
)
from .geometry import LayoutBoundsError, resolve_layout
from .imaging import render_layout
from .models import MAX_JSON_BYTES, CollageError, InputLayout, ResolvedLayout
from .projects import ProjectStore, parse_json, read_json
from .photo_references import ground_references, name_history, name_key
from .task_history import (
    TaskRecord, ordinals, retrieve, task_records, undo_steps, undo_target, validate_navigation,
)


class ModelClient(Protocol):
    async def complete(self, context: dict[str, object], requests: RequestLog, purpose: str) -> str: ...


class Conversation:
    def __init__(
        self, store: ProjectStore, project_id: str, *,
        canvas: tuple[int, int] | None = None, preferences: Path | None = None,
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
            self.state = ConversationState.model_validate(read_json(self.state_path))
            if self.state.project_id != project_id or self.state.photo_digest != self.photo_digest:
                raise CollageError("Conversation project/photo identity mismatch.")
            if preferences is not None:
                raise CollageError("Resume uses captured preferences; omit --preferences.")
            if canvas is not None and canvas != (self.state.controls.width, self.state.controls.height):
                raise CollageError("Resume canvas differs; use /canvas explicitly.")
            self._recover()
        else:
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
        name_history(
            self.state.photo_names, dict(zip(self.state.history, self.history(), strict=True)),
            {photo.photo_id for photo in project.photos},
        )
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

    def history(self) -> list[Exchange | LocalEvent]:
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

    def _append(self, event: Exchange | LocalEvent, **updates: object) -> int:
        if ConversationState.model_validate(read_json(self.state_path)) != self.state:
            raise CollageError("Conversation changed; restart before making further changes.")
        number = self._next_event()
        if isinstance(event, Exchange):
            event = event.model_copy(update={
                "task_id": self._active_task,
                "baseline_before": self._current_source(),
            })
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
        self, proposal_id: str, *, _events: dict[int, Exchange | LocalEvent] | None = None,
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
        history: dict[int, Exchange | LocalEvent], preview: Path,
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
            and entry.stage == "interpretation" and entry.outcome in {"intent", "question"}
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
                task.outcome in {"intent", "question"}
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
        prior_records = [
            record for record in records
            if request_start is None or record.task_id < request_start
        ]
        groups: list[list[tuple[int, Exchange]]] = []
        active: list[Exchange] = []
        for number, event in exchanges:
            if request_start is not None and number >= request_start:
                active.append(event)
                continue
            if not groups or groups[-1][0][1].task_id != event.task_id:
                groups.append([])
            groups[-1].append((number, event))
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
        previous = groups[-1][-1][1] if groups and not getattr(self, "_independent_task", False) else None
        context: dict[str, object] = {
            "stage": stage,
            "photos": [
                {"photo_id": p.photo_id, "width": p.width, "height": p.height,
                 "aspect_ratio": p.width / p.height} for p in project.photos
            ],
            "preferences": self.state.preferences.model_dump(),
            "photo_names": [item.model_dump(mode="json") for item in self.state.photo_names],
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
                {"event_id": groups[-1][-1][0], "prompt": previous.prompt,
                 "original_task": intent.task_request if intent else self._task_origin(prompt)[1],
                 "response": previous.response}
                if previous is not None and previous.outcome == "question" else None
            ),
            "failed_candidate": active[-1].response if active and active[-1].outcome == "invalid" else None,
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
        active_task = next(
            (record for record in records if request_start is not None
             and record.task_id == getattr(self, "_active_task", None)), None,
        )
        context["active_task"] = {
            "request": active_task.request if active_task else prompt,
            "answers": list(dict.fromkeys(
                [event.prompt for number, event in exchanges if active_task
                 and number in active_task.events and event.prompt != active_task.request]
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
            if not isinstance(event, Exchange):
                continue
            if task_id is None:
                task_id = event.task_id
            if event.task_id != task_id:
                break
            if event.generation_timeout:
                return event
            if event.outcome not in {"invalid", "intent", "question"}:
                break
        return None

    def _task_origin(self, prompt: str) -> tuple[int, str]:
        if getattr(self, "_independent_task", False):
            return self._next_event(), prompt
        failure = self._pending_failure()
        if failure is not None:
            history = dict(zip(self.state.history, self.history(), strict=True))
            return failure.task_id, history[failure.task_id].prompt
        history = dict(zip(self.state.history, self.history(), strict=True))
        exchanges = [(number, event) for number, event in history.items() if isinstance(event, Exchange)]
        for _, event in reversed(exchanges):
            if event.outcome == "invalid" and event.stage == "interpretation" and event.prompt == prompt:
                continue
            if event.outcome == "question":
                origin = history[event.task_id]
                return event.task_id, origin.prompt
            break
        return self._next_event(), prompt

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
        if failure is not None and not isinstance(reply, (QuestionIntent, RememberIntent)):
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
        *, progress: Callable[[str, ResolvedIntent | None], None] | None = None,
    ) -> RequestResult:
        if not prompt.strip() or len(prompt.encode("utf-8")) > MAX_JSON_BYTES // 4:
            raise CollageError("Prompt must be nonempty and at most 256 KiB UTF-8.")
        requests = requests if requests is not None else RequestLog(self.store, self.project_id)
        if requests.root != child(self.root, "requests"):
            raise CollageError("Request accounting belongs to a different project.")
        feedback = None
        intent = None
        request_start = self._next_event()
        self._independent_task = False
        self._active_task = self._task_origin(prompt)[0]
        requests.begin_stage("interpretation")
        previous_stage = "interpretation"
        for call in range(4):
            stage = "interpretation" if intent is None else "generation"
            if stage != previous_stage:
                requests.begin_stage(stage)
                previous_stage = stage
                if progress is not None:
                    progress("generation", intent)
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
                    pending_question = context["pending_question"]
                    previous_number = (
                        pending_question["event_id"] if isinstance(pending_question, dict) else None
                    )
                    previous = history.get(previous_number)
                    if not reply.continues_task:
                        self._independent_task = True
                        self._active_task = self._next_event()
                        previous = None
                    pending_reply = (
                        INTENT.validate_json(previous.response or "")
                        if isinstance(previous, Exchange) and previous.outcome == "question" else None
                    )
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
                        names=self.state.photo_names, event_id=self._next_event(),
                        task_request=pending_question["original_task"]
                        if isinstance(pending_question, dict) and reply.continues_task else prompt,
                        pending=(previous_number, previous)
                        if previous_number is not None and isinstance(previous, Exchange)
                        and previous.outcome == "question" else None,
                        reference_history={
                            number: event for number, event in history.items()
                            if number in visible_ids and isinstance(event, Exchange)
                        },
                    )
                    names = {name_key(item.name): item for item in self.state.photo_names}
                    names.update({name_key(item.name): item for item in updates})
                    if not isinstance(reply, ResumeIntent):
                        validate_navigation(
                            reply, prompt,
                            pending_question["original_task"]
                            if isinstance(pending_question, dict) and reply.continues_task else prompt,
                            self.tasks(), self._current_source(), list(names.values()), visible_tasks,
                            pending_reply if isinstance(pending_reply, QuestionIntent) else None,
                        )
                    if isinstance(reply, QuestionIntent):
                        event_id = self._append(Exchange(
                            prompt=prompt, response=raw, outcome="question",
                            stage=stage, parent=self.state.baseline,
                            run_id=None, attempt=len(requests.attempts()),
                            references=reply.references, name_updates=updates,
                        ), photo_names=list(names.values()))
                        if progress is not None:
                            progress("question", None)
                        return RequestResult(
                            kind="question", question=reply.question, event_id=event_id,
                        )
                    if isinstance(reply, RememberIntent):
                        message = "Remembered: " + "; ".join(
                            f"{item.name} = photo {item.photo_id}" for item in updates
                        ) + "."
                        event_id = self._append(Exchange(
                            prompt=prompt, response=raw, outcome="acknowledgement",
                            stage=stage, parent=self.state.baseline, run_id=None,
                            attempt=len(requests.attempts()), references=reply.references,
                            name_updates=updates,
                        ), photo_names=list(names.values()))
                        if progress is not None:
                            progress("remember", None)
                        return RequestResult(
                            kind="acknowledgement", acknowledgement=message, event_id=event_id,
                        )
                    intent = self._resolve_intent(reply, prompt)
                    if isinstance(reply, SelectIntent):
                        self._fresh()
                        event_id = self._append(Exchange(
                            prompt=prompt, response=raw, outcome="selection", stage=stage,
                            intent=intent, parent=self.state.baseline, run_id=None,
                            attempt=len(requests.attempts()), proposal_id=reply.proposal_id,
                            references=reply.references, name_updates=updates,
                        ), baseline=reply.proposal_id, photo_names=list(names.values()))
                        if progress is not None:
                            progress("intent", intent)
                        return RequestResult(
                            kind="selection", proposal_id=reply.proposal_id, event_id=event_id,
                        )
                    self._append(Exchange(
                        prompt=prompt, response=raw, outcome="intent", stage=stage,
                        intent=intent, parent=self.state.baseline, run_id=None,
                        attempt=len(requests.attempts()),
                        references=reply.references, name_updates=updates,
                    ), photo_names=list(names.values()))
                    if progress is not None:
                        progress("intent", intent)
                    feedback = None
                    continue
                resolved = self._validate_recipe(InputLayout.model_validate(data))
            except (CollageError, ValidationError) as exc:
                feedback = self._feedback(exc)
                self._append(Exchange(
                    prompt=prompt, response=(raw if len(raw.encode("utf-8")) <= MAX_JSON_BYTES // 2 else None),
                    outcome="invalid", parent=self.state.baseline,
                    stage=stage, intent=intent,
                    run_id=None, attempt=len(requests.attempts()), error=feedback,
                ))
                if call == 3 or (stage == "interpretation" and call == 1):
                    raise CollageError(f"Model correction failed: {feedback}") from exc
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
            staging.rename(child(proposals, proposal_id))
        self._append(event, baseline=proposal_id)
        return RequestResult(kind="proposal", proposal_id=proposal_id, event_id=event_id)

    def controls(self, controls: Controls) -> None:
        self._fresh()
        self._append(LocalEvent(kind="controls", controls=controls), controls=controls)

    def rate(self, proposal_id: str, rating: str, note: str | None) -> None:
        self.proposal(proposal_id)
        event = LocalEvent.model_validate({
            "kind": "rating", "proposal_id": proposal_id, "rating": rating, "note": note,
        })
        self._append(event)

    def accept(self, proposal_id: str) -> int:
        self._fresh()
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
