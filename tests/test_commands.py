import shlex
import subprocess
import unittest


class TestOpenspeleoCommands(unittest.TestCase):
    def run_command(self, command: str):
        return subprocess.run(
            shlex.split(command),  # noqa: S603
            capture_output=True,
            text=True,
            check=False,
        )

    def test_version_command(self):
        """Test the version command to ensure it returns the correct version."""
        result = self.run_command("openspeleo --version")
        assert "openspeleo_lib version:" in result.stdout

    def test_invalid_command(self):
        """Test the behavior when an invalid command is provided."""
        result = self.run_command("openspeleo invalid_command")
        assert "argument command: invalid choice" in result.stderr

    def test_help_output(self):
        """Test the help command to ensure the help message is displayed."""
        result = self.run_command("openspeleo --help")
        assert "usage:" in result.stdout
        assert "positional arguments:" in result.stdout
        assert "options:" in result.stdout


if __name__ == "__main__":
    unittest.main()
