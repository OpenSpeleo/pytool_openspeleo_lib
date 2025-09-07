from __future__ import annotations

import logging
from collections import defaultdict
from collections import deque
from itertools import count
from typing import TYPE_CHECKING

from pyproj import Geod

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
        super().__init__(f"[Shot ID={shot.shot_id}]: {message}")
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

            if shot.from_id != -1:
                graph[shot.from_id].append(shot.shot_id)

    return graph


def build_shots_map(survey: Survey) -> dict[int, Shot]:
    shots = {}
    for shot in survey.shots:
        if shot.shot_type == ArianeShotType.CLOSURE:
            continue
        shots[shot.shot_id] = shot

    return shots


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
                "[*] Anchor: shot_id=%04d, name=%s, latitude=%.7f, longitude=%.7f",
                a.shot_id,
                a.shot_name,
                a.latitude,
                a.longitude,
            )

    queue = deque(a.shot_id for a in anchors)
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
            current_shot.shot_name,
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


def shot_to_geojson_feature(
    shot: Shot, shots_dict: dict[int, Shot], section_name: str, unit: LengthUnits
) -> dict | None:
    props = {
        "id": shot.shot_id,
        # "shot_name": shot.shot_name,
        "depth": normalize_depth(shot.depth, unit=unit),
        "section_name": section_name,
        # "length": shot.length,
        # "azimuth": shot.azimuth,
        # "closure_to_id": shot.closure_to_id,
        # "from_id": shot.from_id,
        # "depth_in": shot.depth_in,
        # "inclination": shot.inclination,
        # "left": shot.left,
        # "right": shot.right,
        # "up": shot.up,
        # "down": shot.down,
    }
    # props = {k: v for k, v in props.items() if v is not None}

    start_coords = None
    if shot.from_id != -1 and shot.from_id in shots_dict:
        from_shot = shots_dict[shot.from_id]
        start_coords = (
            from_shot.coordinates.as_tuple() if from_shot.coordinates else None
        )

    end_coords = shot.coordinates.as_tuple() if shot.coordinates else None

    # Skip feature if missing valid start or end coordinate
    if end_coords is None:
        raise DisconnectedShotError(
            f"Shot ID={shot.shot_id} does not have a valid destination. "
            "Impossible to determine its location."
        )

    if start_coords is None:
        # No origin - it's just a Point.
        return {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": end_coords},
            "properties": props,
        }

    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [start_coords, end_coords]},
        "properties": props,
    }


def survey_to_geojson(survey: Survey) -> dict:
    shots_map: dict[int, Shot] = build_shots_map(survey)

    logger.debug("Starting coordinate propagation ...")
    propagate_coordinates(survey, shots_map)

    features = [
        shot_to_geojson_feature(shot, shots_map, section.section_name, survey.unit)
        for section in survey.sections
        for shot in section.shots
        if shot.shot_type in [ArianeShotType.REAL, ArianeShotType.START]
        # if shot.shot_type != ArianeShotType.CLOSURE
        if not shot.excluded
    ]

    return {
        "type": "FeatureCollection",
        "features": features,
    }
