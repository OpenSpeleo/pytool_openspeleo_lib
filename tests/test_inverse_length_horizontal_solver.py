"""Independent weighted-loop expectations for the complete horizontal formulation."""

import math
from dataclasses import replace
from fractions import Fraction

import orjson
import pytest
from cave_closure import LoopClosureAlgorithm

from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.enums import LengthUnits
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.loop_closure import geographic_projection
from openspeleo_lib.loop_closure.presets import (
    InverseLengthWeightedLeastSquaresHorizontalSolver,
)
from openspeleo_lib.models import Shot
from tests.test_loop_closure_ground_truth import CASES
from tests.test_loop_closure_ground_truth import read_stalagmight
from tests.utils import make_synthetic_geolocation_survey


@pytest.mark.parametrize("algorithm", LoopClosureAlgorithm.variants())
@pytest.mark.parametrize("unit", [LengthUnits.METERS, LengthUnits.FEET])
@pytest.mark.parametrize("virtual", [False, True])
@pytest.mark.parametrize(
    ("vectors", "variances"),
    [
        ([(10, 0), (0, 20), (-30, 0)], ["10", "20", "30"]),
        ([(0, 0), (0.03, 0.04), (0.3, 0.4)], ["0.1", "0.1", "0.5"]),
    ],
)
def test_weighted_ring_matches_exact_lagrange_solution(
    algorithm, unit, virtual, vectors, variances
):
    source = make_synthetic_geolocation_survey()
    source.unit = unit
    source.use_magnetic_azimuth = False
    factor = 0.3048 if unit == LengthUnits.FEET else 1.0
    section = source.sections[0]
    section.shots[:] = section.shots[:1]
    section.shots[0].depth = 5 / factor
    for i, (dx, dy) in enumerate(vectors):
        shot = Shot(
            id_start=i + 1,
            id_stop=i + 2,
            length=math.hypot(dx, dy) / factor,
            depth=5 / factor,
            azimuth=math.degrees(math.atan2(dx, dy)) % 360,
            shot_type=ArianeShotType.VIRTUAL
            if virtual and i == 1
            else ArianeShotType.REAL,
        )
        shot.section = section
        section.shots.append(shot)
    closure = Shot(id_start=4, id_stop=1, shot_type=ArianeShotType.CLOSURE)
    closure.section = section
    section.shots.append(closure)
    before = source.model_dump_json()
    solver = replace(
        InverseLengthWeightedLeastSquaresHorizontalSolver,
        algorithm=algorithm,
        source_is_fresh=True,
    )
    snapshot = solver.prepare(source)
    result = snapshot.solve()
    points = dict(result.report.coordinates)
    # For a ring, Lagrange multipliers distribute the misclosure in direct
    # proportion to each edge's variance (the inverse observation precision).
    variance = [Fraction(v) for v in variances]
    total = sum(variance)
    displacements = [tuple(Fraction(str(v)) for v in vector) for vector in vectors]
    misclosure = [sum(vector[axis] for vector in displacements) for axis in (0, 1)]
    expected = [Fraction(0), Fraction(0)]
    assert points["1"] == pytest.approx((0, 0, -5), abs=1e-9)
    for i, vector in enumerate(displacements):
        expected = [
            expected[axis] + vector[axis] - misclosure[axis] * variance[i] / total
            for axis in (0, 1)
        ]
        assert points[str(i + 2)][:2] == pytest.approx(
            [float(v) for v in expected], abs=1e-9
        )
        assert points[str(i + 2)][2] == pytest.approx(-5)
    assert len(result.report.observations) == 3
    objective = float(sum(value**2 for value in misclosure) / total)
    assert orjson.loads(result.report.to_json())["diagnostics"][
        "objective"
    ] == pytest.approx(objective, abs=1e-9)
    assert survey_to_geojson(source, loop_closure_solver=solver) == survey_to_geojson(
        source, loop_closure_solver=solver
    )
    assert source.model_dump_json() == before


def test_derived_start_is_fixed_without_becoming_explicit_evidence():
    source = make_synthetic_geolocation_survey(child_type=ArianeShotType.START)
    source.use_magnetic_azimuth = False
    before = source.model_dump_json()
    solver = replace(
        InverseLengthWeightedLeastSquaresHorizontalSolver, source_is_fresh=True
    )
    snapshot = solver.prepare(source)
    assert snapshot.explicit_coordinate_ids == frozenset({1})
    assert dict(snapshot.coordinate_origins)[4242] == "unpopulated"
    points = dict(snapshot.solve().report.coordinates)
    assert points["4242"][:2] == pytest.approx((10, 0), abs=1e-8)
    assert source.model_dump_json() == before


def test_explicit_connected_coordinates_remain_authoritative():
    source = make_synthetic_geolocation_survey(child_coordinates=(40, -70))
    solver = replace(
        InverseLengthWeightedLeastSquaresHorizontalSolver, source_is_fresh=True
    )
    points = dict(solver.prepare(source).solve().report.coordinates)
    assert points["4242"][:2] == pytest.approx((0, 0), abs=1e-10)


def test_floating_component_keeps_unadjusted_centroid():
    source = make_synthetic_geolocation_survey(child_id=2, child_excluded=True)
    source.use_magnetic_azimuth = False
    section = source.sections[0]
    for start, stop in [(2, 3), (3, 4)]:
        shot = Shot(id_start=start, id_stop=stop, length=10, depth=0, azimuth=90)
        shot.section = section
        section.shots.append(shot)
    before = source.model_dump_json()
    measured = source.model_copy(deep=True)
    survey_to_geojson(measured)
    forward, _ = geographic_projection((40, -70))
    expected = [
        forward.transform(s.longitude, s.latitude)
        for s in measured.shots
        if s.id_stop in (3, 4)
    ]
    solver = replace(
        InverseLengthWeightedLeastSquaresHorizontalSolver, source_is_fresh=True
    )
    points = dict(solver.prepare(source).solve().report.coordinates)
    for axis in (0, 1):
        assert sum(points[str(i)][axis] for i in (3, 4)) / 2 == pytest.approx(
            sum(p[axis] for p in expected) / 2, abs=1e-9
        )
    assert source.model_dump_json() == before


def test_common_models_from_native_reader_use_the_same_weighted_solver(tmp_path):

    source = read_stalagmight(tmp_path, CASES["misclosed_ring"])
    before = source.model_dump_json()
    solver = replace(InverseLengthWeightedLeastSquaresHorizontalSolver)
    report = solver.prepare(source).solve().report
    diagnostics = orjson.loads(report.to_json())["diagnostics"]
    assert diagnostics["objective"] == pytest.approx(
        CASES["misclosed_ring"]["objective"]
    )
    assert not diagnostics["calibrated_statistics_eligible"]
    assert len(survey_to_geojson(source, loop_closure_solver=solver)["features"]) == 4
    assert source.model_dump_json() == before
