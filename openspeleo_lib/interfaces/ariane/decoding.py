import contextlib
import logging
from pathlib import Path

from openspeleo_lib.debug_utils import write_debugdata_to_disk
from openspeleo_lib.interfaces.ariane.name_map import ARIANE_MAPPING
from openspeleo_lib.utils import apply_key_mapping
from openspeleo_lib.utils import remove_none_values
from openspeleo_lib.xml_utils import deserialize_xmlfield_to_dict

logger = logging.getLogger(__name__)
DEBUG = False


def ariane_decode(data: dict) -> dict:
    # ===================== DICT FORMATTING TO OSPL ===================== #

    # 1. Remove None values from the dictionary
    data = remove_none_values(data)

    # Formatting Unit - ariane unit is lowercase - OSPL unit is uppercase
    data["unit"] = data["unit"].upper()

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step01-none_cleaned.json"))

    # 2. Apply key mapping: From Ariane to OSPL
    data = apply_key_mapping(data, mapping=ARIANE_MAPPING.inverse)

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step02-mapped.json"))

    # 3. Collapse data["ariane_viewer_layers"]["layer_list"] to data["ariane_viewer_layers"]  # noqa: E501
    data["ariane_viewer_layers"] = data["ariane_viewer_layers"].pop("layer_list")

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step03-collapsed.json"))

    # 4. Sort `shots` into `sections`
    sections = {}
    for shot in data.pop("data")["shots"]:
        # 4.1 Collapse shot["shape"]["radius_collection"]["radius_vector"] to shot["shape"]["radius_vectors"]  # noqa: E501
        with contextlib.suppress(KeyError):
            shot["shape"]["radius_vectors"] = shot["shape"].pop("radius_collection")[
                "radius_vector"
            ]

        # Formatting the color back to OSPL format
        shot["color"] = shot.pop("color").replace("0x", "#")

        # 4.2 Separate shots into sections
        try:
            if (section_name := shot.pop("section_name")) not in sections:
                sections[section_name] = {
                    "section_name": section_name,
                    "date": shot.pop("date", None),
                    "shots": [],
                }
                if ariane_explorer_field := shot.pop("explorers"):
                    _data = deserialize_xmlfield_to_dict(ariane_explorer_field)

                    if isinstance(_data, str):
                        _data = {"explorers": _data}
                    else:
                        _data = apply_key_mapping(_data, mapping=ARIANE_MAPPING.inverse)

                    sections[section_name].update(_data)

            else:
                for key in ["date", "explorers"]:
                    with contextlib.suppress(KeyError):
                        _value = shot.pop(key)

                        if key == "explorers" and isinstance(_value, dict):
                            _data = apply_key_mapping(
                                deserialize_xmlfield_to_dict(_value),
                                mapping=ARIANE_MAPPING.inverse,
                            )

                        else:
                            _data = {key: _value}

                        for sub_key, value in _data.items():
                            if sections[section_name][sub_key] != value:
                                logger.warning(
                                    "Section `%(section)s` has different `%(key)s`: "
                                    "`%(section_val)s` != `%(shot_val)s`",
                                    {
                                        "section": section_name,
                                        "key": sub_key,
                                        "section_val": sections[section_name][sub_key],
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

        except KeyError as e:
            logging.warning(
                "Incomplete shot data: `%(shot)s` - Error: %(error)s",
                {"shot": shot, "error": e},
            )
            continue  # if data is incomplete, skip this shot

    data["sections"] = list(sections.values())

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step04-sections.json"))

    return data
