from __future__ import annotations

import contextlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any
from xml.parsers.expat import ExpatError

from openspeleo_lib.debug_utils import write_debugdata_to_disk
from openspeleo_lib.enums import LengthUnits
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

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step00-start.json"))

    # 1.1 Formatting Top Lvl - ariane unit is lowercase - OSPL unit is uppercase
    for key in ["unit", "Unit", "UNIT"]:
        with contextlib.suppress(KeyError):
            match val := data[key].upper():
                case "FT" | "FEET":
                    data["unit"] = LengthUnits.FEET
                case "M" | "METERS" | "METER":
                    data["unit"] = LengthUnits.METERS
                case _:
                    raise ValueError(f"Unknown metric value: `{val}`")
            break

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step01-unit.json"))

    # 3. Sort `SurveyData` into `sections`
    sections: dict[tuple[str, str], dict[str, Any]] = {}
    for shot in data.pop("Data")["SurveyData"]:
        shot: dict[str, Any]

        # Separate SurveyData into sections
        try:
            name = shot.pop("Section", "")

            description = ""
            if "SectionDescription" in name:
                try:
                    _data = deserialize_xmlfield_to_dict(name)
                except ExpatError:
                    # Deserialization failed, fallback to raw string
                    _data = {"#text": name}

                name = _data.get("#text", "")
                description = _data.get("SectionDescription", "")

            section_date = shot.pop("Date", "")

            section_explorers = ""
            section_surveyors = ""

            # ==================== Explorers / Surveyors ==================== #
            # Ariane Version >= 26
            if any(key in shot for key in ["explorers", "surveyors"]):
                section_explorers = shot.pop("explorers", "")
                section_surveyors = shot.pop("surveyors", "")

                with contextlib.suppress(KeyError):
                    del shot["Explorer"]

            # Ariane Version < 26
            elif ariane_explorer_field := shot.pop("Explorer", ""):
                try:
                    match _data := deserialize_xmlfield_to_dict(ariane_explorer_field):
                        case str():
                            section_explorers = _data

                        case dict():
                            section_explorers = _data.get("Explorer", "") or ""
                            section_surveyors = _data.get("Surveyor", "") or ""

                        case _:
                            raise ValueError(
                                f"Unexpected data received for explorer field: {_data}"
                            )

                except ExpatError:
                    # Deserialization failed, fallback to raw string
                    section_explorers = ariane_explorer_field

            section_key = get_section_key(
                name=name,
                description=description,
                date=section_date,
                explorers=section_explorers,
                surveyors=section_surveyors,
            )

            if section_key not in sections:
                sections[section_key] = {
                    "name": name,
                    "description": description,
                    "date": section_date,
                    "explorers": [val.strip() for val in section_explorers.split(",")],
                    "surveyors": [val.strip() for val in section_surveyors.split(",")],
                    "shots": [],
                }

            sections[section_key]["shots"].append(shot)

        except KeyError:
            logging.exception(
                "Incomplete shot data: `%(shot)s`",
                {"shot": shot},
            )
            continue  # if data is incomplete, skip this shot

    data["sections"] = list(sections.values())

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step02-sections.json"))

    return data
