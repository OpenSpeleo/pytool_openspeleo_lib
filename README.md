# OpenSpeleoLib

OpenSpeleoLib reads, writes, validates, and converts cave-survey data.

## GeoJSON conversion

Convert an Ariane TML or TMLU survey with:

```console
openspeleo convert -i survey.tml -o survey.geojson -f geojson
```

### Shot colors

GeoJSON preserves recorded Ariane shot colors, with survey-color fallback for
missing or invalid values. See [shot-color export](docs/shot-colors.md) for the
normalization, compatibility, and verification contract.

### Coordinate validation

Ariane imports enforce the same constraints as the base survey models. Latitude
must be between -90 and 90 degrees, longitude between -180 and 180 degrees, and
both must be finite when provided. Invalid coordinates raise `ValidationError`
during parsing, with notes identifying the section, station, shot ID, field, and
supplied value. Comments are descriptive text; they never supply coordinates,
UTM zones, or magnetic declination.

Run `openspeleo validate_tml -i survey.tml` to check structural/model validity.
Run full conversion to check geographic consistency as well. See
[coordinate validation](docs/coordinate-validation.md) for diagnostics and the
application integration contract.

### Coordinate safety guard

A connected shot can contain both survey measurements and an explicit geographic
endpoint. During GeoJSON conversion, explicit coordinates remain authoritative,
but OpenSpeleoLib calculates where the shot should end from its length, depth,
azimuth, unit, and magnetic declination. If the supplied and calculated
endpoints differ by more than 500 metres, conversion raises
`InconsistentShotCoordinatesError`.

For example, synthetic Shot ID `4242` with supplied coordinates `(-70, 40)` and
a calculated endpoint near `(40, -70)` produces an error containing:

```text
[Shot ID=4242]: Explicit coordinates are inconsistent with shot measurements
```

The 500-metre threshold is a fixed catastrophic-data guardrail, not a
survey-quality or GPS-accuracy guarantee. Coordinates within the threshold are
accepted without certifying their accuracy. Root anchors and connected anchors
whose parents cannot be resolved cannot be compared and retain their existing
behavior.

The library never swaps coordinates, guesses a correction, or emits a partially
converted GeoJSON document. The CLI calculates and validates the complete
document before opening the output path: a failed conversion does not create a
new output and does not replace an existing output passed with `--overwrite`.
Correct the source survey and run the conversion again.

## Stalagmight input

```python
from cave_closure import LoopClosureAlgorithm
from openspeleo_lib.interfaces import StalagmightInterface
from openspeleo_lib import LoopClosureSolver
from openspeleo_lib.geojson import survey_to_geojson

survey = StalagmightInterface.from_file("survey.stalx")
solver = LoopClosureSolver(algorithm=LoopClosureAlgorithm.LSE_REDUCED_PCG)
geojson = survey_to_geojson(survey, loop_closure_solver=solver)
```

```sh
openspeleo convert -i survey.STALX -o survey.geojson -f geojson --beautify
openspeleo convert -i survey.stalx -o normalized.json -f json
```

`stalagmight_lib.read_stalx()` owns SQLite parsing. `StalagmightInterface`
converts the parsed data into ordinary OpenSpeleo `Survey`, `Section`, and
`Shot` models. No native survey is retained. After conversion, the common
GeoJSON and loop-closure APIs operate exclusively on OpenSpeleo models.

The adapter maps shot kinds, measurement units, bearing corrections, datums,
merges, and active graph connections at the input boundary. It preserves every
measured leg, representing additional station equivalences as standard OSPL
`CLOSURE` records. Explicit schema-19 cycles are preserved. Root layout
positions and editing locks do not become numerical controls.

`survey_to_geojson(survey)` exports measured geometry for any OpenSpeleo survey,
including one read from Ariane or Stalagmight. To opt into adjustment, construct
`solver = LoopClosureSolver(algorithm=...)` from `openspeleo_lib` and pass
`survey_to_geojson(survey, loop_closure_solver=solver)`. The CLI opts in with
`--loop-closure`; `--algorithm`, `--mode`, and `--sigma-m` configure that
solver. Horizontal mode retains endpoint depths; spatial callers provide
independent vertical controls keyed by OpenSpeleo station IDs.
`measurements_are_adjusted` records evidence that measurements may already have
been changed. Solving such a survey requires explicit
`accept_adjusted_measurements=True`; the CLI exposes the corresponding flag.

JSON output uses the OpenSpeleo model for every input format. Native Stalagmight
writing is unsupported. Conversion and serialization finish before output is
opened, so failures preserve existing output. Symlink and hardlink source
aliases are refused. Standalone dependencies and locks remain authoritative;
root integration uses editable local packages.

## Loop-closure snapshots

Loop closure is optional behavior; measured export is the default.
`cave_closure` is included as a package dependency. Spatial adjusted exports use
solved ENU Z to derive positive-down depth; horizontal adjusted exports retain
the recorded depth policy.

`openspeleo_lib.loop_closure.prepare_loop_closure` provides Gaussian loop
closure using `cave_closure`. A fresh `BaseInterface.from_file` captures
coordinate-origin evidence before propagation. Otherwise supply
`source_is_fresh=True` only for a known fresh model, or provide a complete
`coordinate_origins` map. Unknown history is rejected. Snapshots preserve
measured inputs and explicit-coordinate identity; known-derived coordinates do
not become hard controls. The existing 500 m guard runs against unadjusted
geometry on a disposable copy.

Select `mode=LoopClosureMode.HORIZONTAL` or `mode=LoopClosureMode.SPATIAL` and
positive `sigma_m` for the caller-declared independent Cartesian placement
model. Horizontal mode preserves recorded endpoint depths. Spatial geographic
output also requires independent vertical controls; recorded depths are not
silently reused as hard controls. Editing `locked` metadata is not a numerical
constraint. Geographic coordinates use an explicitly recorded local WGS84
azimuthal-equidistant ENU approximation.

Ariane `CLOSURE` records equate **FromID with ClosureToID** when `ClosureToID`
is nonnegative; their `ID` identifies the record, not a new station.
Common-model identity records with no target (the default negative
`closure_to_id`) instead equate `id_start` with `id_stop`. Both forms produce
exact station equivalence. Length, angles, and depths on closure records do not
create observations or controls. Compass closure handling is separate and
belongs to the Compass adapter.

`snapshot.solve()` requires convergence. Pass its associated result to
`loop_closed_survey_to_geojson(snapshot, result)`; mismatched preparation or
changed source evidence is rejected. Neither preparation nor export mutates
source models. Ordinary conversion remains independently available.

For Stalagmight input, first call `StalagmightInterface.from_file(path)`, then
pass the returned OpenSpeleo survey to the same `prepare_loop_closure()` and
`survey_to_geojson()` functions used for other formats. There is no native
preparation or export entrypoint.

Import `LoopClosureMode` and `LoopClosureAlgorithm` directly from
`cave_closure`. Preparation accepts
`algorithm=LoopClosureAlgorithm.LSE_REDUCED_PCG` (the default),
`LSE_UNREDUCED_PCG`, `LSE_SPARSE_QR`, or `LSE_SPARSE_CHOLESKY`. The algorithm
selects the least-squares solver independently of
`mode=LoopClosureMode.HORIZONTAL` or `mode=LoopClosureMode.SPATIAL`.

Closure regression ground truth lives in
`tests/artifacts/loop_closure_ground_truth.json`. Regenerate it with
`uv run python -m tests.loop_closure_reference <output-path>` and compare the
result before replacing it. The generator uses exact rational elimination,
independently of the production solver. Synthetic open branches, misclosed
rings, and coupled loops follow the horizontal graph construction in
`cave-closure/docs/loop_closure/ariane_solver.java`: fixed starts, station
substitutions, and inverse-length edge weights. Equal-length edges make those
weights equivalent to the configured uniform Cartesian uncertainty. These
fixtures do not establish equivalence for variable-length Java weighting or
spatial solving. Tests check every supported least-squares algorithm, both
length units, both reader boundaries, source preservation, and repeated solves.

Ordinary Ariane projection continues to use the parent station's depth;
`DepthIn` remains ancillary there. A common-model shot with
`depth_start_is_authoritative=True` uses its independent measured start depth,
as set by the Stalagmight adapter. This policy survives snapshot serialization.

Public fixture JSON, measured GeoJSON, and GeoJSON for every registered preset
are checked against goldens by `tests/test_export_goldens.py`. Reader JSON stays
byte-exact; GeoJSON permits bounded absolute coordinate variation across
platforms, with exact structure and properties. See
[export regressions](docs/export-regressions.md) for the tolerances, valid and
invalid Stalagmight fixtures, synthetic geographic test controls, and explicit
golden regeneration.

For capped inverse-length weighting, fixed START positions, and measured REAL
and VIRTUAL legs, use
`preset.InverseLengthWeightedLeastSquaresHorizontalSolver`, a premade
`LoopClosureSolver` instance in `openspeleo_lib.loop_closure.presets`. See the
[inverse-length horizontal solver](docs/inverse-length-horizontal-solver.md) for
its graph formulation, source-coordinate safeguards, and encrypted private
regression goldens.

[Loop-closure presets](docs/loop-closure-presets.md) describes all premade
configurations, their numerical origins, and where they are currently used.

`preset.LengthAzimuthWeightedLeastSquaresHorizontalSolver` selects the
horizontal length/azimuth/section-quality weighting used by Stalagmight's
Closures Computed View. The common-model adapter preserves the second forward
bearing and pending closure identities needed by this configuration; the solver
never reopens native files. Its origin and axis-variance formulas are described
in the preset guide.

`preset.InverseLengthWeightedL1SpatialSolver` selects the inverse-length
weighted absolute-error solver used by Compass-lib's L1 preset. It is another
immutable `LoopClosureSolver` instance and works with both readers' common
models. Measurement normalization, closure identities, and LP optimization use
the existing `cave_closure` APIs in separate native calls. Seven minified public
GeoJSON artifacts cover this preset; existing preset artifacts remain unchanged.
