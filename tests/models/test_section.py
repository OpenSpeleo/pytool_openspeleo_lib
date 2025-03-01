import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.constants import OSPL_SECTIONNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SECTIONNAME_MIN_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MIN_LENGTH
from openspeleo_lib.models import RadiusVector
from openspeleo_lib.models import Section
from openspeleo_lib.models import Shape
from openspeleo_lib.models import Shot


def test_valid_survey_section():
    """
    Test creating a valid Section instance.
    """
    survey_shot = Shot(
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
    survey_section = Section(
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
    assert survey_section.id == 1
    assert survey_section.name == "Test Section"
    assert survey_section.date == datetime.datetime.now(tz=datetime.UTC).date()
    assert survey_section.surveyors == ["Surveyor1", "Surveyor2"]
    assert survey_section.shots == [survey_shot]
    assert survey_section.comment == "Test comment"
    assert survey_section.compass_format == "DDDDUDLRLADN"
    assert survey_section.correction == [0.1, 0.2]
    assert survey_section.correction2 == [0.3, 0.4]
    assert survey_section.declination == 0.0


def test_invalid_survey_section():
    """
    Test creating an invalid Section instance.
    """
    with pytest.raises(ValidationError):
        Section(
            id=-1,  # Should be a non-negative integer
            name="invalid name",  # Should match the pattern
            date="invalid",  # Should be a date
            surveyors="invalid",  # Should be a list of strings
            shots="invalid",  # Should be a list of Shot instances
            comment=123,  # Should be a string
            compass_format=123,  # Should be a string
            correction="invalid",  # Should be a list of floats
            correction2="invalid",  # Should be a list of floats
            declination="invalid",  # Should be a float
        )


@given(
    shot_id=st.integers(min_value=0),
    name=st.text(
        alphabet=" a-zA-Z0-9_-~:!?.'()[]{}@*&#%|$",
        max_size=OSPL_SECTIONNAME_MAX_LENGTH,
        min_size=OSPL_SECTIONNAME_MIN_LENGTH,
    ),
    date=st.dates(),
    surveyors=st.lists(st.text()),
    shots=st.lists(
        st.builds(
            Shot,
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
def test_fuzzy_survey_section(
    shot_id,
    name,
    date,
    surveyors,
    shots,
    comment,
    compass_format,
    correction,
    correction2,
    declination,
):
    """
    Fuzzy testing for Section class using Hypothesis.
    """
    survey_section = Section(
        id=shot_id,
        name=name,
        date=date,
        surveyors=surveyors,
        shots=shots,
        comment=comment,
        compass_format=compass_format,
        correction=correction,
        correction2=correction2,
        declination=declination,
    )
    assert isinstance(survey_section, Section)


if __name__ == "__main__":
    pytest.main()
