import tempfile
import unittest
import zipfile
from pathlib import Path

import pytest
from parameterized import parameterized

from openspeleo_lib.formats.ariane.enums_cls import ArianeFileType
from openspeleo_lib.formats.ariane.interface import ArianeInterface
from openspeleo_lib.formats.ariane.interface import _extract_zip
from openspeleo_lib.formats.ariane.interface import _filetype
from tests.utils import named_product


class TestArianeParser(unittest.TestCase):

    @parameterized.expand(["path", "str"])
    def test_filetype_valid_tml(self, path_type: str):
        filepath = "test_file.tml"
        if path_type == "path":
            filepath = Path(filepath)

        result = _filetype(filepath)
        assert result == ArianeFileType.TML

    def test_filetype_valid_tmlu(self):
        filepath = Path("test_file.tmlu")
        result = _filetype(filepath)
        assert result == ArianeFileType.TMLU

    def test_filetype_invalid(self):
        filepath = Path("test_file.invalid")
        with pytest.raises(TypeError, match="Unknown value: INVALID"):
            _filetype(filepath)

    def test_extract_zip(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "test.zip"
            data_path = Path(tmp_dir) / "Data.xml"

            with data_path.open("w") as f:
                f.write("<CaveFile></CaveFile>")

            with zipfile.ZipFile(zip_path, "w") as zipf:
                zipf.write(data_path, "Data.xml")

            extracted_files = _extract_zip(zip_path)
            assert "Data.xml" in extracted_files
            assert extracted_files["Data.xml"] == b"<CaveFile></CaveFile>"

    @parameterized.expand(named_product(
        path_type=["path", "str"],
        is_debug=[True, False]
    ))
    def test_from_ariane_file_tml(self, path_type: str, is_debug: bool):
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "test_file.tml"
            data_path = Path(tmp_dir) / "Data.xml"

            with data_path.open("w") as f:
                f.write("<CaveFile><Test>Value</Test></CaveFile>")

            with zipfile.ZipFile(zip_path, "w") as zipf:
                zipf.write(data_path, "Data.xml")

            if path_type == "str":
                zip_path = str(zip_path)

            data = ArianeInterface._load_from_file(zip_path, debug=is_debug)  # noqa: SLF001
            assert data["Test"] == "Value"

    def test_from_ariane_file_tmlu(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test_file.tmlu"

            with file_path.open("w") as f:
                f.write("<CaveFile><Test>Value</Test></CaveFile>")

            with pytest.raises(NotImplementedError, match="Not supported yet"):
                ArianeInterface.from_file(file_path)

    def test_from_ariane_file_nonexistent(self):
        filepath = Path("nonexistent_file.tml")
        with pytest.raises(FileNotFoundError, match=f"File not found: `{filepath}`"):
            ArianeInterface.from_file(filepath)

    def test_from_ariane_file_invalid_format(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test_file.invalid"
            file_path.touch()
            with pytest.raises(TypeError, match="Unknown value: INVALID"):
                ArianeInterface.from_file(file_path)

    @parameterized.expand(["path", "str"])
    def test_fail_to_ariane_file_tmlu(self, path_type: str):
        data = {"Test": "Value"}
        zip_path = Path("test_file.tmlu")

        if path_type == "str":
            zip_path = str(zip_path)

        with pytest.raises(TypeError, match="Unsupported fileformat"):
            ArianeInterface._write_to_file(filepath=zip_path, data=data)  # noqa: SLF001

    @parameterized.expand(["path", "str"])
    def test_to_ariane_file(self, path_type: str):
        data = {"Test": "Value"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "test_file.tml"

            if path_type == "str":
                zip_path = str(zip_path)

            ArianeInterface._write_to_file(filepath=zip_path, data=data)  # noqa: SLF001

            with zipfile.ZipFile(zip_path, "r") as zipf:
                assert "Data.xml" in zipf.namelist()
                with zipf.open("Data.xml") as f:
                    xml_content = f.read()
                    assert b"<Test>Value</Test>" in xml_content

    def test_to_ariane_file_invalid_format(self):
        data = {"Test": "Value"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test_file.invalid"
            with pytest.raises(TypeError, match="Unknown value: INVALID"):
                ArianeInterface._write_to_file(  # noqa: SLF001
                    filepath=file_path,
                    data=data
                )

    def test_to_ariane_file_debug(self):
        data = {"Test": "Value"}
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = Path(tmp_dir) / "test_file.tml"
            ArianeInterface._write_to_file(  # noqa: SLF001
                filepath=zip_path,
                data=data,
                debug=True
            )
            assert (Path() / "Data.xml").exists()


if __name__ == "__main__":
    unittest.main()
