# class TestRadiusModels(unittest.TestCase):
#     def test_radius_collection_from_radius_vector(self):
#         data = {
#             "tension_corridor": 1.0,
#             "tension_profile": 1.0,
#             "angle": 1.0,
#             "norm": 1.0,
#         }
#         assert RadiusVector(**data).model_dump() == data


# if __name__ == "__main__":
#     unittest.main()

import unittest

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.models import RadiusVector


class TestRadiusVector(unittest.TestCase):
    """
    Unit tests for the RadiusVector class.
    """

    def test_valid_radius_vector(self):
        """
        Test creating a valid RadiusVector instance.
        """
        radius_vector = RadiusVector(
            tension_corridor=1.0, tension_profile=2.0, angle=45.0, norm=5.0
        )
        assert radius_vector.tension_corridor == 1.0
        assert radius_vector.tension_profile == 2.0
        assert radius_vector.angle == 45.0
        assert radius_vector.norm == 5.0

    def test_invalid_radius_vector(self):
        """
        Test creating an invalid RadiusVector instance.
        """
        with pytest.raises(ValidationError):
            RadiusVector(
                tension_corridor="invalid",  # Should be a float
                tension_profile="invalid",  # Should be a float
                angle="invalid",  # Should be a float
                norm="invalid",  # Should be a float
            )

    @given(
        tension_corridor=st.floats(),
        tension_profile=st.floats(),
        angle=st.floats(),
        norm=st.floats(),
    )
    def test_fuzzy_radius_vector(self, tension_corridor, tension_profile, angle, norm):
        """
        Fuzzy testing for RadiusVector class using Hypothesis.
        """
        radius_vector = RadiusVector(
            tension_corridor=tension_corridor,
            tension_profile=tension_profile,
            angle=angle,
            norm=norm,
        )
        assert isinstance(radius_vector, RadiusVector)


if __name__ == "__main__":
    pytest.main()
