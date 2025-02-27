import unittest

import pytest

from openspeleo_lib.constants import OSPL_MAX_RETRY_ATTEMPTS
from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.errors import DuplicateValueError
from openspeleo_lib.generators import UniqueValueGenerator


class TestUniqueNameGenerator(unittest.TestCase):
    def test_generate_unique_name(self):
        with UniqueValueGenerator.activate_uniqueness():
            names = set()
            for _ in range(OSPL_MAX_RETRY_ATTEMPTS):
                name = UniqueValueGenerator.get(vartype=str)
                assert name not in names
                names.add(name)

    def test_register_name(self):
        name = "UNIQUE1"

        # Without active context
        UniqueValueGenerator.register(vartype=str, value=name)
        assert UniqueValueGenerator._used_values is None  # noqa: SLF001

        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator.register(vartype=str, value=name)
            assert name in UniqueValueGenerator._used_values[str]  # noqa: SLF001

            with pytest.raises(
                DuplicateValueError, match="has already been registered."
            ):
                UniqueValueGenerator.register(vartype=str, value=name)

    def test_prevent_duplicate_name_generation(self):
        name = "UNIQUE2"

        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator._used_values[str].add(name)  # noqa: SLF001
            generated_name = UniqueValueGenerator.get(vartype=str)
            assert generated_name != name

    def test_generate_name_too_long(self):
        with pytest.raises(
            ValueError,
            match=(
                f"Maximum length allowed: {OSPL_SHOTNAME_MAX_LENGTH}, "
                f"received: {OSPL_SHOTNAME_MAX_LENGTH + 1}"
            ),
        ):
            _ = UniqueValueGenerator.get(
                vartype=str, str_len=OSPL_SHOTNAME_MAX_LENGTH + 1
            )

    def test_generate_name_with_different_length(self):
        for length in range(1, OSPL_SHOTNAME_MAX_LENGTH + 1):
            name = UniqueValueGenerator.get(vartype=str, str_len=length)
            assert len(name) == length

    def test_reset_used_values(self):
        with UniqueValueGenerator.activate_uniqueness():
            name = UniqueValueGenerator.get(vartype=str)
            assert name in UniqueValueGenerator._used_values[str]  # noqa: SLF001

        with UniqueValueGenerator.activate_uniqueness():
            new_name = UniqueValueGenerator.get(vartype=str)
            assert new_name in UniqueValueGenerator._used_values[str]  # noqa: SLF001
            assert name not in UniqueValueGenerator._used_values[str]  # noqa: SLF001


class TestUniqueIDGenerator(unittest.TestCase):
    def test_generate_unique_id(self):
        with UniqueValueGenerator.activate_uniqueness():
            ids = set()
            for target in range(1, OSPL_MAX_RETRY_ATTEMPTS + 1):
                id_val = UniqueValueGenerator.get(vartype=int)
                assert id_val not in ids
                assert id_val == target
                ids.add(id_val)

    def test_register_id(self):
        id_val = "1234"
        UniqueValueGenerator.register(vartype=int, value=id_val)
        assert UniqueValueGenerator._used_values is None  # noqa: SLF001

        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator.register(vartype=int, value=id_val)
            assert int(id_val) in UniqueValueGenerator._used_values[int]  # noqa: SLF001

            with pytest.raises(
                DuplicateValueError,
                match="has already been registered.",
            ):
                UniqueValueGenerator.register(vartype=int, value=id_val)

    def test_prevent_duplicate_id_generation(self):
        id_val = 1
        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator._used_values[int].add(id_val)  # noqa: SLF001
            generated_id = UniqueValueGenerator.get(vartype=int)
            assert generated_id != id_val


if __name__ == "__main__":
    unittest.main()
