from datetime import datetime, timezone
from portable_flight_display.core.models import Location
from portable_flight_display.providers.flightaware import FlightAwareProvider


def test_builds_simplified_latlong_search_query():
    location = Location(latitude=53.35, longitude=-6.26, source="test")
    query = FlightAwareProvider.build_search_query(location, 20)
    assert query.startswith('-latlong "')
    assert "{range" not in query
    assert query.count(" ") == 4


def test_maps_flight_search_object_and_nested_last_position():
    row = {
        "fa_flight_id": "ABC123-1700000000-airline-001",
        "ident": "ABC123",
        "ident_icao": "EIN123",
        "ident_iata": "EI123",
        "aircraft_type": "A320",
        "origin": {"code": "EIDW", "name": "Dublin Airport"},
        "destination": {"code": "EGLL", "name": "London Heathrow"},
        "last_position": {
            "altitude": 120,
            "groundspeed": 420,
            "heading": 95,
            "latitude": 53.35,
            "longitude": -6.26,
            "timestamp": "2026-11-24T15:30:00Z",
            "altitude_change": "C",
            "update_type": "A",
        },
    }
    aircraft = FlightAwareProvider._to_aircraft(row)
    assert aircraft is not None
    assert aircraft.ident == "ABC123"
    assert aircraft.ident_icao == "EIN123"
    assert aircraft.ident_iata == "EI123"
    assert aircraft.altitude_ft == 12000  # API gives hundreds of feet
    assert aircraft.groundspeed_kts == 420
    assert aircraft.origin == "EIDW"
    assert aircraft.origin_name == "Dublin Airport"
    assert aircraft.destination == "EGLL"
    assert aircraft.aircraft_type == "A320"
    assert aircraft.update_type == "A"
    assert aircraft.position_timestamp == datetime(2026, 11, 24, 15, 30, tzinfo=timezone.utc)


def test_rejects_flight_without_last_position():
    row = {"fa_flight_id": "NO-POS", "ident": "NOCOORD", "last_position": None}
    assert FlightAwareProvider._to_aircraft(row) is None


def test_maps_airport_cities_and_operator_code():
    row = {
        "ident": "EIN123", "ident_icao": "EIN123",
        "origin": {"code": "EIDW", "code_icao": "EIDW", "name": "Dublin Airport", "city": "Dublin"},
        "destination": {"code": "EGLL", "code_icao": "EGLL", "name": "Heathrow", "city": "London"},
        "last_position": {"latitude": 53.35, "longitude": -6.26, "timestamp": "2026-11-24T15:30:00Z"},
    }
    aircraft = FlightAwareProvider._to_aircraft(row)
    assert aircraft is not None
    assert aircraft.operator_code == "EIN"
    assert aircraft.origin_city == "Dublin"
    assert aircraft.destination_city == "London"
    assert aircraft.origin_icao == "EIDW"


async def test_operator_name_lookup_is_cached():
    import httpx

    calls = []

    def handler(request):
        calls.append(request.url.path)
        if request.url.path.endswith("/flights/search"):
            return httpx.Response(200, json={"flights": [{
                "ident": "EIN123", "ident_icao": "EIN123",
                "origin": {"code": "EIDW", "name": "Dublin Airport", "city": "Dublin"},
                "destination": {"code": "EGLL", "name": "Heathrow", "city": "London"},
                "last_position": {"latitude": 53.35, "longitude": -6.26,
                                  "timestamp": "2026-11-24T15:30:00Z"},
            }]})
        if request.url.path.endswith("/operators/EIN"):
            return httpx.Response(200, json={"icao": "EIN", "name": "Aer Lingus Limited",
                                             "shortname": "Aer Lingus"})
        return httpx.Response(404)

    provider = FlightAwareProvider("test-key", "https://example.test/aeroapi")
    await provider.client.aclose()
    provider.client = httpx.AsyncClient(
        base_url="https://example.test/aeroapi/",
        headers={"x-apikey": "test-key"}, transport=httpx.MockTransport(handler),
    )
    location = Location(latitude=53.35, longitude=-6.26, source="test")
    first = await provider.get_aircraft_nearby(location, 20)
    second = await provider.get_aircraft_nearby(location, 20)
    assert first[0].airline == "Aer Lingus"
    assert second[0].airline == "Aer Lingus"
    assert calls.count("/aeroapi/operators/EIN") == 1
    await provider.close()
