from __future__ import annotations

import contextlib
import logging
from pathlib import Path

from openspeleo_lib.debug_utils import write_debugdata_to_disk
from openspeleo_lib.interfaces.ariane.xml_utils import serialize_dict_to_xmlfield

logger = logging.getLogger(__name__)
DEBUG = False


def ariane_encode(data: dict) -> dict:
    # ==================== FORMATING FROM OSPL TO TML =================== #

    # 1. Formatting Unit - ariane unit is lowercase - OSPL unit is uppercase
    data["unit"] = data["unit"].lower()

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.export.step01.json"))

    # 2. Flatten sections into shots
    shots = []
    for section in data.pop("sections"):
        for shot in section.pop("shots"):
            desc_xml = ""
            if description := section["description"]:
                desc_xml = f"<SectionDescription>{description}</SectionDescription>"
            shot["Section"] = f"{section['name']}{desc_xml}"
            shot["Date"] = section["date"]

            # ~~~~~~~~~~~~~~~~ Processing Explorers/Surveyors ~~~~~~~~~~~~~~~ #
            # Ariane stores this field as an escaped embedded fragment with
            # BOTH tags, even when one is empty (see
            # tests/artifacts/hand_survey.tml, authored by Ariane itself):
            #     <Explorer>E</Explorer><Surveyor>S</Surveyor>
            # Any deviation - a Surveyor-only fragment (previous behavior when
            # explorers was empty), a bare string, or extra XMLExplorer /
            # XMLSurveyor sibling tags - is rendered by Ariane as literal text
            # in the data table's Explorer column.
            shot["Explorer"] = serialize_dict_to_xmlfield(
                {
                    "Explorer": ",".join(section["explorers"]),
                    "Surveyor": ",".join(section["surveyors"]),
                }
            )
            # --------------------------------------------------------------- #

            # Color standardization: Ariane-authored files use 0xrrggbbaa;
            # the model's CSS-style default (#FFB366) is not an Ariane format.
            color = shot.get("Color")
            if isinstance(color, str) and color.startswith("#"):
                hex_part = color[1:].lower()
                if len(hex_part) == 6:
                    hex_part += "ff"  # opaque, as on Ariane-authored shots
                shot["Color"] = f"0x{hex_part}"

            shots.append(shot)

    data["Data"] = {"SurveyData": shots}

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.export.step02.json"))

    # ------------------------------------------------------------------- #

    return data
