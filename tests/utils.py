from __future__ import annotations

import hashlib
import zipfile
from collections import namedtuple
from itertools import product
from itertools import starmap
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


def named_product(**items):
    Product = namedtuple("Product", items.keys())
    return starmap(Product, product(*items.values()))


def compute_filehash(filepath: Path) -> str:
    with filepath.open(mode="rb") as f:
        binary_data = f.read()
    return hashlib.sha256(binary_data).hexdigest()


def compute_filehash_in_zip(zip_path: str | Path, file_name: str):
    """Computes the hash of a file inside a ZIP without extracting it.

    Args:
        zip_path (str): Path to the ZIP archive.
        file_name (str): Name of the file inside the ZIP.
        hash_algo (str): Hashing algorithm (default: "sha256").

    Returns:
        str: Hex digest of the file's hash.
    """

    sha256 = hashlib.sha256()
    with zipfile.ZipFile(zip_path, "r") as zip_file:
        file = zip_file.open(file_name)
        while chunk := file.read(8192):  # Read in chunks of 8KB
            sha256.update(chunk)
    return sha256.hexdigest()
