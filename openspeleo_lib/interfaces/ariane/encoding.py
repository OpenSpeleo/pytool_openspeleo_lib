from __future__ import annotations

import logging
from pathlib import Path

# from openspeleo_core.legacy import apply_key_mapping
from openspeleo_core.mapping import apply_key_mapping

from openspeleo_lib.debug_utils import write_debugdata_to_disk
from openspeleo_lib.interfaces.ariane.name_map import ARIANE_MAPPING

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
            shot["section_name"] = f"{section['section_name']}{desc_xml}"
            shot["date"] = section["date"]

            # # ~~~~~~~~~~~~~~~~ Processing Explorers/Surveyors ~~~~~~~~~~~~~~~ #
            shot["explorers"] = section["explorers"]
            shot["surveyors"] = section["surveyors"]
            # # --------------------------------------------------------------- #

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
