from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError
from pydantic import field_validator

from openspeleo_lib.interfaces.ariane.name_map import ARIANE_MAPPING
from openspeleo_lib.models import Shot
from openspeleo_lib.pydantic_utils import aliased_model

ShotAriane = aliased_model(Shot, ARIANE_MAPPING, "Ariane")


@pytest.mark.parametrize("model", [Shot, ShotAriane])
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("longitude", -180.01),
        ("longitude", 180.01),
        ("latitude", -90.01),
        ("latitude", 90.01),
        ("longitude", float("nan")),
        ("longitude", float("inf")),
        ("latitude", float("-inf")),
        ("length", -1),
        ("left", -1),
        ("id_stop", -1),
        ("name", "a" * 1000),
    ],
)
def test_aliases_preserve_constraints(model, field, value):
    data = {"id_stop": 1, "length": 1, "depth": 0, "azimuth": 0, field: value}
    with pytest.raises(ValidationError):
        model.model_validate(data)


@pytest.mark.parametrize("model", [Shot, ShotAriane])
@pytest.mark.parametrize("latitude", [-90, 90])
@pytest.mark.parametrize("longitude", [-180, 180])
def test_coordinate_boundaries(model, latitude, longitude):
    shot = model(
        id_stop=1,
        length=1,
        depth=0,
        azimuth=0,
        latitude=latitude,
        longitude=longitude,
    )
    assert (shot.latitude, shot.longitude) == (latitude, longitude)


def test_aliases_preserve_defaults_factories_nested_fields_and_validators():
    class Child(BaseModel):
        model_config = ConfigDict(validate_by_name=True)
        value: Annotated[int, Field(ge=0, description="A measurement")] = 7
        hidden: str = Field(default="secret", exclude=True)

        @field_validator("value")
        @classmethod
        def reject_unlucky(cls, value):
            if value == 13:
                raise ValueError("unlucky")
            return value

    class Parent(BaseModel):
        children: list[Child] = Field(default_factory=list)

    model = aliased_model(Parent, {Child: {"value": "Value"}}, "Aliased")
    first, second = model(), model()
    first.children.append(Child())
    assert second.children == []
    parsed = model.model_validate({"children": [{"Value": 8}]})
    assert parsed.model_dump(by_alias=True) == {"children": [{"Value": 8}]}
    assert model.model_validate({"children": [{}]}).children[0].value == 7
    assert type(parsed.children[0]).model_fields["value"].description == "A measurement"
    for value in [-1, 13]:
        with pytest.raises(ValidationError):
            model.model_validate({"children": [{"Value": value}]})


def test_shot_aliases_and_inherited_normalization():
    shot = ShotAriane.model_validate(
        {"ID": 1, "Length": 1, "Depth": 0, "Azimut": 450, "Name": "station"}
    )
    assert shot.azimuth == 90
    assert shot.name == "STATION"
    assert "section" not in shot.model_dump()
    assert shot.model_dump(by_alias=True)["ID"] == 1
