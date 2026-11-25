from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_validator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Location(BaseModel):
    model_config = ConfigDict(extra="ignore")
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_m: float | None = None
    accuracy_m: float | None = None
    timestamp: datetime = Field(default_factory=utc_now)
    source: str = "unknown"


class Aircraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    flight_id: str
    ident: str | None = None
    callsign: str | None = None
    registration: str | None = None
    icao_hex: str | None = None
    aircraft_type: str | None = None
    airline: str | None = None
    operator_code: str | None = None
    operator_shortname: str | None = None
    ident_icao: str | None = None
    ident_iata: str | None = None
    origin_name: str | None = None
    destination_name: str | None = None
    origin_city: str | None = None
    destination_city: str | None = None
    origin_icao: str | None = None
    destination_icao: str | None = None
    route: str | None = None
    status: str | None = None
    squawk: str | None = None
    category: str | None = None
    vertical_rate_fpm: int | None = None
    position_age_seconds: float | None = None
    altitude_change: str | None = None
    update_type: str | None = None
    estimated_arrival: datetime | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    altitude_ft: int | None = None
    groundspeed_kts: float | None = None
    heading_deg: float | None = None
    origin: str | None = None
    destination: str | None = None
    position_timestamp: datetime = Field(default_factory=utc_now)
    distance_km: float | None = None
    bearing_deg: float | None = None
    is_overhead_candidate: bool = False

    @field_validator("position_timestamp")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class FlightSnapshot(BaseModel):
    location: Location
    aircraft: list[Aircraft]
    fetched_at: datetime = Field(default_factory=utc_now)
    provider_name: str
    status_message: str = "OK"
