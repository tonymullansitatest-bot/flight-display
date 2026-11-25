import pytest
from portable_flight_display.core.models import Location
from portable_flight_display.providers.mock import MockFlightProvider


@pytest.mark.asyncio
async def test_mock_provider_returns_aircraft():
    provider = MockFlightProvider()
    location = Location(latitude=53.3498, longitude=-6.2603, source="test")
    aircraft = await provider.get_aircraft_nearby(location, 20)
    assert len(aircraft) >= 1
    assert all(item.flight_id.startswith("MOCK-") for item in aircraft)
