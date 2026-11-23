"""Strict authored recipes, computed geometry, and local project contracts."""

import re
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_JSON_BYTES = 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_CANVAS_AXIS = 4096
OWNER_ID = "local-dev"

PositiveInt = Annotated[int, Field(strict=True, gt=0)]
SchemaVersion = Annotated[int, Field(strict=True, ge=3, le=3)]
Coordinate = Annotated[float, Field(strict=True, ge=0, le=1)]
Extent = Annotated[float, Field(strict=True, gt=0, le=1)]
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
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, allow_inf_nan=False)

    @field_validator("schema_version", mode="before", check_fields=False)
    @classmethod
    def supported_version(cls, value: object) -> object:
        if type(value) is int and value != 3:
            raise ValueError(
                f"Unsupported schema_version {value}; expected 3. "
                "Old projects are read-only archives; create a fresh v3 project."
            )
        return value


class Border(Model):
    width_px: Annotated[int, Field(strict=True, ge=0)] = Field(
        description="Uniform outside border thickness in output pixels; zero means none."
    )
    color: HexColor = Field(description="Outside border colour as #RRGGBB.")


class Canvas(Model):
    width: Annotated[int, Field(strict=True, ge=1, le=MAX_CANVAS_AXIS)] = Field(
        description="Output canvas width in pixels."
    )
    height: Annotated[int, Field(strict=True, ge=1, le=MAX_CANVAS_AXIS)] = Field(
        description="Output canvas height in pixels."
    )
    background: HexColor = Field(description="Solid canvas colour as #RRGGBB.")


class WholeBox(Model):
    center_x: Coordinate = Field(
        description="Outer frame centre, as a fraction of canvas width."
    )
    center_y: Coordinate = Field(
        description="Outer frame centre, as a fraction of canvas height."
    )
    width: Extent = Field(description="Border-inclusive outer width / canvas width.")


class FrameBox(WholeBox):
    height: Extent = Field(description="Border-inclusive outer height / canvas height.")


class Crop(Model):
    zoom: Annotated[float, Field(strict=True, ge=1, le=4)] = Field(
        default=1.0, description="Multiplier of the minimum uniform cover scale, from 1 to 4."
    )
    pan_x: Coordinate = Field(
        default=0.5, description="Source crop position over available travel: 0 left, 1 right."
    )
    pan_y: Coordinate = Field(
        default=0.5, description="Source crop position over available travel: 0 top, 1 bottom."
    )


class PhotoLayer(Model):
    photo_id: PositiveInt = Field(
        description="Stable project photo number assigned at import; independent of layer order."
    )
    border: Border | None = None
    corner_radius_px: Annotated[int, Field(strict=True, ge=0)] = Field(
        default=0,
        description="Photo-edge radius in output pixels; positive outer radius adds the border width.",
    )
    rotation_degrees: Annotated[float, Field(strict=True, ge=-10, le=10)] = Field(
        default=0.0,
        description="Clockwise degrees about the outer frame centre; negative is counterclockwise.",
    )


class WholeLayer(PhotoLayer):
    mode: Literal["whole"]
    box: WholeBox = Field(
        description="Centre-anchored width-only frame; derive height without cropping."
    )


class CoverLayer(PhotoLayer):
    mode: Literal["cover"]
    box: FrameBox
    crop: Crop = Field(
        default_factory=Crop,
        description="Optional cover crop controls; omission means centred at 1x. Null is invalid.",
    )


Layer = Annotated[WholeLayer | CoverLayer, Field(discriminator="mode")]


class InputLayout(Model):
    schema_version: SchemaVersion
    canvas: Canvas
    layers: Annotated[list[Layer], Field(min_length=2, max_length=6)] = Field(
        description="Photo layers ordered back to front; each imported photo appears exactly once."
    )


class ResolvedBox(Model):
    x: Coordinate = Field(description="Derived untilted outer left / canvas width.")
    y: Coordinate = Field(description="Derived untilted outer top / canvas height.")
    width: Extent
    height: Extent


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


class LayerGeometry(Model):
    photo_id: PositiveInt
    box_normalized: ResolvedBox
    box_pixels: PixelBox
    photo_box_pixels: PixelBox
    source_crop: SourceCrop | None
    rotated_box_pixels: PixelBox | None


class ResolvedLayout(Model):
    schema_version: SchemaVersion
    version: PositiveInt
    recipe: InputLayout
    geometry: Annotated[list[LayerGeometry], Field(min_length=2, max_length=6)]


class Photo(Model):
    photo_id: PositiveInt
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
        if [photo.photo_id for photo in self.photos] != list(range(1, len(self.photos) + 1)):
            raise ValueError("Photo numbers must be contiguous and in import order.")
        if len({photo.asset_id for photo in self.photos}) != len(self.photos):
            raise ValueError("Photo asset IDs must be unique.")
        return self
