from __future__ import annotations

import datetime
import hashlib
import zipfile
from collections import namedtuple
from itertools import product
from itertools import starmap
from typing import TYPE_CHECKING

from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.enums import LengthUnits
from openspeleo_lib.models import Section
from openspeleo_lib.models import Shot
from openspeleo_lib.models import Survey

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


def make_synthetic_geolocation_survey(
    *,
    unit: LengthUnits = LengthUnits.METERS,
    child_coordinates: tuple[float, float] | None = None,
    child_id: int = 4242,
    child_id_start: int = 1,
    child_type: ArianeShotType = ArianeShotType.REAL,
    child_excluded: bool = False,
) -> Survey:
    """Build a two-shot survey using synthetic, non-fixture coordinates."""
    root = Shot(
        id_stop=1,
        id_start=-1,
        name="START",
        length=0.0,
        depth=0.0,
        depth_start=0.0,
        azimuth=0.0,
        inclination=0.0,
        latitude=40.0,
        longitude=-70.0,
        shot_type=ArianeShotType.START,
        locked=True,
        left=0.0,
        right=0.0,
        up=0.0,
        down=0.0,
    )

    child_latitude = None
    child_longitude = None
    if child_coordinates is not None:
        child_latitude, child_longitude = child_coordinates

    child_length = 10.0
    if unit == LengthUnits.FEET:
        child_length /= 0.3048

    child = Shot(
        id_stop=child_id,
        id_start=child_id_start,
        length=child_length,
        depth=0.0,
        depth_start=-1.0,
        azimuth=90.0,
        inclination=0.0,
        latitude=child_latitude,
        longitude=child_longitude,
        shot_type=child_type,
        excluded=child_excluded,
        left=0.0,
        right=0.0,
        up=0.0,
        down=0.0,
    )

    section = Section(
        name="Synthetic Section",
        date=datetime.date(2025, 1, 1),
        explorers=[],
        surveyors=[],
        shots=[root, child],
    )
    return Survey(
        name="Synthetic Coordinate Guard Survey",
        sections=[section],
        unit=unit,
    )
