"""FlightSight configuration template.

Copy this file to config_local.py and fill in your real values:
    cp config_example.py config_local.py

config_local.py is gitignored and never committed.
"""

# Receiver location (use your real coordinates in config_local.py)
STATION_LAT = 0.0
STATION_LON = 0.0
STATION_NAME = "My Station"

# readsb data source
AIRCRAFT_JSON_PATH = "/run/readsb/aircraft.json"
COLLECTION_INTERVAL_SECONDS = 5

# Database
DB_PATH = "data/flightsight.db"

# Web dashboard
WEB_PORT = 5001
WEB_HOST = "0.0.0.0"

# ntfy push notifications (leave NTFY_TOPIC empty to disable)
NTFY_TOPIC = ""
NTFY_SERVER = "https://ntfy.sh"

# Alert thresholds
EMERGENCY_SQUAWKS = {"7500", "7600", "7700"}
LATE_NIGHT_START_HOUR = 23
LATE_NIGHT_END_HOUR = 5
