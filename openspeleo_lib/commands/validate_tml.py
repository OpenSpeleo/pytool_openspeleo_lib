import argparse
import pathlib


def validate(args):
    parser = argparse.ArgumentParser(
        prog="validate_tml",
        description="Validate a TML file"
    )
    parser.add_argument(
        "--input_file",
        type=pathlib.Path,
        required=True,
        help="Path to the TML file to be validated",
    )

    parsed_args = parser.parse_args(args)

    input_file = parsed_args.input_file

    if not input_file.exists():
        raise FileNotFoundError(f"File not found: `{input_file}`")

    print(f"Filepath: {input_file}")
