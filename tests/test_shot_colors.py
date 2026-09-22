"""Source colors survive export without changing survey geometry or TML data."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from openspeleo_lib.colors import normalize_shot_color
from openspeleo_lib.commands.convert import convert
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces.ariane.interface import ArianeInterface
from openspeleo_lib.interfaces.ariane.interface import ArianeSurvey

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("0xff0000ff", "#ff0000"),
        ("0x11223380", "rgba(17,34,51,0.50196078)"),
        ("#11223300", "rgba(17,34,51,0)"),
        ("#abc", "#aabbcc"),
        ("#abcd", "rgba(170,187,204,0.86666667)"),
        (" #FFB366 ", "#ffb366"),
        ("0X0000FFFF", "#0000ff"),
        ("rgba(17,34,51,0.5)", "rgba(17,34,51,0.5)"),
        ("red", "#ff0000"),
        (None, None),
        ("", None),
        ("not-a-color", None),
        ("#12345", None),
        (42, None),
        ([255, 0, 0], None),
    ],
)
def test_normalize_source_color(source: object, expected: str | None) -> None:
    assert normalize_shot_color(source) == expected


def _survey() -> ArianeSurvey:
    return ArianeSurvey.model_validate(
        {
            "useMagneticAzimuth": False,
            "sections": [
                {
                    "name": "Synthetic section",
                    "date": "2020-01-01",
                    "explorers": [],
                    "surveyors": [],
                    "shots": [
                        {
                            "ID": 71001,
                            "Length": 0,
                            "Depth": 0,
                            "Azimut": 0,
                            "Latitude": 40,
                            "longitude": -70,
                            "Color": "0xff0000ff",
                            "Type": ArianeShotType.START,
                        },
                        {
                            "ID": 71002,
                            "FromID": 71001,
                            "Length": 10,
                            "Depth": 0,
                            "Azimut": 90,
                            "Color": "#11223380",
                        },
                        {
                            "ID": 71003,
                            "FromID": 71002,
                            "Length": 10,
                            "Depth": 0,
                            "Azimut": 90,
                        },
                        {
                            "ID": 71004,
                            "FromID": 71003,
                            "Length": 10,
                            "Depth": 0,
                            "Azimut": 90,
                            "Color": "invalid",
                        },
                    ],
                }
            ],
        }
    )


def test_export_preserves_recorded_colors_and_falls_back_when_unavailable() -> None:
    survey = _survey()
    source_colors = [shot.color for shot in survey.shots]
    exported = survey_to_geojson(survey)
    features = {
        feature["properties"]["id"]: feature for feature in exported["features"]
    }
    assert features[71001]["geometry"]["type"] == "Point"
    assert features[71001]["properties"]["color"] == "#ff0000"
    assert features[71002]["geometry"]["type"] == "LineString"
    assert features[71002]["properties"]["color"] == "rgba(17,34,51,0.50196078)"
    assert "color" not in features[71003]["properties"]
    assert "color" not in features[71004]["properties"]
    assert [shot.color for shot in survey.shots] == source_colors

    # Color-only edits must not affect any coordinates, IDs, depths, or names.
    for shot in survey.shots:
        shot.color = "#00ff00"
    changed = survey_to_geojson(survey)
    for before, after in zip(exported["features"], changed["features"], strict=True):
        before["properties"].pop("color", None)
        assert after["properties"].pop("color") == "#00ff00"
        assert after == before


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("#FFB366", "#ffb366"),
        ("0x11223300", "rgba(17,34,51,0)"),
        ("", None),
        ("0xnot-a-color", None),
    ],
)
def test_explicit_default_transparency_and_invalid_colors_at_export_boundary(
    source: str, expected: str | None
) -> None:
    survey = _survey()
    shot = survey.sections[0].shots[2]
    assert "color" not in shot.model_fields_set
    implicit = survey_to_geojson(survey)
    feature = next(
        f for f in implicit["features"] if f["properties"]["id"] == shot.id_stop
    )
    assert "color" not in feature["properties"]

    shot.color = source
    assert "color" in shot.model_fields_set
    explicit = survey_to_geojson(survey)
    feature = next(
        f for f in explicit["features"] if f["properties"]["id"] == shot.id_stop
    )
    if expected is None:
        assert "color" not in feature["properties"]
    else:
        assert feature["properties"]["color"] == expected
    assert shot.color == source


def test_tml_roundtrip_retains_original_color_encoding(tmp_path: Path) -> None:
    survey = _survey()
    original = [shot.color for shot in survey.shots]
    survey_to_geojson(survey)
    target = tmp_path / "colors.tml"
    ArianeInterface.to_file(survey, target)
    restored = ArianeInterface.from_file(target)
    assert [shot.color for shot in restored.shots] == original


def test_excluded_shot_colors_do_not_resurrect_features() -> None:
    survey = _survey()
    survey.sections[0].shots[-1].excluded = True
    assert len(survey_to_geojson(survey)["features"]) == 3


def test_cli_exports_colors_and_preserves_output_after_failed_input(
    tmp_path: Path,
) -> None:
    source = tmp_path / "colors.tml"
    target = tmp_path / "colors.geojson"
    ArianeInterface.to_file(_survey(), source)
    convert(["-i", str(source), "-o", str(target), "-f", "geojson"])
    output = target.read_bytes()
    features = {f["properties"]["id"]: f for f in json.loads(output)["features"]}
    assert features[71001]["properties"]["color"] == "#ff0000"
    assert features[71002]["properties"]["color"] == "rgba(17,34,51,0.50196078)"
    assert "color" not in features[71004]["properties"]
    with pytest.raises(FileNotFoundError):
        convert(
            [
                "-i",
                str(tmp_path / "missing.tml"),
                "-o",
                str(target),
                "-f",
                "geojson",
                "-w",
            ]
        )
    assert target.read_bytes() == output
