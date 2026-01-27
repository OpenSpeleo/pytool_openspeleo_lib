"""Tests for orphan and cycle detection in GeoJSON conversion."""

from __future__ import annotations

import logging
import unittest

from openspeleo_lib.geojson import (
    _classify_invalid_shots,
    build_shot_graph,
    find_valid_shot_ids,
)
from openspeleo_lib.enums import ArianeShotType
from openspeleo_lib.models import Shot


def make_shot(
    id_stop: int,
    id_start: int = -1,
    latitude: float | None = None,
    longitude: float | None = None,
    shot_type: ArianeShotType = ArianeShotType.REAL,
) -> Shot:
    """Helper to create a minimal Shot for testing."""
    return Shot(
        id_stop=id_stop,
        id_start=id_start,
        length=1.0,
        depth=0.0,
        azimuth=0.0,
        latitude=latitude,
        longitude=longitude,
        shot_type=shot_type,
    )


class TestFindValidShotIds(unittest.TestCase):
    """Test suite for find_valid_shot_ids function."""

    def test_all_shots_connected_to_anchor(self):
        """All shots connected to anchor should be valid."""
        # Anchor (0) -> 1 -> 2 -> 3
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),  # Anchor
            1: make_shot(1, id_start=0),
            2: make_shot(2, id_start=1),
            3: make_shot(3, id_start=2),
        }
        graph = {0: [1], 1: [2], 2: [3]}

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, {0, 1, 2, 3})

    def test_simple_orphan_no_origin(self):
        """Shot with no origin (id_start=-1) and no coordinates is an orphan."""
        # Anchor (0) -> 1
        # Orphan (2) has id_start=-1 but no coordinates
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),  # Anchor
            1: make_shot(1, id_start=0),
            2: make_shot(2, id_start=-1),  # Orphan - no origin, no coords
        }
        graph = {0: [1]}  # Shot 2 is not in graph as it has no origin

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, {0, 1})
        self.assertNotIn(2, valid_ids)

    def test_orphan_missing_parent(self):
        """Shot pointing to non-existent parent is orphan."""
        # Anchor (0) -> 1
        # Shot 3 points to shot 99 which doesn't exist
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),
            1: make_shot(1, id_start=0),
            3: make_shot(3, id_start=99),  # Parent 99 doesn't exist
        }
        graph = {0: [1], 99: [3]}  # 99 is in graph but not in shots_map

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, {0, 1})
        self.assertNotIn(3, valid_ids)

    def test_recursive_orphan_chain(self):
        """A -> B -> None: both A and B should be removed (recursive orphan)."""
        # Anchor (0) -> 1
        # Orphan chain: 3 -> 2 -> None (2 has no valid origin)
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),
            1: make_shot(1, id_start=0),
            2: make_shot(2, id_start=-1),  # No origin
            3: make_shot(3, id_start=2),  # Points to orphan 2
        }
        # Shot 2 has no origin so it's not in the graph as a destination
        # Shot 3 points to 2, but 2 is not reachable from anchor
        graph = {0: [1], 2: [3]}

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, {0, 1})
        self.assertNotIn(2, valid_ids)  # Orphan
        self.assertNotIn(3, valid_ids)  # Recursive orphan

    def test_simple_cycle_two_nodes(self):
        """A -> B -> A: both should be removed if not connected to anchor."""
        # Anchor (0) -> 1
        # Cycle: 2 -> 3 -> 2 (isolated from anchor)
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),
            1: make_shot(1, id_start=0),
            2: make_shot(2, id_start=3),  # Points to 3
            3: make_shot(3, id_start=2),  # Points to 2 - cycle!
        }
        graph = {0: [1], 2: [3], 3: [2]}

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, {0, 1})
        self.assertNotIn(2, valid_ids)
        self.assertNotIn(3, valid_ids)

    def test_cycle_three_nodes(self):
        """A -> B -> C -> A: all three should be removed if isolated."""
        # Anchor (0) -> 1
        # Cycle: 2 -> 3 -> 4 -> 2 (isolated)
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),
            1: make_shot(1, id_start=0),
            2: make_shot(2, id_start=4),  # Points to 4
            3: make_shot(3, id_start=2),  # Points to 2
            4: make_shot(4, id_start=3),  # Points to 3 - completes cycle
        }
        graph = {0: [1], 2: [3], 3: [4], 4: [2]}

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, {0, 1})
        self.assertNotIn(2, valid_ids)
        self.assertNotIn(3, valid_ids)
        self.assertNotIn(4, valid_ids)

    def test_cycle_connected_to_anchor_is_valid(self):
        """Cycle that IS connected to anchor should be valid."""
        # Anchor (0) -> 1 -> 2 -> 3 -> 2 (cycle, but reachable from anchor)
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),
            1: make_shot(1, id_start=0),
            2: make_shot(2, id_start=1),
            3: make_shot(3, id_start=2),
        }
        # Note: 3 points back to 2, creating a cycle, but all are reachable from 0
        graph = {0: [1], 1: [2], 2: [3], 3: [2]}

        valid_ids = find_valid_shot_ids(shots_map, graph)

        # All should be valid because they're reachable from anchor
        self.assertEqual(valid_ids, {0, 1, 2, 3})

    def test_mixed_valid_orphan_and_cycle(self):
        """Complex scenario with valid shots, orphans, and cycles."""
        # Valid chain: Anchor (0) -> 1 -> 2
        # Orphan chain: 3 -> 4 -> None
        # Isolated cycle: 5 -> 6 -> 7 -> 5
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),  # Anchor
            1: make_shot(1, id_start=0),  # Valid
            2: make_shot(2, id_start=1),  # Valid
            3: make_shot(3, id_start=4),  # Orphan chain
            4: make_shot(4, id_start=-1),  # No origin, no coords
            5: make_shot(5, id_start=7),  # Cycle
            6: make_shot(6, id_start=5),  # Cycle
            7: make_shot(7, id_start=6),  # Cycle
        }
        graph = {0: [1], 1: [2], 4: [3], 5: [6], 6: [7], 7: [5]}

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, {0, 1, 2})
        # Orphans
        self.assertNotIn(3, valid_ids)
        self.assertNotIn(4, valid_ids)
        # Cycle
        self.assertNotIn(5, valid_ids)
        self.assertNotIn(6, valid_ids)
        self.assertNotIn(7, valid_ids)

    def test_no_anchor_returns_empty(self):
        """If no anchor exists, all shots are invalid."""
        shots_map = {
            0: make_shot(0, id_start=-1),  # No coords - not an anchor
            1: make_shot(1, id_start=0),
        }
        graph = {0: [1]}

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, set())

    def test_multiple_anchors(self):
        """Multiple anchors should each define valid regions."""
        # Anchor 0 -> 1
        # Anchor 2 -> 3
        # Orphan 4
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),
            1: make_shot(1, id_start=0),
            2: make_shot(2, id_start=-1, latitude=46.0, longitude=-123.0),
            3: make_shot(3, id_start=2),
            4: make_shot(4, id_start=-1),  # No coords
        }
        graph = {0: [1], 2: [3]}

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, {0, 1, 2, 3})
        self.assertNotIn(4, valid_ids)

    def test_branching_tree(self):
        """Anchor with branching children should all be valid."""
        # Anchor (0) -> 1, 2
        #     1 -> 3, 4
        #     2 -> 5
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),
            1: make_shot(1, id_start=0),
            2: make_shot(2, id_start=0),
            3: make_shot(3, id_start=1),
            4: make_shot(4, id_start=1),
            5: make_shot(5, id_start=2),
        }
        graph = {0: [1, 2], 1: [3, 4], 2: [5]}

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, {0, 1, 2, 3, 4, 5})

    def test_empty_survey(self):
        """Empty survey should return empty set."""
        shots_map = {}
        graph = {}

        valid_ids = find_valid_shot_ids(shots_map, graph)

        self.assertEqual(valid_ids, set())


class TestClassifyInvalidShots(unittest.TestCase):
    """Test suite for _classify_invalid_shots function."""

    def test_simple_orphan(self):
        """Shot with no origin is classified as orphan."""
        shots_map = {
            1: make_shot(1, id_start=-1),  # No origin, no coords = orphan
        }
        invalid_ids = {1}

        orphans, cycles = _classify_invalid_shots(invalid_ids, shots_map)

        self.assertEqual(orphans, {1})
        self.assertEqual(cycles, set())

    def test_recursive_orphan(self):
        """Chain leading to orphan should all be classified as orphans."""
        shots_map = {
            1: make_shot(1, id_start=-1),  # Root orphan
            2: make_shot(2, id_start=1),  # Points to orphan
            3: make_shot(3, id_start=2),  # Points to orphan chain
        }
        invalid_ids = {1, 2, 3}

        orphans, cycles = _classify_invalid_shots(invalid_ids, shots_map)

        self.assertEqual(orphans, {1, 2, 3})
        self.assertEqual(cycles, set())

    def test_simple_cycle(self):
        """Two-node cycle should be classified as cycle."""
        shots_map = {
            1: make_shot(1, id_start=2),
            2: make_shot(2, id_start=1),
        }
        invalid_ids = {1, 2}

        orphans, cycles = _classify_invalid_shots(invalid_ids, shots_map)

        self.assertEqual(cycles, {1, 2})
        self.assertEqual(orphans, set())

    def test_three_node_cycle(self):
        """Three-node cycle should all be classified as cycle."""
        shots_map = {
            1: make_shot(1, id_start=3),
            2: make_shot(2, id_start=1),
            3: make_shot(3, id_start=2),
        }
        invalid_ids = {1, 2, 3}

        orphans, cycles = _classify_invalid_shots(invalid_ids, shots_map)

        self.assertEqual(cycles, {1, 2, 3})
        self.assertEqual(orphans, set())

    def test_orphan_leading_to_cycle(self):
        """Orphan chain leading to a cycle: chain is orphan, cycle is cycle."""
        # 4 -> 3 -> (1 <-> 2) cycle
        shots_map = {
            1: make_shot(1, id_start=2),  # Cycle
            2: make_shot(2, id_start=1),  # Cycle
            3: make_shot(3, id_start=1),  # Leads to cycle
            4: make_shot(4, id_start=3),  # Leads to cycle via 3
        }
        invalid_ids = {1, 2, 3, 4}

        orphans, cycles = _classify_invalid_shots(invalid_ids, shots_map)

        self.assertEqual(cycles, {1, 2})
        self.assertEqual(orphans, {3, 4})

    def test_missing_parent(self):
        """Shot pointing to non-existent parent is orphan."""
        shots_map = {
            1: make_shot(1, id_start=99),  # Parent doesn't exist
        }
        invalid_ids = {1}

        orphans, cycles = _classify_invalid_shots(invalid_ids, shots_map)

        self.assertEqual(orphans, {1})
        self.assertEqual(cycles, set())


class TestWarningLogging(unittest.TestCase):
    """Test that warnings are logged for orphans and cycles."""

    def test_orphan_warning_logged(self):
        """Orphan shots should trigger warning logs."""
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),
            1: make_shot(1, id_start=0),
            2: make_shot(2, id_start=-1),  # Orphan
        }
        graph = {0: [1]}

        with self.assertLogs("openspeleo_lib.geojson", level=logging.WARNING) as cm:
            find_valid_shot_ids(shots_map, graph)

        # Check that orphan warning was logged
        self.assertTrue(
            any("Orphan shot detected" in msg for msg in cm.output),
            f"Expected orphan warning in logs: {cm.output}",
        )

    def test_cycle_warning_logged(self):
        """Cycle shots should trigger warning logs."""
        shots_map = {
            0: make_shot(0, id_start=-1, latitude=45.0, longitude=-122.0),
            1: make_shot(1, id_start=0),
            2: make_shot(2, id_start=3),  # Cycle
            3: make_shot(3, id_start=2),  # Cycle
        }
        graph = {0: [1], 2: [3], 3: [2]}

        with self.assertLogs("openspeleo_lib.geojson", level=logging.WARNING) as cm:
            find_valid_shot_ids(shots_map, graph)

        # Check that cycle warning was logged
        self.assertTrue(
            any("Cycle detected" in msg for msg in cm.output),
            f"Expected cycle warning in logs: {cm.output}",
        )


if __name__ == "__main__":
    unittest.main()
