# Inverse-length weighted horizontal least squares

`InverseLengthWeightedLeastSquaresHorizontalSolver` in
`openspeleo_lib.loop_closure.presets` is a premade `LoopClosureSolver`
configuration for the complete optional horizontal graph formulation over the
common OpenSpeleo model. It accepts data from Ariane and Stalagmight readers
without consulting either native reader after parsing. This preset is analogous
to the solver inside Ariane's Line: fixed START XY, measured REAL/VIRTUAL legs,
capped inverse-length weights, station substitutions, and preserved recorded
depths.

```python
from openspeleo_lib.loop_closure.presets import (
    InverseLengthWeightedLeastSquaresHorizontalSolver,
)
from openspeleo_lib.geojson import survey_to_geojson

solver = InverseLengthWeightedLeastSquaresHorizontalSolver
geojson = survey_to_geojson(survey, loop_closure_solver=solver)
```

Measured export remains the default when no solver is supplied. Every preset is
an immutable `LoopClosureSolver` instance. `LeastSquaresHorizontalSolver` and
`LeastSquaresSpatialSolver` provide premade independent Cartesian
configurations. Use
`dataclasses.replace(preset, algorithm=..., source_is_fresh=True)` to customize
a preset without changing the shared instance. Spatial callers also supply
independent vertical controls.

`LoopClosureSolver` exposes weighting, virtual-shot treatment, fixed-start
handling, missing-origin handling, floating XY centroids, dimensions, and
numerical backend independently. `LoopClosureWeighting` selects independent
Cartesian or inverse-length weighting. `VirtualShotPolicy` selects hard offsets
or measured observations. `PRESETS` provides a read-only registry keyed by
stable solver names. The name
`InverseLengthWeightedLeastSquaresHorizontalSolver` labels the weighted preset
and its golden files; it is not a subclass.

## Graph and objective

Each ordinary, non-excluded station is a vertex. Each REAL or VIRTUAL leg with
both endpoints present contributes its measured ENU displacement. CLOSURE
records substitute `FromID` with the nonnegative `ClosureToID` target; their
`ID` identifies the record. Target-less common-model identities equate
`id_start` with `id_stop`. Ancillary measurements on both forms are ignored.
Identity-only station IDs are resolved without creating measured observations.
An unresolved origin contributes no measured edge.

The objective sums `w * ((x_to - x_from - dx)^2 + (y_to - y_from - dy)^2)` over
measured edges, with `w = min(10, 1 / displacement_length_m)`. Zero-length edges
use the capped weight of ten. The length is the three-dimensional measured
vector magnitude, in metres. The implementation passes relative precision to the
numerical backend, so these weights do not claim calibrated instrument variances
or justify calibrated statistical inference.

The local frame is an explicitly recorded WGS84 azimuthal-equidistant ENU
projection. Measured vectors use common-model lengths, depths, bearing
corrections, and units. Independent authoritative start depths are respected.
START stations are fixed to their unadjusted positions. Explicit source XY
coordinates remain hard controls under the coordinate-safety contract. A derived
START control is labelled separately from original explicit-coordinate evidence.
A floating measured component retains its unadjusted centroid, reproducing the
translation gauge preserved by conjugate gradient started from that view.

The default numerical backend is the reduced preconditioned conjugate-gradient
least-squares solver. Select another supported `LoopClosureAlgorithm` through
`algorithm=...`; this changes the backend, not the objective or graph policy.
Solutions must converge under the backend's stopping and residual checks. The
mathematical graph formulation follows the Java graph construction and weighted
normal equations in `cave-closure/docs/loop_closure`; the historical iteration
stopping behavior is not used as a substitute for convergence.

The solver changes only X and Y. Recorded endpoint depths are preserved.
Preparation and export operate on disposable common-model views; source models,
measurements, and original coordinates remain unchanged. The ordinary 500-metre
coordinate guard runs before adjustment, so solving cannot conceal invalid
source coordinates.

## Regression evidence

`tests/test_inverse_length_horizontal_solver.py` checks variable-length closed
loops against exact rational Lagrange-multiplier solutions. Coverage includes
zero-length and short-edge caps, VIRTUAL measured legs, every numerical backend,
both length units, fixed starts, authoritative coordinates, floating-component
centroids, and native-reader common models.

`tests/test_geojson_convert.py` retains measured private-fixture identity tests
and adds `test_convert_to_geojson_inverse_length_weighted_horizontal` cases.
Expected adjusted output uses minified
`projectXXX-InverseLengthWeightedLeastSquaresHorizontalSolver.geojson` files,
stored as `.geojson.encrypted` artifacts. The existing pytest fixture setup
handles decryption. Coordinate-invalid surveys have rejection coverage rather
than a successful-output golden.

Regenerate encrypted goldens explicitly from the package root:

```sh
uv run python -m tests.export_private_horizontal_goldens tests/artifacts/private/ariane --env-file .env
```

The encryption key follows the existing environment-file workflow. Plaintext
inputs and intermediate outputs remain in an OS temporary directory during
generation. Only encrypted new goldens belong in version control. Tests never
regenerate or overwrite expected outputs.
