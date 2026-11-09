# OpenSpeleoLib

OpenSpeleoLib reads, writes, validates, and converts cave-survey data.

## GeoJSON conversion

Convert an Ariane TML survey with:

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

## StalagMight input

```python
from openspeleo_lib.interfaces import StalagMightInterface
from openspeleo_lib.geojson import survey_to_geojson

survey = StalagMightInterface.from_file("survey.stalx")
geojson = survey_to_geojson(survey)
```

```sh
openspeleo convert -i survey.STALX -o survey.geojson -f geojson --beautify
openspeleo convert -i survey.stalx -o normalized.json -f json
```

`stalagmight_lib.read_stalx()` owns SQLite parsing and validates immutable
native models, including datums and station merges. `StalagMightInterface`
translates these models into OpenSpeleo's common survey; `survey_to_geojson()`
remains the shared exporter. Native writing is unsupported. The `stalagmight`
CLI exports native-model JSON, which intentionally differs from OpenSpeleo's
normalized JSON.

Sections retain their names (including duplicates), dates, surveyor text,
colors, shot comments, and nullable LRUD. Null section names become
`Section {id}`. Station comments remain native metadata. Units are metres.
Normal shots map to REAL; jump/reference shots map to VIRTUAL and position
downstream shots without producing features.

The adapter builds a deterministic section spanning forest. Each component roots
at its lowest-ID datum's actual station, otherwise its lowest section ID. Merges
attach children at actual station indices, including middle and final stations.
Shots point outward from attachments; middle attachments create two branches.
Reversal swaps start/end depths and left/right, adds 180 degrees to
`azimuth_in`, and negates inclination. Native shot values are unchanged.
Additional merge constraints remain available in native metadata and trigger a
warning that no closure adjustment was applied.

Bearings use `azimuth_in` plus recorded section correction when section north
metadata is present (a null correction means zero); otherwise they inherit
project correction, or zero. No IGRF calculation or date is required. Direction
`out` alone does not reverse a section. Native pitch is negated into common
inclination. Each shot uses its own `depth_start` for horizontal projection,
supporting depth discontinuities. Impossible individual geometry fails with
native row ID, section ID, and sequence. The unchanged bundled example fails at
shot 282; the integration test adjusts only its length in a temporary copy and
expects 467 LineStrings and one START Point.

Graph IDs are deterministic nonnegative export identifiers allocated in section
ID/native sequence order, plus synthetic component START nodes. They do not
replace native database IDs. The first occurrence of each valid v4 shot UUID
supplies the optional feature ID; repeated or unsupported UUIDs are omitted,
without generating replacements. Zero coordinates are valid anchors. Conflicting
datums at the same graph node are rejected; other explicit anchors use the
shared 500-metre consistency guardrail. Unanchored components follow shared
filtering, and surveys without anchors raise `NoKnownAnchorError`.

GeoJSON keeps the existing FeatureCollection, Point/LineString geometries,
precision, depth conversion, feature IDs, section names, normalized colors, and
filtering conventions. Native-only metadata adds no map properties. Native
section offsets, station moves, adjusted geometry, and loop-closure corrections
are not reproduced. Parsing and geometry finish before output is opened; failure
preserves new and existing output. Symlink and hardlink source aliases are
refused.

Standalone installs use the published reader dependency declared in
`pyproject.toml` and pinned in `uv.lock`. Local integration uses the root
editable `stalagmight_lib` source. Validate frozen sync, tests, lint, and
packaging in the standalone environment as well as the root integration
environment.
