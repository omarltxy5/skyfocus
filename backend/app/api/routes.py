"""REST API v1 routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import (
    AirportIntelligenceResponse,
    AirportListResponse,
    AirportSummarySchema,
    FlightDetailsResponse,
    FlightStateResponse,
    FlightTelemetrySchema,
    MetarDecodedSchema,
    WindComponentSchema,
)
from app.inference.metar_decode import decode_metar
from app.ingestion.aircraft_enrichment import get_flight_details
from app.data.airports_index import AirportRecord, airport_index
from app.ingestion.metar import fetch_metar_batch
from app.state.telemetry import store

router = APIRouter(prefix="/api/v1")


def _airport_summary(a: AirportRecord) -> AirportSummarySchema:
    return AirportSummarySchema(
        icao=a.icao,
        name=a.name,
        latitude=a.latitude,
        longitude=a.longitude,
        elevation_ft=a.elevation_ft,
        type=a.type,
        iso_country=a.iso_country,
        municipality=a.municipality,
        iata_code=a.iata_code,
    )


@router.get("/airports", response_model=AirportListResponse)
async def list_airports(
    min_lat: float | None = Query(None, ge=-90, le=90),
    min_lon: float | None = Query(None, ge=-180, le=180),
    max_lat: float | None = Query(None, ge=-90, le=90),
    max_lon: float | None = Query(None, ge=-180, le=180),
) -> AirportListResponse:
    """
    List medium/large airports. With bbox params, filter to viewport; otherwise top 500 hubs.
    """
    bbox_params = [min_lat, min_lon, max_lat, max_lon]
    if any(p is not None for p in bbox_params) and not all(p is not None for p in bbox_params):
        raise HTTPException(
            status_code=400,
            detail="Provide all bbox params: min_lat, min_lon, max_lat, max_lon",
        )

    if all(p is not None for p in bbox_params):
        assert min_lat is not None and min_lon is not None
        assert max_lat is not None and max_lon is not None
        if min_lat > max_lat or min_lon > max_lon:
            raise HTTPException(status_code=400, detail="Invalid bounding box")
        records = airport_index.query_bbox(min_lat, min_lon, max_lat, max_lon)
        mode = "bbox"
    else:
        records = airport_index.top_hubs(500)
        mode = "hubs"

    return AirportListResponse(
        count=len(records),
        airports=[_airport_summary(a) for a in records],
        mode=mode,
    )


def _flight_to_response(f) -> FlightStateResponse:
    return FlightStateResponse(
        icao24=f.icao24,
        callsign=f.callsign,
        phase=f.phase.value,
        go_around=f.go_around,
        inferred_runway=f.inferred_runway,
        nearest_airport=f.nearest_airport,
        telemetry=FlightTelemetrySchema(
            latitude=f.latitude,
            longitude=f.longitude,
            altitude_ft=f.altitude_ft,
            vertical_speed_fpm=f.vertical_speed_fpm,
            ground_speed_kt=f.ground_speed_kt,
            heading_deg=f.heading_deg,
            on_ground=f.on_ground,
        ),
        trajectory=f.trajectory,
        updated_at=f.updated_at,
    )


@router.get("/airports/{icao}/intelligence", response_model=AirportIntelligenceResponse)
async def airport_intelligence(icao: str) -> AirportIntelligenceResponse:
    icao = icao.upper()
    intel = await store.get_airport_intel(icao)
    if intel is None:
        # On-demand METAR for airports discovered via the global layer
        try:
            await fetch_metar_batch([icao])
        except Exception:
            pass
        intel = await store.get_airport_intel(icao)
    if intel is None:
        raise HTTPException(
            status_code=404,
            detail=f"No METAR/intelligence for {icao}. NOAA may not publish a current report.",
        )

    runways: list[WindComponentSchema] = []
    active_runway = None
    headwind = None
    crosswind = None
    if intel.runway_inference:
        inf = intel.runway_inference
        active_runway = inf.active_runway
        headwind = inf.headwind_kt
        crosswind = inf.crosswind_kt
        runways = [
            WindComponentSchema(
                designator=r.designator,
                heading_deg=r.heading_deg,
                headwind_kt=r.headwind_kt,
                crosswind_kt=r.crosswind_kt,
            )
            for r in inf.all_runways
        ]

    metar_decoded = None
    if intel.metar_raw:
        dec = decode_metar(intel.metar_raw, station=intel.icao)
        metar_decoded = MetarDecodedSchema(
            station=dec.station,
            observation_time=dec.observation_time,
            wind=dec.wind,
            visibility=dec.visibility,
            weather=dec.weather,
            clouds=dec.clouds,
            temperature_c=dec.temperature_c,
            dewpoint_c=dec.dewpoint_c,
            altimeter_inhg=dec.altimeter_inhg,
            flight_category=dec.flight_category,
            explanations=dec.explanations,
        )

    return AirportIntelligenceResponse(
        icao=intel.icao,
        metar_raw=intel.metar_raw,
        metar_decoded=metar_decoded,
        wind=intel.wind,
        active_runway=active_runway,
        headwind_kt=headwind,
        crosswind_kt=crosswind,
        runways=runways,
        updated_at=intel.updated_at,
    )


@router.get("/flights/icao/{icao24}/details", response_model=FlightDetailsResponse)
async def flight_details(icao24: str) -> FlightDetailsResponse:
    details = await get_flight_details(icao24)
    return FlightDetailsResponse(
        icao24=details.icao24,
        callsign=details.callsign,
        airline=details.airline,
        aircraft_type=details.aircraft_type,
        registration=details.registration,
        data_sources=details.data_sources,
        origin_icao=details.origin_icao,
        destination_icao=details.destination_icao,
        origin_name=details.origin_name,
        destination_name=details.destination_name,
        photo_url=details.photo_url,
        phase=details.phase,
        go_around=details.go_around,
        altitude_ft=details.altitude_ft,
        vertical_speed_fpm=details.vertical_speed_fpm,
        ground_speed_kt=details.ground_speed_kt,
        heading_deg=details.heading_deg,
    )


@router.get("/flights/{callsign}/state", response_model=FlightStateResponse)
async def flight_state(callsign: str) -> FlightStateResponse:
    flight = await store.get_flight_by_callsign(callsign)
    if flight is None:
        raise HTTPException(
            status_code=404,
            detail=f"No active flight for callsign {callsign.upper()}",
        )
    return _flight_to_response(flight)
