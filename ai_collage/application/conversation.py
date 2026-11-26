"""Durable local HTTP operations over the shared conversation stages."""

from __future__ import annotations

from contextlib import nullcontext
import logging
import os
from pathlib import Path
from time import monotonic
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from ..agent.conversation import Conversation, ModelClient, RequestRejected
from ..agent.files import canonical, child, digest, save
from ..agent.models import (
    INTENT, Digest, Exchange, LocalSelection, PreparedGeneration, ProposalId, QuestionIntent, Record,
    RequestResult,
)
from ..agent.photo_references import receipt_question
from ..agent.requests import RequestLog, StageTimeout, WorkTimeout, call_budget
from ..engine.models import MAX_JSON_BYTES, CollageError, validate_project_id
from ..engine.projects import ProjectStore, read_json
from .projects import FlowError, ProjectFlow, project_guard, project_is_busy


RequestId = Annotated[str, Field(pattern=r"^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$")]
Status = Literal["interpreting", "prepared", "generating", "completed", "failed", "uncertain", "abandoned"]
UNRESOLVED = {"interpreting", "prepared", "generating", "uncertain"}


class Submission(BaseModel):
    model_config = Record.model_config
    request_id: RequestId
    prompt: str
    revision: Digest

    @field_validator("request_id")
    @classmethod
    def valid_uuid(cls, value: str) -> str:
        if str(UUID(value)) != value:
            raise ValueError("Use a canonical UUID request ID.")
        return value

    @field_validator("prompt")
    @classmethod
    def bounded_prompt(cls, value: str) -> str:
        if not value.strip() or len(value.encode("utf-8")) > MAX_JSON_BYTES // 4:
            raise ValueError("Prompt must be nonempty and at most 256 KiB UTF-8.")
        return value


class GenerationRequest(BaseModel):
    model_config = Record.model_config
    revision: Digest


class SafeError(Record):
    code: str
    message: str


class SelectionSubmission(BaseModel):
    model_config = Record.model_config
    action_id: RequestId
    proposal_id: ProposalId
    revision: Digest
    abandon_pending: bool

    @field_validator("action_id")
    @classmethod
    def valid_uuid(cls, value: str) -> str:
        return Submission.valid_uuid(value)


class SelectionAction(Record):
    project_id: str
    submission: SelectionSubmission
    event_id: Annotated[int, Field(ge=1)]
    abandoned_request: RequestId | None
    status: Literal["claimed", "completed"]


class Operation(Record):
    project_id: str
    sequence: Annotated[int, Field(ge=1)]
    submission: Submission
    request_start: Annotated[int, Field(ge=1)]
    status: Status
    summary: str = ""
    prepared: PreparedGeneration | None = None
    result: RequestResult | None = None
    error: SafeError | None = None

    @model_validator(mode="after")
    def consistent(self) -> Operation:
        if (self.status == "completed") != (self.result is not None):
            raise ValueError("Only completed operations have a result.")
        if (self.status in {"failed", "uncertain"}) != (self.error is not None):
            raise ValueError("Failure states require a diagnostic.")
        if self.status in {"prepared", "generating"} and self.prepared is None:
            raise ValueError("Generation requires the saved handoff.")
        if self.prepared is not None and (
            self.prepared.project_id != self.project_id
            or self.prepared.prompt != self.submission.prompt
            or self.prepared.request_start != self.request_start
        ):
            raise ValueError("Operation handoff identity mismatch.")
        return self


class ConversationSettings:
    def __init__(
        self, *, live: bool = False, budget_path: Path | None = None,
        max_calls: int | None = None, trial_project: str | None = None,
    ):
        self.live = live
        self.budget_path = budget_path
        self.max_calls = max_calls
        self.trial_project = trial_project
        supplied = (budget_path is not None, max_calls is not None, trial_project is not None)
        if any(supplied) and not all(supplied):
            raise FlowError("configuration_error", "Supply the trial project, absolute budget path and call limit together.", 500)
        if all(supplied):
            assert budget_path is not None and max_calls is not None and trial_project is not None
            if not budget_path.is_absolute() or max_calls < 1:
                raise FlowError("configuration_error", "Invalid trial call-budget configuration.", 500)
            validate_project_id(trial_project)

    @classmethod
    def configured(cls) -> ConversationSettings:
        live = os.environ.get("AI_COLLAGE_LIVE")
        count = os.environ.get("AI_COLLAGE_MAX_CALLS")
        path = os.environ.get("AI_COLLAGE_CALL_BUDGET_PATH")
        if live not in {None, "0", "1"} or count is not None and not count.isdecimal():
            raise FlowError("configuration_error", "Invalid local conversation configuration.", 500)
        return cls(
            live=live == "1", budget_path=Path(path) if path else None,
            max_calls=int(count) if count else None,
            trial_project=os.environ.get("AI_COLLAGE_TRIAL_PROJECT"),
        )

    def require_live(self, project_id: str) -> None:
        if not self.live:
            raise FlowError("live_disabled", "Model requests are disabled. Start the local API with -Live.", 503)
        if self.trial_project is not None and project_id != self.trial_project:
            raise FlowError("trial_project_only", "This host permits model requests only for its configured trial project.", 403)

    def budget(self):
        if self.budget_path is None:
            return nullcontext()
        assert self.max_calls is not None
        return call_budget(self.budget_path, self.max_calls)


def result_message(result: RequestResult) -> str:
    if result.question is not None:
        return result.question
    if result.acknowledgement is not None:
        return result.acknowledgement
    return f"{'Created' if result.kind == 'proposal' else 'Returned to'} {result.proposal_id}."


def intent_summary(prepared: PreparedGeneration) -> str:
    intent = prepared.intent
    source = intent.source
    label = source.proposal_id or f"accepted version {source.accepted_version}" if source else "none"
    photos = sorted({item.photo_id for item in intent.references if item.photo_id is not None})
    targets = ", ".join(str(photo) for photo in photos) if photos else "as requested"
    return f"{intent.action.capitalize()}; source: {label}; photo references: {targets}."


class ConversationFlow:
    def __init__(
        self, store: ProjectStore, settings: ConversationSettings | None = None,
        client: ModelClient | None = None,
    ):
        self.store = store
        self.settings = settings if settings is not None else ConversationSettings.configured()
        self.client = client

    def _directory(self, project_id: str) -> Path:
        return child(self.store.project_dir(project_id), "web-operations")

    def _path(self, project_id: str, request_id: str) -> Path:
        Submission.valid_uuid(request_id)
        return child(self._directory(project_id), f"{request_id}.json")

    def _selection_path(self, project_id: str, action_id: str) -> Path:
        Submission.valid_uuid(action_id)
        return child(self.store.project_dir(project_id), "web-selections", f"{action_id}.json")

    def _selections(self, project_id: str) -> list[SelectionAction]:
        directory = child(self.store.project_dir(project_id), "web-selections")
        actions = []
        for path in directory.glob("*.json"):
            action = SelectionAction.model_validate(read_json(child(directory, path.name)))
            if action.project_id != project_id or path.name != f"{action.submission.action_id}.json":
                raise CollageError("Local selection identity mismatch.")
            actions.append(action)
        actions.sort(key=lambda action: action.event_id)
        if len({action.event_id for action in actions}) != len(actions):
            raise CollageError("Local selections have duplicate event identities.")
        return actions

    def _save_selection(self, action: SelectionAction) -> None:
        save(self._selection_path(action.project_id, action.submission.action_id), action)

    @staticmethod
    def _validate_selection(conversation: Conversation, operations: list[Operation], action: SelectionAction) -> None:
        events = dict(zip(conversation.state.history, conversation.history(), strict=True))
        event = events.get(action.event_id)
        if not isinstance(event, LocalSelection) or event.proposal_id != action.submission.proposal_id:
            raise CollageError("Local selection does not match its canonical event.")
        if event.abandoned_task is not None and not action.submission.abandon_pending:
            raise CollageError("Local selection abandoned work without confirmation.")
        if action.abandoned_request is not None:
            operation = next((op for op in operations
                              if op.submission.request_id == action.abandoned_request), None)
            if operation is None or operation.status != "abandoned" or operation.prepared is None:
                raise CollageError("Selected source conflicts with preparation retirement.")
            if event.abandoned_task != operation.prepared.active_task:
                raise CollageError("Selection retired a different logical task.")

    def _operations(self, project_id: str) -> list[Operation]:
        operations = []
        for path in self._directory(project_id).glob("*.json"):
            operation = Operation.model_validate(read_json(child(path.parent, path.name)))
            if operation.project_id != project_id or path.name != f"{operation.submission.request_id}.json":
                raise CollageError("Web operation identity mismatch.")
            operations.append(operation)
        operations.sort(key=lambda operation: operation.sequence)
        if [op.sequence for op in operations] != list(range(1, len(operations) + 1)):
            raise CollageError("Web operation sequence is inconsistent.")
        if any(op.status in UNRESOLVED for op in operations[:-1]):
            raise CollageError("A new operation followed unresolved work.")
        return operations

    def _save(self, operation: Operation) -> None:
        save(self._path(operation.project_id, operation.submission.request_id), operation)

    def _conversation(self, project_id: str) -> Conversation:
        ProjectFlow(self.store)._load(project_id)
        return Conversation(self.store, project_id, read_only=True)

    def _snapshot(self, project_id: str) -> tuple[Conversation, list[Operation], list[SelectionAction], str]:
        for _ in range(3):
            try:
                conversation = self._conversation(project_id)
                operations = self._operations(project_id)
                actions = self._selections(project_id)
                for action in actions:
                    if action.status == "completed":
                        self._validate_selection(conversation, operations, action)
                for operation in operations:
                    if operation.status == "abandoned" and not any(
                        action.abandoned_request == operation.submission.request_id for action in actions
                    ):
                        raise CollageError("Abandoned preparation has no selection claim.")
                core = self._core_bytes(conversation)
                op_bytes = b"".join(canonical(op) for op in operations) + b"".join(canonical(a) for a in actions)
                if (
                    core == self._core_bytes(conversation)
                    and op_bytes == (
                        b"".join(canonical(op) for op in self._operations(project_id))
                        + b"".join(canonical(a) for a in self._selections(project_id))
                    )
                ):
                    conversation._fresh()
                    return conversation, operations, actions, digest(core + op_bytes)
            except (CollageError, ValidationError, FileNotFoundError) as exc:
                logging.info("Conversation snapshot unavailable: %s", type(exc).__name__)
        raise FlowError("invalid_conversation_state", "Saved conversation is changing or invalid; check its preserved state.", 409)

    def _core_bytes(self, conversation: Conversation) -> bytes:
        history = conversation.history()
        return (
            canonical(self.store.load(conversation.project_id)) + canonical(conversation.state)
            + b"".join(canonical(event) for event in history)
            + b"".join(canonical(conversation.proposal(event.proposal_id))
                       for event in history
                       if isinstance(event, Exchange) and event.outcome == "proposal")
        )

    @staticmethod
    def _validate_result(conversation: Conversation, operation: Operation) -> None:
        result = operation.result
        if result is None:
            return
        events = dict(zip(conversation.state.history, conversation.history(), strict=True))
        event = events.get(result.event_id)
        expected = {"acknowledgement", "inspection"} if result.kind == "acknowledgement" else {result.kind}
        if (
            not isinstance(event, Exchange) or event.outcome not in expected
            or result.event_id < operation.request_start
            or event.prompt != operation.submission.prompt
            or event.proposal_id != result.proposal_id
        ):
            raise FlowError("invalid_operation_state", "Saved operation result conflicts with conversation history.", 409)
        if result.proposal_id is not None:
            conversation.proposal(result.proposal_id)

    def _operation_view(self, operation: Operation, revision: str, *, owns_guard: bool = False) -> dict:
        status = operation.status
        error = operation.error
        if status in {"interpreting", "generating"} and (
            owns_guard or not project_is_busy(self.store, operation.project_id)
        ):
            status = "uncertain"
            error = SafeError(code="outcome_unknown", message="Execution was interrupted. Outcome unknown; inspect saved state before another paid request.")
        return {
            "request_id": operation.submission.request_id, "status": status,
            "summary": operation.summary,
            "result_kind": operation.result.kind if operation.result else None,
            "message": result_message(operation.result) if operation.result else
                "Request abandoned before generation. No generation was started."
                if status == "abandoned" else None,
            "proposal_id": operation.result.proposal_id if operation.result else None,
            "error": {"code": error.code, "message": error.message} if error else None,
            "can_continue": status == "prepared", "revision": revision,
        }

    def detail(self, project_id: str) -> dict:
        conversation, operations, actions, revision = self._snapshot(project_id)
        ordered = []
        for operation in operations:
            self._validate_result(conversation, operation)
            identity = operation.submission.request_id
            ordered.append((operation.request_start, 0, {
                "id": f"{identity}:user", "role": "user", "text": operation.submission.prompt,
                "kind": "prompt", "proposal_id": None,
            }))
            if operation.result is not None or operation.error is not None or operation.status == "abandoned":
                ordered.append((operation.result.event_id if operation.result else operation.request_start, 1, {
                    "id": f"{identity}:assistant", "role": "assistant",
                    "text": result_message(operation.result) if operation.result else
                        operation.error.message if operation.error else
                        "Request abandoned before generation. No generation was started.",
                    "kind": operation.result.kind if operation.result else operation.status,
                    "proposal_id": operation.result.proposal_id if operation.result else None,
                }))
        for action in actions:
            if action.status == "completed":
                ordered.append((action.event_id, 2, {
                    "id": f"{action.submission.action_id}:activity", "role": "activity",
                    "text": f"You chose collage {action.submission.proposal_id} as the starting point for further edits.",
                    "kind": "local_selection", "proposal_id": action.submission.proposal_id,
                }))
        messages = [item for _, _, item in sorted(ordered, key=lambda item: item[:2])]
        pending = None
        receipt = conversation._pending_names()
        question = conversation._pending_question()
        if receipt is not None:
            pending = {"kind": "name_confirmation", "message": receipt_question(
                receipt[1].name_receipt, conversation.state.photo_names,
            )}
        elif question is not None:
            intent = INTENT.validate_json(question[1].response or "")
            if not isinstance(intent, QuestionIntent):
                raise FlowError("invalid_conversation_state", "Saved question is invalid.", 409)
            pending = {"kind": "question", "message": intent.question}
        return {
            "project_id": project_id, "revision": revision,
            "live_enabled": self.settings.live and self.settings.trial_project in {None, project_id},
            "messages": messages,
            "baseline": {"proposal_id": conversation.state.baseline} if conversation.state.baseline else None,
            "pending": pending,
            "operation": self._operation_view(operations[-1], revision)
            if operations and operations[-1].status in UNRESOLVED else None,
            "proposals": [
                {"proposal_id": event.proposal_id,
                 "width": conversation.proposal(event.proposal_id).recipe.canvas.width,
                 "height": conversation.proposal(event.proposal_id).recipe.canvas.height}
                for event in conversation.history()
                if isinstance(event, Exchange) and event.outcome == "proposal"
            ],
            "selection": self._selection_eligibility(conversation, operations, actions, revision),
        }

    def _selection_eligibility(
        self, conversation: Conversation, operations: list[Operation],
        actions: list[SelectionAction], revision: str,
    ) -> dict:
        unresolved = next((action for action in actions if action.status != "completed"), None)
        operation = operations[-1] if operations else None
        reason = ""
        if unresolved is not None:
            reason = "A collage selection is unresolved. Check its saved status; do not repeat it."
        elif project_is_busy(self.store, conversation.project_id):
            reason = "Another project change is in progress."
        elif operation and operation.status in UNRESOLVED and operation.status != "prepared":
            reason = "An existing request is running or uncertain. Check saved status first."
        confirmation = None
        if conversation.state.pending_names:
            confirmation = "This ends the pending name confirmation and associated edit without applying the proposed names. Already learned names stay saved."
        elif conversation._pending_question():
            confirmation = "This ends the unanswered request. Your history and learned names stay saved."
        elif operation and operation.status == "prepared":
            confirmation = "This abandons the prepared request before generation. Already learned names and consumed model attempts stay recorded."
        elif conversation.selection_task() is not None:
            confirmation = "This ends the unfinished request. Your history and learned names stay saved."
        return {
            "enabled": not reason, "reason": reason, "confirmation": confirmation,
            "action": self._selection_view(unresolved, revision) if unresolved else None,
        }

    def _selection_view(self, action: SelectionAction, revision: str | None) -> dict:
        status = "completed" if action.status == "completed" else (
            "saving" if project_is_busy(self.store, action.project_id) else "uncertain"
        )
        return {
            "action_id": action.submission.action_id, "proposal_id": action.submission.proposal_id,
            "status": status, "revision": revision,
            "message": "Collage selection saved." if status == "completed" else
                "Collage selection is not confirmed. Inspect saved status; do not repeat the action.",
        }

    def selection(self, project_id: str, action_id: str) -> dict:
        path = self._selection_path(project_id, action_id)
        if not path.exists():
            raise FlowError("not_found", "Collage selection not found.", 404)
        action = SelectionAction.model_validate(read_json(path))
        if action.project_id != project_id or action.submission.action_id != action_id:
            raise CollageError("Local selection identity mismatch.")
        if action.status != "completed":
            return self._selection_view(action, None)
        conversation, operations, _, revision = self._snapshot(project_id)
        self._validate_selection(conversation, operations, action)
        return self._selection_view(action, revision)

    def select(self, project_id: str, submission: SelectionSubmission) -> tuple[dict, bool]:
        with project_guard(self.store, project_id):
            actions = self._selections(project_id)
            existing = next((a for a in actions if a.submission.action_id == submission.action_id), None)
            if existing is not None:
                if existing.submission != submission:
                    raise FlowError("action_id_conflict", "That action ID already has a different selection.", 409)
                return self.selection(project_id, submission.action_id), False
            if any(action.status != "completed" for action in actions):
                raise FlowError("selection_unresolved", "Check the unresolved collage selection before another change.", 409)
            conversation, operations, _, revision = self._snapshot(project_id)
            if submission.revision != revision:
                raise FlowError("stale_revision", "Conversation changed; refresh before choosing a collage.", 409)
            conversation.proposal(submission.proposal_id)
            operation = operations[-1] if operations else None
            if operation and operation.status in UNRESOLVED and operation.status != "prepared":
                raise FlowError("operation_unresolved", "An existing request is running or uncertain; selection is blocked.", 409)
            pending = conversation.selection_task()
            prepared = operation if operation and operation.status == "prepared" else None
            if (pending is not None or prepared) and not submission.abandon_pending:
                raise FlowError("confirmation_required", "Confirm ending the pending request before choosing a collage.", 409)
            if prepared and (
                prepared.prepared.state_digest != conversation._generation_digest(prepared.prepared.intent)
                or prepared.prepared.active_task != pending
            ):
                raise FlowError("stale_preparation", "Prepared work conflicts with saved state; inspect it before changing source.", 409)
            if submission.proposal_id == conversation.state.baseline and pending is None and prepared is None:
                raise FlowError("already_current", "This collage is already current.", 409)
            action = SelectionAction(
                project_id=project_id, submission=submission, event_id=conversation._next_event(),
                abandoned_request=prepared.submission.request_id if prepared else None, status="claimed",
            )
            self._save_selection(action)
            if prepared:
                self._save(prepared.model_copy(update={"status": "abandoned"}))
            event_id = conversation.select_proposal(submission.proposal_id, abandon_pending=submission.abandon_pending)
            if event_id != action.event_id:
                raise CollageError("Collage selection event identity changed during publication.")
            action = action.model_copy(update={"status": "completed"})
            self._validate_selection(conversation, self._operations(project_id), action)
            self._save_selection(action)
            return self.selection(project_id, submission.action_id), True

    def operation(self, project_id: str, request_id: str) -> dict:
        self._path(project_id, request_id)
        conversation, operations, _, revision = self._snapshot(project_id)
        for operation in operations:
            if operation.submission.request_id == request_id:
                self._validate_result(conversation, operation)
                return self._operation_view(operation, revision)
        raise FlowError("not_found", "Conversation request not found.", 404)

    def preview(self, project_id: str, proposal_id: str) -> bytes:
        conversation, _, _, _ = self._snapshot(project_id)
        proposal = conversation.proposal(proposal_id)
        raw = conversation.preview_path(proposal_id).read_bytes()
        if digest(raw) != proposal.preview_digest:
            raise FlowError("invalid_preview", "Published preview changed; no image was returned.", 409)
        return raw

    async def interpret(self, project_id: str, submission: Submission) -> tuple[dict, bool]:
        with project_guard(self.store, project_id):
            if any(action.status != "completed" for action in self._selections(project_id)):
                raise FlowError("selection_unresolved", "Check the unresolved collage selection before another Send.", 409)
            conversation, operations, _, revision = self._snapshot(project_id)
            for existing in operations:
                if existing.submission.request_id == submission.request_id:
                    if existing.submission != submission:
                        raise FlowError("request_id_conflict", "That request ID already has a different submission.", 409)
                    return self._operation_view(existing, revision, owns_guard=True), False
            if operations and operations[-1].status in UNRESOLVED:
                raise FlowError("operation_unresolved", "Check the existing operation before another Send.", 409)
            if submission.revision != revision:
                raise FlowError("stale_revision", "Conversation changed; reload before sending.", 409)
            self.settings.require_live(project_id)
            operation = Operation(
                project_id=project_id, sequence=len(operations) + 1, submission=submission,
                request_start=conversation._next_event(), status="interpreting",
            )
            with self.settings.budget():
                self._save(operation)
                await self._execute(conversation, operation)
            return self.operation(project_id, submission.request_id), True

    async def generate(self, project_id: str, request_id: str, request: GenerationRequest) -> dict:
        self._path(project_id, request_id)
        with project_guard(self.store, project_id):
            if any(action.status != "completed" for action in self._selections(project_id)):
                raise FlowError("selection_unresolved", "Check the unresolved collage selection before generation.", 409)
            conversation, operations, _, revision = self._snapshot(project_id)
            operation = next((op for op in operations if op.submission.request_id == request_id), None)
            if operation is None:
                raise FlowError("not_found", "Conversation request not found.", 404)
            if operation.status != "prepared":
                return self._operation_view(operation, revision, owns_guard=True)
            if revision != request.revision:
                raise FlowError("stale_revision", "Conversation changed; check the saved operation.", 409)
            self.settings.require_live(project_id)
            assert operation.prepared is not None
            if operation.prepared.state_digest != conversation._generation_digest(operation.prepared.intent):
                raise FlowError("stale_preparation", "Prepared generation has stale state/source; inspect saved state.", 409)
            with self.settings.budget():
                operation = operation.model_copy(update={"status": "generating"})
                self._save(operation)
                await self._execute(conversation, operation)
            return self.operation(project_id, request_id)

    async def _execute(self, conversation: Conversation, operation: Operation) -> None:
        from ..agent.provider import FoundryModel

        log = RequestLog(self.store, operation.project_id)
        if operation.prepared is not None:
            log.limits = operation.prepared.limits
            log.generation_reasoning = operation.prepared.generation_reasoning
            log.interpretation_reasoning = operation.prepared.interpretation_reasoning
        log.work_deadline = monotonic() + (210 if operation.status == "generating" else 150)
        baseline_before = conversation.state.baseline
        try:
            if operation.prepared is None:
                result = await conversation.interpret(operation.submission.prompt, self.client or FoundryModel(), log)
            else:
                result = await conversation.generate(operation.prepared, self.client or FoundryModel(), log)
        except (CollageError, OSError, ValidationError) as exc:
            known = isinstance(exc, (StageTimeout, WorkTimeout, RequestRejected))
            try:
                current = self._conversation(operation.project_id)
                events = current.history()
                last = events[-1] if events else None
                known = current.state.baseline == baseline_before and (known or (
                    isinstance(exc, CollageError) and isinstance(last, Exchange)
                    and last.outcome == "error" and last.stage == (
                        "generation" if operation.prepared else "interpretation"
                    ) and not (last.error or "").startswith("Proposal publication stopped")
                    and current.state.history[-1] >= operation.request_start
                ))
            except (CollageError, OSError, ValidationError, FlowError):
                known = False
            timeout = isinstance(exc, (StageTimeout, WorkTimeout))
            code = "stage_timeout" if timeout and known else "stage_failed" if known else "outcome_unknown"
            message = (
                "Stage timed out; no automatic retry. Saved names may already have changed. Any retry is a new paid request."
                if timeout and known else
                "Couldn't create a valid layout within the attempt limit. Your previous preview is unchanged. "
                "No automatic retry. Saved names may already have changed."
                if known and operation.prepared is not None and isinstance(exc, RequestRejected) else
                "Stage failed; no automatic retry. Saved names may already have changed. Review before explicitly trying again."
                if known else
                "Outcome unknown. Publication or storage may be incomplete; inspect preserved state before another paid request."
            )
            logging.warning("Conversation operation %s stopped (%s, known=%s)",
                            operation.submission.request_id, type(exc).__name__, known, exc_info=not known)
            self._save(operation.model_copy(update={
                "status": "failed" if known else "uncertain", "error": SafeError(code=code, message=message),
            }))
            raise FlowError(code, message, 504 if timeout else 422 if known else 500) from exc
        if isinstance(result, PreparedGeneration):
            operation = operation.model_copy(update={
                "status": "prepared", "prepared": result, "summary": intent_summary(result),
            })
        else:
            operation = operation.model_copy(update={"status": "completed", "result": result})
        self._save(operation)
