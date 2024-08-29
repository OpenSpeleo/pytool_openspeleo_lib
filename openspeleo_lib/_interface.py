from abc import ABCMeta
from abc import abstractmethod
from pathlib import Path
from typing import Self

from openspeleo_lib.models import Survey


class BaseInterface(metaclass=ABCMeta):
    def __init__(self, survey: Survey) -> None:
        self._survey = survey

    @property
    def survey(self):
        return self._survey

    @property
    def survey_data(self):
        return self.survey.model_dump()

    @abstractmethod
    def to_file(self, filepath: Path, debug: bool = False) -> None:
        raise NotImplementedError  # pragma: no cover

    @classmethod
    @abstractmethod
    def from_file(cls, filepath: Path, debug: bool = False) -> Self:
        raise NotImplementedError  # pragma: no cover
