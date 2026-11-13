"""Plain and abbreviated Ariane XML share the normal reader boundary."""

import zipfile

import orjson
import pytest
from openspeleo_core import ariane_core
from pydantic import ValidationError

from openspeleo_lib.commands.convert import convert
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.interfaces.ariane.decoding import expand_tmlu_shots
from tests.utils import write_synthetic_tml


def test_plain_xml_and_compressed_xml_have_identical_models(tmp_path):
    compressed = tmp_path / "survey.tml"
    plain = tmp_path / "survey.tmlu"
    write_synthetic_tml(compressed)
    with zipfile.ZipFile(compressed) as archive:
        plain.write_bytes(archive.read("Data.xml"))
    expected = ArianeInterface.from_file(compressed).model_dump(mode="json")
    assert ArianeInterface.from_file(plain).model_dump(mode="json") == expected
    output = tmp_path / "survey.json"
    convert(["-i", str(plain), "-o", str(output), "-f", "json"])
    assert orjson.loads(output.read_bytes()) == expected


@pytest.mark.parametrize("longitude", [-70, -183])
def test_abbreviated_records_use_common_coordinate_validation(tmp_path, longitude):
    record = {
        "ID": 1,
        "FRID": -1,
        "TY": "START",
        "SC": "Synthetic",
        "DT": "2025-01-01",
        "NM": "ANCHOR",
        "LG": 0,
        "DP": 0,
        "AZ": 0,
        "LT": 40,
        "LGT": longitude,
    }
    path = tmp_path / "abbreviated.tmlu"
    path.write_text(
        ariane_core.dict_to_xml_str(
            {"unit": "m", "Data": {"SRVD": record}}, root_name="CaveFile"
        )
    )
    if longitude < -180:
        with pytest.raises(ValidationError) as error:
            ArianeInterface.from_file(path)
        assert any("ANCHOR" in note for note in error.value.__notes__)
    else:
        source = ArianeInterface.from_file(path)
        shot = next(source.shots)
        assert (shot.id_stop, shot.id_start) == (1, -1)
        assert (shot.latitude, shot.longitude) == (40, -70)


@pytest.mark.parametrize(
    "records",
    [
        {"SRVD": [], "SurveyData": []},
        {"SRVD": {"LG": 1, "Length": 2}},
    ],
)
def test_mixed_or_duplicate_field_names_are_rejected(records):
    with pytest.raises(ValueError, match=r"mixes|Duplicate"):
        expand_tmlu_shots({"Data": records})
