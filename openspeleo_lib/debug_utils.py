from __future__ import annotations

from typing import TYPE_CHECKING

import orjson

if TYPE_CHECKING:
    from pathlib import Path


def write_debugdata_to_disk(data: dict, filepath: Path) -> None:
    with filepath.open(mode="w") as f:
        f.write(
            orjson.dumps(
                data, None, option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
            ).decode("utf-8")
        )
