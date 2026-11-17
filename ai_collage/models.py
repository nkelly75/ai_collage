"""Strict input and persisted-state contracts for the offline engine."""

import re
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_CANVAS_AXIS = 4096
OWNER_ID = "local-dev"

PositiveInt = Annotated[int, Field(strict=True, gt=0)]
SchemaVersion = Annotated[int, Field(strict=True, ge=1, le=1)]
Coordinate = Annotated[float, Field(strict=True, ge=0, le=1)]
Width = Annotated[float, Field(strict=True, gt=0, le=1)]
ProjectId = Annotated[
    str, Field(strict=True, pattern=r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
]
HexColor = Annotated[str, Field(strict=True, pattern=r"^#[0-9a-fA-F]{6}$")]


class CollageError(Exception):
    """An invalid input or inconsistent local project."""


def validate_project_id(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", value):
        raise CollageError(
            "Project ID must be 1-64 lowercase letters, digits, or hyphens, "
            "starting and ending with a letter or digit."
        )
    if value in {"con", "prn", "aux", "nul"} or re.fullmatch(r"(com|lpt)[1-9]", value):
        raise CollageError("Project ID cannot be a reserved Windows device name.")
    return value


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class Background(Model):
    type: Literal["color"]
    value: HexColor


class Border(Model):
    width_px: Annotated[int, Field(strict=True, ge=0)]
    color: HexColor


class Canvas(Model):
    width: Annotated[int, Field(strict=True, ge=1, le=MAX_CANVAS_AXIS)]
    height: Annotated[int, Field(strict=True, ge=1, le=MAX_CANVAS_AXIS)]
    background: Background


class Box(Model):
    x: Coordinate
    y: Coordinate
    width: Width
    height: Width | None = None


class Framing(Model):
    mode: Literal["cover"]
    zoom: Annotated[float, Field(strict=True, ge=1, le=4)] = 1.0
    pan_x: Coordinate = 0.5
    pan_y: Coordinate = 0.5


class Element(Model):
    id: PositiveInt
    type: Literal["image"]
    source_image_id: PositiveInt
    box_normalized: Box
    z_index: Annotated[int, Field(strict=True)]
    border: Border | None = None
    framing: Framing | None = None
    corner_radius_px: Annotated[int, Field(strict=True, ge=0)] = 0
    rotation_degrees: Annotated[float, Field(strict=True, ge=-10, le=10)] = 0.0


class InputLayout(Model):
    schema_version: SchemaVersion
    canvas: Canvas
    elements: Annotated[list[Element], Field(min_length=2, max_length=6)]

    @model_validator(mode="after")
    def check_frame_mode(self) -> Self:
        for element in self.elements:
            if element.framing is None and "height" in element.box_normalized.model_fields_set:
                raise ValueError(
                    f"Element {element.id}: supplied height requires framing.mode='cover'."
                )
            if element.framing is not None and element.box_normalized.height is None:
                raise ValueError(
                    f"Element {element.id}: framing.mode='cover' requires an outer height."
                )
        return self


class ResolvedBox(Box):
    height: Width


class PixelBox(Model):
    x: Annotated[int, Field(strict=True, ge=0)]
    y: Annotated[int, Field(strict=True, ge=0)]
    width: PositiveInt
    height: PositiveInt


class SourceCrop(Model):
    left: Annotated[float, Field(strict=True, ge=0)]
    top: Annotated[float, Field(strict=True, ge=0)]
    right: Annotated[float, Field(strict=True, gt=0)]
    bottom: Annotated[float, Field(strict=True, gt=0)]

    @model_validator(mode="after")
    def check_area(self) -> Self:
        if self.right <= self.left or self.bottom <= self.top:
            raise ValueError("Source crop must have positive width and height.")
        return self


class ResolvedElement(Element):
    box_normalized: ResolvedBox
    box_pixels: PixelBox
    source_crop: SourceCrop | None = None
    rotated_box_pixels: PixelBox | None = None

    @model_validator(mode="after")
    def check_source_crop_mode(self) -> Self:
        if (self.framing is None) != (self.source_crop is None):
            raise ValueError("Only cover-mode snapshots require a derived source_crop.")
        return self

    @model_validator(mode="after")
    def check_rotation_box(self) -> Self:
        if (self.rotation_degrees == 0) != (self.rotated_box_pixels is None):
            raise ValueError("Only tilted snapshots require a derived rotated_box_pixels.")
        return self

    @property
    def photo_box_pixels(self) -> PixelBox:
        inset = self.border.width_px if self.border is not None else 0
        outer = self.box_pixels
        return PixelBox(
            x=outer.x + inset,
            y=outer.y + inset,
            width=outer.width - 2 * inset,
            height=outer.height - 2 * inset,
        )


class ResolvedLayout(Model):
    schema_version: SchemaVersion
    version: PositiveInt
    canvas: Canvas
    elements: Annotated[list[ResolvedElement], Field(min_length=2, max_length=6)]

    def as_input(self) -> InputLayout:
        data = self.model_dump()
        del data["version"]
        for element in data["elements"]:
            del element["box_pixels"]
            del element["source_crop"]
            del element["rotated_box_pixels"]
            if element["framing"] is None:
                del element["box_normalized"]["height"]
        return InputLayout.model_validate(data)


class Photo(Model):
    source_image_id: PositiveInt
    asset_id: Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{32}$")]
    imported_path: Annotated[str, Field(strict=True)]
    original_filename: Annotated[str, Field(strict=True, min_length=1)]
    width: PositiveInt
    height: PositiveInt

    @model_validator(mode="after")
    def check_pixel_limit(self) -> Self:
        if self.width * self.height > MAX_IMAGE_PIXELS:
            raise ValueError(f"Photo exceeds {MAX_IMAGE_PIXELS:,} decoded pixels.")
        return self


class Project(Model):
    schema_version: SchemaVersion
    owner_id: Literal["local-dev"]
    project_id: ProjectId
    photos: Annotated[list[Photo], Field(min_length=2, max_length=6)]
    current_version: PositiveInt | None

    @model_validator(mode="after")
    def check_photo_ids(self) -> Self:
        validate_project_id(self.project_id)
        if [photo.source_image_id for photo in self.photos] != list(
            range(1, len(self.photos) + 1)
        ):
            raise ValueError("Photo numbers must be contiguous and in import order.")
        if len({photo.asset_id for photo in self.photos}) != len(self.photos):
            raise ValueError("Photo asset IDs must be unique.")
        return self
