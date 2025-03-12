import contextlib
import logging
from pathlib import Path
from typing import Any

# from openspeleo_core.legacy import apply_key_mapping
from openspeleo_core.mapping import apply_key_mapping

from openspeleo_lib.debug_utils import write_debugdata_to_disk
from openspeleo_lib.interfaces.ariane.name_map import ARIANE_MAPPING
from openspeleo_lib.xml_utils import serialize_dict_to_xmlfield

logger = logging.getLogger(__name__)
DEBUG = False


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

    # ======= IMPLEMENTATION 2 - A little faster - much more difficult to read ======= #

    # stack = [data]

    # while stack:
    #     current = stack.pop()

    #     if isinstance(current, dict):
    #         for k, v in current.items():
    #             if isinstance(v, bool):
    #                 current[k] = "true" if v else "false"
    #             elif isinstance(v, (dict, list, set)):
    #                 stack.append(v)
    #             elif isinstance(v, (int, float)):
    #                 current[k] = str(v)

    #     elif isinstance(current, list):
    #         for i in range(len(current)):
    #             if isinstance(current[i], bool):
    #                 current[i] = "true" if current[i] else "false"
    #             elif isinstance(current[i], (dict, list, set)):
    #                 stack.append(current[i])
    #             elif isinstance(current[i], (int, float)):
    #                 current[i] = str(current[i])
    # return data


# def ArianeCustomXMLEncoder(data: dict) -> dict:
#     stack = [data]

#     while stack:
#         current = stack.pop()

#         if isinstance(current, dict):
#             for k, v in current.items():
#                 if isinstance(v, bool):
#                     current[k] = "true" if v else "false"

#                 elif isinstance(v, (float, int)):
#                     current[k] = str(data)

#                 elif isinstance(v, (dict, list)):
#                     stack.append(v)

#         elif isinstance(current, list):
#             for i in range(len(current)):
#                 if isinstance(current[i], bool):
#                     current[i] = "true" if current[i] else "false"

#                 elif isinstance(v, (float, int)):
#                     current[k] = str(data)

#                 elif isinstance(current[i], (dict, list)):
#                     stack.append(current[i])

#     return data


def ariane_encode(data: dict) -> dict:
    # ==================== FORMATING FROM OSPL TO TML =================== #

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.export.before.json"))

    # 1. Encode dtypes to `Ariane` format (e.g. `True` -> `true`)
    data = ArianeCustomXMLEncoder(data)

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.export.step01.json"))

    # Formatting Unit - ariane unit is lowercase - OSPL unit is uppercase
    data["unit"] = data["unit"].lower()

    # 2. Flatten sections into shots
    shots = []
    for section in data.pop("sections"):
        for shot in section.pop("shots"):
            shot["section_name"] = section["section_name"]
            shot["date"] = section["date"]

            # ~~~~~~~~~~~~~~~~ Processing Explorers/Surveyors ~~~~~~~~~~~~~~~ #
            _explo_data = {}
            for key in ["explorers", "surveyors"]:
                if (_value := section[key]) is not None:
                    _explo_data[key] = _value

            # In case only "explorer" data exists - Ariane doesn't store in format XML
            if len(_explo_data) == 1:
                with contextlib.suppress(KeyError):
                    _explo_data = _explo_data["explorers"]

            if isinstance(_explo_data, dict):
                _explo_data = apply_key_mapping(_explo_data, mapping=ARIANE_MAPPING)

            shot["explorers"] = serialize_dict_to_xmlfield(_explo_data)
            # --------------------------------------------------------------- #

            radius_vectors = shot["shape"].pop("radius_vectors")
            shot["shape"]["radius_collection"] = {"radius_vector": radius_vectors}
            shot["color"] = shot.pop("color").replace("#", "0x")

            shots.append(shot)

    data["data"] = {"shots": shots}

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.export.step02.json"))

    # 3. Restore ArianeViewerLayer => Layers[LayerList] = [Layer1, Layer2, ...]
    data["ariane_viewer_layers"] = {"layer_list": data.pop("ariane_viewer_layers")}

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.export.step03.json"))

    # 4. Apply key mapping in reverse order
    data = apply_key_mapping(data, mapping=ARIANE_MAPPING)

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.export.mapped.json"))

    # ------------------------------------------------------------------- #

    return data
