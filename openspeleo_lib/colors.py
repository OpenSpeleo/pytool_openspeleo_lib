"""Normalize source shot colors for portable GeoJSON rendering."""

from __future__ import annotations

from pydantic_extra_types.color import Color


def normalize_shot_color(value: object) -> str | None:
    """Convert JavaFX/CSS colors without altering their source representation.

    JavaFX's ``0xRRGGBBAA`` uses trailing alpha, not ARGB. Invalid colors are
    absent display metadata, not grounds to reject otherwise valid geometry.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    value = value.strip()
    if value.lower().startswith("0x"):
        value = "#" + value[2:]
    try:
        color = Color(value)
    except ValueError:
        return None
    red, green, blue, alpha = color.as_rgb_tuple(alpha=True)
    if alpha == 1:
        return f"#{red:02x}{green:02x}{blue:02x}"
    opacity = f"{alpha:.8f}".rstrip("0").rstrip(".")
    return f"rgba({red},{green},{blue},{opacity})"
