import random
import re

from openspeleo_lib.errors import DuplicateNameError


class UniqueNameGenerator:
    VOCAB = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    _used_names = set()

    @classmethod
    def get(cls, str_len=6):
        while True:
            name = "".join(random.choices(cls.VOCAB, k=str_len))
            if name in cls._used_names:
                continue
            cls._used_names.add(name)
            return name

    @classmethod
    def register(cls, name):
        if name in cls._used_names:
            raise DuplicateNameError(f"Name `{name}` has already been allocated.")
        cls._used_names.add(name)


# def camel2snakecase(value: str) -> str:
#     # Breaks on uppercase letters or the start of a sequence of digits
#     return re.sub(r"(?<!^)(?=[A-Z])|(?<=\D)(?=\d)", "_", value).lower()
def camel2snakecase(value: str) -> str:
    # Breaks before sequences of uppercase letters (but not for acronyms) or digits
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])|(?<=\D)(?=\d)', '_', value).lower()

def snake2camelcase(value: str) -> str:
    first, *others = value.split("_")
    return "".join([first.lower(), *map(str.title, others)])

def str2bool(value: str) -> bool:
    """
    Convert a string or integer value to a boolean.
    Accepts common string representations and integers.
    Returns True or False based on the input.
    Raises ValueError if the input cannot be converted to a boolean.
    """

    if isinstance(value, str):
        value = value.strip().lower()

        if value in {"true", "t", "yes", "y", "1", "on"}:
            return True

        if value in {"false", "f", "no", "n", "0", "off"}:
            return False

    raise ValueError(f"Cannot convert {value!r} to boolean")
