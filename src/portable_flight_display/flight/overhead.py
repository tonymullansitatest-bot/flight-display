from datetime import datetime, timezone
from portable_flight_display.config import DetectionSettings
from portable_flight_display.core.models import Aircraft, Location


class OverheadDetector:
    def __init__(self, settings: DetectionSettings):
        self.settings = settings

    def is_fresh(self, aircraft: Aircraft, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        age = (now - aircraft.position_timestamp).total_seconds()
        return -5 <= age <= self.settings.max_position_age_seconds

    def is_overhead_candidate(self, aircraft: Aircraft, location: Location) -> bool:
        if aircraft.distance_km is None or aircraft.altitude_ft is None:
            return False
        if not self.is_fresh(aircraft):
            return False
        return (
            aircraft.distance_km <= self.settings.overhead_radius_km
            and self.settings.minimum_altitude_ft <= aircraft.altitude_ft
            <= self.settings.maximum_altitude_ft
        )
