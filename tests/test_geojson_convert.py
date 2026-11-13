from __future__ import annotations

import hashlib
import os
import unittest
from typing import TYPE_CHECKING

import orjson
from deepdiff import DeepDiff
from parameterized import parameterized

from openspeleo_lib.colors import normalize_shot_color
from openspeleo_lib.geojson import MAX_GEOLOCATION_DISCREPANCY_M
from openspeleo_lib.geojson import InconsistentShotCoordinatesError
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.loop_closure.presets import (
    InverseLengthWeightedLeastSquaresHorizontalSolver,
)
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

        # Legacy goldens pin geometry and all pre-existing metadata. Verify
        # additive color metadata separately against the original source shots.
        shots_by_id = {shot.id_stop: shot for shot in survey.shots}
        for feature in geojson_new["features"]:
            shot = shots_by_id[feature["properties"]["id"]]
            expected_color = (
                normalize_shot_color(shot.color)
                if "color" in shot.model_fields_set
                else None
            )
            assert feature["properties"].pop("color", None) == expected_color

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

    @parameterized.expand(
        sorted(
            path.with_suffix("")
            for path in PRIVATE_ARIANE_DATA_DIR.glob("*.tml.encrypted")
        )
    )
    def test_convert_to_geojson_inverse_length_weighted_horizontal(
        self, filepath: Path
    ):
        solver = InverseLengthWeightedLeastSquaresHorizontalSolver
        golden = filepath.with_name(f"{filepath.stem}-{solver.name}.geojson")
        if not filepath.exists() and not os.environ.get("ARTIFACT_ENCRYPTION_KEY"):
            self.skipTest("Private fixtures require ARTIFACT_ENCRYPTION_KEY")
        survey = ArianeInterface.from_file(filepath)
        before = hashlib.sha256(survey.model_dump_json().encode()).digest()
        try:
            converted = survey_to_geojson(
                survey,
                loop_closure_solver=solver,
            )
        except InconsistentShotCoordinatesError as error:
            assert_invalid_coordinate_rejection(error)
            assert not golden.with_suffix(".geojson.encrypted").exists()
            return
        except Exception as error:  # noqa: BLE001 - never print private survey details
            raise AssertionError(
                f"{filepath.name}: weighted horizontal export failed "
                f"({type(error).__name__}); survey data omitted"
            ) from None
        finally:
            after = hashlib.sha256(survey.model_dump_json().encode()).digest()
            assert after == before, "Loop closure changed the input survey"
        if not golden.exists() and not os.environ.get("ARTIFACT_ENCRYPTION_KEY"):
            self.skipTest("Private goldens require ARTIFACT_ENCRYPTION_KEY")
        actual = orjson.dumps(converted, option=orjson.OPT_SORT_KEYS)
        if actual != golden.read_bytes():
            raise AssertionError(f"{golden.name}: weighted horizontal golden differs")
