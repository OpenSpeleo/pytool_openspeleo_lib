# Resolved native shots

`survey_to_geojson(..., on_resolved_shot=callback)` reports native shot evidence
with the geographic position of the original destination. This supports features
such as importing exploration annotations without guessing identity from a
rendered feature. The callback is optional; GeoJSON content is unchanged.
`LoopClosureSolver.to_geojson` and `loop_closed_survey_to_geojson` accept the
same keyword, using the solved positions rather than unadjusted propagation.

The callback receives an immutable `openspeleo_lib.ResolvedShot` with `uuid`,
`shot_id`, `from_id`, `namespace`, `length_m`, `azimuth`, `comment`,
`longitude`, and `latitude`. It visits resolved, non-excluded REAL shots,
including shots without a comment. START, VIRTUAL, CLOSURE, and unanchored
records do not emit callbacks. Comments are preserved in full. Bearings are
native measured degrees, before magnetic correction, traversal reversal, or loop
closure. Lengths are converted to metres. Positions are WGS84 longitude/latitude
at the native TO end.

For Ariane, IDs come from native `ID` and `FromID`, and UUID is optional. The
namespace is empty because those numeric IDs are survey-wide. The exporter does
not manufacture UUIDs for callbacks.

For Stalagmight, IDs come from native SQLite shot rows rather than the adapter's
generated traversal numbers. The predecessor is the previous native row in
implicit topology. Explicit topology follows the permanent-number origin graph,
including retired ancestry, back to a live native row. Roots use
`section:<native section ID>:root`. Row IDs remain the identity representation
across supported native schema upgrades; permanent graph numbers do not replace
them. Native UUIDs are returned unchanged even when they cannot populate the
common model's UUID field. They are not guaranteed unique across sections, so a
consumer must decide how to handle ambiguity. The namespace is empty because
native row IDs are survey-wide.

The Stalagmight adapter stores immutable `ShotSource` provenance in
`Shot.source_identity`, including the original endpoint orientation. It survives
loop-closure snapshots as explicit immutable evidence; downstream conversion
never reopens the native reader. It is excluded from ordinary OSPL JSON and
Ariane XML exports, preserving their existing contracts. Reversing a shot during
graph traversal therefore cannot move its annotation to the opposite endpoint.
Separate native station comments remain outside this shot-comment contract.

Callbacks run after the complete feature collection is built. Callback
exceptions propagate to the caller. Collect results in memory and persist them
only after the exporter and application publication succeed; the library does
not provide database transactions or deduplication. Native identity changes can
require application reconciliation; a UUID alone is not a universal continuity
guarantee.

The additional pass is linear in source shots and runs only when a callback is
supplied. `tests/test_resolved_shots.py` exercises native IDs, measured units,
exclusion, schema transitions, and original destinations after reversed
traversal and loop closure.
