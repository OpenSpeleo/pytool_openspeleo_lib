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
            shot["XMLExplorer"] = ",".join(section["explorers"])
            shot["XMLSurveyor"] = ",".join(section["surveyors"])

            # ----------------- Legacy backport: Ariane < 26 ---------------- #
            _explo_data = {}
            for dest_key, orig_key in [
                ("Explorer", "explorers"),
                ("Surveyor", "surveyors"),
            ]:
                if _value := section.get(orig_key, ""):
                    _explo_data[dest_key] = ",".join(_value)

            # In case only "explorer" data exists - Ariane doesn't store in format XML
            if len(_explo_data) == 1:
                with contextlib.suppress(KeyError):
                    _explo_data = ",".join(_explo_data["explorers"])

            shot["Explorer"] = serialize_dict_to_xmlfield(_explo_data)
            # --------------------------------------------------------------- #

            # # Reverse Color standardization
            # print(f"{shot["Color"]=}")
            # shot["Color"] = shot.pop("Color").replace("#", "0x")

            shots.append(shot)

    data["Data"] = {"SurveyData": shots}

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.export.step02.json"))

    # ------------------------------------------------------------------- #

    return data
