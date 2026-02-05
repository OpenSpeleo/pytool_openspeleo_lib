"""Compass interface for OpenSpeleo Lib.

This module provides the CompassInterface class for loading and saving
Compass MAK/DAT files to the OSPL common data format.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from compass_lib.interface import CompassInterface as CompassLibInterface

from openspeleo_lib.interfaces.base import BaseInterface
from openspeleo_lib.interfaces.compass.decoding import compass_decode
from openspeleo_lib.interfaces.compass.encoding import compass_encode
from openspeleo_lib.interfaces.compass.encoding import get_dat_filename_from_mak
from openspeleo_lib.models import Survey

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class CompassFileType:
    """Compass file type detection."""

    MAK = "mak"
    DAT = "dat"

    @classmethod
    def from_path(cls, filepath: str | Path) -> str:
        """Detect file type from path extension.

        Args:
            filepath: Path to the file.

        Returns:
            File type string ("mak" or "dat").

        Raises:
            TypeError: If the file extension is not recognized.
        """
        path = Path(filepath)
        ext = path.suffix.lower()

        if ext == ".mak":
            return cls.MAK
        elif ext == ".dat":
            return cls.DAT
        else:
            raise TypeError(
                f"Unsupported file format: `{ext}`. "
                f"Expected: `.mak` or `.dat`"
            )


class CompassInterface(BaseInterface):
    """Interface for loading and saving Compass files.

    This interface implements the OSPL BaseInterface pattern for
    Compass MAK/DAT files. It uses compass_lib for parsing and
    formatting, and transforms the data to/from the OSPL common format.

    Note:
        Compass surveys commonly have loop closures where multiple shots
        connect to the same station. Unlike Ariane (which uses unique UUIDs
        per shot), Compass uses station names as references. Therefore,
        this interface does NOT enforce unique id_stop values.

    Example:
        # Load a Compass project
        survey = CompassInterface.from_file(Path("cave.mak"))

        # Access the data
        for section in survey.sections:
            print(f"{section.name}: {len(section.shots)} shots")

        # Save back to Compass format
        CompassInterface.to_file(survey, Path("cave_out.mak"))
    """

    @classmethod
    def from_file(cls, filepath: str | Path) -> Survey:
        """Load a survey from a Compass MAK file.

        Note:
            This overrides BaseInterface.from_file to skip uniqueness
            validation. Compass surveys have valid loop closures where
            multiple shots can connect to the same station (same id_stop).

        Args:
            filepath: Path to the MAK file.

        Returns:
            The loaded OSPL Survey.

        Raises:
            TypeError: If the file format is not supported.
            FileNotFoundError: If the file doesn't exist.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: `{filepath}`")

        # Note: We intentionally do NOT use UniqueValueGenerator.activate_uniqueness()
        # because Compass surveys have valid loop closures where multiple shots
        # can connect to the same station. The uniqueness check would reject
        # these valid surveys.
        return cls._from_file(filepath=filepath)

    @classmethod
    def to_file(cls, survey: Survey, filepath: Path) -> None:
        """Save a survey to Compass MAK/DAT files.

        Args:
            survey: The OSPL survey to save.
            filepath: Path to write the MAK file. DAT file is written
                     in the same directory.

        Raises:
            TypeError: If the output format is not supported.
        """
        filepath = Path(filepath)

        # Validate file type
        filetype = CompassFileType.from_path(filepath)
        if filetype != CompassFileType.MAK:
            raise TypeError(
                f"Output must be a .mak file, got: `{filepath.suffix}`"
            )

        # Generate DAT filename
        dat_filename = get_dat_filename_from_mak(filepath)

        # Encode to Compass format
        project = compass_encode(survey, dat_filename=dat_filename)

        # Save using compass_lib
        CompassLibInterface.save_project(
            project,
            filepath,
            save_dat_files=True,
        )

        logger.info("Saved Compass project to: %s", filepath)

    @classmethod
    def _from_file(cls, filepath: Path) -> Survey:
        """Load a survey from a Compass MAK file.

        Args:
            filepath: Path to the MAK file.

        Returns:
            The loaded OSPL Survey.

        Raises:
            TypeError: If the file format is not supported.
            FileNotFoundError: If the file doesn't exist.
        """
        filepath = Path(filepath)

        # Validate file type
        filetype = CompassFileType.from_path(filepath)
        if filetype != CompassFileType.MAK:
            raise TypeError(
                f"Input must be a .mak file, got: `{filepath.suffix}`"
            )

        logger.debug("Loading Compass file: %s", filepath)

        # Load using compass_lib
        project = CompassLibInterface.load_project(filepath)

        # Decode to OSPL format
        data = compass_decode(project)

        # Validate and create Survey model
        return Survey.model_validate(data)
