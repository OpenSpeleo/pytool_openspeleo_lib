import argparse
import logging
import pathlib

logger = logging.getLogger(__name__)


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

    logger.info(f"Filepath: {input_file}")  # noqa: T201
