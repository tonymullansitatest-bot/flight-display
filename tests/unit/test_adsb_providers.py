from datetime import datetime, timezone

import httpx
import pytest

from portable_flight_display.core.models import Location
from portable_flight_display.providers.adsb_base import ADSBProviderError, ADSBPointProvider
from portable_flight_display.providers.airplanes_live import AirplanesLiveProvider
from portable_flight_display.providers.adsb_lol import ADSBLolProvider


SAMPLE_AIRCRAFT = {
    "hex": "4ca123",
    "flight": "EIN123  ",
    "r": "EI-ABC",
    "t": "A320",
    "lat": 53.45,
    "lon": -6.15,
    "alt_baro": 12000,
    "gs": 320.5,
    "track": 270.0,
    "baro_rate": 640,
    "squawk": "1234",
    "category": "A3",
    "seen_pos": 1.2,
}


@pytest.mark.asyncio
async def test_airplanes_live_uses_point_radius_and_maps_aircraft():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ac": [SAMPLE_AIRCRAFT], "total": 1})

    provider = AirplanesLiveProvider()
    await provider.client.aclose()
    provider.client = httpx.AsyncClient(
        base_url="https://api.airplanes.live/v2/",
        transport=httpx.MockTransport(handler),
    )
    location = Location(latitude=53.35, longitude=-6.26, source="test")
    aircraft = await provider.get_aircraft_nearby(location, 20)

    assert requests[0].url.path.startswith("/v2/point/53.35000/-6.26000/")
    assert len(aircraft) == 1
    item = aircraft[0]
    assert item.icao_hex == "4ca123"
    assert item.callsign == "EIN123"
    assert item.registration == "EI-ABC"
    assert item.aircraft_type == "A320"
    assert item.altitude_ft == 12000
    assert item.groundspeed_kts == 320.5
    assert item.heading_deg == 270
    assert item.vertical_rate_fpm == 640
    assert item.altitude_change == "climbing"
    assert item.squawk == "1234"
    assert item.position_age_seconds == 1.2
    assert item.position_timestamp.tzinfo == timezone.utc
    await provider.close()


@pytest.mark.asyncio
async def test_adsb_lol_uses_lat_lon_dist_and_optional_api_key():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ac": [SAMPLE_AIRCRAFT]})

    provider = ADSBLolProvider(api_key="demo-key")
    await provider.client.aclose()
    provider.client = httpx.AsyncClient(
        base_url="https://api.adsb.lol/v2/",
        headers={"x-api-key": "demo-key"},
        transport=httpx.MockTransport(handler),
    )
    location = Location(latitude=53.35, longitude=-6.26, source="test")
    aircraft = await provider.get_aircraft_nearby(location, 20)

    assert requests[0].url.path.startswith("/v2/lat/53.35000/lon/-6.26000/dist/")
    assert requests[0].headers["x-api-key"] == "demo-key"
    assert len(aircraft) == 1
    await provider.close()


def test_adsb_radius_is_converted_from_km_to_nautical_miles():
    assert ADSBPointProvider.radius_nm(18.52) == 10
    assert ADSBPointProvider.radius_nm(20) == 11


def test_adsb_mapping_handles_ground_and_missing_optional_fields():
    item = ADSBPointProvider.map_aircraft({
        "hex": "abc123", "lat": 53.0, "lon": -6.0, "alt_baro": "ground",
        "seen_pos": 0,
    })
    assert item is not None
    assert item.status == "ground"
    assert item.altitude_ft is None
    assert item.registration is None
    assert item.position_timestamp <= datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_adsb_rate_limit_is_reported_with_retry_after():
    def handler(_request):
        return httpx.Response(429, headers={"Retry-After": "30"})

    provider = AirplanesLiveProvider()
    await provider.client.aclose()
    provider.client = httpx.AsyncClient(
        base_url="https://api.airplanes.live/v2/",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(ADSBProviderError, match="Retry-After: 30"):
        await provider.get_aircraft_nearby(
            Location(latitude=53.0, longitude=-6.0), 20
        )
    await provider.close()


def test_config_supports_provider_override_and_adsb_lol_key(monkeypatch, tmp_path):
    from portable_flight_display.config import load_settings

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "flight_provider:\n  provider: airplanes_live\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("PFD_PROVIDER", "adsb_lol")
    monkeypatch.setenv("ADSB_LOL_API_KEY", "test-adsb-key")
    settings = load_settings(config_file)

    assert settings.flight_provider.provider == "adsb_lol"
    assert settings.flight_provider.adsb_lol_api_key == "test-adsb-key"


def test_adsb_mapping_uses_nested_last_position_when_present():
    item = ADSBPointProvider.map_aircraft({
        "hex": "abc123",
        "lastPosition": {"lat": 53.1, "lon": -6.1, "seen_pos": 4.5},
    })
    assert item is not None
    assert item.latitude == 53.1
    assert item.longitude == -6.1
    assert item.position_age_seconds == 4.5

@pytest.mark.asyncio
async def test_local_readsb_provider_reads_aircraft_json(tmp_path):
    import json
    from portable_flight_display.providers.local_adsb import LocalAdsbProvider

    aircraft_file = tmp_path / "aircraft.json"
    aircraft_file.write_text(json.dumps({
        "now": 1795600000.0,
        "messages": 12345,
        "aircraft": [SAMPLE_AIRCRAFT, {"hex": "abc999", "flight": "NO_POS"}],
    }), encoding="utf-8")

    provider = LocalAdsbProvider(aircraft_file)
    aircraft = await provider.get_aircraft_nearby(
        Location(latitude=53.35, longitude=-6.26, source="test"), 20
    )

    assert len(aircraft) == 1
    assert aircraft[0].icao_hex == "4ca123"
    assert aircraft[0].callsign == "EIN123"
    assert aircraft[0].altitude_ft == 12000
    assert aircraft[0].groundspeed_kts == 320.5
    assert aircraft[0].vertical_rate_fpm == 640
    await provider.close()


@pytest.mark.asyncio
async def test_local_readsb_provider_reports_missing_file(tmp_path):
    from portable_flight_display.providers.local_adsb import LocalAdsbProvider

    provider = LocalAdsbProvider(tmp_path / "missing-aircraft.json")
    with pytest.raises(ADSBProviderError, match="Is readsb installed and running"):
        await provider.get_aircraft_nearby(Location(latitude=53.0, longitude=-6.0), 20)


def test_local_readsb_provider_rejects_invalid_payload():
    from portable_flight_display.providers.local_adsb import LocalAdsbProvider

    with pytest.raises(ADSBProviderError, match="aircraft array"):
        LocalAdsbProvider._decode({"now": 1, "aircraft": None})


def test_config_accepts_five_second_local_receiver_polling(tmp_path):
    from portable_flight_display.config import load_settings

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "flight_provider:\n  provider: local_adsb\n"
        "polling:\n  interval_seconds: 5\n",
        encoding="utf-8",
    )
    settings = load_settings(config_file)
    assert settings.flight_provider.provider == "local_adsb"
    assert settings.flight_provider.local_adsb_aircraft_json_path == "/run/readsb/aircraft.json"
    assert settings.polling.interval_seconds == 5
