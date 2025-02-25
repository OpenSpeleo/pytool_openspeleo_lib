from pathlib import Path
from typing import Annotated
from typing import Any
from typing import Self

import orjson
from iteration_utilities import duplicates
from pydantic import NonNegativeInt
from pydantic import StringConstraints
from pydantic import model_validator

from openspeleo_lib.constants import OSPL_MAX_NAME_LENGTH
from openspeleo_lib.constants import OSPL_MIN_NAME_LENGTH
from openspeleo_lib.errors import DuplicateValueError
from openspeleo_lib.generators import UniqueValueGenerator


class BaseMixin:
    @model_validator(mode="before")
    @classmethod
    def enforce_snake_and_remove_none(cls, data: dict) -> dict:
        return {k: v for k, v in data.items() if v is not None}

    def to_json(self, filepath: str | Path) -> None:
        """
        Serializes the model to a JSON file.

        Args:
            filepath (str | Path): The filepath where the JSON data will be written.

        Returns:
            None
        """
        with Path(filepath).open(mode="w") as f:
            f.write(
                orjson.dumps(
                    self.model_dump(mode="json"),
                    None,
                    option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
                ).decode("utf-8")
            )

    @classmethod
    def from_json(cls, filepath: str | Path) -> Self:
        with Path(filepath).open(mode="rb") as f:
            return cls.model_validate(orjson.loads(f.read()))

    # ======================== VALIDATOR UTILS ======================== #

    @classmethod
    def validate_unique(cls, field: str, values: list) -> list:
        vals2check = [getattr(val, field) for val in values]
        dupl_vals = list(duplicates(vals2check))
        if dupl_vals:
            raise DuplicateValueError(
                f"[{cls.__name__}] Duplicate value found for `{field}`: {dupl_vals}"
            )
        return values


class AutoIdModelMixin:
    id: NonNegativeInt = None

    @model_validator(mode="before")
    @classmethod
    def clean_input_args(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values.get("id") == "":  # empty `id` is not allowed
            del values["id"]
        return values

    @model_validator(mode="after")
    def validate_id_uniqueness(self) -> Self:
        if self.id is None:
            self.id = UniqueValueGenerator.get(vartype=int)
        else:
            UniqueValueGenerator.register(vartype=int, value=self.id)
        return self


class NameIdModelMixin:
    name_compass: Annotated[
        str,
        StringConstraints(
            pattern=rf"^[a-zA-Z0-9_\-~:!?.'\(\)\[\]\{{\}}@*&#%|$]{{{OSPL_MIN_NAME_LENGTH},{OSPL_MAX_NAME_LENGTH}}}$",
            to_upper=True,
        ),
    ] = None

    @model_validator(mode="before")
    @classmethod
    def clean_input_args(cls, values: dict[str, Any]) -> dict[str, Any]:
        if values.get("name_compass") == "":  # empty `name_compass` is not allowed
            del values["name_compass"]
        return values

    @model_validator(mode="after")
    def validate_name_compass_uniqueness(self) -> Self:
        if self.name_compass is None:
            self.name_compass = UniqueValueGenerator.get(vartype=str)
        else:
            UniqueValueGenerator.register(vartype=str, value=self.name_compass)
        return self
