"""Aircraft identity lookup by ICAO24 hex and registration (free public APIs)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL = 86400.0
_cache: dict[str, tuple[float, "AircraftIdentity"]] = {}


@dataclass
class AircraftIdentity:
    registration: str | None = None
    aircraft_type: str | None = None
    airline: str | None = None
    manufacturer: str | None = None
    icao_type_code: str | None = None
    sources: list[str] | None = None


def _cache_key(icao24: str, registration: str | None) -> str:
    return f"{icao24}:{registration or ''}"


async def _hexdb_by_hex(icao24: str) -> dict:
    url = f"https://hexdb.io/api/v1/aircraft/{icao24.lower()}"
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.get(url)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {}


async def _adsb_lol_by_hex(icao24: str) -> dict:
    url = f"https://api.adsb.lol/v2/hex/{icao24.lower()}"
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.get(url)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            ac = data.get("ac") or data.get("aircraft")
            if isinstance(ac, list) and ac:
                return ac[0] if isinstance(ac[0], dict) else {}
            return data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
        return {}


async def _adsb_lol_by_reg(registration: str) -> dict:
    reg = registration.strip().upper()
    url = f"https://api.adsb.lol/v2/reg/{reg}"
    async with httpx.AsyncClient(timeout=12.0) as client:
        resp = await client.get(url)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            ac = data.get("ac") or data.get("aircraft")
            if isinstance(ac, list) and ac:
                return ac[0] if isinstance(ac[0], dict) else {}
            return data
        if isinstance(data, list) and data and isinstance(data[0], dict):
            return data[0]
        return {}


def _merge_identity(
    base: AircraftIdentity,
    *,
    registration: str | None = None,
    aircraft_type: str | None = None,
    airline: str | None = None,
    manufacturer: str | None = None,
    icao_type: str | None = None,
    source: str,
) -> AircraftIdentity:
    sources = list(base.sources or [])
    if source not in sources:
        sources.append(source)
    return AircraftIdentity(
        registration=registration or base.registration,
        aircraft_type=aircraft_type or base.aircraft_type,
        airline=airline or base.airline,
        manufacturer=manufacturer or base.manufacturer,
        icao_type_code=icao_type or base.icao_type_code,
        sources=sources,
    )


async def lookup_aircraft(icao24: str, registration_hint: str | None = None) -> AircraftIdentity:
    """
    Resolve airline and aircraft type using registration-first lookups.

    Sources: hexdb.io (hex), adsb.lol (hex + registration).
    """
    icao24 = icao24.strip().lower()
    key = _cache_key(icao24, registration_hint)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return hit[1]

    identity = AircraftIdentity(sources=[])

    try:
        hx = await _hexdb_by_hex(icao24)
        reg = (hx.get("Registration") or hx.get("registration") or "").strip() or None
        typ = (hx.get("Type") or hx.get("type") or "").strip() or None
        mfr = (hx.get("Manufacturer") or hx.get("manufacturer") or "").strip() or None
        icao_t = (hx.get("ICAOTypeCode") or hx.get("icao_type") or "").strip() or None
        owner = (hx.get("RegisteredOwners") or hx.get("owner") or "").strip() or None
        identity = _merge_identity(
            identity,
            registration=reg or registration_hint,
            aircraft_type=typ or (f"{mfr} {icao_t}".strip() if mfr or icao_t else None),
            airline=owner,
            manufacturer=mfr,
            icao_type=icao_t,
            source="hexdb.io",
        )
    except Exception:
        logger.debug("hexdb lookup failed for %s", icao24)

    try:
        ad = await _adsb_lol_by_hex(icao24)
        reg = (ad.get("r") or ad.get("reg") or ad.get("registration") or "").strip() or None
        typ = (ad.get("t") or ad.get("type") or ad.get("desc") or "").strip() or None
        owner = (ad.get("own") or ad.get("owner") or ad.get("operator") or "").strip() or None
        identity = _merge_identity(
            identity,
            registration=reg or identity.registration or registration_hint,
            aircraft_type=typ,
            airline=owner,
            source="adsb.lol",
        )
    except Exception:
        logger.debug("adsb.lol hex lookup failed for %s", icao24)

    reg = identity.registration or registration_hint
    if reg:
        try:
            ad_reg = await _adsb_lol_by_reg(reg)
            typ = (ad_reg.get("t") or ad_reg.get("type") or ad_reg.get("desc") or "").strip()
            owner = (ad_reg.get("own") or ad_reg.get("owner") or "").strip()
            identity = _merge_identity(
                identity,
                registration=reg,
                aircraft_type=typ or None,
                airline=owner or None,
                source="adsb.lol-reg",
            )
        except Exception:
            logger.debug("adsb.lol reg lookup failed for %s", reg)

    _cache[key] = (time.time(), identity)
    return identity
