"""Build synthetic measurements from remapped topology, without a private source."""

import math
import zipfile
from pathlib import Path

import orjson
from openspeleo_core import ariane_core
from pyproj import Geod

TOPOLOGY = Path(__file__).parent / "artifacts" / "synthetic-connectivity-topology.json"


def write_connectivity_tml(destination):
    rows = orjson.loads(TOPOLOGY.read_bytes())
    parents = {i: i for row in rows for i in row[1:4] if i >= 0}

    def root(i):
        while parents[i] != i:
            i = parents[i]
        return i

    for _, start, stop, target, kind, _ in rows:
        if kind == "CLOSURE":
            parents[root(start)] = root(target if target >= 0 else stop)
    geod = Geod(ellps="WGS84")

    def position(i):
        identity = root(i)
        angle = identity * 137.5 % 360
        lon, lat, _ = geod.fwd(12.5, 47.5, angle, 20 + identity % 180)
        return lon, lat, 3.0 + identity % 11

    records = []
    for section, start, stop, target, kind, gps in rows:
        lon, lat, depth = position(stop)
        length, azimuth = 0.0, 0.0
        if start >= 0 and kind != "CLOSURE":
            x, y, origin_depth = position(start)
            azimuth, _, distance = geod.inv(x, y, lon, lat)
            length = math.hypot(distance, depth - origin_depth)
        record = {
            "ID": stop,
            "FromID": start,
            "ClosureToID": target,
            "Type": kind,
            "Section": f"Synthetic branch {section}",
            "Date": "2024-02-03",
            "Length": length,
            "Depth": depth,
            "Azimut": azimuth % 360,
        }
        if gps:
            record.update(Latitude=lat, Longitude=lon)
        records.append(record)
    xml = ariane_core.dict_to_xml_str(
        {"unit": "m", "Data": {"SurveyData": records}}, root_name="CaveFile"
    )
    with zipfile.ZipFile(destination, "w") as archive:
        archive.writestr("Data.xml", xml)
