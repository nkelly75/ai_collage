"""Strict local conversation records, separate from format 3 recipes."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from ..engine.models import InputLayout, LayerGeometry, PositiveInt


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, allow_inf_nan=False)
    record_version: Literal[1] = 1


class Preferences(BaseModel):
    model_config = Record.model_config
    preferences_version: Literal[1]
    borders: Literal["prefer", "avoid", "agent_choice"]
    rounding: Literal["prefer", "avoid", "agent_choice"]
    tilt: Literal["prefer", "avoid", "agent_choice"]


class Controls(Record):
    width: Annotated[int, Field(ge=1, le=4096)]
    height: Annotated[int, Field(ge=1, le=4096)]
    cropping: bool = False


ProposalId = Annotated[str, Field(pattern=r"^P[0-9]{3,}$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Question = Annotated[str, Field(min_length=1, max_length=1000, pattern=r"\S")]


class PhotoReference(BaseModel):
    model_config = Record.model_config
    text: Annotated[str, Field(min_length=1, max_length=200)]
    photo_id: PositiveInt | None
    event_id: PositiveInt | None = None


class NameUpdate(BaseModel):
    model_config = Record.model_config
    name: Annotated[str, Field(min_length=1, max_length=200, pattern=r"\S")]
    photo_id: PositiveInt | None
    quote: Annotated[str, Field(min_length=1, max_length=1000, pattern=r"\S")]


class PhotoName(BaseModel):
    model_config = Record.model_config
    name: str
    photo_id: PositiveInt | None
    event_id: PositiveInt
    quote: str
    receipt_event: PositiveInt | None = None


class NavigationEvidence(BaseModel):
    model_config = Record.model_config
    kind: Literal["id", "ordinal", "undo", "before", "after"]
    text: Annotated[str, Field(min_length=1, max_length=1000)]
    task_id: PositiveInt | None = None
    field: str | None = None
    steps: PositiveInt | None = None

    @model_validator(mode="after")
    def matching_evidence(self) -> "NavigationEvidence":
        if self.kind in {"before", "after"}:
            valid = self.task_id is not None and bool(self.field) and self.steps is None
        elif self.kind == "undo":
            valid = self.steps is not None and self.task_id is None and self.field is None
        else:
            valid = self.task_id is None and self.field is None and self.steps is None
        if not valid:
            raise ValueError("Navigation fields must match the evidence kind.")
        return self


class ReturnConfirmation(BaseModel):
    model_config = Record.model_config
    proposal_id: ProposalId
    action: Literal["select", "edit"]
    evidence: NavigationEvidence


class GroundedIntent(BaseModel):
    model_config = Record.model_config
    references: list[PhotoReference]
    name_updates: list[NameUpdate]
    navigation: NavigationEvidence | None = None
    continues_task: bool = True


class EditIntent(GroundedIntent):
    action: Literal["edit"]
    source: Literal["current"] | ProposalId


class FreshIntent(GroundedIntent):
    action: Literal["fresh"]


class RetryIntent(GroundedIntent):
    action: Literal["retry"]
    proposal_id: ProposalId


class SelectIntent(GroundedIntent):
    action: Literal["select"]
    proposal_id: ProposalId


class QuestionIntent(GroundedIntent):
    action: Literal["question"]
    question: Question
    continuation: Literal["design", "naming"] = Field(
        default="design", description="Whether the originating task changes a layout or only teaches names.",
    )
    return_confirmation: ReturnConfirmation | None = None


class MemoryIntent(GroundedIntent):
    action: Literal["remember", "forget"]


class InspectNamesIntent(GroundedIntent):
    action: Literal["list_names"]

    @model_validator(mode="after")
    def read_only(self) -> "InspectNamesIntent":
        if self.references or self.name_updates or self.navigation:
            raise ValueError("Listing names is read-only and requires no bindings or updates.")
        return self


class NamesIntent(GroundedIntent):
    action: Literal["names"]
    decision: Literal["approve", "reject"]
    receipt_event: PositiveInt

    @model_validator(mode="after")
    def exact_receipt(self) -> "NamesIntent":
        if self.references or self.name_updates or self.navigation or not self.continues_task:
            raise ValueError("Naming approval/rejection uses the exact pending receipt, not new bindings.")
        return self


class ResumeIntent(GroundedIntent):
    action: Literal["resume"]

    @model_validator(mode="after")
    def unchanged_task(self) -> "ResumeIntent":
        if self.references or self.name_updates or self.navigation or not self.continues_task:
            raise ValueError("Resume reuses the timed-out task without new bindings or navigation.")
        return self


Intent = Annotated[
    EditIntent | FreshIntent | RetryIntent | SelectIntent | QuestionIntent | MemoryIntent | InspectNamesIntent | ResumeIntent | NamesIntent,
    Field(discriminator="action"),
]
INTENT = TypeAdapter(Intent)


class ConversationRecord(Record):
    record_version: Literal[8] = 8


class LayoutSource(BaseModel):
    model_config = Record.model_config
    proposal_id: ProposalId | None = None
    accepted_version: PositiveInt | None = None

    @model_validator(mode="after")
    def one_identity(self) -> "LayoutSource":
        if (self.proposal_id is None) == (self.accepted_version is None):
            raise ValueError("A source must identify exactly one proposal or accepted version.")
        return self


class ResolvedIntent(BaseModel):
    model_config = Record.model_config
    action: Literal["edit", "fresh", "retry", "select"]
    source: LayoutSource | None
    task_turn: PositiveInt
    task_request: Annotated[str, Field(min_length=1, pattern=r"\S")]
    reference: LayoutSource | None = None
    references: list[PhotoReference] = Field(default_factory=list)
    navigation: NavigationEvidence | None = None

    @model_validator(mode="after")
    def matching_action(self) -> "ResolvedIntent":
        if self.action in {"edit", "select"} and self.source is None:
            raise ValueError("Editing/selection requires a source.")
        if self.action == "fresh" and self.source is not None:
            raise ValueError("Fresh generation has no edit source.")
        if self.action == "retry" and (
            self.reference is None or self.reference.proposal_id is None
        ):
            raise ValueError("Retry requires a rejected proposal reference.")
        if self.action == "select" and (
            self.source is None or self.source.proposal_id is None or self.reference is not None
        ):
            raise ValueError("Selection requires exactly a published proposal.")
        return self


class NameReceipt(BaseModel):
    model_config = Record.model_config
    updates: Annotated[list[NameUpdate], Field(min_length=1)]
    intent: ResolvedIntent | None
    baseline: LayoutSource | None
    controls: Controls
    names_digest: Digest

    @model_validator(mode="after")
    def unique_labels(self) -> "NameReceipt":
        if len({" ".join(item.name.split()).casefold() for item in self.updates}) != len(self.updates):
            raise ValueError("Naming receipt repeats a label.")
        return self


class RequestResult(BaseModel):
    model_config = Record.model_config
    kind: Literal["proposal", "selection", "question", "name_confirmation", "acknowledgement"]
    event_id: PositiveInt
    proposal_id: ProposalId | None = None
    question: Question | None = None
    acknowledgement: str | None = None
    identity_question: bool = False

    @model_validator(mode="after")
    def matching_fields(self) -> "RequestResult":
        if self.kind in {"question", "name_confirmation"}:
            valid = self.question is not None and self.proposal_id is None and self.acknowledgement is None
        elif self.kind == "acknowledgement":
            valid = self.acknowledgement is not None and self.proposal_id is None and self.question is None
        else:
            valid = self.proposal_id is not None and self.question is None and self.acknowledgement is None
        if not valid:
            raise ValueError("Result fields do not match its kind.")
        return self


class ReceiptPointer(BaseModel):
    model_config = Record.model_config
    event_id: PositiveInt
    sha256: Digest


class ConversationState(ConversationRecord):
    project_id: str
    photo_digest: Digest
    expected_version: PositiveInt | None
    initial_version: PositiveInt | None
    preferences: Preferences
    controls: Controls
    baseline: ProposalId | None = None
    accepted_proposal: ProposalId | None = None
    history: list[PositiveInt] = Field(default_factory=list)
    photo_names: list[PhotoName] = Field(default_factory=list)
    pending_names: ReceiptPointer | None = None


class Proposal(ConversationRecord):
    proposal_id: ProposalId
    turn_id: PositiveInt
    parent: ProposalId | None
    intent: ResolvedIntent
    controls: Controls
    recipe: InputLayout
    geometry: list[LayerGeometry]
    recipe_digest: Digest
    preview_digest: Digest


class Exchange(ConversationRecord):
    kind: Literal["turn"] = "turn"
    prompt: str
    response: str | None = None
    outcome: Literal["intent", "proposal", "selection", "question", "name_confirmation", "acknowledgement", "inspection", "invalid", "error"]
    stage: Literal["interpretation", "generation"]
    intent: ResolvedIntent | None = None
    parent: ProposalId | None
    run_id: str | None
    attempt: int | None = None
    error: str | None = None
    proposal_id: ProposalId | None = None
    references: list[PhotoReference] = Field(default_factory=list)
    name_updates: list[PhotoName] = Field(default_factory=list)
    task_id: PositiveInt | None = None
    baseline_before: LayoutSource | None = None
    generation_timeout: bool = False
    name_receipt: NameReceipt | None = None
    receipt_event: PositiveInt | None = None

    @model_validator(mode="after")
    def timeout_evidence(self) -> "Exchange":
        if (self.outcome == "name_confirmation") != (self.name_receipt is not None):
            raise ValueError("A naming receipt belongs only to its confirmation event.")
        if self.generation_timeout and (
            self.stage != "generation" or self.outcome != "error" or self.intent is None
        ):
            raise ValueError("Generation timeout requires a failed generation with resolved intent.")
        return self


class LocalEvent(ConversationRecord):
    kind: Literal["controls", "rating", "accept"]
    controls: Controls | None = None
    proposal_id: ProposalId | None = None
    rating: Literal["worked", "partly", "failed"] | None = None
    note: str | None = None
    accepted_version: PositiveInt | None = None


class LocalSelection(ConversationRecord):
    kind: Literal["local_selection"] = "local_selection"
    proposal_id: ProposalId
    baseline_before: LayoutSource | None
    abandoned_task: PositiveInt | None


HISTORY = TypeAdapter(Exchange | LocalEvent | LocalSelection)


class AcceptanceIntent(ConversationRecord):
    proposal_id: ProposalId
    previous_version: PositiveInt | None
    next_version: PositiveInt


class Limits(Record):
    input_tokens: Annotated[int, Field(ge=1, le=50_000)] = 50_000
    output_tokens: Annotated[int, Field(ge=1, le=25_000)] = 25_000
    timeout_seconds: Annotated[int, Field(ge=1, le=120)] = 120
    generation_timeout_seconds: Annotated[int, Field(ge=1, le=180)] = 180


Reasoning = Literal["high", "low"]


class PreparedGeneration(BaseModel):
    """Internal, reconstructible handoff; not a browser-authorized intent."""

    model_config = Record.model_config
    handoff_version: Literal[1] = 1
    project_id: str
    photo_digest: Digest
    state_digest: Digest
    prompt: Annotated[str, Field(min_length=1, pattern=r"\S")]
    intent: ResolvedIntent
    request_start: PositiveInt
    active_task: PositiveInt
    independent_task: bool
    calls_used: Annotated[int, Field(ge=1, le=2)]
    limits: Limits
    generation_reasoning: Reasoning
    interpretation_reasoning: Reasoning

    @model_validator(mode="after")
    def generation_only(self) -> "PreparedGeneration":
        if self.intent.action == "select":
            raise ValueError("Exact selection finishes during interpretation.")
        return self


class Attempt(Record):
    record_version: Literal[2] = 2
    number: PositiveInt
    purpose: str
    input_bound: Annotated[int, Field(ge=0)]
    started: float
    status: Literal["pending", "complete", "incomplete", "error"] = "pending"
    duration: Annotated[float, Field(ge=0)] | None = None
    input_tokens: Annotated[int, Field(ge=0)] | None = None
    output_tokens: Annotated[int, Field(ge=0)] | None = None
    cached_tokens: Annotated[int, Field(ge=0)] | None = None
    reasoning_tokens: Annotated[int, Field(ge=0)] | None = None
    error: str | None = None
    stage: Literal["interpretation", "generation"] | None = None
    reasoning_effort: Reasoning | None = None
    timeout_seconds: Annotated[float, Field(gt=0, le=180)] | None = None
