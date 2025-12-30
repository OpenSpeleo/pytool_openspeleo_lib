from __future__ import annotations

from bidict import frozenbidict

_ARIANE_MAPPING = frozenbidict(
    {
        # ArianeRadiusVector Attributes
        "tension_corridor": "TensionCorridor",
        "tension_profile": "TensionProfile",
        "angle": "angle",
        "norm": "length",
        # RadiusCollection Attributes
        "radius_vector": "RadiusVector",
        # ArianeShape Attributes
        "radius_collection": "RadiusCollection",
        "has_profile_azimuth": "hasProfileAzimut",
        "has_profile_tilt": "hasProfileTilt",
        "profile_azimuth": "profileAzimut",
        "profile_tilt": "profileTilt",
        # ArianeViewerLayerStyle Attributes
        "dash_scale": "dashScale",
        "fill_color_string": "fillColorString",
        "line_type": "lineType",
        "line_type_scale": "lineTypeScale",
        "opacity": "opacity",
        "size_mode": "sizeMode",
        "stroke_color_string": "strokeColorString",
        "stroke_thickness": "strokeThickness",
        # ArianeViewerLayer Attributes
        "constant": "constant",
        "locked_layer": "locked",
        "layer_name": "name",
        "style": "style",
        "visible": "visible",
        # ArianeViewerLayerCollection Attributes
        "layer_list": "layerList",
        # Shot Attributes
        "id": "UUID",
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
        # "section": "Section",
        "shape": "Shape",
        "shot_type": "Type",
        # LRUD
        "left": "Left",
        "right": "Right",
        "up": "Up",
        "down": "Down",
        # ====================== Section Attributes ====================== #
        # "id": None,
        "section_name": "Section",
        "date": "Date",
        "explorers": "XMLExplorer",
        "surveyors": "XMLSurveyor",
        # "section_comment": None,
        "shots": "SurveyData",
        # ====================== Survey Attributes ====================== #
        "speleodb_id": "speleodb_id",
        "cave_name": "caveName",
        "unit": "unit",
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
        # ====================== Non-Model Attributes ====================== #
        "data": "Data",
    }
)

ARIANE_MAPPING = dict(_ARIANE_MAPPING)
ARIANE_INVERSE_MAPPING = dict(_ARIANE_MAPPING.inverse)
