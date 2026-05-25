"""One-shot script to initialize the FlightSight database.

Run from the project root:
    python scripts/init_db.py
"""

import sys
from pathlib import Path

# Make the project root importable so `import config_local` and
# `from flightsight import db` both work.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import config_local as config
except ImportError:
    print("ERROR: config_local.py not found.")
    print("Copy config_example.py to config_local.py and fill in your values.")
    sys.exit(1)

from flightsight import db


def main() -> None:
    db_path = config.DB_PATH
    if not Path(db_path).is_absolute():
        db_path = str(PROJECT_ROOT / db_path)

    print(f"Initializing database at: {db_path}")
    conn = db.get_connection(db_path)
    db.init_schema(conn)

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    print("Tables created:")
    for row in tables:
        print(f"  - {row['name']}")

    conn.close()
    print("Done.")


if __name__ == "__main__":
    main()
