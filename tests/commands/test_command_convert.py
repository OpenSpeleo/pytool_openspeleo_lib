from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from tests.utils import write_synthetic_tml

SYNTHETIC_INVALID_TML = (
    Path(__file__).parents[1] / "artifacts" / "synthetic-invalid.tml"
)


def run_convert(input_file: Path, output_file: Path):
    executable = Path(sys.executable).with_name("openspeleo")
    return subprocess.run(  # noqa: S603
        [
            str(executable),
            "convert",
            "--input_file",
            str(input_file),
            "--output_file",
            str(output_file),
            "--format",
            "geojson",
            "--overwrite",
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_invalid_coordinates_abort_without_modifying_output(tmp_path: Path):
    new_output = tmp_path / "new.geojson"
    existing_output = tmp_path / "existing.geojson"
    existing_contents = b"existing output must be preserved"
    existing_output.write_bytes(existing_contents)

    new_result = run_convert(SYNTHETIC_INVALID_TML, new_output)
    overwrite_result = run_convert(SYNTHETIC_INVALID_TML, existing_output)

    for result in [new_result, overwrite_result]:
        assert result.returncode != 0
        assert "InconsistentShotCoordinatesError" in result.stderr
        assert "[Shot ID=4242]" in result.stderr
        assert "maximum allowed discrepancy=500.000 m" in result.stderr

    assert not new_output.exists()
    assert existing_output.read_bytes() == existing_contents


def test_out_of_range_coordinates_preserve_output_and_report_stations(tmp_path):
    source = tmp_path / "invalid.tml"
    write_synthetic_tml(source, coordinates=[(40, -183)] * 4)
    new_output = tmp_path / "new.geojson"
    existing_output = tmp_path / "existing.geojson"
    existing_output.write_bytes(b"keep this")
    for output in [new_output, existing_output]:
        result = run_convert(source, output)
        assert result.returncode != 0
        assert "ValidationError" in result.stderr
        for index in range(4):
            assert f"station 'ANCHOR{index}'" in result.stderr
        assert "[-180, 180]" in result.stderr
    assert not new_output.exists()
    assert existing_output.read_bytes() == b"keep this"
