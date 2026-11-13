"""Stalagmight topology normalization belongs to the OpenSpeleo adapter."""

import json
import sqlite3
from contextlib import closing

import pytest
from cave_closure import LoopClosureAlgorithm
from cave_closure import LoopClosureMode

from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.interfaces import StalagmightInterface
from openspeleo_lib.loop_closure import prepare_loop_closure
from tests.stalagmight_helpers import GEOGRAPHIC_SCHEMA
from tests.stalagmight_helpers import SCHEMA


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "native.stalx"
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(SCHEMA + GEOGRAPHIC_SCHEMA)
        connection.execute("INSERT INTO zero_datums VALUES(1,42,0,40,-70,0)")
    return path


def execute(path, sql, parameters=()):
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(sql, parameters)


def schema19(database, *, origins=None, identities=None):
    execute(database, "PRAGMA user_version=19")
    execute(database, "UPDATE project SET schema_version=19")
    numbering = {"next": 4, "identities": identities or {"42:legacy:0": 1}}
    graph = {
        "initialized": True,
        "explicit": True,
        "origins": origins or {"1": None},
        "root_positions": {"1": [123.0, 456.0]},
        "geometry_locks": {"1": True},
    }
    for key, value in (("shot_numbering", numbering), ("shot_graph", graph)):
        execute(
            database,
            "INSERT INTO project_settings VALUES (?,?)",
            (key, json.dumps(value)),
        )


@pytest.mark.parametrize(
    "algorithm",
    [
        LoopClosureAlgorithm.LSE_REDUCED_PCG,
        LoopClosureAlgorithm.LSE_UNREDUCED_PCG,
        LoopClosureAlgorithm.LSE_SPARSE_QR,
        LoopClosureAlgorithm.LSE_SPARSE_CHOLESKY,
    ],
)
def test_native_loop_closure_preserves_cycles_without_layout_cuts(database, algorithm):
    execute(database, "UPDATE shots SET length=10, depth_in=0, depth_out=0")
    execute(
        database,
        "INSERT INTO shots SELECT 100, section_id, 1, azimuth_in, azimuth_out, "
        "length, depth_in, depth_out, pitch_in, pitch_out, left_distance, "
        "right_distance, up_distance, down_distance, comment, kind, marker_index, "
        "temperature, NULL FROM shots",
    )
    schema19(
        database,
        origins={"1": 2, "2": 1},
        identities={"42:legacy:0": 1, "42:legacy:1": 2},
    )
    native = StalagmightInterface.from_file(database)
    before = native.model_dump_json()
    snapshot = prepare_loop_closure(
        native,
        algorithm=algorithm,
        mode=LoopClosureMode.HORIZONTAL,
        sigma_m=1.0,
    )
    result = snapshot.solve()
    points = dict(result.report.coordinates)
    for shot in native.shots:
        if shot.shot_type is ArianeShotType.CLOSURE:
            assert points[str(shot.id_start)][:2] == points[str(shot.id_stop)][:2]
    assert len(result.report.observations) == 2
    assert native.model_dump_json() == before


def test_schema19_override_precedence_ignores_layout_and_editing_locks(database):
    execute(
        database,
        "UPDATE shots SET length=10, depth_in=0, depth_out=0, "
        "azimuth_in=90, azimuth_out=90",
    )
    execute(
        database,
        "UPDATE sections SET azimuth_north='true', azimuth_correction=20, "
        "azimuth_source='manual'",
    )
    schema19(database)
    graph = {
        "initialized": True,
        "explicit": True,
        "origins": {"1": None},
        "root_positions": {"1": [9999.0, 9999.0]},
        "geometry_locks": {"1": True},
        "azimuth_overrides": {
            "1": {"north": "true", "correction": 30.0, "source": "manual"}
        },
    }
    execute(
        database,
        "UPDATE project_settings SET value=? WHERE key='shot_graph'",
        (json.dumps(graph),),
    )
    source = StalagmightInterface.from_file(database)
    result = prepare_loop_closure(
        source,
        mode=LoopClosureMode.HORIZONTAL,
        sigma_m=1.0,
    ).solve()
    points = dict(result.report.coordinates)
    shot = next(shot for shot in source.shots if shot.shot_type is ArianeShotType.REAL)
    actual = [
        v - u
        for u, v in zip(
            points[str(shot.id_start)], points[str(shot.id_stop)], strict=True
        )
    ]
    assert actual == pytest.approx((8.660254037844386, -5.0, 0.0), abs=1e-12)
