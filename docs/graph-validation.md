# Geographic graph validation

Measured GeoJSON export and every loop-closure preset share a physical
connectivity pass before evaluating geometry. It operates on common OpenSpeleo
models, after parsing, and does not invoke a native reader or numerical solver.

## Reachability and cleanup

An active station is reachable when it has a path to an active, explicitly
recorded GPS point. Ordinary shot connections can be followed in either
direction. Closure records connect equivalent station identities at the same
physical location. Targeted Ariane closures connect `FromID` to `ClosureToID`;
the closure record's own ID is not a station. Targetless closures connect
`FromID` to `ID` and may define identity-only aliases, including alias chains.

Excluded records provide no anchors, connections, aliases, or solver
constraints. A supported alias cannot recreate an excluded ordinary station.
Previously derived coordinates and vertical controls do not supply GPS anchors
for loop-closure preparation; coordinate-origin provenance remains mandatory.

Cleanup retains GPS-connected components and removes unanchored components,
including their measurements and closures. An isolated cycle cannot anchor
itself. Multiple independently GPS-anchored components are retained.

A station and its incoming measurement are distinct. If a measurement references
a nonexistent or excluded origin, that leg is dropped. Its endpoint station can
still survive through GPS, another measured connection, or a closure. The export
represents a surviving REAL or START station with no valid incoming leg as a
Point. No measurement is invented for the absent origin. A closure whose
endpoints cannot be resolved is dropped.

Cleanup selects records without deleting them from the input survey. Numerical
requests include only retained stations, observations, and constraints. Vertical
controls for removed stations are discarded; unknown control IDs remain errors.

## Placement and safety

Measured export first exhausts the established forward traversal, preserving
placement for ordinary forward-connected geometry. It then uses closure links
and reverse traversal to place remaining connected stations deterministically.
Reverse placement inverts the original forward bearing on WGS84 and checks the
forward residual, rather than assuming that a bearing plus 180 degrees is its
exact inverse. Placement never overwrites an explicit GPS point or adjusts
already placed geometry to close a loop. Numerical adjustment remains opt-in.

Horizontal distance respects units, measured endpoint depths, and authoritative
independent start depths. Only retained active GPS points can supply magnetic
placement context. Source measurements and file bytes remain unchanged. Measured
export retains its existing behavior of populating derived coordinates on
retained source stations; adjusted export and preparation remain immutable.
Snapshots retain the original evidence and the immutable graph selection so
prepared and direct export use identical topology.

Parsing still validates coordinate ranges. The existing 500-metre discrepancy
guard runs on unadjusted geometry, including comparable excluded explicit
endpoints, without using those excluded records for connectivity. Conflicting
solver controls remain errors. A survey without usable GPS-connected geometry
fails; the CLI does not create or overwrite output on failure.

## Warnings and regression fixtures

Each affected source record emits one warning per conversion, in source order,
with its shot ID, section, and reason. Examples using synthetic IDs:

```text
[Shot 123] Is unreachable from any GPS anchor; dropping station and incident connections.
[Shot 456] Incoming leg references missing or excluded origin 789; dropping leg and retaining connected station.
[Shot 987] Closure references an unavailable station; dropping closure.
```

`tests/test_geojson_connectivity.py` covers the shared graph policy, native
request filtering, reverse geometry, exclusions, aliases, coordinate provenance,
CLI diagnostics, and source/output preservation. Tests run each preset with its
required controls and compare direct and prepared export.

`tests/connectivity_fixture.py` builds a synthetic TML in a temporary directory
from remapped topology in
`tests/artifacts/synthetic-connectivity-topology.json`. The topology preserves
the original failure pattern, including missing origins and closure-connected
branches. Coordinates, measurements, section names, dates, and station IDs are
synthetic; personal and cartographic metadata are absent. The original user
survey is not required to generate or run this test. The resulting regression
failed with the former unknown-station closure error before graph cleanup and
bidirectional placement were introduced.
