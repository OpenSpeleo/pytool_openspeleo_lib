"""Translate native stations into the shared directed survey graph."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections import deque
from typing import TYPE_CHECKING

from pydantic import Field
from pydantic import PrivateAttr
from stalagmight_lib import ShotKind
from stalagmight_lib import read_stalx

from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.interfaces.base import BaseInterface
from openspeleo_lib.models import Section
from openspeleo_lib.models import Shot
from openspeleo_lib.models import Survey

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class StalagMightShot(Shot):
    inclination: float | None = None

    _source: tuple[int, int, int] | None = PrivateAttr(default=None)

    def length_2d(self, origin_depth: float | None) -> float:
        try:
            return super().length_2d(self.depth_start)
        except (ArithmeticError, ValueError) as exc:
            if self._source is None:
                raise
            row, section, sequence = self._source
            raise ValueError(
                f"shots row {row} section {section} sequence {sequence}: {exc}"
            ) from exc

    def is_geolocation_known(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class StalagMightSection(Section):
    # Native names have no length limit; preserve them without truncation.
    name: str
    shots: list[StalagMightShot] = Field(default_factory=list)

    @property
    def computed_declination(self) -> float:
        return self.declination


class StalagMightSurvey(Survey):
    sections: list[StalagMightSection] = Field(default_factory=list)

    # Keep source identity and constraints available without serializing native
    # fields into the common JSON/GeoJSON contract.
    _native = PrivateAttr(default=None)


def _forest(native):
    """Return (section, attachment station, parent station) in traversal order."""
    adjacency = defaultdict(list)
    for merge in native.station_merges:
        a = (merge.station_a_section, merge.station_a_index)
        b = (merge.station_b_section, merge.station_b_index)
        adjacency[a[0]].append((merge.id, a[1], b[0], b[1]))
        adjacency[b[0]].append((merge.id, b[1], a[0], a[1]))
    datums_by_section = defaultdict(list)
    for datum in native.zero_datums:
        datums_by_section[datum.section_id].append(datum)
    remaining = {section.id for section in native.sections}
    traversal = []
    selected = 0
    for seed in sorted(remaining):
        if seed not in remaining:
            continue
        component = set()
        queue = [seed]
        while queue:
            section_id = queue.pop()
            if section_id in component:
                continue
            component.add(section_id)
            queue.extend(edge[2] for edge in adjacency[section_id])
        datum = min(
            (
                datum
                for section_id in component
                for datum in datums_by_section[section_id]
            ),
            key=lambda datum: datum.id,
            default=None,
        )
        root = datum.section_id if datum is not None else seed
        pivot = datum.station_index if datum is not None else 0
        queue = deque([(root, pivot, None)])
        seen = {root}
        while queue:
            section_id, pivot, parent = queue.popleft()
            traversal.append((section_id, pivot, parent))
            for _, index, child, child_index in sorted(adjacency[section_id]):
                if child in seen:
                    continue
                seen.add(child)
                selected += 1
                queue.append((child, child_index, (section_id, index)))
        remaining -= component
    if len(native.station_merges) > selected:
        logger.warning(
            "%d additional station merge constraints retained in native data; "
            "no closure adjustment was applied",
            len(native.station_merges) - selected,
        )
    return traversal


def _normalized_shot(source, section, start, stop, *, reverse, uuid):
    depth_start, depth = source.depth_in, source.depth_out
    left, right = source.left_distance, source.right_distance
    inclination = -source.pitch_in if source.pitch_in is not None else None
    if reverse:
        depth_start, depth = depth, depth_start
        left, right = right, left
        if inclination is not None:
            inclination = -inclination
    values = {
        "id": uuid,
        "id_start": start,
        "id_stop": stop,
        "shot_type": (
            ArianeShotType.REAL
            if source.kind == ShotKind.NORMAL
            else ArianeShotType.VIRTUAL
        ),
        "length": source.length,
        "depth_start": depth_start,
        "depth": depth,
        "azimuth": (source.azimuth_in + (180 if reverse else 0)) % 360,
        "left": left,
        "right": right,
        "up": source.up_distance,
        "down": source.down_distance,
        "comment": source.comment,
        "color": section.color,
    }
    if inclination is not None:
        values["inclination"] = inclination
    return values


def _adapt(native):
    sections = {section.id: section for section in native.sections}
    traversal = _forest(native)
    ids, uuids, used_uuids = {}, {}, set()
    for section in sorted(native.sections, key=lambda section: section.id):
        for source in section.shots:
            ids[source.id] = len(ids)
            uuid = source.uuid
            uuids[source.id] = None
            if uuid is not None and uuid.version == 4 and uuid not in used_uuids:
                uuids[source.id] = uuid
                used_uuids.add(uuid)
    stations, nodes, normalized = {}, {}, {}
    root_id = len(ids)
    for section_id, pivot, parent in traversal:
        section = sections[section_id]
        output = []
        if parent is None:
            station_id = root_id
            root_id += 1
            depth = (
                section.shots[pivot].depth_in
                if pivot < len(section.shots)
                else section.shots[-1].depth_out
                if section.shots
                else 0.0
            )
            root = {
                "id_stop": station_id,
                "shot_type": ArianeShotType.START,
                "length": 0,
                "depth": depth,
                "depth_start": depth,
                "azimuth": 0,
                "color": section.color,
            }
            output.append(root)
            nodes[station_id] = root
        else:
            station_id = stations[parent]
        stations[section_id, pivot] = station_id
        for indices, reverse in (
            (range(pivot, len(section.shots)), False),
            (range(pivot - 1, -1, -1), True),
        ):
            start = station_id
            for index in indices:
                source = section.shots[index]
                stop = ids[source.id]
                shot = _normalized_shot(
                    source, section, start, stop, reverse=reverse, uuid=uuids[source.id]
                )
                output.append(shot)
                nodes[stop] = shot
                stations[section_id, index if reverse else index + 1] = stop
                start = stop
        default = native.project.default_azimuth_reference
        correction = (
            section.azimuth_correction or 0.0
            if section.azimuth_north is not None
            else default.correction
            if default is not None
            else 0.0
        )
        normalized[section_id] = {
            "name": section.name
            if section.name is not None
            else f"Section {section.id}",
            "date": section.date,
            "surveyors": [section.surveyor] if section.surveyor is not None else None,
            "declination": correction,
            "shots": output,
        }
    assigned = {}
    for datum in sorted(native.zero_datums, key=lambda datum: datum.id):
        node_id = stations[datum.section_id, datum.station_index]
        coordinates = (datum.latitude, datum.longitude)
        if node_id in assigned and assigned[node_id] != coordinates:
            raise ValueError(
                f"zero_datums row {datum.id}: conflicting coordinates "
                f"at graph node {node_id}"
            )
        assigned[node_id] = coordinates
        nodes[node_id]["latitude"], nodes[node_id]["longitude"] = coordinates
    survey = StalagMightSurvey(
        name=native.project.name,
        sections=[normalized[key] for key in sorted(normalized)],
    )
    # Validate the nested graph once, so uniqueness registration is neither
    # repeated for existing instances nor bypassed for raw model/JSON inputs.
    source_ids = {
        ids[source.id]: (source.id, source.section_id, source.sequence_order)
        for section in native.sections
        for source in section.shots
    }
    for shot in survey.shots:
        shot._source = source_ids.get(shot.id_stop)  # noqa: SLF001 - adapter identity
    survey._native = native  # noqa: SLF001 - adapter owns the native data
    return survey


class StalagMightInterface(BaseInterface):
    @classmethod
    def to_file(cls, survey: Survey, filepath: Path) -> None:
        raise NotImplementedError("Native StalagMight writing is unsupported")

    @classmethod
    def _from_file(cls, filepath: Path) -> Survey:
        return _adapt(read_stalx(filepath))
