from __future__ import annotations

import xmltodict
from dicttoxml2 import dicttoxml


def deserialize_xmlfield_to_dict(xmlfield: str) -> dict | str | None:
    return xmltodict.parse(f"<root>{xmlfield}</root>")["root"]


def serialize_dict_to_xmlfield(data: dict | str) -> str:
    if isinstance(data, str):
        return data.strip()

    if data is None:
        return ""

    return dicttoxml(data, attr_type=False, root=False).decode("utf-8")
