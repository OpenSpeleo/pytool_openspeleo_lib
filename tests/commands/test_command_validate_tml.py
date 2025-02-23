import shlex
import subprocess
import unittest
from pathlib import Path


class TestValidateTMLCommand(unittest.TestCase):
    def setUp(self):
        self.cmd = "openspeleo validate_tml"
        self.file = Path("tests/artifacts/hand_survey.tml")

    def run_command(self, command: str):
        return subprocess.run(  # noqa: S603
            shlex.split(command), capture_output=True, text=True, check=False
        )

    def test_valid_command(self):
        """Test the version command to ensure it returns the correct version."""
        result = self.run_command(f"{self.cmd} --input_file={self.file}")
        assert result.returncode == 0

    def test_file_doesnt_exist_command(self):
        """Test the version command to ensure it returns the correct version."""
        result = self.run_command(f"{self.cmd} --input_file=hello.tml")
        assert "FileNotFoundError: File not found: `hello.tml`" in result.stderr

    def test_invalid_command(self):
        """Test the behavior when an invalid command is provided."""
        result = self.run_command(f"{self.cmd} --input_file={self.file} invalid_flag")
        assert "unrecognized arguments: invalid_flag" in result.stderr

    def test_help_output(self):
        """Test the help command to ensure the help message is displayed."""
        result = self.run_command(f"{self.cmd} --help")
        assert "usage:" in result.stdout
        assert "Validate a TML file" in result.stdout
        assert "options:" in result.stdout
        assert "--input_file INPUT_FILE" in result.stdout


if __name__ == "__main__":
    unittest.main()
