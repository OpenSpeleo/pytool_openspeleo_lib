from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic import ValidationError

MAX_COORDINATE_ERROR_NOTES = 100


def _label(value: object) -> str:
    """Keep diagnostics bounded and on one line; never include whole input records."""
    return repr(str(value)[:120])


def add_coordinate_error_notes(error: ValidationError, data: dict) -> None:
    """Annotate the original exception with actionable, bounded station details.

    Applications can display ``__notes__`` without exposing Pydantic's complete
    input records. Comments are deliberately never read as coordinate sources.
    """
    seen = set()
    for detail in error.errors(include_url=False, include_context=False):
        location = detail["loc"]
        if (
            len(location) != 5
            or location[0] != "sections"
            or location[2] != "shots"
            or location[4] not in {"Latitude", "Longitude", "latitude", "longitude"}
        ):
            continue
        if location in seen:
            continue
        seen.add(location)
        if len(seen) > MAX_COORDINATE_ERROR_NOTES:
            continue
        section = data["sections"][location[1]]
        shot = section["shots"][location[3]]
        field = location[4].lower()
        limit = 90 if field == "latitude" else 180
        error.add_note(
            f"Section {_label(section.get('name', ''))}, "
            f"station {_label(shot.get('Name', shot.get('name', '')))} "
            f"[Shot ID={_label(shot.get('ID', shot.get('id_stop', '?')))}]: "
            f"{field}={_label(detail.get('input'))}; "
            f"expected a finite value in [-{limit}, {limit}] degrees. "
            "Verify the explicit coordinate field against the original GPS record."
        )
    if len(seen) > MAX_COORDINATE_ERROR_NOTES:
        error.add_note(
            f"{len(seen) - MAX_COORDINATE_ERROR_NOTES} additional invalid "
            "coordinate fields omitted from station diagnostics."
        )
