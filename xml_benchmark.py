import json
import random
import statistics
import string
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import openspeleo_core
import rxml
import xmltodict
from defusedxml.minidom import parseString
from dicttoxml2 import dicttoxml
from lxml import etree

# Function to generate a large XML file


def generate_large_xml(filename, depth, breadth) -> str:
    def random_string(str_len: int):
        return "".join(random.choices(string.ascii_letters + string.digits, k=str_len))

    result = {}
    current_level = [result]

    for d in range(depth):
        next_level = []
        for parent in current_level:
            for _ in range(breadth):
                key = random_string(5)
                if d == depth - 1:
                    parent[key] = random_string(5)
                else:
                    parent[key] = {}
                    next_level.append(parent[key])
        current_level = next_level

    xml_str = dicttoxml(result, attr_type=False, fold_list=False)

    xml_prettyfied = (
        parseString(xml_str)
        .toprettyxml(indent=" " * 4, encoding="utf-8", standalone=True)
        .decode("utf-8")
    )

    with Path(filename).open("w") as f:
        f.write(xml_prettyfied)


def validate_xml(filename):
    try:
        tree = ET.parse(filename)  # noqa: S314
        _ = tree.getroot()
        print(f"Validated XML file: {filename}")  # noqa: T201
        return True  # noqa: TRY300
    except Exception as e:  # noqa: BLE001
        print(f"XML validation error: {e}")  # noqa: T201
        return False


# ============================ LXML ============================ #


def lxml_xml_to_dict(xml_data: str) -> dict:
    root = etree.fromstring(xml_data)
    return _lxml_etree_to_dict(root)


def _lxml_etree_to_dict(t) -> dict:
    d = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = {}
        for dc in map(_lxml_etree_to_dict, children):
            for k, v in dc.items():
                if k in dd:
                    if not isinstance(dd[k], list):
                        dd[k] = [dd[k]]
                    dd[k].append(v)
                else:
                    dd[k] = v
        d = {t.tag: dd}
    if t.attrib:
        d[t.tag].update(("@" + k, v) for k, v in t.attrib.items())
    if t.text:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]["#text"] = text
        else:
            d[t.tag] = text
    return d


# ---------------------------------------------------------------------- #


if __name__ == "__main__":
    # Generate and validate the XML file
    with tempfile.NamedTemporaryFile() as temp_file:
        # xml_f = Path(temp_file.name)
        xml_f = Path("demo.xml")
        generate_large_xml(xml_f, 4, 25)
        validate_xml(xml_f)
        print(f"FileSize: {xml_f.stat().st_size / 1024.0 / 1024.0:.2f} MBs")  # noqa: T201

        xml_str = xml_f.read_text(encoding="utf-8")
        xml_bstr = xml_str.encode("utf-8")

        runs = []
        for idx in range(15):
            start_time = time.perf_counter()
            data = lxml_xml_to_dict(xml_bstr)
            runs.append(time.perf_counter() - start_time)
            print(f"[{idx + 1:02d}] LXML Time taken: {runs[-1]:.2f} secs")  # noqa: T201
        print(f"Average: {statistics.mean(runs[5:]):.2f} secs")  # noqa: T201

        print()  # noqa: T201

        runs = []
        for idx in range(15):
            start_time = time.perf_counter()
            data = xmltodict.parse(xml_str)
            runs.append(time.perf_counter() - start_time)
            print(f"[{idx + 1:02d}] XMLTODICT Time taken: {runs[-1]:.2f} secs")  # noqa: T201
        print(f"Average: {statistics.mean(runs[5:]):.2f} secs")  # noqa: T201

        with Path("demo.json").open("w") as f:
            data = xmltodict.parse(xml_str)
            json.dump(data, f, indent=4)

        print()  # noqa: T201

        runs = []
        for idx in range(15):
            start_time = time.perf_counter()
            data = rxml.read_string(xml_str, root_tag="root").to_dict()
            runs.append(time.perf_counter() - start_time)
            print(f"[{idx + 1:02d}] RXML Time taken: {runs[-1]:.2f} secs")  # noqa: T201
        print(f"Average: {statistics.mean(runs[5:]):.2f} secs")  # noqa: T201

        print()  # noqa: T201

        runs = []
        for idx in range(15):
            start_time = time.perf_counter()
            data = openspeleo_core.xml_str_to_dict(xml_str)
            runs.append(time.perf_counter() - start_time)
            print(f"[{idx + 1:02d}] XML_DICT Time taken: {runs[-1]:.2f} secs")  # noqa: T201
        print(f"Average: {statistics.mean(runs[5:]):.2f} secs")  # noqa: T201
