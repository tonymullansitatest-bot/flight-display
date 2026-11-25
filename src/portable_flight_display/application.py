import asyncio
import logging
from portable_flight_display.config import Settings
from portable_flight_display.display.factory import create_display
from portable_flight_display.flight.service import FlightService
from portable_flight_display.location.service import LocationService


class ApplicationController:
    def __init__(self, settings: Settings, display_type: str | None = None,
                 force_mock: bool = False):
        self.settings = settings
        self.location_service = LocationService(settings.location)
        self.flight_service = FlightService(settings, self.location_service, force_mock)
        self.display_type = display_type or settings.display.type
        self.display = create_display(settings.display, self.display_type)

    async def run(self):
        self.display.initialise()
        try:
            while True:
                try:
                    snapshot = await self.flight_service.refresh()
                    self.display.render(snapshot)
                except Exception:
                    logging.exception("Flight refresh failed")
                await asyncio.sleep(self.settings.polling.interval_seconds)
        finally:
            self.display.shutdown()
            await self.flight_service.close()
