import json
import tempfile
import zipfile
from pathlib import Path
from typing import Self

import xmltodict
from defusedxml.minidom import parseString
from dicttoxml2 import dicttoxml

from openspeleo_lib._interface import BaseInterface
from openspeleo_lib.formats.ariane.enums_cls import ArianeFileType
from openspeleo_lib.formats.ariane.name_map import ARIANE_MAPPING
from openspeleo_lib.models import Survey
from openspeleo_lib.utils import apply_key_mapping


def _extract_zip(input_zip):
    input_zip=zipfile.ZipFile(input_zip)
    return {name: input_zip.read(name) for name in input_zip.namelist()}


def _filetype(filepath: Path) -> ArianeFileType:
    if isinstance(filepath, str):
        filepath = Path(filepath)

    try:
        return ArianeFileType.from_str(filepath.suffix[1:])
    except ValueError as e:
        raise TypeError(e) from e


class ArianeInterface(BaseInterface):

    @classmethod
    def _write_to_file(cls, filepath: Path, data: dict, debug: bool = False) -> None:
        if isinstance(filepath, str):
            filepath = Path(filepath)

        filetype  = _filetype(filepath=filepath)

        if filetype != ArianeFileType.TML:
            raise TypeError(f"Unsupported fileformat: `{filetype.name}`. "
                            f"Expected: `{ArianeFileType.TML.name}`")

        xml_str = dicttoxml(
            data,
            custom_root="CaveFile",
            attr_type=False,
            fold_list=False
        )

        xml_prettyfied = parseString(xml_str).toprettyxml(
            indent=" " * 4, encoding="utf-8", standalone=True
        ).decode("utf-8")

        with tempfile.TemporaryDirectory() as tmp_dir:
            xml_f = Path(tmp_dir) / "Data.xml"
            with xml_f.open(mode="w") as f:
                f.write(xml_prettyfied)

            if debug:
                with open("Data.xml", mode="w") as f:  # noqa: PTH123
                    f.write(xml_prettyfied)

            with zipfile.ZipFile(filepath, "w", compression=zipfile.ZIP_DEFLATED) as zf:

                if debug:
                    print(f"[DEBUG] Exporting {filetype.name} File: `{filepath}`")  # noqa: T201

                zf.write(f.name, "Data.xml")

    def to_file(self, filepath: Path, debug: bool = False) -> None:

        data = self.survey_data

        if debug:
            with open("data.export.before.json", mode="w") as f:  # noqa: PTH123
                f.write(json.dumps(data, indent=4, sort_keys=True))

        data = apply_key_mapping(data, mapping=ARIANE_MAPPING)

        if debug:
            with open("data.export.after.json", mode="w") as f:  # noqa: PTH123
                f.write(json.dumps(data, indent=4, sort_keys=True))

        self._write_to_file(filepath=filepath, data=data, debug=debug)

    @classmethod
    def _load_from_file(cls, filepath: Path, debug=True) -> dict:
        if isinstance(filepath, str):
            filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: `{filepath}`")

        filetype  = _filetype(filepath=filepath)

        if debug:
            print(f"[DEBUG] Loading {filetype.name} File: `{filepath}`")  # noqa: T201

        match filetype:
            case ArianeFileType.TML:
                xml_data = _extract_zip(filepath)["Data.xml"]

            case ArianeFileType.TMLU:
                raise NotImplementedError("Not supported yet")
                # with filepath.open(mode="r") as f:
                #     xml_data = f.read()

        return xmltodict.parse(xml_data)["CaveFile"]

    @classmethod
    def from_file(cls, filepath: Path, debug: bool = False) -> Self:

        data = cls._load_from_file(filepath=filepath, debug=debug)

        if debug:
            with open("data.import.before.json", mode="w") as f:  # noqa: PTH123
                f.write(json.dumps(data, indent=4, sort_keys=True))

        data = apply_key_mapping(data, mapping=ARIANE_MAPPING.inverse)

        if debug:
            with open("data.import.after.json", mode="w") as f:  # noqa: PTH123
                f.write(json.dumps(data, indent=4, sort_keys=True))

        return ArianeInterface(survey=Survey(**data))
