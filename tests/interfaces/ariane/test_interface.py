import tempfile
import unittest
import zipfile
from pathlib import Path

import pytest
from parameterized import parameterized

from openspeleo_lib.interfaces.ariane.enums_cls import ArianeFileType
from openspeleo_lib.interfaces.ariane.interface import ArianeInterface
from openspeleo_lib.interfaces.ariane.interface import _extract_zip
from openspeleo_lib.interfaces.ariane.interface import _filetype


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

    def test_from_ariane_file_tmlu(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "test_file.tmlu"

            with file_path.open("w") as f:
                f.write("<CaveFile><Test>Value</Test></CaveFile>")

            with pytest.raises(TypeError, match="Unsupported fileformat: `TMLU`"):
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

    def test_instanciation(self):
        with pytest.raises(NotImplementedError):
            ArianeInterface()


if __name__ == "__main__":
    unittest.main()
