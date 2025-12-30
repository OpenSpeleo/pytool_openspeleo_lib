from __future__ import annotations

import contextlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any
from xml.parsers.expat import ExpatError

# from openspeleo_core.legacy import remove_none_values
# from openspeleo_core.legacy import apply_key_mapping
from openspeleo_core.mapping import apply_key_mapping

from openspeleo_lib.debug_utils import write_debugdata_to_disk
from openspeleo_lib.interfaces.ariane.name_map import ARIANE_INVERSE_MAPPING
from openspeleo_lib.interfaces.ariane.xml_utils import deserialize_xmlfield_to_dict

logger = logging.getLogger(__name__)
DEBUG = False


@lru_cache(maxsize=128)
def get_section_key(
    name: str, description: str, date: str, explorers: str, surveyors: str
) -> str:
    """
    Generate a unique key for a section based on its name, date, surveyors and explorers
    This is used to ensure that sections are uniquely identified in the data structure.

    Note: Using `∎` as a separator as it's unlikely to be used by people in the
          `fields` of the survey.
    """
    return hash(f"{name}∎{description}∎{date}∎{explorers}∎{surveyors}")


def ariane_decode(data: dict) -> dict:  # noqa: PLR0915
    # ===================== DICT FORMATTING TO OSPL ===================== #

    # 1. Apply key mapping: From Ariane to OSPL
    data = apply_key_mapping(data, mapping=ARIANE_INVERSE_MAPPING)

    if (cavename := data.pop("CaveName", None)) is not None:
        data["cave_name"] = cavename

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step01-mapped.json"))

    # 1.1 Formatting Top Lvl - ariane unit is lowercase - OSPL unit is uppercase
    for key in ["unit", "Unit"]:
        with contextlib.suppress(KeyError):
            data["unit"] = data[key].upper()
            break
    else:
        raise KeyError("Missing 'unit' field in data")

    # 2. Collapse `ariane_viewer_layers`:
    # - BEFORE: data["ariane_viewer_layers"]["layer_list"]
    # - AFTER:  data["ariane_viewer_layers"]
    data["ariane_viewer_layers"] = data["ariane_viewer_layers"].pop("layer_list")

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step02-collapsed.json"))

    # 3. Sort `shots` into `sections`
    sections: dict[tuple[str, str], dict[str, Any]] = {}
    for shot in data.pop("data")["shots"]:
        shot: dict[str, Any]
        # 3.1 Collapse `radius_vectors`:
        # - BEFORE: shot["shape"]["radius_collection"]["radius_vector"]
        # - AFTER:  shot["shape"]["radius_vectors"]
        with contextlib.suppress(KeyError):
            shot["shape"]["radius_vectors"] = shot["shape"].pop("radius_collection")[
                "radius_vector"
            ]

        # Formatting the color back to OSPL format
        shot["color"] = shot.pop("color").replace("0x", "#")

        # 3.2 Separate shots into sections
        try:
            section_name = shot.pop("section_name", "")

            description = ""
            if "SectionDescription" in section_name:
                _data = deserialize_xmlfield_to_dict(section_name)
                section_name = _data.get("#text", "")
                description = _data.get("SectionDescription", "")

            section_date = shot.pop("date", "")

            section_explorers = ""
            section_surveyors = ""

            # ==================== Explorers / Surveyors ==================== #
            # Ariane Version >= 26
            if any(key in shot for key in ["explorers", "surveyors"]):
                section_explorers = shot.pop("explorers", "")
                section_surveyors = shot.pop("surveyors", "")

            # Ariane Version < 26
            elif ariane_explorer_field := shot.pop("Explorer", ""):
                try:
                    _data = deserialize_xmlfield_to_dict(ariane_explorer_field)
                    if isinstance(_data, str):
                        section_explorers = _data
                    else:
                        _data = apply_key_mapping(_data, mapping=ARIANE_INVERSE_MAPPING)
                        section_explorers = _data.get("explorers", "")
                        section_surveyors = _data.get("surveyors", "")

                except ExpatError:
                    # Deserialization failed, fallback to raw string
                    section_explorers = ariane_explorer_field

            section_key = get_section_key(
                name=section_name,
                description=description,
                date=section_date,
                explorers=section_explorers,
                surveyors=section_surveyors,
            )

            if section_key not in sections:
                sections[section_key] = {
                    "section_name": section_name,
                    "description": description,
                    "date": section_date,
                    "explorers": section_explorers,
                    "surveyors": section_surveyors,
                    "shots": [],
                }

            with contextlib.suppress(KeyError):
                if not isinstance(
                    (radius_vectors := shot["shape"]["radius_vectors"]),
                    (tuple, list),
                ):
                    shot["shape"]["radius_vectors"] = [radius_vectors]

            sections[section_key]["shots"].append(shot)

        except KeyError:
            logging.exception(
                "Incomplete shot data: `%(shot)s`",
                {"shot": shot},
            )
            continue  # if data is incomplete, skip this shot

    data["sections"] = list(sections.values())

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step03-sections.json"))

    return data
