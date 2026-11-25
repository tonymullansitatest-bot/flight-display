from portable_flight_display.core.models import Aircraft, Location
from portable_flight_display.providers.adsb_base import ADSBPointProvider


class ADSBLolProvider(ADSBPointProvider):
    """adsb.lol point/radius API adapter; API key is optional."""

    name = "adsb.lol"

    def __init__(self, base_url: str = "https://api.adsb.lol/v2",
                 timeout_seconds: float = 12, api_key: str | None = None):
        super().__init__(base_url, timeout_seconds, api_key=api_key)

    async def get_aircraft_nearby(self, location: Location, radius_km: float) -> list[Aircraft]:
        radius_nm = min(self.radius_nm(radius_km), int(self.max_radius_nm))
        path = f"lat/{location.latitude:.5f}/lon/{location.longitude:.5f}/dist/{radius_nm:d}"
        return await self._get(path)
