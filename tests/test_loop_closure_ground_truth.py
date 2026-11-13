"""Public, independently generated Ariane-style horizontal solver regressions."""

import json
import math
import zipfile
from pathlib import Path

import pytest
from cave_closure import LoopClosureAlgorithm
from openspeleo_core import ariane_core

from openspeleo_lib import LoopClosureSolver
from openspeleo_lib.commands.convert import convert
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.enums import LengthUnits
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.interfaces import StalagmightInterface
from openspeleo_lib.loop_closure import geographic_projection
from tests.loop_closure_reference import generate
from tests.stalagmight_helpers import write_stalx

GOLDEN = Path(__file__).parent / "artifacts" / "loop_closure_ground_truth.json"
CASES = json.loads(GOLDEN.read_text())


def read_ariane(tmp_path, case):
    common = {"Section": "Origin", "Date": "2025-01-01", "Depth": 2}
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
    for index, (start, stop, dx, dy) in enumerate(case["edges"]):
        records.append(
            {
                **common,
                "Section": f"edge:{index}",
                "ID": stop,
                "FromID": start,
                "Type": "REAL",
                "Length": 5,
                "Azimut": math.degrees(math.atan2(dx, dy)) % 360,
            }
        )
    for start, stop in case["closures"]:
        records.append({**common, "ID": stop, "FromID": start, "Type": "CLOSURE"})
    path = tmp_path / "reference.tml"
    xml = ariane_core.dict_to_xml_str(
        {"unit": "m", "Data": {"SurveyData": records}}, root_name="CaveFile"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Data.xml", xml)
    source = ArianeInterface.from_file(path)
    source.use_magnetic_azimuth = False
    return source


def read_stalagmight(tmp_path, case):
    sections, occurrences = [], {}
    for index, (start, stop, dx, dy) in enumerate(case["edges"]):
        section_id = 100 + index
        sections.append(
            {
                "id": section_id,
                "name": f"edge:{index}",
                "shots": [
                    {
                        "length": 5,
                        "depth_in": 2,
                        "depth_out": 2,
                        "azimuth_in": math.degrees(math.atan2(dx, dy)) % 360,
                    }
                ],
            }
        )
        occurrences.setdefault(start, []).append((section_id, 0))
        occurrences.setdefault(stop, []).append((section_id, 1))
    merges = []
    for stations in occurrences.values():
        for station in stations[1:]:
            merges.append(
                (len(merges) + 1, *stations[0], *station, "2025-01-01T00:00:00Z")
            )
    for start, stop in case["closures"]:
        merges.append(
            (
                len(merges) + 1,
                *occurrences[start][0],
                *occurrences[stop][0],
                "2025-01-01T00:00:00Z",
            )
        )
    path = write_stalx(
        tmp_path / "reference.stalx",
        sections,
        [(1, *occurrences[1][0], 40.0, -70.0, 0.0)],
        merges,
    )
    return StalagmightInterface.from_file(path)


def test_ground_truth_regeneration_is_stable():
    assert generate() == GOLDEN.read_text()


@pytest.mark.parametrize("reverse_sections", [False, True])
@pytest.mark.parametrize("case_name", CASES)
@pytest.mark.parametrize("reader", [read_ariane, read_stalagmight])
@pytest.mark.parametrize("unit", [LengthUnits.METERS, LengthUnits.FEET])
@pytest.mark.parametrize(
    "algorithm",
    [
        LoopClosureAlgorithm.LSE_REDUCED_PCG,
        LoopClosureAlgorithm.LSE_UNREDUCED_PCG,
        LoopClosureAlgorithm.LSE_SPARSE_QR,
        LoopClosureAlgorithm.LSE_SPARSE_CHOLESKY,
    ],
)
def test_reader_model_against_ground_truth(
    tmp_path, case_name, reader, unit, algorithm, *, reverse_sections
):
    case = CASES[case_name]
    source = reader(tmp_path, case)
    if unit == LengthUnits.FEET:
        for shot in source.shots:
            shot.length /= 0.3048
            shot.depth /= 0.3048
            if shot.depth_start is not None:
                shot.depth_start /= 0.3048
        source.unit = unit
    if reverse_sections:
        source.sections.reverse()
    before = source.model_dump_json()
    solver = LoopClosureSolver(algorithm=algorithm, sigma_m=math.sqrt(5))
    snapshot = solver.prepare(source)
    first, repeated = snapshot.solve(), snapshot.solve()
    assert first.report.to_json() == repeated.report.to_json()
    diagnostics = json.loads(first.report.to_json())["diagnostics"]
    assert diagnostics["objective"] == pytest.approx(case["objective"], abs=1e-10)
    points = dict(first.report.coordinates)
    for section in source.sections:
        for shot in section.shots:
            if shot.shot_type != ArianeShotType.REAL:
                continue
            index = int(section.name.split(":")[1])
            start, stop, _, _ = case["edges"][index]
            expected = [case["coordinates"][str(i)] for i in (start, stop)]
            actual = [points[str(i)][:2] for i in (shot.id_start, shot.id_stop)]
            assert (
                min(
                    sum(math.dist(a, b) for a, b in zip(actual, order, strict=True))
                    for order in (expected, expected[::-1])
                )
                < 1e-8
            )
            assert points[str(shot.id_stop)][2] == pytest.approx(-2)
    exported = survey_to_geojson(source, loop_closure_solver=solver)
    assert exported == survey_to_geojson(source, loop_closure_solver=solver)
    project, _ = geographic_projection((40, -70))
    legs = [f for f in exported["features"] if f["geometry"]["type"] == "LineString"]
    assert len(legs) == len(case["edges"])
    for feature in legs:
        index = int(feature["properties"]["name"].split(":")[1])
        start, stop, _, _ = case["edges"][index]
        expected = [case["coordinates"][str(i)] for i in (start, stop)]
        actual = [
            project.transform(*point) for point in feature["geometry"]["coordinates"]
        ]
        # The native adapter may reverse a leg while traversing the graph.
        assert (
            min(
                sum(math.dist(a, b) for a, b in zip(actual, order, strict=True))
                for order in (expected, expected[::-1])
            )
            < 0.04
        )
        assert feature["properties"]["depth"] == 7
    assert source.model_dump_json() == before


@pytest.mark.parametrize("reader", [read_ariane, read_stalagmight])
def test_default_export_never_prepares_solver(tmp_path, monkeypatch, reader):
    source = reader(tmp_path, CASES["misclosed_ring"])

    def forbidden(*args, **kwargs):
        pytest.fail("Default measured export invoked loop closure")

    monkeypatch.setattr("openspeleo_lib.loop_closure.prepare_loop_closure", forbidden)
    assert len(survey_to_geojson(source)["features"]) == 4


@pytest.mark.parametrize("reader", [read_ariane, read_stalagmight])
def test_cli_opt_in_matches_common_model_export(tmp_path, monkeypatch, reader):
    monkeypatch.setattr("openspeleo_lib.models.get_declination", lambda **kwargs: 0.0)
    source = reader(tmp_path, CASES["misclosed_ring"])
    path = tmp_path / ("reference.tml" if reader == read_ariane else "reference.stalx")
    measured_output = tmp_path / "measured.geojson"
    adjusted_output = tmp_path / "adjusted.geojson"
    args = ["-i", str(path), "-f", "geojson"]
    convert([*args, "-o", str(measured_output)])
    convert(
        [
            *args,
            "-o",
            str(adjusted_output),
            "--loop-closure",
            "--algorithm",
            "LSE_SPARSE_QR",
            "--sigma-m",
            str(math.sqrt(5)),
        ]
    )
    solver = LoopClosureSolver(
        algorithm=LoopClosureAlgorithm.LSE_SPARSE_QR, sigma_m=math.sqrt(5)
    )
    expected = survey_to_geojson(source, loop_closure_solver=solver)
    assert json.loads(adjusted_output.read_text()) == json.loads(json.dumps(expected))
    assert measured_output.read_bytes() != adjusted_output.read_bytes()
