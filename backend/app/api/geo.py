"""Client geolocation and nearest-airport resolution."""

from __future__ import annotations

import logging
import math

import httpx
from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import AirportSummarySchema, GeoHomeResponse
from app.data.airports_index import airport_index

logger = logging.getLogger(__name__)

geo_router = APIRouter(prefix="/api/v1")


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3440.065  # earth radius nm
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


async def _resolve_lat_lon(request: Request) -> tuple[float, float, str | None]:
    """Return (lat, lon, city label) from client IP or egress IP."""
    ip = _client_ip(request)
    local = ip in (None, "127.0.0.1", "::1", "localhost")

    if local:
        url = "http://ip-api.com/json/?fields=status,lat,lon,city,country"
    else:
        url = f"http://ip-api.com/json/{ip}?fields=status,lat,lon,city,country"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        if data.get("status") != "success":
            raise ValueError("geo lookup failed")
        lat = float(data["lat"])
        lon = float(data["lon"])
        city = data.get("city")
        country = data.get("country")
        label = ", ".join(p for p in (city, country) if p) or None
        return lat, lon, label
    except Exception:
        logger.exception("IP geolocation failed")
        # Default NYC if lookup fails
        return 40.6413, -73.7781, "Default (NYC)"


@geo_router.get("/geo/home", response_model=GeoHomeResponse)
async def geo_home(request: Request) -> GeoHomeResponse:
    """
    Resolve the user's approximate location from IP and return the nearest indexed airport.
    """
    lat, lon, location_label = await _resolve_lat_lon(request)
    nearest = airport_index.nearest(lat, lon)
    if nearest is None:
        raise HTTPException(status_code=503, detail="Airport index not loaded")

    dist_nm = _haversine_nm(lat, lon, nearest.latitude, nearest.longitude)
    return GeoHomeResponse(
        latitude=lat,
        longitude=lon,
        location_label=location_label,
        nearest_airport=AirportSummarySchema(
            icao=nearest.icao,
            name=nearest.name,
            latitude=nearest.latitude,
            longitude=nearest.longitude,
            elevation_ft=nearest.elevation_ft,
            type=nearest.type,
            iso_country=nearest.iso_country,
            municipality=nearest.municipality,
            iata_code=nearest.iata_code,
        ),
        distance_nm=round(dist_nm, 1),
        zoom=10,
    )
