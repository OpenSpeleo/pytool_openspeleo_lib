"""Translate native topology once into ordinary OpenSpeleo survey models."""

from __future__ import annotations

import math
from collections import defaultdict
from collections import deque
from typing import TYPE_CHECKING

from stalagmight_lib import ShotKind
from stalagmight_lib import read_stalx
from stalagmight_lib.graph import SHOT_START_INDEX_FLAG

from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.interfaces.base import BaseInterface
from openspeleo_lib.models import Survey

if TYPE_CHECKING:
    from pathlib import Path


def _topology(native):
    """Collect measurement endpoints and exact native station identities."""
    explicit = native.schema_version == 19 and native.shot_graph.explicit
    numbers = native.live_numbers() if explicit else {}
    references, observations, links = {}, [], []
    endpoints = {}
    overrides = (
        {item.number: item.reference for item in native.shot_graph.azimuth_overrides}
        if native.shot_graph is not None
        else {}
    )
    for section in native.sections:
        if not section.shots:
            references[section.id, 0] = (section.id, 0)
        for shot in section.shots:
            number = numbers.get((section.id, shot.sequence_order))
            if explicit:
                start, stop = (number, "start"), (number, "end")
                index = (
                    0
                    if shot.sequence_order == 0
                    else (SHOT_START_INDEX_FLAG | shot.sequence_order)
                )
                references[section.id, index] = start
                references[section.id, shot.sequence_order + 1] = stop
                endpoints[number] = (start, stop)
            else:
                start = (section.id, shot.sequence_order)
                stop = (section.id, shot.sequence_order + 1)
                references[section.id, shot.sequence_order] = start
                references[section.id, shot.sequence_order + 1] = stop
            reference = overrides.get(number)
            if reference is not None:
                correction = reference.correction
            elif section.azimuth_north is not None:
                correction = section.azimuth_correction or 0.0
            elif native.project.default_azimuth_reference is not None:
                correction = native.project.default_azimuth_reference.correction
            else:
                correction = 0.0
            observations.append((section, shot, start, stop, correction))
    if explicit:
        origins = {item.number: item.parent for item in native.shot_graph.origins}
        for number, (start, _) in endpoints.items():
            parent = origins[number]
            while parent is not None and parent not in endpoints:
                parent = origins[parent]
            if parent is not None:
                links.append((start, endpoints[parent][1]))
    links.extend(
        (
            references[merge.station_a_section, merge.station_a_index],
            references[merge.station_b_section, merge.station_b_index],
        )
        for merge in native.station_merges
    )
    links.extend(
        (
            references[closure.station_a_section, closure.station_a_index],
            references[closure.station_b_section, closure.station_b_index],
        )
        for closure in native.loop_closures
        if closure.is_aligned
    )
    return references, observations, links


def _normalized_shot(source, section, start, stop, *, correction, reverse, uuid):
    depth_start, depth = (
        (source.depth_out, source.depth_in)
        if reverse
        else (source.depth_in, source.depth_out)
    )
    context = (
        f"shots row {source.id} section {section.id} sequence {source.sequence_order}"
    )
    if not all(
        math.isfinite(value)
        for value in (
            source.length,
            depth_start,
            depth,
            source.azimuth_in,
            correction,
        )
    ) or source.length < abs(depth - depth_start):
        raise ValueError(f"{context}: invalid measured geometry")
    try:
        math.sqrt(source.length**2 - (depth - depth_start) ** 2)
    except (ArithmeticError, ValueError) as exc:
        raise ValueError(f"{context}: invalid measured geometry") from exc
    return {
        "id": uuid,
        "id_start": start,
        "id_stop": stop,
        "shot_type": ArianeShotType.REAL
        if source.kind is ShotKind.NORMAL
        else ArianeShotType.VIRTUAL,
        "length": source.length,
        "depth_start": depth_start,
        "depth_start_is_authoritative": True,
        "depth": depth,
        "azimuth": (source.azimuth_in + correction + (180 if reverse else 0)) % 360,
        "azimuth_secondary": (source.azimuth_out + correction + (180 if reverse else 0))
        % 360,
        "inclination": (
            -source.pitch_in * (-1 if reverse else 1)
            if source.pitch_in is not None
            else None
        ),
        "left": source.right_distance if reverse else source.left_distance,
        "right": source.left_distance if reverse else source.right_distance,
        "up": source.up_distance,
        "down": source.down_distance,
        "comment": source.comment,
        "color": section.color,
    }


def _datum_positions(native, references, find):
    datums = {}
    for datum in sorted(native.zero_datums, key=lambda item: item.id):
        key = find(references[datum.section_id, datum.station_index])
        position = (datum.latitude, datum.longitude)
        if key in datums and datums[key] != position:
            raise ValueError(f"zero_datums row {datum.id}: conflicting coordinates")
        datums[key] = position
    section_for_root = {}
    for (section_id, _), key in references.items():
        section_for_root.setdefault(find(key), section_id)
    for datum in sorted(native.zero_datums, key=lambda item: item.id, reverse=True):
        section_for_root[find(references[datum.section_id, datum.station_index])] = (
            datum.section_id
        )
    return datums, section_for_root


def _shot_uuids(observations):
    uuids, seen_uuids = {}, set()
    for index, (_, shot, _, _, _) in enumerate(observations):
        uuid = shot.uuid
        uuids[index] = (
            uuid
            if uuid is not None and uuid.version == 4 and uuid not in seen_uuids
            else None
        )
        seen_uuids.add(uuid)
    return uuids


def _append_pending_closures(native, references, find, representatives, output):
    for closure in native.loop_closures:
        if closure.is_aligned or closure.strategy not in {
            "Batch",
            "LeastSquaresWeighted",
        }:
            continue
        start = representatives[
            find(references[closure.station_a_section, closure.station_a_index])
        ]
        stop = representatives[
            find(references[closure.station_b_section, closure.station_b_index])
        ]
        if start != stop:
            output[closure.station_a_section].append(
                {
                    "id_start": start,
                    "id_stop": stop,
                    "shot_type": ArianeShotType.CLOSURE,
                }
            )


def _apply_datums(nodes, representatives, datums):
    for key, (latitude, longitude) in datums.items():
        nodes[representatives[key]].update(latitude=latitude, longitude=longitude)


def _observation_adjacency(observations, find):
    adjacency = defaultdict(list)
    for index, (_, _, start, stop, _) in enumerate(observations):
        adjacency[find(start)].append(index)
        adjacency[find(stop)].append(index)
    return adjacency


def _adapt(native):
    references, observations, links = _topology(native)
    parents = {key: key for key in references.values()}

    def find(key):
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    for left, right in links:
        parents[find(right)] = find(left)
    adjacency = _observation_adjacency(observations, find)
    pending = {key: iter(edges) for key, edges in adjacency.items()}
    datums, section_for_root = _datum_positions(native, references, find)
    output = {section.id: [] for section in native.sections}
    nodes, representatives, used = {}, {}, set()
    uuids = _shot_uuids(observations)
    roots = list(datums) + list(dict.fromkeys(find(key) for key in references.values()))
    next_root = len(observations)
    colors = {section.id: section.color for section in native.sections}
    for root in roots:
        if root in representatives:
            continue
        root_id = next_root
        next_root += 1
        representatives[root] = root_id
        depth = 0.0
        if adjacency[root]:
            _, shot, start, _, _ = observations[adjacency[root][0]]
            depth = shot.depth_in if find(start) == root else shot.depth_out
        root_shot = {
            "id_stop": root_id,
            "shot_type": ArianeShotType.START,
            "color": colors[section_for_root[root]],
            "length": 0.0,
            "depth": depth,
            "depth_start": depth,
            "azimuth": 0.0,
        }
        nodes[root_id] = root_shot
        output[section_for_root[root]].append(root_shot)
        queue = deque([root])
        while queue:
            current = queue.popleft()
            for index in pending.get(current, ()):
                if index in used:
                    continue
                used.add(index)
                queue.appendleft(current)
                section, source, start, stop, correction = observations[index]
                reverse = find(start) != current
                target = find(start if reverse else stop)
                values = _normalized_shot(
                    source,
                    section,
                    representatives[current],
                    index,
                    correction=correction,
                    reverse=reverse,
                    uuid=uuids[index],
                )
                output[section.id].append(values)
                nodes[index] = values
                if target in representatives:
                    # Keep every measured leg. A closing leg gets its own endpoint
                    # and an ordinary OSPL station-equivalence record.
                    output[section.id].append(
                        {
                            "id_start": index,
                            "id_stop": representatives[target],
                            "shot_type": ArianeShotType.CLOSURE,
                        }
                    )
                else:
                    representatives[target] = index
                    queue.appendleft(target)
                break
    _append_pending_closures(native, references, find, representatives, output)
    _apply_datums(nodes, representatives, datums)
    return Survey(
        name=native.project.name,
        use_magnetic_azimuth=False,
        measurements_are_adjusted=any(
            closure.is_aligned and closure.strategy != "Move"
            for closure in native.loop_closures
        ),
        sections=[
            {
                "name": section.name
                if section.name is not None
                else f"Section {section.id}",
                "date": section.date,
                "quality": section.quality if section.quality != 1.0 else None,
                "surveyors": [section.surveyor]
                if section.surveyor is not None
                else None,
                "shots": output[section.id],
            }
            for section in native.sections
        ],
    )


class StalagmightInterface(BaseInterface):
    @classmethod
    def _from_file(cls, filepath: Path) -> Survey:
        return _adapt(read_stalx(filepath))

    @classmethod
    def to_file(cls, survey: Survey, filepath: Path) -> None:
        raise NotImplementedError("Native Stalagmight writing is unsupported")
