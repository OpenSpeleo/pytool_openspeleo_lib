from __future__ import annotations

import pytest

from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.enums import LengthUnits
from openspeleo_lib.geojson import MAX_GEOLOCATION_DISCREPANCY_M
from openspeleo_lib.geojson import InconsistentShotCoordinatesError
from openspeleo_lib.geojson import length_to_meters
from openspeleo_lib.geojson import propagate_position
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.models import Shot
from tests.utils import make_synthetic_geolocation_survey


def set_child_endpoint_discrepancy(survey, discrepancy_m: float):
    root, child = list(survey.shots)
    expected_coordinates = propagate_position(
        base_lat=root.latitude,
        base_lon=root.longitude,
        length_m=length_to_meters(child.length, survey.unit),
        azimuth_deg=child.azimuth_true,
    )
    supplied_coordinates = propagate_position(
        base_lat=expected_coordinates[0],
        base_lon=expected_coordinates[1],
        length_m=discrepancy_m,
        azimuth_deg=0.0,
    )
    child.latitude, child.longitude = supplied_coordinates
    return expected_coordinates, supplied_coordinates


def test_rejects_synthetic_swapped_coordinates_with_shot_details():
    survey = make_synthetic_geolocation_survey(
        child_coordinates=(-70.0, 40.0),
    )

    with pytest.raises(InconsistentShotCoordinatesError) as exc_info:
        survey_to_geojson(survey)

    error = exc_info.value
    assert error.shot.id_stop == 4242
    assert error.supplied_coordinates == (-70.0, 40.0)
    assert error.calculated_coordinates[0] == pytest.approx(40.0, abs=0.001)
    assert error.calculated_coordinates[1] == pytest.approx(-70.0, abs=0.001)
    assert error.discrepancy_m > 1_000_000
    assert error.max_discrepancy_m == MAX_GEOLOCATION_DISCREPANCY_M
    assert str(error).startswith("[Shot ID=4242]")
    assert "supplied=" in str(error)
    assert "calculated=" in str(error)
    assert f"discrepancy={error.discrepancy_m:,.3f} m" in str(error)
    assert "500.000 m" in str(error)


@pytest.mark.parametrize(
    ("discrepancy_m", "should_raise"),
    [
        (499.0, False),
        (500.0, False),
        (500.01, True),
    ],
)
def test_fixed_discrepancy_boundary(discrepancy_m: float, should_raise: bool):
    survey = make_synthetic_geolocation_survey()
    _, supplied_coordinates = set_child_endpoint_discrepancy(
        survey,
        discrepancy_m=discrepancy_m,
    )

    if should_raise:
        with pytest.raises(InconsistentShotCoordinatesError):
            survey_to_geojson(survey)
        return

    data = survey_to_geojson(survey)
    child_feature = next(
        feature for feature in data["features"] if feature["properties"]["id"] == 4242
    )
    endpoint = child_feature["geometry"]["coordinates"][1]
    assert endpoint[0] == pytest.approx(supplied_coordinates[1], abs=1e-7)
    assert endpoint[1] == pytest.approx(supplied_coordinates[0], abs=1e-7)


@pytest.mark.parametrize("unit", [LengthUnits.METERS, LengthUnits.FEET])
def test_guard_is_unit_independent(unit: LengthUnits):
    survey = make_synthetic_geolocation_survey(unit=unit)
    set_child_endpoint_discrepancy(survey, discrepancy_m=501.0)

    with pytest.raises(InconsistentShotCoordinatesError) as exc_info:
        survey_to_geojson(survey)

    assert exc_info.value.discrepancy_m == pytest.approx(501.0, abs=1e-6)


def test_normal_propagation_and_multiple_roots_are_unchanged():
    survey = make_synthetic_geolocation_survey()
    root, child = list(survey.shots)
    expected_coordinates = propagate_position(
        base_lat=root.latitude,
        base_lon=root.longitude,
        length_m=length_to_meters(child.length, survey.unit),
        azimuth_deg=child.azimuth_true,
    )
    second_root = Shot(
        id_stop=2,
        id_start=-1,
        length=0.0,
        depth=0.0,
        azimuth=0.0,
        inclination=0.0,
        latitude=41.0,
        longitude=-71.0,
        shot_type=ArianeShotType.START,
    )
    second_root.section = survey.sections[0]
    survey.sections[0].shots.append(second_root)

    data = survey_to_geojson(survey)

    assert (child.latitude, child.longitude) == pytest.approx(expected_coordinates)
    assert len(data["features"]) == 3
    assert (second_root.latitude, second_root.longitude) == (41.0, -71.0)


def test_connected_anchor_without_resolved_parent_is_not_compared():
    survey = make_synthetic_geolocation_survey(
        child_coordinates=(39.0, -69.0),
        child_id_start=999,
    )

    data = survey_to_geojson(survey)

    child_feature = next(
        feature for feature in data["features"] if feature["properties"]["id"] == 4242
    )
    assert child_feature["geometry"]["type"] == "Point"


def test_excluded_virtual_anchor_is_still_validated():
    survey = make_synthetic_geolocation_survey(
        child_coordinates=(-70.0, 40.0),
        child_type=ArianeShotType.VIRTUAL,
        child_excluded=True,
    )

    with pytest.raises(InconsistentShotCoordinatesError, match=r"Shot ID=4242"):
        survey_to_geojson(survey)


def test_reports_lowest_inconsistent_shot_id_deterministically():
    survey = make_synthetic_geolocation_survey(
        child_coordinates=(-70.0, 40.0),
    )
    first_bad_shot = survey.sections[0].shots[1].model_copy(update={"id_stop": 1234})
    first_bad_shot.section = survey.sections[0]
    survey.sections[0].shots.append(first_bad_shot)

    with pytest.raises(InconsistentShotCoordinatesError) as exc_info:
        survey_to_geojson(survey)

    assert exc_info.value.shot.id_stop == 1234
