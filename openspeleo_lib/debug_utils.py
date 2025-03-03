from pathlib import Path

import orjson


def write_debugdata_to_disk(data: dict, filepath: Path) -> None:
    with filepath.open(mode="w") as f:
        f.write(
            orjson.dumps(
                data, None, option=(orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS)
            ).decode("utf-8")
        )
