import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MIN_LENGTH
from openspeleo_lib.models import RadiusVector
from openspeleo_lib.models import Shape
from openspeleo_lib.models import SurveyShot


def test_valid_survey_shot():
    """
    Test creating a valid SurveyShot instance.
    """
    shape = Shape(
        radius_vectors=[],
        has_profile_azimuth=True,
        has_profile_tilt=False,
        profile_azimuth=30.0,
        profile_tilt=15.0,
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
        shape=shape,
        left=0.0,
        right=0.0,
        up=0.0,
        down=0.0,
    )
    assert survey_shot.id == 1
    assert survey_shot.name_compass == "TEST_SHOT"
    assert survey_shot.azimuth == 45.0
    assert survey_shot.closure_to_id == -1
    assert survey_shot.color == "#FFFFFF"
    assert survey_shot.comment == "Test comment"
    assert survey_shot.depth == 100.0
    assert survey_shot.depth_in == 10.0
    assert survey_shot.excluded is False
    assert survey_shot.from_id == 2
    assert survey_shot.inclination == 5.0
    assert survey_shot.latitude == 40.7128
    assert survey_shot.length == 50.0
    assert survey_shot.locked is True
    assert survey_shot.longitude == -74.0060
    assert survey_shot.profiletype == "TestProfile"
    assert survey_shot.type == "TestType"
    assert survey_shot.shape == shape
    assert survey_shot.left == 0.0
    assert survey_shot.right == 0.0
    assert survey_shot.up == 0.0
    assert survey_shot.down == 0.0


def test_invalid_survey_shot():
    """
    Test creating an invalid SurveyShot instance.
    """
    with pytest.raises(ValidationError):
        SurveyShot(
            id=-1,  # Should be a non-negative integer
            name_compass="invalid name",  # Should match the pattern
            azimuth="invalid",  # Should be a float
            closure_to_id="invalid",  # Should be an integer
            color=123,  # Should be a string
            comment=456,  # Should be a string or None
            depth="invalid",  # Should be a float
            depth_in="invalid",  # Should be a float
            excluded="invalid",  # Should be a bool
            from_id="invalid",  # Should be an integer
            inclination="invalid",  # Should be a float
            latitude="invalid",  # Should be a float
            length="invalid",  # Should be a float
            locked="invalid",  # Should be a bool
            longitude="invalid",  # Should be a float
            profiletype=789,  # Should be a string
            type=101112,  # Should be a string
            shape="invalid",  # Should be a Shape instance or None
            left=-1.0,  # Should be a non-negative float
            right=-1.0,  # Should be a non-negative float
            up=-1.0,  # Should be a non-negative float
            down=-1.0,  # Should be a non-negative float
        )


@given(
    shot_id=st.integers(min_value=0),
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
    shot_type=st.text(),
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
def test_fuzzy_survey_shot(
    shot_id,
    name_compass,
    azimuth,
    closure_to_id,
    color,
    comment,
    depth,
    depth_in,
    excluded,
    from_id,
    inclination,
    latitude,
    length,
    locked,
    longitude,
    profiletype,
    shot_type,
    shape,
    left,
    right,
    up,
    down,
):
    """
    Fuzzy testing for SurveyShot class using Hypothesis.
    """
    survey_shot = SurveyShot(
        id=shot_id,
        name_compass=name_compass,
        azimuth=azimuth,
        closure_to_id=closure_to_id,
        color=color,
        comment=comment,
        depth=depth,
        depth_in=depth_in,
        excluded=excluded,
        from_id=from_id,
        inclination=inclination,
        latitude=latitude,
        length=length,
        locked=locked,
        longitude=longitude,
        profiletype=profiletype,
        type=shot_type,
        shape=shape,
        left=left,
        right=right,
        up=up,
        down=down,
    )
    assert isinstance(survey_shot, SurveyShot)


if __name__ == "__main__":
    pytest.main()
