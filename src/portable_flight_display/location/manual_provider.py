from portable_flight_display.core.models import Location
from portable_flight_display.location.base import LocationProvider


class ManualLocationProvider(LocationProvider):
    def __init__(self, latitude: float, longitude: float, altitude_m: float | None = None):
        self.latitude = latitude
        self.longitude = longitude
        self.altitude_m = altitude_m

    async def get_location(self) -> Location:
        return Location(
            latitude=self.latitude,
            longitude=self.longitude,
            altitude_m=self.altitude_m,
            source="manual",
        )
