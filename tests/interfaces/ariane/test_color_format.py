"""Ariane-authored files store shot colors as `0xrrggbbaa` (see
tests/artifacts/hand_survey.tml, test_simple.tml, test_ariane_v26.tml — no
Ariane file uses CSS-style `#RRGGBB`). Model-built surveys carry the CSS-style
default and must be normalized on export."""

import zipfile

from openspeleo_lib.generators import UniqueValueGenerator
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.interfaces.ariane.interface import ArianeSurvey


def _survey():
    data = {
        "name": "color-test",
        "unit": "FT",
        "sections": [
            {
                "name": "S1", "survey": None, "date": "2024-02-23",
                "explorers": [], "surveyors": [],
                "shots": [
                    {"id_stop": 0, "section": None, "shot_type": "START",
                     "name": "E", "length": 0.0, "depth": 0.0, "azimuth": 0.0},
                    {"id_start": 0, "id_stop": 1, "section": None, "name": "S1",
                     "length": 10.0, "depth": 0.0, "azimuth": 90.0,
                     "color": "#FFB366"},
                ],
            }
        ],
    }
    with UniqueValueGenerator.activate_uniqueness():
        return ArianeSurvey.model_validate(data)


def test_css_colors_normalized_to_ariane_format(tmp_path):
    out = tmp_path / "out.tml"
    ArianeInterface.to_file(_survey(), out)
    with zipfile.ZipFile(out) as z:
        xml = z.read("Data.xml").decode()
    assert "<Color>0xffb366ff</Color>" in xml
    assert "<Color>#" not in xml


def test_ariane_native_colors_pass_through(tmp_path):
    survey = _survey()
    survey.sections[0].shots[1].color = "0x8f6112ff"
    out = tmp_path / "out.tml"
    ArianeInterface.to_file(survey, out)
    with zipfile.ZipFile(out) as z:
        xml = z.read("Data.xml").decode()
    assert "<Color>0x8f6112ff</Color>" in xml
