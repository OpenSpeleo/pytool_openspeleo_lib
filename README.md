# OpenSpeleoLib

OpenSpeleoLib reads, writes, validates, and converts cave-survey data.

## GeoJSON conversion

Convert an Ariane TML survey with:

```console
openspeleo convert -i survey.tml -o survey.geojson -f geojson
```

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
