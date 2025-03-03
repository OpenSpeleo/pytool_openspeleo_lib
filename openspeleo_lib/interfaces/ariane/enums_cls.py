#!/usr/bin/env python

from enum import IntEnum
from pathlib import Path
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

    @classmethod
    def from_path(cls, filepath: Path | str) -> Self:
        filepath = Path(filepath)

        try:
            return cls.from_str(filepath.suffix[1:])

        except ValueError as e:
            raise TypeError(e) from e


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
