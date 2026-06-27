from __future__ import annotations

import unittest
from typing import TYPE_CHECKING

import orjson
from deepdiff import DeepDiff
from parameterized import parameterized

from openspeleo_lib.geojson import MAX_GEOLOCATION_DISCREPANCY_M
from openspeleo_lib.geojson import InconsistentShotCoordinatesError
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from tests.conftest import PRIVATE_ARIANE_DATA_DIR

if TYPE_CHECKING:
    from pathlib import Path

DEBUG = False


def assert_invalid_coordinate_rejection(error: InconsistentShotCoordinatesError):
    assert error.shot.id_stop >= 0
    assert error.discrepancy_m > MAX_GEOLOCATION_DISCREPANCY_M
    assert str(error).startswith(f"[Shot ID={error.shot.id_stop}]")


class TestConvertToGeoJson(unittest.TestCase):
    @parameterized.expand(sorted(PRIVATE_ARIANE_DATA_DIR.glob("*.tml")))
    def test_convert_to_geojson(self, filepath: Path):
        survey = ArianeInterface.from_file(filepath)
        try:
            geojson_new = survey_to_geojson(survey)
        except InconsistentShotCoordinatesError as error:
            # Invalid private surveys have no valid golden GeoJSON conversion.
            assert_invalid_coordinate_rejection(error)
            return

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
        )
        assert ddiff == {}, ddiff
