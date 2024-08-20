import unittest

import pytest
from pydantic import ValidationError

from openspeleo_lib.types import Layer


class TestLayerModel(unittest.TestCase):

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
                "stroke_thickness": "1.0"
            },
            "visible": "true"
        }

    def test_layer_model(self):
        layer = Layer(**self.data)
        assert layer.constant
        assert not layer.locked_layer
        assert layer.layer_name == "Layer"
        assert layer.style.dash_scale == 1.0
        assert layer.style.fill_color_string == "0x00000000"
        assert layer.style.line_type == "STANDARD"
        assert layer.style.line_type_scale == 1.0
        assert layer.style.opacity == 100.0  # noqa: PLR2004
        assert layer.style.size_mode == "SWITCHABLE"
        assert layer.style.stroke_color_string == "0x000000ff"
        assert layer.style.stroke_thickness == 1.0
        assert layer.visible

    def test_missing_optional_fields(self):
        del self.data["constant"]
        del self.data["locked_layer"]
        del self.data["visible"]
        layer = Layer(**self.data)
        assert layer.constant
        assert not layer.locked_layer
        assert layer.visible

    def test_invalid_boolean(self):
        self.data["visible"] = "AAA"
        with pytest.raises(ValidationError, match="Cannot convert 'aaa' to boolean"):
            _ = Layer(**self.data)

    def test_invalid_float(self):
        self.data["style"]["stroke_thickness"] = "aaa"
        with pytest.raises(ValidationError, match="could not convert string to float"):
            Layer(**self.data)

if __name__ == "__main__":
    unittest.main()
