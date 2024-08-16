import random


class DuplicateNameError(ValueError):
    pass


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
