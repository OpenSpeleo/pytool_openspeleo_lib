import uuid
from datetime import date

from pydantic import UUID4
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

from openspeleo_lib.formats.ariane import ARIANE_MAPPING
from openspeleo_lib.mixins import BaseMixin
from openspeleo_lib.mixins import UniqueSubFieldMixin
from openspeleo_lib.utils import apply_key_mapping
from openspeleo_lib.utils import str2bool


class RadiusVector(BaseModel):
    tension_corridor: float
    tension_profile: float
    angle: float
    norm: float  # Euclidian Norm aka. length

    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def convert_to_float(cls, v):
        if isinstance(v, str):
            return float(v)
        return v


class RadiusCollection(BaseModel):
    radius_vector: list[RadiusVector] = []

    model_config = ConfigDict(extra="forbid")

    @field_validator("radius_vector", mode="before")
    @classmethod
    def ensure_list_type(cls, v):
        if isinstance(v, dict):
            return [v]
        return v


class Shape(BaseModel):
    radius_collection: RadiusCollection
    has_profile_azimuth: bool
    has_profile_tilt: bool
    profile_azimuth: float
    profile_tilt: float

    model_config = ConfigDict(extra="forbid")

    @field_validator("has_profile_azimuth", "has_profile_tilt", mode="before")
    @classmethod
    def convert_to_bool(cls, v):
        if isinstance(v, str):
            return str2bool(v)
        return v

    @field_validator("profile_azimuth", "profile_tilt", mode="before")
    @classmethod
    def convert_to_float(cls, v):
        if isinstance(v, str):
            return float(v)
        return v


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

    @field_validator("dash_scale", "line_type_scale", "opacity", "stroke_thickness",
                     mode="before")
    @classmethod
    def convert_to_float(cls, v):
        if isinstance(v, str):
            return float(v)
        return v


class Layer(BaseModel):
    constant: bool = True
    locked_layer: bool = False
    layer_name: str
    style: LayerStyle
    visible: bool = True

    model_config = ConfigDict(extra="forbid")

    @field_validator("constant", "locked_layer", "visible", mode="before")
    @classmethod
    def convert_to_bool(cls, v):
        if isinstance(v, str):
            return str2bool(v)
        return v


class LayerCollection(BaseModel):
    layer_list: list[Layer] = []

    model_config = ConfigDict(extra="forbid")

    @field_validator("layer_list", mode="before")
    @classmethod
    def ensure_list_type(cls, v):
        if isinstance(v, dict):
            return [v]
        return v


class Shot(BaseMixin, UniqueSubFieldMixin, BaseModel):
    azimuth: float
    closure_to_id: int
    color: str
    comment: str | None = None
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
    type: str

    # SubModel
    shape: Shape

    # LRUD
    left: float
    right: float
    up: float
    down: float

    model_config = ConfigDict(extra="forbid")

    # model_config = ConfigDict(use_enum_values=True)

    @field_validator("azimuth", "depth", "depth_in", "down", "inclination", "latitude",
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

    @classmethod
    def from_ariane(cls, data):
        data = apply_key_mapping(data, mapping=ARIANE_MAPPING.inverse)
        return cls(**data)

# class Section(BaseMixin, UniqueSubFieldMixin, BaseModel):
#     id: int
#     shots: list[Shot] = []

#     @field_validator("shots")
#     @classmethod
#     def validate_shots_unique(cls, values: list[Shot]):
#         return cls.validate_unique(field="id", values=values)

class ShotCollection(BaseModel):
    shot_list: list[Shot] = []

    model_config = ConfigDict(extra="forbid")

    @field_validator("shot_list", mode="before")
    @classmethod
    def ensure_list_type(cls, v):
        if isinstance(v, dict):
            return [v]
        return v


class Survey(UniqueSubFieldMixin, BaseModel):
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

    @field_validator("use_magnetic_azimuth", mode="before")
    @classmethod
    def convert_to_bool(cls, v):
        if isinstance(v, str):
            return str2bool(v)
        return v

    @field_validator("first_start_absolute_elevation", mode="before")
    @classmethod
    def convert_to_float(cls, v):
        if isinstance(v, str):
            return float(v)
        return v

    # @classmethod
    # def from_compass_file(cls, filepath: Path):
    #     from compass_lib.parser import CompassParser

    #     if not filepath.exists():
    #             raise FileNotFoundError(f"File not found: `{filepath}`")

    #     survey = CompassParser(filepath)

    #     return cls(name="")

    # @classmethod
    # def from_ariane_file(cls, filepath):
    #     from ariane_lib.parser import ArianeParser

    #     if not filepath.exists():
    #             raise FileNotFoundError(f"File not found: `{filepath}`")
    #     survey = ArianeParser(filepath)

    #     sections = []
    #     for section in survey.sections:
    #         shots = [Shot(name=shot.name) for shot in section.shots]
    #         sections.append(Section(name=section.name, shots=shots))

    #     return cls(name=survey.name, sections=sections)

    @classmethod
    def from_ariane_file(cls, filepath):
        from ariane_lib.parser import ArianeParser

        if not filepath.exists():
                raise FileNotFoundError(f"File not found: `{filepath}`")
        survey = ArianeParser(filepath)

        return cls.from_ariane(survey.data)


    @classmethod
    def from_ariane(cls, data):
        data = apply_key_mapping(data, mapping=ARIANE_MAPPING.inverse)
        return cls(**data)
