"""Check random section trees against independently known station positions."""

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from openspeleo_lib.constants import OSPL_GEOJSON_DIGIT_PRECISION
from openspeleo_lib.geojson import GEOD
from openspeleo_lib.geojson import survey_to_geojson
from openspeleo_lib.interfaces import StalagmightInterface
from tests.stalagmight_helpers import write_stalx


@st.composite
def section_trees(draw):
    section_ids = sorted(
        draw(st.lists(st.integers(0, 100000), min_size=1, max_size=6, unique=True))
    )
    counts = draw(
        st.lists(
            st.integers(0, 4), min_size=len(section_ids), max_size=len(section_ids)
        )
    )
    sections = [
        {
            "id": section_id,
            "direction": draw(st.sampled_from(["in", "out"])),
            "shots": [{} for _ in range(count)],
        }
        for section_id, count in zip(section_ids, counts, strict=True)
    ]
    offsets = [0]
    merges = []
    for child in range(1, len(section_ids)):
        parent = draw(st.integers(0, child - 1))
        parent_station = draw(st.integers(0, counts[parent]))
        child_station = draw(st.integers(0, counts[child]))
        offsets.append(offsets[parent] + parent_station - child_station)
        merges.append(
            (
                child,
                section_ids[parent],
                parent_station,
                section_ids[child],
                child_station,
                "2026-01-01T00:00:00Z",
            )
        )
    anchor_section = draw(st.integers(0, len(section_ids) - 1))
    anchor_station = draw(st.integers(0, counts[anchor_section]))
    anchor_offset = offsets[anchor_section] + anchor_station
    datum = (1, section_ids[anchor_section], anchor_station, 1.0, 1.0, 0.0)
    return sections, counts, offsets, anchor_offset, datum, merges


@settings(max_examples=75)
@given(section_trees())
def test_random_tree_preserves_every_station_attachment(tree):
    sections, counts, offsets, anchor_offset, datum, merges = tree
    with TemporaryDirectory(prefix="sdb-stalagmight-tree-") as directory:
        source = write_stalx(
            Path(directory) / "tree.stalx", sections, datums=[datum], merges=merges
        )
        actual = survey_to_geojson(StalagmightInterface.from_file(source))
        repeated = survey_to_geojson(StalagmightInterface.from_file(source))
    assert repeated == actual
    features = {feature["properties"]["id"]: feature for feature in actual["features"]}
    shot_count = sum(counts)
    assert len(features) == shot_count + 1
    assert set(features) == set(range(shot_count + 1))
    assert features[shot_count]["geometry"]["type"] == "Point"
    assert tuple(features[shot_count]["geometry"]["coordinates"]) == (1.0, 1.0)

    # Independently project the expected station offsets from the common anchor.
    export_id = 0
    for offset, count in zip(offsets, counts, strict=True):
        for sequence in range(count):
            ticks = offset + sequence - anchor_offset
            expected = set()
            for station_offset in (ticks, ticks + 1):
                longitude, latitude, _ = GEOD.fwd(1.0, 1.0, 90.0, station_offset * 10.0)
                expected.add(
                    (
                        round(longitude, OSPL_GEOJSON_DIGIT_PRECISION),
                        round(latitude, OSPL_GEOJSON_DIGIT_PRECISION),
                    )
                )
            geometry = features[export_id]["geometry"]
            assert geometry["type"] == "LineString"
            assert {tuple(point) for point in geometry["coordinates"]} == expected
            export_id += 1
