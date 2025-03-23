import logging
import zipfile
from pathlib import Path

from openspeleo_core import ariane_core

from openspeleo_lib.constants import ARIANE_DATA_FILENAME
from openspeleo_lib.debug_utils import write_debugdata_to_disk
from openspeleo_lib.interfaces.base import BaseInterface
from openspeleo_lib.interfaces.compass.encoding import ariane_encode
from openspeleo_lib.interfaces.compass.enums_cls import CompassFileType
from openspeleo_lib.models import Survey

logger = logging.getLogger(__name__)
DEBUG = False


class CompassInterface(BaseInterface):
    @classmethod
    def to_file(cls, survey: Survey, filepath: Path) -> None:
        return
        if (
            filetype := CompassFileType.from_path(filepath=filepath)
        ) != CompassFileType.DAT:
            raise TypeError(
                f"Unsupported fileformat: `{filetype.name}`. "
                f"Expected: `{CompassFileType.DAT.name}`"
            )

        data = survey.model_dump(mode="json")

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
    def _from_file(cls, filepath: str | Path) -> Survey:
        # =========================== XML TO DICT =========================== #
        match filetype := CompassFileType.from_path(filepath=filepath):
            case CompassFileType.DAT:
                data = ariane_core.load_ariane_tml_file_to_dict(path=filepath)[
                    "CaveFile"
                ]

            case _:
                raise NotImplementedError(
                    f"Not supported yet - Format: `{filetype.name}`"
                )

        # # ------------------------------------------------------------------- #

        # if DEBUG:
        #     write_debugdata_to_disk(data, Path("data.import.before.json"))

        # data = ariane_decode(data)

        # if DEBUG:
        #     write_debugdata_to_disk(data, Path("data.import.after.json"))

        # # ------------------------------------------------------------------- #

        # Use to be commented out - probably broken
        return Survey.model_validate(data)
