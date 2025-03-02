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
from pydantic_extra_types.color import Color

from openspeleo_lib.constants import OSPL_SECTIONNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SECTIONNAME_MIN_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MIN_LENGTH
from openspeleo_lib.enums import ArianeProfileType
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.enums import LengthUnits
from openspeleo_lib.generators import UniqueValueGenerator

ShotID = NewType("ShotID", int)
ShotCompassName = NewType("ShotCompassName", str)

SectionID = NewType("SectionID", int)
SectionName = NewType("SectionName", str)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~ ARIANE SPECIFIC MODELS ~~~~~~~~~~~~~~~~~~~~~~~~~ #


class ArianeRadiusVector(BaseModel):
    angle: float
    norm: float  # Euclidian Norm aka. length
    tension_corridor: float
    tension_profile: float

    model_config = ConfigDict(extra="forbid")


class ArianeShape(BaseModel):
    has_profile_azimuth: bool
    has_profile_tilt: bool
    profile_azimuth: Annotated[float, Field(ge=0, lt=360)]
    profile_tilt: float
    radius_vectors: list[ArianeRadiusVector] = []

    model_config = ConfigDict(extra="forbid")


class ArianeViewerLayerStyle(BaseModel):
    dash_scale: float
    fill_color_string: str
    line_type: str
    line_type_scale: float
    opacity: float
    size_mode: str
    stroke_color_string: str
    stroke_thickness: float

    model_config = ConfigDict(extra="forbid")


class ArianeViewerLayer(BaseModel):
    constant: bool
    locked_layer: bool
    layer_name: str
    style: ArianeViewerLayerStyle
    visible: bool

    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ COMMON MODELS ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #
class Shot(BaseModel):
    # Primary Keys
    shot_id: NonNegativeInt = None

    shot_name: Annotated[
        str,
        StringConstraints(
            pattern=rf"^[a-zA-Z0-9_\-~:!?.'\(\)\[\]\{{\}}@*&#%|$]{{{OSPL_SHOTNAME_MIN_LENGTH},{OSPL_SHOTNAME_MAX_LENGTH}}}$",
            to_upper=True,
        ),
    ] = None

    # Core Attributes
    length: NonNegativeFloat
    depth: NonNegativeFloat
    azimuth: Annotated[float, Field(ge=0, lt=360)]

    # Attributes
    closure_to_id: int = -1
    from_id: int = -1

    depth_in: float = None
    inclination: float = None

    latitude: Annotated[float, Field(ge=-90, le=90)] = None
    longitude: Annotated[float, Field(ge=-180, le=180)] = None

    color: Color = Color("#FFB366")  # An orange color easily visible
    shot_comment: str | None = None

    excluded: bool = False
    locked: bool = False

    # Ariane Specific
    shape: ArianeShape | None = None
    profiletype: ArianeProfileType = ArianeProfileType.VERTICAL
    shot_type: ArianeShotType = ArianeShotType.REAL

    # LRUD
    left: NonNegativeFloat = None
    right: NonNegativeFloat = None
    up: NonNegativeFloat = None
    down: NonNegativeFloat = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        for key, dtype in [("shot_id", ShotID), ("shot_name", ShotCompassName)]:
            if getattr(self, key) is None:
                setattr(self, key, UniqueValueGenerator.get(vartype=dtype))
            else:
                UniqueValueGenerator.register(vartype=dtype, value=getattr(self, key))

        return self

    @field_serializer("color")
    def serialize_dt(self, color: Color | None, _info):
        if color is None:
            return None
        return color.original()


class Section(BaseModel):
    # Primary Keys
    section_id: NonNegativeInt = None

    section_name: Annotated[
        str,
        StringConstraints(
            pattern=rf"^[ a-zA-Z0-9_\-~:!?.'\(\)\[\]\{{\}}@*&#%|$]{{{OSPL_SECTIONNAME_MIN_LENGTH},{OSPL_SECTIONNAME_MAX_LENGTH}}}$",  # noqa: E501
            # to_upper=True,
        ),
    ]  # Default value not allowed - No `None` value set by default

    # Attributes
    date: datetime.date = None
    explorers: list[str] = []
    surveyors: list[str] = []

    shots: list[Shot] = []

    # Compass Specific
    section_comment: str = ""
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
            ("section_id", SectionID, True),
            ("section_name", SectionName, False),
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
    sections: list[Section] = []

    unit: LengthUnits = LengthUnits.FEET
    first_start_absolute_elevation: NonNegativeFloat = 0.0
    use_magnetic_azimuth: bool = True

    ariane_viewer_layers: list[ArianeViewerLayer] = []

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
