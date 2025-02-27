import datetime
import uuid
from pathlib import Path
from typing import Annotated
from typing import Literal
from typing import NewType
from typing import Self

import orjson
from pydantic import UUID4
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import NonNegativeFloat
from pydantic import NonNegativeInt
from pydantic import StringConstraints
from pydantic import field_serializer
from pydantic import model_validator

from openspeleo_lib.constants import OSPL_SECTIONNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SECTIONNAME_MIN_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MIN_LENGTH
from openspeleo_lib.generators import UniqueValueGenerator

ShotID = NewType("ShotID", int)
ShotCompassName = NewType("ShotCompassName", str)

SectionID = NewType("SectionID", int)
SectionName = NewType("SectionName", str)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~ ARIANE SPECIFIC MODELS ~~~~~~~~~~~~~~~~~~~~~~~~~ #


class RadiusVector(BaseModel):
    tension_corridor: float
    tension_profile: float
    angle: float
    norm: float  # Euclidian Norm aka. length

    model_config = ConfigDict(extra="forbid")


class Shape(BaseModel):
    radius_vectors: list[RadiusVector] = []
    has_profile_azimuth: bool
    has_profile_tilt: bool
    profile_azimuth: float
    profile_tilt: float

    model_config = ConfigDict(extra="forbid")


class LayerStyle(BaseModel):
    dash_scale: float
    fill_color_string: str
    line_type: str
    line_type_scale: float
    opacity: float
    size_mode: str
    stroke_color_string: str
    stroke_thickness: float

    model_config = ConfigDict(extra="forbid")


class Layer(BaseModel):
    constant: bool = True
    locked_layer: bool = False
    layer_name: str
    style: LayerStyle
    visible: bool = True

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ COMMON MODELS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
class SurveyShot(BaseModel):
    # Primary Keys
    id: NonNegativeInt = None

    name_compass: Annotated[
        str,
        StringConstraints(
            pattern=rf"^[a-zA-Z0-9_\-~:!?.'\(\)\[\]\{{\}}@*&#%|$]{{{OSPL_SHOTNAME_MIN_LENGTH},{OSPL_SHOTNAME_MAX_LENGTH}}}$",
            to_upper=True,
        ),
    ] = None

    # Attributes
    azimuth: float
    closure_to_id: int = -1
    color: str
    comment: str | None = None
    # date: datetime.date
    depth: float
    depth_in: float
    excluded: bool
    from_id: int
    inclination: float
    latitude: float
    length: float
    locked: bool
    longitude: float
    profiletype: str
    type: str

    # SubModel
    shape: Shape | None = None

    # LRUD
    left: NonNegativeFloat = 0.0
    right: NonNegativeFloat = 0.0
    up: NonNegativeFloat = 0.0
    down: NonNegativeFloat = 0.0

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        for key, dtype in [("id", ShotID), ("name_compass", ShotCompassName)]:
            if getattr(self, key) is None:
                setattr(self, key, UniqueValueGenerator.get(vartype=dtype))
            else:
                UniqueValueGenerator.register(vartype=dtype, value=getattr(self, key))

        return self


class SurveySection(BaseModel):
    # Primary Keys
    id: NonNegativeInt = None

    name: Annotated[
        str,
        StringConstraints(
            pattern=rf"^[ a-zA-Z0-9_\-~:!?.'\(\)\[\]\{{\}}@*&#%|$]{{{OSPL_SECTIONNAME_MIN_LENGTH},{OSPL_SECTIONNAME_MAX_LENGTH}}}$",  # noqa: E501
            # to_upper=True,
        ),
    ]  # Default value not allowed - No `None` value set by default

    # Attributes
    date: datetime.date = None
    surveyors: list[str] = []

    shots: list[SurveyShot] = []

    # Compass Specific
    comment: str = ""
    compass_format: str = "DDDDUDLRLADN"
    correction: list[float] = []
    correction2: list[float] = []
    declination: float = 0.0

    model_config = ConfigDict(extra="forbid")

    @field_serializer("date")
    def serialize_dt(self, dt: datetime.date | None, _info):
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        for key, dtype, allow_generate in [
            ("id", SectionID, True),
            ("name", SectionName, False),
        ]:
            if getattr(self, key) is None:
                if allow_generate:
                    setattr(self, key, UniqueValueGenerator.get(vartype=dtype))
                else:
                    raise ValueError(f"Value for `{key}` cannot be None.")

            else:
                UniqueValueGenerator.register(vartype=dtype, value=getattr(self, key))

        return self


class Survey(BaseModel):
    speleodb_id: UUID4 = Field(default_factory=uuid.uuid4)
    cave_name: str
    sections: list[SurveySection] = []

    unit: Literal["m", "ft"] = "m"
    first_start_absolute_elevation: float = 0.0
    use_magnetic_azimuth: bool = True

    ariane_layers: list[Layer] = []

    carto_ellipse: str | None = None
    carto_line: str | None = None
    carto_linked_surface: str | None = None
    carto_overlay: str | None = None
    carto_page: str | None = None
    carto_rectangle: str | None = None
    carto_selection: str | None = None
    carto_spline: str | None = None
    constraints: str | None = None
    list_annotation: str | None = None

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def from_json(cls, filepath: str | Path) -> Self:
        with Path(filepath).open(mode="rb") as f:
            return cls.model_validate(orjson.loads(f.read()))

    def to_json(self, filepath: str | Path) -> None:
        """
        Serializes the model to a JSON file.

        Args:
            filepath (str | Path): The filepath where the JSON data will be written.

        Returns:
            None
        """
        with Path(filepath).open(mode="w") as f:
            f.write(
                orjson.dumps(
                    self.model_dump(mode="json"),
                    None,
                    option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
                ).decode("utf-8")
            )
