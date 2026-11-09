from __future__ import annotations

import argparse
import logging
import os
import pathlib

import orjson

from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import ArianeInterface
from openspeleo_lib.interfaces import StalagMightInterface

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def convert(args):
    parser = argparse.ArgumentParser(
        prog="convert", description="Convert a Survey File"
    )
    parser.add_argument(
        "-i",
        "--input_file",
        type=pathlib.Path,
        required=True,
        help="Path to the TML or STALX survey",
    )

    parser.add_argument(
        "-o",
        "--output_file",
        type=pathlib.Path,
        default=None,
        required=True,
        help="Path to save the converted file at.",
    )

    parser.add_argument(
        "-w",
        "--overwrite",
        action="store_true",
        help="Allow overwrite an already existing file.",
        default=False,
    )

    parser.add_argument(
        "-b",
        "--beautify",
        action="store_true",
        help="Beautify the JSON output (indent=2 and sorted).",
        default=False,
    )

    parser.add_argument(
        "-f",
        "--format",
        type=str,
        choices=["geojson", "json"],
        required=True,
        help="Conversion format used.",
    )

    parsed_args = parser.parse_args(args)

    input_file: pathlib.Path = parsed_args.input_file
    output_file: pathlib.Path = parsed_args.output_file

    if not input_file.exists():
        raise FileNotFoundError(f"File not found: `{input_file}`")

    if input_file.resolve() == output_file.resolve() or (
        output_file.exists() and input_file.samefile(output_file)
    ):
        raise ValueError("Input and output refer to the same file")

    if output_file.exists() and not parsed_args.overwrite:
        raise FileExistsError(
            f"The file `{output_file}` already existing. "
            "Please pass the flag `--overwrite` to ignore."
        )

    if not input_file.is_file():
        raise ValueError("Input must be a regular file")

    # Keep the inode alive even if a producer removes or replaces the path.
    # A stat snapshot alone can match an unrelated output after inode reuse.
    with input_file.open(mode="rb") as source:
        _convert_file(parsed_args, source_stat=os.fstat(source.fileno()))


def _convert_file(parsed_args, source_stat):
    input_file = parsed_args.input_file
    output_file = parsed_args.output_file

    match input_file.suffix.lower():
        case ".tml":
            survey = ArianeInterface.from_file(input_file)

        case ".stalx":
            survey = StalagMightInterface.from_file(input_file)

        case _:
            raise ValueError(f"Unsupported file format: `{input_file.suffix}`")

    match parsed_args.format:
        case "geojson":
            data = survey_to_geojson(survey)

        case "json":
            data = survey.model_dump(mode="json")

        case _:
            raise ValueError(f"Unsupported conversion format: `{parsed_args.format}`")

    payload = orjson.dumps(
        data,
        None,
        option=(
            (orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
            if parsed_args.beautify
            else None
        ),
    )
    # Exclusive creation enforces no-overwrite even if a file appears during
    # conversion. Append mode opens existing targets without truncating them,
    # letting us verify the actual descriptor before changing its contents.
    with output_file.open(mode="ab" if parsed_args.overwrite else "xb") as output:
        output_stat = os.fstat(output.fileno())
        # A producer can replace the input atomically while we parse it. Protect
        # both the original inode and the current input, which may be the inode
        # the parser actually read, before truncating an output alias.
        try:
            current_source_stat = input_file.stat()
        except FileNotFoundError:
            current_source_stat = None
        if os.path.samestat(source_stat, output_stat) or (
            current_source_stat is not None
            and os.path.samestat(current_source_stat, output_stat)
        ):
            raise ValueError("Input and output refer to the same file")
        if parsed_args.overwrite:
            output.truncate(0)
        output.write(payload)
