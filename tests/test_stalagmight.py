"""Stalagmight normalizes to common models and measured geographic export."""

import json
import math
import shutil
import sqlite3
import zipfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from threading import Event
from threading import local
from uuid import UUID

import orjson
import pytest
from openspeleo_core import ariane_core
from pydantic import ValidationError
from stalagmight_lib import StalagmightFormatError

from openspeleo_lib.commands.convert import convert
from openspeleo_lib.constants import OSPL_SECTIONNAME_MAX_LENGTH
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.generators import UniqueValueGenerator
from openspeleo_lib.geojson import GEOD
from openspeleo_lib.geojson import InconsistentShotCoordinatesError
from openspeleo_lib.geojson import NoKnownAnchorError
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.interfaces import StalagmightInterface
from openspeleo_lib.models import Section
from openspeleo_lib.models import Shot
from openspeleo_lib.models import Survey
from tests.commands.test_command_convert import run_convert
from tests.stalagmight_helpers import write_stalx

VALID_EXAMPLE = Path(__file__).parent / "artifacts/stalagmight.stalx"
INVALID_EXAMPLE = Path(__file__).parent / "artifacts/stalagmight-invalid.stalx"
STAMP = "2026-01-01T00:00:00Z"
UUID4 = "f26c8521-2164-425d-b967-a4a4a874b69c"


def load(tmp_path, sections, datums=((1, 42, 0, 40.0, -70.0, 0.0),), merges=()):
    path = write_stalx(tmp_path / "survey.STALX", sections, datums, merges)
    return StalagmightInterface.from_file(path)


def test_single_section_metadata_and_virtual_positioning(tmp_path):
    survey = load(
        tmp_path,
        [
            {
                "id": 42,
                "date": None,
                "surveyor": "A, B",
                "shots": [
                    {"kind": 1, "uuid": UUID4, "comment": "jump"},
                    {"kind": 2},
                    {
                        "depth_in": 0.0,
                        "depth_out": 6.0,
                        "pitch_in": 30.0,
                        "comment": "shot",
                    },
                ],
            }
        ],
    )
    section = survey.sections[0]
    assert section.date is None
    assert section.surveyors == ["A, B"]
    start, jump, reference, real = section.shots
    assert jump.shot_type == reference.shot_type == ArianeShotType.VIRTUAL
    assert real.inclination == -30
    assert real.left is None
    assert real.comment == "shot"
    assert real.depth_start == 0
    assert real.length_2d(0) == 8
    assert jump.id == UUID(UUID4)
    output = survey_to_geojson(survey)
    assert [f["geometry"]["type"] for f in output["features"]] == [
        "Point",
        "LineString",
    ]
    feature = output["features"][1]
    assert feature["properties"]["color"] == "#aabbcc"
    assert set(feature["properties"]) == {"id", "depth", "name", "color"}
    assert feature["geometry"]["coordinates"][0][0] > start.longitude
    assert start.is_geolocation_known()
    assert output == survey_to_geojson(survey)


@pytest.mark.parametrize("pivot", [0, 1, 2])
def test_root_attachment_reversal_and_identity(tmp_path, pivot):
    survey = load(
        tmp_path,
        [
            {
                "id": 42,
                "direction": "out",
                "shots": [
                    {
                        "uuid": UUID4,
                        "left_distance": 2.0,
                        "right_distance": 3.0,
                        "pitch_in": 15.0,
                    },
                    {},
                ],
            }
        ],
        datums=[(1, 42, pivot, 40.0, -70.0, 0.0)],
    )
    shots = list(survey.shots)
    assert len(shots) == 3
    assert len({s.id_stop for s in shots}) == 3
    source_zero = next(s for s in shots if s.id == UUID(UUID4))
    assert source_zero.azimuth == (270 if pivot else 90)
    assert source_zero.left == (3 if pivot else 2)
    assert source_zero.inclination == (15 if pivot else -15)
    assert len(survey_to_geojson(survey)["features"]) == 3
    again = StalagmightInterface.from_file(tmp_path / "survey.STALX")
    assert survey_to_geojson(again) == survey_to_geojson(survey)


@pytest.mark.parametrize(("parent_index", "child_index"), [(0, 0), (1, 1), (2, 2)])
def test_merges_at_every_station(tmp_path, parent_index, child_index):
    survey = load(
        tmp_path,
        [{"id": 42, "shots": [{}, {}]}, {"id": 999999, "shots": [{}, {}]}],
        merges=[(1, 42, parent_index, 999999, child_index, STAMP)],
    )
    assert [s.name for s in survey.sections] == ["Repeat", "Repeat"]
    assert len(list(survey.shots)) == 5
    assert len(survey_to_geojson(survey)["features"]) == 5
    first = survey.sections[0].shots
    parent_node = first[parent_index].id_stop
    child = survey.sections[1].shots
    assert sum(s.id_start == parent_node for s in child) == (
        2 if child_index == 1 else 1
    )


def test_lowest_datum_root_and_additional_constraints(tmp_path):
    survey = load(
        tmp_path,
        [{"id": 42, "shots": [{}]}, {"id": 1, "name": None, "shots": [{}]}],
        datums=[(20, 1, 1, 40.0, -70.0, 0.0), (2, 42, 1, 40.0, -70.0, 0.0)],
        merges=[(2, 1, 1, 42, 1, STAMP), (3, 1, 0, 42, 0, STAMP)],
    )
    assert survey.sections[0].name == "Section 1"
    assert any(s.shot_type == ArianeShotType.START for s in survey.sections[1].shots)
    assert len(survey_to_geojson(survey)["features"]) == 3
    assert any(shot.shot_type is ArianeShotType.CLOSURE for shot in survey.shots)
    assert type(survey) is Survey
    assert not hasattr(survey, "_native")


def test_conflicting_anchors(tmp_path):
    with pytest.raises(ValueError, match="conflicting coordinates"):
        load(
            tmp_path,
            [{"id": 42, "shots": []}, {"id": 43, "shots": []}],
            datums=[(1, 42, 0, 40.0, -70.0, 0.0), (2, 43, 0, 41.0, -70.0, 0.0)],
            merges=[(1, 42, 0, 43, 0, STAMP)],
        )


def test_connected_anchor_consistency(tmp_path):
    survey = load(
        tmp_path,
        [{"id": 42, "shots": [{}]}],
        datums=[(1, 42, 0, 40.0, -70.0, 0.0), (2, 42, 1, 41.0, -70.0, 0.0)],
    )
    with pytest.raises(InconsistentShotCoordinatesError):
        survey_to_geojson(survey)


def test_multiple_components_and_unanchored_filtering(tmp_path):
    sections = [
        {"id": 42, "shots": [{}]},
        {"id": 43, "shots": [{}]},
        {"id": 44, "shots": [{}]},
    ]
    survey = load(
        tmp_path,
        sections,
        datums=[(1, 42, 0, 40.0, -70.0, 0.0), (2, 43, 1, 40.0, -70.0, 0.0)],
    )
    assert len(survey_to_geojson(survey)["features"]) == 4
    path = write_stalx(tmp_path / "none.stalx", sections)
    with pytest.raises(NoKnownAnchorError):
        survey_to_geojson(StalagmightInterface.from_file(path))


def test_correction_and_uuid_inheritance(tmp_path):
    survey = load(
        tmp_path,
        [
            {
                "id": 42,
                "azimuth_north": "true",
                "azimuth_correction": 12.0,
                "shots": [{"uuid": UUID4}],
            },
            {"id": 43, "shots": [{"uuid": UUID4}]},
            {
                "id": 44,
                "azimuth_north": "magnetic",
                "shots": [{"uuid": str(UUID(int=0))}],
            },
        ],
    )
    path = tmp_path / "survey.STALX"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute(
            "INSERT INTO project_settings VALUES(?,?)",
            (
                "default_azimuth_reference",
                '{"north":"true","correction":23,"source":"manual"}',
            ),
        )
    survey = StalagmightInterface.from_file(path)
    assert not survey.use_magnetic_azimuth
    assert [
        shot.azimuth for shot in survey.shots if shot.shot_type is ArianeShotType.REAL
    ] == [102, 113, 90]
    assert [s.shots[-1].id for s in survey.sections] == [UUID(UUID4), None, None]


def test_valid_and_invalid_examples_and_common_model_export():
    """Check every normalized measured leg against its source length."""
    before = INVALID_EXAMPLE.read_bytes()
    with pytest.raises(ValueError, match=r"shots row 282 section \d+ sequence \d+"):
        survey_to_geojson(StalagmightInterface.from_file(INVALID_EXAMPLE))
    valid_before = VALID_EXAMPLE.read_bytes()
    actual = json.loads(
        json.dumps(survey_to_geojson(StalagmightInterface.from_file(VALID_EXAMPLE)))
    )
    # Compare every measured common-model leg independently of traversal order.
    common = StalagmightInterface.from_file(VALID_EXAMPLE)
    measurements = {
        shot.id_stop: shot
        for shot in common.shots
        if shot.shot_type is ArianeShotType.REAL
    }
    for feature in actual["features"]:
        if feature["geometry"]["type"] != "LineString":
            continue
        shot = measurements[feature["properties"]["id"]]
        start, stop = feature["geometry"]["coordinates"]
        _, _, length = GEOD.inv(*start, *stop)
        expected_length = math.sqrt(
            shot.length**2 - (shot.depth - shot.depth_start) ** 2
        )
        assert length == pytest.approx(expected_length, abs=0.02)
    features = actual["features"]
    assert sum(f["geometry"]["type"] == "LineString" for f in features) == 467
    assert sum(f["geometry"]["type"] == "Point" for f in features) == 1
    assert INVALID_EXAMPLE.read_bytes() == before
    assert VALID_EXAMPLE.read_bytes() == valid_before


def cli_args(source, output, fmt="geojson"):
    return ["-i", str(source), "-o", str(output), "-f", fmt]


@pytest.mark.parametrize("fmt", ["json", "geojson"])
def test_cli_output_overwrite_and_beautification(tmp_path, fmt):
    source = write_stalx(
        tmp_path / "survey.STALX",
        [{"id": 42, "shots": [{}]}],
        [(1, 42, 0, 40.0, -70.0, 0.0)],
    )
    output = tmp_path / "output.json"
    args = cli_args(source, output, fmt)
    convert([*args, "--beautify"])
    assert "\n" in output.read_text()
    assert json.loads(output.read_text())
    with pytest.raises(FileExistsError):
        convert(args)
    convert([*args, "--overwrite"])
    assert "\n" not in output.read_text()


@pytest.mark.parametrize("alias", ["same", "symlink", "hardlink"])
def test_cli_aliases(tmp_path, alias):
    source = write_stalx(tmp_path / "survey.stalx", [{"id": 42, "shots": [{}]}])
    before = source.read_bytes()
    output = tmp_path / "alias.json"
    if alias == "same":
        output = source
    elif alias == "symlink":
        output.symlink_to(source)
    else:
        output.hardlink_to(source)
    with pytest.raises(ValueError, match="same file"):
        convert([*cli_args(source, output), "--overwrite"])
    assert source.read_bytes() == before


@pytest.mark.parametrize("invalid", ["geometry", "parsing"])
def test_cli_failure_preserves_outputs(tmp_path, invalid):
    source = tmp_path / "source.stalx"
    if invalid == "geometry":
        shutil.copyfile(INVALID_EXAMPLE, source)
    else:
        source.write_bytes(b"invalid SQLite")
    for existing in (False, True):
        output = tmp_path / f"{existing}.json"
        if existing:
            output.write_bytes(b"keep")
        with pytest.raises((ValueError, StalagmightFormatError)):
            convert([*cli_args(source, output), "--overwrite"])
        assert output.read_bytes() == b"keep" if existing else not output.exists()


def test_writer_unsupported(tmp_path):
    with pytest.raises(NotImplementedError):
        StalagmightInterface.to_file(None, tmp_path / "output.stalx")


def test_equivalent_ariane_and_stalagmight_geojson(tmp_path, monkeypatch):
    monkeypatch.setattr("openspeleo_lib.models.get_declination", lambda **kwargs: 0.0)
    native = load(
        tmp_path,
        [{"id": 42, "shots": [{"uuid": UUID4}]}],
        datums=[(1, 42, 0, 40.0, -70.0, 0.0)],
    )
    common = {"Section": "Repeat", "Date": "2026-01-01", "Color": "#abc", "Depth": 0}
    shots = [
        {
            **common,
            "ID": 1,
            "FromID": -1,
            "Type": "START",
            "Length": 0,
            "Azimut": 0,
            "Latitude": 40,
            "Longitude": -70,
        },
        {
            **common,
            "ID": 0,
            "FromID": 1,
            "Type": "REAL",
            "Length": 10,
            "Azimut": 90,
            "UUID": UUID4,
        },
    ]
    xml = ariane_core.dict_to_xml_str(
        {"unit": "m", "Data": {"SurveyData": shots}}, root_name="CaveFile"
    )
    path = tmp_path / "equivalent.tml"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Data.xml", xml)
    ariane = ArianeInterface.from_file(path)
    assert json.loads(json.dumps(survey_to_geojson(native))) == json.loads(
        json.dumps(survey_to_geojson(ariane))
    )


def test_cli_subprocess_nonzero_status(tmp_path):
    output = tmp_path / "output.geojson"
    result = run_convert(INVALID_EXAMPLE, output)
    assert result.returncode != 0
    assert "shots row 282" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize("pitch", [None, 15.0])
def test_adapter_model_and_json_roundtrips(tmp_path, pitch):

    survey = load(
        tmp_path,
        [{"id": 42, "date": None, "shots": [{"pitch_in": pitch}]}],
    )
    cls = type(survey)
    for roundtrip in (
        cls.model_validate(survey.model_dump()),
        cls.model_validate_json(survey.model_dump_json()),
    ):
        assert isinstance(roundtrip.sections[0], Section)
        assert all(isinstance(shot, Shot) for shot in roundtrip.shots)
        assert roundtrip.sections[0].survey is roundtrip
        assert all(shot.section is roundtrip.sections[0] for shot in roundtrip.shots)
        assert survey_to_geojson(roundtrip) == survey_to_geojson(survey)

    output = tmp_path / "roundtrip.json"
    survey.to_json(output)
    assert cls.from_json(output).model_dump() == survey.model_dump()


def test_adapter_model_rejects_invalid_nested_shots(tmp_path):

    survey = load(tmp_path, [{"id": 42, "shots": [{}]}])
    raw = survey.model_dump()
    raw["sections"][0]["shots"][1]["length"] = -1
    with pytest.raises(ValidationError, match="greater_than_equal"):
        type(survey).model_validate(raw)

    raw = survey.model_dump()
    raw["sections"][0]["shots"][1]["id_stop"] = raw["sections"][0]["shots"][0][
        "id_stop"
    ]
    with (
        UniqueValueGenerator.activate_uniqueness(),
        pytest.raises(ValidationError, match="already been registered"),
    ):
        type(survey).model_validate(raw)


def test_native_names_follow_common_model_validation(tmp_path):
    name = "native section " * OSPL_SECTIONNAME_MAX_LENGTH
    with pytest.raises(ValidationError, match="string_too_long"):
        load(tmp_path, [{"id": 42, "name": name, "shots": [{}]}])


def test_simultaneous_native_loads_have_independent_id_registries(
    tmp_path, monkeypatch
):
    source = write_stalx(tmp_path / "survey.stalx", [{"id": 42, "shots": [{}]}])
    second_entered = Event()
    first_registered = Event()
    second_finished = Event()
    worker = local()
    original_read = StalagmightInterface._from_file  # noqa: SLF001
    original_register = UniqueValueGenerator.register

    def gated_read(filepath):
        if worker.first:
            assert second_entered.wait(10)
        else:
            second_entered.set()
            assert first_registered.wait(10)
        return original_read(filepath)

    def gated_register(vartype, value):
        original_register(vartype, value)
        if worker.first and not first_registered.is_set():
            first_registered.set()
            assert second_finished.wait(10)

    def load_in_worker(first):
        worker.first = first
        try:
            return StalagmightInterface.from_file(source).model_dump()
        finally:
            if not first:
                second_finished.set()

    monkeypatch.setattr(StalagmightInterface, "_from_file", gated_read)
    monkeypatch.setattr(UniqueValueGenerator, "register", gated_register)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(load_in_worker, first=True)
        second = executor.submit(load_in_worker, first=False)
        assert first.result(timeout=15) == second.result(timeout=15)


@pytest.mark.parametrize("fmt", ["json", "geojson"])
@pytest.mark.parametrize("alias", ["symlink", "hardlink"])
def test_cli_detects_alias_replaced_at_output_open(tmp_path, monkeypatch, fmt, alias):
    source = write_stalx(
        tmp_path / "survey.stalx",
        [{"id": 42, "shots": [{}]}],
        [(1, 42, 0, 40.0, -70.0, 0.0)],
    )
    before = source.read_bytes()
    output = tmp_path / "output.json"
    output.write_bytes(b"previous output")
    original_open = Path.open

    def replace_then_open(path, *args, **kwargs):
        if path == output:
            path.unlink()
            if alias == "symlink":
                path.symlink_to(source)
            else:
                path.hardlink_to(source)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", replace_then_open)
    with pytest.raises(ValueError, match="same file"):
        convert([*cli_args(source, output, fmt), "--overwrite"])
    assert source.read_bytes() == before


@pytest.mark.parametrize("fmt", ["json", "geojson"])
@pytest.mark.parametrize("alias", ["symlink", "hardlink"])
def test_cli_protects_atomically_replaced_input(tmp_path, monkeypatch, fmt, alias):
    sections = [{"id": 42, "shots": [{}]}]
    datums = [(1, 42, 0, 40.0, -70.0, 0.0)]
    source = write_stalx(tmp_path / "survey.stalx", sections, datums)
    replacement = write_stalx(tmp_path / "replacement.stalx", sections, datums)
    before = replacement.read_bytes()
    output = tmp_path / "output.json"
    original_read = StalagmightInterface.from_file

    def replace_before_read(path):
        replacement.replace(source)
        if alias == "symlink":
            output.symlink_to(source)
        else:
            output.hardlink_to(source)
        return original_read(path)

    monkeypatch.setattr(StalagmightInterface, "from_file", replace_before_read)
    with pytest.raises(ValueError, match="same file"):
        convert([*cli_args(source, output, fmt), "--overwrite"])
    assert source.read_bytes() == before
    assert output.read_bytes() == before


def test_cli_protects_original_input_inode_after_replacement(tmp_path, monkeypatch):
    sections = [{"id": 42, "shots": [{}]}]
    source = write_stalx(tmp_path / "survey.stalx", sections)
    replacement = write_stalx(tmp_path / "replacement.stalx", sections)
    archived = tmp_path / "original.stalx"
    output = tmp_path / "output.json"
    before = source.read_bytes()
    original_read = StalagmightInterface.from_file

    def replace_after_read(path):
        survey = original_read(path)
        source.rename(archived)
        replacement.replace(source)
        output.hardlink_to(archived)
        return survey

    monkeypatch.setattr(StalagmightInterface, "from_file", replace_after_read)
    with pytest.raises(ValueError, match="same file"):
        convert([*cli_args(source, output, "json"), "--overwrite"])
    assert archived.read_bytes() == before
    assert output.read_bytes() == before


def test_cli_allows_input_removed_after_read(tmp_path, monkeypatch):
    source = write_stalx(tmp_path / "survey.stalx", [{"id": 42, "shots": [{}]}])
    output = tmp_path / "output.json"
    original_read = StalagmightInterface.from_file

    def remove_after_read(path):
        survey = original_read(path)
        path.unlink()
        return survey

    monkeypatch.setattr(StalagmightInterface, "from_file", remove_after_read)
    convert(cli_args(source, output, "json"))
    assert json.loads(output.read_text())["name"] == "Cave"


@pytest.mark.parametrize("fmt", ["json", "geojson"])
def test_cli_no_overwrite_when_output_appears_during_conversion(
    tmp_path, monkeypatch, fmt
):
    source = write_stalx(
        tmp_path / "survey.stalx",
        [{"id": 42, "shots": [{}]}],
        [(1, 42, 0, 40.0, -70.0, 0.0)],
    )
    output = tmp_path / "output.json"
    original_read = StalagmightInterface.from_file

    def create_output_before_return(path):
        survey = original_read(path)
        output.write_bytes(b"created concurrently")
        return survey

    monkeypatch.setattr(StalagmightInterface, "from_file", create_output_before_return)
    with pytest.raises(FileExistsError):
        convert(cli_args(source, output, fmt))
    assert output.read_bytes() == b"created concurrently"


@pytest.mark.parametrize("fmt", ["json", "geojson"])
@pytest.mark.parametrize("existing", [False, True])
def test_cli_serialization_failure_preserves_output(
    tmp_path, monkeypatch, fmt, existing
):

    source = write_stalx(
        tmp_path / "survey.stalx",
        [{"id": 42, "shots": [{}]}],
        [(1, 42, 0, 40.0, -70.0, 0.0)],
    )
    output = tmp_path / "output.json"
    if existing:
        output.write_bytes(b"keep")

    def fail_serialization(*args, **kwargs):
        raise TypeError("synthetic serialization failure")

    monkeypatch.setattr(orjson, "dumps", fail_serialization)
    with pytest.raises(TypeError, match="synthetic serialization failure"):
        convert([*cli_args(source, output, fmt), "--overwrite"])
    assert output.read_bytes() == b"keep" if existing else not output.exists()


@pytest.mark.parametrize("kind", [0, 1, 2])
def test_geometry_arithmetic_overflow_has_native_identity(tmp_path, kind):
    with pytest.raises(ValueError, match="shots row 1234 section 42 sequence 0"):
        load(
            tmp_path,
            [{"id": 42, "shots": [{"id": 1234, "length": 1e200, "kind": kind}]}],
        )


@pytest.mark.parametrize("fmt", ["json", "geojson"])
def test_cli_overwrite_preserves_output_symlink_semantics(tmp_path, fmt):
    source = write_stalx(
        tmp_path / "survey.stalx",
        [{"id": 42, "shots": [{}]}],
        [(1, 42, 0, 40.0, -70.0, 0.0)],
    )
    target = tmp_path / "target.json"
    target.write_bytes(b"previous output")
    output = tmp_path / "symlink.json"
    output.symlink_to(target)
    convert([*cli_args(source, output, fmt), "--overwrite"])
    assert output.is_symlink()
    assert json.loads(target.read_text())
