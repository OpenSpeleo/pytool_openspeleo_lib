import contextlib
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import orjson
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


def _ensure_nested_as_list_inplace(data: dict, keys: list[str]) -> None:
    """
    Ensure that the value at the nested dictionary keys is a list.

    Args:
        data (dict): The dictionary to modify.
        keys (list): A list of keys to traverse the dictionary.

    Returns:
        dict: The modified dictionary.
    """
    data_ptr = data
    with contextlib.suppress(KeyError):
        for key in keys[:-1]:
            data_ptr = data_ptr[key]

        # Ensure the last key in the list is a list
        last_key = keys[-1]

        val = data_ptr[last_key]
        if not isinstance(val, list):
            data_ptr[last_key] = [val]


def ArianeCustomXMLEncoder(data: Any) -> Any:  # noqa: N802
    """
    Recursively encodes data into a format suitable for Ariane XML serialization.

    Args:
        data (Any): The input data to be encoded. It can be of any type.

    Returns:
        Any: The encoded data. Dictionaries, Lists, Tuples and Sets are recursively
        encoded. Booleans are converted to lowercase strings.
    """

    match data:
        case dict():
            return {k: ArianeCustomXMLEncoder(v) for k, v in data.items()}

        case tuple() | list() | set():
            return [ArianeCustomXMLEncoder(item) for item in data]

        case bool():
            return "true" if data else "false"

        case _:
            return data


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

        data = ArianeCustomXMLEncoder(data)
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
        data = survey.model_dump(mode="json")

        if DEBUG:
            with open("data.export.before.json", mode="w") as f:  # noqa: PTH123
                f.write(
                    orjson.dumps(
                        data, None, option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
                    ).decode("utf-8")
                )

        data = apply_key_mapping(data, mapping=ARIANE_MAPPING)

        if DEBUG:
            with open("data.export.after.json", mode="w") as f:  # noqa: PTH123
                f.write(
                    orjson.dumps(
                        data, None, option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
                    ).decode("utf-8")
                )

        cls._write_to_file(filepath=filepath, data=data)

    @classmethod
    def _from_file_to_dict(cls, filepath: Path) -> dict:
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
    def _from_file(cls, filepath: Path) -> Survey:
        data = cls._from_file_to_dict(filepath=filepath)

        if DEBUG:
            with open("data.import.before.json", mode="w") as f:  # noqa: PTH123
                f.write(
                    orjson.dumps(
                        data, None, option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
                    ).decode("utf-8")
                )

        for shot_data in data["Data"]["SurveyData"]:
            for nested_keys in [
                ["Shape", "RadiusCollection", "RadiusVector"],
            ]:
                _ensure_nested_as_list_inplace(shot_data, nested_keys)

        data = apply_key_mapping(data, mapping=ARIANE_MAPPING.inverse)

        if DEBUG:
            with open("data.import.after.json", mode="w") as f:  # noqa: PTH123
                f.write(
                    orjson.dumps(
                        data, None, option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
                    ).decode("utf-8")
                )

        return Survey(**data)
