from __future__ import annotations

import unittest
from contextlib import nullcontext

import pytest

from openspeleo_lib.constants import OSPL_MAX_RETRY_ATTEMPTS
from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.errors import DuplicateValueError
from openspeleo_lib.generators import UniqueValueGenerator


@pytest.mark.parametrize("inner_failure", [False, True])
def test_nested_uniqueness_restores_outer_registry(inner_failure):
    def register_inner():
        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator.register(vartype=int, value=100)
            UniqueValueGenerator.register(vartype=int, value=200)
            if inner_failure:
                raise ValueError("inner failure")

    with UniqueValueGenerator.activate_uniqueness():
        UniqueValueGenerator.register(vartype=int, value=100)
        expected = (
            pytest.raises(ValueError, match="inner failure")
            if inner_failure
            else nullcontext()
        )
        with expected:
            register_inner()
        with pytest.raises(DuplicateValueError, match="already been registered"):
            UniqueValueGenerator.register(vartype=int, value=100)
        UniqueValueGenerator.register(vartype=int, value=200)


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
        UniqueValueGenerator.register(vartype=str, value=name)

        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator.register(vartype=str, value=name)

            with pytest.raises(
                DuplicateValueError, match="has already been registered"
            ):
                UniqueValueGenerator.register(vartype=str, value=name)

    def test_prevent_duplicate_name_generation(self):
        name = "UNIQUE2"

        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator.register(vartype=str, value=name)
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
            with pytest.raises(DuplicateValueError):
                UniqueValueGenerator.register(vartype=str, value=name)

        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator.register(vartype=str, value=name)


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
        UniqueValueGenerator.register(vartype=int, value=id_val)

        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator.register(vartype=int, value=id_val)

            with pytest.raises(
                DuplicateValueError,
                match="has already been registered",
            ):
                UniqueValueGenerator.register(vartype=int, value=id_val)

    def test_prevent_duplicate_id_generation(self):
        id_val = 1
        with UniqueValueGenerator.activate_uniqueness():
            UniqueValueGenerator.register(vartype=int, value=id_val)
            generated_id = UniqueValueGenerator.get(vartype=int)
            assert generated_id != id_val


if __name__ == "__main__":
    unittest.main()
