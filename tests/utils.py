from collections import namedtuple
from itertools import product
from itertools import starmap


def named_product(**items):
    Product = namedtuple("Product", items.keys())
    return starmap(Product, product(*items.values()))
