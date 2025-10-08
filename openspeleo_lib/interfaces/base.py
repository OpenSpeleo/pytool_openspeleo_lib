from __future__ import annotations

from abc import ABCMeta
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from openspeleo_lib.generators import UniqueValueGenerator

if TYPE_CHECKING:
    from openspeleo_lib.models import Survey


class BaseInterface(metaclass=ABCMeta):
    def __init__(self, *args, **kwargs) -> None:
        raise NotImplementedError(
            "This class is not meant to be instantiated directly."
        )

    @classmethod
    @abstractmethod
    def to_file(cls, survey: Survey, filepath: Path) -> None:
        raise NotImplementedError  # pragma: no cover

    @classmethod
    def from_file(cls, filepath: str | Path) -> Survey:
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: `{filepath}`")

        with UniqueValueGenerator.activate_uniqueness():
            return cls._from_file(filepath=filepath)

    @classmethod
    @abstractmethod
    def _from_file(cls, filepath: Path) -> Survey:
        raise NotImplementedError  # pragma: no cover
