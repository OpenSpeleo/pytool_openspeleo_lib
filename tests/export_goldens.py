"""Reproducible exports of the public interface fixtures.

JSON pins the reader's unmodified common-model output. Geographic exports use
copies with synthetic (40, -70) controls for STARTs lacking geolocation. Spatial
Gaussian solves use independently declared synthetic ENU Z=0 controls at
geographic anchors. Presets explicitly fixing control depths retain that policy.
These controls test conversion, not real-world placement. Original source
measurements and files remain unchanged.

Regenerate explicitly from the package root:
uv run python -m tests.export_goldens tests/artifacts
"""

import argparse
from dataclasses import replace
from pathlib import Path

import orjson
from cave_closure import LoopClosureMode

from openspeleo_lib import LoopClosureSolver
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.interfaces import StalagmightInterface
from openspeleo_lib.loop_closure.presets import PRESETS
from openspeleo_lib.models import Survey

ARTIFACTS = Path(__file__).parent / "artifacts"
FIXTURES = (
    ("stalagmight.stalx", "stalagmight"),
    ("test_ariane_v26.tml", "test_ariane_v26"),
    ("test_large.tml", "test_large"),
    ("test_simple.tml", "test_simple"),
    ("test_simple.tmlu", "test_simple-tmlu"),
    ("test_simple.mini.tml", "test_simple.mini"),
    ("test_with_walls.tml", "test_with_walls"),
)
EXPORTS = ("json", "geojson", *PRESETS.values())
JSON_OPTIONS = orjson.OPT_SORT_KEYS


def read_source(filename):
    reader = StalagmightInterface if filename.endswith(".stalx") else ArianeInterface
    return reader.from_file(ARTIFACTS / filename)


def golden_name(prefix, export):
    if isinstance(export, LoopClosureSolver):
        if export.name is None:
            raise ValueError("Export presets must have a stable name")
        return f"{prefix}-{export.name}.geojson"
    return f"{prefix}.{export}"


def geographic_source(source):
    """Keep reader JSON pristine and declare synthetic test controls explicitly."""
    view = Survey.model_validate_json(source.model_dump_json())
    for shot in view.shots:
        if (
            shot.shot_type == ArianeShotType.START
            and not shot.excluded
            and not shot.is_geolocation_known()
        ):
            shot.latitude, shot.longitude = 40.0, -70.0
    return view


def export_geojson(source, export):
    view = geographic_source(source)
    solver = None
    if isinstance(export, LoopClosureSolver):
        solver = replace(
            export,
            source_is_fresh=True,
            vertical_controls=(
                {
                    shot.id_stop: 0.0
                    for shot in view.shots
                    if shot.shot_type != ArianeShotType.CLOSURE
                    and not shot.excluded
                    and shot.is_geolocation_known()
                }
                if export.mode == LoopClosureMode.SPATIAL
                and not export.fix_control_depths
                else None
            ),
        )
    return survey_to_geojson(view, loop_closure_solver=solver)


def write_export(source, export, destination):
    if export == "json":
        source.to_json(destination, beautify=False)
    else:
        destination.write_bytes(
            orjson.dumps(export_geojson(source, export), option=JSON_OPTIONS)
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    for filename, prefix in FIXTURES:
        source = read_source(filename)
        before = source.model_dump_json()
        for export in EXPORTS:
            write_export(
                source, export, args.output_directory / golden_name(prefix, export)
            )
        assert source.model_dump_json() == before


if __name__ == "__main__":
    main()
