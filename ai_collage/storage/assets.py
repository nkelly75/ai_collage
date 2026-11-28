"""Bounded proposal images and their shared publication/commitment checks."""

import io
import os
from pathlib import Path

from PIL import Image

from ..agent.files import canonical, digest
from ..agent.models import (
    HISTORY, MAX_THUMBNAIL_BYTES, ConversationState, Exchange, Proposal, Thumbnail,
    thumbnail_dimensions,
)
from ..engine.models import CollageError
from .contracts import MAX_PREVIEW_BYTES, ConversationStorage, ProposalNotFound


def read_image(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        size = os.fstat(stream.fileno()).st_size
        if not 0 < size <= limit:
            raise CollageError("Saved image is empty or exceeds its byte limit.")
        raw = stream.read(size + 1)
    if len(raw) != size:
        raise CollageError("Saved image changed during its bounded read.")
    return raw


def read_preview(path: Path) -> bytes:
    return read_image(path, MAX_PREVIEW_BYTES)


def validate_png(raw: bytes, size: tuple[int, int], sha256: str, limit: int) -> None:
    if not 0 < len(raw) <= limit or digest(raw) != sha256:
        raise CollageError("Saved image size/digest identity mismatch.")
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format != "PNG" or image.size != size or getattr(image, "n_frames", 1) != 1:
                raise CollageError("Saved image format/dimensions mismatch.")
            image.verify()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise CollageError("Saved image is not a valid PNG.") from exc


def validate_preview(proposal: Proposal, raw: bytes) -> None:
    validate_png(
        raw, (proposal.recipe.canvas.width, proposal.recipe.canvas.height),
        proposal.preview_digest, MAX_PREVIEW_BYTES,
    )


def validate_thumbnail(proposal: Proposal, raw: bytes) -> None:
    thumbnail = proposal.thumbnail
    if len(raw) != thumbnail.size:
        raise CollageError("Saved thumbnail size mismatch.")
    validate_png(raw, (thumbnail.width, thumbnail.height), thumbnail.sha256, MAX_THUMBNAIL_BYTES)


def create_thumbnail(preview: Path) -> tuple[Thumbnail, bytes]:
    raw = read_preview(preview)
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if (
                image.format != "PNG" or getattr(image, "n_frames", 1) != 1
                or not all(1 <= axis <= 4096 for axis in image.size)
            ):
                raise CollageError("Thumbnail requires a supported rendered PNG.")
            size = thumbnail_dimensions(*image.size)
            with image.convert("RGBA") as source:
                with source.resize(size, Image.Resampling.LANCZOS) as small:
                    output = io.BytesIO()
                    small.save(output, format="PNG")
                    thumbnail_raw = output.getvalue()
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        raise CollageError("Could not create the proposal thumbnail.") from exc
    thumbnail = Thumbnail(
        width=size[0], height=size[1], size=len(thumbnail_raw), sha256=digest(thumbnail_raw),
        source_preview_digest=digest(raw),
    )
    validate_png(thumbnail_raw, size, thumbnail.sha256, MAX_THUMBNAIL_BYTES)
    return thumbnail, thumbnail_raw


def committed_proposal(records: ConversationStorage, proposal_id: str) -> Proposal:
    raw = records.read("proposal", proposal_id)
    if raw is None:
        raise ProposalNotFound("Unknown or unpublished proposal ID.")
    proposal = Proposal.model_validate(raw)
    state = ConversationState.model_validate(records.read("state", "state"))
    if state.project_id != records.project_id:
        raise CollageError("Conversation project identity mismatch.")
    if proposal.turn_id not in state.history:
        raise ProposalNotFound("Unknown or unpublished proposal ID.")
    event = HISTORY.validate_python(records.read("event", f"{proposal.turn_id:06d}"))
    if (
        proposal.proposal_id != proposal_id
        or not isinstance(event, Exchange) or event.outcome != "proposal"
        or event.proposal_id != proposal_id or event.intent != proposal.intent
        or event.parent != proposal.parent
        or proposal.parent != (proposal.intent.source.proposal_id if proposal.intent.source else None)
        or proposal.recipe_digest != digest(canonical(proposal.recipe))
        or (proposal.controls.width, proposal.controls.height) != (
            proposal.recipe.canvas.width, proposal.recipe.canvas.height,
        )
    ):
        raise CollageError("Committed proposal identity mismatch.")
    records.validate_assets(proposal)
    return proposal
