import datetime
import uuid

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.constants import OSPL_SECTIONNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SECTIONNAME_MIN_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MIN_LENGTH
from openspeleo_lib.models import ArianeViewerLayer
from openspeleo_lib.models import ArianeViewerLayerStyle
from openspeleo_lib.models import RadiusVector
from openspeleo_lib.models import Shape
from openspeleo_lib.models import Survey
from openspeleo_lib.models import SurveySection
from openspeleo_lib.models import SurveyShot


def test_valid_survey():
    """
    Test creating a valid Survey instance.
    """
    layer_style = ArianeViewerLayerStyle(
        dash_scale=1.0,
        fill_color_string="#FFFFFF",
        line_type="solid",
        line_type_scale=1.0,
        opacity=0.5,
        size_mode="normal",
        stroke_color_string="#000000",
        stroke_thickness=2.0,
    )
    layer = ArianeViewerLayer(
        constant=True,
        locked_layer=False,
        layer_name="Test ArianeViewerLayer",
        style=layer_style,
        visible=True,
    )
    survey_shot = SurveyShot(
        id=1,
        name_compass="TEST_SHOT",
        azimuth=45.0,
        closure_to_id=-1,
        color="#FFFFFF",
        comment="Test comment",
        depth=100.0,
        depth_in=10.0,
        excluded=False,
        from_id=2,
        inclination=5.0,
        latitude=40.7128,
        length=50.0,
        locked=True,
        longitude=-74.0060,
        profiletype="TestProfile",
        type="TestType",
        shape=None,
        left=0.0,
        right=0.0,
        up=0.0,
        down=0.0,
    )
    survey_section = SurveySection(
        id=1,
        name="Test Section",
        date=datetime.datetime.now(tz=datetime.UTC).date(),
        surveyors=["Surveyor1", "Surveyor2"],
        shots=[survey_shot],
        comment="Test comment",
        compass_format="DDDDUDLRLADN",
        correction=[0.1, 0.2],
        correction2=[0.3, 0.4],
        declination=0.0,
    )
    survey = Survey(
        speleodb_id=uuid.uuid4(),
        cave_name="Test Cave",
        sections=[survey_section],
        unit="m",
        first_start_absolute_elevation=100.0,
        use_magnetic_azimuth=True,
        ariane_viewer_layers=[layer],
        carto_ellipse=None,
        carto_line=None,
        carto_linked_surface=None,
        carto_overlay=None,
        carto_page=None,
        carto_rectangle=None,
        carto_selection=None,
        carto_spline=None,
        constraints=None,
        list_annotation=None,
    )
    assert isinstance(survey.speleodb_id, uuid.UUID)
    assert survey.cave_name == "Test Cave"
    assert survey.sections == [survey_section]
    assert survey.unit == "m"
    assert survey.first_start_absolute_elevation == 100.0
    assert survey.use_magnetic_azimuth is True
    assert survey.ariane_viewer_layers == [layer]
    assert survey.carto_ellipse is None
    assert survey.carto_line is None
    assert survey.carto_linked_surface is None
    assert survey.carto_overlay is None
    assert survey.carto_page is None
    assert survey.carto_rectangle is None
    assert survey.carto_selection is None
    assert survey.carto_spline is None
    assert survey.constraints is None
    assert survey.list_annotation is None


def test_invalid_survey():
    """
    Test creating an invalid Survey instance.
    """
    with pytest.raises(ValidationError):
        Survey(
            speleodb_id="invalid",  # Should be a UUID4
            cave_name=123,  # Should be a string
            sections="invalid",  # Should be a list of SurveySection instances
            unit="invalid",  # Should be "m" or "ft"
            first_start_absolute_elevation="invalid",  # Should be a float
            use_magnetic_azimuth="invalid",  # Should be a bool
            ariane_viewer_layers="invalid",  # Should be a list of ArianeViewerLayer instances
            carto_ellipse=123,  # Should be a string or None
            carto_line=123,  # Should be a string or None
            carto_linked_surface=123,  # Should be a string or None
            carto_overlay=123,  # Should be a string or None
            carto_page=123,  # Should be a string or None
            carto_rectangle=123,  # Should be a string or None
            carto_selection=123,  # Should be a string or None
            carto_spline=123,  # Should be a string or None
            constraints=123,  # Should be a string or None
            list_annotation=123,  # Should be a string or None
        )


@given(
    speleodb_id=st.uuids(version=4),
    cave_name=st.text(),
    sections=st.lists(
        st.builds(
            SurveySection,
            id=st.integers(min_value=0),
            name=st.text(
                alphabet=" a-zA-Z0-9_-~:!?.'()[]{}@*&#%|$",
                max_size=OSPL_SECTIONNAME_MAX_LENGTH,
                min_size=OSPL_SECTIONNAME_MIN_LENGTH,
            ),
            date=st.dates(),
            surveyors=st.lists(st.text()),
            shots=st.lists(
                st.builds(
                    SurveyShot,
                    id=st.integers(min_value=0),
                    name_compass=st.text(
                        alphabet="a-zA-Z0-9_-~:!?.'()[]{}@*&#%|$",
                        max_size=OSPL_SHOTNAME_MAX_LENGTH,
                        min_size=OSPL_SHOTNAME_MIN_LENGTH,
                    ),
                    azimuth=st.floats(),
                    closure_to_id=st.integers(),
                    color=st.text(),
                    comment=st.one_of(st.none(), st.text()),
                    depth=st.floats(),
                    depth_in=st.floats(),
                    excluded=st.booleans(),
                    from_id=st.integers(),
                    inclination=st.floats(),
                    latitude=st.floats(),
                    length=st.floats(),
                    locked=st.booleans(),
                    longitude=st.floats(),
                    profiletype=st.text(),
                    type=st.text(),
                    shape=st.one_of(
                        st.none(),
                        st.builds(
                            Shape,
                            radius_vectors=st.lists(
                                st.builds(
                                    RadiusVector,
                                    tension_corridor=st.floats(),
                                    tension_profile=st.floats(),
                                    angle=st.floats(),
                                    norm=st.floats(),
                                )
                            ),
                            has_profile_azimuth=st.booleans(),
                            has_profile_tilt=st.booleans(),
                            profile_azimuth=st.floats(),
                            profile_tilt=st.floats(),
                        ),
                    ),
                    left=st.floats(min_value=0.0),
                    right=st.floats(min_value=0.0),
                    up=st.floats(min_value=0.0),
                    down=st.floats(min_value=0.0),
                )
            ),
            comment=st.text(),
            compass_format=st.text(),
            correction=st.lists(st.floats()),
            correction2=st.lists(st.floats()),
            declination=st.floats(),
        )
    ),
    unit=st.sampled_from(["m", "ft"]),
    first_start_absolute_elevation=st.floats(min_value=0.0),
    use_magnetic_azimuth=st.booleans(),
    ariane_viewer_layers=st.lists(
        st.builds(
            ArianeViewerLayer,
            constant=st.booleans(),
            locked_layer=st.booleans(),
            layer_name=st.text(),
            style=st.builds(
                ArianeViewerLayerStyle,
                dash_scale=st.floats(),
                fill_color_string=st.text(),
                line_type=st.text(),
                line_type_scale=st.floats(),
                opacity=st.floats(),
                size_mode=st.text(),
                stroke_color_string=st.text(),
                stroke_thickness=st.floats(),
            ),
            visible=st.booleans(),
        )
    ),
    carto_ellipse=st.one_of(st.none(), st.text()),
    carto_line=st.one_of(st.none(), st.text()),
    carto_linked_surface=st.one_of(st.none(), st.text()),
    carto_overlay=st.one_of(st.none(), st.text()),
    carto_page=st.one_of(st.none(), st.text()),
    carto_rectangle=st.one_of(st.none(), st.text()),
    carto_selection=st.one_of(st.none(), st.text()),
    carto_spline=st.one_of(st.none(), st.text()),
    constraints=st.one_of(st.none(), st.text()),
    list_annotation=st.one_of(st.none(), st.text()),
)
def test_fuzzy_survey(
    speleodb_id,
    cave_name,
    sections,
    unit,
    first_start_absolute_elevation,
    use_magnetic_azimuth,
    ariane_viewer_layers,
    carto_ellipse,
    carto_line,
    carto_linked_surface,
    carto_overlay,
    carto_page,
    carto_rectangle,
    carto_selection,
    carto_spline,
    constraints,
    list_annotation,
):
    """
    Fuzzy testing for Survey class using Hypothesis.
    """
    survey = Survey(
        speleodb_id=speleodb_id,
        cave_name=cave_name,
        sections=sections,
        unit=unit,
        first_start_absolute_elevation=first_start_absolute_elevation,
        use_magnetic_azimuth=use_magnetic_azimuth,
        ariane_viewer_layers=ariane_viewer_layers,
        carto_ellipse=carto_ellipse,
        carto_line=carto_line,
        carto_linked_surface=carto_linked_surface,
        carto_overlay=carto_overlay,
        carto_page=carto_page,
        carto_rectangle=carto_rectangle,
        carto_selection=carto_selection,
        carto_spline=carto_spline,
        constraints=constraints,
        list_annotation=list_annotation,
    )
    assert isinstance(survey, Survey)


if __name__ == "__main__":
    pytest.main()
