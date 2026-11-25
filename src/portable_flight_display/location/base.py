from abc import ABC, abstractmethod
from portable_flight_display.core.models import Location


class LocationProvider(ABC):
    @abstractmethod
    async def get_location(self) -> Location:
        raise NotImplementedError
