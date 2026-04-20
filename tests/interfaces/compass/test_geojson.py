"""GeoJSON export tests for Compass data.

These tests verify that Compass surveys can be exported to valid GeoJSON
with proper coordinate propagation.
"""

from __future__ import annotations

import unittest
from pathlib import Path

import pytest

from tests.conftest import COMPASS_WITH_GEOJSON
from tests.conftest import PRIVATE_COMPASS_DATA_DIR
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces.compass.interface import CompassInterface


@pytest.mark.skipif(
    not PRIVATE_COMPASS_DATA_DIR.exists(),
    reason="Private Compass data directory not found",
)
class TestCompassToGeoJSON:
    """Test GeoJSON export from Compass-sourced OSPL surveys."""

    @pytest.mark.parametrize("mak_path,geojson_path", COMPASS_WITH_GEOJSON)
    def test_geojson_generation(self, mak_path: Path, geojson_path: Path) -> None:
        """Test that GeoJSON can be generated from a Compass file."""

        survey = CompassInterface.from_file(mak_path)

        # This should not raise
        geojson = survey_to_geojson(survey)

        # Basic structure validation
        assert geojson["type"] == "FeatureCollection"
        assert "features" in geojson

    @pytest.mark.parametrize("mak_path,geojson_path", COMPASS_WITH_GEOJSON)
    def test_geojson_has_features(self, mak_path: Path, geojson_path: Path) -> None:
        """Test that generated GeoJSON has features."""

        survey = CompassInterface.from_file(mak_path)
        geojson = survey_to_geojson(survey)

        # Should have at least one feature
        assert len(geojson["features"]) > 0

    @pytest.mark.parametrize("mak_path,geojson_path", COMPASS_WITH_GEOJSON)
    def test_geojson_coordinates_valid(self, mak_path: Path, geojson_path: Path) -> None:
        """Test that GeoJSON coordinates are in valid WGS84 ranges."""

        survey = CompassInterface.from_file(mak_path)
        geojson = survey_to_geojson(survey)

        for feature in geojson["features"]:
            geom = feature["geometry"]
            geom_type = geom["type"]
            coords = geom["coordinates"]

            if geom_type == "Point":
                lon, lat = coords[0], coords[1]
                assert -180 <= lon <= 180, f"Invalid longitude: {lon}"
                assert -90 <= lat <= 90, f"Invalid latitude: {lat}"

            elif geom_type == "LineString":
                for coord in coords:
                    lon, lat = coord[0], coord[1]
                    assert -180 <= lon <= 180, f"Invalid longitude: {lon}"
                    assert -90 <= lat <= 90, f"Invalid latitude: {lat}"


class TestGeoJSONStructure(unittest.TestCase):
    """Test GeoJSON structure from Compass surveys."""

    @pytest.mark.skipif(
        not PRIVATE_COMPASS_DATA_DIR.exists(),
        reason="Private Compass data directory not found",
    )
    def test_geojson_feature_types(self) -> None:
        """Test that GeoJSON features have valid types."""

        mak_files = list(PRIVATE_COMPASS_DATA_DIR.glob("*.mak"))
        if not mak_files:
            pytest.skip("No MAK files found")

        mak_path = mak_files[0]
        survey = CompassInterface.from_file(mak_path)
        geojson = survey_to_geojson(survey)

        valid_types = {"Point", "LineString", "Polygon"}
        for feature in geojson["features"]:
            geom_type = feature["geometry"]["type"]
            assert geom_type in valid_types, f"Invalid geometry type: {geom_type}"


if __name__ == "__main__":
    unittest.main()
