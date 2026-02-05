"""OSPL to Compass encoding (transformation) logic.

This module handles the conversion from OSPL Survey structures
to Compass MAK/DAT format for round-trip capability.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from compass_lib.project.models import CompassMakFile
from compass_lib.project.models import FileDirective
from compass_lib.survey.models import CompassDatFile
from compass_lib.survey.models import CompassShot
from compass_lib.survey.models import CompassTrip
from compass_lib.survey.models import CompassTripHeader

if TYPE_CHECKING:
    from openspeleo_lib.models import Section
    from openspeleo_lib.models import Shot
    from openspeleo_lib.models import Survey

logger = logging.getLogger(__name__)


def build_station_names(survey: Survey) -> dict[int, str]:
    """Build a mapping from station IDs to names from shot data.

    Station names are derived from Shot.name field. For stations without
    names, a synthetic name is generated.

    Args:
        survey: The OSPL survey to extract station names from.

    Returns:
        Dictionary mapping station IDs to station names.
    """
    station_names: dict[int, str] = {}

    for section in survey.sections:
        for shot in section.shots:
            # Use shot name as the station name for id_stop
            if shot.name:
                station_names[shot.id_stop] = shot.name

    return station_names


def encode_shot(
    shot: Shot,
    station_names: dict[int, str],
) -> CompassShot:
    """Convert an OSPL Shot to a Compass shot.

    Args:
        shot: The OSPL shot to convert.
        station_names: Mapping of station IDs to names.

    Returns:
        A Compass shot model.
    """
    # Get station names, generating synthetic names if needed
    from_name = station_names.get(shot.id_start, f"S{shot.id_start}") if shot.id_start >= 0 else f"S{shot.id_stop}O"
    to_name = station_names.get(shot.id_stop, f"S{shot.id_stop}")

    return CompassShot(
        from_station_name=from_name,
        to_station_name=to_name,
        length=shot.length,
        frontsight_azimuth=shot.azimuth,
        frontsight_inclination=shot.inclination,
        left=shot.left,
        right=shot.right,
        up=shot.up,
        down=shot.down,
        comment=shot.comment,
        excluded_from_all_processing=shot.excluded,
        excluded_from_plotting=False,
        excluded_from_length=False,
        do_not_adjust=False,
    )


def encode_section(
    section: Section,
    station_names: dict[int, str],
    cave_name: str | None = None,
) -> CompassTrip:
    """Convert an OSPL Section to a Compass trip.

    Args:
        section: The OSPL section to convert.
        station_names: Mapping of station IDs to names.
        cave_name: The cave name to use in the trip header.

    Returns:
        A Compass trip model.
    """
    shots = [encode_shot(shot, station_names) for shot in section.shots]

    # Extract corrections if available
    corrections = section.correction if section.correction else []
    corrections2 = section.correction2 if section.correction2 else []

    header = CompassTripHeader(
        cave_name=cave_name,
        survey_name=section.name,
        date=section.date,
        comment=section.description,
        team=",".join(section.surveyors) if section.surveyors else None,
        declination=section.declination,
        length_correction=corrections[0] if len(corrections) > 0 else 0.0,
        frontsight_azimuth_correction=corrections[1] if len(corrections) > 1 else 0.0,
        frontsight_inclination_correction=corrections[2] if len(corrections) > 2 else 0.0,
        backsight_azimuth_correction=corrections2[0] if len(corrections2) > 0 else 0.0,
        backsight_inclination_correction=corrections2[1] if len(corrections2) > 1 else 0.0,
    )

    return CompassTrip(header=header, shots=shots)


def compass_encode(survey: Survey, dat_filename: str = "survey.dat") -> CompassMakFile:
    """Transform an OSPL Survey to a Compass project.

    This creates a minimal MAK file structure with a single DAT file
    containing all the survey data.

    Args:
        survey: The OSPL survey to convert.
        dat_filename: The filename to use for the DAT file reference.

    Returns:
        A Compass MAK file model.
    """
    station_names = build_station_names(survey)

    trips = [
        encode_section(section, station_names, cave_name=survey.name)
        for section in survey.sections
    ]

    dat_file = CompassDatFile(trips=trips)

    logger.info(
        "Encoded %d trips with %d total shots to Compass format",
        len(trips),
        sum(len(t.shots) for t in trips),
    )

    return CompassMakFile(
        directives=[
            FileDirective(file=dat_filename, data=dat_file),
        ]
    )


def get_dat_filename_from_mak(mak_path: Path) -> str:
    """Generate a DAT filename from a MAK file path.

    Args:
        mak_path: Path to the MAK file.

    Returns:
        The DAT filename (same name but with .dat extension).
    """
    return mak_path.stem + ".dat"
