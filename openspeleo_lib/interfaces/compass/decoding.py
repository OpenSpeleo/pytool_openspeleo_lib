import logging
from pathlib import Path

from openspeleo_core.mapping import apply_key_mapping

from openspeleo_lib.debug_utils import write_debugdata_to_disk
from openspeleo_lib.interfaces.compass.name_map import COMPASS_INVERSE_MAPPING

logger = logging.getLogger(__name__)
DEBUG = False


def compass_decode(data: dict) -> dict:
    # ===================== DICT FORMATTING TO OSPL ===================== #

    # 1. Apply key mapping: From Ariane to OSPL
    data = apply_key_mapping(data, mapping=COMPASS_INVERSE_MAPPING)

    if DEBUG:
        write_debugdata_to_disk(data, Path("data.import.step01-mapped.json"))

    return data
