from __future__ import annotations

import argparse
import logging
import pathlib

from openspeleo_lib.interfaces import ArianeInterface

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def validate(args):
    parser = argparse.ArgumentParser(
        prog="validate_tml", description="Validate a TML file"
    )
    parser.add_argument(
        "-i",
        "--input_file",
        type=pathlib.Path,
        required=True,
        help="Path to the TML file to be validated",
    )

    parsed_args = parser.parse_args(args)

    input_file = parsed_args.input_file

    if not input_file.exists():
        raise FileNotFoundError(f"File not found: `{input_file}`")

    _ = ArianeInterface.from_file(input_file)

    logger.info("Filepath: `%(input_file)s` ... VALID", {"input_file": input_file})
