"""Field name mappings for Compass to OSPL conversion.

This module defines the mapping between Compass field names and OSPL field names.
Unlike Ariane which uses XML aliases, Compass uses different model structures
so the mapping is more of a conceptual reference for the transformation logic.
"""

from __future__ import annotations

# Compass Shot -> OSPL Shot field mapping reference
# Note: Actual transformation happens in decoding.py, this is for documentation
COMPASS_SHOT_MAPPING = {
    # Compass field -> OSPL field
    "from_station_name": "id_start",  # Station name -> integer ID via StationMapper
    "to_station_name": "id_stop",  # Station name -> integer ID via StationMapper
    "length": "length",  # Direct copy (feet)
    "frontsight_azimuth": "azimuth",  # Direct copy
    "frontsight_inclination": "inclination",  # Direct copy
    "left": "left",  # Direct copy (feet)
    "right": "right",  # Direct copy (feet)
    "up": "up",  # Direct copy (feet)
    "down": "down",  # Direct copy (feet)
    "comment": "comment",  # Direct copy
    "excluded_from_all_processing": "excluded",  # OR with excluded_from_plotting
    # Fields dropped during import (no OSPL equivalent):
    # - backsight_azimuth
    # - backsight_inclination
    # - do_not_adjust
    # - excluded_from_length
}

# Compass TripHeader -> OSPL Section field mapping reference
COMPASS_TRIP_MAPPING = {
    "survey_name": "name",  # Direct copy
    "date": "date",  # Direct copy
    "comment": "description",  # Maps to description
    "team": "surveyors",  # Split by comma
    "declination": "declination",  # Direct copy
    # cave_name goes to Survey.name
}

# Fields that need to be calculated or defaulted in OSPL
OSPL_CALCULATED_FIELDS = {
    "depth": "Calculated from inclination and cumulative elevation",
    "depth_start": "Depth at origin station",
    "shot_type": "Default: REAL",
    "color": "Default: #FFB366",
    "profiletype": "Default: VERTICAL",
    "closure_to_id": "Default: -1",
}
