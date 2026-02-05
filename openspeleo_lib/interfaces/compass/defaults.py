"""Default values for Compass to OSPL conversion.

This module defines default values used when converting from Compass format
to OSPL format where certain fields don't have direct equivalents.
"""

from __future__ import annotations

# Default shot values
DEFAULT_SHOT_COLOR = "#FFB366"  # Orange color for visibility
DEFAULT_SHOT_TYPE = "REAL"
DEFAULT_PROFILE_TYPE = "VERTICAL"
DEFAULT_CLOSURE_TO_ID = -1

# Default section values
DEFAULT_SECTION_NAME = "Unnamed"  # Single word to survive compass_lib roundtrip
DEFAULT_COMPASS_FORMAT = "DDDDUDLRLADN"

# Default survey values
DEFAULT_START_ELEVATION = 0.0
