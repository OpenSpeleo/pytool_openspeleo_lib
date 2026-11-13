"""Export regressions; normal test runs never regenerate golden assets."""

import math

import orjson
import pytest

from openspeleo_lib.constants import OSPL_GEOJSON_DIGIT_PRECISION
from openspeleo_lib.loop_closure import LoopClosureMethod
from openspeleo_lib.loop_closure import LoopClosureSolver
from tests.export_goldens import ARTIFACTS
from tests.export_goldens import EXPORTS
from tests.export_goldens import FIXTURES
from tests.export_goldens import golden_name
from tests.export_goldens import read_source
from tests.export_goldens import write_export

# One unit at output precision, plus floating-point subtraction roundoff. This is
# an absolute angular tolerance; relative tolerances grow with longitude.
COORDINATE_TOLERANCE = 10**-OSPL_GEOJSON_DIGIT_PRECISION + 1e-12
CG_COORDINATE_TOLERANCE = 5 * 10**-OSPL_GEOJSON_DIGIT_PRECISION + 1e-12


def coordinate_tolerance(export):
    if isinstance(export, LoopClosureSolver) and export.method in {
        LoopClosureMethod.REFERENCE_CG,
        LoopClosureMethod.TRAVERSE_QUALITY_CG,
    }:
        return CG_COORDINATE_TOLERANCE
    return COORDINATE_TOLERANCE


def assert_geojson_matches(
    actual, expected, path=(), *, tolerance=COORDINATE_TOLERANCE
):
    """Keep structure and properties exact; allow coordinate rounding noise."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            pytest.fail(f"{path}: object keys differ", pytrace=False)
        for key, value in expected.items():
            assert_geojson_matches(
                actual[key], value, (*path, key), tolerance=tolerance
            )
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            pytest.fail(f"{path}: array shape differs", pytrace=False)
        for index, value in enumerate(expected):
            assert_geojson_matches(
                actual[index], value, (*path, index), tolerance=tolerance
            )
    elif (
        path[:1] == ("features",)
        and path[2:4] == ("geometry", "coordinates")
        and type(expected) in (float, int)
        and type(actual) in (float, int)
    ):
        if not math.isclose(actual, expected, rel_tol=0, abs_tol=tolerance):
            pytest.fail(
                f"{path}: coordinate differs: {actual} != {expected}", pytrace=False
            )
    elif actual != expected or type(actual) is not type(expected):
        pytest.fail(f"{path}: value differs", pytrace=False)


@pytest.fixture(scope="module", params=FIXTURES, ids=[prefix for _, prefix in FIXTURES])
def source_case(request):
    filename, prefix = request.param
    original_bytes = (ARTIFACTS / filename).read_bytes()
    source = read_source(filename)
    original_model = source.model_dump_json()
    yield source, prefix
    assert source.model_dump_json() == original_model
    assert (ARTIFACTS / filename).read_bytes() == original_bytes


@pytest.mark.parametrize(
    "export",
    EXPORTS,
    ids=[export if isinstance(export, str) else export.name for export in EXPORTS],
)
def test_export_matches_golden(source_case, export, tmp_path):
    source, prefix = source_case
    name = golden_name(prefix, export)
    target = tmp_path / name
    write_export(source, export, target)
    expected = (ARTIFACTS / name).read_bytes()
    actual = target.read_bytes()
    if actual == expected:
        return
    if export == "json":
        pytest.fail(f"{name}: export differs from its checked-in golden", pytrace=False)
    assert_geojson_matches(
        orjson.loads(actual),
        orjson.loads(expected),
        tolerance=coordinate_tolerance(export),
    )


def coordinate_feature(coordinates, *, depth=1.0):
    return {
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": coordinates},
                "properties": {"depth": depth},
            }
        ]
    }


@pytest.mark.parametrize("delta", [-1e-7, 0, 1e-7])
def test_golden_comparison_accepts_coordinate_rounding(delta):
    assert_geojson_matches(
        coordinate_feature([-70.0 + delta, 40.0]),
        coordinate_feature([-70.0, 40.0]),
    )


@pytest.mark.parametrize(
    "actual",
    [
        coordinate_feature([-70.0 + 2e-7, 40.0]),
        coordinate_feature([-70.0, 40.0], depth=1.00000001),
        coordinate_feature([-70.0]),
        coordinate_feature([[-70.0, 40.0]]),
        coordinate_feature([True, 40.0]),
        coordinate_feature([float("nan"), 40.0]),
        {"features": []},
        {"features": [], "extra": None},
    ],
)
def test_golden_comparison_rejects_export_changes(actual):
    with pytest.raises(pytest.fail.Exception):
        assert_geojson_matches(actual, coordinate_feature([-70.0, 40.0]))


@pytest.mark.parametrize("delta", [-5e-7, 5e-7])
def test_golden_comparison_accepts_cg_convergence_noise(delta):
    assert_geojson_matches(
        coordinate_feature([-70.0 + delta, 40.0]),
        coordinate_feature([-70.0, 40.0]),
        tolerance=CG_COORDINATE_TOLERANCE,
    )


@pytest.mark.parametrize(
    "actual",
    [
        coordinate_feature([-70.0 + 6e-7, 40.0]),
        coordinate_feature([-70.0, 40.0], depth=1.00000001),
    ],
)
def test_golden_comparison_rejects_cg_export_changes(actual):
    with pytest.raises(pytest.fail.Exception):
        assert_geojson_matches(
            actual, coordinate_feature([-70.0, 40.0]), tolerance=CG_COORDINATE_TOLERANCE
        )
