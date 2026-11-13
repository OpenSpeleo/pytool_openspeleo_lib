"""Synthetic provenance and Ariane identity regressions; no private fixtures."""

import json
import sqlite3
import zipfile
from contextlib import closing

import pytest
from cave_closure import LoopClosureAlgorithm
from cave_closure import LoopClosureMode
from openspeleo_core import ariane_core

from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.geojson import InconsistentShotCoordinatesError
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.interfaces.stalagmight import StalagmightInterface
from openspeleo_lib.loop_closure import LoopClosureSolver
from openspeleo_lib.loop_closure import loop_closed_survey_to_geojson
from openspeleo_lib.loop_closure import prepare_loop_closure
from openspeleo_lib.models import Section
from openspeleo_lib.models import Shot
from openspeleo_lib.models import Survey
from tests.stalagmight_helpers import write_stalx
from tests.utils import make_synthetic_geolocation_survey


@pytest.mark.parametrize(
    "algorithm",
    [
        LoopClosureAlgorithm.LSE_REDUCED_PCG,
        LoopClosureAlgorithm.LSE_UNREDUCED_PCG,
        LoopClosureAlgorithm.LSE_SPARSE_QR,
        LoopClosureAlgorithm.LSE_SPARSE_CHOLESKY,
    ],
)
def test_snapshot_before_propagation_and_source_unchanged(algorithm):
    source = make_synthetic_geolocation_survey()
    before = source.model_dump_json()
    snapshot = prepare_loop_closure(
        source,
        mode=LoopClosureMode.HORIZONTAL,
        algorithm=algorithm,
        sigma_m=1.0,
        source_is_fresh=True,
    )
    assert snapshot.explicit_coordinate_ids == frozenset({1})
    result = snapshot.solve()
    geojson = loop_closed_survey_to_geojson(snapshot, result, source=source)
    assert len(geojson["features"]) == 2
    assert (
        survey_to_geojson(
            source,
            loop_closure_solver=LoopClosureSolver(
                algorithm=algorithm, source_is_fresh=True
            ),
        )
        == geojson
    )
    assert source.model_dump_json() == before
    source.sections[0].shots[1].length += 1
    with pytest.raises(ValueError, match="source no longer matches"):
        loop_closed_survey_to_geojson(snapshot, result, source=source)


def test_unknown_coordinate_history_rejected():
    with pytest.raises(ValueError, match="history is unknown"):
        prepare_loop_closure(
            make_synthetic_geolocation_survey(),
            mode=LoopClosureMode.HORIZONTAL,
            sigma_m=1.0,
        )


def test_guard_runs_on_disposable_unadjusted_source():
    source = make_synthetic_geolocation_survey(child_coordinates=(-70.0, 40.0))
    before = source.model_dump_json()
    with pytest.raises(InconsistentShotCoordinatesError):
        prepare_loop_closure(
            source, mode=LoopClosureMode.HORIZONTAL, sigma_m=1.0, source_is_fresh=True
        )
    assert source.model_dump_json() == before


def test_result_preparation_mismatch():
    source = make_synthetic_geolocation_survey()
    first = prepare_loop_closure(
        source, mode=LoopClosureMode.HORIZONTAL, sigma_m=1.0, source_is_fresh=True
    )
    second = prepare_loop_closure(
        source, mode=LoopClosureMode.HORIZONTAL, sigma_m=2.0, source_is_fresh=True
    )
    with pytest.raises(ValueError, match="different preparation"):
        loop_closed_survey_to_geojson(second, first.solve())


def test_targetless_closure_only_equates_id_with_fromid():
    source = make_synthetic_geolocation_survey()
    # Intentionally absurd ancillary fields must have no numerical meaning.
    source.sections[0].shots.append(
        Shot(
            id_start=1,
            id_stop=4242,
            shot_type=ArianeShotType.CLOSURE,
            length=123456.0,
            depth=765432.0,
            azimuth=211.0,
            excluded=True,
        )
    )
    before = source.model_dump_json()
    snapshot = prepare_loop_closure(
        source, mode=LoopClosureMode.HORIZONTAL, sigma_m=1.0, source_is_fresh=True
    )
    result = snapshot.solve().report
    points = dict(result.coordinates)
    assert points["1"][:2] == points["4242"][:2]
    assert len(result.observations) == 1
    assert json.loads(result.to_json())["diagnostics"]["objective"] > 0
    assert source.model_dump_json() == before


def test_explicit_origin_map_drops_derived_control():
    source = make_synthetic_geolocation_survey(child_coordinates=(40.0, -70.0))
    snapshot = prepare_loop_closure(
        source,
        mode=LoopClosureMode.HORIZONTAL,
        sigma_m=1.0,
        coordinate_origins={1: "explicit", 4242: "derived"},
    )
    assert snapshot.explicit_coordinate_ids == frozenset({1})
    assert dict(snapshot.solve().report.coordinates)["4242"][:2] != (0.0, 0.0)


@pytest.mark.parametrize("schema", [18, 19])
@pytest.mark.parametrize(
    "algorithm",
    [
        LoopClosureAlgorithm.LSE_REDUCED_PCG,
        LoopClosureAlgorithm.LSE_UNREDUCED_PCG,
        LoopClosureAlgorithm.LSE_SPARSE_QR,
        LoopClosureAlgorithm.LSE_SPARSE_CHOLESKY,
    ],
)
def test_native_input_uses_only_common_models(tmp_path, schema, algorithm, monkeypatch):
    path = write_stalx(
        tmp_path / "native.stalx",
        [{"id": 42, "shots": [{"azimuth_out": 90.0}]}],
        datums=[(1, 42, 0, 40.0, -70.0, 0.0)],
    )
    if schema == 19:
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute("PRAGMA user_version=19")
            connection.execute("UPDATE project SET schema_version=19")
            for key, value in (
                ("shot_numbering", {"next": 2, "identities": {"42:legacy:0": 1}}),
                (
                    "shot_graph",
                    {
                        "initialized": True,
                        "explicit": True,
                        "origins": {"1": None},
                        "root_positions": {"1": [999.0, 999.0]},
                        "geometry_locks": {"1": True},
                    },
                ),
            ):
                connection.execute(
                    "INSERT INTO project_settings VALUES (?,?)",
                    (key, json.dumps(value)),
                )
    before = path.read_bytes()
    source = StalagmightInterface.from_file(path)
    assert type(source) is Survey
    assert not hasattr(source, "_native")

    def forbid_native_read(*args, **kwargs):
        pytest.fail("Native reader called after conversion to an OSPL Survey")

    monkeypatch.setattr(
        "openspeleo_lib.interfaces.stalagmight.read_stalx", forbid_native_read
    )
    assert all(type(section) is Section for section in source.sections)
    assert all(type(shot) is Shot for shot in source.shots)
    snapshot = prepare_loop_closure(
        source, mode=LoopClosureMode.HORIZONTAL, algorithm=algorithm, sigma_m=1.0
    )
    result = snapshot.solve()
    exported = loop_closed_survey_to_geojson(snapshot, result, source=source)
    leg = next(
        feature
        for feature in exported["features"]
        if feature["geometry"]["type"] == "LineString"
    )
    assert leg["geometry"]["coordinates"][0] == pytest.approx((-70.0, 40.0), abs=1e-6)
    assert len(result.report.observations) == 1
    assert (
        survey_to_geojson(
            source, loop_closure_solver=LoopClosureSolver(algorithm=algorithm)
        )
        == exported
    )
    assert path.read_bytes() == before


def test_minimal_closure_record_has_no_required_measurements():
    closure = Shot(id_start=1, id_stop=2, shot_type=ArianeShotType.CLOSURE)
    assert (closure.id_start, closure.id_stop) == (1, 2)
    with pytest.raises(ValueError, match="Field required"):
        Shot(id_start=1, id_stop=2, shot_type=ArianeShotType.REAL)


def test_ariane_file_identity_record_reuses_existing_station_ids(tmp_path):
    records = [
        {
            "ID": i,
            "FromID": -1,
            "Type": "START",
            "Section": "Synthetic",
            "Date": "2025-01-01",
            "Length": 0,
            "Depth": 0,
            "Azimut": 0,
            "Latitude": 40.0,
            "Longitude": -70.0,
        }
        for i in (1, 2)
    ]
    records.append(
        {
            "ID": 2,
            "FromID": 1,
            "Type": "CLOSURE",
            "Section": "Synthetic",
            "Date": "2025-01-01",
        }
    )
    path = tmp_path / "identities.tml"
    xml = ariane_core.dict_to_xml_str(
        {"unit": "m", "Data": {"SurveyData": records}}, root_name="CaveFile"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Data.xml", xml)
    source = ArianeInterface.from_file(path)
    snapshot = prepare_loop_closure(
        source, mode=LoopClosureMode.HORIZONTAL, sigma_m=1.0
    )
    result = snapshot.solve().report
    assert len(result.observations) == 0
    assert dict(result.coordinates)["1"][:2] == dict(result.coordinates)["2"][:2]


def test_spatial_export_uses_solved_vertical_control():
    source = make_synthetic_geolocation_survey()
    before = source.model_dump_json()
    snapshot = prepare_loop_closure(
        source,
        mode=LoopClosureMode.SPATIAL,
        sigma_m=1.0,
        source_is_fresh=True,
        vertical_controls={1: 5.0},
    )
    result = snapshot.solve()
    exported = loop_closed_survey_to_geojson(snapshot, result, source=source)
    start = next(
        feature for feature in exported["features"] if feature["properties"]["id"] == 1
    )
    assert start["properties"]["depth"] == -16
    assert source.model_dump_json() == before


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("mode", [LoopClosureMode.HORIZONTAL, LoopClosureMode.SPATIAL])
def test_closure_can_introduce_an_identity_only_station(reverse, mode):
    source = make_synthetic_geolocation_survey(child_id_start=2)
    section = source.sections[0]
    closure = Shot(
        id_start=2 if reverse else 1,
        id_stop=1 if reverse else 2,
        shot_type=ArianeShotType.CLOSURE,
    )
    closure.section = section
    section.shots.append(closure)
    before = source.model_dump_json()
    solver = LoopClosureSolver(
        mode=mode,
        source_is_fresh=True,
        vertical_controls={1: 0.0} if mode == LoopClosureMode.SPATIAL else None,
    )
    snapshot = solver.prepare(source)
    result = snapshot.solve()
    points = dict(result.report.coordinates)
    assert points["1"] == pytest.approx(points["2"])
    assert len(result.report.observations) == 1
    exported = loop_closed_survey_to_geojson(snapshot, result, source=source)
    assert len(exported["features"]) == 2
    assert source.model_dump_json() == before
