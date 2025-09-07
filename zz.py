#!/usr/bin/env python

# ruff: noqa: T201

import xmltodict
import time
from pathlib import Path

import re
import orjson, json, tempfile, zipfile
from deepdiff import DeepDiff

from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.models import Survey

if __name__ == "__main__":

    file = Path("tests/artifacts/test_simple.tml")

    survey: Survey = ArianeInterface.from_file(file)

    with tempfile.TemporaryDirectory() as name:
        target_f = Path(name) / "SurveyRoundTrip.tml"
        ArianeInterface.to_file(survey=survey, filepath=target_f)

        # Verifying the XML Data is the same
        with zipfile.ZipFile(file, "r") as zip_file:
            original_xml_data = xmltodict.parse(zip_file.open("Data.xml").read())

        with zipfile.ZipFile(target_f, "r") as zip_file:
            round_trip_xml_data = xmltodict.parse(zip_file.open("Data.xml").read())

        with (file.parent / "test.orig.json").open("w") as f:
            f.write(json.dumps(original_xml_data, indent=2, sort_keys=True))

        with (file.parent / "test.round.json").open("w") as f:
            f.write(json.dumps(round_trip_xml_data, indent=2, sort_keys=True))

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
