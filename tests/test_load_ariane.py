import hashlib
import tempfile
import unittest
from pathlib import Path

from ariane_lib.parser import ArianeParser
from deepdiff import DeepDiff
from parameterized import parameterized_class

from openspeleo_lib.types import Survey
from openspeleo_lib.utils import UniqueNameGenerator


@parameterized_class(
    ("filepath"),
    [
        ("tests/artifacts/hand_survey.tml",),
        ("tests/artifacts/test_simple.tml",),
        # ("tests/artifacts/test_simple.tmlu",),
        ("tests/artifacts/test_with_walls.tml",),
        ("tests/artifacts/test_large.tml",)
    ]
)
class TestLoadTMLFile(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_names.clear()  # noqa: SLF001

    def test_load_ariane_file(self):
        file = Path(self.filepath)
        Survey.from_ariane_file(filepath=file)


@parameterized_class(
    ("filepath"),
    [
        ("tests/artifacts/hand_survey.tml",),
    ]
)
class TestTMLRoundTrip(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_names.clear()  # noqa: SLF001

    def test_json_roundtrip(self):
        file = Path(self.filepath)

        if not file.exists():
            raise FileNotFoundError(f"File not found: `{file}`")

        survey = ArianeParser(file)

        original_data = survey.data

        pydantic_survey = Survey.from_ariane(original_data)

        round_trip_data = pydantic_survey.to_ariane()

        ddiff = DeepDiff(original_data, round_trip_data, ignore_order=True)

        assert ddiff == {}

    def test_sha256_roundtrip(self):
        file = Path(self.filepath)

        def compute_filehash(filepath: Path) -> str:
            with filepath.open(mode="rb") as f:
                binary_data = f.read()
            return hashlib.sha256(binary_data).hexdigest()

        original_hash = compute_filehash(file)

        survey = Survey.from_ariane_file(filepath=file)

        with tempfile.TemporaryDirectory() as name:
            target_f = Path(name) / "Survey.tml"
            survey.to_ariane_file(target_f)

            roundtrip_hash = compute_filehash(file)

        assert original_hash == roundtrip_hash


if __name__ == "__main__":
    unittest.main()
