from bidict import frozenbidict

ARIANE_MAPPING = frozenbidict(
    {
        # RadiusVector Attributes
        "tension_corridor": "TensionCorridor",
        "tension_profile": "TensionProfile",
        "angle": "angle",
        "norm": "length",

        # RadiusCollection Attributes
        "radius_vector": "RadiusVector",

        # Shape Attributes
        "radius_collection": "RadiusCollection",
        "has_profile_azimuth": "hasProfileAzimut",
        "has_profile_tilt": "hasProfileTilt",
        "profile_azimuth": "profileAzimut",
        "profile_tilt": "profileTilt",

        # LayerStyle Attributes
        "dash_scale": "dashScale",
        "fill_color_string": "fillColorString",
        "line_type": "lineType",
        "line_type_scale": "lineTypeScale",
        "opacity": "opacity",
        "size_mode": "sizeMode",
        "stroke_color_string": "strokeColorString",
        "stroke_thickness": "strokeThickness",

        # Layer Attributes
        "constant": "constant",
        "locked_layer": "locked",
        "layer_name": "name",
        "style" : "style",
        "visible": "visible",

        # LayerCollection Attributes
        "layer_list": "layerList",

        # Shot Attributes
        "azimuth": "Azimut",
        "closure_to_id": "ClosureToID",
        "color": "Color",
        "comment": "Comment",
        "date": "Date",
        "depth": "Depth",
        "depth_in": "DepthIn",
        "excluded": "Excluded",
        "explorer": "Explorer",
        "from_id": "FromID",
        "id": "ID",
        "inclination": "Inclination",
        "latitude": "Latitude",
        "length": "Length",
        "locked": "Locked",
        "longitude": "Longitude",
        "name_compass": "Name",
        "profiletype": "Profiletype",
        "section": "Section",
        "shape": "Shape",
        "type": "Type",

        # LRUD
        "left": "Left",
        "right": "Right",
        "up": "Up",
        "down": "Down",

        # ShotCollection Attributes
        "shot_list": "SurveyData",

        # Survey Attributes,
        "cave_name": "caveName",
        "unit": "unit",
        "data": "Data",
        "layers": "Layers",
        "use_magnetic_azimuth": "useMagneticAzimuth",
        "first_start_absolute_elevation": "firstStartAbsoluteElevation",
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
    })
