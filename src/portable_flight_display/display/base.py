from abc import ABC, abstractmethod
from portable_flight_display.core.models import FlightSnapshot


class DisplayInterface(ABC):
    @abstractmethod
    def initialise(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def render(self, snapshot: FlightSnapshot) -> None:
        raise NotImplementedError

    @abstractmethod
    def shutdown(self) -> None:
        raise NotImplementedError
