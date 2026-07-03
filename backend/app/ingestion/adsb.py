"""ADS-B ingestion dynamically driven by global client viewport bounding boxes via adsb.lol."""

from __future__ import annotations

import asyncio
import logging
import math
import random
import time

import httpx

from app.config import settings
from app.state.telemetry import store

logger = logging.getLogger(__name__)

# Mock aircraft near NYC for baseline test patterns
_MOCK_AIRCRAFT: list[dict] = [
    {"icao24": "a1b2c1", "callsign": "SKY101", "lat": 40.72, "lon": -73.85, "alt": 1800, "vs": -700, "hdg": 130, "spd": 140},
    {"icao24": "a1b2c2", "callsign": "SKY202", "lat": 40.68, "lon": -73.92, "alt": 2200, "vs": 2400, "hdg": 310, "spd": 155},
    {"icao24": "a1b2c3", "callsign": "SKY303", "lat": 40.75, "lon": -73.70, "alt": 8500, "vs": 1200, "hdg": 90, "spd": 280},
    {"icao24": "a1b2c4", "callsign": "SKY404", "lat": 40.60, "lon": -73.78, "alt": 32000, "vs": 0, "hdg": 270, "spd": 450},
    {"icao24": "a1b2c5", "callsign": "SKY505", "lat": 40.80, "lon": -73.95, "alt": 12000, "vs": -900, "hdg": 180, "spd": 320},
    {"icao24": "a1b2c6", "callsign": "SKY606", "lat": 40.55, "lon": -73.65, "alt": 4500, "vs": -1100, "hdg": 45, "spd": 210},
]

# Track the last active viewport requested by a connected frontend client
# Format: (min_lat, min_lon, max_lat, max_lon)
_current_client_viewport: tuple[float, float, float, float] | None = None

def update_active_viewport(bbox: tuple[float, float, float, float]) -> None:
    """Updates the target global map framing context used by the background loop."""
    global _current_client_viewport
    _current_client_viewport = bbox

def _advance_mock() -> list[dict]:
    t = time.time()
    states: list[dict] = []
    for i, ac in enumerate(_MOCK_AIRCRAFT):
        phase_t = t * 0.15 + i
        dlat = math.sin(phase_t) * 0.008
        dlon = math.cos(phase_t * 0.9) * 0.012
        alt = ac["alt"] + math.sin(phase_t * 0.5) * 200
        vs = ac["vs"]
        if ac["callsign"] == "SKY202" and (int(t) % 30) < 15:
            vs = 2500  
            alt = min(alt, 2200)
        states.append({
            "icao24": ac["icao24"],
            "callsign": ac["callsign"],
            "latitude": ac["lat"] + dlat,
            "longitude": ac["lon"] + dlon,
            "altitude_ft": round(alt),
            "vertical_speed_fpm": vs,
            "ground_speed_kt": ac["spd"] + random.uniform(-5, 5),
            "heading_deg": (ac["hdg"] + int(t * 2) + i * 40) % 360,
            "on_ground": False,
            "nearest_airport": "KJFK",
        })
    return states

def _calculate_bbox_center_and_radius(bbox: tuple[float, float, float, float]) -> tuple[float, float, int]:
    """Translates bounding box matrices into a point and radius (NM) for adsb.lol."""
    min_lat, min_lon, max_lat, max_lon = bbox
    
    center_lat = (min_lat + max_lat) / 2.0
    center_lon = (min_lon + max_lon) / 2.0
    
    # Distance from center to outer bounds
    phi1 = math.radians(center_lat)
    phi2 = math.radians(max_lat)
    delta_lambda = math.radians(max_lon - center_lon)
    
    a = math.sin((phi2 - phi1) / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    # Earth radius in km * nautical mile conversion scaler
    radius_nm = int((6371 * c) * 0.539957)
    
    # Adsb.lol v2 strict parameter boundary requirements (1 - 250 NM)
    radius_nm = max(5, min(radius_nm, 250))
    return center_lat, center_lon, radius_nm

async def fetch_opensky(bbox: tuple[float, float, float, float] | None = None) -> int:
    """
    Maintained proxy signature for backend compatibility. 
    Queries the adsb.lol v2 dynamic geospatial endpoints.
    """
    # Prioritize passing the explicit functional bbox over the tracked global viewport state
    target_bbox = bbox or _current_client_viewport
    
    if not target_bbox:
        # Fallback to current browser geolocation frame (Alexandria) if map hasn't loaded yet
        lat, lon, radius = 31.2001, 29.9187, 100
    else:
        try:
            lat, lon, radius = _calculate_bbox_center_and_radius(target_bbox)
        except Exception:
            logger.error("Error parsing layout vector bounding geometry — reverting to system default")
            lat, lon, radius = 31.2001, 29.9187, 100

    # Clean REST query syntax matching adsb.lol v2 docs
    url = f"https://api.adsb.lol/v2/point/{lat}/{lon}/{radius}"
    headers = {"User-Agent": "SkyFocusIntelligencePlatform/1.0.0"}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code in (429, 503):
                logger.warning("adsb.lol target server heavily loaded — drops skipped cycle")
                return 0
                
            resp.raise_for_status()
            data = resp.json()
            aircraft_list = data.get("ac") or []
            
            if not aircraft_list:
                return 0
                
            normalized_states = []
            for ac in aircraft_list:
                if ac.get("lat") is None or ac.get("lon") is None:
                    continue
                    
                on_ground = ac.get("gs") == "ground" or ac.get("alt_baro") == "ground"
                
                try:
                    vs = float(ac.get("baro_rate", 0))
                except (ValueError, TypeError):
                    vs = 0.0

                normalized_states.append({
                    "icao24": ac.get("hex", "").strip().lower(),
                    "callsign": ac.get("flight", "").strip() or "UNK",
                    "latitude": ac.get("lat"),
                    "longitude": ac.get("lon"),
                    "altitude_ft": 0 if on_ground else ac.get("alt_baro", 0),
                    "vertical_speed_fpm": vs,
                    "ground_speed_kt": ac.get("gs", 0.0),
                    "heading_deg": ac.get("track", 0.0),
                    "on_ground": on_ground,
                    "nearest_airport": None
                })
                
            if not normalized_states:
                return 0
                
            # Clear historical local states and overwrite cache completely with updated bounds vectors
            return await store.upsert_mock_states(normalized_states)
            
        except Exception:
            logger.exception("Provider dynamic geospatial ingestion loop crashed")
            return 0

async def poll_adsb_loop(interval_sec: float, use_mock: bool) -> None:
    while True:
        try:
            if use_mock:
                n = await store.upsert_mock_states(_advance_mock())
                logger.info("Mock ADS-B: %d aircraft sync complete", n)
            else:
                n = await fetch_opensky(bbox=None)
                logger.info("adsb.lol viewport polling update: tracked %d planes", n)
        except Exception:
            logger.exception("ADS-B automation process loop failed")
            
        await asyncio.sleep(interval_sec if use_mock else max(interval_sec, 2.5))