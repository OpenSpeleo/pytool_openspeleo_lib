"""Tests for Compass decoding logic."""

from __future__ import annotations

import math
import unittest

from openspeleo_lib.geojson import calculate_depth_from_inclination
from openspeleo_lib.interfaces.compass.station_mapper import StationMapper


class TestCalculateDepthFromInclination(unittest.TestCase):
    """Tests for depth calculation from inclination.

    Note: Depth calculation is now performed during GeoJSON coordinate
    propagation via calculate_depth_from_inclination().
    """

    def test_horizontal_shot_no_depth_change(self):
        """Test that a horizontal shot (0° inclination) has no depth change."""
        depth = calculate_depth_from_inclination(
            origin_depth=0.0,
            length=10.0,
            inclination=0.0,
        )
        self.assertAlmostEqual(depth, 0.0, places=5)

    def test_downward_shot(self):
        """Test that a downward shot (-45°) increases depth (goes down)."""
        depth = calculate_depth_from_inclination(
            origin_depth=0.0,
            length=10.0,
            inclination=-45.0,  # 45 degrees down
        )
        # sin(-45°) ≈ -0.707, so depth = 0 + 10 * -0.707 ≈ -7.07
        self.assertAlmostEqual(depth, -7.071, places=2)

    def test_upward_shot(self):
        """Test that an upward shot (+45°) increases depth (goes up)."""
        depth = calculate_depth_from_inclination(
            origin_depth=0.0,
            length=10.0,
            inclination=45.0,  # 45 degrees up
        )
        # sin(45°) ≈ 0.707, so depth = 0 + 10 * 0.707 ≈ 7.07
        self.assertAlmostEqual(depth, 7.071, places=2)

    def test_vertical_down_shot(self):
        """Test that a vertical down shot (-90°) has full length as depth."""
        depth = calculate_depth_from_inclination(
            origin_depth=0.0,
            length=100.0,
            inclination=-90.0,
        )
        self.assertAlmostEqual(depth, -100.0, places=5)

    def test_vertical_up_shot(self):
        """Test that a vertical up shot (+90°) has full length as depth."""
        depth = calculate_depth_from_inclination(
            origin_depth=0.0,
            length=100.0,
            inclination=90.0,
        )
        self.assertAlmostEqual(depth, 100.0, places=5)

    def test_cumulative_depth(self):
        """Test that depths accumulate correctly."""
        # First shot: straight down
        depth1 = calculate_depth_from_inclination(
            origin_depth=0.0,
            length=10.0,
            inclination=-90.0,
        )
        self.assertAlmostEqual(depth1, -10.0, places=5)

        # Second shot: straight down from depth1
        depth2 = calculate_depth_from_inclination(
            origin_depth=depth1,
            length=10.0,
            inclination=-90.0,
        )
        self.assertAlmostEqual(depth2, -20.0, places=5)

    def test_origin_depth_offset(self):
        """Test that origin_depth is used correctly."""
        depth = calculate_depth_from_inclination(
            origin_depth=100.0,
            length=10.0,
            inclination=0.0,
        )
        self.assertAlmostEqual(depth, 100.0, places=5)

    def test_none_inclination_returns_origin(self):
        """Test that None inclination returns origin depth (horizontal)."""
        depth = calculate_depth_from_inclination(
            origin_depth=50.0,
            length=10.0,
            inclination=None,
        )
        self.assertAlmostEqual(depth, 50.0, places=5)


class TestDecodeShot(unittest.TestCase):
    """Tests for individual shot decoding."""

    def test_decode_shot_basic(self):
        """Test basic shot decoding."""
        from compass_lib.survey.models import CompassShot

        from openspeleo_lib.interfaces.compass.decoding import decode_shot

        mapper = StationMapper()

        compass_shot = CompassShot(
            from_station_name="A1",
            to_station_name="A2",
            length=10.5,
            frontsight_azimuth=45.0,
            frontsight_inclination=-5.0,
            left=2.0,
            right=3.0,
            up=1.0,
            down=4.0,
        )

        result = decode_shot(compass_shot, mapper)

        assert result["id_start"] == 0
        assert result["id_stop"] == 1
        assert result["name"] == "A2"
        assert result["length"] == 10.5
        assert result["azimuth"] == 45.0
        assert result["inclination"] == -5.0
        assert result["left"] == 2.0
        assert result["right"] == 3.0
        assert result["up"] == 1.0
        assert result["down"] == 4.0
        assert result["excluded"] is False
        assert result["shot_type"] == "REAL"

    def test_decode_shot_with_exclusion(self):
        """Test that exclusion flags are properly decoded."""
        from compass_lib.survey.models import CompassShot

        from openspeleo_lib.interfaces.compass.decoding import decode_shot

        mapper = StationMapper()

        compass_shot = CompassShot(
            from_station_name="A1",
            to_station_name="A2",
            length=10.0,
            excluded_from_all_processing=True,
        )

        result = decode_shot(compass_shot, mapper)
        assert result["excluded"] is True

    def test_decode_shot_truncates_long_names(self):
        """Test that station names are truncated to 50 chars."""
        from compass_lib.survey.models import CompassShot

        from openspeleo_lib.interfaces.compass.decoding import decode_shot

        mapper = StationMapper()
        long_name = "A" * 100

        compass_shot = CompassShot(
            from_station_name="A1",
            to_station_name=long_name,
            length=10.0,
        )

        result = decode_shot(compass_shot, mapper)
        assert len(result["name"]) == 50


if __name__ == "__main__":
    unittest.main()
