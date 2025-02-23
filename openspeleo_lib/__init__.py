#!/usr/bin/env python

import importlib.metadata

__version__ = importlib.metadata.version("openspeleo_lib")

# Initialize the logger
from openspeleo_lib import logger  # noqa: F401
