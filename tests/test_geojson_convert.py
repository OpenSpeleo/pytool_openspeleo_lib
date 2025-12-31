from __future__ import annotations

import re
import unittest
from pathlib import Path

import orjson
from deepdiff import DeepDiff
from parameterized import parameterized

from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface

DEBUG = False


class TestConvertToGeoJson(unittest.TestCase):
    @parameterized.expand(sorted(Path("tests/artifacts/private").glob("*.tml")))
    def test_convert_to_geojson(self, filepath: Path):
        survey = ArianeInterface.from_file(filepath)
        geojson_new = survey_to_geojson(survey)

        with (filepath.parent / f"{filepath.stem}.geojson").open(mode="rb") as f:
            geojson_original = orjson.loads(f.read())

        if DEBUG:
            with (filepath.parent / f"{filepath.stem}.new.geojson").open(
                mode="wb"
            ) as f:
                f.write(
                    orjson.dumps(
                        geojson_new,
                        None,
                        option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
                    )
                )

        ddiff = DeepDiff(
            geojson_original,
            # This is necessary in order to obtain a consistent sorting
            orjson.loads(
                orjson.dumps(
                    geojson_new,
                    None,
                    option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS),
                )
            ),
            ignore_order=True,
            exclude_regex_paths=[
                # Ignore the shot `UUID` field
                re.escape("root['features'][*]['properties']['uuid']").replace(
                    r"\*", r"\d+"
                ),
            ],
        )
        assert ddiff == {}, ddiff
