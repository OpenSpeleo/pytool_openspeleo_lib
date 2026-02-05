"""Tests for the CompassInterface class."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pytest

from openspeleo_lib.interfaces.compass.interface import CompassFileType
from openspeleo_lib.interfaces.compass.interface import CompassInterface


class TestCompassFileType(unittest.TestCase):
    """Tests for CompassFileType detection."""

    def test_mak_file_detection(self):
        """Test that .mak files are detected correctly."""
        filetype = CompassFileType.from_path("cave.mak")
        assert filetype == CompassFileType.MAK

    def test_dat_file_detection(self):
        """Test that .dat files are detected correctly."""
        filetype = CompassFileType.from_path("survey.dat")
        assert filetype == CompassFileType.DAT

    def test_uppercase_extension(self):
        """Test that uppercase extensions work."""
        assert CompassFileType.from_path("CAVE.MAK") == CompassFileType.MAK
        assert CompassFileType.from_path("SURVEY.DAT") == CompassFileType.DAT

    def test_mixed_case_extension(self):
        """Test that mixed case extensions work."""
        assert CompassFileType.from_path("cave.Mak") == CompassFileType.MAK

    def test_unknown_extension_raises(self):
        """Test that unknown extensions raise TypeError."""
        with pytest.raises(TypeError, match="Unsupported file format"):
            CompassFileType.from_path("cave.txt")

    def test_path_object(self):
        """Test that Path objects work."""
        filetype = CompassFileType.from_path(Path("cave.mak"))
        assert filetype == CompassFileType.MAK


class TestCompassInterfaceInstantiation(unittest.TestCase):
    """Tests for CompassInterface instantiation."""

    def test_cannot_instantiate(self):
        """Test that CompassInterface cannot be instantiated directly."""
        with pytest.raises(NotImplementedError):
            CompassInterface()


class TestCompassInterfaceFromFile(unittest.TestCase):
    """Tests for CompassInterface.from_file method."""

    def test_nonexistent_file_raises(self):
        """Test that a nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            CompassInterface.from_file(Path("/nonexistent/cave.mak"))

    def test_dat_file_raises_type_error(self):
        """Test that a DAT file directly raises TypeError."""
        # Create a temporary DAT file for the test

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as f:
            f.write(b"dummy content")
            dat_path = Path(f.name)

        try:
            with pytest.raises(TypeError, match=r"Input must be a \.mak file"):
                CompassInterface.from_file(dat_path)
        finally:
            dat_path.unlink()


if __name__ == "__main__":
    unittest.main()
