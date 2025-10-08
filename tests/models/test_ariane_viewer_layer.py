from __future__ import annotations

import unittest

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from openspeleo_lib.models import ArianeViewerLayer
from openspeleo_lib.models import ArianeViewerLayerStyle


class TestArianeViewerLayerModel(unittest.TestCase):
    def setUp(self) -> None:
        self.data = {
            "constant": "true",
            "locked_layer": "false",
            "layer_name": "Layer",
            "style": {
                "dash_scale": "1.0",
                "fill_color_string": "0x00000000",
                "line_type": "STANDARD",
                "line_type_scale": "1.0",
                "opacity": "100.0",
                "size_mode": "SWITCHABLE",
                "stroke_color_string": "0x000000ff",
                "stroke_thickness": "1.0",
            },
            "visible": "true",
        }

    def test_layer_model(self):
        layer = ArianeViewerLayer(**self.data)
        assert layer.constant
        assert not layer.locked_layer
        assert layer.layer_name == "Layer"
        assert layer.style.dash_scale == 1.0
        assert layer.style.fill_color_string == "0x00000000"
        assert layer.style.line_type == "STANDARD"
        assert layer.style.line_type_scale == 1.0
        assert layer.style.opacity == 100.0
        assert layer.style.size_mode == "SWITCHABLE"
        assert layer.style.stroke_color_string == "0x000000ff"
        assert layer.style.stroke_thickness == 1.0
        assert layer.visible

    def test_invalid_boolean(self):
        self.data["visible"] = "AAA"
        with pytest.raises(ValidationError, match="Input should be a valid boolean"):
            _ = ArianeViewerLayer(**self.data)

    def test_invalid_float(self):
        self.data["style"]["stroke_thickness"] = "aaa"
        with pytest.raises(ValidationError, match="Input should be a valid number"):
            ArianeViewerLayer(**self.data)

    def test_valid_layer(self):
        """
        Test creating a valid `ArianeViewerLayer` & `ArianeViewerLayerStyle` instance.
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
        assert layer.constant is True
        assert layer.locked_layer is False
        assert layer.layer_name == "Test ArianeViewerLayer"
        assert layer.style == layer_style
        assert layer.visible is True

    def test_invalid_layer(self):
        """
        Test creating an invalid ArianeViewerLayer instance.
        """
        with pytest.raises(ValidationError):
            ArianeViewerLayer(
                constant="invalid",  # Should be a bool
                locked_layer="invalid",  # Should be a bool
                layer_name=123,  # Should be a string
                style="invalid",  # Should be a ArianeViewerLayerStyle instance
                visible="invalid",  # Should be a bool
            )

    @given(
        constant=st.booleans(),
        locked_layer=st.booleans(),
        layer_name=st.text(),
        dash_scale=st.floats(),
        fill_color_string=st.text(),
        line_type=st.text(),
        line_type_scale=st.floats(),
        opacity=st.floats(),
        size_mode=st.text(),
        stroke_color_string=st.text(),
        stroke_thickness=st.floats(),
        visible=st.booleans(),
    )
    def test_fuzzy_layer(
        self,
        constant,
        locked_layer,
        layer_name,
        dash_scale,
        fill_color_string,
        line_type,
        line_type_scale,
        opacity,
        size_mode,
        stroke_color_string,
        stroke_thickness,
        visible,
    ):
        """
        Fuzzy testing for ArianeViewerLayer class using Hypothesis.
        """
        try:
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
            layer = ArianeViewerLayer(
                constant=constant,
                locked_layer=locked_layer,
                layer_name=layer_name,
                style=layer_style,
                visible=visible,
            )
            assert isinstance(layer, ArianeViewerLayer)
        except ValidationError:
            pass  # Expected for invalid inputs


if __name__ == "__main__":
    pytest.main()
