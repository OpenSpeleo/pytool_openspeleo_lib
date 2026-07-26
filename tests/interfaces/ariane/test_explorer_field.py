"""The `Explorer` field must match Ariane's native encoding: an escaped
embedded fragment carrying BOTH tags, exactly as Ariane itself writes it
(tests/artifacts/hand_survey.tml):

    <Explorer>&lt;Explorer&gt;E&lt;/Explorer&gt;&lt;Surveyor&gt;S&lt;/Surveyor&gt;</Explorer>

The previous Surveyor-only fragment (produced whenever `explorers` was empty)
and the XMLExplorer/XMLSurveyor sibling tags are rendered by Ariane as literal
text in the data table's Explorer column.
"""

import zipfile

import pytest

from openspeleo_lib.generators import UniqueValueGenerator
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.interfaces.ariane.interface import ArianeSurvey


@pytest.fixture
def survey_surveyors_only():
    data = {
        "name": "explorer-field-test",
        "unit": "FT",
        "sections": [
            {
                "name": "S1",
                "survey": None,
                "date": "2024-02-23",
                "explorers": [],
                "surveyors": ["A. Pitkin & C. Roberson", "Guy Bryant"],
                "shots": [
                    {
                        "id_stop": 0, "section": None, "shot_type": "START",
                        "name": "E", "length": 0.0, "depth": 0.0, "azimuth": 0.0,
                    },
                    {
                        "id_start": 0, "id_stop": 1, "section": None, "name": "S1",
                        "length": 10.0, "depth": 0.0, "azimuth": 90.0,
                    },
                ],
            }
        ],
    }
    with UniqueValueGenerator.activate_uniqueness():
        return ArianeSurvey.model_validate(data)


def test_explorer_field_native_both_tags(survey_surveyors_only, tmp_path):
    out = tmp_path / "out.tml"
    ArianeInterface.to_file(survey_surveyors_only, out)

    with zipfile.ZipFile(out) as z:
        xml = z.read("Data.xml").decode()

    # both tags present even though explorers is empty - matching Ariane
    assert (
        "<Explorer>&lt;Explorer&gt;&lt;/Explorer&gt;"
        "&lt;Surveyor&gt;A. Pitkin &amp;amp; C. Roberson,Guy Bryant"
        "&lt;/Surveyor&gt;</Explorer>"
    ) in xml
    # no Ariane-foreign sibling tags
    assert "XMLExplorer" not in xml
    assert "XMLSurveyor" not in xml


def test_surveyors_round_trip(survey_surveyors_only, tmp_path):
    out = tmp_path / "out.tml"
    ArianeInterface.to_file(survey_surveyors_only, out)
    back = ArianeInterface.from_file(out)
    assert back.sections[0].surveyors == ["A. Pitkin & C. Roberson", "Guy Bryant"]
