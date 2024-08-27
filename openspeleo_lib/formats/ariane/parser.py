import tempfile
import zipfile
from pathlib import Path

import xmltodict
from defusedxml.minidom import parseString
from dicttoxml2 import dicttoxml

from openspeleo_lib.formats.ariane.enums_cls import ArianeFileType


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


class ArianeParser:

    @classmethod
    def from_ariane_file(cls, filepath: Path, debug=False) -> dict:
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
                with filepath.open(mode="r") as f:
                    xml_data = f.read()
                # TODO convert the keys to TMLU

        return xmltodict.parse(xml_data)["CaveFile"]

    @classmethod
    def to_ariane_file(cls, data: dict, filepath: Path, debug=False) -> None:
        if isinstance(filepath, str):
            filepath = Path(filepath)

        filetype  = _filetype(filepath=filepath)

        if filetype != ArianeFileType.TML:
            raise TypeError(f"Unsupported fileformat: `{filetype}`. "
                            f"Expected: `{ArianeFileType.TML}`")

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

            with zipfile.ZipFile(filepath, "w", compression=zipfile.ZIP_STORED) as zipf:

                if debug:
                    print(f"[DEBUG] Exporting {filetype.name} File: `{filepath}`")  # noqa: T201

                zipf.write(f.name, "Data.xml")
