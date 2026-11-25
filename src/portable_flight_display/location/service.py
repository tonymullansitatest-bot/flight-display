import logging
from portable_flight_display.config import LocationSettings
from portable_flight_display.location.gpsd_provider import GpsdLocationProvider
from portable_flight_display.location.manual_provider import ManualLocationProvider


class LocationService:
    def __init__(self, settings: LocationSettings):
        self.settings = settings
        self.manual_fallback = ManualLocationProvider(
            settings.latitude, settings.longitude, settings.altitude_m
        )
        if settings.provider == "gpsd":
            self.provider = GpsdLocationProvider(settings.gpsd_host, settings.gpsd_port)
        elif settings.provider == "manual":
            self.provider = self.manual_fallback
        else:
            raise ValueError(f"Unsupported location provider: {settings.provider}")

    async def get_current_location(self):
        try:
            return await self.provider.get_location()
        except Exception as exc:
            if self.settings.provider != "gpsd":
                raise
            logging.warning("GPSD unavailable (%s); using configured manual fallback", exc)
            location = await self.manual_fallback.get_location()
            location.source = "manual-fallback"
            return location
