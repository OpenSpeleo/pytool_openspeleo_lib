import json
import logging
import tempfile
import zipfile
from pathlib import Path

import xmltodict
from defusedxml.minidom import parseString
from dicttoxml2 import dicttoxml

from openspeleo_lib.interfaces.ariane.enums_cls import ArianeFileType
from openspeleo_lib.interfaces.ariane.name_map import ARIANE_MAPPING
from openspeleo_lib.interfaces.base import BaseInterface
from openspeleo_lib.models import Survey
from openspeleo_lib.utils import apply_key_mapping

logger = logging.getLogger(__name__)
DEBUG = False


def _extract_zip(input_zip) -> dict[str, bytes]:
    input_zip = zipfile.ZipFile(input_zip)
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
    def _write_to_file(cls, filepath: Path, data: dict) -> None:
        if isinstance(filepath, str):
            filepath = Path(filepath)

        filetype = _filetype(filepath=filepath)

        if filetype != ArianeFileType.TML:
            raise TypeError(
                f"Unsupported fileformat: `{filetype.name}`. "
                f"Expected: `{ArianeFileType.TML.name}`"
            )

        xml_str = dicttoxml(
            data, custom_root="CaveFile", attr_type=False, fold_list=False
        )

        xml_prettyfied = (
            parseString(xml_str)
            .toprettyxml(indent=" " * 4, encoding="utf-8", standalone=True)
            .decode("utf-8")
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            xml_f = Path(tmp_dir) / "Data.xml"
            with xml_f.open(mode="w") as f:
                f.write(xml_prettyfied)

            if DEBUG:
                with open("Data.xml", mode="w") as f:  # noqa: PTH123
                    f.write(xml_prettyfied)

            with zipfile.ZipFile(filepath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                logging.debug(
                    "Exporting %(filetype)s File: `%(filepath)s`",
                    {"filetype": filetype.name, "filepath": filepath},
                )
                zf.write(f.name, "Data.xml")

    @classmethod
    def to_file(cls, survey: Survey, filepath: Path) -> None:
        data = survey.model_dump()

        if DEBUG:
            with open("data.export.before.json", mode="w") as f:  # noqa: PTH123
                f.write(json.dumps(data, indent=4, sort_keys=True))

        data = apply_key_mapping(data, mapping=ARIANE_MAPPING)

        if DEBUG:
            with open("data.export.after.json", mode="w") as f:  # noqa: PTH123
                f.write(json.dumps(data, indent=4, sort_keys=True))

        cls._write_to_file(filepath=filepath, data=data)

    @classmethod
    def _load_from_file(cls, filepath: Path) -> dict:
        if isinstance(filepath, str):
            filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: `{filepath}`")

        filetype = _filetype(filepath=filepath)

        logging.debug(
            "Loading %(filetype)s File: `%(filepath)s`",
            {"filetype": filetype.name, "filepath": filepath},
        )

        match filetype:
            case ArianeFileType.TML:
                xml_data = _extract_zip(filepath)["Data.xml"]

            case _:
                raise NotImplementedError(
                    f"Not supported yet - Format: `{filetype.name}`"
                )
                # with filepath.open(mode="r") as f:
                #     xml_data = f.read()

        return xmltodict.parse(xml_data)["CaveFile"]

    @classmethod
    def from_file(cls, filepath: Path) -> Survey:
        data = cls._load_from_file(filepath=filepath)

        if DEBUG:
            with open("data.import.before.json", mode="w") as f:  # noqa: PTH123
                f.write(json.dumps(data, indent=4, sort_keys=True))

        data = apply_key_mapping(data, mapping=ARIANE_MAPPING.inverse)

        if DEBUG:
            with open("data.import.after.json", mode="w") as f:  # noqa: PTH123
                f.write(json.dumps(data, indent=4, sort_keys=True))

        return Survey(**data)
