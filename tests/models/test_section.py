import datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.constants import OSPL_SECTIONNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.enums import ArianeProfileType
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.models import ArianeRadiusVector
from openspeleo_lib.models import ArianeShape
from openspeleo_lib.models import Section
from openspeleo_lib.models import Shot


def test_valid_section():
    """
    Test creating a valid Section instance.
    """
    shot = Shot(
        shot_id=1,
        shot_name="TEST_SHOT",
        azimuth=45.0,
        closure_to_id=-1,
        color="#FFFFFF",
        shot_comment="Test comment",
        depth=100.0,
        depth_in=10.0,
        excluded=False,
        from_id=2,
        inclination=5.0,
        latitude=40.7128,
        length=50.0,
        locked=True,
        longitude=-74.0060,
        profiletype=ArianeProfileType.BISECTION,
        shot_type=ArianeShotType.REAL,
        shape=None,
        left=0.0,
        right=0.0,
        up=0.0,
        down=0.0,
    )
    section = Section(
        section_id=1,
        section_name="Test Section",
        date=datetime.datetime.now(tz=datetime.UTC).date(),
        explorers="Explorer1, Explorer2",
        surveyors="Surveyor1, Surveyor2",
        shots=[shot],
        section_comment="Test comment",
        compass_format="DDDDUDLRLADN",
        correction=[0.1, 0.2],
        correction2=[0.3, 0.4],
        declination=0.0,
    )
    assert section.section_id == 1
    assert section.section_name == "Test Section"
    assert section.date == datetime.datetime.now(tz=datetime.UTC).date()
    assert section.explorers == "Explorer1, Explorer2"
    assert section.surveyors == "Surveyor1, Surveyor2"
    assert section.shots == [shot]
    assert section.section_comment == "Test comment"
    assert section.compass_format == "DDDDUDLRLADN"
    assert section.correction == [0.1, 0.2]
    assert section.correction2 == [0.3, 0.4]
    assert section.declination == 0.0


def test_invalid_section():
    """
    Test creating an invalid Section instance.
    """
    with pytest.raises(ValidationError):
        Section(
            section_id=-1,  # Should be a non-negative integer
            section_name="invalid name",  # Should match the pattern
            date="invalid",  # Should be a date
            explorers=["invalid"],  # Should be a string
            surveyors=["invalid"],  # Should be a string
            shots="invalid",  # Should be a list of Shot instances
            section_comment=123,  # Should be a string
            compass_format=123,  # Should be a string
            correction="invalid",  # Should be a list of floats
            correction2="invalid",  # Should be a list of floats
            declination="invalid",  # Should be a float
        )


@given(
    section_id=st.integers(min_value=0),
    section_name=st.text(
        alphabet=" a-zA-Z0-9_-~:!?.'()[]{}@*&#%|$",
        max_size=OSPL_SECTIONNAME_MAX_LENGTH,
    ),
    date=st.dates(),
    explorers=st.text(),
    surveyors=st.text(),
    shots=st.lists(
        st.builds(
            Shot,
            shot_id=st.integers(min_value=0),
            shot_name=st.text(
                alphabet="a-zA-Z0-9_-~:!?.'()[]{}@*&#%|$",
                max_size=OSPL_SHOTNAME_MAX_LENGTH,
            ),
            azimuth=st.floats(min_value=0.0, max_value=360.0, exclude_max=True),
            closure_to_id=st.integers(),
            color=st.from_regex(r"^#(?:[0-9a-fA-F]{3}){1,2}$"),
            shot_comment=st.one_of(st.none(), st.text()),
            depth=st.floats(min_value=0.0),
            depth_in=st.floats(),
            excluded=st.booleans(),
            from_id=st.integers(),
            inclination=st.floats(),
            latitude=st.floats(min_value=-90.0, max_value=90.0),
            length=st.floats(min_value=0.0),
            locked=st.booleans(),
            longitude=st.floats(min_value=-180.0, max_value=180.0),
            profiletype=st.sampled_from(ArianeProfileType),
            shot_type=st.sampled_from(ArianeShotType),
            shape=st.one_of(
                st.none(),
                st.builds(
                    ArianeShape,
                    radius_vectors=st.lists(
                        st.builds(
                            ArianeRadiusVector,
                            tension_corridor=st.floats(),
                            tension_profile=st.floats(),
                            angle=st.floats(),
                            norm=st.floats(),
                        )
                    ),
                    has_profile_azimuth=st.booleans(),
                    has_profile_tilt=st.booleans(),
                    profile_azimuth=st.floats(
                        min_value=0.0, max_value=360.0, exclude_max=True
                    ),
                    profile_tilt=st.floats(),
                ),
            ),
            left=st.floats(min_value=0.0),
            right=st.floats(min_value=0.0),
            up=st.floats(min_value=0.0),
            down=st.floats(min_value=0.0),
        )
    ),
    section_comment=st.text(),
    compass_format=st.text(),
    correction=st.lists(st.floats()),
    correction2=st.lists(st.floats()),
    declination=st.floats(),
)
def test_fuzzy_section(
    section_id,
    section_name,
    date,
    explorers,
    surveyors,
    shots,
    section_comment,
    compass_format,
    correction,
    correction2,
    declination,
):
    """
    Fuzzy testing for Section class using Hypothesis.
    """
    section = Section(
        section_id=section_id,
        section_name=section_name,
        date=date,
        explorers=explorers,
        surveyors=surveyors,
        shots=shots,
        section_comment=section_comment,
        compass_format=compass_format,
        correction=correction,
        correction2=correction2,
        declination=declination,
    )
    assert isinstance(section, Section)


if __name__ == "__main__":
    pytest.main()
