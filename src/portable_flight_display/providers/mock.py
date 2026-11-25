from datetime import datetime, timezone
from portable_flight_display.core.models import Aircraft, Location
from portable_flight_display.flight.geo import GeoCalculator
from portable_flight_display.providers.base import FlightDataProvider


class MockFlightProvider(FlightDataProvider):
    name = "Mock provider"

    async def get_aircraft_nearby(
        self, location: Location, radius_km: float
    ) -> list[Aircraft]:
        now = datetime.now(timezone.utc)
        # Offset lat/lon to create repeatable positions around the current location.
        samples = [
            ("MOCK001", 0.010, 0.010, 28000, 430, 95),
            ("MOCK002", 0.020, -0.018, 32000, 410, 245),
            ("MOCK003", 0.003, -0.002, 4500, 180, 180),
            ("MOCK004", 0.110, 0.050, 36000, 470, 80),
        ]
        aircraft = []
        for ident, dlat, dlon, altitude, speed, heading in samples:
            lat = max(-90, min(90, location.latitude + dlat))
            lon = max(-180, min(180, location.longitude + dlon))
            if GeoCalculator.distance_km(location.latitude, location.longitude, lat, lon) <= radius_km * 1.5:
                aircraft.append(Aircraft(
                    flight_id=f"MOCK-{ident}",
                    ident=ident,
                    callsign=ident,
                    aircraft_type="A320" if altitude < 30000 else "B738",
                    latitude=lat,
                    longitude=lon,
                    altitude_ft=altitude,
                    groundspeed_kts=speed,
                    heading_deg=heading,
                    position_timestamp=now,
                    origin="DUB",
                    destination="LHR",
                ))
        return aircraft
