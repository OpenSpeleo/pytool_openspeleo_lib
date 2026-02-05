from __future__ import annotations

import logging
import math
from collections import defaultdict
from collections import deque
from itertools import count
from typing import TYPE_CHECKING

from geojson import Feature
from geojson import FeatureCollection
from geojson import LineString
from geojson import Point
from pyproj import Geod

from openspeleo_lib.constants import OSPL_GEOJSON_DIGIT_PRECISION
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.enums import LengthUnits

if TYPE_CHECKING:
    from openspeleo_lib.models import Section
    from openspeleo_lib.models import Shot
    from openspeleo_lib.models import Survey

logger = logging.getLogger(__name__)

# clrk66 WGS84
GEOD = Geod(ellps="WGS84")
FEET_TO_METERS = float("0.3048")
METERS_TO_FEET = float("1.0") / FEET_TO_METERS


class DisconnectedShotError(Exception):
    """Raised when a shot is disconnected from the graph."""


class NoKnownAnchorError(Exception):
    """Raised when a survey has no known anchor."""


class IterationLimitExceededError(Exception):
    """Raised when the maximum iteration limit is exceeded."""


class IncorrectShotDataError(Exception):
    """Raised when a shot has incorrect or missing data."""

    def __init__(self, shot: Shot, message: str):
        super().__init__(f"[Shot ID={shot.id_stop}]: {message}")
        self.shot = shot
        self.message = message


def length_to_meters(length: float, unit: LengthUnits) -> float:
    """Convert a length to meters based on the provided unit (no rounding)."""
    match unit:
        case LengthUnits.FEET:
            return length * FEET_TO_METERS
        case LengthUnits.METERS:
            return length
        case _:
            raise ValueError(f"Unsupported length unit: {unit}")


def normalize_depth(depth: float | None, unit: LengthUnits) -> float | None:
    if depth is None:
        return None
    match unit:
        case LengthUnits.FEET:
            return round(depth)
        case LengthUnits.METERS:
            return round(depth * METERS_TO_FEET)
        case _:
            raise ValueError(f"Unsupported length unit: {unit}")


def propagate_position(
    base_lat: float, base_lon: float, length_m: float, azimuth_deg: float
) -> tuple[float, float]:
    longitude, latitude, _ = GEOD.fwd(
        base_lon, base_lat, azimuth_deg, length_m, return_back_azimuth=False
    )
    return latitude, longitude


def build_shot_graph(sections: list[Section]) -> dict[int, list[int]]:
    graph: dict[int, list[int]] = defaultdict(list)
    for section in sections:
        for shot in section.shots:
            if shot.shot_type == ArianeShotType.CLOSURE:
                continue

            if shot.id_start != -1:
                graph[shot.id_start].append(shot.id_stop)

    return graph


def build_shots_map(survey: Survey) -> dict[int, Shot]:
    """Build a mapping from station ID to Shot.

    When multiple shots have the same id_stop (common in Compass loop closures),
    prefer the shot that has known geolocation to preserve anchor information.
    """
    shots: dict[int, Shot] = {}
    for shot in survey.shots:
        if shot.shot_type == ArianeShotType.CLOSURE:
            continue

        # If this id_stop already exists, only overwrite if current has no coords
        # and the new shot does (preserve anchors)
        if shot.id_stop in shots:
            existing = shots[shot.id_stop]
            # Keep the one with known geolocation, or the existing one if neither has it
            if not existing.is_geolocation_known() and shot.is_geolocation_known():
                shots[shot.id_stop] = shot
        else:
            shots[shot.id_stop] = shot

    return shots

def find_valid_shot_ids(
    shots_map: dict[int, Shot], graph: dict[int, list[int]]
) -> set[int]:
    """Find all shot IDs reachable from anchor points.

    Shots NOT in the returned set are either:
    - Orphans: shots that cannot trace back to an anchor (directly or recursively)
    - Cycles: shots that are part of isolated cycles not connected to any anchor

    Args:
        shots_map: Mapping of shot id_stop to Shot objects
        graph: Directed graph of shot connections (id_start -> list of id_stop)

    Returns:
        Set of valid shot IDs that are reachable from anchors
    """
    # Find anchor shots (shots with known geolocation)
    anchors = {s.id_stop for s in shots_map.values() if s.is_geolocation_known()}

    if not anchors:
        logger.warning("No anchor shots found - all shots will be considered invalid")
        return set()

    # BFS from all anchor points to find all reachable shots
    visited: set[int] = set()
    queue = deque(anchors)

    while queue:
        current_id = queue.popleft()

        if current_id in visited:
            continue

        visited.add(current_id)

        # Visit all children of the current shot
        for child_id in graph.get(current_id, []):
            if child_id not in visited:
                queue.append(child_id)

    # Identify invalid shots and classify them
    invalid_ids = set(shots_map.keys()) - visited
    if invalid_ids:
        orphans, cycles = _classify_invalid_shots(invalid_ids, shots_map)

        # Log warnings for orphan shots
        for orphan_id in sorted(orphans):
            shot = shots_map.get(orphan_id)
            shot_name = shot.name if shot and shot.name else f"ID={orphan_id}"
            logger.warning(
                "Orphan shot detected: %s (id_stop=%d) - no valid path to anchor",
                shot_name,
                orphan_id,
            )

        # Log warnings for cycle shots
        if cycles:
            cycle_ids_str = ", ".join(str(c) for c in sorted(cycles))
            logger.warning(
                "Cycle detected involving %d shots: [%s] - isolated from anchors",
                len(cycles),
                cycle_ids_str,
            )
            for cycle_id in sorted(cycles):
                shot = shots_map.get(cycle_id)
                shot_name = shot.name if shot and shot.name else f"ID={cycle_id}"
                logger.warning(
                    "  Cycle member: %s (id_stop=%d, id_start=%d)",
                    shot_name,
                    cycle_id,
                    shot.id_start if shot else -1,
                )

    logger.debug(
        "Found %d valid shots out of %d total (removed %d orphan/cycle shots)",
        len(visited),
        len(shots_map),
        len(shots_map) - len(visited),
    )

    return visited



def _classify_invalid_shots(
    invalid_ids: set[int], shots_map: dict[int, Shot]
) -> tuple[set[int], set[int]]:
    """Classify invalid shots as either orphans or cycle members.

    Args:
        invalid_ids: Set of shot IDs that are not reachable from anchors
        shots_map: Mapping of shot id_stop to Shot objects

    Returns:
        Tuple of (orphan_ids, cycle_ids)
    """
    orphans: set[int] = set()
    cycles: set[int] = set()

    for shot_id in invalid_ids:
        if shot_id in orphans or shot_id in cycles:
            continue  # Already classified

        # Trace back through id_start to find the root cause
        path: list[int] = []
        path_set: set[int] = set()
        current_id = shot_id

        while True:
            if current_id in path_set:
                # Found a cycle - mark all nodes in the cycle
                cycle_start_idx = path.index(current_id)
                cycle_nodes = set(path[cycle_start_idx:])
                cycles.update(cycle_nodes)
                # Nodes before the cycle are orphans (they lead to a cycle)
                orphans.update(path[:cycle_start_idx])
                break

            if current_id not in shots_map:
                # Origin doesn't exist - entire path is orphaned
                orphans.update(path)
                break

            shot = shots_map[current_id]
            path.append(current_id)
            path_set.add(current_id)

            if shot.id_start == -1:
                # Reached a root without coordinates - entire path is orphaned
                orphans.update(path)
                break

            current_id = shot.id_start

    return orphans, cycles


def calculate_depth_from_inclination(
    origin_depth: float,
    length: float,
    inclination: float | None,
) -> float:
    """Calculate depth at the end of a shot from inclination.

    Args:
        origin_depth: Depth at the start of the shot.
        length: Shot length.
        inclination: Vertical angle in degrees (positive = up, negative = down).

    Returns:
        Depth at the end of the shot.
    """
    if inclination is None:
        return origin_depth

    vertical = length * math.sin(math.radians(inclination))
    return origin_depth + vertical


def propagate_coordinates(survey: Survey, shots_map: dict[int, Shot]) -> None:
    """Propagate coordinates and depth through the survey graph via BFS.

    Starting from anchor shots (shots with known lat/lon), this function
    traverses the shot graph and calculates:
    1. Depth for each shot (if not already set) from inclination
    2. Lat/lon coordinates from the parent shot's position

    This unified approach ensures consistent depth and coordinate propagation
    across all survey formats (Ariane, Compass, etc.).
    """
    graph = build_shot_graph(survey.sections)

    anchors = [s for s in shots_map.values() if s.is_geolocation_known()]
    logging.info("Found %d anchor shots with known coordinates.", len(anchors))

    if not anchors:
        raise NoKnownAnchorError(
            "This survey has no anchor shots with known coordinates."
        )

    # Ensure anchor shots have a valid depth (default to 0 if not set)
    for anchor in anchors:
        if anchor.depth is None:
            anchor.depth = survey.first_start_absolute_elevation
            anchor.depth_start = survey.first_start_absolute_elevation

    if logger.isEnabledFor(logging.DEBUG):
        for a in anchors:
            logger.debug(
                "[*] Anchor: id_stop=%04d, name=%s, latitude=%.7f, longitude=%.7f, depth=%.2f",
                a.id_stop,
                a.name,
                a.latitude,
                a.longitude,
                a.depth if a.depth is not None else 0.0,
            )

    queue = deque(a.id_stop for a in anchors)
    visited = set()

    max_iterations = 1e6  # ridiculously high for any realistic survey
    iteration_count = count(0)
    while queue:
        if next(iteration_count) > max_iterations:
            raise IterationLimitExceededError(
                "Exceeded maximum iterations while propagating coordinates."
            )

        current_id = queue.popleft()

        if current_id in visited:
            continue

        visited.add(current_id)
        current_shot = shots_map[current_id]

        logger.debug(
            "[*] Processing Shot ID=%04d, name=%s, latitude=%.7f, longitude=%.7f",
            current_id,
            current_shot.name,
            current_shot.latitude,
            current_shot.longitude,
        )

        for child_id in graph.get(current_id, []):
            if child_id in visited or child_id in queue:
                continue

            child_shot = shots_map[child_id]

            if child_shot.length is None:
                raise IncorrectShotDataError(
                    shot=child_shot, message="Missing length for propagation"
                )

            if child_shot.azimuth is None:
                raise IncorrectShotDataError(
                    shot=child_shot, message="Missing azimuth for propagation"
                )

            # Calculate depth during traversal if not already set
            # This handles Compass data where depth is derived from inclination
            if child_shot.depth is None:
                if child_shot.inclination is None:
                    # No inclination data - assume horizontal (depth unchanged)
                    child_shot.depth = current_shot.depth
                else:
                    child_shot.depth = calculate_depth_from_inclination(
                        origin_depth=current_shot.depth,
                        length=child_shot.length,
                        inclination=child_shot.inclination,
                    )
                child_shot.depth_start = current_shot.depth

            length_m = length_to_meters(
                child_shot.length_2d(origin_depth=current_shot.depth),
                unit=survey.unit,
            )

            child_shot.latitude, child_shot.longitude = propagate_position(
                base_lat=current_shot.latitude,
                base_lon=current_shot.longitude,
                length_m=length_m,
                azimuth_deg=child_shot.azimuth_true,
            )

            logger.debug(
                "Propagated ID=%04d: lat=%.7f lon=%.7f depth=%.2f from=%04d",
                child_id,
                child_shot.latitude,
                child_shot.longitude,
                child_shot.depth,
                current_id,
            )

            queue.append(child_id)


def shot_to_geojson_feature(
    shot: Shot, shots_dict: dict[int, Shot], name: str, unit: LengthUnits
) -> dict | None:
    props = {
        "id": shot.id_stop,
        # "name": shot.name,
        "depth": normalize_depth(shot.depth, unit=unit),
        "name": name,
        # "length": shot.length,
        # "azimuth": shot.azimuth,
        # "closure_to_id": shot.closure_to_id,
        # "id_start": shot.id_start,
        # "depth_start": shot.depth_start,
        # "inclination": shot.inclination,
        # "left": shot.left,
        # "right": shot.right,
        # "up": shot.up,
        # "down": shot.down,
    }
    # props = {k: v for k, v in props.items() if v is not None}

    start_coords = None
    if shot.id_start != -1 and shot.id_start in shots_dict:
        from_shot = shots_dict[shot.id_start]
        start_coords = (
            from_shot.coordinates.as_tuple() if from_shot.coordinates else None
        )

    end_coords = shot.coordinates.as_tuple() if shot.coordinates else None

    # Skip feature if missing valid start or end coordinate
    if end_coords is None:
        raise DisconnectedShotError(
            f"Shot ID={shot.id_stop} does not have a valid destination. "
            "Impossible to determine its location."
        )

    if start_coords is None:
        # No origin - it's just a Point.
        return Feature(
            id=str(shot.id) if shot.id else None,
            geometry=Point(end_coords, precision=OSPL_GEOJSON_DIGIT_PRECISION),
            properties=props,
        )

    return Feature(
        id=str(shot.id) if shot.id else None,
        geometry=LineString(
            coordinates=[start_coords, end_coords],
            precision=OSPL_GEOJSON_DIGIT_PRECISION,
        ),
        properties=props,
    )


def survey_to_geojson(survey: Survey) -> dict:
    shots_map: dict[int, Shot] = build_shots_map(survey)
    graph = build_shot_graph(survey.sections)

    # Find valid shots (reachable from anchors, excluding orphans and cycles)
    valid_shot_ids = find_valid_shot_ids(shots_map, graph)

    logger.debug("Starting coordinate propagation ...")
    propagate_coordinates(survey, shots_map)

    # Propagate coordinates from shots_map to ALL shots with the same id_stop
    # This handles loop closures where multiple shots terminate at the same station
    for section in survey.sections:
        for shot in section.shots:
            if shot.id_stop in shots_map:
                source = shots_map[shot.id_stop]
                # Copy propagated coordinates and depth to all shots with same id_stop
                if source is not shot:
                    shot.latitude = source.latitude
                    shot.longitude = source.longitude
                    shot.depth = source.depth
                    shot.depth_start = source.depth_start

    features = [
        shot_to_geojson_feature(shot, shots_map, section.name, survey.unit)
        for section in survey.sections
        for shot in section.shots
        if shot.shot_type in [ArianeShotType.REAL, ArianeShotType.START]
        # if shot.shot_type != ArianeShotType.CLOSURE
        if not shot.excluded
        if shot.id_stop in valid_shot_ids  # Filter out orphans and cycles
    ]

    return FeatureCollection(features=features)
