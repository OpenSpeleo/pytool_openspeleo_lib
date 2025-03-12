import argparse
import statistics
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

    with tempfile.TemporaryDirectory() as tmp_d:
        target_f = Path(tmp_d) / "export.tml"

        if args.profile:
            ariane_f = Path("tests/artifacts/test_large.tml")
            with Profiler(interval=0.1) as profiler:
                survey = ArianeInterface.from_file(ariane_f)

                ArianeInterface.to_file(survey, target_f)

            profiler.print()

        else:
            for filepath in [
                "tests/artifacts/hand_survey.tml",
                "tests/artifacts/test_large.tml",  # LONG
                "tests/artifacts/test_simple.mini.tml",
                "tests/artifacts/test_simple.tml",
                "tests/artifacts/test_with_walls.tml",
            ]:
                ariane_f = Path(filepath)
                print(f"\nFilename: {filepath} ...\n")  # noqa: T201

                runs = []
                for idx in range(15):
                    start_t = time.perf_counter()
                    survey = ArianeInterface.from_file(ariane_f)
                    runs.append(time.perf_counter() - start_t)
                    print(f"[{idx + 1:02d}] [Loading] Elapsed: {runs[-1]:.2f} secs")  # noqa: T201
                print(f"Average: {statistics.mean(runs[5:]):.2f} secs")  # noqa: T201

                runs = []
                for idx in range(15):
                    start_t = time.perf_counter()
                    ArianeInterface.to_file(survey, target_f)
                    runs.append(time.perf_counter() - start_t)
                    print(f"[{idx + 1:02d}] [Export] Elapsed: {runs[-1]:.2f} secs")  # noqa: T201
                print(f"Average: {statistics.mean(runs[5:]):.2f} secs")  # noqa: T201
