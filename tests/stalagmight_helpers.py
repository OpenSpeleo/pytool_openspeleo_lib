"""Independent schema-18 SQLite fixtures for adapter tests."""

import sqlite3
from contextlib import closing

SCHEMA = """
PRAGMA user_version=18;
CREATE TABLE project(id INTEGER, name TEXT, location TEXT, created_at TEXT,
 modified_at TEXT, schema_version INTEGER);
CREATE TABLE sections(id INTEGER, name TEXT, surveyor TEXT, date TEXT,
 color TEXT, direction TEXT, quality REAL, created_at TEXT,
 gauge_shot_uuid TEXT, gauge_neighbour_uuid TEXT, reverse_parity INTEGER,
 azimuth_north TEXT, azimuth_correction REAL, azimuth_source TEXT,
 azimuth_epoch_year INTEGER);
CREATE TABLE shots(id INTEGER, section_id INTEGER, sequence_order INTEGER,
 azimuth_in REAL, azimuth_out REAL, length REAL, depth_in REAL, depth_out REAL,
 pitch_in REAL, pitch_out REAL, left_distance REAL, right_distance REAL,
 up_distance REAL, down_distance REAL, comment TEXT, kind INTEGER,
 marker_index INTEGER, temperature REAL, uuid TEXT);
CREATE TABLE station_comments(section_id INTEGER, station_index INTEGER, comment TEXT);
CREATE TABLE project_settings(key TEXT, value TEXT);
INSERT INTO project VALUES(7, 'Cave', NULL, '2026-01-01T00:00:00+00:00',
 '2026-01-02T00:00:00+00:00', 18);
INSERT INTO sections VALUES(42, 'Repeat', NULL, '2026-01-01', '#abc', 'in',
 1.5, '2026-01-01T00:00:00Z', NULL, NULL, 0, NULL, NULL, NULL, NULL);
INSERT INTO shots VALUES(99, 42, 0, 12.123456789, 14, 0, -1, 20, NULL, 90,
 NULL, 0, 2, 3, NULL, 0, 17, 23.5, NULL);
"""


GEOGRAPHIC_SCHEMA = """
CREATE TABLE zero_datums(id INTEGER, section_id INTEGER, station_index INTEGER,
 latitude REAL, longitude REAL, depth_reference REAL);
CREATE TABLE station_merges(id INTEGER, station_a_section INTEGER,
 station_a_index INTEGER, station_b_section INTEGER, station_b_index INTEGER,
 merged_at TEXT);
"""


def write_stalx(path, sections, datums=(), merges=()):
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.executescript(SCHEMA + GEOGRAPHIC_SCHEMA)
        section_template = dict(
            zip(
                [row[1] for row in conn.execute("PRAGMA table_info(sections)")],
                conn.execute("SELECT * FROM sections").fetchone(),
                strict=True,
            )
        )
        shot_template = dict(
            zip(
                [row[1] for row in conn.execute("PRAGMA table_info(shots)")],
                conn.execute("SELECT * FROM shots").fetchone(),
                strict=True,
            )
        )
        conn.execute("DELETE FROM sections")
        conn.execute("DELETE FROM shots")
        for index, section in enumerate(sections):
            data = {
                **section_template,
                **{k: v for k, v in section.items() if k != "shots"},
            }
            conn.execute(
                "INSERT INTO sections VALUES(" + ",".join("?" for _ in data) + ")",
                tuple(data.values()),
            )
            for sequence, shot in enumerate(section.get("shots", [])):
                data = {
                    **shot_template,
                    "id": index * 100 + sequence,
                    "section_id": section["id"],
                    "sequence_order": sequence,
                    "length": 10.0,
                    "depth_in": 0.0,
                    "depth_out": 0.0,
                    "azimuth_in": 90.0,
                    **shot,
                }
                conn.execute(
                    "INSERT INTO shots VALUES(" + ",".join("?" for _ in data) + ")",
                    tuple(data.values()),
                )
        conn.executemany("INSERT INTO zero_datums VALUES(?,?,?,?,?,?)", datums)
        conn.executemany("INSERT INTO station_merges VALUES(?,?,?,?,?,?)", merges)
    return path
