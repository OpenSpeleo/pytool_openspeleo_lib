"""Native annotation identity and endpoints survive geographic solving."""

import json
import sqlite3
from contextlib import closing
from dataclasses import replace
from uuid import uuid4

import pytest
from openspeleo_core import ariane_core

from openspeleo_lib.enums import LengthUnits
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.interfaces import StalagmightInterface
from openspeleo_lib.loop_closure.presets import (
    InverseLengthWeightedConjugateGradientHorizontalSolver,
)
from openspeleo_lib.loop_closure.presets import (
    LengthAzimuthWeightedLeastSquaresHorizontalSolver,
)
from tests.stalagmight_helpers import write_stalx
from tests.utils import make_synthetic_geolocation_survey


@pytest.mark.parametrize(
    "solver",
    [
        None,
        replace(
            InverseLengthWeightedConjugateGradientHorizontalSolver, source_is_fresh=True
        ),
    ],
)
def test_native_ariane_identity_and_measured_units(solver):
    survey = make_synthetic_geolocation_survey(unit=LengthUnits.FEET)
    shot = survey.sections[0].shots[1]
    shot.id = uuid4()
    shot.comment = "Passage !NE! and !180!"
    resolved = []
    output = survey_to_geojson(
        survey, loop_closure_solver=solver, on_resolved_shot=resolved.append
    )
    assert len(resolved) == 1
    item = resolved[0]
    assert (item.shot_id, item.from_id, item.uuid) == ("4242", "1", str(shot.id))
    assert item.namespace == ()
    assert item.length_m == pytest.approx(10.0)
    assert item.azimuth == 90.0
    assert item.comment == shot.comment
    endpoint = output["features"][1]["geometry"]["coordinates"][-1]
    assert (item.longitude, item.latitude) == pytest.approx(endpoint, abs=1e-7)


@pytest.mark.parametrize("schema", [18, 19])
@pytest.mark.parametrize("reversed_anchor", [False, True])
def test_stalagmight_native_identity_and_original_destination(
    tmp_path, schema, reversed_anchor
):
    native_uuid = str(uuid4())
    path = write_stalx(
        tmp_path / "survey.stalx",
        [
            {
                "id": 42,
                "shots": [
                    {
                        "id": 99,
                        "uuid": native_uuid,
                        "azimuth_out": 90.0,
                        "comment": "!E!",
                    }
                ],
            }
        ],
        datums=[(1, 42, int(reversed_anchor), 40.0, -70.0, 0.0)],
    )
    if schema == 19:
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute("PRAGMA user_version=19")
            connection.execute("UPDATE project SET schema_version=19")
            connection.executemany(
                "INSERT INTO project_settings VALUES (?, ?)",
                [
                    (
                        "shot_numbering",
                        json.dumps({"next": 8, "identities": {f"42:{native_uuid}": 7}}),
                    ),
                    (
                        "shot_graph",
                        json.dumps(
                            {
                                "initialized": True,
                                "explicit": True,
                                "origins": {"7": None},
                            }
                        ),
                    ),
                ],
            )
    survey = StalagmightInterface.from_file(path)
    resolved = []
    output = survey_to_geojson(
        survey,
        loop_closure_solver=LengthAzimuthWeightedLeastSquaresHorizontalSolver,
        on_resolved_shot=resolved.append,
    )
    assert len(resolved) == 1
    item = resolved[0]
    assert (item.shot_id, item.from_id, item.uuid) == (
        "99",
        "section:42:root",
        native_uuid,
    )
    assert (item.length_m, item.azimuth, item.comment) == (10.0, 90.0, "!E!")
    line = next(f for f in output["features"] if f["geometry"]["type"] == "LineString")
    endpoint = line["geometry"]["coordinates"][0 if reversed_anchor else -1]
    assert (item.longitude, item.latitude) == pytest.approx(endpoint, abs=1e-7)
    if reversed_anchor:
        assert (item.longitude, item.latitude) == pytest.approx((-70.0, 40.0))


def test_excluded_shots_do_not_resolve():
    survey = make_synthetic_geolocation_survey(child_excluded=True)
    resolved = []
    survey_to_geojson(survey, on_resolved_shot=resolved.append)
    assert resolved == []


def test_native_ariane_without_uuid_keeps_source_ids_across_reads(tmp_path):
    path = tmp_path / "survey.tmlu"
    path.write_text(
        ariane_core.dict_to_xml_str(
            {
                "unit": "m",
                "Data": {
                    "SurveyData": [
                        {
                            "ID": 50,
                            "FromID": -1,
                            "Type": "START",
                            "Section": "Dive",
                            "Date": "2025-01-01",
                            "Length": 0,
                            "Depth": 0,
                            "Azimut": 0,
                            "Latitude": 40,
                            "Longitude": -70,
                        },
                        {
                            "ID": 75,
                            "FromID": 50,
                            "Type": "REAL",
                            "Section": "Dive",
                            "Date": "2025-01-01",
                            "Length": 10,
                            "Depth": 0,
                            "Azimut": 90,
                            "Comment": "!W!",
                        },
                    ]
                },
            },
            root_name="CaveFile",
        )
    )
    resolved = []
    for _ in range(2):
        survey_to_geojson(
            ArianeInterface.from_file(path),
            loop_closure_solver=InverseLengthWeightedConjugateGradientHorizontalSolver,
            on_resolved_shot=resolved.append,
        )
    assert len(resolved) == 2
    assert resolved[0] == resolved[1]
    assert (resolved[0].shot_id, resolved[0].from_id, resolved[0].uuid) == (
        "75",
        "50",
        None,
    )


def test_stalagmight_predecessor_uses_native_row_not_sequence(tmp_path):
    path = write_stalx(
        tmp_path / "survey.stalx",
        [
            {
                "id": 42,
                "shots": [
                    {"id": 99, "azimuth_out": 90.0},
                    {"id": 750, "azimuth_out": 90.0, "comment": "!NE!"},
                ],
            }
        ],
        datums=[(1, 42, 2, 40.0, -70.0, 0.0)],
    )
    resolved = []
    survey_to_geojson(
        StalagmightInterface.from_file(path),
        loop_closure_solver=LengthAzimuthWeightedLeastSquaresHorizontalSolver,
        on_resolved_shot=resolved.append,
    )
    item = next(shot for shot in resolved if shot.comment == "!NE!")
    assert (item.shot_id, item.from_id, item.uuid) == ("750", "99", None)
    assert (item.longitude, item.latitude) == pytest.approx((-70.0, 40.0))
