from portable_flight_display.config import DetectionSettings
from portable_flight_display.core.models import Aircraft, Location
from portable_flight_display.flight.geo import GeoCalculator
from portable_flight_display.flight.overhead import OverheadDetector


class FlightProcessor:
    def __init__(self, settings: DetectionSettings):
        self.settings = settings
        self.detector = OverheadDetector(settings)

    def process(self, aircraft_list: list[Aircraft], location: Location) -> list[Aircraft]:
        processed: list[Aircraft] = []
        for aircraft in aircraft_list:
            distance = GeoCalculator.distance_km(
                location.latitude, location.longitude,
                aircraft.latitude, aircraft.longitude,
            )
            if distance > self.settings.search_radius_km:
                continue
            aircraft.distance_km = round(distance, 2)
            aircraft.bearing_deg = round(GeoCalculator.bearing_deg(
                location.latitude, location.longitude,
                aircraft.latitude, aircraft.longitude,
            ), 1)
            aircraft.is_overhead_candidate = self.detector.is_overhead_candidate(
                aircraft, location
            )
            processed.append(aircraft)
        return sorted(
            processed,
            key=lambda item: (not item.is_overhead_candidate, item.distance_km or 99999),
        )
