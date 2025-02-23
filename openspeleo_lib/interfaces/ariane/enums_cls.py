#!/usr/bin/env python

from enum import IntEnum


class ArianeFileType(IntEnum):
    TML = 0
    TMLU = 1

    @classmethod
    def from_str(cls, value):
        value = value.upper()
        match value:
            case "TML":
                return cls.TML
            case "TMLU":
                return cls.TMLU
            case _:
                raise ValueError(f"Unknown value: {value}")


class UnitType(IntEnum):
    METRIC = 0
    IMPERIAL = 1

    @classmethod
    def from_str(cls, value):
        value = value.upper()
        match value:
            case "M" | "METRIC":
                return cls.METRIC
            case "FT" | "IMPERIAL":
                return cls.IMPERIAL
            case _:
                raise ValueError(f"Unknown value: {value}")


class ProfileType(IntEnum):
    VERTICAL = 0

    @classmethod
    def from_str(cls, value):
        value = value.upper()
        match value:
            case "VERTICAL":
                return cls.VERTICAL
            case _:
                raise ValueError(f"Unknown value: {value}")


class ShotType(IntEnum):
    REAL = 1
    VIRTUAL = 2
    START = 3
    CLOSURE = 4

    @classmethod
    def from_str(cls, value):
        value = value.upper()
        match value:
            case "REAL":
                return cls.REAL
            case "VIRTUAL":
                return cls.VIRTUAL
            case "START":
                return cls.START
            case "CLOSURE":
                return cls.CLOSURE
            case _:
                raise ValueError(f"Unknown value: {value}")
