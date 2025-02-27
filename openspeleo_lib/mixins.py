from typing import NewType

from pydantic import model_validator

ShotID = NewType("ShotID", int)
ShotCompassName = NewType("ShotCompassName", str)

SectionID = NewType("SectionID", int)
SectionName = NewType("SectionName", str)


class BaseMixin:
    @model_validator(mode="before")
    @classmethod
    def remove_none_values(cls, data: dict) -> dict:
        return {k: v for k, v in data.items() if v is not None}
