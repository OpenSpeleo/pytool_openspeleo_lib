from __future__ import annotations

import unittest

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.models import ArianeRadiusVector


class TestArianeRadiusVector(unittest.TestCase):
    """
    Unit tests for the ArianeRadiusVector class.
    """

    def test_valid_radius_vector(self):
        """
        Test creating a valid ArianeRadiusVector instance.
        """
        radius_vector = ArianeRadiusVector(
            tension_corridor="A",
            tension_profile="B",
            angle=45.0,
            norm=5.0,
        )
        assert radius_vector.tension_corridor == "A"
        assert radius_vector.tension_profile == "B"
        assert radius_vector.angle == 45.0
        assert radius_vector.norm == 5.0

    def test_invalid_radius_vector(self):
        """
        Test creating an invalid ArianeRadiusVector instance.
        """
        with pytest.raises(ValidationError):
            ArianeRadiusVector(
                tension_corridor="invalid",  # Should be a float
                tension_profile="invalid",  # Should be a float
                angle="invalid",  # Should be a float
                norm="invalid",  # Should be a float
            )

    @given(
        tension_corridor=st.one_of(st.none(), st.text()),
        tension_profile=st.one_of(st.none(), st.text()),
        angle=st.floats(),
        norm=st.floats(),
    )
    def test_fuzzy_radius_vector(self, tension_corridor, tension_profile, angle, norm):
        """
        Fuzzy testing for ArianeRadiusVector class using Hypothesis.
        """
        radius_vector = ArianeRadiusVector(
            tension_corridor=tension_corridor,
            tension_profile=tension_profile,
            angle=angle,
            norm=norm,
        )
        assert isinstance(radius_vector, ArianeRadiusVector)


if __name__ == "__main__":
    pytest.main()
