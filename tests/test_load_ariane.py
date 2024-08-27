import hashlib
import tempfile
import unittest
from pathlib import Path

from deepdiff import DeepDiff
from parameterized import parameterized_class

from openspeleo_lib.formats.ariane.parser import ArianeParser
from openspeleo_lib.generators import UniqueNameGenerator
from openspeleo_lib.types import Survey


@parameterized_class(
    ("filepath"),
    [
        # ("artifacts/hand_survey.tml",),
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
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

    def test_load_ariane_file(self):
        file = Path(self.filepath)
        _ = Survey.from_ariane_file(filepath=file, debug=True)


@parameterized_class(
    ("filepath"),
    [
        # ("artifacts/hand_survey.tml",),
        ("tests/artifacts/hand_survey.tml",),
    ]
)
class TestTMLRoundTrip(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

    def test_json_roundtrip(self):
        file = Path(self.filepath)

        if not file.exists():
            raise FileNotFoundError(f"File not found: `{file}`")

        original_data = ArianeParser.from_ariane_file(file)

        pydantic_survey = Survey.from_ariane_dict(original_data)

        round_trip_data = pydantic_survey.to_ariane_dict()

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
