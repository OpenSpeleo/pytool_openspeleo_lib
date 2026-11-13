"""Ariane closure record IDs are distinct from their station targets."""

import math
import zipfile

import orjson
import pytest
from openspeleo_core import ariane_core

from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.loop_closure import loop_closed_survey_to_geojson
from openspeleo_lib.loop_closure.presets import (
    InverseLengthWeightedLeastSquaresHorizontalSolver,
)


def read_targeted_closure(tmp_path, target=1):
    common = {"Section": "Synthetic", "Date": "2025-01-01", "Depth": 0}
    records = [
        {
            **common,
            "ID": 1,
            "FromID": -1,
            "Type": "START",
            "Length": 0,
            "Azimut": 0,
            "Latitude": 40,
            "Longitude": -70,
        }
    ]
    for station, length, bearing in [(2, 10, 90), (3, 20, 0), (4, 30, 270)]:
        records.append(
            {
                **common,
                "ID": station,
                "FromID": station - 1,
                "Type": "REAL",
                "Length": length,
                "Azimut": bearing,
            }
        )
    records.append(
        {
            **common,
            "ID": 99,
            "FromID": 4,
            "ClosureToID": target,
            "Type": "CLOSURE",
        }
    )
    xml = ariane_core.dict_to_xml_str(
        {"unit": "m", "Data": {"SurveyData": records}}, root_name="CaveFile"
    )
    path = tmp_path / "targeted.tml"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Data.xml", xml)
    source = ArianeInterface.from_file(path)
    source.use_magnetic_azimuth = False
    return source


def test_closure_to_id_closes_measured_ring(tmp_path):
    source = read_targeted_closure(tmp_path)
    before = source.model_dump_json()
    solver = InverseLengthWeightedLeastSquaresHorizontalSolver
    snapshot = solver.prepare(source)
    result = snapshot.solve()
    report = orjson.loads(result.report.to_json())
    assert report["diagnostics"]["cycle_rank"] == 1
    assert report["diagnostics"]["objective"] == pytest.approx(40 / 3)
    points = dict(result.report.coordinates)
    assert "99" not in points  # A record identifier must not become a station.
    assert points["4"][:2] == pytest.approx(points["1"][:2], abs=1e-8)
    # Misclosure (-20, 20) is distributed in proportion to leg lengths.
    assert points["2"][:2] == pytest.approx((40 / 3, -10 / 3), abs=1e-8)
    assert points["3"][:2] == pytest.approx((20, 10), abs=1e-8)
    assert len(result.report.observations) == 3
    assert source.model_dump_json() == before
    exported = loop_closed_survey_to_geojson(snapshot, result, source=source)
    assert exported == survey_to_geojson(source, loop_closure_solver=solver)
    assert source.model_dump_json() == before
    unclosed = survey_to_geojson(source.model_copy(deep=True))
    assert exported != unclosed
    assert all(
        math.isfinite(v) for _, position in result.report.coordinates for v in position
    )


def test_unknown_closure_to_id_is_rejected(tmp_path):
    source = read_targeted_closure(tmp_path, target=100)
    with pytest.raises(ValueError, match="CLOSURE refers to an unknown station"):
        InverseLengthWeightedLeastSquaresHorizontalSolver.prepare(source)
