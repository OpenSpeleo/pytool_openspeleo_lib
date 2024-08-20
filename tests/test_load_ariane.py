import unittest
from pathlib import Path

from parameterized import parameterized_class

from openspeleo_lib.types import Survey


@parameterized_class(
    ("filepath"),
    [
        ("tests/artifacts/test_simple.tml",),
        # ("tests/artifacts/test_simple.tmlu",),
        ("tests/artifacts/test_with_walls.tml",),
        ("tests/artifacts/test_large.tml",)
    ]
)
class TestSurvey(unittest.TestCase):

    # def setUp(self):
    #     # Clear used names before each test
    #     self._reset_used_names()

    def test_load_ariane_file(self):
        file = Path(self.filepath)
        Survey.from_ariane_file(filepath=file)


if __name__ == "__main__":
    unittest.main()
