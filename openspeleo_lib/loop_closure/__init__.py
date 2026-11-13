"""Immutable source snapshots and loop-closure GeoJSON export.

Ariane CLOSURE records equate FromID with ClosureToID when it is populated.
Common-model identity records without a target equate ID with FromID.
Compass normalization lives in compass_lib and follows its separate convention.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from enum import StrEnum

import orjson
from cave_closure import LoopClosureAlgorithm
from cave_closure import LoopClosureMode
from cave_closure import prepare_l1_loop_closure as _prepare_l1_loop_closure
from cave_closure import prepare_loop_closure as _prepare_loop_closure
from cave_closure import solve_l1_loop_closure_json as _solve_l1_loop_closure_json
from cave_closure import solve_loop_closure_json as _solve_loop_closure_json
from geojson import FeatureCollection
from pyproj import CRS
from pyproj import Transformer

from openspeleo_lib import geojson
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.models import Shot
from openspeleo_lib.models import Survey


def _digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class LoopClosureWeighting(StrEnum):
    INDEPENDENT_CARTESIAN = "independent_cartesian"
    INVERSE_LENGTH = "inverse_length"
    LENGTH_AZIMUTH_DIAGONAL = "length_azimuth_diagonal"
    TRAVERSE_QUALITY_INVERSE_SQUARED_LENGTH = "traverse_quality_inverse_squared_length"


class LoopClosureMethod(StrEnum):
    LEAST_SQUARES = "least_squares"
    TRAVERSE_QUALITY_CG = "traverse_quality_cg"
    REFERENCE_CG = "reference_cg"
    INVERSE_LENGTH_WEIGHTED_L1 = "inverse_length_weighted_l1"


class VirtualShotPolicy(StrEnum):
    HARD_OFFSET = "hard_offset"
    MEASURED = "measured"


@dataclass(frozen=True, kw_only=True)
class LoopClosureSolver:
    """Opt-in configuration for loop-closed geographic export.

    Fresh readers supply coordinate provenance automatically. For hand-built
    models, declare fresh inputs or supply an explicit coordinate origin map.
    """

    name: str | None = None
    mode: LoopClosureMode = LoopClosureMode.HORIZONTAL
    algorithm: LoopClosureAlgorithm | None = LoopClosureAlgorithm.LSE_REDUCED_PCG
    sigma_m: float | None = 1.0
    weighting: LoopClosureWeighting = LoopClosureWeighting.INDEPENDENT_CARTESIAN
    inverse_length_weight_cap: float = 10.0
    base_sigma_length_m: float = 0.05
    base_sigma_azimuth_deg: float = 1.0
    average_azimuth_readings: bool = False
    anchor_floating_components: bool = False
    virtual_shot_policy: VirtualShotPolicy = VirtualShotPolicy.HARD_OFFSET
    fix_start_positions: bool = False
    preserve_floating_xy_centroids: bool = False
    skip_missing_origins: bool = False
    source_is_fresh: bool = False
    coordinate_origins: dict[int, str] | None = None
    vertical_controls: dict[int, float] | None = None
    accept_adjusted_measurements: bool = False
    method: LoopClosureMethod = LoopClosureMethod.LEAST_SQUARES
    cg_max_iterations: int = 60_000
    cg_absolute_tolerance: float = 1e-8
    cg_relative_tolerance: float = 1e-5
    fix_control_depths: bool = False
    length_floor_m: float = 0.1
    minimum_anchor_count: int = 2
    deduplicate_edges: bool = True
    max_iterations: int | None = None

    def _prepare(self, source: Survey, *, compute=False) -> LoopClosureSnapshot:
        l1 = self.method == LoopClosureMethod.INVERSE_LENGTH_WEIGHTED_L1
        if not isinstance(self.mode, LoopClosureMode) or (
            not l1 and not isinstance(self.algorithm, LoopClosureAlgorithm)
        ):
            raise TypeError("mode and algorithm must be their enum types")
        if l1 and (self.algorithm is not None or self.sigma_m is not None):
            raise ValueError("L1 requires algorithm=None and sigma_m=None")
        if l1 and (
            self.weighting != LoopClosureWeighting.INVERSE_LENGTH
            or self.virtual_shot_policy != VirtualShotPolicy.MEASURED
        ):
            raise ValueError(
                "L1 requires inverse-length weights and measured VIRTUAL shots"
            )
        if not isinstance(self.weighting, LoopClosureWeighting) or not isinstance(
            self.virtual_shot_policy, VirtualShotPolicy
        ):
            raise TypeError(
                "weighting and virtual_shot_policy must be their enum types"
            )
        if (
            not math.isfinite(self.inverse_length_weight_cap)
            or self.inverse_length_weight_cap <= 0
        ):
            raise ValueError("inverse_length_weight_cap must be positive and finite")
        if (
            not l1
            and self.weighting != LoopClosureWeighting.INDEPENDENT_CARTESIAN
            and self.sigma_m != 1.0
        ):
            raise ValueError("sigma_m only applies to independent Cartesian weighting")
        if self.weighting == LoopClosureWeighting.LENGTH_AZIMUTH_DIAGONAL:
            if self.mode != LoopClosureMode.HORIZONTAL:
                raise ValueError("Length/azimuth diagonal weighting is horizontal-only")
            if any(
                not math.isfinite(value) or value <= 0
                for value in (self.base_sigma_length_m, self.base_sigma_azimuth_deg)
            ):
                raise ValueError(
                    "Instrument standard deviations must be positive and finite"
                )
        if not isinstance(self.method, LoopClosureMethod):
            raise TypeError("method must be a LoopClosureMethod")
        traverse = (
            self.weighting
            == LoopClosureWeighting.TRAVERSE_QUALITY_INVERSE_SQUARED_LENGTH
        )
        if traverse != (self.method == LoopClosureMethod.TRAVERSE_QUALITY_CG):
            raise ValueError(
                "Traverse-quality weights require their native graph method"
            )
        if traverse and self.algorithm != LoopClosureAlgorithm.LSE_UNREDUCED_PCG:
            raise ValueError(
                "The native graph method uses unreduced conjugate gradients"
            )
        if self.method == LoopClosureMethod.REFERENCE_CG and (
            self.weighting != LoopClosureWeighting.INVERSE_LENGTH
            or self.mode != LoopClosureMode.HORIZONTAL
            or self.algorithm != LoopClosureAlgorithm.LSE_UNREDUCED_PCG
        ):
            raise ValueError(
                "Reference CG requires inverse-length unreduced horizontal solving"
            )
        if (
            isinstance(self.cg_max_iterations, bool)
            or not isinstance(self.cg_max_iterations, int)
            or self.cg_max_iterations <= 0
            or not math.isfinite(self.cg_absolute_tolerance)
            or self.cg_absolute_tolerance <= 0
        ):
            raise ValueError(
                "CG iteration limit and tolerances must be positive and finite"
            )
        if (
            not math.isfinite(self.cg_relative_tolerance)
            or self.cg_relative_tolerance < 0
        ):
            raise ValueError("CG relative tolerance must be nonnegative and finite")
        return _build_loop_closure_snapshot(
            source,
            mode=self.mode,
            algorithm=self.algorithm,
            sigma_m=self.sigma_m,
            source_is_fresh=self.source_is_fresh,
            coordinate_origins=self.coordinate_origins,
            vertical_controls=self.vertical_controls,
            accept_adjusted_measurements=self.accept_adjusted_measurements,
            weighting=self.weighting,
            base_sigma_length_m=self.base_sigma_length_m,
            base_sigma_azimuth_deg=self.base_sigma_azimuth_deg,
            average_azimuth_readings=self.average_azimuth_readings,
            anchor_floating_components=self.anchor_floating_components,
            inverse_length_weight_cap=self.inverse_length_weight_cap,
            virtual_shot_policy=self.virtual_shot_policy,
            fix_start_positions=self.fix_start_positions,
            preserve_floating_xy_centroids=self.preserve_floating_xy_centroids,
            skip_missing_origins=self.skip_missing_origins,
            compute=compute,
            method=self.method,
            cg_max_iterations=self.cg_max_iterations,
            cg_absolute_tolerance=self.cg_absolute_tolerance,
            cg_relative_tolerance=self.cg_relative_tolerance,
            fix_control_depths=self.fix_control_depths,
            l1_options={
                "mode": self.mode,
                "length_floor_m": self.length_floor_m,
                "minimum_anchor_count": self.minimum_anchor_count,
                "deduplicate_edges": self.deduplicate_edges,
                "max_iterations": self.max_iterations,
            }
            if l1
            else None,
        )

    def prepare(self, source: Survey) -> LoopClosureSnapshot:
        return self._prepare(source)

    def to_geojson(self, source: Survey):
        snapshot = self._prepare(source, compute=True)
        result = LoopClosureResult(snapshot.fingerprint, snapshot.prepared)
        return loop_closed_survey_to_geojson(snapshot, result, source=source)


@dataclass(frozen=True)
class _ExportReport:
    """Owned result data returned with the single native export computation."""

    coordinates: tuple
    observations: tuple
    status: str
    encoded: str

    @classmethod
    def from_json(cls, encoded):
        data = orjson.loads(encoded)
        return cls(
            tuple((p["station"], tuple(p["value"])) for p in data["coordinates"]),
            tuple((p["id"], tuple(p["residual"])) for p in data["observations"]),
            data["status"],
            encoded,
        )

    def require_converged(self):
        if self.status != "converged":
            raise ValueError(f"Incomplete native adjustment: {self.status}")
        return self

    def to_json(self):
        return self.encoded


def _l1_report(encoded, aliases, station_ids):
    """Restore native-resolved station aliases by identity, without arithmetic."""
    data = orjson.loads(encoded)
    coordinates = {row["station"]: row["value"] for row in data["coordinates"]}
    roots = dict(aliases)
    data["coordinates"] = [
        {"station": station, "value": coordinates[roots.get(station, station)]}
        for station in station_ids
    ]
    return _ExportReport.from_json(orjson.dumps(data).decode())


@dataclass(frozen=True)
class _L1Preparation:
    """Own an immutable native LP and the native-resolved identity mapping."""

    prepared: object
    aliases: tuple
    station_ids: tuple

    def solve(self, **kwargs):
        report = self.prepared.solve(**kwargs)
        report.require_converged()
        return _l1_report(report.to_json(), self.aliases, self.station_ids)

    def normalized_json(self):
        return self.prepared.normalized_json()


@dataclass(frozen=True)
class LoopClosureResult:
    fingerprint: str
    report: object

    def require_converged(self):
        self.report.require_converged()
        return self


@dataclass(frozen=True)
class LoopClosureSnapshot:
    """Own serialized pre-propagation evidence and immutable numerical preparation."""

    source_json: str
    source_fingerprint: str
    fingerprint: str
    explicit_coordinate_ids: frozenset[int]
    coordinate_origins: tuple[tuple[int, str], ...]
    origin: tuple[float, float]
    prepared: object
    mode: LoopClosureMode
    algorithm: LoopClosureAlgorithm | None

    def solve(self, **kwargs):
        report = self.prepared.solve(**kwargs)
        report.require_converged()
        return LoopClosureResult(self.fingerprint, report)

    def validate_source(self, source):
        if _digest(source.model_dump_json()) != self.source_fingerprint:
            raise ValueError("source no longer matches its loop-closure snapshot")


def geographic_projection(origin):
    latitude, longitude = origin
    local = CRS.from_proj4(
        f"+proj=aeqd +lat_0={latitude} +lon_0={longitude} +datum=WGS84 +units=m"
    )
    return Transformer.from_crs(
        "EPSG:4326", local, always_xy=True
    ), Transformer.from_crs(local, "EPSG:4326", always_xy=True)


def _add_closure_alias_stations(survey):
    """Materialize identity-only station IDs on disposable solver views.

    Identity records without ClosureToID can introduce a station solely through
    ID == FromID. Targeted Ariane closure IDs identify records, not stations.
    Ordinary measured export retains its existing filtering.
    """
    nodes = geojson.build_shots_map(survey)
    pending = [
        s
        for s in survey.shots
        if s.shot_type == ArianeShotType.CLOSURE and s.closure_to_id < 0
    ]
    added = {}
    while pending:
        remaining = []
        for closure in pending:
            left, right = closure.id_start, closure.id_stop
            if (left in nodes) == (right in nodes):
                remaining.append(closure)
                continue
            parent_id, alias_id = (left, right) if left in nodes else (right, left)
            parent = nodes[parent_id]
            if parent.excluded:
                continue
            alias = Shot(
                id_start=parent_id,
                id_stop=alias_id,
                length=0.0,
                depth=parent.depth,
                azimuth=0.0,
                shot_type=ArianeShotType.VIRTUAL,
            )
            alias.section = parent.section
            parent.section.shots.append(alias)
            nodes[alias_id] = added[alias_id] = alias
        if len(remaining) == len(pending):
            break
        pending = remaining
    return added


def prepare_loop_closure(
    source: Survey,
    *,
    mode: LoopClosureMode,
    sigma_m,
    source_is_fresh=False,
    coordinate_origins=None,
    locked_policy="metadata",
    vertical_controls=None,
    accept_adjusted_measurements=False,
    algorithm: LoopClosureAlgorithm = LoopClosureAlgorithm.LSE_REDUCED_PCG,
):
    """Prepare the caller-declared independent Cartesian uncertainty model."""
    return _build_loop_closure_snapshot(
        source,
        mode=mode,
        sigma_m=sigma_m,
        source_is_fresh=source_is_fresh,
        coordinate_origins=coordinate_origins,
        locked_policy=locked_policy,
        vertical_controls=vertical_controls,
        accept_adjusted_measurements=accept_adjusted_measurements,
        algorithm=algorithm,
    )


def _prepare_numerical_problem(
    baseline,
    nodes,
    index,
    *,
    forward,
    mode,
    algorithm,
    sigma_m,
    vertical_controls,
    relationships,
    observations,
    explicit,
    fixed_xy,
    weighting,
    base_sigma_length_m,
    base_sigma_azimuth_deg,
    inverse_length_weight_cap,
    preserve_floating_xy_centroids,
    cg_options,
    method,
    fix_control_depths,
    average_azimuth_readings,
    anchor_floating_components,
    compute,
    l1_options,
):
    """Map common-model data into one owned native request; perform no numerics."""
    ids = list(nodes) if method == LoopClosureMethod.REFERENCE_CG else sorted(nodes)
    controls = [
        (
            f"{'explicit' if station in explicit else 'start-view'}:{station}",
            index[station],
            [0, 1],
            list(forward.transform(nodes[station].longitude, nodes[station].latitude)),
        )
        for station in sorted(fixed_xy)
    ]
    controls.extend(
        (f"vertical:{station}", index[station], [2], [z])
        for station, z in sorted((vertical_controls or {}).items())
    )
    request = {
        "station_ids": [str(i) for i in ids],
        "measurements": observations,
        "relationships": relationships,
        "initial_positions": [
            (
                *forward.transform(nodes[i].longitude, nodes[i].latitude),
                -geojson.length_to_meters(nodes[i].depth, baseline.unit),
            )
            for i in ids
        ],
        "controls": controls,
        "source_order": [index[i] for i in nodes],
        "options": {
            "mode": mode,
            "algorithm": algorithm.name if algorithm is not None else None,
            "weighting": weighting,
            "method": method,
            "sigma_m": sigma_m,
            "weight_cap": inverse_length_weight_cap,
            "sigma_length_m": base_sigma_length_m,
            "sigma_azimuth_deg": base_sigma_azimuth_deg,
            "average_azimuths": average_azimuth_readings,
            "anchor_floating": anchor_floating_components,
            "preserve_centroids": preserve_floating_xy_centroids,
            "fix_control_depths": fix_control_depths,
            **cg_options,
        },
    }
    if l1_options is not None:
        return _prepare_l1_problem(request, l1_options, compute=compute), [
            "OpenSpeleo measurement vectors and exact identities prepared in Rust",
            "Inverse-length weighted L1 solved through existing cave-closure APIs",
        ]
    action = _solve_loop_closure_json if compute else _prepare_loop_closure
    output = action(request)
    return (_ExportReport.from_json(output) if compute else output), [
        "Common OpenSpeleo measurements normalized to metres and true bearing",
        "All weighting, preparation and adjustment computed by cave-closure",
    ]


def _prepare_l1_problem(source_request, options, *, compute):
    """Use the published native measurement normalizer, then its native L1 API.

    Graph preparation resolves measured vectors, identities and controls without
    running CG. The released L1 entry point accepts those Cartesian graph rows.
    """
    source_request["options"].update(
        algorithm=LoopClosureAlgorithm.LSE_UNREDUCED_PCG.name,
        sigma_m=1.0,
        weighting=LoopClosureWeighting.TRAVERSE_QUALITY_INVERSE_SQUARED_LENGTH,
        method=LoopClosureMethod.TRAVERSE_QUALITY_CG,
    )
    normal = orjson.loads(_prepare_loop_closure(source_request).normalized_json()[0])
    aliases = tuple((row["from"], row["to"]) for row in normal["relationships"])
    alias_ids = {station for station, _ in aliases}
    names = [row["id"] for row in normal["stations"] if row["id"] not in alias_ids]
    index = {name: i for i, name in enumerate(names)}
    initial = dict(
        zip(
            source_request["station_ids"],
            source_request["initial_positions"],
            strict=True,
        )
    )
    for control in normal["controls"]:
        station, value = control["station"], control["value"]
        initial[station] = (*value, *initial[station][len(value) :])
    request = {
        "station_ids": names,
        "observations": [
            (row["id"], index[row["from"]], index[row["to"]], row["value"])
            for row in normal["observations"]
        ],
        "initial_positions": [initial[name] for name in names],
        "anchor_indices": [index[row["station"]] for row in normal["controls"]],
        "options": options,
    }
    station_ids = tuple(source_request["station_ids"])
    if compute:
        return _l1_report(_solve_l1_loop_closure_json(request), aliases, station_ids)
    return _L1Preparation(_prepare_l1_loop_closure(request), aliases, station_ids)


def _build_loop_closure_snapshot(
    source: Survey,
    *,
    mode: LoopClosureMode,
    sigma_m,
    source_is_fresh=False,
    coordinate_origins=None,
    locked_policy="metadata",
    vertical_controls=None,
    accept_adjusted_measurements=False,
    algorithm: LoopClosureAlgorithm = LoopClosureAlgorithm.LSE_REDUCED_PCG,
    weighting=LoopClosureWeighting.INDEPENDENT_CARTESIAN,
    base_sigma_length_m=0.05,
    base_sigma_azimuth_deg=1.0,
    average_azimuth_readings=False,
    anchor_floating_components=False,
    inverse_length_weight_cap=10.0,
    virtual_shot_policy=VirtualShotPolicy.HARD_OFFSET,
    fix_start_positions=False,
    preserve_floating_xy_centroids=False,
    skip_missing_origins=False,
    compute=False,
    method=LoopClosureMethod.LEAST_SQUARES,
    cg_max_iterations=60_000,
    cg_absolute_tolerance=1e-8,
    cg_relative_tolerance=1e-5,
    fix_control_depths=False,
    l1_options=None,
):
    """Capture inputs before propagation, or require an explicit origin map.

    Explicit XY coordinates become hard controls. Spatial callers must supply
    independent ENU vertical controls; recorded depths are not silently reused as
    hard controls. The Gaussian uncertainty model is caller-declared independent
    Cartesian placement noise. Raw instrument correlations are not inferred.
    """
    mode = LoopClosureMode(mode)
    if source.measurements_are_adjusted and not accept_adjusted_measurements:
        raise ValueError("stored measurements may already have been adjusted")
    if locked_policy != "metadata":
        raise ValueError(
            "locked is editing metadata; "
            "alternative numerical interpretation is unsupported"
        )
    if coordinate_origins is None:
        coordinate_origins = getattr(source, "_coordinate_origin_map", None)
    if not source_is_fresh and coordinate_origins is None:
        raise ValueError(
            "coordinate history is unknown; "
            "supply a fresh parse or explicit coordinate_origins"
        )
    if l1_options is None and (
        sigma_m is None or not math.isfinite(sigma_m) or sigma_m <= 0
    ):
        raise ValueError("sigma_m must be positive and finite")
    source_json = source.model_dump_json()
    # All ordinary safety validation and propagation operate on this disposable
    # model; evidence captured above stays unchanged even if validation fails.
    baseline = Survey.model_validate_json(source_json)
    nodes = {
        shot.id_stop: shot
        for shot in baseline.shots
        if shot.shot_type != ArianeShotType.CLOSURE and not shot.excluded
    }
    if len(nodes) != sum(
        shot.shot_type != ArianeShotType.CLOSURE and not shot.excluded
        for shot in baseline.shots
    ):
        raise ValueError("duplicate station ID in ordinary shot records")
    populated = {i for i, shot in nodes.items() if shot.is_geolocation_known()}
    if coordinate_origins is None:
        origins = {i: "explicit" if i in populated else "unpopulated" for i in nodes}
    else:
        origins = dict(coordinate_origins)
        if set(origins) != set(nodes) or any(
            v not in {"explicit", "derived", "unpopulated"} for v in origins.values()
        ):
            raise ValueError("coordinate_origins must classify every station")
        if any(
            (kind == "explicit") != (i in populated)
            for i, kind in origins.items()
            if kind != "derived"
        ):
            raise ValueError("coordinate_origins disagrees with supplied coordinates")
    explicit = frozenset(i for i, kind in origins.items() if kind == "explicit")
    if not explicit:
        raise ValueError(
            "adjusted geographic export needs an explicit geographic control"
        )
    # Drop known-derived coordinates before validating measured geometry. They
    # must not become controls just because an earlier conversion populated them.
    for i, shot in nodes.items():
        if i not in explicit:
            shot.latitude = shot.longitude = None
    aliases = _add_closure_alias_stations(baseline)
    for identity, alias in aliases.items():
        nodes[identity] = alias
        origins[identity] = "derived"
    geojson.measured_survey_to_geojson(
        baseline
    )  # Preserves the existing 500 m guard on raw geometry.
    valid = geojson.find_valid_shot_ids(
        nodes, geojson.build_shot_graph(baseline.sections)
    )
    nodes = {key: value for key, value in nodes.items() if key in valid}
    origins = {key: value for key, value in origins.items() if key in valid}
    first = nodes[min(explicit)]
    origin = (first.latitude, first.longitude)
    forward, _ = geographic_projection(origin)
    ids = list(nodes) if method == LoopClosureMethod.REFERENCE_CG else sorted(nodes)
    index = {station: i for i, station in enumerate(ids)}
    relationships, observations = _prepare_rows(
        baseline,
        nodes,
        index,
        virtual_shot_policy=virtual_shot_policy,
        skip_missing_origins=skip_missing_origins,
        alias_ids=frozenset(aliases),
    )
    fixed_xy = explicit | (
        {i for i, shot in nodes.items() if shot.shot_type == ArianeShotType.START}
        if fix_start_positions
        else set()
    )
    prepared, provenance = _prepare_numerical_problem(
        baseline,
        nodes,
        index,
        forward=forward,
        mode=mode,
        algorithm=algorithm,
        sigma_m=sigma_m,
        vertical_controls=vertical_controls,
        relationships=relationships,
        observations=observations,
        explicit=explicit,
        fixed_xy=fixed_xy,
        weighting=weighting,
        base_sigma_length_m=base_sigma_length_m,
        base_sigma_azimuth_deg=base_sigma_azimuth_deg,
        inverse_length_weight_cap=inverse_length_weight_cap,
        preserve_floating_xy_centroids=preserve_floating_xy_centroids,
        fix_control_depths=fix_control_depths,
        method=method,
        average_azimuth_readings=average_azimuth_readings,
        anchor_floating_components=anchor_floating_components,
        compute=compute,
        l1_options=l1_options,
        cg_options={
            "max_iterations": cg_max_iterations,
            "absolute_tolerance": cg_absolute_tolerance,
            "relative_tolerance": cg_relative_tolerance,
        },
    )
    fingerprint = _digest(
        json.dumps(
            [
                source_json,
                mode,
                algorithm.name if algorithm is not None else None,
                sigma_m,
                sorted(origins.items()),
                locked_policy,
                sorted((vertical_controls or {}).items()),
                origin,
                provenance,
                virtual_shot_policy,
                fix_start_positions,
                skip_missing_origins,
                preserve_floating_xy_centroids,
                base_sigma_length_m,
                base_sigma_azimuth_deg,
                average_azimuth_readings,
                anchor_floating_components,
                weighting,
                inverse_length_weight_cap,
                method,
                cg_max_iterations,
                cg_absolute_tolerance,
                cg_relative_tolerance,
                fix_control_depths,
                *([l1_options] if l1_options is not None else []),
            ],
            sort_keys=True,
            allow_nan=False,
        )
    )
    return LoopClosureSnapshot(
        source_json,
        _digest(source_json),
        fingerprint,
        explicit,
        tuple(sorted(origins.items())),
        origin,
        prepared,
        mode,
        algorithm,
    )


def loop_closed_survey_to_geojson(
    snapshot: LoopClosureSnapshot,
    result: LoopClosureResult,
    *,
    source=None,
):
    """Export a converged matching result; never alter source or ordinary conversion."""
    if result.fingerprint != snapshot.fingerprint:
        raise ValueError("loop-closure result belongs to a different preparation")
    result.require_converged()
    if source is not None:
        snapshot.validate_source(source)
    origin = snapshot.origin
    view = Survey.model_validate_json(snapshot.source_json)
    _add_closure_alias_stations(view)
    nodes = geojson.build_shots_map(view)
    _, inverse = geographic_projection(origin)
    solved_ids = {int(identity) for identity, _ in result.report.coordinates}
    for identity, value in result.report.coordinates:
        node = nodes[int(identity)]
        node.longitude, node.latitude = inverse.transform(value[0], value[1])
        if snapshot.mode == LoopClosureMode.SPATIAL:
            node.depth = -value[2] / geojson.length_to_meters(1.0, view.unit)
    return FeatureCollection(
        features=[
            geojson.shot_to_geojson_feature(shot, nodes, section.name, view.unit)
            for section in view.sections
            for shot in section.shots
            if not shot.excluded
            and shot.id_stop in solved_ids
            and shot.shot_type in {ArianeShotType.REAL, ArianeShotType.START}
        ]
    )


def _prepare_rows(
    baseline,
    nodes,
    index,
    *,
    virtual_shot_policy=VirtualShotPolicy.HARD_OFFSET,
    skip_missing_origins=False,
    alias_ids=frozenset(),
):
    relationships, observations = [], []
    for section_index, section in enumerate(baseline.sections):
        for shot_index, shot in enumerate(section.shots):
            identity = f"section:{section_index}/shot:{shot_index}"
            if shot.shot_type == ArianeShotType.CLOSURE:
                left = shot.id_start
                right = shot.closure_to_id if shot.closure_to_id >= 0 else shot.id_stop
                if left not in nodes and right not in nodes:
                    continue
                if left not in nodes or right not in nodes:
                    raise ValueError(
                        f"{identity}: CLOSURE refers to an unknown station"
                    )
                # ClosureToID is the station target; ID is the record identity.
                # Target-less common-model records use ID == FromID instead.
                relationships.append(
                    (
                        identity,
                        "equivalent",
                        index[left],
                        index[right],
                        (0.0, 0.0, 0.0),
                    )
                )
                continue
            if shot.excluded or shot.id_stop not in nodes:
                continue
            if shot.shot_type == ArianeShotType.START or (
                virtual_shot_policy == VirtualShotPolicy.MEASURED
                and shot.id_stop in alias_ids
            ):
                continue
            if shot.id_start not in nodes:
                if skip_missing_origins:
                    continue
                raise ValueError(f"{identity}: missing origin station")
            parent = nodes[shot.id_start]
            depth_start = (
                shot.depth_start
                if shot.depth_start_is_authoritative and shot.depth_start is not None
                else parent.depth
            )
            vertical = geojson.length_to_meters(depth_start - shot.depth, baseline.unit)
            length = geojson.length_to_meters(shot.length, baseline.unit)
            bearing = (
                shot.azimuth_true if baseline.use_magnetic_azimuth else shot.azimuth
            )
            secondary = shot.azimuth_secondary
            if secondary is not None and baseline.use_magnetic_azimuth:
                secondary += bearing - shot.azimuth
            observations.append(
                (
                    identity,
                    index[shot.id_start],
                    index[shot.id_stop],
                    length,
                    bearing,
                    vertical,
                    secondary,
                    shot.section.quality if shot.section.quality is not None else 1.0,
                    shot.shot_type == ArianeShotType.VIRTUAL
                    and virtual_shot_policy == VirtualShotPolicy.HARD_OFFSET,
                )
            )
    return relationships, observations
