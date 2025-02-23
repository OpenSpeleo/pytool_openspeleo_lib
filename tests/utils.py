import hashlib
from collections import namedtuple
from itertools import product
from itertools import starmap
from pathlib import Path


def named_product(**items):
    Product = namedtuple("Product", items.keys())
    return starmap(Product, product(*items.values()))


def compute_filehash(filepath: Path) -> str:
    with filepath.open(mode="rb") as f:
        binary_data = f.read()
    return hashlib.sha256(binary_data).hexdigest()
