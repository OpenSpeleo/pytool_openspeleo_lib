from __future__ import annotations

from enum import Enum


class CustomEnum(Enum):
    @classmethod
    def reverse(cls, name):
        return cls._value2member_map_[name]


class ArianeProfileType(CustomEnum):
    VERTICAL = "VERTICAL"
    HORIZONTAL = "HORIZONTAL"
    PERPENDICULAR = "PERPENDICULAR"
    BISECTION = "BISECTION"


class ArianeShotType(CustomEnum):
    REAL = "REAL"
    START = "START"
    VIRTUAL = "VIRTUAL"
    CLOSURE = "CLOSURE"


class LengthUnits(CustomEnum):
    FEET = "FT"
    METERS = "M"
