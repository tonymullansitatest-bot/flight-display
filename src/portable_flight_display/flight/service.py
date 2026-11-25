from portable_flight_display.config import Settings
from portable_flight_display.core.models import FlightSnapshot
from portable_flight_display.flight.processor import FlightProcessor
from portable_flight_display.location.service import LocationService
from portable_flight_display.providers.flightaware import FlightAwareProvider
from portable_flight_display.providers.airplanes_live import AirplanesLiveProvider
from portable_flight_display.providers.adsb_lol import ADSBLolProvider
from portable_flight_display.providers.local_adsb import LocalAdsbProvider
from portable_flight_display.providers.mock import MockFlightProvider
from portable_flight_display.repository.sqlite import SQLiteFlightRepository


class FlightService:
    def __init__(self, settings: Settings, location_service: LocationService,
                 force_mock: bool = False):
        self.settings = settings
        self.location_service = location_service
        provider_name = "mock" if force_mock else settings.flight_provider.provider.lower()
        if provider_name == "mock":
            self.provider = MockFlightProvider()
        elif provider_name == "flightaware":
            self.provider = FlightAwareProvider(
                api_key=settings.api_key or "",
                base_url=settings.flight_provider.base_url,
                timeout_seconds=settings.flight_provider.request_timeout_seconds,
                max_results=settings.flight_provider.max_results,
                max_pages=settings.flight_provider.max_pages,
                enrich_operator_names=settings.flight_provider.enrich_operator_names,
            )
        elif provider_name in {"airplanes_live", "airplanes.live", "airplaneslive"}:
            self.provider = AirplanesLiveProvider(
                base_url=settings.flight_provider.airplanes_live_base_url,
                timeout_seconds=settings.flight_provider.request_timeout_seconds,
            )
        elif provider_name in {"local_adsb", "readsb", "local"}:
            self.provider = LocalAdsbProvider(
                aircraft_json_path=settings.flight_provider.local_adsb_aircraft_json_path,
            )
        elif provider_name in {"adsb_lol", "adsb.lol", "adsblol"}:
            self.provider = ADSBLolProvider(
                base_url=settings.flight_provider.adsb_lol_base_url,
                timeout_seconds=settings.flight_provider.request_timeout_seconds,
                api_key=settings.flight_provider.adsb_lol_api_key or settings.adsb_lol_api_key,
            )
        else:
            raise ValueError(
                f"Unsupported flight provider: {provider_name}. Choose mock, flightaware, "
                "airplanes_live, adsb_lol or local_adsb."
            )
        self.processor = FlightProcessor(settings.detection)
        self.repository = SQLiteFlightRepository(settings.storage.sqlite_path)

    async def refresh(self) -> FlightSnapshot:
        location = await self.location_service.get_current_location()
        raw = await self.provider.get_aircraft_nearby(
            location, self.settings.detection.search_radius_km
        )
        processed = self.processor.process(raw, location)
        snapshot = FlightSnapshot(
            location=location,
            aircraft=processed,
            provider_name=self.provider.name,
            status_message=f"{len(processed)} aircraft within {self.settings.detection.search_radius_km:g} km",
        )
        self.repository.save(snapshot)
        return snapshot

    async def close(self) -> None:
        await self.provider.close()
