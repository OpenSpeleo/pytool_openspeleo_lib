import tempfile
import unittest
from pathlib import Path
from typing import TYPE_CHECKING

from parameterized import parameterized_class

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
    def test_roundtrip(self):
        file = Path(self.filepath)

        if not file.exists():
            raise FileNotFoundError(f"File not found: `{file}`")

        # original_data = ArianeInterface._from_file(file)

        survey: Survey = ArianeInterface.from_file(file)

        with tempfile.TemporaryDirectory() as name:
            target_f = Path(name) / "SurveyRoundTrip.tml"
            ArianeInterface.to_file(survey=survey, filepath=target_f)

            # round_trip_data = ArianeInterface.from_file(target_f)

            # assert compute_filehash(file) == compute_filehash(target_f)

        # ddiff = DeepDiff(
        #     survey.model_dump_json(sort_keys=True), round_trip_data, ignore_order=True
        # )
        # assert ddiff == {}, ddiff


if __name__ == "__main__":
    unittest.main()
