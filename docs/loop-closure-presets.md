# Loop-closure presets

`openspeleo_lib.loop_closure.presets` provides seven named, immutable
`LoopClosureSolver` instances. Each declaration specifies every solver argument
explicitly, including `None` and `False` values, rather than relying on
constructor defaults. Their TitleCase names identify configurations; they are
not classes or factories, so use them without parentheses. `PRESETS` is a
read-only registry keyed by their stable names. All presets operate on common
OpenSpeleo models from either supported reader.

| Preset                                                   | Coordinates | Origin and purpose                                                                                                |
| -------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------- |
| `LeastSquaresHorizontalSolver`                           | XY          | OpenSpeleo independent Cartesian Gaussian adjustment, recorded depths retained                                    |
| `LeastSquaresSpatialSolver`                              | XYZ         | Same model with independent vertical controls                                                                     |
| `InverseLengthWeightedLeastSquaresHorizontalSolver`      | XY          | The graph formulation inside Ariane's Line; capped inverse-length weights with modern cave-closure convergence    |
| `LengthAzimuthWeightedLeastSquaresHorizontalSolver`      | XY          | Stalagmight's Closures Computed View, length/azimuth variances and section quality                                |
| `InverseLengthWeightedConjugateGradientHorizontalSolver` | XY          | Compass's Java/Rust reference copy of the solver inside Ariane's Line, including its historical CG stopping rules |
| `TraverseQualityWeightedLeastSquaresSpatialSolver`       | XYZ         | Compass's Python sparse normal-equation solver with inverse-squared-length and traverse-quality weights           |
| `InverseLengthWeightedL1SpatialSolver`                   | XYZ         | Compass-lib's former SparseSolver and current L1 preset, inverse-length weighted absolute errors via HiGHS        |

## Numerical settings and provenance

The original four presets default to `LoopClosureAlgorithm.LSE_REDUCED_PCG`. The
algorithm selects the numerical backend independently of the coordinate mode and
graph policy. Other supported least-squares backends can be selected on a
customized instance. The shared source checks, coordinate provenance, local
WGS84 azimuthal-equidistant projection, and immutable snapshots live in
`openspeleo_lib/loop_closure.py`. Every preset computes in the Rust
`cave-closure` library. `openspeleo_lib` maps models, units, coordinate
provenance and geographic projections into that interface; it performs no
loop-closure numerics. The Rust implementation lives in
`src_rust/loop_closure.rs`, `graph.rs`, and `l1.rs`. The two CG presets select
`LSE_UNREDUCED_PCG`; no graph reduction or preconditioner is introduced.

`LeastSquaresHorizontalSolver` is the named form of `LoopClosureSolver`'s
existing defaults. Each measured REAL leg has independent Cartesian uncertainty
with `sigma_m=1.0`; customize `sigma_m` for the caller's declared placement
uncertainty. VIRTUAL legs are exact hard offsets. Only original explicit XY
coordinates become hard geographic controls. Missing measured origins and
uncontrolled translation are rejected.

`LeastSquaresSpatialSolver` uses the same weighting and graph settings with
`LoopClosureMode.SPATIAL`. Z is solved in local ENU coordinates and export
converts it to positive-down depth. Independent Z controls are supplied through
`vertical_controls`; recorded survey depths are not silently promoted to them.

`InverseLengthWeightedLeastSquaresHorizontalSolver` selects relative precision
`min(10, 1 / measured_displacement_length_m)`, including the weight cap for
zero-length legs. It treats both REAL and VIRTUAL legs as measured observations,
fixes START positions on the unadjusted geographic view, skips unresolved
origins, and preserves unadjusted centroids for floating XY components. Explicit
source coordinates remain authoritative. The reference sources are
`cave-closure/docs/loop_closure/ariane_solver.java` and
`cave-closure/docs/loop_closure/graph_solver.rs`. This is analogous to the
solver inside Ariane's Line at the graph-formulation level; the numerical
backends use their own convergence checks rather than reproducing historical
early stopping. See
[the weighted solver formulation](inverse-length-horizontal-solver.md) for the
objective, safeguards, and independent numerical regression evidence.

`LengthAzimuthWeightedLeastSquaresHorizontalSolver` matches Stalagmight's
horizontal, per-axis weighted normal equations. It uses the circular mean of
both forward azimuth readings and multiplies the base length and angle standard
deviations by section quality. For true azimuth `a`, slope length `L`, and
quality `q`, its independent axis variances are:

- `var_x = (sin(a) * sigma_length_m * q)^2 + (L * cos(a) * radians(sigma_azimuth_deg) * q)^2`
- `var_y = (cos(a) * sigma_length_m * q)^2 + (L * sin(a) * radians(sigma_azimuth_deg) * q)^2`

The default base sigmas, taken from Stalagmight's
`src-tauri/crates/models/src/config/mod.rs`, are 0.05 metres and 1 degree.
Invalid or missing section quality falls back to one. An off-diagonal XY
covariance is deliberately not introduced: Stalagmight solves the axes
independently. Its depth-sigma config field does not enter this horizontal
solve. Zero-variance axes contribute no observation, exactly as in the source
solver; they are not approximated with a large or small artificial weight.
Null-space translations retain their measured positions. Each component without
a geographic control gets a deterministic unadjusted anchor in source station
order.

The native boundary preserves second azimuth readings, section quality and
pending `Batch`/`LeastSquaresWeighted` closure identities in common models.
Consequently preparation never calls the native reader. Existing presets retain
the primary-reading convention unless `average_azimuth_readings=True` is chosen.
Depths and source measurements remain unchanged. Geographic export still needs
at least one genuine geographic control, and coordinate inconsistencies remain
errors. Joint calibrated statistics are not reported for the combined
independent axis result; the weighted objective and convergence remain
available.

## Compass implementations

`InverseLengthWeightedConjugateGradientHorizontalSolver` ports
`compass_lib/loop_closure/ariane_solver.java` and `graph_solver.rs`. Those
reference files are identical to the copies in `cave-closure/docs/loop_closure`.
Its graph settings match `InverseLengthWeightedLeastSquaresHorizontalSolver`:
measured REAL/VIRTUAL legs, fixed START XY, skipped missing origins, station
substitutions, and capped inverse-length precision. Its
`LoopClosureMethod.REFERENCE_CG` method instead preserves the reference's
unreduced, unpreconditioned CG recurrence, measured-position warm start,
absolute residual threshold `0.001`, denominator threshold `1e-15`, and
iteration limit `60_000`. Floating translations follow the initial guess. The
reference returns its current iterate on any of these exits; it does not fall
back to a direct solve or enforce modern backend convergence criteria. Recorded
depths remain unchanged. A zero relative tolerance explicitly selects absolute
stopping only. It uses no coordinate centering, matching the Rust reference
code.

`TraverseQualityWeightedLeastSquaresSpatialSolver` ports
`compass_lib/compass_lib/solver/ariane.py::ArianeSolver`, a distinct Python
implementation inspired by Larry Fish's traverse-quality method. Its
`LoopClosureMethod.TRAVERSE_QUALITY_CG` method reproduces:

- Full XYZ adjustment with fixed geographic anchors. This preset explicitly opts
  into `fix_control_depths=True`, treating their recorded depths as anchor
  elevations; supplied `vertical_controls` override those elevations. The
  Cartesian spatial preset requires independent vertical controls.
- Base precision `1 / max(length_m, 0.1)^2`.
- BFS paths between sorted anchor pairs, blocking other intermediate anchors.
  Each undirected endpoint pair retains its best traverse's 3D misclosure per
  shot. Parallel-edge traversal deltas follow the source's last-edge lookup.
- A quality multiplier `1 / quality^2` only when quality exceeds `1e-6`;
  otherwise the multiplier is one. Unvisited edges also use one.
- Unreduced sparse normal equations centered on the anchor centroid, with
  measured-position warm starts. Anchor iteration is sorted for reproducible
  floating-point summation across Python processes.
- Rust CG matching the source with `60_000` iterations, absolute tolerance
  `1e-8`, and relative tolerance `1e-5` (explicitly recording the source's SciPy
  default). Each axis falls back to a native sparse direct solve if CG reports
  failure.
- Fewer than two anchors returns the unadjusted positions, even for a closed
  loop. Anchors are counted after common-model closure identities are merged.

The source's length-change check emits warnings; it does not constrain the
solution. The unused heading-change setting does not enter its equations. Both
ports use common-model measurements after the same coordinate-safety validation
and local projection as other presets. CLOSURE identities substitute stations
before numerical preparation. VIRTUAL legs must be measured for these backends;
incompatible custom settings raise instead of being ignored. Explicit
coordinates remain authoritative and conflicting controls are rejected. Source
measurements and files remain unchanged. Relative precision does not claim
calibrated instrument statistics. Matching the implementations' numerical rules
retains the existing checked-in GeoJSON bytes. Native scalar power, compensated
norm/sum and fused sparse-product rounding preserve the historical numerical
contract. For these two CG presets, normal exports pass the complete request to
`cave_closure.solve_loop_closure_json` once; Rust prepares, solves and
serializes the complete result before returning. Python only maps that returned
data into GeoJSON. The explicit `prepare().solve()` interface retains reusable
immutable native preparations; internal component/gauge solves never return to
Python.

## Inverse-length weighted L1

`InverseLengthWeightedL1SpatialSolver` matches the numerical configuration of
`compass_lib.preset.InverseLengthWeightedL1SpatialSolver`, derived from
Compass-lib's former `SparseSolver` using SciPy's HiGHS linear-programming
backend. The implementation is now `cave-closure/src_rust/l1.rs`. It minimizes
inverse-length weighted absolute XYZ displacement errors with a 0.1 metre length
floor, retains the first observation for each undirected station pair, requires
two distinct anchors after identity substitution, and has no iteration limit.
Fewer than two anchors preserves the measured positions. `algorithm` and
`sigma_m` are `None`: Gaussian solver selection and covariance do not apply.
Customize `length_floor_m`, `minimum_anchor_count`, `deduplicate_edges`, and
`max_iterations` using `dataclasses.replace`.

The preset uses common-model REAL and VIRTUAL measurements from either reader.
Explicit geographic coordinates supply hard XY controls, and
`fix_control_depths=True` explicitly retains their recorded depths as anchor Z.
Caller-supplied `vertical_controls` override those depths. Missing origins are
skipped and exact CLOSURE identities are preserved. The ordinary coordinate
safety guard, provenance checks, local projection, and source immutability apply
as for other presets. No fixture coordinates or measurements are corrected.

The published native L1 API accepts Cartesian observations. OpenSpeleo first
uses the existing native graph preparation and its inspection API to normalize
length/bearing/depth observations and resolve station identities and controls.
It does not run the CG solver. Python maps the normalized rows to the native L1
request and maps resolved alias IDs back onto the result. All vector arithmetic,
identity resolution, weighting, deduplication and optimization remain in Rust;
this preset uses separate existing native calls without extending cave-closure.
The explicit `prepare().solve()` path retains an immutable native LP snapshot.
The analytical L1 regression in `tests/test_loop_closure_presets.py` checks the
short-leg optimum, exact anchors and aliases, direct/prepared export equality,
and unchanged source measurements.

## Current use in the repository

The weighted preset is used directly by:

- `tests/test_geojson_convert.py::TestConvertToGeoJson::test_convert_to_geojson_inverse_length_weighted_horizontal`,
  which compares private Ariane conversions with encrypted, minified
  solver-named goldens.
- `tests/export_private_horizontal_goldens.py`, which explicitly generates those
  encrypted expected outputs.
- `tests/test_inverse_length_horizontal_solver.py`, which checks exact
  weighted-loop solutions, both length units, all numerical backends, fixed
  starts, centroid preservation, and common models from the Stalagmight reader.

The instrument-weighted preset is available to API callers for either reader's
common models. It is selected directly by the public named-preset golden matrix
and is not selected implicitly by the CLI. Its source and intended use are
recorded immediately above its fully explicit declaration in
`openspeleo_lib/preset.py`.

`tests/test_loop_closure_presets.py` exercises all seven presets, their common
instance type, immutability, customization, and the independence of weighting
and graph policies.

All seven presets are used by public golden generation in
`tests/export_goldens.py` and comparisons in `tests/test_export_goldens.py`, for
every public fixture in the matrix. Filenames include the full preset name. The
two Cartesian presets are also available to API callers. Current CLI conversion
in `openspeleo_lib/commands/convert.py` constructs customized
`LoopClosureSolver` instances directly; it does not look up or import these
presets. Measured conversion without a supplied solver never selects a preset
implicitly.

## Using and customizing a preset

```python
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.loop_closure.presets import (
    InverseLengthWeightedLeastSquaresHorizontalSolver,
)

geojson = survey_to_geojson(
    survey,
    loop_closure_solver=InverseLengthWeightedLeastSquaresHorizontalSolver,
)
```

Use `dataclasses.replace` to customize an immutable preset:

```python
from dataclasses import replace
from cave_closure import LoopClosureAlgorithm
from openspeleo_lib.loop_closure.presets import LeastSquaresHorizontalSolver

solver = replace(
    LeastSquaresHorizontalSolver,
    algorithm=LoopClosureAlgorithm.LSE_SPARSE_QR,
    sigma_m=2.0,
)
```

For spatial export, clone `LeastSquaresSpatialSolver` with independently
supplied `vertical_controls`. For a hand-built common model, also declare
`source_is_fresh=True` only when its coordinates have not been populated by
propagation, or supply a complete `coordinate_origins` map. Reader-created
models already carry coordinate provenance.

Preset names are stable artifact labels. The weighted private goldens retain the
suffix `-InverseLengthWeightedLeastSquaresHorizontalSolver.geojson.encrypted`
when a preset is customized with numerically equivalent backend settings.
