"""Physical connectivity selections shared by geographic export and adjustment."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections import deque
from dataclasses import dataclass

from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.models import Shot

logger = logging.getLogger(__name__)


def records(survey):
    for section_index, section in enumerate(survey.sections):
        for shot_index, shot in enumerate(section.shots):
            yield (section_index, shot_index), shot


def closure_endpoints(shot):
    return (
        shot.id_start,
        shot.closure_to_id if shot.closure_to_id >= 0 else shot.id_stop,
    )


@dataclass(frozen=True)
class SurveyGraph:
    stations: frozenset[int]
    defined_stations: frozenset[int]
    legs: frozenset[tuple[int, int]]
    closures: frozenset[tuple[int, int]]
    aliases: tuple[tuple[int, int], ...]

    def nodes(self, survey):
        nodes = {
            shot.id_stop: shot
            for shot in survey.shots
            if shot.shot_type != ArianeShotType.CLOSURE
            and not shot.excluded
            and shot.id_stop in self.stations
        }
        for identity, parent_id in self.aliases:
            parent = nodes[parent_id]
            alias = Shot(
                id_start=parent_id,
                id_stop=identity,
                length=0.0,
                depth=parent.depth,
                azimuth=0.0,
                shot_type=ArianeShotType.VIRTUAL,
            )
            alias.section = parent.section
            nodes[identity] = alias
        return nodes


def _resolve_aliases(rows, ordinary, nodes):
    blocked = {s.id_stop for s in ordinary if s.excluded} - nodes.keys()
    identities = set(nodes)
    aliases = []
    pending = [
        s
        for _, s in rows
        if s.shot_type == ArianeShotType.CLOSURE
        and not s.excluded
        and s.closure_to_id < 0
    ]
    while pending:
        remaining = []
        for shot in pending:
            a, b = closure_endpoints(shot)
            if a < 0 or b < 0 or a in blocked or b in blocked:
                continue
            if (a in identities) == (b in identities):
                remaining.append(shot)
                continue
            parent, alias = (a, b) if a in identities else (b, a)
            identities.add(alias)
            aliases.append((alias, parent))
        if len(remaining) == len(pending):
            break
        pending = remaining
    return identities, aliases


def prepare_graph(survey):
    """Select GPS-connected components without evaluating any measurements."""
    rows = list(records(survey))
    ordinary = [s for _, s in rows if s.shot_type != ArianeShotType.CLOSURE]
    nodes = {s.id_stop: s for s in ordinary if not s.excluded}
    if len(nodes) != sum(not s.excluded for s in ordinary):
        raise ValueError("duplicate station ID in ordinary shot records")
    identities, aliases = _resolve_aliases(rows, ordinary, nodes)
    edges = defaultdict(list)
    legs, closures = set(), set()
    for key, shot in rows:
        if shot.excluded:
            continue
        if shot.shot_type == ArianeShotType.CLOSURE:
            a, b = closure_endpoints(shot)
            if a not in identities or b not in identities:
                continue
            closures.add(key)
        else:
            a, b = shot.id_start, shot.id_stop
            if a not in identities:
                continue
            legs.add(key)
        edges[a].append(b)
        edges[b].append(a)
    reached = {i for i, s in nodes.items() if s.is_geolocation_known()}
    queue = deque(sorted(reached))
    while queue:
        for child in edges[queue.popleft()]:
            if child not in reached:
                reached.add(child)
                queue.append(child)
    for key, shot in rows:
        if shot.excluded:
            continue
        reason = None
        if shot.shot_type == ArianeShotType.CLOSURE:
            a, b = closure_endpoints(shot)
            if key not in closures or a not in reached or b not in reached:
                closures.discard(key)
                reason = "Closure references an unavailable station; dropping closure."
        elif shot.id_stop not in reached:
            legs.discard(key)
            reason = (
                "Is unreachable from any GPS anchor; "
                "dropping station and incident connections."
            )
        elif key not in legs and shot.id_start != -1:
            reason = (
                f"Incoming leg references missing or excluded origin {shot.id_start}; "
                "dropping leg and retaining connected station."
            )
        if reason:
            logger.warning(
                "[Shot %s] %s (section %s)",
                shot.id_stop,
                reason,
                survey.sections[key[0]].name,
            )
    return SurveyGraph(
        frozenset(reached),
        frozenset(identities),
        frozenset(legs),
        frozenset(closures),
        tuple((a, p) for a, p in aliases if a in reached),
    )
