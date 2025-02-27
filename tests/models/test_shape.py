import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.models import RadiusVector
from openspeleo_lib.models import Shape


def test_valid_shape():
    """
    Test creating a valid Shape instance.
    """
    radius_vector = RadiusVector(
        tension_corridor=1.0, tension_profile=2.0, angle=45.0, norm=5.0
    )
    shape = Shape(
        radius_vectors=[radius_vector],
        has_profile_azimuth=True,
        has_profile_tilt=False,
        profile_azimuth=30.0,
        profile_tilt=15.0,
    )
    assert shape.radius_vectors == [radius_vector]
    assert shape.has_profile_azimuth is True
    assert shape.has_profile_tilt is False
    assert shape.profile_azimuth == 30.0
    assert shape.profile_tilt == 15.0


def test_invalid_shape():
    """
    Test creating an invalid Shape instance.
    """
    with pytest.raises(ValidationError):
        Shape(
            radius_vectors="invalid",  # Should be a list of RadiusVector instances
            has_profile_azimuth="invalid",  # Should be a bool
            has_profile_tilt="invalid",  # Should be a bool
            profile_azimuth="invalid",  # Should be a float
            profile_tilt="invalid",  # Should be a float
        )


@given(
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
)
def test_fuzzy_shape(
    radius_vectors, has_profile_azimuth, has_profile_tilt, profile_azimuth, profile_tilt
):
    """
    Fuzzy testing for Shape class using Hypothesis.
    """
    try:
        shape = Shape(
            radius_vectors=radius_vectors,
            has_profile_azimuth=has_profile_azimuth,
            has_profile_tilt=has_profile_tilt,
            profile_azimuth=profile_azimuth,
            profile_tilt=profile_tilt,
        )
        assert isinstance(shape, Shape)
    except ValidationError:
        pass  # Expected for invalid inputs


if __name__ == "__main__":
    pytest.main()
