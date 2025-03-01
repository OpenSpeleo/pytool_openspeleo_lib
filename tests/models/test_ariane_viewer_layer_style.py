import unittest

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.models import ArianeViewerLayerStyle


class TestArianeViewerLayerStyle(unittest.TestCase):
    """
    Unit tests for the ArianeViewerLayerStyle class.
    """

    def test_valid_layer_style(self):
        """
        Test creating a valid ArianeViewerLayerStyle instance.
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
        assert layer_style.dash_scale == 1.0
        assert layer_style.fill_color_string == "#FFFFFF"
        assert layer_style.line_type == "solid"
        assert layer_style.line_type_scale == 1.0
        assert layer_style.opacity == 0.5
        assert layer_style.size_mode == "normal"
        assert layer_style.stroke_color_string == "#000000"
        assert layer_style.stroke_thickness == 2.0

    def test_invalid_layer_style(self):
        """
        Test creating an invalid ArianeViewerLayerStyle instance.
        """
        with pytest.raises(ValidationError):
            ArianeViewerLayerStyle(
                dash_scale="invalid",  # Should be a float
                fill_color_string=123,  # Should be a string
                line_type=456,  # Should be a string
                line_type_scale="invalid",  # Should be a float
                opacity="invalid",  # Should be a float
                size_mode=789,  # Should be a string
                stroke_color_string=101112,  # Should be a string
                stroke_thickness="invalid",  # Should be a float
            )

    @given(
        dash_scale=st.floats(),
        fill_color_string=st.text(),
        line_type=st.text(),
        line_type_scale=st.floats(),
        opacity=st.floats(),
        size_mode=st.text(),
        stroke_color_string=st.text(),
        stroke_thickness=st.floats(),
    )
    def test_fuzzy_layer_style(
        self,
        dash_scale,
        fill_color_string,
        line_type,
        line_type_scale,
        opacity,
        size_mode,
        stroke_color_string,
        stroke_thickness,
    ):
        """
        Fuzzy testing for ArianeViewerLayerStyle class using Hypothesis.
        """
        layer_style = ArianeViewerLayerStyle(
            dash_scale=dash_scale,
            fill_color_string=fill_color_string,
            line_type=line_type,
            line_type_scale=line_type_scale,
            opacity=opacity,
            size_mode=size_mode,
            stroke_color_string=stroke_color_string,
            stroke_thickness=stroke_thickness,
        )
        assert isinstance(layer_style, ArianeViewerLayerStyle)


if __name__ == "__main__":
    pytest.main()
