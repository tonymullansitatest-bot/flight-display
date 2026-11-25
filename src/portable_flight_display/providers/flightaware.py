from datetime import datetime, timezone
import httpx
from portable_flight_display.core.models import Aircraft, Location
from portable_flight_display.flight.geo import GeoCalculator
from portable_flight_display.providers.base import FlightDataProvider


class FlightAwareError(RuntimeError):
    pass


class FlightAwareProvider(FlightDataProvider):
    """AeroAPI v4 airborne-flight search adapter using GET /flights/search."""

    name = "FlightAware AeroAPI"

    def __init__(
        self, api_key: str, base_url: str, timeout_seconds: float = 12,
        max_results: int = 15, max_pages: int = 1, enrich_operator_names: bool = True,
    ):
        if not api_key:
            raise ValueError("FLIGHTAWARE_API_KEY is required for live provider mode")
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/") + "/",
            headers={"x-apikey": api_key, "Accept": "application/json"},
            timeout=timeout_seconds,
        )
        # AeroAPI returns a maximum of 15 records per result set.
        self.max_results = max(1, min(max_results, 15))
        self.max_pages = max(1, max_pages)
        self.enrich_operator_names = enrich_operator_names
        # Cached for the lifetime of this provider to avoid repeated billable lookups.
        self._operator_name_cache: dict[str, tuple[str | None, str | None]] = {}

    @staticmethod
    def build_search_query(location: Location, radius_km: float) -> str:
        min_lat, min_lon, max_lat, max_lon = GeoCalculator.bounding_box(
            location.latitude, location.longitude, radius_km
        )
        # /flights/search uses simplified syntax, not the advanced {range ...} syntax.
        return f'-latlong "{min_lat:.6f} {min_lon:.6f} {max_lat:.6f} {max_lon:.6f}"'

    async def get_aircraft_nearby(
        self, location: Location, radius_km: float
    ) -> list[Aircraft]:
        query = self.build_search_query(location, radius_km)
        try:
            response = await self.client.get(
                "flights/search",
                params={"query": query, "max_pages": self.max_pages},
            )
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "unknown")
                raise FlightAwareError(
                    f"FlightAware rate limit reached (Retry-After: {retry_after})"
                )
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPStatusError as exc:
            raise FlightAwareError(
                f"FlightAware returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            ) from exc
        except httpx.HTTPError as exc:
            raise FlightAwareError(f"FlightAware request failed: {exc}") from exc

        # /flights/search returns {flights, links, num_pages}; unlike the positions
        # endpoint, each flight carries a richer flight object and nested last_position.
        rows = payload.get("flights") or []
        result: list[Aircraft] = []
        for row in rows[: self.max_results]:
            aircraft = self._to_aircraft(row)
            if aircraft is not None:
                result.append(aircraft)

        if self.enrich_operator_names:
            await self._enrich_operator_names(result)
        return result

    async def _enrich_operator_names(self, aircraft_list: list[Aircraft]) -> None:
        """Resolve each distinct ICAO operator once and cache it for this session."""
        codes = sorted({item.operator_code for item in aircraft_list if item.operator_code})
        for code in codes:
            if code in self._operator_name_cache:
                continue
            try:
                response = await self.client.get(f"operators/{code}")
                response.raise_for_status()
                payload = response.json()
                self._operator_name_cache[code] = (
                    payload.get("name"), payload.get("shortname")
                )
            except (httpx.HTTPError, ValueError):
                # Enrichment is optional: keep the operator code and flight results.
                continue

        for item in aircraft_list:
            if item.operator_code and item.operator_code in self._operator_name_cache:
                name, shortname = self._operator_name_cache[item.operator_code]
                item.airline = shortname or name or item.airline
                item.operator_shortname = shortname

    @staticmethod
    def _parse_datetime(value) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        return None

    @classmethod
    def _to_aircraft(cls, row: dict) -> Aircraft | None:
        """Map AeroAPI InFlightStatus. last_position altitude is in hundreds of feet."""
        try:
            position = row.get("last_position") or {}
            # Keep direct fields as a defensive compatibility path for fixtures/adapters.
            lat = position.get("latitude", row.get("latitude"))
            lon = position.get("longitude", row.get("longitude"))
            if lat is None or lon is None:
                return None

            altitude_raw = position.get("altitude", row.get("altitude"))
            # AeroAPI v4 FlightPosition.altitude is hundreds of feet / flight level.
            altitude_ft = round(float(altitude_raw) * 100) if altitude_raw is not None else None
            timestamp = cls._parse_datetime(
                position.get("timestamp") or row.get("last_position_time") or row.get("timestamp")
            ) or datetime.now(timezone.utc)

            origin = row.get("origin") or {}
            destination = row.get("destination") or {}
            if isinstance(origin, str):
                origin_code, origin_name, origin_city, origin_icao = origin, None, None, None
            else:
                origin_code = origin.get("code")
                origin_name = origin.get("name")
                origin_city = origin.get("city")
                origin_icao = origin.get("code_icao")
            if isinstance(destination, str):
                destination_code, destination_name, destination_city, destination_icao = destination, None, None, None
            else:
                destination_code = destination.get("code")
                destination_name = destination.get("name")
                destination_city = destination.get("city")
                destination_icao = destination.get("code_icao")

            ident_icao = row.get("ident_icao")
            operator = row.get("operator")
            operator_code = (
                str(operator.get("icao") or operator.get("code"))
                if isinstance(operator, dict) and (operator.get("icao") or operator.get("code"))
                else str(row.get("operator_icao") or (ident_icao[:3] if ident_icao and len(ident_icao) >= 3 else "")) or None
            )

            return Aircraft(
                flight_id=str(row.get("fa_flight_id") or position.get("fa_flight_id") or row.get("ident") or "unknown"),
                ident=row.get("ident"),
                callsign=row.get("ident_icao") or row.get("ident"),
                ident_icao=ident_icao,
                ident_iata=row.get("ident_iata"),
                operator_code=operator_code,
                registration=row.get("registration"),
                aircraft_type=row.get("aircraft_type"),
                airline=(operator.get("name") if isinstance(operator, dict) else operator) or row.get("operator_name"),
                operator_shortname=(operator.get("shortname") if isinstance(operator, dict) else None),
                origin=origin_code,
                destination=destination_code,
                origin_name=origin_name,
                destination_name=destination_name,
                origin_city=origin_city,
                destination_city=destination_city,
                origin_icao=origin_icao,
                destination_icao=destination_icao,
                route=row.get("route"),
                latitude=float(lat),
                longitude=float(lon),
                altitude_ft=altitude_ft,
                groundspeed_kts=float(position["groundspeed"]) if position.get("groundspeed") is not None else None,
                heading_deg=float(position["heading"]) if position.get("heading") is not None else None,
                altitude_change=position.get("altitude_change"),
                update_type=position.get("update_type"),
                position_timestamp=timestamp,
                estimated_arrival=cls._parse_datetime(row.get("estimated_on")),
            )
        except (AttributeError, TypeError, ValueError, OverflowError):
            return None

    async def close(self) -> None:
        await self.client.aclose()
