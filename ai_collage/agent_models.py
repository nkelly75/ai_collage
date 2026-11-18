"""Strict local conversation records, separate from format 3 recipes."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

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


class ProposalReply(BaseModel):
    model_config = Record.model_config
    kind: Literal["proposal"]
    recipe: InputLayout


class QuestionReply(BaseModel):
    model_config = Record.model_config
    kind: Literal["question"]
    question: Annotated[str, Field(min_length=1, max_length=1000, pattern=r"\S")]


Reply = Annotated[ProposalReply | QuestionReply, Field(discriminator="kind")]
REPLY = TypeAdapter(Reply)
ProposalId = Annotated[str, Field(pattern=r"^P[0-9]{3,}$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class ConversationState(Record):
    project_id: str
    photo_digest: Digest
    expected_version: PositiveInt | None
    initial_version: PositiveInt | None
    preferences: Preferences
    controls: Controls
    baseline: ProposalId | None = None
    accepted_proposal: ProposalId | None = None
    history: list[PositiveInt] = Field(default_factory=list)


class Proposal(Record):
    proposal_id: ProposalId
    turn_id: PositiveInt
    parent: ProposalId | None
    controls: Controls
    recipe: InputLayout
    geometry: list[LayerGeometry]
    recipe_digest: Digest
    preview_digest: Digest


class Exchange(Record):
    kind: Literal["turn"] = "turn"
    prompt: str
    response: str | None = None
    outcome: Literal["proposal", "question", "invalid", "error"]
    parent: ProposalId | None
    run_id: str | None
    attempt: int | None = None
    error: str | None = None
    proposal_id: ProposalId | None = None


class LocalEvent(Record):
    kind: Literal["controls", "rating", "accept"]
    controls: Controls | None = None
    proposal_id: ProposalId | None = None
    rating: Literal["worked", "partly", "failed"] | None = None
    note: str | None = None
    accepted_version: PositiveInt | None = None


HISTORY = TypeAdapter(Exchange | LocalEvent)


class AcceptanceIntent(Record):
    proposal_id: ProposalId
    previous_version: PositiveInt | None
    next_version: PositiveInt


class Limits(Record):
    max_attempts: Annotated[int, Field(ge=1, le=50)] = 50
    input_tokens: Annotated[int, Field(ge=1, le=50_000)] = 50_000
    output_tokens: Annotated[int, Field(ge=1, le=25_000)] = 25_000
    timeout_seconds: Annotated[int, Field(ge=1, le=120)] = 120


class RunConfig(Record):
    run_id: str
    limits: Limits = Field(default_factory=Limits)
    halted: bool = False


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
