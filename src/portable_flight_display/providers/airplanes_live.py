from portable_flight_display.core.models import Aircraft, Location
from portable_flight_display.providers.adsb_base import ADSBPointProvider


class AirplanesLiveProvider(ADSBPointProvider):
    """Airplanes.live point/radius API adapter (radius is expressed in NM)."""

    name = "Airplanes.live"

    def __init__(self, base_url: str = "https://api.airplanes.live/v2",
                 timeout_seconds: float = 12):
        super().__init__(base_url, timeout_seconds)

    async def get_aircraft_nearby(self, location: Location, radius_km: float) -> list[Aircraft]:
        radius_nm = min(self.radius_nm(radius_km), int(self.max_radius_nm))
        path = f"point/{location.latitude:.5f}/{location.longitude:.5f}/{radius_nm:d}"
        return await self._get(path)
