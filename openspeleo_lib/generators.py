from __future__ import annotations

import contextlib
import random
from collections import defaultdict
from typing import Any
from typing import NewType

from openspeleo_lib.constants import OSPL_MAX_RETRY_ATTEMPTS
from openspeleo_lib.constants import OSPL_SHOTNAME_DEFAULT_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.errors import DuplicateValueError
from openspeleo_lib.errors import MaxRetriesError


class UniqueValueGenerator:
    _used_values = None
    VOCAB = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    def __init__(self):
        raise NotImplementedError("This class should not be instantiated.")

    @classmethod
    @contextlib.contextmanager
    def activate_uniqueness(cls):
        try:
            cls._used_values = defaultdict(set)
            yield
        finally:
            cls._used_values = None

    @classmethod
    def register(cls, vartype: type, value: Any) -> None:
        """Register the generated value."""
        if cls._used_values is None:  # uniqueness is not activated
            return

        value = vartype(value)

        if value in cls._used_values[vartype]:
            raise DuplicateValueError(
                f"Value `{value}` for type `{vartype}` has already been registered."
            )

        cls._used_values[vartype].add(value)

    @classmethod
    def get(cls, vartype: type, **kwargs) -> Any:
        """Get unique value for an object primary key."""
        iter_idx = 0
        while True:
            iter_idx += 1
            if iter_idx > OSPL_MAX_RETRY_ATTEMPTS:
                raise MaxRetriesError(
                    "Impossible to find an available value to use. "
                    "Max retry attempts reached: "
                    f"{OSPL_MAX_RETRY_ATTEMPTS}"
                )
            try:
                if vartype is str or (
                    isinstance(vartype, NewType) and vartype.__supertype__ is str
                ):
                    value = cls._generate_str(**kwargs)

                elif vartype is int or (
                    isinstance(vartype, NewType) and vartype.__supertype__ is int
                ):
                    value = cls._generate_int(
                        known_values=(
                            cls._used_values[vartype] if cls._used_values else []
                        )
                    )
                else:
                    raise TypeError(f"Unsupported type: `{vartype}`")

                cls.register(vartype=vartype, value=value)
                break
            except DuplicateValueError:
                continue

        return value

    @classmethod
    def _generate_str(cls, str_len: int = OSPL_SHOTNAME_DEFAULT_LENGTH) -> str:
        if str_len > OSPL_SHOTNAME_MAX_LENGTH:
            raise ValueError(
                f"Maximum length allowed: {OSPL_SHOTNAME_MAX_LENGTH}, received: {str_len}"  # noqa: E501
            )
        return "".join(random.choices(cls.VOCAB, k=str_len))

    @classmethod
    def _generate_int(cls, known_values: list[int] | set[int]) -> str:
        return max(known_values, default=0) + 1
