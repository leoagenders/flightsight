"""Database schema and connection helpers for FlightSight."""

import sqlite3
import os
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS aircraft (
    hex             TEXT PRIMARY KEY,
    first_seen      INTEGER NOT NULL,
    last_seen       INTEGER NOT NULL,
    callsign        TEXT,
    registration    TEXT,
    aircraft_type   TEXT,
    operator        TEXT,
    is_military     INTEGER DEFAULT 0,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS positions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    hex             TEXT NOT NULL,
    ts              INTEGER NOT NULL,
    lat             REAL,
    lon             REAL,
    altitude_ft     INTEGER,
    ground_speed_kt REAL,
    track_deg       REAL,
    vertical_rate   INTEGER,
    squawk          TEXT,
    callsign        TEXT,
    rssi            REAL,
    distance_nm     REAL,
    FOREIGN KEY (hex) REFERENCES aircraft(hex)
);

CREATE INDEX IF NOT EXISTS idx_positions_hex      ON positions(hex);
CREATE INDEX IF NOT EXISTS idx_positions_ts       ON positions(ts);
CREATE INDEX IF NOT EXISTS idx_positions_hex_ts   ON positions(hex, ts);
CREATE INDEX IF NOT EXISTS idx_aircraft_last_seen ON aircraft(last_seen);

CREATE TABLE IF NOT EXISTS events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              INTEGER NOT NULL,
    hex             TEXT,
    event_type      TEXT NOT NULL,
    severity        TEXT DEFAULT 'info',
    details         TEXT,
    notified        INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_events_ts        ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_type      ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_notified  ON events(notified);
"""


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open a connection with sensible defaults for our workload."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Apply the schema. Idempotent thanks to IF NOT EXISTS."""
    conn.executescript(SCHEMA)
