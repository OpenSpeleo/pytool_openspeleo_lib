import uuid
from datetime import date
from pathlib import Path

from pydantic import UUID4
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from openspeleo_lib.mixins import BaseMixin
from openspeleo_lib.mixins import UniqueSubFieldMixin
from openspeleo_lib.utils import str2bool


class RadiusVector(BaseModel):
    TensionCorridor: float = Field(..., alias="TensionCorridor")
    TensionProfile: float = Field(..., alias="TensionProfile")
    angle: float
    length: float

    @field_validator("*", mode="before")
    @classmethod
    def convert_to_float(cls, v):
        if isinstance(v, str):
            return float(v)
        return v

class RadiusCollection(BaseModel):
    RadiusVector: list[RadiusVector]

class Shape(BaseModel):
    RadiusCollection: RadiusCollection
    hasProfileAzimut: bool
    hasProfileTilt: bool
    profileAzimut: float
    profileTilt: float

    @field_validator("hasProfileAzimut", "hasProfileTilt", mode="before")
    @classmethod
    def convert_to_bool(cls, v):
        if isinstance(v, str):
            return str2bool(v)
        return v

    @field_validator("profileAzimut", "profileTilt", mode="before")
    @classmethod
    def convert_to_float(cls, v):
        if isinstance(v, str):
            return float(v)
        return v

class Shot(BaseMixin, UniqueSubFieldMixin, BaseModel):
    azimut: float
    closure_to_id: int
    color: str
    comment: str | None
    date: date
    depth: float
    depth_in: float
    excluded: bool
    explorer: str
    from_id: int
    id: int
    inclination: float
    latitude: float
    length: float
    locked: bool
    longitude: float
    profiletype: str
    section: str
    shape: Shape
    type: str

    # LRUD
    left: float
    right: float
    up: float
    down: float

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("azimut", "depth", "depth_in", "down", "inclination", "latitude",
                     "left", "length", "longitude", "right", "up", mode="before")
    @classmethod
    def convert_to_float(cls, v):
        if isinstance(v, str):
            return float(v)
        return v

    @field_validator("closure_to_id", "from_id", "id", mode="before")
    @classmethod
    def convert_to_int(cls, v):
        if isinstance(v, str):
            return int(v)
        return v

    @field_validator("excluded", "locked", mode="before")
    @classmethod
    def convert_to_bool(cls, v):
        if isinstance(v, str):
            return str2bool(v)
        return v

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, v):
        if isinstance(v, str):
            return date.fromisoformat(v)
        return v



class Section(BaseMixin, UniqueSubFieldMixin, BaseModel):
    id: int
    shots: list[Shot] = []

    @field_validator("shots")
    @classmethod
    def validate_shots_unique(cls, values: list[Shot]):
        return cls.validate_unique(field="id", values=values)


class Survey(UniqueSubFieldMixin, BaseModel):
    id: UUID4 = Field(default_factory=uuid.uuid4)
    name: str
    sections: list[Section] = []

    @property
    def shots(self):
        return [
            shot
            for section in self.sections
            for shot in section.shots
        ]

    @field_validator("sections")
    @classmethod
    def validate_shots_unique(cls, values):

        # 1. validate shots are unique
        shots = [shot for section in values for shot in section.shots]
        _ = cls.validate_unique(field="id", values=shots)
        _ = cls.validate_unique(field="name", values=shots)

        # 2. validate sections are unique
        _ = cls.validate_unique(field="id", values=values)
        _ = cls.validate_unique(field="name", values=values)

        return values

    @classmethod
    def from_compass_file(cls, filepath: Path):
        from compass_lib.parser import CompassParser

        if not filepath.exists():
                raise FileNotFoundError(f"File not found: `{filepath}`")

        survey = CompassParser(filepath)

        return cls(name="")

    @classmethod
    def from_ariane_file(cls, filepath):
        from ariane_lib.parser import ArianeParser

        if not filepath.exists():
                raise FileNotFoundError(f"File not found: `{filepath}`")
        survey = ArianeParser(filepath)

        sections = []
        for section in survey.sections:
            shots = [Shot(name=shot.name) for shot in section.shots]
            sections.append(Section(name=section.name, shots=shots))

        return cls(name=survey.name, sections=sections)


