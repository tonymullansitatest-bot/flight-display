from datetime import datetime, timezone
from portable_flight_display.config import DetectionSettings
from portable_flight_display.core.models import Aircraft, Location
from portable_flight_display.flight.processor import FlightProcessor


def test_processor_marks_nearby_high_aircraft_as_candidate():
    location = Location(latitude=53.3, longitude=-6.2, source="test")
    aircraft = Aircraft(
        flight_id="test-1", ident="TEST1", latitude=53.301, longitude=-6.2,
        altitude_ft=12000, position_timestamp=datetime.now(timezone.utc),
    )
    settings = DetectionSettings(search_radius_km=20, overhead_radius_km=5)
    result = FlightProcessor(settings).process([aircraft], location)
    assert len(result) == 1
    assert result[0].is_overhead_candidate is True
    assert result[0].distance_km < 1


def test_processor_excludes_out_of_radius_aircraft():
    location = Location(latitude=53.3, longitude=-6.2, source="test")
    aircraft = Aircraft(
        flight_id="test-2", latitude=54.0, longitude=-6.2, altitude_ft=12000
    )
    result = FlightProcessor(DetectionSettings(search_radius_km=20)).process(
        [aircraft], location
    )
    assert result == []
