"""Tests for the StationMapper class."""

from __future__ import annotations

import unittest

from openspeleo_lib.interfaces.compass.station_mapper import StationMapper


class TestStationMapper(unittest.TestCase):
    """Tests for StationMapper bidirectional mapping."""

    def test_empty_mapper(self):
        """Test that a new mapper is empty."""
        mapper = StationMapper()
        assert len(mapper) == 0
        assert mapper.names == []

    def test_get_or_create_first_station(self):
        """Test that the first station gets ID 0."""
        mapper = StationMapper()
        station_id = mapper.get_or_create_id("A1")
        assert station_id == 0

    def test_get_or_create_sequential_ids(self):
        """Test that stations get sequential IDs."""
        mapper = StationMapper()
        id1 = mapper.get_or_create_id("A1")
        id2 = mapper.get_or_create_id("A2")
        id3 = mapper.get_or_create_id("B1")

        assert id1 == 0
        assert id2 == 1
        assert id3 == 2

    def test_get_or_create_returns_same_id(self):
        """Test that requesting the same name returns the same ID."""
        mapper = StationMapper()
        id1 = mapper.get_or_create_id("ENTRANCE")
        id2 = mapper.get_or_create_id("ENTRANCE")

        assert id1 == id2 == 0
        assert len(mapper) == 1

    def test_get_name(self):
        """Test reverse lookup from ID to name."""
        mapper = StationMapper()
        mapper.get_or_create_id("A1")
        mapper.get_or_create_id("A2")

        assert mapper.get_name(0) == "A1"
        assert mapper.get_name(1) == "A2"
        assert mapper.get_name(99) is None

    def test_get_id(self):
        """Test lookup from name to ID without creating."""
        mapper = StationMapper()
        mapper.get_or_create_id("A1")

        assert mapper.get_id("A1") == 0
        assert mapper.get_id("UNKNOWN") is None

    def test_contains(self):
        """Test the in operator for station names."""
        mapper = StationMapper()
        mapper.get_or_create_id("A1")

        assert "A1" in mapper
        assert "B1" not in mapper

    def test_names_property(self):
        """Test that names property returns stations in order."""
        mapper = StationMapper()
        mapper.get_or_create_id("ENTRANCE")
        mapper.get_or_create_id("A1")
        mapper.get_or_create_id("A2")

        assert mapper.names == ["ENTRANCE", "A1", "A2"]

    def test_name_to_id_property(self):
        """Test that name_to_id returns a copy of the mapping."""
        mapper = StationMapper()
        mapper.get_or_create_id("A1")
        mapper.get_or_create_id("A2")

        mapping = mapper.name_to_id
        assert mapping == {"A1": 0, "A2": 1}

        # Verify it's a copy
        mapping["A3"] = 2
        assert "A3" not in mapper

    def test_id_to_name_property(self):
        """Test that id_to_name returns a copy of the mapping."""
        mapper = StationMapper()
        mapper.get_or_create_id("A1")
        mapper.get_or_create_id("A2")

        mapping = mapper.id_to_name
        assert mapping == {0: "A1", 1: "A2"}

        # Verify it's a copy
        mapping[2] = "A3"
        assert mapper.get_name(2) is None

    def test_special_characters_in_names(self):
        """Test that station names with special characters work."""
        mapper = StationMapper()

        id1 = mapper.get_or_create_id("A-1")
        id2 = mapper.get_or_create_id("B_2")
        id3 = mapper.get_or_create_id("C.3")

        assert mapper.get_name(id1) == "A-1"
        assert mapper.get_name(id2) == "B_2"
        assert mapper.get_name(id3) == "C.3"

    def test_numeric_station_names(self):
        """Test that numeric station names work."""
        mapper = StationMapper()

        id1 = mapper.get_or_create_id("1")
        id2 = mapper.get_or_create_id("2")
        id3 = mapper.get_or_create_id("100")

        assert mapper.get_name(id1) == "1"
        assert mapper.get_name(id2) == "2"
        assert mapper.get_name(id3) == "100"


if __name__ == "__main__":
    unittest.main()
