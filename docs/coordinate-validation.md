# Coordinate validation

## Explicit coordinates and comments

Ariane's `Latitude` and `Longitude` fields contain decimal degrees. Provided
latitude must be finite and in `[-90, 90]`; longitude must be finite and in
`[-180, 180]`. The aliased Ariane models preserve base-model field constraints,
defaults, factories, exclusions, and validators. Missing coordinates retain the
existing anchor-selection behavior; parsing does not require a geographic anchor.

Comments remain opaque descriptive text. Coordinate-looking text, UTM zone
numbers, and declination values in comments do not influence anchors, geographic
propagation, or magnetic declination. The library does not infer a correction or
silently wrap, clamp, offset, or swap invalid coordinates. Verify the explicit
fields against the original GPS record, including its coordinate system and datum.

## Diagnostics

`ArianeInterface.from_file()` preserves the original Pydantic `ValidationError`
and its structured `errors()` API. Invalid coordinates add Python exception notes
(`__notes__`), for example:

```text
Section 'Synthetic anchors', station 'ANCHOR0' [Shot ID='0']: longitude='-183'; expected a finite value in [-180, 180] degrees. Verify the explicit coordinate field against the original GPS record.
```

Notes identify individual invalid fields across all stations. At most 100 notes
are included, followed by an omitted-field count when needed. Labels and values
are limited to 120 characters and escaped onto a single line. Applications can
show these notes without exposing the full input records in Pydantic's default
traceback. Escape them as text in HTML. Unexpected exceptions should remain in
server logs rather than being returned to users.

## Validation versus conversion

`openspeleo validate_tml -i survey.tml` validates parsing and the survey models,
including coordinate ranges. It does not certify geographic accuracy or require
all the inputs needed to generate a map. `openspeleo convert -i survey.tml -o
survey.geojson -f geojson` additionally requires usable anchors and performs the
existing 500-metre consistency check for connected explicit endpoints.

A parsing or geometric validation failure leaves CLI output untouched, including
when `--overwrite` is supplied. Existing valid Ariane files retain their normal
round-trip behavior. An upload application should persist source data independently
and perform conversion after its source commit is durably published; invalid map
data must not invalidate an otherwise successful source upload.

## Regression coverage

Synthetic tests cover all four invalid anchors, coordinate boundaries and
non-finite values, aliased/base-model validation parity, nested default factories,
excluded back-references, inherited validators, CLI no-create/no-overwrite behavior,
and comment isolation. Existing round-trip and coordinate-discrepancy tests remain
part of the full suite. Real user surveys are not committed as test fixtures.
