from __future__ import annotations

import logging
from collections import defaultdict
from collections import deque
from typing import TYPE_CHECKING

from geojson import Feature
from geojson import FeatureCollection
from geojson import LineString
from geojson import Point
from pyproj import Geod

from openspeleo_lib.colors import normalize_shot_color
from openspeleo_lib.constants import OSPL_GEOJSON_DIGIT_PRECISION
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.enums import LengthUnits
from openspeleo_lib.resolved_shot import ResolvedShot
from openspeleo_lib.survey_graph import closure_endpoints
from openspeleo_lib.survey_graph import prepare_graph
from openspeleo_lib.survey_graph import records

if TYPE_CHECKING:
    from collections.abc import Callable

    from openspeleo_lib.loop_closure import LoopClosureSolver
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


def reverse_position(latitude, longitude, length_m, azimuth_deg):
    """Invert the original forward bearing, including meridian convergence."""
    lon, lat, _ = GEOD.fwd(longitude, latitude, azimuth_deg + 180, length_m)
    for _ in range(32):
        end_lon, end_lat, _ = GEOD.fwd(lon, lat, azimuth_deg, length_m)
        correction, _, residual = GEOD.inv(end_lon, end_lat, longitude, latitude)
        if residual < 1e-5:
            return lat, lon
        lon, lat, _ = GEOD.fwd(lon, lat, correction, residual)
    raise ValueError("Reverse shot placement did not converge")


def _propagation_edges(survey, selection):
    forward = defaultdict(list)
    reverse = defaultdict(list)
    equivalences = defaultdict(list)
    for key, shot in records(survey):
        if key in selection.legs:
            forward[shot.id_start].append(shot)
            reverse[shot.id_stop].append(shot)
        if key in selection.closures:
            a, b = closure_endpoints(shot)
            equivalences[a].append(b)
            equivalences[b].append(a)
    return forward, reverse, equivalences


def propagate_coordinates(survey, shots_map, *, selection=None):
    selection = selection or prepare_graph(survey)
    if not any(s.is_geolocation_known() for s in shots_map.values()):
        raise NoKnownAnchorError(
            "This survey has no anchor shots with known coordinates."
        )
    forward, reverse, equivalences = _propagation_edges(survey, selection)
    placed = {i for i, s in shots_map.items() if s.is_geolocation_known()}
    queue = deque(i for i in shots_map if i in placed)

    def place_leg(shot, *, backwards=False):
        parent = shots_map[shot.id_start]
        length = length_to_meters(shot.length_2d(parent.depth), survey.unit)
        bearing = shot.azimuth_true if survey.use_magnetic_azimuth else shot.azimuth
        start = shots_map[shot.id_stop] if backwards else parent
        target = parent if backwards else shots_map[shot.id_stop]
        if backwards:
            target.latitude, target.longitude = reverse_position(
                start.latitude, start.longitude, length, bearing
            )
        else:
            target.latitude, target.longitude = propagate_position(
                start.latitude, start.longitude, length, bearing
            )
        placed.add(target.id_stop)
        queue.append(target.id_stop)

    # Exhaust the original forward traversal before using additional connections.
    while True:
        while queue:
            identity = queue.popleft()
            for shot in forward[identity]:
                if shot.id_stop not in placed:
                    place_leg(shot)
        if len(placed) == len(shots_map):
            break
        progressed = False
        for identity in shots_map:
            if identity not in placed:
                continue
            for other in equivalences[identity]:
                if other not in placed:
                    shots_map[other].latitude = shots_map[identity].latitude
                    shots_map[other].longitude = shots_map[identity].longitude
                    placed.add(other)
                    queue.append(other)
                    progressed = True
            for shot in reverse[identity]:
                if shot.id_start not in placed:
                    place_leg(shot, backwards=True)
                    progressed = True
            if progressed:
                break
        if not progressed:
            raise DisconnectedShotError(
                "Retained graph could not be placed from GPS anchors"
            )


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
            azimuth_deg=(
                shot.azimuth_true if survey.use_magnetic_azimuth else shot.azimuth
            ),
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
    shot: Shot,
    shots_dict: dict[int, Shot],
    name: str,
    unit: LengthUnits,
    *,
    include_origin=True,
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
    # An implicit model default is not a recorded source color.
    if "color" in shot.model_fields_set:
        color = normalize_shot_color(shot.color)
        if color is not None:
            props["color"] = color

    start_coords = None
    if include_origin and shot.id_start != -1 and shot.id_start in shots_dict:
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


def notify_resolved_shots(
    survey: Survey,
    nodes: dict[int, Shot],
    station_ids: set[int] | frozenset[int],
    on_resolved_shot: Callable[[ResolvedShot], None],
) -> None:
    """Report original real shots using the coordinates of their native TO end."""
    for shot in survey.shots:
        if (
            shot.excluded
            or shot.shot_type != ArianeShotType.REAL
            or shot.id_stop not in station_ids
        ):
            continue
        source = shot.source_identity
        endpoint = nodes[
            shot.id_start if source and source.destination_at_start else shot.id_stop
        ]
        coordinates = endpoint.coordinates
        if coordinates is None:
            continue
        on_resolved_shot(
            ResolvedShot(
                uuid=source.uuid if source else str(shot.id) if shot.id else None,
                shot_id=source.shot_id if source else str(shot.id_stop),
                from_id=source.from_id if source else str(shot.id_start),
                namespace=(),
                length_m=source.length_m
                if source
                else length_to_meters(shot.length, survey.unit),
                azimuth=source.azimuth if source else shot.azimuth,
                comment=shot.comment,
                longitude=coordinates.longitude,
                latitude=coordinates.latitude,
            )
        )


def measured_survey_to_geojson(
    survey: Survey,
    *,
    selection=None,
    nodes=None,
    on_resolved_shot: Callable[[ResolvedShot], None] | None = None,
) -> dict:
    """Place and validate only the selected GPS-connected physical graph."""
    selection = selection or prepare_graph(survey)
    shots_map = selection.nodes(survey) if nodes is None else nodes
    explicit = {i for i, s in shots_map.items() if s.is_geolocation_known()}
    propagate_coordinates(survey, shots_map, selection=selection)
    # Retain the safety guard for comparable excluded explicit endpoints without
    # allowing them to provide connectivity, positions, or numerical controls.
    validation_nodes = dict(shots_map)
    for shot in survey.shots:
        if (
            shot.excluded
            and shot.shot_type != ArianeShotType.CLOSURE
            and shot.is_geolocation_known()
        ):
            validation_nodes.setdefault(shot.id_stop, shot)
            explicit.add(shot.id_stop)
    validate_explicit_shot_coordinates(
        survey, validation_nodes, explicit, set(validation_nodes)
    )
    output = FeatureCollection(
        features=[
            shot_to_geojson_feature(
                shot,
                shots_map,
                shot.section.name,
                survey.unit,
                include_origin=key in selection.legs,
            )
            for key, shot in records(survey)
            if not shot.excluded
            and shot.id_stop in selection.stations
            and shot.shot_type in {ArianeShotType.REAL, ArianeShotType.START}
        ]
    )
    if on_resolved_shot is not None:
        notify_resolved_shots(survey, shots_map, selection.stations, on_resolved_shot)
    return output


def survey_to_geojson(
    survey: Survey,
    *,
    loop_closure_solver: LoopClosureSolver | None = None,
    on_resolved_shot: Callable[[ResolvedShot], None] | None = None,
) -> dict:
    """Export measured geometry, optionally applying a configured closure solver."""
    if loop_closure_solver is None:
        return measured_survey_to_geojson(survey, on_resolved_shot=on_resolved_shot)
    return loop_closure_solver.to_geojson(survey, on_resolved_shot=on_resolved_shot)
