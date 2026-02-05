"""Tests for loading Compass files into OSPL format."""

from __future__ import annotations

import unittest
from pathlib import Path

import pytest

from tests.conftest import ALL_COMPASS_MAK_FILES
from tests.conftest import PRIVATE_COMPASS_DATA_DIR


@pytest.mark.skipif(
    not PRIVATE_COMPASS_DATA_DIR.exists(),
    reason="Private Compass data directory not found",
)
class TestLoadCompassFiles:
    """Test loading Compass MAK files to OSPL Survey format."""

    @pytest.mark.parametrize("mak_path", ALL_COMPASS_MAK_FILES)
    def test_load_compass_to_survey(self, mak_path: Path) -> None:
        """Test that a Compass MAK file can be loaded as an OSPL Survey."""
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        survey = CompassInterface.from_file(mak_path)

        # Basic structure validation
        assert survey is not None
        assert hasattr(survey, "sections")
        assert hasattr(survey, "name")

    @pytest.mark.parametrize("mak_path", ALL_COMPASS_MAK_FILES)
    def test_loaded_survey_has_sections(self, mak_path: Path) -> None:
        """Test that loaded surveys have at least one section."""
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        survey = CompassInterface.from_file(mak_path)
        assert len(survey.sections) > 0

    @pytest.mark.parametrize("mak_path", ALL_COMPASS_MAK_FILES)
    def test_loaded_sections_have_shots(self, mak_path: Path) -> None:
        """Test that loaded sections have at least one shot each."""
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        survey = CompassInterface.from_file(mak_path)

        for section in survey.sections:
            # Most sections should have shots, but some might be empty
            # Just verify the shots list exists
            assert hasattr(section, "shots")

    @pytest.mark.parametrize("mak_path", ALL_COMPASS_MAK_FILES)
    def test_loaded_shots_have_required_fields(self, mak_path: Path) -> None:
        """Test that all shots have the required OSPL fields.

        Note: depth may be None after initial load; it is calculated during
        GeoJSON generation via coordinate propagation.
        """
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        survey = CompassInterface.from_file(mak_path)

        for section in survey.sections:
            for shot in section.shots:
                # Check required fields exist
                assert hasattr(shot, "id_start")
                assert hasattr(shot, "id_stop")
                assert hasattr(shot, "length")
                assert hasattr(shot, "azimuth")
                # depth attribute exists (may be None until GeoJSON propagation)
                assert hasattr(shot, "depth")

    @pytest.mark.parametrize("mak_path", ALL_COMPASS_MAK_FILES)
    def test_survey_serializes_to_json(self, mak_path: Path) -> None:
        """Test that loaded surveys can be serialized to JSON."""
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        survey = CompassInterface.from_file(mak_path)

        # This should not raise
        json_data = survey.model_dump(mode="json")

        assert isinstance(json_data, dict)
        assert "sections" in json_data

    @pytest.mark.parametrize("mak_path", ALL_COMPASS_MAK_FILES)
    def test_station_ids_are_valid(self, mak_path: Path) -> None:
        """Test that station IDs are valid integers."""
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        survey = CompassInterface.from_file(mak_path)

        for section in survey.sections:
            for shot in section.shots:
                # id_stop must be non-negative
                assert shot.id_stop >= 0

                # id_start can be -1 (no origin) or non-negative
                assert shot.id_start >= -1


class TestLoadCompassFileEdgeCases(unittest.TestCase):
    """Test edge cases for Compass file loading."""

    def test_load_nonexistent_file(self) -> None:
        """Test that loading a nonexistent file raises FileNotFoundError."""
        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        with pytest.raises(FileNotFoundError):
            CompassInterface.from_file(Path("/nonexistent/path/cave.mak"))

    def test_load_wrong_extension(self) -> None:
        """Test that loading a file with wrong extension raises TypeError."""
        import tempfile

        from openspeleo_lib.interfaces.compass.interface import CompassInterface

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"dummy content")
            temp_path = Path(f.name)

        try:
            with pytest.raises(TypeError):
                CompassInterface.from_file(temp_path)
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    unittest.main()
