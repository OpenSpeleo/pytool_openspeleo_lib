import unittest

from openspeleo_lib.errors import DuplicateNameError
from openspeleo_lib.utils import UniqueNameGenerator


class TestUniqueNameGenerator(unittest.TestCase):

    def setUp(self):
        # Clear used names before each test
        self._reset_used_names()

    @staticmethod
    def _reset_used_names():
        UniqueNameGenerator._used_names.clear()  # noqa: SLF001

    def test_generate_unique_name(self):
        names = set()
        for _ in range(100):
            name = UniqueNameGenerator.get()
            if name in names:
                raise AssertionError(f"{name} should be unique.")
            names.add(name)

    def test_register_name(self):
        name = "UNIQUE1"
        UniqueNameGenerator.register(name)
        if name not in UniqueNameGenerator._used_names:  # noqa: SLF001
            raise AssertionError(f"{name} should be registered.")

        try:
            UniqueNameGenerator.register(name)
        except DuplicateNameError:
            pass
        else:
            raise AssertionError("DuplicateNameError was not raised when expected.")

    def test_prevent_duplicate_name_generation(self):
        name = "UNIQUE2"
        UniqueNameGenerator._used_names.add(name)  # noqa: SLF001
        generated_name = UniqueNameGenerator.get()
        if generated_name == name:
            raise AssertionError(f"{generated_name} should not be generated again.")

    def test_generate_name_with_different_length(self):
        for length in range(1, 10):
            name = UniqueNameGenerator.get(str_len=length)
            if len(name) != length:
                raise AssertionError(
                    f"Generated name {name} does not have the expected length {length}."
                )

    def test_reset_used_names(self):
        name = UniqueNameGenerator.get()
        if name not in UniqueNameGenerator._used_names:  # noqa: SLF001
            raise AssertionError(f"{name} should be in the used names set.")

        self._reset_used_names()
        new_name = UniqueNameGenerator.get()

        if name in UniqueNameGenerator._used_names:  # noqa: SLF001
            raise AssertionError(f"{name} should have been cleared from used names.")

        if name == new_name:
            raise AssertionError(
                f"The new name {new_name} should be different from the previous name "
                f"{name}."
            )

if __name__ == "__main__":
    unittest.main()
