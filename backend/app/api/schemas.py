"""API response schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WindComponentSchema(BaseModel):
    designator: str
    heading_deg: float
    headwind_kt: float
    crosswind_kt: float


class AirportSummarySchema(BaseModel):
    icao: str
    name: str
    latitude: float
    longitude: float
    elevation_ft: int | None = None
    type: str
    iso_country: str = ""
    municipality: str | None = None
    iata_code: str | None = None


class GeoHomeResponse(BaseModel):
    latitude: float
    longitude: float
    location_label: str | None = None
    nearest_airport: AirportSummarySchema
    distance_nm: float
    zoom: int = 10


class AirportListResponse(BaseModel):
    count: int
    airports: list[AirportSummarySchema]
    mode: str = Field(description="'bbox' or 'hubs'")


class MetarDecodedSchema(BaseModel):
    station: str
    observation_time: str | None = None
    wind: dict | None = None
    visibility: str | None = None
    weather: list[str] = Field(default_factory=list)
    clouds: list[str] = Field(default_factory=list)
    temperature_c: float | None = None
    dewpoint_c: float | None = None
    altimeter_inhg: float | None = None
    flight_category: str | None = None
    explanations: list[str] = Field(default_factory=list)


class AirportIntelligenceResponse(BaseModel):
    icao: str
    metar_raw: str | None = None
    metar_decoded: MetarDecodedSchema | None = None
    wind: dict | None = None
    active_runway: str | None = None
    headwind_kt: float | None = None
    crosswind_kt: float | None = None
    runways: list[WindComponentSchema] = Field(default_factory=list)
    updated_at: float | None = None


class FlightTelemetrySchema(BaseModel):
    latitude: float
    longitude: float
    altitude_ft: float
    vertical_speed_fpm: float
    ground_speed_kt: float | None = None
    heading_deg: float | None = None
    on_ground: bool = False


class FlightStateResponse(BaseModel):
    icao24: str
    callsign: str
    phase: str
    go_around: bool
    inferred_runway: str | None = None
    nearest_airport: str | None = None
    telemetry: FlightTelemetrySchema
    trajectory: list[dict[str, float]] = Field(default_factory=list)
    updated_at: float


class FlightDetailsResponse(BaseModel):
    icao24: str
    callsign: str
    airline: str | None = None
    aircraft_type: str | None = None
    registration: str | None = None
    data_sources: list[str] = Field(default_factory=list)
    origin_icao: str | None = None
    destination_icao: str | None = None
    origin_name: str | None = None
    destination_name: str | None = None
    photo_url: str | None = None
    phase: str | None = None
    go_around: bool = False
    altitude_ft: float | None = None
    vertical_speed_fpm: float | None = None
    ground_speed_kt: float | None = None
    heading_deg: float | None = None


class FlightDeltaSchema(BaseModel):
    icao24: str
    callsign: str
    phase: str
    go_around: bool
    latitude: float
    longitude: float
    altitude_ft: float
    vertical_speed_fpm: float
    heading_deg: float | None = None
    ground_speed_kt: float | None = None
    inferred_runway: str | None = None
    nearest_airport: str | None = None


class WsSubscribeMessage(BaseModel):
    type: str = "subscribe"
    bbox: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="[south, west, north, east]",
    )


class WsUpdateMessage(BaseModel):
    type: str = "update"
    flights: list[FlightDeltaSchema]
    ts: float
