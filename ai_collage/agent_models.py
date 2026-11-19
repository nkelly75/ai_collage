"""Strict local conversation records, separate from format 3 recipes."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from .models import InputLayout, LayerGeometry, PositiveInt


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


class EditIntent(BaseModel):
    model_config = Record.model_config
    action: Literal["edit"]
    source: Literal["current"] | ProposalId


class FreshIntent(BaseModel):
    model_config = Record.model_config
    action: Literal["fresh"]


class RetryIntent(BaseModel):
    model_config = Record.model_config
    action: Literal["retry"]
    proposal_id: ProposalId


class SelectIntent(BaseModel):
    model_config = Record.model_config
    action: Literal["select"]
    proposal_id: ProposalId


class QuestionIntent(BaseModel):
    model_config = Record.model_config
    action: Literal["question"]
    question: Question


Intent = Annotated[
    EditIntent | FreshIntent | RetryIntent | SelectIntent | QuestionIntent,
    Field(discriminator="action"),
]
INTENT = TypeAdapter(Intent)


class ConversationRecord(Record):
    record_version: Literal[2] = 2


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


class RequestResult(BaseModel):
    model_config = Record.model_config
    kind: Literal["proposal", "selection", "question"]
    event_id: PositiveInt
    proposal_id: ProposalId | None = None
    question: Question | None = None

    @model_validator(mode="after")
    def matching_fields(self) -> "RequestResult":
        if self.kind == "question":
            valid = self.question is not None and self.proposal_id is None
        else:
            valid = self.proposal_id is not None and self.question is None
        if not valid:
            raise ValueError("Result fields do not match its kind.")
        return self


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
    outcome: Literal["intent", "proposal", "selection", "question", "invalid", "error"]
    stage: Literal["interpretation", "generation"]
    intent: ResolvedIntent | None = None
    parent: ProposalId | None
    run_id: str | None
    attempt: int | None = None
    error: str | None = None
    proposal_id: ProposalId | None = None


class LocalEvent(ConversationRecord):
    kind: Literal["controls", "rating", "accept"]
    controls: Controls | None = None
    proposal_id: ProposalId | None = None
    rating: Literal["worked", "partly", "failed"] | None = None
    note: str | None = None
    accepted_version: PositiveInt | None = None


HISTORY = TypeAdapter(Exchange | LocalEvent)


class AcceptanceIntent(ConversationRecord):
    proposal_id: ProposalId
    previous_version: PositiveInt | None
    next_version: PositiveInt


class Limits(Record):
    input_tokens: Annotated[int, Field(ge=1, le=50_000)] = 50_000
    output_tokens: Annotated[int, Field(ge=1, le=25_000)] = 25_000
    timeout_seconds: Annotated[int, Field(ge=1, le=120)] = 120


class Attempt(Record):
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
