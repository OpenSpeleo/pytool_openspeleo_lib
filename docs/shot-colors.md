# Shot colors in Ariane GeoJSON

Emitted shot features include optional `properties.color` from the recorded shot
color. JavaFX `0xRRGGBBAA` values use **trailing alpha**, not ARGB. Opaque
colors become CSS `#rrggbb`; transparent colors become `rgba(r,g,b,a)` with
eight decimal places of alpha precision. Supported CSS colors are normalized
through the existing color parser.

Missing or invalid source colors omit the property so viewers can fall back to
their survey/project color. The implicit model default is not treated as a
recorded source color; explicitly setting that same default does export it.
Normalization does not change source model values or the TML representation.
Start-point features receive the same optional metadata as survey legs, while
exclusions, coordinates, depths, IDs, and names keep their existing behavior.

Clients may select this metadata for shot rendering or retain their existing
survey/depth styles. Existing saved GeoJSON must be regenerated to gain shot
colors. Portable tests in `tests/test_shot_colors.py` cover normalization,
per-shot propagation, unavailable-color fallback, geometry stability, and TML
round trips. Legacy private goldens still verify geometry and pre-existing
properties, with color assertions checked separately against source shots.
