from __future__ import annotations

import logging
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
MAX_GEOLOCATION_DISCREPANCY_M = 500.0


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


class InconsistentShotCoordinatesError(IncorrectShotDataError):
    """Raised when explicit coordinates catastrophically disagree with a shot.

    For example, synthetic Shot ID 4242 would be reported when its supplied
    endpoint ``(-70, 40)`` is over 500 m from its calculated endpoint.
    """

    def __init__(
        self,
        shot: Shot,
        supplied_coordinates: tuple[float, float],
        calculated_coordinates: tuple[float, float],
        discrepancy_m: float,
        max_discrepancy_m: float,
    ):
        self.supplied_coordinates = supplied_coordinates
        self.calculated_coordinates = calculated_coordinates
        self.discrepancy_m = discrepancy_m
        self.max_discrepancy_m = max_discrepancy_m

        supplied_latitude, supplied_longitude = supplied_coordinates
        calculated_latitude, calculated_longitude = calculated_coordinates
        super().__init__(
            shot=shot,
            message=(
                "Explicit coordinates are inconsistent with shot measurements: "
                f"supplied=(latitude={supplied_latitude:.7f}, "
                f"longitude={supplied_longitude:.7f}), "
                f"calculated=(latitude={calculated_latitude:.7f}, "
                f"longitude={calculated_longitude:.7f}), "
                f"discrepancy={discrepancy_m:,.3f} m exceeds the "
                f"maximum allowed discrepancy={max_discrepancy_m:.3f} m"
            ),
        )


def length_to_meters(length: float, unit: LengthUnits) -> float:
    """Convert a length to meters based on the provided unit (no rounding)."""
    match unit:
        case LengthUnits.FEET:
            return length * FEET_TO_METERS
        case LengthUnits.METERS:
            return length
        case _:
            raise ValueError(f"Unsupported length unit: {unit}")


def normalize_depth(depth: float, unit: LengthUnits) -> float:
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
    shots = {}
    for shot in survey.shots:
        if shot.shot_type == ArianeShotType.CLOSURE:
            continue
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


def propagate_coordinates(survey: Survey, shots_map: dict[int, Shot]) -> None:
    graph = build_shot_graph(survey.sections)

    anchors = [s for s in shots_map.values() if s.is_geolocation_known()]
    logging.info("Found %d anchor shots with known coordinates.", len(anchors))

    if not anchors:
        raise NoKnownAnchorError(
            "This survey has no anchor shots with known coordinates."
        )

    if logger.isEnabledFor(logging.DEBUG):
        for a in anchors:
            logger.debug(
                "[*] Anchor: id_stop=%04d, name=%s, latitude=%.7f, longitude=%.7f",
                a.id_stop,
                a.name,
                a.latitude,
                a.longitude,
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

            if child_shot.depth is None:
                raise IncorrectShotDataError(
                    shot=child_shot, message="Missing depth for propagation"
                )

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
                "Propagated ID=%04d: lat=%.7f lon=%.7f from=%04d",
                child_id,
                child_shot.latitude,
                child_shot.longitude,
                current_id,
            )

            queue.append(child_id)


def validate_explicit_shot_coordinates(
    survey: Survey,
    shots_map: dict[int, Shot],
    explicit_coordinate_ids: set[int],
    valid_shot_ids: set[int],
) -> None:
    """Reject explicit endpoints that are over 500 m from their measured position.

    Root anchors and connected anchors whose parents cannot be resolved have no
    measured endpoint to compare against and are therefore skipped. For example,
    synthetic Shot ID 4242 with swapped ``(-70, 40)`` coordinates is rejected.
    This is a catastrophic-data guardrail, not a survey-accuracy validation.
    """
    for shot_id in sorted(explicit_coordinate_ids & valid_shot_ids):
        shot = shots_map[shot_id]
        if shot.id_start == -1:
            continue

        origin_shot = shots_map.get(shot.id_start)
        if origin_shot is None or origin_shot.coordinates is None:
            continue

        supplied_coordinates = shot.coordinates
        if supplied_coordinates is None:
            continue

        horizontal_length_m = length_to_meters(
            shot.length_2d(origin_depth=origin_shot.depth),
            unit=survey.unit,
        )
        calculated_coordinates = propagate_position(
            base_lat=origin_shot.latitude,
            base_lon=origin_shot.longitude,
            length_m=horizontal_length_m,
            azimuth_deg=shot.azimuth_true,
        )

        calculated_latitude, calculated_longitude = calculated_coordinates
        _, _, discrepancy_m = GEOD.inv(
            calculated_longitude,
            calculated_latitude,
            supplied_coordinates.longitude,
            supplied_coordinates.latitude,
        )

        if discrepancy_m > MAX_GEOLOCATION_DISCREPANCY_M:
            raise InconsistentShotCoordinatesError(
                shot=shot,
                supplied_coordinates=(
                    supplied_coordinates.latitude,
                    supplied_coordinates.longitude,
                ),
                calculated_coordinates=calculated_coordinates,
                discrepancy_m=discrepancy_m,
                max_discrepancy_m=MAX_GEOLOCATION_DISCREPANCY_M,
            )


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
    """Convert a survey to GeoJSON after validating explicit shot coordinates.

    Raises:
        InconsistentShotCoordinatesError: If a connected shot's explicit endpoint
            is more than 500 metres from the endpoint implied by its measurements.
    """
    shots_map: dict[int, Shot] = build_shots_map(survey)
    graph = build_shot_graph(survey.sections)
    explicit_coordinate_ids = {
        shot.id_stop for shot in shots_map.values() if shot.is_geolocation_known()
    }

    # Find valid shots (reachable from anchors, excluding orphans and cycles)
    valid_shot_ids = find_valid_shot_ids(shots_map, graph)

    logger.debug("Starting coordinate propagation ...")
    propagate_coordinates(survey, shots_map)

    validate_explicit_shot_coordinates(
        survey=survey,
        shots_map=shots_map,
        explicit_coordinate_ids=explicit_coordinate_ids,
        valid_shot_ids=valid_shot_ids,
    )

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
