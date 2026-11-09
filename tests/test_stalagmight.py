"""StalagMight uses the existing geographic exporter and CLI."""

import json
import shutil
import sqlite3
import zipfile
from contextlib import closing
from pathlib import Path
from uuid import UUID

import orjson
import pytest
from deepdiff import DeepDiff
from openspeleo_core import ariane_core
from pydantic import ValidationError
from stalagmight_lib import StalagMightFormatError

from openspeleo_lib.commands.convert import convert
from openspeleo_lib.constants import OSPL_SECTIONNAME_MAX_LENGTH
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.generators import UniqueValueGenerator
from openspeleo_lib.geojson import InconsistentShotCoordinatesError
from openspeleo_lib.geojson import NoKnownAnchorError
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.interfaces import StalagMightInterface
from openspeleo_lib.interfaces.stalagmight import StalagMightSection
from openspeleo_lib.interfaces.stalagmight import StalagMightShot
from tests.commands.test_command_convert import run_convert
from tests.stalagmight_helpers import write_stalx

EXAMPLE = Path(__file__).parent / "artifacts/example.stalx"
GEOJSON_GOLDEN = Path(__file__).parent / "artifacts/stalagmight.geojson"
STAMP = "2026-01-01T00:00:00Z"
UUID4 = "f26c8521-2164-425d-b967-a4a4a874b69c"


def load(tmp_path, sections, datums=((1, 42, 0, 0.0, 0.0, 0.0),), merges=()):
    path = write_stalx(tmp_path / "survey.STALX", sections, datums, merges)
    return StalagMightInterface.from_file(path)


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
                        "depth_in": 50.0,
                        "depth_out": 56.0,
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
    assert real.depth_start == 50
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
    assert feature["geometry"]["coordinates"][0][0] > 0
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
    again = StalagMightInterface.from_file(tmp_path / "survey.STALX")
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


def test_lowest_datum_root_and_additional_constraints(tmp_path, caplog):
    survey = load(
        tmp_path,
        [{"id": 42, "shots": [{}]}, {"id": 1, "name": None, "shots": [{}]}],
        datums=[(20, 1, 1, 40.0, -70.0, 0.0), (2, 42, 1, 40.0, -70.0, 0.0)],
        merges=[(2, 1, 1, 42, 1, STAMP), (3, 1, 0, 42, 0, STAMP)],
    )
    assert survey.sections[0].name == "Section 1"
    assert any(s.shot_type == ArianeShotType.START for s in survey.sections[1].shots)
    assert len(survey_to_geojson(survey)["features"]) == 3
    assert "no closure adjustment" in caplog.text
    assert len(survey._native.station_merges) == 2  # noqa: SLF001 - native retention


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
        survey_to_geojson(StalagMightInterface.from_file(path))


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
    survey = StalagMightInterface.from_file(path)
    assert [s.computed_declination for s in survey.sections] == [12, 23, 0]
    assert [s.shots[-1].id for s in survey.sections] == [UUID(UUID4), None, None]


def test_example_failure_and_deliberately_repaired_copy_matches_geojson_golden(
    tmp_path,
):
    """Compare the synthetic length variant to a decoded, standalone golden."""
    before = EXAMPLE.read_bytes()
    with pytest.raises(ValueError, match=r"shots row 282 section \d+ sequence \d+"):
        survey_to_geojson(StalagMightInterface.from_file(EXAMPLE))
    repaired = tmp_path / "synthetic-valid-length.stalx"
    shutil.copyfile(EXAMPLE, repaired)
    with closing(sqlite3.connect(repaired)) as conn, conn:
        conn.execute("UPDATE shots SET length=ABS(depth_out-depth_in)+1 WHERE id=282")
    actual = json.loads(
        json.dumps(survey_to_geojson(StalagMightInterface.from_file(repaired)))
    )
    expected = json.loads(GEOJSON_GOLDEN.read_text(encoding="utf-8"))
    assert actual == expected, DeepDiff(expected, actual).pretty()
    features = actual["features"]
    assert sum(f["geometry"]["type"] == "LineString" for f in features) == 467
    assert sum(f["geometry"]["type"] == "Point" for f in features) == 1
    assert EXAMPLE.read_bytes() == before


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
        shutil.copyfile(EXAMPLE, source)
    else:
        source.write_bytes(b"invalid SQLite")
    for existing in (False, True):
        output = tmp_path / f"{existing}.json"
        if existing:
            output.write_bytes(b"keep")
        with pytest.raises((ValueError, StalagMightFormatError)):
            convert([*cli_args(source, output), "--overwrite"])
        assert output.read_bytes() == b"keep" if existing else not output.exists()


def test_writer_unsupported(tmp_path):
    with pytest.raises(NotImplementedError):
        StalagMightInterface.to_file(None, tmp_path / "output.stalx")


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
    result = run_convert(EXAMPLE, output)
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
        assert isinstance(roundtrip.sections[0], StalagMightSection)
        assert all(isinstance(shot, StalagMightShot) for shot in roundtrip.shots)
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


def test_long_native_section_name_is_preserved(tmp_path):

    name = "native section " * OSPL_SECTIONNAME_MAX_LENGTH
    survey = load(tmp_path, [{"id": 42, "name": name, "shots": [{}]}])
    assert survey.sections[0].name == name
    assert all(
        feature["properties"]["name"] == name
        for feature in survey_to_geojson(survey)["features"]
    )


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
def test_cli_no_overwrite_when_output_appears_during_conversion(
    tmp_path, monkeypatch, fmt
):
    source = write_stalx(
        tmp_path / "survey.stalx",
        [{"id": 42, "shots": [{}]}],
        [(1, 42, 0, 40.0, -70.0, 0.0)],
    )
    output = tmp_path / "output.json"
    original_read = StalagMightInterface.from_file

    def create_output_before_return(path):
        survey = original_read(path)
        output.write_bytes(b"created concurrently")
        return survey

    monkeypatch.setattr(StalagMightInterface, "from_file", create_output_before_return)
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
    survey = load(
        tmp_path, [{"id": 42, "shots": [{"id": 1234, "length": 1e200, "kind": kind}]}]
    )
    with pytest.raises(ValueError, match="shots row 1234 section 42 sequence 0"):
        survey_to_geojson(survey)


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
