"""FlightSight collector.

Reads /run/readsb/aircraft.json on a fixed interval and writes new
position reports into the SQLite database. Designed to run forever
under systemd.
"""

import json
import math
import signal
import sqlite3
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import config_local as config
except ImportError:
    print("ERROR: config_local.py not found.", file=sys.stderr)
    sys.exit(1)

from flightsight import db


_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in nautical miles."""
    R_NM = 3440.065
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R_NM * c


def upsert_aircraft(conn: sqlite3.Connection, hex_id: str, now: int,
                    callsign: str | None) -> None:
    """Insert or update the aircraft row, tracking first/last seen."""
    conn.execute(
        """
        INSERT INTO aircraft (hex, first_seen, last_seen, callsign)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(hex) DO UPDATE SET
            last_seen = excluded.last_seen,
            callsign = COALESCE(excluded.callsign, aircraft.callsign)
        """,
        (hex_id, now, now, callsign),
    )


def insert_position(conn: sqlite3.Connection, hex_id: str, ts: int,
                    ac: dict) -> None:
    """Insert one row into positions. Caller has already checked the data."""
    lat = ac.get("lat")
    lon = ac.get("lon")
    distance = None
    if lat is not None and lon is not None:
        distance = haversine_nm(
            config.STATION_LAT, config.STATION_LON, lat, lon
        )

    conn.execute(
        """
        INSERT INTO positions (
            hex, ts, lat, lon, altitude_ft, ground_speed_kt,
            track_deg, vertical_rate, squawk, callsign, rssi, distance_nm
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            hex_id,
            ts,
            lat,
            lon,
            ac.get("alt_baro") if isinstance(ac.get("alt_baro"), int) else None,
            ac.get("gs"),
            ac.get("track"),
            ac.get("baro_rate"),
            ac.get("squawk"),
            (ac.get("flight") or "").strip() or None,
            ac.get("rssi"),
            distance,
        ),
    )


def process_snapshot(conn: sqlite3.Connection, snapshot: dict) -> tuple[int, int]:
    """Process one aircraft.json snapshot. Returns (aircraft_count, positions_logged)."""
    now = int(snapshot.get("now", time.time()))
    aircraft = snapshot.get("aircraft", [])

    positions_logged = 0
    for ac in aircraft:
        hex_id = ac.get("hex")
        if not hex_id:
            continue

        callsign = (ac.get("flight") or "").strip() or None
        upsert_aircraft(conn, hex_id, now, callsign)
        insert_position(conn, hex_id, now, ac)
        positions_logged += 1

    return (len(aircraft), positions_logged)


def main() -> int:
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    db_path = config.DB_PATH
    if not Path(db_path).is_absolute():
        db_path = str(PROJECT_ROOT / db_path)

    print(f"[collector] db={db_path}")
    print(f"[collector] reading {config.AIRCRAFT_JSON_PATH} every "
          f"{config.COLLECTION_INTERVAL_SECONDS}s")
    print(f"[collector] station: {config.STATION_NAME} "
          f"({config.STATION_LAT}, {config.STATION_LON})")

    conn = db.get_connection(db_path)
    db.init_schema(conn)

    last_log = 0
    snapshots = 0
    rows = 0

    while not _shutdown:
        try:
            with open(config.AIRCRAFT_JSON_PATH, "r") as f:
                snapshot = json.load(f)
            ac_count, positions = process_snapshot(conn, snapshot)
            snapshots += 1
            rows += positions
        except FileNotFoundError:
            print(f"[collector] {config.AIRCRAFT_JSON_PATH} not found, "
                  "is readsb running?", file=sys.stderr)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[collector] read error: {e}", file=sys.stderr)

        now = int(time.time())
        if now - last_log >= 60:
            print(f"[collector] {snapshots} snapshots, {rows} positions logged "
                  "in last minute")
            snapshots = 0
            rows = 0
            last_log = now

        for _ in range(config.COLLECTION_INTERVAL_SECONDS * 10):
            if _shutdown:
                break
            time.sleep(0.1)

    print("[collector] shutdown")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
