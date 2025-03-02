import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.constants import OSPL_SHOTNAME_MAX_LENGTH
from openspeleo_lib.constants import OSPL_SHOTNAME_MIN_LENGTH
from openspeleo_lib.enums import ArianeProfileType
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.models import ArianeRadiusVector
from openspeleo_lib.models import ArianeShape
from openspeleo_lib.models import Shot


def test_valid_shot():
    """
    Test creating a valid Shot instance.
    """
    shape = ArianeShape(
        radius_vectors=[],
        has_profile_azimuth=True,
        has_profile_tilt=False,
        profile_azimuth=30.0,
        profile_tilt=15.0,
    )
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
        profiletype=ArianeProfileType.HORIZONTAL,
        shot_type=ArianeShotType.VIRTUAL,
        shape=shape,
        left=0.0,
        right=0.0,
        up=0.0,
        down=0.0,
    )
    assert shot.shot_id == 1
    assert shot.shot_name == "TEST_SHOT"
    assert shot.azimuth == 45.0
    assert shot.closure_to_id == -1
    assert str(shot.color.original()) == "#FFFFFF"
    assert shot.shot_comment == "Test comment"
    assert shot.depth == 100.0
    assert shot.depth_in == 10.0
    assert shot.excluded is False
    assert shot.from_id == 2
    assert shot.inclination == 5.0
    assert shot.latitude == 40.7128
    assert shot.length == 50.0
    assert shot.locked is True
    assert shot.longitude == -74.0060
    assert shot.profiletype == ArianeProfileType.HORIZONTAL
    assert shot.shot_type == ArianeShotType.VIRTUAL
    assert shot.shape == shape
    assert shot.left == 0.0
    assert shot.right == 0.0
    assert shot.up == 0.0
    assert shot.down == 0.0


def test_invalid_shot():
    """
    Test creating an invalid Shot instance.
    """
    with pytest.raises(ValidationError):
        Shot(
            shot_id=-1,  # Should be a non-negative integer
            shot_name="invalid name",  # Should match the pattern
            azimuth="invalid",  # Should be a float
            closure_to_id="invalid",  # Should be an integer
            color=123,  # Should be a string
            shot_comment=456,  # Should be a string or None
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
            shot_type=101112,  # Should be a string
            shape="invalid",  # Should be a ArianeShape instance or None
            left=-1.0,  # Should be a non-negative float
            right=-1.0,  # Should be a non-negative float
            up=-1.0,  # Should be a non-negative float
            down=-1.0,  # Should be a non-negative float
        )


@given(
    shot_id=st.integers(min_value=0),
    shot_name=st.text(
        alphabet="a-zA-Z0-9_-~:!?.'()[]{}@*&#%|$",
        max_size=OSPL_SHOTNAME_MAX_LENGTH,
        min_size=OSPL_SHOTNAME_MIN_LENGTH,
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
            profile_azimuth=st.floats(min_value=0.0, max_value=360.0, exclude_max=True),
            profile_tilt=st.floats(),
        ),
    ),
    left=st.floats(min_value=0.0),
    right=st.floats(min_value=0.0),
    up=st.floats(min_value=0.0),
    down=st.floats(min_value=0.0),
)
def test_fuzzy_shot(
    shot_id,
    shot_name,
    azimuth,
    closure_to_id,
    color,
    shot_comment,
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
    Fuzzy testing for Shot class using Hypothesis.
    """
    shot = Shot(
        shot_id=shot_id,
        shot_name=shot_name,
        azimuth=azimuth,
        closure_to_id=closure_to_id,
        color=color,
        shot_comment=shot_comment,
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
        shot_type=shot_type,
        shape=shape,
        left=left,
        right=right,
        up=up,
        down=down,
    )
    assert isinstance(shot, Shot)


if __name__ == "__main__":
    pytest.main()
