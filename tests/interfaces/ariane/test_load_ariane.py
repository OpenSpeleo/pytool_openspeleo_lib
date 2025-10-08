from __future__ import annotations

import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import xmltodict
from deepdiff import DeepDiff
from parameterized import parameterized_class

from openspeleo_lib.interfaces.ariane.interface import ArianeInterface

if TYPE_CHECKING:
    from openspeleo_lib.models import Survey


@parameterized_class(
    ("filepath",),
    [
        ("tests/artifacts/hand_survey.tml",),
        ("tests/artifacts/test_simple.mini.tml",),
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


class TestLoadTMLUFile(unittest.TestCase):
    filepath = None

    def test_load_ariane_file(self):
        file = Path("tests/artifacts/test_simple.tmlu")
        with pytest.raises(TypeError, match="Unsupported fileformat: `TMLU`"):
            _ = ArianeInterface.from_file(filepath=file)


@parameterized_class(
    ("filepath"),
    [
        ("tests/artifacts/hand_survey.tml",),
        ("tests/artifacts/test_simple.mini.tml",),
        ("tests/artifacts/test_simple.tml",),
        # ("tests/artifacts/test_simple.tmlu",),
        ("tests/artifacts/test_with_walls.tml",),
        ("tests/artifacts/test_large.tml",),
    ],
)
class TestTMLRoundTrip(unittest.TestCase):
    def test_roundtrip(self):
        file = Path(self.filepath)

        if not file.exists():
            raise FileNotFoundError(f"File not found: `{file}`")

        survey: Survey = ArianeInterface.from_file(file)

        with tempfile.TemporaryDirectory() as name:
            target_f = Path(name) / "SurveyRoundTrip.tml"
            ArianeInterface.to_file(survey=survey, filepath=target_f)

            # Verifying the XML Data is the same
            with zipfile.ZipFile(file, "r") as zip_file:
                original_xml_data = xmltodict.parse(zip_file.open("Data.xml").read())

            # with zipfile.ZipFile(file, "r") as zip_file:
            #     with (file.parent / "test.source.xml").open("w") as f:
            #         f.write(zip_file.open("Data.xml").read().decode("utf-8"))

            # with (file.parent / "test_simple.source.mini.json").open("w") as f:
            #     f.write(json.dumps(original_xml_data, indent=2, sort_keys=True))

            with zipfile.ZipFile(target_f, "r") as zip_file:
                round_trip_xml_data = xmltodict.parse(zip_file.open("Data.xml").read())

            # with zipfile.ZipFile(target_f, "r") as zip_file:
            #     with (file.parent / "test.dest.xml").open("w") as f:
            #         f.write(zip_file.open("Data.xml").read().decode("utf-8"))

            # with (file.parent / "test_simple.dest.mini.json").open("w") as f:
            #     f.write(json.dumps(round_trip_xml_data, indent=2, sort_keys=True))

            ddiff = DeepDiff(
                original_xml_data,
                round_trip_xml_data,
                ignore_order=True,
                exclude_regex_paths=[
                    re.escape("root['CaveFile']['speleodb_id']"),
                    re.escape(
                        "root['CaveFile']['Data']['SurveyData'][*]['Name']"
                    ).replace(r"\*", r"\d+"),
                ],
            )
            assert ddiff == {}, ddiff

            # Verifying the JSON Data is the same
            original_data = json.dumps(
                survey.model_dump(mode="json"), sort_keys=True, indent=2
            )

            round_trip_survey = ArianeInterface.from_file(target_f)
            round_trip_data = json.dumps(
                round_trip_survey.model_dump(mode="json"), sort_keys=True, indent=2
            )

            ddiff = DeepDiff(original_data, round_trip_data, ignore_order=True)
            assert ddiff == {}, ddiff


if __name__ == "__main__":
    unittest.main()
