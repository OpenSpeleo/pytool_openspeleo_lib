"""Native shot evidence paired with its solved geographic destination."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ResolvedShot:
    uuid: str | None
    shot_id: str
    from_id: str
    namespace: tuple[str, ...]
    length_m: float | None
    azimuth: float | None
    comment: str | None
    longitude: float
    latitude: float
