"""Shared adapter for ADS-B Exchange-compatible community APIs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
from typing import Any

import httpx

from portable_flight_display.core.models import Aircraft, Location
from portable_flight_display.providers.base import FlightDataProvider


class ADSBProviderError(RuntimeError):
    """Raised when a community ADS-B provider cannot return aircraft data."""


class ADSBPointProvider(FlightDataProvider):
    """Maps a point/radius ADS-B response into the application's Aircraft model."""

    name = "ADS-B provider"

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 12,
        api_key: str | None = None,
        max_radius_nm: float = 250,
    ) -> None:
        headers = {"Accept": "application/json", "User-Agent": "PortableFlightDisplay/0.1"}
        if api_key:
            headers["x-api-key"] = api_key
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers=headers,
            timeout=timeout_seconds,
        )
        self.max_radius_nm = max(1.0, min(float(max_radius_nm), 250.0))

    @staticmethod
    def radius_nm(radius_km: float) -> int:
        # Both public point APIs document an integer nautical-mile path parameter.
        return max(1, math.ceil(radius_km / 1.852))

    @staticmethod
    def _number(value: Any) -> float | None:
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.strip())
            except ValueError:
                return None
        return None

    @classmethod
    def map_aircraft(cls, row: dict[str, Any]) -> Aircraft | None:
        """Map the common ADSBexchange/readsb aircraft response shape."""
        try:
            last_position = row.get("lastPosition") or {}
            lat = cls._number(row.get("lat"))
            lon = cls._number(row.get("lon"))
            if lat is None:
                lat = cls._number(last_position.get("lat"))
            if lon is None:
                lon = cls._number(last_position.get("lon"))
            if lat is None or lon is None:
                return None

            seen_pos = cls._number(row.get("seen_pos"))
            if seen_pos is None:
                seen_pos = cls._number(last_position.get("seen_pos"))
            if seen_pos is None:
                seen_pos = cls._number(row.get("seen"))
            seen_pos = max(0.0, seen_pos or 0.0)
            position_time = datetime.now(timezone.utc) - timedelta(seconds=seen_pos)

            baro_altitude = row.get("alt_baro")
            geom_altitude = row.get("alt_geom")
            altitude = cls._number(baro_altitude)
            if altitude is None:
                altitude = cls._number(geom_altitude)

            vertical_rate = cls._number(row.get("baro_rate"))
            if vertical_rate is None:
                vertical_rate = cls._number(row.get("geom_rate"))
            altitude_change = (
                "climbing" if vertical_rate and vertical_rate > 0
                else "descending" if vertical_rate and vertical_rate < 0
                else "level" if vertical_rate == 0
                else None
            )
            callsign = str(row.get("flight") or "").strip() or None
            hex_code = str(row.get("hex") or "").strip().lower() or None
            ground = isinstance(baro_altitude, str) and baro_altitude.lower() == "ground"

            return Aircraft(
                flight_id=hex_code or callsign or f"adsb-{lat:.5f}-{lon:.5f}",
                ident=callsign,
                callsign=callsign,
                icao_hex=hex_code,
                registration=row.get("r"),
                aircraft_type=row.get("t"),
                latitude=lat,
                longitude=lon,
                altitude_ft=round(altitude) if altitude is not None else None,
                groundspeed_kts=cls._number(row.get("gs")),
                heading_deg=cls._number(row.get("track")),
                altitude_change=altitude_change,
                vertical_rate_fpm=round(vertical_rate) if vertical_rate is not None else None,
                squawk=str(row.get("squawk")) if row.get("squawk") is not None else None,
                category=row.get("category"),
                status="ground" if ground else "airborne",
                position_age_seconds=round(seen_pos, 1),
                position_timestamp=position_time,
            )
        except (TypeError, ValueError, OverflowError):
            return None

    async def _get(self, path: str) -> list[Aircraft]:
        try:
            response = await self.client.get(path)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "not supplied")
                raise ADSBProviderError(
                    f"{self.name} rate limit reached (Retry-After: {retry_after})"
                )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise ADSBProviderError(
                f"{self.name} returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ADSBProviderError(f"{self.name} request failed: {exc}") from exc
        except ValueError as exc:
            raise ADSBProviderError(f"{self.name} returned invalid JSON") from exc

        rows = (payload.get("ac") or payload.get("aircraft") or []) if isinstance(payload, dict) else []
        return [aircraft for row in rows if (aircraft := self.map_aircraft(row)) is not None]

    async def close(self) -> None:
        await self.client.aclose()
