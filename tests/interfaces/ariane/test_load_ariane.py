import hashlib
import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

from deepdiff import DeepDiff
from parameterized import parameterized_class

from openspeleo_lib.generators import UniqueNameGenerator
from openspeleo_lib.interfaces.ariane.interface import ArianeInterface

if TYPE_CHECKING:
    from openspeleo_lib.models import Survey


@parameterized_class(
    ("filepath",),
    [
        # ("artifacts/hand_survey.tml",),
        ("tests/artifacts/hand_survey.tml",),
        ("tests/artifacts/hand_survey.tml",),
        ("tests/artifacts/test_simple.tml",),
        # ("tests/artifacts/test_simple.tmlu",),
        ("tests/artifacts/test_with_walls.tml",),
        ("tests/artifacts/test_large.tml",),
    ],
)
class TestLoadTMLFile(unittest.TestCase):
    filepath = None

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

    def test_load_ariane_file(self):
        file = Path(self.filepath)
        _ = ArianeInterface.from_file(filepath=file)


@parameterized_class(
    ("filepath"),
    [
        # ("artifacts/hand_survey.tml",),
        ("tests/artifacts/hand_survey.tml",),
    ],
)
class TestTMLRoundTrip(unittest.TestCase):
    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

    def test_roundtrip(self):
        def compute_filehash(filepath: Path) -> str:
            with filepath.open(mode="rb") as f:
                binary_data = f.read()
            return hashlib.sha256(binary_data).hexdigest()

        file = Path(self.filepath)

        if not file.exists():
            raise FileNotFoundError(f"File not found: `{file}`")

        original_hash = compute_filehash(file)
        original_data = ArianeInterface._load_from_file(file)  # noqa: SLF001

        survey: Survey = ArianeInterface.from_file(file)

        with tempfile.TemporaryDirectory() as name:
            target_f = Path(name) / "SurveyRoundTrip.tml"
            ArianeInterface.to_file(survey=survey, filepath=target_f)

            round_trip_data = ArianeInterface._load_from_file(target_f)  # noqa: SLF001
            roundtrip_hash = compute_filehash(file)

        ddiff = DeepDiff(original_data, round_trip_data, ignore_order=True)
        assert ddiff == {}, ddiff

        assert original_hash == roundtrip_hash


if __name__ == "__main__":
    unittest.main()
