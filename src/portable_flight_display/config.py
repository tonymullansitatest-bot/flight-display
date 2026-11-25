from pathlib import Path
import os
import yaml
from pydantic import BaseModel, Field
from dotenv import load_dotenv


class LocationSettings(BaseModel):
    provider: str = "manual"
    latitude: float = 53.3498
    longitude: float = -6.2603
    altitude_m: float | None = None
    gpsd_host: str = "127.0.0.1"
    gpsd_port: int = 2947
    stale_after_seconds: int = 60


class ProviderSettings(BaseModel):
    provider: str = "mock"
    base_url: str = "https://aeroapi.flightaware.com/aeroapi"
    request_timeout_seconds: float = 12
    max_pages: int = 1
    max_results: int = Field(default=15, ge=1, le=15)
    enrich_operator_names: bool = True
    airplanes_live_base_url: str = "https://api.airplanes.live/v2"
    adsb_lol_base_url: str = "https://api.adsb.lol/v2"
    adsb_lol_api_key: str | None = None
    local_adsb_aircraft_json_path: str = "/run/readsb/aircraft.json"


class PollingSettings(BaseModel):
    interval_seconds: int = Field(default=30, ge=1)


class DetectionSettings(BaseModel):
    search_radius_km: float = 20
    overhead_radius_km: float = 5
    max_position_age_seconds: int = 120
    minimum_altitude_ft: int = 500
    maximum_altitude_ft: int = 45000


class DisplaySettings(BaseModel):
    type: str = "desktop"
    max_aircraft: int = 8
    led_rows: int = 32
    led_cols: int = 64
    led_chain_length: int = 1
    led_parallel: int = 1
    led_brightness: int = 45
    led_font_path: str = "fonts/5x8.bdf"


class StorageSettings(BaseModel):
    sqlite_path: str = "data/flights.db"


class Settings(BaseModel):
    application: dict = Field(default_factory=dict)
    location: LocationSettings = Field(default_factory=LocationSettings)
    flight_provider: ProviderSettings = Field(default_factory=ProviderSettings)
    polling: PollingSettings = Field(default_factory=PollingSettings)
    detection: DetectionSettings = Field(default_factory=DetectionSettings)
    display: DisplaySettings = Field(default_factory=DisplaySettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    api_key: str | None = None
    adsb_lol_api_key: str | None = None


def load_settings(path: str | Path) -> Settings:
    load_dotenv()
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as stream:
        raw = yaml.safe_load(stream) or {}
    raw["api_key"] = os.getenv("FLIGHTAWARE_API_KEY")
    raw["adsb_lol_api_key"] = os.getenv("ADSB_LOL_API_KEY")
    if raw.get("flight_provider", {}).get("adsb_lol_api_key") is None:
        raw.setdefault("flight_provider", {})["adsb_lol_api_key"] = raw["adsb_lol_api_key"]
    provider_override = os.getenv("PFD_PROVIDER")
    if provider_override:
        raw.setdefault("flight_provider", {})["provider"] = provider_override
    return Settings.model_validate(raw)
