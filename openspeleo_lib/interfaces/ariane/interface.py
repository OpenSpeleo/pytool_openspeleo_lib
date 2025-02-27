import contextlib
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import orjson

from openspeleo_lib.interfaces.ariane.enums_cls import ArianeFileType
from openspeleo_lib.interfaces.ariane.name_map import ARIANE_MAPPING
from openspeleo_lib.interfaces.base import BaseInterface
from openspeleo_lib.models import Survey
from openspeleo_lib.utils import apply_key_mapping
from openspeleo_lib.utils import remove_none_values
from openspeleo_lib.xml_utils import dict_to_xml
from openspeleo_lib.xml_utils import xml_to_dict

logger = logging.getLogger(__name__)
DEBUG = False


def _write_debugdata_to_disk(data: dict, filepath: Path) -> None:
    with filepath.open(mode="w") as f:
        f.write(
            orjson.dumps(
                data, None, option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
            ).decode("utf-8")
        )


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

        case int() | float():
            return str(data)

        case _:
            return data


class ArianeInterface(BaseInterface):
    @classmethod
    def to_file(cls, survey: Survey, filepath: Path) -> None:
        if (filetype := _filetype(filepath=filepath)) != ArianeFileType.TML:
            raise TypeError(
                f"Unsupported fileformat: `{filetype.name}`. "
                f"Expected: `{ArianeFileType.TML.name}`"
            )

        data = survey.model_dump(mode="json")

        # ==================== FORMATING FROM OSPL TO TML =================== #

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.export.before.json"))

        # 1. Encode dtypes to `Ariane` format (e.g. `True` -> `true`)
        data = ArianeCustomXMLEncoder(data)

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.export.step01.json"))

        # 2. Flatten sections into shots
        shots = []
        for section in data.pop("sections"):
            for shot in section.pop("shots"):
                shot["section"] = section["name"]
                shot["date"] = section["date"]
                shot["surveyors"] = ",".join(section["surveyors"])

                radius_vectors = shot["shape"].pop("radius_vectors")
                shot["shape"]["radius_collection"] = {"radius_vector": radius_vectors}

                shots.append(shot)

        data["data"] = {"shots": shots}

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.export.step02.json"))

        # 3. Restore Layers => Layers[LayerList] = [Layer1, Layer2, ...]
        data["ariane_layers"] = {"layer_list": data.pop("ariane_layers")}

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.export.step03.json"))

        # 4. Apply key mapping in reverse order
        data = apply_key_mapping(data, mapping=ARIANE_MAPPING)

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.export.mapped.json"))

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.export.after.json"))

        # ------------------------------------------------------------------- #

        # =========================== DICT TO XML =========================== #

        xml_str = dict_to_xml(data)

        with Path("data.export.xml").open(mode="w") as f:
            f.write(xml_str)

        # ------------------------------------------------------------------- #

        if DEBUG:
            with Path("data.export.xml").open(mode="w") as f:
                f.write(xml_str)

        # ========================== WRITE TO DISK ========================== #

        with tempfile.TemporaryDirectory() as tmp_dir:
            xml_f = Path(tmp_dir) / "Data.xml"
            with xml_f.open(mode="w") as f:
                f.write(xml_str)

            with zipfile.ZipFile(filepath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                logging.debug(
                    "Exporting %(filetype)s File: `%(filepath)s`",
                    {"filetype": filetype.name, "filepath": filepath},
                )
                zf.write(f.name, "Data.xml")

    @classmethod
    def _from_file(cls, filepath: str | Path) -> Survey:
        # ========================= INPUT VALIDATION ======================== #

        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"File not found: `{filepath}`")

        if (filetype := _filetype(filepath=filepath)) != ArianeFileType.TML:
            raise TypeError(
                f"Unsupported fileformat: `{filetype.name}`. "
                f"Expected: `{ArianeFileType.TML.name}`"
            )

        logging.debug(
            "Loading %(filetype)s File: `%(filepath)s`",
            {"filetype": filetype.name, "filepath": filepath},
        )

        # ------------------------------------------------------------------- #

        # =========================== XML TO DICT =========================== #

        match filetype:
            case ArianeFileType.TML:
                xml_data = _extract_zip(filepath)["Data.xml"]

            case _:
                raise NotImplementedError(
                    f"Not supported yet - Format: `{filetype.name}`"
                )

        data = xml_to_dict(xml_data)["CaveFile"]

        # ------------------------------------------------------------------- #

        # ===================== DICT FORMATTING TO OSPL ===================== #

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.import.before.json"))

        # 1. Remove None values from the dictionary
        data = remove_none_values(data)

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.import.step01-none_cleaned.json"))

        # 2. Apply key mapping: From Ariane to OSPL
        data = apply_key_mapping(data, mapping=ARIANE_MAPPING.inverse)

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.import.step02-mapped.json"))

        # 3. Collapse data["ariane_layers"]["layer_list"] to data["ariane_layers"]
        data["ariane_layers"] = data["ariane_layers"].pop("layer_list")

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.import.step03-collapsed.json"))

        # 4. Sort `shots` into `sections`
        sections = {}
        for shot in data.pop("data")["shots"]:
            # 4.1 Collapse shot["shape"]["radius_collection"]["radius_vector"] to shot["shape"]["radius_vectors"]  # noqa: E501
            with contextlib.suppress(KeyError):
                shot["shape"]["radius_vectors"] = shot["shape"].pop(
                    "radius_collection"
                )["radius_vector"]

            # 4.2 Separate shots into sections
            try:
                if (section_name := shot.pop("section")) not in sections:
                    sections[section_name] = {
                        "name": section_name,
                        "date": shot.pop("date", None),
                        "shots": [],
                        "surveyors": (
                            shot.pop("surveyors").split(",")
                            if "surveyors" in shot
                            else []
                        ),
                    }
                else:
                    for key, should_split in [("date", False), ("surveyors", True)]:
                        with contextlib.suppress(KeyError):
                            value = shot.pop(key)

                            if should_split:
                                value = value.split(",")

                            if sections[section_name][key] != value:
                                logger.warning(
                                    "Section `%(section)s` has different `%(key)s`: "
                                    "`%(section_val)s` != `%(shot_val)s`",
                                    {
                                        "section": section_name,
                                        "key": key,
                                        "section_val": sections[section_name][key],
                                        "shot_val": value,
                                    },
                                )

                with contextlib.suppress(KeyError):
                    if not isinstance(
                        (radius_vectors := shot["shape"]["radius_vectors"]),
                        (tuple, list),
                    ):
                        shot["shape"]["radius_vectors"] = [radius_vectors]

                sections[section_name]["shots"].append(shot)

            except KeyError:
                continue  # if data is incomplete, skip this shot

        data["sections"] = list(sections.values())

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.import.step04-sections.json"))

        if DEBUG:
            _write_debugdata_to_disk(data, Path("data.import.formatted.json"))

        # ------------------------------------------------------------------- #

        return Survey(**data)
