from __future__ import annotations

import datetime  # noqa: TC003
import json
import uuid
from typing import TYPE_CHECKING

import orjson
from pydantic import UUID4
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

if TYPE_CHECKING:
    from pathlib import Path


class Location(BaseModel):
    """UTM or projected coordinate with elevation."""

    easting: float
    northing: float
    up: float

    model_config = ConfigDict(extra="forbid")

    @field_validator("up")
    @classmethod
    def up_must_be_valid(cls, v: float) -> float:
        if not (-10000.0 <= v <= 10000.0):
            raise ValueError("up value out of realistic range")
        return v


class CorrectionFactors(BaseModel):
    azimuth: float
    inclination: float
    length: float

    model_config = ConfigDict(extra="forbid")


class Shot(BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4)
    from_: str = Field(..., alias="from")
    to: str
    length: float
    azimuth: float
    inclination: float
    up: float
    down: float
    left: float
    right: float
    flags: str | None = None
    comment: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("length")
    @classmethod
    def non_negative_length(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Shot length must be non-negative")
        return v


class Survey(BaseModel):
    cave_name: str
    id: UUID4 = Field(default_factory=uuid.uuid4)
    name: str
    date: datetime.date | None = None
    comment: str
    team: str
    shots: list[Shot]

    declination: float
    correction_factors: CorrectionFactors
    backsight_correction_factors: CorrectionFactors | None = None

    model_config = ConfigDict(extra="forbid")


class Anchor(BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4)
    name: str
    location: Location


class DATFile(BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4)
    filename: str
    anchors: list[Anchor]
    surveys: list[Survey]


class EastNorthElevation(BaseModel):
    easting: float
    northing: float
    up: float


class BaseLocation(BaseModel):
    east_north_elevation: EastNorthElevation
    zone: int
    convergence_angle: float


class MAKFile(BaseModel):
    speleodb_id: UUID4 = Field(default_factory=uuid.uuid4)
    filename: str
    base_location: BaseLocation
    datum: str
    utm_zone: int | None
    survey_files: list[DATFile]

    # convenience methods
    @classmethod
    def from_json(cls, path: Path) -> MAKFile:
        with path.open(mode="r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.model_validate(data)

    def to_json(self, path: Path | None = None, **kwargs) -> str | None:
        json_str = orjson.dumps(
            self.model_dump(by_alias=True, mode="json", **kwargs),
            None,
            option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
        ).decode("utf-8")

        if not path:
            return json_str

        with path.open(mode="w", encoding="utf-8") as f:
            f.write(json_str)
        return None
