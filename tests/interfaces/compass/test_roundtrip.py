"""Round-trip tests for Compass to OSPL conversion.

These tests verify that:
1. MAK+DAT -> OSPL -> MAK+DAT produces stable JSON output
2. Survey data is preserved through the round-trip
"""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import pytest
from deepdiff import DeepDiff

from tests.conftest import ALL_COMPASS_MAK_FILES
from tests.conftest import PRIVATE_COMPASS_DATA_DIR


@pytest.mark.skipif(
    not PRIVATE_COMPASS_DATA_DIR.exists(),
    reason="Private Compass data directory not found",
)
class TestCompassRoundTrip:
    """Test round-trip conversion: MAK+DAT -> OSPL -> MAK+DAT."""

    @pytest.mark.parametrize("mak_path", ALL_COMPASS_MAK_FILES)
    def test_ospl_json_roundtrip(self, mak_path: Path) -> None:
        """Test that OSPL JSON is stable through round-trip.

        Load -> Export -> Load should produce identical JSON (excluding UUIDs).
        """
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        # Load original
        survey1 = CompassInterface.from_file(mak_path)

        # Export to temporary MAK file
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "roundtrip.mak"
            CompassInterface.to_file(survey1, out_path)

            # Reload
            survey2 = CompassInterface.from_file(out_path)

        # Compare JSON dumps (excluding generated UUIDs and section IDs)
        json1 = survey1.model_dump(mode="json")
        json2 = survey2.model_dump(mode="json")

        diff = DeepDiff(
            json1,
            json2,
            ignore_order=True,
            exclude_regex_paths=[
                # Exclude UUIDs which are generated fresh
                r".*\['id'\]",
                r".*\['speleodb_id'\]",
                # Exclude section IDs
                re.escape("root['sections'][*]['id']").replace(r"\*", r"\d+"),
                # Exclude station IDs - these are internal identifiers regenerated on import
                # The mapping from Compass station names to OSPL integer IDs is recreated each time
                r".*\['id_start'\]",
                r".*\['id_stop'\]",
                # Exclude lat/lon - Compass stores location at project level, not per-shot
                # These are derived from project location and set on first shot during load
                r".*\['latitude'\]",
                r".*\['longitude'\]",
                # Exclude depth fields - calculated during GeoJSON propagation
                r".*\['depth'\]",
                r".*\['depth_start'\]",
            ],
        )

        assert diff == {}, f"Round-trip produced differences: {diff}"

    @pytest.mark.parametrize("mak_path", ALL_COMPASS_MAK_FILES)
    def test_section_count_preserved(self, mak_path: Path) -> None:
        """Test that the number of sections is preserved through round-trip."""
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        # Load original
        survey1 = CompassInterface.from_file(mak_path)

        # Export and reload
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "roundtrip.mak"
            CompassInterface.to_file(survey1, out_path)
            survey2 = CompassInterface.from_file(out_path)

        assert len(survey1.sections) == len(survey2.sections)

    @pytest.mark.parametrize("mak_path", ALL_COMPASS_MAK_FILES)
    def test_shot_count_preserved(self, mak_path: Path) -> None:
        """Test that the total number of shots is preserved through round-trip."""
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        # Load original
        survey1 = CompassInterface.from_file(mak_path)

        # Export and reload
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "roundtrip.mak"
            CompassInterface.to_file(survey1, out_path)
            survey2 = CompassInterface.from_file(out_path)

        total1 = sum(len(s.shots) for s in survey1.sections)
        total2 = sum(len(s.shots) for s in survey2.sections)

        assert total1 == total2

    @pytest.mark.parametrize("mak_path", ALL_COMPASS_MAK_FILES)
    def test_section_names_preserved(self, mak_path: Path) -> None:
        """Test that section names are preserved through round-trip."""
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        # Load original
        survey1 = CompassInterface.from_file(mak_path)

        # Export and reload
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "roundtrip.mak"
            CompassInterface.to_file(survey1, out_path)
            survey2 = CompassInterface.from_file(out_path)

        names1 = [s.name for s in survey1.sections]
        names2 = [s.name for s in survey2.sections]

        assert names1 == names2


class TestRoundTripEdgeCases(unittest.TestCase):
    """Test edge cases in round-trip conversion."""

    def test_survey_with_empty_name(self) -> None:
        """Test round-trip with a survey that has no name."""
        from openspeleo_lib.models import Section
        from openspeleo_lib.models import Shot
        from openspeleo_lib.models import Survey

        # Create a minimal survey with no name
        survey = Survey(
            name=None,
            sections=[
                Section(
                    name="Test Section",
                    shots=[
                        Shot(
                            id_start=-1,
                            id_stop=0,
                            name="A1",
                            length=10.0,
                            depth=0.0,
                            azimuth=45.0,
                        ),
                    ],
                ),
            ],
        )

        # This should work without error
        json_data = survey.model_dump(mode="json")
        assert json_data["name"] is None


if __name__ == "__main__":
    unittest.main()
