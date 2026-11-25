from abc import ABC, abstractmethod
from portable_flight_display.core.models import Aircraft, Location


class FlightDataProvider(ABC):
    name = "base"

    @abstractmethod
    async def get_aircraft_nearby(
        self, location: Location, radius_km: float
    ) -> list[Aircraft]:
        raise NotImplementedError

    async def close(self) -> None:
        """Release provider resources, if any."""
