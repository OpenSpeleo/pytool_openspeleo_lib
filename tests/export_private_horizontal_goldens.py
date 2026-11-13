"""Explicitly generate encrypted, minified horizontal private-fixture snapshots.

uv run python -m tests.export_private_horizontal_goldens \
    tests/artifacts/private/ariane --env-file .env

Plaintext inputs and outputs are confined to an OS temporary directory. Normal
pytest runs decrypt the encrypted goldens through the existing fixture setup.
"""

import argparse
import base64
import lzma
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import orjson
from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from dotenv import load_dotenv

from openspeleo_lib.commands.encrypt import encrypt
from openspeleo_lib.geojson import InconsistentShotCoordinatesError
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.loop_closure.presets import (
    InverseLengthWeightedLeastSquaresHorizontalSolver,
)
from tests.conftest import PRIVATE_ARIANE_DATA_DIR
from tests.conftest import XZ_MAGIC_HEADER


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_directory", type=Path)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    args = parser.parse_args()
    load_dotenv(args.env_file, override=True)
    key = os.environ.get("ARTIFACT_ENCRYPTION_KEY")
    if key is None:
        parser.error(
            "ARTIFACT_ENCRYPTION_KEY is required for private golden generation"
        )
    aead = AESSIV(base64.urlsafe_b64decode(key))
    args.output_directory.mkdir(parents=True, exist_ok=True)
    solver = InverseLengthWeightedLeastSquaresHorizontalSolver
    solver_name = solver.name
    converted = rejected = 0
    with TemporaryDirectory(prefix="openspeleo-horizontal-goldens-") as directory:
        scratch = Path(directory)
        for encrypted in sorted(PRIVATE_ARIANE_DATA_DIR.glob("*.tml.encrypted")):
            data = aead.decrypt(encrypted.read_bytes(), None)
            if data.startswith(XZ_MAGIC_HEADER):
                data = lzma.decompress(data)
            source_path = scratch / encrypted.stem
            source_path.write_bytes(data)
            try:
                source = ArianeInterface.from_file(source_path)
                result = survey_to_geojson(
                    source,
                    loop_closure_solver=solver,
                )
            except InconsistentShotCoordinatesError:
                rejected += 1
                continue
            except Exception as error:  # noqa: BLE001 - redact private survey details
                raise RuntimeError(
                    f"Private horizontal export failed: {source_path.name} "
                    f"({type(error).__name__}); survey data omitted"
                ) from None
            clear_output = scratch / f"{source_path.stem}-{solver_name}.geojson"
            clear_output.write_bytes(orjson.dumps(result, option=orjson.OPT_SORT_KEYS))
            encrypt(
                [
                    "-i",
                    str(clear_output),
                    "-o",
                    str(args.output_directory / f"{clear_output.name}.encrypted"),
                    "-e",
                    str(args.env_file),
                ]
            )
            converted += 1
    print(  # noqa: T201 - report counts only, never private survey data
        f"Generated {converted} encrypted {solver_name} goldens; "
        f"{rejected} rejected by coordinate guard"
    )


if __name__ == "__main__":
    main()
