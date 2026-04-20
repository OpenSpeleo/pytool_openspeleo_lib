"""Station name to ID mapping for Compass data.

Compass uses string station names while OSPL uses integer IDs.
This module provides bidirectional mapping between the two systems.
"""

from __future__ import annotations


class StationMapper:
    """Maps station names to sequential integer IDs.

    Compass uses string station names (e.g., "A1", "B2", "ENTRANCE")
    while OSPL uses integer station IDs. This class provides bidirectional
    mapping that preserves the original station names.

    The first station encountered gets ID 0, and IDs increment sequentially.
    """

    def __init__(self) -> None:
        self._name_to_id: dict[str, int] = {}
        self._id_to_name: dict[int, str] = {}
        self._next_id: int = 0

    def get_or_create_id(self, name: str) -> int:
        """Get the ID for a station name, creating one if needed.

        Args:
            name: The station name to look up or register.

        Returns:
            The integer ID for this station name.
        """
        if name not in self._name_to_id:
            self._name_to_id[name] = self._next_id
            self._id_to_name[self._next_id] = name
            self._next_id += 1
        return self._name_to_id[name]

    def get_id(self, name: str) -> int | None:
        """Get the ID for a station name, or None if not found.

        Args:
            name: The station name to look up.

        Returns:
            The integer ID for this station name, or None if not registered.
        """
        return self._name_to_id.get(name)

    def get_name(self, station_id: int) -> str | None:
        """Get the station name for an ID.

        Args:
            station_id: The integer ID to look up.

        Returns:
            The station name for this ID, or None if not found.
        """
        return self._id_to_name.get(station_id)

    def __len__(self) -> int:
        """Return the number of registered stations."""
        return len(self._name_to_id)

    def __contains__(self, name: str) -> bool:
        """Check if a station name is registered."""
        return name in self._name_to_id

    @property
    def names(self) -> list[str]:
        """Return all registered station names in order of registration."""
        return [self._id_to_name[i] for i in range(len(self._id_to_name))]

    @property
    def name_to_id(self) -> dict[str, int]:
        """Return a copy of the name to ID mapping."""
        return dict(self._name_to_id)

    @property
    def id_to_name(self) -> dict[int, str]:
        """Return a copy of the ID to name mapping."""
        return dict(self._id_to_name)
