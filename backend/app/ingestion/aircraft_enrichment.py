"""Aircraft metadata, route, and photo enrichment."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from app.config import settings
from app.data.airports_index import airport_index
from app.ingestion.airlines import airline_from_callsign
from app.ingestion.registration_lookup import lookup_aircraft
from app.state.telemetry import store

logger = logging.getLogger(__name__)

_CACHE_TTL_SEC = 3600.0
_meta_cache: dict[str, tuple[float, dict]] = {}
_route_cache: dict[str, tuple[float, dict | list]] = {}
_photo_cache: dict[str, tuple[float, str | None]] = {}


@dataclass
class FlightDetails:
    icao24: str
    callsign: str
    airline: str | None
    aircraft_type: str | None
    registration: str | None
    origin_icao: str | None
    destination_icao: str | None
    origin_name: str | None
    destination_name: str | None
    photo_url: str | None
    data_sources: list[str]
    phase: str | None
    go_around: bool
    altitude_ft: float | None
    vertical_speed_fpm: float | None
    ground_speed_kt: float | None
    heading_deg: float | None


def _cache_get(cache: dict, key: str):
    entry = cache.get(key)
    if not entry:
        return None
    ts, val = entry
    if time.time() - ts > _CACHE_TTL_SEC:
        cache.pop(key, None)
        return None
    return val


def _cache_set(cache: dict, key: str, val) -> None:
    cache[key] = (time.time(), val)


async def _fetch_opensky_metadata(icao24: str) -> dict:
    cached = _cache_get(_meta_cache, icao24)
    if cached is not None:
        return cached

    url = f"{settings.opensky_base_url.rstrip('/')}/metadata/aircraft/icao24/{icao24}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(url)
        if resp.status_code == 404:
            data: dict = {}
        else:
            resp.raise_for_status()
            raw = resp.json()
            data = raw if isinstance(raw, dict) else {}
    _cache_set(_meta_cache, icao24, data)
    return data


async def _fetch_opensky_route(icao24: str) -> dict | list:
    cached = _cache_get(_route_cache, icao24)
    if cached is not None:
        return cached

    url = f"{settings.opensky_base_url.rstrip('/')}/flights/aircraft"
    begin = int(time.time()) - 6 * 3600
    end = int(time.time())
    async with httpx.AsyncClient(timeout=25.0) as client:
        resp = await client.get(
            url,
            params={"icao24": icao24, "begin": begin, "end": end},
        )
        if resp.status_code in (404, 429):
            data: dict | list = {}
        else:
            resp.raise_for_status()
            raw = resp.json()
            data = raw if isinstance(raw, (dict, list)) else {}
    _cache_set(_route_cache, icao24, data)
    return data


async def _fetch_planespotters_photo(registration: str) -> str | None:
    reg = registration.strip().upper()
    if not reg:
        return None
    cached = _cache_get(_photo_cache, reg)
    if cached is not None:
        return cached if cached != "" else None

    url = f"https://api.planespotters.net/pub/photos/reg/{reg}"
    photo_url: str | None = None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"Accept": "application/json"})
            if resp.is_success:
                body = resp.json()
                photos = body.get("photos") or []
                if photos:
                    thumbs = photos[0].get("thumbnail_src") or {}
                    photo_url = (
                        thumbs.get("large")
                        or thumbs.get("medium")
                        or thumbs.get("small")
                    )
    except Exception:
        logger.debug("Planespotters lookup failed for %s", reg)

    _cache_set(_photo_cache, reg, photo_url or "")
    return photo_url


def _airport_label(icao: str | None) -> str | None:
    if not icao:
        return None
    rec = airport_index.get(icao.upper())
    if rec:
        return f"{rec.name} ({icao.upper()})"
    return icao.upper()


def _parse_route(data: dict | list) -> tuple[str | None, str | None]:
    best_dep: str | None = None
    best_arr: str | None = None
    best_ts = 0

    rows: list = []
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict) and "estDepartureAirport" in data:
        rows = [data]
    elif isinstance(data, dict):
        for key in ("departure", "arrival"):
            part = data.get(key)
            if isinstance(part, list):
                rows.extend(part)

    for row in rows:
        dep = arr = None
        ts = 0
        if isinstance(row, dict):
            dep = row.get("estDepartureAirport") or row.get("departure")
            arr = row.get("estArrivalAirport") or row.get("arrival")
            ts = row.get("lastSeen") or row.get("firstSeen") or 0
        elif isinstance(row, (list, tuple)) and len(row) >= 5:
            dep, arr, ts = row[2], row[3], row[4] or 0
        if ts >= best_ts:
            best_ts = ts
            if dep:
                best_dep = dep
            if arr:
                best_arr = arr
    return best_dep, best_arr


async def get_flight_details(icao24: str) -> FlightDetails:
    icao24 = icao24.strip().lower()
    flight = await store.get_flight_by_icao24(icao24)
    callsign = flight.callsign if flight else icao24.upper()

    opensky = await _fetch_opensky_metadata(icao24)
    reg_hint = (opensky.get("registration") or "").strip() or None

    identity = await lookup_aircraft(icao24, reg_hint)
    route_data = await _fetch_opensky_route(icao24)

    registration = identity.registration or reg_hint
    aircraft_type = identity.aircraft_type
    if not aircraft_type:
        model = (opensky.get("model") or "").strip()
        typecode = (opensky.get("typecode") or opensky.get("icaoaircrafttype") or "").strip()
        aircraft_type = " ".join(p for p in (model, typecode) if p) or None

    airline = identity.airline or (opensky.get("operator") or "").strip() or None
    if not airline:
        airline = airline_from_callsign(callsign)

    sources = list(identity.sources or [])
    if opensky:
        sources.append("opensky-metadata")

    origin, dest = _parse_route(route_data)
    photo_url = await _fetch_planespotters_photo(registration) if registration else None

    return FlightDetails(
        icao24=icao24,
        callsign=callsign,
        airline=airline,
        aircraft_type=aircraft_type,
        registration=registration,
        origin_icao=origin,
        destination_icao=dest,
        origin_name=_airport_label(origin),
        destination_name=_airport_label(dest),
        photo_url=photo_url,
        data_sources=sources,
        phase=flight.phase.value if flight else None,
        go_around=flight.go_around if flight else False,
        altitude_ft=flight.altitude_ft if flight else None,
        vertical_speed_fpm=flight.vertical_speed_fpm if flight else None,
        ground_speed_kt=flight.ground_speed_kt if flight else None,
        heading_deg=flight.heading_deg if flight else None,
    )
