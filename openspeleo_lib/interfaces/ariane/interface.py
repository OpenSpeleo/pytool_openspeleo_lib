from __future__ import annotations

import logging
import uuid
import zipfile
from pathlib import Path

from openspeleo_core import ariane_core

from openspeleo_lib.constants import ARIANE_DATA_FILENAME
from openspeleo_lib.debug_utils import write_debugdata_to_disk
from openspeleo_lib.interfaces.ariane.decoding import ariane_decode
from openspeleo_lib.interfaces.ariane.encoding import ariane_encode
from openspeleo_lib.interfaces.ariane.enums_cls import ArianeFileType
from openspeleo_lib.interfaces.ariane.name_map import ARIANE_MAPPING
from openspeleo_lib.interfaces.base import BaseInterface
from openspeleo_lib.models import Survey as BaseSurvey
from openspeleo_lib.pydantic_utils import aliased_model

logger = logging.getLogger(__name__)
DEBUG = False

ArianeSurvey = aliased_model(BaseSurvey, ARIANE_MAPPING, "Ariane")


class ArianeInterface(BaseInterface):
    @classmethod
    def to_file(cls, survey: BaseSurvey, filepath: Path) -> None:
        # 1. Validation

        if not isinstance(survey, ArianeSurvey):
            raise TypeError(f"Unexpected type received: `{type(survey)}`.")

        if (
            filetype := ArianeFileType.from_path(filepath=filepath)
        ) != ArianeFileType.TML:
            raise TypeError(
                f"Unsupported fileformat: `{filetype.name}`. "
                f"Expected: `{ArianeFileType.TML.name}`"
            )

        # 2. Populate missing shot UUIDs
        for shot in survey.shots:
            if shot.id is None:
                shot.id = uuid.uuid4()

        # 3. Convert to dict
        data = survey.model_dump(mode="json", by_alias=True)

        # ------------------------------------------------------------------- #

        if DEBUG:
            write_debugdata_to_disk(data, Path("data.export.before.json"))

        data = ariane_encode(data)

        if DEBUG:
            write_debugdata_to_disk(data, Path("data.export.after.json"))

        # ------------------------------------------------------------------- #

        # =========================== DICT TO XML =========================== #

        # xml_str = dict_to_xml(data)
        xml_str = ariane_core.dict_to_xml_str(data, root_name="CaveFile")

        if DEBUG:
            with Path("data.export.xml").open(mode="w") as f:
                f.write(xml_str)

        # ========================== WRITE TO DISK ========================== #

        with zipfile.ZipFile(filepath, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            logging.debug(
                "Exporting %(filetype)s File: `%(filepath)s`",
                {"filetype": filetype.name, "filepath": filepath},
            )
            zf.writestr(ARIANE_DATA_FILENAME, xml_str)

    @classmethod
    def _from_file(cls, filepath: str | Path) -> BaseSurvey:
        # ========================= INPUT VALIDATION ======================== #

        if (
            filetype := ArianeFileType.from_path(filepath=filepath)
        ) != ArianeFileType.TML:
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
                data = ariane_core.load_ariane_tml_file_to_dict(path=filepath)[
                    "CaveFile"
                ]

            case _:
                raise NotImplementedError(
                    f"Not supported yet - Format: `{filetype.name}`"
                )

        # ------------------------------------------------------------------- #

        if DEBUG:
            write_debugdata_to_disk(data, Path("data.import.before.json"))

        data = ariane_decode(data)

        if DEBUG:
            write_debugdata_to_disk(data, Path("data.import.after.json"))

        # ------------------------------------------------------------------- #

        return ArianeSurvey.model_validate(data, by_alias=True)
