"""Compass to OSPL decoding (transformation) logic.

This module handles the conversion from Compass MAK/DAT structures
to OSPL-compatible dictionaries that can be validated by Pydantic models.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import utm

from openspeleo_lib.interfaces.compass.defaults import DEFAULT_COMPASS_FORMAT
from openspeleo_lib.interfaces.compass.defaults import DEFAULT_PROFILE_TYPE
from openspeleo_lib.interfaces.compass.defaults import DEFAULT_SECTION_NAME
from openspeleo_lib.interfaces.compass.defaults import DEFAULT_SHOT_COLOR
from openspeleo_lib.interfaces.compass.defaults import DEFAULT_SHOT_TYPE
from openspeleo_lib.interfaces.compass.defaults import DEFAULT_START_ELEVATION
from openspeleo_lib.interfaces.compass.station_mapper import StationMapper

if TYPE_CHECKING:
    from compass_lib.project.models import CompassMakFile
    from compass_lib.survey.models import CompassShot
    from compass_lib.survey.models import CompassTrip

logger = logging.getLogger(__name__)


# Constants for unit conversion
FEET_TO_METERS = 0.3048


def get_project_anchor_wgs84(project: CompassMakFile) -> tuple[float, float] | None:
    """Get the project anchor location as WGS84 lat/lon.

    The anchor location is used to set coordinates on the first shot,
    enabling GeoJSON export. Priority:
    1. LocationDirective (@) if it has a valid location (zone != 0)
    2. First fixed station with coordinates from link stations

    Args:
        project: The Compass project

    Returns:
        Tuple of (latitude, longitude) or None if no valid location found
    """
    if not project.utm_zone:
        logger.debug("No UTM zone found in project")
        return None

    # Determine hemisphere from zone sign (positive = north, negative = south)
    northern = project.utm_zone > 0
    utm_zone = abs(project.utm_zone)

    # Try 1: Use project location (@) if valid
    loc = project.location
    if loc and loc.has_location:
        try:
            lat, lon = utm.to_latlon(
                loc.easting, loc.northing, utm_zone, northern=northern
            )
            logger.debug(
                "Using project location: (%.6f, %.6f) from UTM zone %d",
                lat,
                lon,
                project.utm_zone,
            )
        except Exception:
            logger.exception("Failed to convert project location to lat/lon")
            raise

        return lat, lon

    # Try 2: Use first fixed station with coordinates
    fixed_stations = project.get_fixed_stations()
    if fixed_stations:
        first_fixed = fixed_stations[0]
        fixed_loc = first_fixed.location
        if fixed_loc:
            # Convert feet to meters if needed
            factor = FEET_TO_METERS if fixed_loc.unit.lower() == "f" else 1.0

            easting = fixed_loc.easting * factor
            northing = fixed_loc.northing * factor

            try:
                lat, lon = utm.to_latlon(easting, northing, utm_zone, northern=northern)
                logger.debug(
                    "Using fixed station '%s' as anchor: (%.6f, %.6f)",
                    first_fixed.name,
                    lat,
                    lon,
                )

            except Exception:
                logger.exception(
                    "Failed to convert fixed station '%s' to lat/lon", first_fixed.name
                )
                raise

            return lat, lon

    logger.debug("No valid anchor location found for project")
    return None


def decode_shot(
    shot: CompassShot,
    station_mapper: StationMapper,
) -> dict:
    """Convert a Compass shot to an OSPL-compatible dictionary.

    Args:
        shot: The Compass shot to convert.
        station_mapper: The station mapper for name/ID conversion.

    Returns:
        A dictionary compatible with OSPL Shot model validation.
    """
    from_id = station_mapper.get_or_create_id(shot.from_station_name)
    to_id = station_mapper.get_or_create_id(shot.to_station_name)

    return {
        "id_start": from_id,
        "id_stop": to_id,
        "name": shot.to_station_name[:50].upper() if shot.to_station_name else None,
        "length": shot.length if shot.length is not None else 0.0,
        "azimuth": shot.frontsight_azimuth
        if shot.frontsight_azimuth is not None
        else 0.0,
        "inclination": shot.frontsight_inclination,
        "left": shot.left,
        "right": shot.right,
        "up": shot.up,
        "down": shot.down,
        "comment": shot.comment,
        "excluded": shot.excluded_from_all_processing or shot.excluded_from_plotting,
        "shot_type": DEFAULT_SHOT_TYPE,
        "color": DEFAULT_SHOT_COLOR,
        "profiletype": DEFAULT_PROFILE_TYPE,
        # Note: depth and depth_start are left unset (None).
        # They are calculated during GeoJSON coordinate propagation via BFS.
    }


def decode_trip(
    trip: CompassTrip,
    station_mapper: StationMapper,
) -> dict:
    """Convert a Compass trip to an OSPL-compatible section dictionary.

    Args:
        trip: The Compass trip to convert.
        station_mapper: The station mapper for name/ID conversion.

    Returns:
        A dictionary compatible with OSPL Section model validation.

    Note:
        Depth values are left as None. They are calculated during the
        GeoJSON coordinate propagation BFS, which traverses the shot graph
        and calculates both depth and lat/lon simultaneously.
    """
    header = trip.header

    # Convert shots (depth will be calculated later)
    shots = [decode_shot(shot, station_mapper) for shot in trip.shots]

    # Build surveyors list from team string
    surveyors = []
    if header.team:
        surveyors = [s.strip() for s in header.team.split(",") if s.strip()]

    # Build corrections list
    corrections = [
        header.length_correction,
        header.frontsight_azimuth_correction,
        header.frontsight_inclination_correction,
    ]
    corrections2 = [
        header.backsight_azimuth_correction,
        header.backsight_inclination_correction,
    ]

    return {
        "name": header.survey_name or DEFAULT_SECTION_NAME,
        "date": header.date.isoformat() if header.date else None,
        "description": header.comment,
        "surveyors": surveyors,
        "explorers": [],
        "declination": header.declination,
        "compass_format": DEFAULT_COMPASS_FORMAT,
        "correction": corrections,
        "correction2": corrections2,
        "shots": shots,
    }


def compass_decode(project: CompassMakFile) -> dict:
    """Transform a Compass project to an OSPL-compatible dictionary.

    This is the main entry point for decoding Compass data. It processes
    all DAT files referenced by the MAK file and converts them to the
    OSPL Survey format.

    Args:
        project: The loaded Compass MAK file with DAT data.

    Returns:
        A dictionary compatible with OSPL Survey model validation.
    """
    mapper = StationMapper()
    sections: list[dict] = []
    cave_name: str | None = None

    # Get anchor location for GeoJSON support
    anchor_coords = get_project_anchor_wgs84(project)
    anchor_set = False

    for file_dir in project.file_directives:
        if not file_dir.data:
            logger.debug("Skipping file directive without data: %s", file_dir.file)
            continue

        for trip in file_dir.data.trips:
            # Use first non-empty cave name as survey name
            if not cave_name and trip.header.cave_name:
                cave_name = trip.header.cave_name

            section = decode_trip(trip, mapper)

            # Set anchor coordinates on the first shot
            if anchor_coords and not anchor_set and section["shots"]:
                first_shot = section["shots"][0]
                first_shot["latitude"] = anchor_coords[0]
                first_shot["longitude"] = anchor_coords[1]
                anchor_set = True
                logger.debug(
                    "Set anchor coordinates on first shot: (%.6f, %.6f)",
                    anchor_coords[0],
                    anchor_coords[1],
                )

            sections.append(section)

    # Note: Depth calculation is deferred to the GeoJSON coordinate propagation
    # which calculates both depth and lat/lon during the same BFS traversal.
    # This ensures consistent handling of connected vs disconnected shots.

    logger.info(
        "Decoded %d sections with %d total stations from Compass project",
        len(sections),
        len(mapper),
    )

    return {
        "name": cave_name,
        "unit": "FT",  # Compass uses feet internally
        "sections": sections,
        "first_start_absolute_elevation": DEFAULT_START_ELEVATION,
        "use_magnetic_azimuth": True,
    }
