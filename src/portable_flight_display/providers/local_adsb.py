"""Local readsb aircraft.json provider for an RTL-SDR ADS-B receiver."""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from portable_flight_display.core.models import Aircraft, Location
from portable_flight_display.providers.adsb_base import ADSBPointProvider, ADSBProviderError
from portable_flight_display.providers.base import FlightDataProvider

logger = logging.getLogger(__name__)


class LocalAdsbProvider(FlightDataProvider):
    """Read aircraft decoded by readsb from its local aircraft.json output.

    readsb atomically refreshes this file (normally once per second). Reading it
    directly avoids exposing a network port and avoids all third-party API calls.
    """

    name = "Local ADS-B (readsb)"

    def __init__(self, aircraft_json_path: str | Path = "/run/readsb/aircraft.json") -> None:
        self.aircraft_json_path = Path(aircraft_json_path).expanduser()

    @staticmethod
    def _decode(payload: Any) -> list[Aircraft]:
        if not isinstance(payload, dict):
            raise ADSBProviderError("readsb aircraft.json root must be a JSON object")
        rows = payload.get("aircraft")
        if not isinstance(rows, list):
            raise ADSBProviderError("readsb aircraft.json does not contain an aircraft array")
        aircraft: list[Aircraft] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = ADSBPointProvider.map_aircraft(row)
            if item is not None:
                aircraft.append(item)
        return aircraft

    def _read_payload(self) -> dict[str, Any]:
        try:
            raw = self.aircraft_json_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ADSBProviderError(
                f"readsb aircraft file not found: {self.aircraft_json_path}. "
                "Is readsb installed and running?"
            ) from exc
        except OSError as exc:
            raise ADSBProviderError(
                f"Cannot read readsb aircraft file {self.aircraft_json_path}: {exc}"
            ) from exc
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ADSBProviderError(
                f"readsb aircraft file contains invalid JSON: {self.aircraft_json_path}"
            ) from exc
        if not isinstance(payload, dict):
            raise ADSBProviderError("readsb aircraft.json root must be a JSON object")
        return payload

    async def get_aircraft_nearby(
        self, location: Location, radius_km: float
    ) -> list[Aircraft]:
        # readsb writes aircraft.json using an atomic rename, so this read should
        # never observe a partially written JSON document.
        payload = await asyncio.to_thread(self._read_payload)
        aircraft = self._decode(payload)
        logger.debug(
            "Read %d positioned aircraft from %s (radius filtering follows in FlightProcessor)",
            len(aircraft), self.aircraft_json_path,
        )
        return aircraft

    async def close(self) -> None:
        return None
