from __future__ import annotations

import contextlib
import datetime
import math
import uuid
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated
from typing import NewType

import annotated_types
import orjson
from pydantic import UUID4
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import NonNegativeInt
from pydantic import StringConstraints
from pydantic import ValidationInfo
from pydantic import field_serializer
from pydantic import field_validator
from pydantic import model_validator
from pydantic_extra_types.color import Color

from openspeleo_lib.constants import OSPL_GEOJSON_DIGIT_PRECISION
from openspeleo_lib.constants import OSPL_SECTIONNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.enums import ArianeProfileType
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.enums import LengthUnits
from openspeleo_lib.generators import UniqueValueGenerator
from openspeleo_lib.geo_utils import GeoLocation
from openspeleo_lib.geo_utils import get_declination

if TYPE_CHECKING:
    import sys
    from collections.abc import Generator

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

ShotID = NewType("ShotID", int)
ShotCompassName = NewType("ShotCompassName", str)

SectionID = NewType("SectionID", int)
SectionName = NewType("SectionName", str)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Types ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ #

NonNegativeFloat = Annotated[float, annotated_types.Ge(0)]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~ ARIANE SPECIFIC MODELS ~~~~~~~~~~~~~~~~~~~~~~~~~ #


class ArianeRadiusVector(BaseModel):
    angle: float
    norm: float  # Euclidian Norm aka. length
    tension_corridor: str | None = None
    tension_profile: str | None = None

    model_config = ConfigDict(extra="forbid")


class ArianeShape(BaseModel):
    has_profile_azimuth: bool
    has_profile_tilt: bool
    profile_azimuth: Annotated[float, Field(ge=0, lt=360)]
    profile_tilt: float
    radius_vectors: Annotated[list[ArianeRadiusVector], Field(default_factory=list)]

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
    id: Annotated[UUID4, Field(default_factory=uuid.uuid4)]

    # Primary Keys
    shot_id: NonNegativeInt | None = None

    shot_name: Annotated[
        str,
        StringConstraints(
            max_length=OSPL_SHOTNAME_MAX_LENGTH,
            to_upper=True,
        ),
    ] = None

    # Exluded Fields - Upward keys
    section: Annotated[Section | None, Field(default=None, exclude=True)]

    # Ariane shot type (before core fields)
    shot_type: ArianeShotType = ArianeShotType.REAL

    # Core Attributes
    length: NonNegativeFloat
    depth: float
    azimuth: float

    # Attributes
    closure_to_id: int = -1
    from_id: int = -1

    depth_in: float = None
    inclination: float = None

    latitude: Annotated[float | None, Field(ge=-90, le=90)] = None
    longitude: Annotated[float | None, Field(ge=-180, le=180)] = None

    color: Color = Color("#FFB366")  # An orange color easily visible
    shot_comment: str | None = None

    excluded: bool = False
    locked: bool = False

    # Ariane Specific
    shape: ArianeShape | None = None
    profiletype: ArianeProfileType = ArianeProfileType.VERTICAL

    # LRUD
    left: NonNegativeFloat | None = None
    right: NonNegativeFloat | None = None
    up: NonNegativeFloat | None = None
    down: NonNegativeFloat | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("length", "left", "right", "up", "down", mode="before")
    @classmethod
    def _ensure_non_negative(
        cls, value: float | str | None, info: ValidationInfo
    ) -> float | str | None:
        shot_type = info.data.get("shot_type")
        if shot_type == ArianeShotType.REAL:
            # Skip coercion for REAL; let type constraints handle
            return value

        match value:
            case float():
                return value if value >= 0 else 0.0
            case str():
                with contextlib.suppress(ValueError, TypeError):
                    val = float(value)
                    return val if val >= 0 else 0.0
                return value
            case None:
                return None
            case _:
                return value

    @field_validator("shot_type", mode="before")
    @classmethod
    def _validate_shot_type(
        cls, value: ArianeShotType | str, info: ValidationInfo
    ) -> ArianeShotType:
        match value:
            case ArianeShotType():
                return value

            case str():
                with contextlib.suppress(KeyError):
                    return ArianeShotType.reverse(value)

                return ArianeShotType.REAL

            case _:
                raise ValueError(f"Unexpected type received: {type(value)}")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        # 1. Validate unique keys
        for key, dtype in [
            ("shot_id", ShotID),
            # ("shot_name", ShotCompassName),
        ]:
            if getattr(self, key) is None:
                setattr(self, key, UniqueValueGenerator.get(vartype=dtype))
            else:
                UniqueValueGenerator.register(vartype=dtype, value=getattr(self, key))

        # 2. Validate `azimuth`
        if self.shot_type == ArianeShotType.REAL:
            if not (0 <= self.azimuth <= 360):
                self.azimuth = self.azimuth % 360

        return self

    @field_serializer("color")
    def serialize_dt(self, color: Color | None, _info):
        if color is None:
            return None
        return color.original()

    def length_2d(self, origin_depth: float | None) -> float:
        """
        Horizontal plan-view length for this shot in the same unit as `length`.

        Preference order for computing horizontal component:
        - Use `depth` if available: horizontal = sqrt(length^2 - delta_depth^2)
        - Else, `inclination` if available: horizontal = length * cos(inclination)
        - Otherwise: raise ValueError
        """

        if self.depth is not None:
            if origin_depth is None:
                raise ValueError("`origin_depth` is missing")

            if (delta_depth := abs(self.depth - origin_depth)) <= self.length:
                return math.sqrt(self.length**2 - delta_depth**2)

            raise ValueError(
                f"Shot is shorter than the vertical variation: {self.length=}, "
                f"{delta_depth=}."
            )

        if self.inclination is not None:
            if self.inclination < -90 or self.inclination > 90:
                raise ValueError(f"Invalid inclination: {self.inclination}")

            return self.length * math.cos(math.radians(self.inclination))

        raise ValueError("Impossible to calculate length projection ...")

    def is_geolocation_known(self) -> bool:
        if self.latitude is None or self.longitude is None:
            return False

        return abs(self.latitude) > float(f"1e-{OSPL_GEOJSON_DIGIT_PRECISION}") and abs(
            self.longitude
        ) > float(f"1e-{OSPL_GEOJSON_DIGIT_PRECISION}")

    @property
    def azimuth_true(self) -> float:
        if (section := self.section) is None:
            raise ValueError(
                "Section is not assigned. Impossible to access magnetic declination."
            )

        return (self.azimuth + section.computed_declination) % 360

    @property
    def coordinates(self) -> GeoLocation | None:
        if not self.is_geolocation_known():
            return None

        return GeoLocation(latitude=self.latitude, longitude=self.longitude)


class Section(BaseModel):
    id: Annotated[UUID4, Field(default_factory=uuid.uuid4)]

    section_name: Annotated[
        str,
        StringConstraints(
            max_length=OSPL_SECTIONNAME_MAX_LENGTH,
            # to_upper=True,
        ),
    ]  # Default value not allowed - No `None` value set by default

    # Exluded Fields - Upward keys
    survey: Annotated[Survey | None, Field(default=None, exclude=True)]

    # Attributes
    date: datetime.date | None = None
    description: str | None = None
    explorers: str | None = None
    surveyors: str | None = None

    shots: Annotated[list[Shot], Field(default_factory=list)]

    # Compass Specific
    section_comment: str = ""
    compass_format: str = "DDDDUDLRLADN"
    correction: Annotated[list[float], Field(default_factory=list)]
    correction2: Annotated[list[float], Field(default_factory=list)]
    declination: float = 0.0

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        # 1. Assigning upward reference to the shot => section
        for shot in self.shots:
            shot.section = self

        return self

    @field_serializer("date")
    def serialize_dt(self, dt: datetime.date | None, _info):
        if dt is None:
            return None
        return dt.strftime("%Y-%m-%d")

    @cached_property
    def computed_declination(self) -> float:
        if (geo_anchor := self.survey.geo_anchor) is None:
            raise ValueError(
                "Impossible to find a known Lat/Long point in this survey."
            )

        return get_declination(
            location=geo_anchor,
            dt=datetime.datetime(self.date.year, self.date.month, self.date.day),
        )


class Survey(BaseModel):
    speleodb_id: Annotated[UUID4, Field(default_factory=uuid.uuid4)]
    cave_name: str
    sections: Annotated[list[Section], Field(default_factory=list)]

    unit: LengthUnits = LengthUnits.FEET
    first_start_absolute_elevation: NonNegativeFloat = 0.0
    use_magnetic_azimuth: bool = True

    ariane_viewer_layers: Annotated[
        list[ArianeViewerLayer],
        Field(default_factory=list),
    ]

    carto_ellipse: dict | None = None
    carto_line: dict | None = None
    carto_linked_surface: dict | None = None
    carto_overlay: dict | None = None
    carto_page: dict | None = None
    carto_rectangle: dict | None = None
    carto_selection: dict | None = None
    carto_spline: dict | None = None
    constraints: dict | None = None
    list_annotation: dict | None = None

    # model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_model(self) -> Self:
        # 1. Assigning upward reference to the section => survey
        for section in self.sections:
            section.survey = self

        return self

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

    @property
    def shots(self) -> Generator[Shot]:
        """Returns a flat list of all shots in the survey."""
        for section in self.sections:
            yield from section.shots

    @cached_property
    def geo_anchor(self) -> GeoLocation | None:
        """Returns the geographic anchor point for the survey.
        This point is being used to calculate geo magnetic declination.
        It doesn't really matter, which location is being used as the anchor point.
        It just has to be the right "geographic area".

        Result: we just return the first `GeoLocation` found.
        """

        if not self.sections:
            return None

        # Get the first section's anchor point
        for shot in self.shots:
            if (geoloc := shot.coordinates) is not None:
                return geoloc

        # No shot with "known location found".
        return None
