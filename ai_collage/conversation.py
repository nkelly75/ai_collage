"""Local proposals, real conversation history, and explicit acceptance."""

import json
import re
import tempfile
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from .agent_requests import RequestLog
from .agent_files import canonical, child, digest, save
from .agent_models import (
    HISTORY, INTENT, AcceptanceIntent, Controls, ConversationState, EditIntent, Exchange,
    FreshIntent, Intent, LayoutSource, LocalEvent, Preferences, Proposal, QuestionIntent,
    RememberIntent, RequestResult, ResolvedIntent, RetryIntent, SelectIntent,
)
from .geometry import LayoutBoundsError, resolve_layout
from .imaging import render_layout
from .models import MAX_JSON_BYTES, CollageError, InputLayout, ResolvedLayout
from .projects import ProjectStore, parse_json, read_json
from .photo_references import ground_references, name_history, name_key


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

    def proposal(self, proposal_id: str) -> Proposal:
        preview = self.preview_path(proposal_id)
        committed = {
            entry.proposal_id: (number, entry)
            for number, entry in zip(self.state.history, self.history(), strict=True)
            if isinstance(entry, Exchange) and entry.outcome == "proposal"
        }
        if proposal_id not in committed:
            raise CollageError("Unknown or unpublished proposal ID.")
        proposal = Proposal.model_validate(read_json(child(preview.parent, "proposal.json")))
        number, event = committed[proposal_id]
        project = self.store.load(self.project_id)
        expected = resolve_layout(proposal.recipe, project.photos, 1)
        history = dict(zip(self.state.history, self.history(), strict=True))
        task = history.get(proposal.intent.task_turn)
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
            or any(identity not in committed or committed[identity][0] >= number for identity in identities)
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
            or task.stage != "interpretation" or task.outcome not in {"intent", "question"}
        ):
            raise CollageError("Proposal recipe, geometry, or preview identity mismatch.")
        return proposal

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
        groups: list[list[tuple[int, Exchange]]] = []
        active: list[Exchange] = []
        for number, event in exchanges:
            if request_start is not None and number >= request_start:
                active.append(event)
                continue
            if not groups or (
                groups[-1][-1][1].outcome in {
                    "proposal", "selection", "question", "acknowledgement", "error",
                }
                or len(groups[-1]) >= 4
                or (
                    event.stage == "interpretation" and len(groups[-1]) >= 2
                    and all(item.stage == "interpretation" for _, item in groups[-1])
                )
            ):
                groups.append([])
            groups[-1].append((number, event))
        recent = groups[-3:]
        history = [
            {
                "kind": "turn", "turn": group[0][0], "prompt": group[0][1].prompt,
                "outcome": group[-1][1].outcome, "proposal_id": group[-1][1].proposal_id,
                "response": group[-1][1].response if group[-1][1].outcome == "question" else None,
            }
            for group in recent
        ]
        published = [event.proposal_id for _, event in exchanges if event.outcome == "proposal"]
        selected = {self.state.baseline}
        if published:
            selected.update((published[0], published[-1]))
        selected.update(event.proposal_id for group in recent for _, event in group)
        selected.update(re.findall(r"\bP[0-9]{3,}\b", prompt))
        ordinals = {
            "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
            "sixth": 6, "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10,
        }
        positions = [
            ordinals[word] for word in re.findall(r"\b[a-z]+\b", prompt.lower())
            if word in ordinals
        ]
        positions.extend(
            int(value) for value in re.findall(r"\b([0-9]{1,9})(?:st|nd|rd|th)\b", prompt.lower())
        )
        selected.update(published[position - 1] for position in positions if 1 <= position <= len(published))
        if intent is not None:
            selected.update(
                source.proposal_id for source in (intent.source, intent.reference) if source is not None
            )
        catalogue = []
        for ordinal, proposal_id in enumerate(published, 1):
            if proposal_id not in selected:
                continue
            assert proposal_id is not None
            proposal = self.proposal(proposal_id)
            catalogue.append({
                "proposal_id": proposal_id, "ordinal": ordinal,
                "action": proposal.intent.action,
                "source": proposal.intent.source.model_dump(mode="json") if proposal.intent.source else None,
                "controls": proposal.controls.model_dump(mode="json"),
            })
        previous = groups[-1][-1][1] if groups else None
        context: dict[str, object] = {
            "stage": stage,
            "photos": [
                {"photo_id": p.photo_id, "width": p.width, "height": p.height,
                 "aspect_ratio": p.width / p.height} for p in project.photos
            ],
            "preferences": self.state.preferences.model_dump(),
            "photo_names": [item.model_dump(mode="json") for item in self.state.photo_names],
            "reference_history": [
                {"event_id": number,
                 "references": [item.model_dump(mode="json") for item in event.references],
                 "name_updates": [item.model_dump(mode="json") for item in event.name_updates]}
                for group in recent for number, event in [group[-1]]
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

    def _task_origin(self, prompt: str) -> tuple[int, str]:
        task_turn = self._next_event()
        task_request = prompt
        question_prompt = prompt
        for number, event in reversed(list(zip(self.state.history, self.history(), strict=True))):
            if (
                isinstance(event, Exchange) and event.outcome == "invalid"
                and event.stage == "interpretation" and event.prompt == question_prompt
            ):
                continue
            if not isinstance(event, Exchange) or event.outcome != "question":
                break
            task_turn, task_request = number, event.prompt
            question_prompt = event.prompt
        return task_turn, task_request

    def _resolve_intent(self, reply: Intent, prompt: str) -> ResolvedIntent:
        task_turn, task_request = self._task_origin(prompt)
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
            task_request=task_request,             reference=reference, references=references,
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
    ) -> RequestResult:
        if not prompt.strip() or len(prompt.encode("utf-8")) > MAX_JSON_BYTES // 4:
            raise CollageError("Prompt must be nonempty and at most 256 KiB UTF-8.")
        requests = requests if requests is not None else RequestLog(self.store, self.project_id)
        if requests.root != child(self.root, "requests"):
            raise CollageError("Request accounting belongs to a different project.")
        feedback = None
        intent = None
        request_start = self._next_event()
        for call in range(4):
            stage = "interpretation" if intent is None else "generation"
            context = self.context(
                prompt, feedback, stage=stage, intent=intent, request_start=request_start,
            )
            attempts_before = len(requests.attempts())
            try:
                raw = await client.complete(context, requests, f"{self.project_id}: {stage}")
            except (CollageError, OSError) as exc:
                self._append(Exchange(
                    prompt=prompt, outcome="error", parent=self.state.baseline,
                    stage=stage, intent=intent,
                    run_id=None,
                    attempt=(
                        len(requests.attempts())
                        if len(requests.attempts()) > attempts_before else None
                    ),
                    error=str(exc) if isinstance(exc, CollageError) else f"Request stopped: {type(exc).__name__}.",
                ))
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
                    visible = context["reference_history"]
                    assert isinstance(visible, list)
                    visible_ids = {item["event_id"] for item in visible}
                    updates = ground_references(
                        reply, prompt,
                        photos={photo.photo_id for photo in self.store.load(self.project_id).photos},
                        names=self.state.photo_names, event_id=self._next_event(),
                        task_request=pending_question["original_task"]
                        if isinstance(pending_question, dict) else prompt,
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
                    if isinstance(reply, QuestionIntent):
                        event_id = self._append(Exchange(
                            prompt=prompt, response=raw, outcome="question",
                            stage=stage, parent=self.state.baseline,
                            run_id=None, attempt=len(requests.attempts()),
                            references=reply.references, name_updates=updates,
                        ), photo_names=list(names.values()))
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
                        return RequestResult(
                            kind="selection", proposal_id=reply.proposal_id, event_id=event_id,
                        )
                    self._append(Exchange(
                        prompt=prompt, response=raw, outcome="intent", stage=stage,
                        intent=intent, parent=self.state.baseline, run_id=None,
                        attempt=len(requests.attempts()),
                        references=reply.references, name_updates=updates,
                    ), photo_names=list(names.values()))
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
            except (CollageError, OSError) as exc:
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
            self._fresh()
            staging.rename(child(proposals, proposal_id))
        self._append(Exchange(
            prompt=prompt, response=raw, outcome="proposal",
            parent=proposal.parent, stage="generation", intent=intent,
            run_id=None, attempt=len(requests.attempts()), proposal_id=proposal_id,
            references=intent.references,
        ), baseline=proposal_id)
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
