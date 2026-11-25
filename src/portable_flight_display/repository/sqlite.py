import json
import sqlite3
from pathlib import Path
from portable_flight_display.core.models import FlightSnapshot


class SQLiteFlightRepository:
    def __init__(self, database_path: str):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialise()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _initialise(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS flight_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fetched_at TEXT NOT NULL,
                    provider_name TEXT NOT NULL,
                    location_json TEXT NOT NULL,
                    aircraft_json TEXT NOT NULL
                )
            """)

    def save(self, snapshot: FlightSnapshot) -> None:
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO flight_snapshots
                   (fetched_at, provider_name, location_json, aircraft_json)
                   VALUES (?, ?, ?, ?)""",
                (
                    snapshot.fetched_at.isoformat(),
                    snapshot.provider_name,
                    snapshot.location.model_dump_json(),
                    json.dumps([item.model_dump(mode="json") for item in snapshot.aircraft]),
                ),
            )
