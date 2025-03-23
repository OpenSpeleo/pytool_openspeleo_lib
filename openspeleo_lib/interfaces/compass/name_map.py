from bidict import frozenbidict

_COMPASS_MAPPING = frozenbidict(
    {
        # Shot Attributes
        "azimuth": "Azimut",
        "closure_to_id": "ClosureToID",
        "color": "Color",
        "shot_comment": "Comment",
        "depth": "Depth",
        "depth_in": "DepthIn",
        "excluded": "Excluded",
        "from_id": "FromID",
        "shot_id": "ID",
        "inclination": "Inclination",
        "latitude": "Latitude",
        "length": "Length",
        "locked": "Locked",
        "longitude": "Longitude",
        "shot_name": "Name",
        "profiletype": "Profiletype",
        "shape": "Shape",
        "shot_type": "Type",
        # LRUD
        "left": "Left",
        "right": "Right",
        "up": "Up",
        "down": "Down",
        # ====================== Section Attributes ====================== #
        # "section_id": None,
        "section_name": "Section",
        "date": "Date",
        "explorers": "Explorer",
        "surveyors": "Surveyor",
        # "section_comment": None,
        "shots": "SurveyData",
        # ====================== Survey Attributes ====================== #
        "speleodb_id": "speleodb_id",
        "cave_name": "caveName",
        "unit": "unit",
        "first_start_absolute_elevation": "firstStartAbsoluteElevation",
        "use_magnetic_azimuth": "useMagneticAzimuth",
        # ====================== Non-Model Attributes ====================== #
        "data": "Data",
    }
)

COMPASS_MAPPING = dict(_COMPASS_MAPPING)
COMPASS_INVERSE_MAPPING = dict(_COMPASS_MAPPING.inverse)
