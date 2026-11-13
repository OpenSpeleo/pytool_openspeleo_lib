"""Premade, immutable configurations of the single LoopClosureSolver type.

LeastSquaresHorizontalSolver uses OpenSpeleo's independent Cartesian placement
model in XY and preserves depths. LeastSquaresSpatialSolver uses the same model
in XYZ and requires independent vertical controls. Both come from the Gaussian
preparation and least-squares backends in cave-closure.

InverseLengthWeightedLeastSquaresHorizontalSolver is analogous to the solver
inside Ariane's Line. It follows the Java graph construction and Rust weighted
normal equations in cave-closure/docs/loop_closure: fixed START XY, measured
REAL/VIRTUAL legs, capped inverse-length weights, and station substitutions.
It preserves depths and is used by the private GeoJSON identity regressions,
their encrypted-golden generator, and the numerical weighted-loop tests.

LengthAzimuthWeightedLeastSquaresHorizontalSolver matches Stalagmight's
horizontal per-axis instrument propagation with section quality and averaged
forward bearings. It is available to common-model API callers; its numerical
preparation and independent-axis solves live in cave-closure, without readers.

Three additional presets port Compass's implementations: the horizontal
reference CG loop, the full-XYZ traverse-quality CG solver, and the inverse-length
weighted L1 solver. All numerical work stays in cave-closure, without readers.

The public golden generator and tests exercise every registered preset.
The CLI currently constructs custom LoopClosureSolver configurations directly.
See docs/loop-closure-presets.md for settings, origins, current call sites, and
examples. Names label instances, not
Python types. Customize with dataclasses.replace; shared presets stay unchanged.
"""

from types import MappingProxyType

from cave_closure import LoopClosureAlgorithm
from cave_closure import LoopClosureMode

from openspeleo_lib.loop_closure import LoopClosureMethod
from openspeleo_lib.loop_closure import LoopClosureSolver
from openspeleo_lib.loop_closure import LoopClosureWeighting
from openspeleo_lib.loop_closure import VirtualShotPolicy

# Origin/software: OpenSpeleo's independent Cartesian Gaussian model, prepared
# and solved in cave-closure/src_rust/loop_closure.rs; no software analogue
# is claimed. Use for horizontal adjustment while retaining recorded depths.
# Used by tests/export_goldens.py and tests/test_export_goldens.py for every
# public fixture, and by tests/test_loop_closure_presets.py. The OpenSpeleo CLI
# constructs equivalent configurations directly.
LeastSquaresHorizontalSolver = LoopClosureSolver(
    name="LeastSquaresHorizontalSolver",
    mode=LoopClosureMode.HORIZONTAL,
    algorithm=LoopClosureAlgorithm.LSE_REDUCED_PCG,
    sigma_m=1.0,
    weighting=LoopClosureWeighting.INDEPENDENT_CARTESIAN,
    inverse_length_weight_cap=10.0,
    base_sigma_length_m=0.05,
    base_sigma_azimuth_deg=1.0,
    average_azimuth_readings=False,
    anchor_floating_components=False,
    virtual_shot_policy=VirtualShotPolicy.HARD_OFFSET,
    fix_start_positions=False,
    preserve_floating_xy_centroids=False,
    skip_missing_origins=False,
    source_is_fresh=False,
    coordinate_origins=None,
    vertical_controls=None,
    accept_adjusted_measurements=False,
    method=LoopClosureMethod.LEAST_SQUARES,
    cg_max_iterations=60_000,
    cg_absolute_tolerance=1e-8,
    cg_relative_tolerance=1e-5,
    fix_control_depths=False,
    length_floor_m=0.1,
    minimum_anchor_count=2,
    deduplicate_edges=True,
    max_iterations=None,
)

# Origin/software: the spatial form of OpenSpeleo's Cartesian Gaussian model,
# using the same cave-closure backend; no external software analogue is claimed.
# Use for XYZ adjustment with independently supplied vertical controls; measured
# depths are not automatically hard controls. This API preset is exercised by
# tests/test_loop_closure_presets.py and used directly for public named-preset
# goldens in tests/export_goldens.py and tests/test_export_goldens.py.
LeastSquaresSpatialSolver = LoopClosureSolver(
    name="LeastSquaresSpatialSolver",
    mode=LoopClosureMode.SPATIAL,
    algorithm=LoopClosureAlgorithm.LSE_REDUCED_PCG,
    sigma_m=1.0,
    weighting=LoopClosureWeighting.INDEPENDENT_CARTESIAN,
    inverse_length_weight_cap=10.0,
    base_sigma_length_m=0.05,
    base_sigma_azimuth_deg=1.0,
    average_azimuth_readings=False,
    anchor_floating_components=False,
    virtual_shot_policy=VirtualShotPolicy.HARD_OFFSET,
    fix_start_positions=False,
    preserve_floating_xy_centroids=False,
    skip_missing_origins=False,
    source_is_fresh=False,
    coordinate_origins=None,
    vertical_controls=None,
    accept_adjusted_measurements=False,
    method=LoopClosureMethod.LEAST_SQUARES,
    cg_max_iterations=60_000,
    cg_absolute_tolerance=1e-8,
    cg_relative_tolerance=1e-5,
    fix_control_depths=False,
    length_floor_m=0.1,
    minimum_anchor_count=2,
    deduplicate_edges=True,
    max_iterations=None,
)

# Origin/software: analogous to the solver inside Ariane's Line, based on the
# Java graph construction and Rust weighted normal equations documented in
# cave-closure/docs/loop_closure/{ariane_solver.java,graph_solver.rs}.
# Identical reference sources also live in compass_lib/loop_closure; this is
# the same graph formulation. The separate ConjugateGradient preset below
# also reproduces the historical numerical stopping rules.
# Use for inverse-length weighted XY adjustment: fixed START positions,
# measured REAL/VIRTUAL legs, exact station substitutions, and unchanged depths.
# Used by tests/test_geojson_convert.py, the encrypted-golden generator
# tests/export_private_horizontal_goldens.py, and the independent numerical
# checks in tests/test_inverse_length_horizontal_solver.py. All computation
# runs on common OpenSpeleo models through cave-closure, for either reader.
# Also used by the public named-preset golden generator and comparisons.
InverseLengthWeightedLeastSquaresHorizontalSolver = LoopClosureSolver(
    name="InverseLengthWeightedLeastSquaresHorizontalSolver",
    mode=LoopClosureMode.HORIZONTAL,
    algorithm=LoopClosureAlgorithm.LSE_REDUCED_PCG,
    sigma_m=1.0,
    weighting=LoopClosureWeighting.INVERSE_LENGTH,
    inverse_length_weight_cap=10.0,
    base_sigma_length_m=0.05,
    base_sigma_azimuth_deg=1.0,
    average_azimuth_readings=False,
    anchor_floating_components=False,
    virtual_shot_policy=VirtualShotPolicy.MEASURED,
    fix_start_positions=True,
    preserve_floating_xy_centroids=True,
    skip_missing_origins=True,
    source_is_fresh=False,
    coordinate_origins=None,
    vertical_controls=None,
    accept_adjusted_measurements=False,
    method=LoopClosureMethod.LEAST_SQUARES,
    cg_max_iterations=60_000,
    cg_absolute_tolerance=1e-8,
    cg_relative_tolerance=1e-5,
    fix_control_depths=False,
    length_floor_m=0.1,
    minimum_anchor_count=2,
    deduplicate_edges=True,
    max_iterations=None,
)

# Origin/software: Stalagmight's Closures Computed View (LeastSquaresWeighted).
# Source: src-tauri/crates/models/src/project/lsq.rs and
# config/mod.rs. Independent X/Y variances use slope length, circular-mean true
# azimuth, section quality, 0.05 m length sigma and 1 degree azimuth sigma.
# Use for non-destructive horizontal instrument-weighted adjustment; depths stay
# recorded. REAL/VIRTUAL legs are measured; merges/closures substitute stations.
# Degree-two reduction and Jacobi-PCG solve each axis independently. Zero-weight
# axes retain their measured translation, rather than inventing observations.
# Used by tests/export_goldens.py and tests/test_export_goldens.py for every
# public fixture; available to common-model API callers for either reader.
LengthAzimuthWeightedLeastSquaresHorizontalSolver = LoopClosureSolver(
    name="LengthAzimuthWeightedLeastSquaresHorizontalSolver",
    mode=LoopClosureMode.HORIZONTAL,
    algorithm=LoopClosureAlgorithm.LSE_REDUCED_PCG,
    sigma_m=1.0,
    weighting=LoopClosureWeighting.LENGTH_AZIMUTH_DIAGONAL,
    inverse_length_weight_cap=10.0,
    base_sigma_length_m=0.05,
    base_sigma_azimuth_deg=1.0,
    average_azimuth_readings=True,
    anchor_floating_components=True,
    virtual_shot_policy=VirtualShotPolicy.MEASURED,
    fix_start_positions=False,
    preserve_floating_xy_centroids=False,
    skip_missing_origins=True,
    source_is_fresh=False,
    coordinate_origins=None,
    vertical_controls=None,
    accept_adjusted_measurements=False,
    method=LoopClosureMethod.LEAST_SQUARES,
    cg_max_iterations=60_000,
    cg_absolute_tolerance=1e-8,
    cg_relative_tolerance=1e-5,
    fix_control_depths=False,
    length_floor_m=0.1,
    minimum_anchor_count=2,
    deduplicate_edges=True,
    max_iterations=None,
)

# Origin/software: compass_lib/compass_lib/solver/ariane.py, ArianeSolver.
# This is Compass's Python extension of sparse graph adjustment, inspired by
# Larry Fish's traverse-quality approach; it is not the horizontal reference
# solver inside Ariane's Line. Use for full XYZ adjustment with 1/L² base
# precision and best anchor-traverse misclosure-per-shot quality factors.
# Matches its BFS paths, 0.1 m length floor, 1e-6 quality threshold, centred
# sparse normal equations, the source CG warm start and direct-solver fallback.
# All numerical work runs in cave-closure Rust, including source rounding rules.
# Fewer than two anchors leaves measured positions unchanged. Anchor depths
# are deliberately fixed by this preset; caller vertical controls override them.
# Used by tests/export_goldens.py and tests/test_export_goldens.py across all
# public Ariane and Stalagmight inputs; available to common-model API callers.
TraverseQualityWeightedLeastSquaresSpatialSolver = LoopClosureSolver(
    name="TraverseQualityWeightedLeastSquaresSpatialSolver",
    mode=LoopClosureMode.SPATIAL,
    algorithm=LoopClosureAlgorithm.LSE_UNREDUCED_PCG,
    sigma_m=1.0,
    weighting=LoopClosureWeighting.TRAVERSE_QUALITY_INVERSE_SQUARED_LENGTH,
    inverse_length_weight_cap=10.0,
    base_sigma_length_m=0.05,
    base_sigma_azimuth_deg=1.0,
    average_azimuth_readings=False,
    anchor_floating_components=False,
    virtual_shot_policy=VirtualShotPolicy.MEASURED,
    fix_start_positions=False,
    preserve_floating_xy_centroids=False,
    skip_missing_origins=True,
    source_is_fresh=False,
    coordinate_origins=None,
    vertical_controls=None,
    accept_adjusted_measurements=False,
    method=LoopClosureMethod.TRAVERSE_QUALITY_CG,
    cg_max_iterations=60_000,
    cg_absolute_tolerance=1e-8,
    cg_relative_tolerance=1e-5,
    fix_control_depths=True,
    length_floor_m=0.1,
    minimum_anchor_count=2,
    deduplicate_edges=True,
    max_iterations=None,
)

# Origin/software: compass_lib/loop_closure/ariane_solver.java and
# graph_solver.rs, the horizontal solver inside Ariane's Line. The copies in
# cave-closure/docs/loop_closure are identical. Use to reproduce the historical
# unreduced, unpreconditioned CG implementation, including its 0.001 absolute
# residual tolerance, 1e-15 denominator exit and 60,000-iteration limit.
# Unlike the existing least-squares preset, this retains reference early exits.
# Used by tests/export_goldens.py and tests/test_export_goldens.py on every
# public fixture; works with common models from Ariane and Stalagmight alike.
InverseLengthWeightedConjugateGradientHorizontalSolver = LoopClosureSolver(
    name="InverseLengthWeightedConjugateGradientHorizontalSolver",
    mode=LoopClosureMode.HORIZONTAL,
    algorithm=LoopClosureAlgorithm.LSE_UNREDUCED_PCG,
    sigma_m=1.0,
    weighting=LoopClosureWeighting.INVERSE_LENGTH,
    inverse_length_weight_cap=10.0,
    base_sigma_length_m=0.05,
    base_sigma_azimuth_deg=1.0,
    average_azimuth_readings=False,
    anchor_floating_components=False,
    virtual_shot_policy=VirtualShotPolicy.MEASURED,
    fix_start_positions=True,
    preserve_floating_xy_centroids=True,
    skip_missing_origins=True,
    source_is_fresh=False,
    coordinate_origins=None,
    vertical_controls=None,
    accept_adjusted_measurements=False,
    method=LoopClosureMethod.REFERENCE_CG,
    cg_max_iterations=60_000,
    cg_absolute_tolerance=0.001,
    cg_relative_tolerance=0.0,
    fix_control_depths=False,
    length_floor_m=0.1,
    minimum_anchor_count=2,
    deduplicate_edges=True,
    max_iterations=None,
)

# Origin/software: Compass-lib's former SparseSolver and its current
# InverseLengthWeightedL1SpatialSolver preset. It originally used SciPy's HiGHS
# linear programming backend; all optimization now lives in cave-closure's l1.rs.
# Use for XYZ inverse-length weighted absolute-error closure, keeping the first
# undirected observation, a 0.1 m length floor, and unchanged positions below two
# anchors. Exact OpenSpeleo closure identities are resolved by the existing
# native graph preparation before the native L1 solver is called. Geographic
# anchor depths are fixed explicitly; supplied vertical controls override them.
# Used by tests/export_goldens.py and tests/test_export_goldens.py for all public
# Ariane and Stalagmight fixtures, without changing existing preset artifacts.
InverseLengthWeightedL1SpatialSolver = LoopClosureSolver(
    name="InverseLengthWeightedL1SpatialSolver",
    mode=LoopClosureMode.SPATIAL,
    algorithm=None,
    sigma_m=None,
    weighting=LoopClosureWeighting.INVERSE_LENGTH,
    inverse_length_weight_cap=10.0,
    base_sigma_length_m=0.05,
    base_sigma_azimuth_deg=1.0,
    average_azimuth_readings=False,
    anchor_floating_components=False,
    virtual_shot_policy=VirtualShotPolicy.MEASURED,
    fix_start_positions=False,
    preserve_floating_xy_centroids=False,
    skip_missing_origins=True,
    source_is_fresh=False,
    coordinate_origins=None,
    vertical_controls=None,
    accept_adjusted_measurements=False,
    method=LoopClosureMethod.INVERSE_LENGTH_WEIGHTED_L1,
    cg_max_iterations=60_000,
    cg_absolute_tolerance=1e-8,
    cg_relative_tolerance=1e-5,
    fix_control_depths=True,
    length_floor_m=0.1,
    minimum_anchor_count=2,
    deduplicate_edges=True,
    max_iterations=None,
)

PRESETS = MappingProxyType(
    {
        solver.name: solver
        for solver in (
            InverseLengthWeightedL1SpatialSolver,
            LeastSquaresHorizontalSolver,
            LeastSquaresSpatialSolver,
            InverseLengthWeightedLeastSquaresHorizontalSolver,
            LengthAzimuthWeightedLeastSquaresHorizontalSolver,
            TraverseQualityWeightedLeastSquaresSpatialSolver,
            InverseLengthWeightedConjugateGradientHorizontalSolver,
        )
    }
)
