import argparse
import tempfile
import time
from pathlib import Path

from pyinstrument import Profiler

from openspeleo_lib.interfaces import ArianeInterface

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="convert", description="Convert a Survey File"
    )

    parser.add_argument(
        "-p",
        "--profile",
        action="store_true",
        help="Use PyInstrument to profile execution. Otherwise `time.perf_counter()`.",
        default=False,
    )

    args = parser.parse_args()

    ariane_f = Path("/workspace/openspeleo_lib/tests/artifacts/test_large.tml")

    with tempfile.TemporaryDirectory() as tmp_d:
        target_f = Path(tmp_d) / "export.tml"

        if args.profile:
            with Profiler(interval=0.1) as profiler:
                survey = ArianeInterface.from_file(ariane_f)

                ArianeInterface.to_file(survey, target_f)

            profiler.print()

        else:
            start_t = time.perf_counter()
            survey = ArianeInterface.from_file(ariane_f)
            print(f"[Loading] Elapsed: {time.perf_counter() - start_t}")  # noqa: T201

            start_t = time.perf_counter()
            ArianeInterface.to_file(survey, target_f)
            print(f"[Export] Elapsed: {time.perf_counter() - start_t}")  # noqa: T201
