from __future__ import annotations

from frozendict import frozendict

from openspeleo_lib.models import Shot
from openspeleo_lib.models import Survey

ARIANE_MAPPING = frozendict(
    {
        Shot: {
            "id": "UUID",
            "id_start": "FromID",
            "id_stop": "ID",
            "azimuth": "Azimut",
            "closure_to_id": "ClosureToID",
            "color": "Color",
            "comment": "Comment",
            "depth": "Depth",
            "depth_start": "DepthIn",
            "excluded": "Excluded",
            "inclination": "Inclination",
            "latitude": "Latitude",
            "length": "Length",
            "locked": "Locked",
            "longitude": "Longitude",
            "name": "Name",
            "profiletype": "Profiletype",
            "shape": "Shape",
            "shot_type": "Type",
            # LRUD
            "left": "Left",
            "right": "Right",
            "up": "Up",
            "down": "Down",
        },
        # Section: {
        #     # ====================== Section Attributes ====================== #
        #     "name": "Section",
        #     "date": "Date",
        #     "explorers": "XMLExplorer",
        #     "surveyors": "XMLSurveyor",
        #     "shots": "SurveyData",
        # },
        Survey: {
            # ====================== Survey Attributes ====================== #
            "speleodb_id": "speleodb_id",
            "name": "caveName",
            "first_start_absolute_elevation": "firstStartAbsoluteElevation",
            "use_magnetic_azimuth": "useMagneticAzimuth",
            "ariane_viewer_layers": "Layers",
            "carto_ellipse": "CartoEllipse",
            "carto_line": "CartoLine",
            "carto_linked_surface": "CartoLinkedSurface",
            "carto_overlay": "CartoOverlay",
            "carto_page": "CartoPage",
            "carto_rectangle": "CartoRectangle",
            "carto_selection": "CartoSelection",
            "carto_spline": "CartoSpline",
            "constraints": "Constraints",
            "list_annotation": "ListAnnotation",
            "list_lidar_records": "ListLidarRecords",
        },
    }
)
