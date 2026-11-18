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
    HISTORY, REPLY, AcceptanceIntent, Controls, ConversationState, Exchange,
    LocalEvent, Preferences, Proposal, ProposalReply,
)
from .geometry import LayoutBoundsError, resolve_layout
from .imaging import render_layout
from .models import MAX_JSON_BYTES, CollageError, InputLayout, ResolvedLayout
from .projects import ProjectStore, parse_json, read_json


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
        self.history()
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
            entry.proposal_id for entry in self.history()
            if isinstance(entry, Exchange) and entry.outcome == "proposal"
        }
        if proposal_id not in committed:
            raise CollageError("Unknown or unpublished proposal ID.")
        proposal = Proposal.model_validate(read_json(child(preview.parent, "proposal.json")))
        project = self.store.load(self.project_id)
        expected = resolve_layout(proposal.recipe, project.photos, 1)
        if (
            proposal.proposal_id != proposal_id
            or proposal.geometry != expected.geometry
            or proposal.recipe_digest != digest(canonical(proposal.recipe))
            or proposal.preview_digest != digest(preview.read_bytes())
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

    def context(self, prompt: str, feedback: str | None = None) -> dict[str, object]:
        self._fresh()
        project = self.store.load(self.project_id)
        baseline = self.baseline()
        history = []
        for event in self.history():
            if isinstance(event, LocalEvent) and event.kind == "rating":
                continue
            history.append(event.model_dump(mode="json"))
        return {
            "photos": [
                {"photo_id": p.photo_id, "width": p.width, "height": p.height,
                 "aspect_ratio": p.width / p.height} for p in project.photos
            ],
            "preferences": self.state.preferences.model_dump(),
            "trusted_controls": self.state.controls.model_dump(),
            "editing_baseline": baseline.model_dump(mode="json") if baseline else None,
            "baseline_geometry": (
                [g.model_dump(mode="json")
                 for g in resolve_layout(baseline, project.photos, 1).geometry]
                if baseline else None
            ),
            "history": history, "user_request": prompt, "validation_feedback": feedback,
        }

    async def request(
        self, prompt: str, client: ModelClient, requests: RequestLog | None = None,
    ) -> str:
        if not prompt.strip() or len(prompt.encode("utf-8")) > MAX_JSON_BYTES // 4:
            raise CollageError("Prompt must be nonempty and at most 256 KiB UTF-8.")
        requests = requests if requests is not None else RequestLog(self.store, self.project_id)
        if requests.root != child(self.root, "requests"):
            raise CollageError("Request accounting belongs to a different project.")
        feedback = None
        for correction in range(4):
            context = self.context(prompt, feedback)
            try:
                raw = await client.complete(context, requests, f"{self.project_id}: turn")
            except (CollageError, OSError) as exc:
                self._append(Exchange(
                    prompt=prompt, outcome="error", parent=self.state.baseline,
                    run_id=None, attempt=len(requests.attempts()) or None,
                    error=f"Request stopped: {type(exc).__name__}.",
                ))
                raise
            try:
                reply = REPLY.validate_python(parse_json(raw.encode("utf-8")))
                resolved = self._validate_recipe(reply.recipe) if isinstance(reply, ProposalReply) else None
            except (CollageError, ValidationError) as exc:
                if isinstance(exc, ValidationError):
                    errors = [
                        {"field": list(item["loc"]), "error": item["type"]}
                        for item in exc.errors(include_url=False, include_context=False, include_input=False)[:20]
                    ]
                    feedback = json.dumps(errors)[:8192]
                elif isinstance(exc, LayoutBoundsError):
                    feedback = json.dumps(exc.details)[:8192]
                else:
                    message = str(exc)
                    feedback = (
                        message[:2048] if message.startswith(
                            ("Photo ", "Recipe must", "Cropping is", "Each imported")
                        ) else "Invalid JSON response; return one object matching the response schema."
                    )
                self._append(Exchange(
                    prompt=prompt, response=(raw if len(raw.encode("utf-8")) <= MAX_JSON_BYTES // 2 else None),
                    outcome="invalid", parent=self.state.baseline,
                    run_id=None, attempt=len(requests.attempts()), error=feedback,
                ))
                if correction == 3:
                    raise CollageError(f"Model correction failed: {feedback}") from exc
                continue
            if not isinstance(reply, ProposalReply):
                self._append(Exchange(
                    prompt=prompt, response=raw, outcome="question", parent=self.state.baseline,
                    run_id=None, attempt=len(requests.attempts()),
                ))
                return reply.question
            assert resolved is not None
            try:
                return self._publish(prompt, raw, resolved, requests)
            except (CollageError, OSError) as exc:
                self._append(Exchange(
                    prompt=prompt,
                    response=raw if len(raw.encode("utf-8")) <= MAX_JSON_BYTES // 2 else None,
                    outcome="error", parent=self.state.baseline,
                    run_id=None, attempt=len(requests.attempts()),
                    error=f"Proposal publication stopped: {type(exc).__name__}.",
                ))
                raise
        raise AssertionError("Unreachable correction loop.")

    def _publish(
        self, prompt: str, raw: str, resolved: ResolvedLayout, requests: RequestLog,
    ) -> str:
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
                proposal_id=proposal_id, turn_id=event_id, parent=self.state.baseline,
                controls=self.state.controls, recipe=resolved.recipe, geometry=resolved.geometry,
                recipe_digest=digest(canonical(resolved.recipe)),
                preview_digest=digest(preview.read_bytes()),
            )
            save(staging / "proposal.json", proposal)
            staging.rename(child(proposals, proposal_id))
        self._append(Exchange(
            prompt=prompt, response=raw, outcome="proposal", parent=self.state.baseline,
            run_id=None, attempt=len(requests.attempts()), proposal_id=proposal_id,
        ), baseline=proposal_id)
        return proposal_id

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
