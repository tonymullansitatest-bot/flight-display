import asyncio
from datetime import datetime, timezone
from portable_flight_display.core.models import Location
from portable_flight_display.location.base import LocationProvider


class GpsdLocationProvider(LocationProvider):
    """GPSD adapter. Requires gpsd running and the optional gpsd-py3 package."""

    def __init__(self, host: str = "127.0.0.1", port: int = 2947):
        self.host = host
        self.port = port

    async def get_location(self) -> Location:
        return await asyncio.to_thread(self._read_fix)

    def _read_fix(self) -> Location:
        try:
            from gpsd import connect, get_current
        except ImportError as exc:
            raise RuntimeError("GPS provider requires optional dependency: pip install gpsd-py3") from exc
        try:
            connect(host=self.host, port=self.port)
            packet = get_current()
            lat = getattr(packet, "lat", None)
            lon = getattr(packet, "lon", None)
            if lat is None or lon is None:
                raise RuntimeError("GPSD has no valid 2D/3D fix yet")
            altitude = getattr(packet, "alt", None)
            return Location(
                latitude=float(lat),
                longitude=float(lon),
                altitude_m=float(altitude) if altitude is not None else None,
                timestamp=datetime.now(timezone.utc),
                source="gpsd",
            )
        except Exception as exc:
            raise RuntimeError(f"Unable to read GPSD fix: {exc}") from exc
