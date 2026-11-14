"""Physical reachability must agree across measured and adjusted export."""

from dataclasses import replace

import orjson
import pytest
from cave_closure import LoopClosureMode

import openspeleo_lib.loop_closure as closure
from openspeleo_lib.enums import ArianeShotType as Kind
from openspeleo_lib.enums import LengthUnits
from openspeleo_lib.geojson import GEOD
from openspeleo_lib.geojson import NoKnownAnchorError
from openspeleo_lib.geojson import length_to_meters
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.loop_closure import LoopClosureSolver
from openspeleo_lib.loop_closure import loop_closed_survey_to_geojson
from openspeleo_lib.loop_closure.presets import PRESETS
from openspeleo_lib.loop_closure.presets import (
    InverseLengthWeightedConjugateGradientHorizontalSolver,
)
from openspeleo_lib.models import Shot
from tests.commands.test_command_convert import run_convert
from tests.connectivity_fixture import write_connectivity_tml
from tests.utils import make_synthetic_geolocation_survey
from tests.utils import write_synthetic_tml


def append(source, **values):
    shot = Shot(length=10, depth=0, azimuth=90, **values)
    shot.section = source.sections[0]
    source.sections[0].shots.append(shot)
    return shot


def branch():
    source = make_synthetic_geolocation_survey(child_id=3, child_id_start=2)
    source.use_magnetic_azimuth = False
    append(source, id_start=999, id_stop=2)
    append(source, id_start=3, id_stop=50, closure_to_id=1, shot_type=Kind.CLOSURE)
    return source


@pytest.mark.parametrize(
    "export", [None, *PRESETS.values()], ids=lambda p: getattr(p, "name", "measured")
)
def test_closure_reaches_branch_backward_and_discards_missing_leg(export, caplog):
    source = branch()
    before = source.model_dump_json()
    solver = (
        replace(
            export,
            source_is_fresh=True,
            vertical_controls={1: 0}
            if export.mode == LoopClosureMode.SPATIAL
            else None,
        )
        if export
        else None
    )
    result = survey_to_geojson(source, loop_closure_solver=solver)
    features = {f["properties"]["id"]: f for f in result["features"]}
    assert set(features) == {1, 2, 3}
    assert features[2]["geometry"]["type"] == "Point"
    assert features[3]["geometry"]["type"] == "LineString"
    assert "[Shot 2]" in caplog.text
    assert "999" in caplog.text
    if solver:
        assert source.model_dump_json() == before
        snapshot = solver.prepare(source)
        solved = snapshot.solve()
        assert set(dict(solved.report.coordinates).keys()) == {"1", "2", "3"}
        assert len(solved.report.observations) == 1
        assert loop_closed_survey_to_geojson(snapshot, solved) == result


@pytest.mark.parametrize(
    "kind", ["chain", "cycle", "self", "excluded_bridge", "excluded_closure"]
)
@pytest.mark.parametrize("adjusted", [False, True])
def test_unanchored_components_do_not_influence_export(kind, adjusted, caplog):
    source = make_synthetic_geolocation_survey()
    source.use_magnetic_azimuth = False
    solver = LoopClosureSolver(source_is_fresh=True) if adjusted else None
    expected = survey_to_geojson(source, loop_closure_solver=solver)
    append(
        source,
        id_start=3 if kind == "cycle" else 2 if kind == "self" else 999,
        id_stop=2,
    )
    append(source, id_start=2, id_stop=3)
    if kind == "excluded_bridge":
        append(source, id_start=1, id_stop=999, excluded=True)
    if kind == "excluded_closure":
        append(
            source,
            id_start=2,
            id_stop=50,
            closure_to_id=1,
            shot_type=Kind.CLOSURE,
            excluded=True,
        )
    bad = append(source, id_start=3, id_stop=4)
    bad.length = 0
    bad.depth = 1000  # Would fail geometry validation if evaluated.
    assert survey_to_geojson(source, loop_closure_solver=solver) == expected
    assert "[Shot 2]" in caplog.text
    assert "unreachable" in caplog.text


@pytest.mark.parametrize("adjusted", [False, True])
def test_alias_chain_can_connect_a_leg(adjusted):
    source = make_synthetic_geolocation_survey(child_id_start=3)
    source.use_magnetic_azimuth = False
    append(source, id_start=2, id_stop=3, shot_type=Kind.CLOSURE)
    append(source, id_start=1, id_stop=2, shot_type=Kind.CLOSURE)
    solver = LoopClosureSolver(source_is_fresh=True) if adjusted else None
    result = survey_to_geojson(source, loop_closure_solver=solver)
    assert len(result["features"]) == 2
    assert result["features"][1]["geometry"]["type"] == "LineString"


@pytest.mark.parametrize("adjusted", [False, True])
def test_unavailable_closure_is_dropped(adjusted, caplog):
    source = make_synthetic_geolocation_survey()
    source.use_magnetic_azimuth = False
    append(source, id_start=1, id_stop=50, closure_to_id=999, shot_type=Kind.CLOSURE)
    solver = LoopClosureSolver(source_is_fresh=True) if adjusted else None
    assert len(survey_to_geojson(source, loop_closure_solver=solver)["features"]) == 2
    assert "[Shot 50]" in caplog.text
    assert "closure" in caplog.text.lower()


def test_excluded_gps_does_not_anchor():
    source = make_synthetic_geolocation_survey()
    source.sections[0].shots[0].excluded = True
    with pytest.raises(NoKnownAnchorError):
        survey_to_geojson(source)


@pytest.mark.parametrize(
    ("latitude", "longitude"), [(47.5, 12.5), (80, 179.999), (-75, -179.999)]
)
def test_reverse_placement_satisfies_original_bearing(latitude, longitude):
    source = make_synthetic_geolocation_survey(child_coordinates=(latitude, longitude))
    source.use_magnetic_azimuth = False
    origin, child = source.sections[0].shots
    origin.latitude = origin.longitude = None
    child.length = 1000
    child.azimuth = 33
    survey_to_geojson(source)
    x, y, _ = GEOD.fwd(origin.longitude, origin.latitude, child.azimuth, child.length)
    assert GEOD.inv(x, y, longitude, latitude)[2] < 1e-5


@pytest.mark.parametrize(
    "solver",
    [LoopClosureSolver(), InverseLengthWeightedConjugateGradientHorizontalSolver],
)
def test_synthetic_survey_reproduces_real_topology(tmp_path, solver):
    path = tmp_path / "synthetic.tml"
    write_connectivity_tml(path)
    source = ArianeInterface.from_file(path)
    source.use_magnetic_azimuth = False
    before = source.model_dump_json()
    result = solver.to_geojson(source)
    assert len(result["features"]) == 1165
    assert source.model_dump_json() == before


def test_native_request_contains_only_cleaned_graph(monkeypatch):

    source = branch()
    append(source, id_start=998, id_stop=7)
    append(source, id_start=7, id_stop=8)
    original = closure._prepare_loop_closure  # noqa: SLF001 - inspect native boundary
    captured = []

    def inspect(request):
        captured.append(request)
        return original(request)

    monkeypatch.setattr(closure, "_prepare_loop_closure", inspect)
    solver = LoopClosureSolver(
        source_is_fresh=True,
        mode=LoopClosureMode.SPATIAL,
        vertical_controls={1: 0, 7: 1000},
    )
    snapshot = solver.prepare(source)
    assert len(captured) == 1
    request = captured[0]
    assert set(request["station_ids"]) == {"1", "2", "3"}
    assert len(request["measurements"]) == 1
    assert len(request["relationships"]) == 1
    assert all("7" not in row[0] for row in request["controls"])
    assert set(dict(snapshot.solve().report.coordinates).keys()) == {"1", "2", "3"}


@pytest.mark.parametrize("adjusted", [False, True])
def test_excluded_station_cannot_be_recreated_as_alias(adjusted):
    source = make_synthetic_geolocation_survey(child_id=2, child_excluded=True)
    source.use_magnetic_azimuth = False
    append(source, id_start=2, id_stop=3)
    append(source, id_start=1, id_stop=2, shot_type=Kind.CLOSURE)
    solver = LoopClosureSolver(source_is_fresh=True) if adjusted else None
    result = survey_to_geojson(source, loop_closure_solver=solver)
    assert [f["properties"]["id"] for f in result["features"]] == [1]


@pytest.mark.parametrize("adjusted", [False, True])
def test_anchored_cycle_and_self_link_terminate(adjusted):
    source = make_synthetic_geolocation_survey(child_id=2)
    source.use_magnetic_azimuth = False
    append(source, id_start=2, id_stop=1, shot_type=Kind.CLOSURE)
    append(source, id_start=2, id_stop=2, shot_type=Kind.CLOSURE)
    solver = LoopClosureSolver(source_is_fresh=True) if adjusted else None
    assert len(survey_to_geojson(source, loop_closure_solver=solver)["features"]) == 2


def test_multiple_components_and_warning_once(caplog):
    source = branch()
    append(
        source, id_start=-1, id_stop=10, latitude=46, longitude=13, shot_type=Kind.START
    )
    append(source, id_start=10, id_stop=11)
    append(source, id_start=90, id_stop=91)
    solver = LoopClosureSolver(source_is_fresh=True)
    solver.to_geojson(source)
    warnings = [
        r.getMessage()
        for r in caplog.records
        if r.name == "openspeleo_lib.survey_graph"
    ]
    assert sum("[Shot 91]" in m for m in warnings) == 1
    assert sum("[Shot 2]" in m for m in warnings) == 1


def test_derived_coordinates_do_not_rescue_a_component():
    source = make_synthetic_geolocation_survey()
    source.use_magnetic_azimuth = False
    append(source, id_start=999, id_stop=2, latitude=46, longitude=13)
    solver = LoopClosureSolver(
        coordinate_origins={1: "explicit", 4242: "unpopulated", 2: "derived"}
    )
    points = dict(solver.prepare(source).solve().report.coordinates)
    assert set(points) == {"1", "4242"}


@pytest.mark.parametrize("unit", ["m", "ft"])
@pytest.mark.parametrize("independent_depth", [False, True])
def test_reverse_depth_and_units(unit, independent_depth):

    source = make_synthetic_geolocation_survey(child_coordinates=(47.5, 12.5))
    source.unit = LengthUnits.METERS if unit == "m" else LengthUnits.FEET
    source.use_magnetic_azimuth = False
    origin, child = source.sections[0].shots
    origin.latitude = origin.longitude = None
    child.depth = 6
    child.depth_start = 2
    child.depth_start_is_authoritative = independent_depth
    survey_to_geojson(source)
    distance = length_to_meters(child.length_2d(origin.depth), source.unit)
    x, y, _ = GEOD.fwd(origin.longitude, origin.latitude, child.azimuth, distance)
    assert GEOD.inv(x, y, child.longitude, child.latitude)[2] < 1e-5


@pytest.mark.parametrize("loop_closure", [False, True])
def test_synthetic_cli_and_warning_output(tmp_path, loop_closure):

    source = tmp_path / "synthetic.tml"
    target = tmp_path / "output.geojson"
    write_connectivity_tml(source)
    before = source.read_bytes()
    result = run_convert(source, target, loop_closure=loop_closure)
    assert result.returncode == 0, result.stderr
    assert "dropping leg and retaining connected station" in result.stderr
    assert len(orjson.loads(target.read_bytes())["features"]) == 1165
    assert source.read_bytes() == before


def test_no_anchor_cli_preserves_output(tmp_path):

    source = tmp_path / "no-gps.tml"
    write_synthetic_tml(source, coordinates=[(None, None)])
    target = tmp_path / "output.geojson"
    for loop in [False, True]:
        assert run_convert(source, target, loop_closure=loop).returncode != 0
        assert not target.exists()
    target.write_bytes(b"keep")
    assert run_convert(source, target).returncode != 0
    assert target.read_bytes() == b"keep"


def test_excluded_bridge_with_alternate_closure_keeps_only_active_measurements():
    source = branch()
    bridge = append(source, id_start=1, id_stop=999, excluded=True)
    before = survey_to_geojson(source)
    assert len(before["features"]) == 3
    bridge.length = 999999
    bridge.azimuth = 123
    for shot in source.shots:
        if shot.id_stop != 1:
            shot.latitude = shot.longitude = None
    assert survey_to_geojson(source) == before


def test_controls_for_unreachable_alias_are_dropped_but_unknown_ids_fail():
    source = make_synthetic_geolocation_survey()
    source.use_magnetic_azimuth = False
    append(source, id_start=999, id_stop=2)
    append(source, id_start=2, id_stop=3, shot_type=Kind.CLOSURE)
    solver = LoopClosureSolver(
        mode=LoopClosureMode.SPATIAL,
        source_is_fresh=True,
        vertical_controls={1: 0, 3: 200},
    )
    assert set(dict(solver.prepare(source).solve().report.coordinates)) == {"1", "4242"}
    with pytest.raises(ValueError, match="unknown station"):
        replace(solver, vertical_controls={1: 0, 999: 200}).prepare(source)
