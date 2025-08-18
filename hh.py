#!/usr/bin/env python

# ruff: noqa: T201

import time
from pathlib import Path

import orjson

from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.models import Survey

if __name__ == "__main__":
    # filepath = Path("camilo__2025-06-20_22h13.tml")
    # filepath = Path("mayan-blue__2024-06-26_15h26.tml")
    # filepath = Path("oho-tucha__2025-05-19_22h40.tml")
    # for filepath in [Path("tests/artifacts/private/ponderosa__2025-08-13_16h50.tml")]:
    for filepath in sorted(Path("tests/artifacts/private").glob("*.tml")):
        print(f"Processing file: {filepath} ...")
        script_time = time.perf_counter()

        start_time = time.perf_counter()
        survey: Survey = ArianeInterface.from_file(filepath)
        end_time = time.perf_counter()
        print(
            "Opening Ariane file and conversion to OSPL took: "
            f"{end_time - start_time:.4f} seconds"
        )

        start_time = time.perf_counter()
        geojson_data = survey_to_geojson(survey)
        end_time = time.perf_counter()
        print(
            f"GeoJSON conversion took:                        "
            f" {end_time - start_time:.4f} seconds"
        )

        with (filepath.parent / f"{filepath.stem}.geojson").open(mode="wb") as f:
            f.write(orjson.dumps(geojson_data))

        end_time = time.perf_counter()
        print(
            f"Total script script with write to disk took:     "
            f"{end_time - script_time:.4f} seconds\n"
        )

# with Path("survey.json").open(mode="wb") as f:
#     f.write(
#         orjson.dumps(
#             survey.model_dump(),
#             option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
#         )
#     )
