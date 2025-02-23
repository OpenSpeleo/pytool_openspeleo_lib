#!/usr/bin/env python

from enum import IntEnum
from typing import Self


class BaseEnum(IntEnum):
    @classmethod
    def from_str(cls, value: str) -> Self:
        try:
            return cls[value.upper()]
        except KeyError as e:
            raise ValueError(f"Unknown value: {value.upper()}") from e


class ArianeFileType(BaseEnum):
    TML = 0
    TMLU = 1


class UnitType(BaseEnum):
    METRIC = 0
    IMPERIAL = 1


class ProfileType(BaseEnum):
    VERTICAL = 0


class ShotType(BaseEnum):
    REAL = 1
    VIRTUAL = 2
    START = 3
    CLOSURE = 4
