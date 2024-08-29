import hashlib
import tempfile
import unittest
from pathlib import Path

from deepdiff import DeepDiff
from parameterized import parameterized
from parameterized import parameterized_class

from openspeleo_lib.formats.ariane.interface import ArianeInterface
from openspeleo_lib.generators import UniqueNameGenerator


@parameterized_class(
    ("filepath", "is_debug"),
    [
        # ("artifacts/hand_survey.tml",),
        ("tests/artifacts/hand_survey.tml", True),
        ("tests/artifacts/hand_survey.tml", False),
        ("tests/artifacts/test_simple.tml", False),
        # ("tests/artifacts/test_simple.tmlu",),
        ("tests/artifacts/test_with_walls.tml", False),
        ("tests/artifacts/test_large.tml", False)
    ]
)
class TestLoadTMLFile(unittest.TestCase):

    def setUp(self) -> None:
        # Clear already used names
        UniqueNameGenerator._used_values.clear()  # noqa: SLF001

    def test_load_ariane_file(self):
        file = Path(self.filepath)
        _ = ArianeInterface.from_file(filepath=file, debug=self.is_debug)


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

    @parameterized.expand([True, False])
    def test_roundtrip(self, debug: bool):

        def compute_filehash(filepath: Path) -> str:
            with filepath.open(mode="rb") as f:
                binary_data = f.read()
            return hashlib.sha256(binary_data).hexdigest()

        file = Path(self.filepath)

        if not file.exists():
            raise FileNotFoundError(f"File not found: `{file}`")

        original_hash = compute_filehash(file)
        original_data = ArianeInterface._load_from_file(file, debug=debug)  # noqa: SLF001

        interface = ArianeInterface.from_file(file)

        with tempfile.TemporaryDirectory() as name:
            target_f = Path(name) / "SurveyRoundTrip.tml"
            interface.to_file(filepath=target_f, debug=debug)

            round_trip_data = ArianeInterface._load_from_file(target_f, debug=debug)  # noqa: SLF001
            roundtrip_hash = compute_filehash(file)

        ddiff = DeepDiff(
            original_data,
            round_trip_data,
            ignore_order=True
        )
        assert ddiff == {}, ddiff

        assert original_hash == roundtrip_hash


if __name__ == "__main__":
    unittest.main()
