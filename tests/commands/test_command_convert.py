from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import orjson
import pytest

from openspeleo_lib.commands.convert import convert
from openspeleo_lib.interfaces import StalagmightInterface
from tests.stalagmight_helpers import write_stalx
from tests.utils import write_synthetic_tml

SYNTHETIC_INVALID_TML = (
    Path(__file__).parents[1] / "artifacts" / "synthetic-invalid.tml"
)


def run_convert(input_file: Path, output_file: Path, *, loop_closure=False):
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
            *(["--loop-closure"] if loop_closure else []),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("loop_closure", [False, True])
def test_invalid_coordinates_abort_without_modifying_output(
    tmp_path: Path, loop_closure
):
    new_output = tmp_path / "new.geojson"
    existing_output = tmp_path / "existing.geojson"
    existing_contents = b"existing output must be preserved"
    existing_output.write_bytes(existing_contents)

    new_result = run_convert(
        SYNTHETIC_INVALID_TML, new_output, loop_closure=loop_closure
    )
    overwrite_result = run_convert(
        SYNTHETIC_INVALID_TML, existing_output, loop_closure=loop_closure
    )

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


@pytest.mark.parametrize("failure", [None, "read", "geometry", "serialization"])
def test_source_identity_stays_pinned_and_handle_closes(tmp_path, monkeypatch, failure):
    source = write_stalx(
        tmp_path / "survey.stalx",
        [{"id": 42, "shots": [{}]}],
        [(1, 42, 0, 40.0, -70.0, 0.0)],
    )
    output = tmp_path / "output.geojson"
    source_stat = source.stat()
    source_handles = []
    original_open = Path.open
    original_read = StalagmightInterface.from_file

    def track_source_handles(path, *args, **kwargs):
        handle = original_open(path, *args, **kwargs)
        if path == source:
            source_handles.append(handle)
        return handle

    def assert_source_pinned():
        assert any(
            not handle.closed
            and os.path.samestat(source_stat, os.fstat(handle.fileno()))
            for handle in source_handles
        ), "The source inode must remain pinned until conversion finishes"

    def read_then_remove(path):
        if failure == "read":
            assert_source_pinned()
            raise ValueError("synthetic read failure")
        survey = original_read(path)
        assert_source_pinned()
        path.unlink()
        return survey

    def fail_conversion(*args, **kwargs):
        raise ValueError(f"synthetic {failure} failure")

    monkeypatch.setattr(Path, "open", track_source_handles)
    monkeypatch.setattr(StalagmightInterface, "from_file", read_then_remove)
    if failure == "geometry":
        monkeypatch.setattr(
            "openspeleo_lib.commands.convert.survey_to_geojson", fail_conversion
        )
    elif failure == "serialization":
        monkeypatch.setattr(orjson, "dumps", fail_conversion)
    args = ["-i", str(source), "-o", str(output), "-f", "geojson"]
    if failure is None:
        convert(args)
        assert output.exists()
    else:
        with pytest.raises(ValueError, match=f"synthetic {failure} failure"):
            convert(args)
        assert not output.exists()
    assert source_handles
    assert all(handle.closed for handle in source_handles)


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="Named pipes require POSIX")
def test_non_regular_input_is_rejected_without_opening(tmp_path, monkeypatch):
    source = tmp_path / "pipe.stalx"
    output = tmp_path / "output.json"
    os.mkfifo(source)
    original_open = Path.open

    def refuse_pipe_open(path, *args, **kwargs):
        assert path != source, "Opening a named pipe could block conversion"
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refuse_pipe_open)
    with pytest.raises(ValueError, match="regular file"):
        convert(["-i", str(source), "-o", str(output), "-f", "json"])
    assert not output.exists()
