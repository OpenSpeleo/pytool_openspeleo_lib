from __future__ import annotations

import pytest
from pydantic import ValidationError

from openspeleo_lib.geojson import NoKnownAnchorError
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from tests.utils import write_synthetic_tml

MISLEADING_COMMENT = (
    "Latitude=40 Longitude=-70; UTM zone 16N 450000 2240000; "
    "declination=-999; <Latitude>999</Latitude><Longitude>999</Longitude>"
)


def test_invalid_anchors_report_all_station_coordinates(tmp_path):
    source = tmp_path / "invalid.tml"
    write_synthetic_tml(source, coordinates=[(40, -183)] * 4)
    with pytest.raises(ValidationError) as caught:
        ArianeInterface.from_file(source)
    notes = caught.value.__notes__
    assert len(notes) == 4
    for index, note in enumerate(notes):
        assert "Synthetic anchors" in note
        assert f"ANCHOR{index}" in note
        assert f"Shot ID='{index}'" in note
        assert "longitude='-183" in note
        assert "[-180, 180]" in note


def test_comments_do_not_change_anchor_declination_or_geometry(tmp_path):
    source = tmp_path / "survey.tml"
    write_synthetic_tml(source)
    original = ArianeInterface.from_file(source)
    write_synthetic_tml(source, comment=MISLEADING_COMMENT)
    changed = ArianeInterface.from_file(source)
    assert changed.geo_anchor == original.geo_anchor
    assert (
        changed.sections[0].computed_declination
        == original.sections[0].computed_declination
    )
    assert survey_to_geojson(changed) == survey_to_geojson(original)
    assert next(changed.shots).comment == MISLEADING_COMMENT


def test_comments_cannot_supply_missing_coordinates(tmp_path):
    source = tmp_path / "survey.tml"
    write_synthetic_tml(source, coordinates=[(None, None)], comment=MISLEADING_COMMENT)
    survey = ArianeInterface.from_file(source)
    assert survey.geo_anchor is None
    with pytest.raises(ValueError, match="Lat/Long"):
        _ = survey.sections[0].computed_declination
    with pytest.raises(NoKnownAnchorError):
        survey_to_geojson(survey)


def test_comments_cannot_repair_invalid_coordinates(tmp_path):
    source = tmp_path / "survey.tml"
    write_synthetic_tml(source, coordinates=[(40, -183)], comment=MISLEADING_COMMENT)
    with pytest.raises(ValidationError) as caught:
        ArianeInterface.from_file(source)
    assert "longitude='-183" in caught.value.__notes__[0]
    assert MISLEADING_COMMENT not in caught.value.__notes__[0]


def test_diagnostics_are_bounded(tmp_path):
    source = tmp_path / "survey.tml"
    write_synthetic_tml(source, coordinates=[(100, -183)] * 60)
    with pytest.raises(ValidationError) as caught:
        ArianeInterface.from_file(source)
    assert len(caught.value.__notes__) == 101
    assert caught.value.__notes__[-1].startswith("20 additional")
