import datetime
import uuid

from pydantic import UUID4
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_serializer

from openspeleo_lib.mixins import AutoIdModelMixin
from openspeleo_lib.mixins import BaseMixin
from openspeleo_lib.mixins import NameIdModelMixin


class RadiusVector(BaseModel):
    tension_corridor: float
    tension_profile: float
    angle: float
    norm: float  # Euclidian Norm aka. length

    model_config = ConfigDict(extra="forbid")


class RadiusCollection(BaseModel):
    radius_vector: list[RadiusVector] = []

    model_config = ConfigDict(extra="forbid")


class Shape(BaseModel):
    radius_collection: RadiusCollection
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


class LayerCollection(BaseModel):
    layer_list: list[Layer] = []

    model_config = ConfigDict(extra="forbid")


class SurveyShot(BaseMixin, AutoIdModelMixin, NameIdModelMixin, BaseModel):
    azimuth: float
    closure_to_id: int = -1
    color: str
    comment: str | None = None
    date: datetime.date
    depth: float
    depth_in: float
    excluded: bool
    explorer: str | None = None
    from_id: int
    inclination: float
    latitude: float
    length: float
    locked: bool
    longitude: float
    profiletype: str
    section: str
    type: str

    # SubModel
    shape: Shape | None = None

    # LRUD
    left: float
    right: float
    up: float
    down: float

    model_config = ConfigDict(extra="forbid")

    @field_serializer("date")
    def serialize_dt(self, dt: datetime.date, _info):
        return dt.strftime("%Y-%m-%d")


class ShotCollection(BaseModel):
    shot_list: list[SurveyShot] = []

    model_config = ConfigDict(extra="forbid")


class Survey(BaseMixin, BaseModel):
    speleodb_id: UUID4 = Field(default_factory=uuid.uuid4)
    cave_name: str
    unit: str = "m"
    data: ShotCollection = Field(default_factory=lambda: ShotCollection())
    layers: LayerCollection = Field(default_factory=lambda: LayerCollection())
    first_start_absolute_elevation: float = 0.0
    use_magnetic_azimuth: bool = True

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
