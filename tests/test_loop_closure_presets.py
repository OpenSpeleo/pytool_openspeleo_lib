"""Presets are immutable configurations of the single public solver type."""

from dataclasses import FrozenInstanceError
from dataclasses import replace

import orjson
import pytest
from cave_closure import LoopClosureMode
from cave_closure import ValidationError

from openspeleo_lib import LoopClosureSolver
from openspeleo_lib import LoopClosureWeighting
from openspeleo_lib import VirtualShotPolicy
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.loop_closure import geographic_projection
from openspeleo_lib.loop_closure import loop_closed_survey_to_geojson
from openspeleo_lib.loop_closure.presets import PRESETS
from openspeleo_lib.loop_closure.presets import InverseLengthWeightedL1SpatialSolver
from openspeleo_lib.loop_closure.presets import (
    InverseLengthWeightedLeastSquaresHorizontalSolver,
)
from openspeleo_lib.loop_closure.presets import LeastSquaresHorizontalSolver
from openspeleo_lib.loop_closure.presets import LeastSquaresSpatialSolver
from openspeleo_lib.loop_closure.presets import (
    TraverseQualityWeightedLeastSquaresSpatialSolver,
)
from openspeleo_lib.models import Shot
from tests.utils import make_synthetic_geolocation_survey


def close_to_start(source):
    closure = Shot(id_start=1, id_stop=4242, shot_type=ArianeShotType.CLOSURE)
    closure.section = source.sections[0]
    source.sections[0].shots.append(closure)


def test_presets_are_named_instances_of_one_solver_type():
    assert len(PRESETS) == 7
    assert all(type(solver) is LoopClosureSolver for solver in PRESETS.values())
    assert all(solver.name == name for name, solver in PRESETS.items())
    assert LeastSquaresHorizontalSolver.mode == LoopClosureMode.HORIZONTAL
    assert LeastSquaresSpatialSolver.mode == LoopClosureMode.SPATIAL
    with pytest.raises(TypeError):
        PRESETS["Other"] = LoopClosureSolver()
    with pytest.raises(FrozenInstanceError):
        LeastSquaresHorizontalSolver.name = "Other"


def test_custom_configuration_reproduces_preset_without_a_subclass():
    source = make_synthetic_geolocation_survey()
    custom = LoopClosureSolver(
        name="Custom",
        weighting=LoopClosureWeighting.INVERSE_LENGTH,
        virtual_shot_policy=VirtualShotPolicy.MEASURED,
        fix_start_positions=True,
        preserve_floating_xy_centroids=True,
        skip_missing_origins=True,
        source_is_fresh=True,
    )
    configured = replace(
        InverseLengthWeightedLeastSquaresHorizontalSolver, source_is_fresh=True
    )
    assert type(configured) is LoopClosureSolver
    assert not InverseLengthWeightedLeastSquaresHorizontalSolver.source_is_fresh
    assert (
        configured.prepare(source).solve().report.to_json()
        == custom.prepare(source).solve().report.to_json()
    )


def test_l1_preserves_short_leg_controls_aliases_and_source():
    source = make_synthetic_geolocation_survey()
    source.use_magnetic_azimuth = False
    root, middle = source.sections[0].shots
    middle.length = 5.0
    middle.azimuth = 90.0
    middle.depth = middle.depth_start = 0.0
    _, inverse = geographic_projection((root.latitude, root.longitude))
    longitude, latitude = inverse.transform(24.0, 0.0)
    end = Shot(
        id_start=middle.id_stop,
        id_stop=9999,
        length=15.0,
        azimuth=90.0,
        depth=0.0,
        latitude=latitude,
        longitude=longitude,
        shot_type=ArianeShotType.REAL,
    )
    alias = Shot(id_start=root.id_stop, id_stop=1234, shot_type=ArianeShotType.CLOSURE)
    for shot in (end, alias):
        shot.section = source.sections[0]
        source.sections[0].shots.append(shot)
    before = source.model_dump_json()
    solver = replace(
        InverseLengthWeightedL1SpatialSolver,
        source_is_fresh=True,
        vertical_controls={root.id_stop: 0.0, end.id_stop: 4.0},
    )
    snapshot = solver.prepare(source)
    result = snapshot.solve()
    points = dict(result.report.coordinates)
    assert points[str(middle.id_stop)] == pytest.approx((5.0, 0.0, 0.0), abs=1e-8)
    assert points[str(end.id_stop)] == pytest.approx((24.0, 0.0, 4.0), abs=1e-8)
    assert points[str(alias.id_stop)] == points[str(root.id_stop)]
    assert solver.to_geojson(source) == loop_closed_survey_to_geojson(
        snapshot, result, source=source
    )
    assert source.model_dump_json() == before


@pytest.mark.parametrize("weighting", LoopClosureWeighting)
@pytest.mark.parametrize("policy", VirtualShotPolicy)
def test_virtual_shot_policy_is_independent_of_weighting(weighting, policy):
    source = make_synthetic_geolocation_survey(child_type=ArianeShotType.VIRTUAL)
    close_to_start(source)
    traverse = weighting == LoopClosureWeighting.TRAVERSE_QUALITY_INVERSE_SQUARED_LENGTH
    solver = (
        replace(
            TraverseQualityWeightedLeastSquaresSpatialSolver,
            mode=LoopClosureMode.HORIZONTAL,
            virtual_shot_policy=policy,
            source_is_fresh=True,
        )
        if traverse
        else LoopClosureSolver(
            weighting=weighting, virtual_shot_policy=policy, source_is_fresh=True
        )
    )
    if policy == VirtualShotPolicy.HARD_OFFSET:
        with pytest.raises(ValueError if traverse else ValidationError):
            solver.prepare(source)
    else:
        report = solver.prepare(source).solve().report
        expected_observations = (
            0 if weighting == LoopClosureWeighting.LENGTH_AZIMUTH_DIAGONAL else 1
        )
        assert len(report.observations) == expected_observations
        objective = orjson.loads(report.to_json())["diagnostics"]["objective"]
        if weighting == LoopClosureWeighting.LENGTH_AZIMUTH_DIAGONAL:
            assert objective == 0
        else:
            assert objective == pytest.approx(
                1
                if traverse
                else 10
                if weighting == LoopClosureWeighting.INVERSE_LENGTH
                else 100
            )


def test_inverse_length_weights_do_not_implicitly_fix_starts():
    source = make_synthetic_geolocation_survey(child_type=ArianeShotType.START)
    solver = LoopClosureSolver(
        weighting=LoopClosureWeighting.INVERSE_LENGTH, source_is_fresh=True
    )
    with pytest.raises(ValidationError, match="uncontrolled translation"):
        solver.prepare(source)
    report = replace(solver, fix_start_positions=True).prepare(source).solve().report
    assert len(report.coordinates) == 2


@pytest.mark.parametrize("cap", [2, 10, 40])
def test_inverse_length_cap_is_configurable(cap):
    source = make_synthetic_geolocation_survey()
    source.sections[0].shots[1].length = 0.05
    close_to_start(source)
    solver = LoopClosureSolver(
        weighting=LoopClosureWeighting.INVERSE_LENGTH,
        inverse_length_weight_cap=cap,
        source_is_fresh=True,
    )
    report = solver.prepare(source).solve().report
    assert orjson.loads(report.to_json())["diagnostics"]["objective"] == pytest.approx(
        min(cap, 20) * 0.05**2
    )


def test_inverse_length_weighting_supports_spatial_hard_offsets():
    source = make_synthetic_geolocation_survey(child_type=ArianeShotType.VIRTUAL)
    solver = LoopClosureSolver(
        weighting=LoopClosureWeighting.INVERSE_LENGTH,
        mode=LoopClosureMode.SPATIAL,
        vertical_controls={1: 3.0},
        source_is_fresh=True,
    )
    report = solver.prepare(source).solve().report
    assert len(report.observations) == 0
    assert all(point[2] == pytest.approx(3) for _, point in report.coordinates)


@pytest.mark.parametrize("cap", [0, -1, float("inf"), float("nan")])
def test_invalid_weight_caps_are_rejected(cap):
    solver = LoopClosureSolver(inverse_length_weight_cap=cap)
    with pytest.raises(ValueError, match="positive and finite"):
        solver.prepare(make_synthetic_geolocation_survey())


def test_inverse_length_weights_reject_ignored_sigma():
    solver = LoopClosureSolver(weighting=LoopClosureWeighting.INVERSE_LENGTH, sigma_m=2)
    with pytest.raises(ValueError, match="sigma_m only applies"):
        solver.prepare(make_synthetic_geolocation_survey())
