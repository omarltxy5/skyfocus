"""In-memory sliding-window telemetry cache and fusion."""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field

from app.inference.models import (
    FlightPhase,
    MetarReport,
    PhaseSnapshot,
    RunwayInference,
    TrajectoryPoint,
)
from app.inference.phase import PhaseTracker
from app.inference.trajectory import douglas_peucker
from app.inference.runway import infer_active_runway
from app.inference.runways_data import get_runways


@dataclass
class FlightRecord:
    icao24: str
    callsign: str
    latitude: float
    longitude: float
    altitude_ft: float
    vertical_speed_fpm: float
    ground_speed_kt: float | None
    heading_deg: float | None
    phase: FlightPhase
    go_around: bool
    on_ground: bool
    trajectory: list[dict[str, float]]
    nearest_airport: str | None = None
    inferred_runway: str | None = None
    updated_at: float = field(default_factory=time.time)


@dataclass
class AirportIntel:
    icao: str
    metar_raw: str | None
    wind: dict | None
    runway_inference: RunwayInference | None
    updated_at: float


def _meters_to_ft(m: float | None) -> float:
    if m is None:
        return 0.0
    return m * 3.28084


def _ms_to_fpm(ms: float | None) -> float:
    if ms is None:
        return 0.0
    return ms * 196.850394


def _ms_to_kt(ms: float | None) -> float | None:
    if ms is None:
        return None
    return ms * 1.94384


# Rough airport centroids for associating flights (deg)
_AIRPORT_LOCATIONS: dict[str, tuple[float, float]] = {
    "KJFK": (40.6413, -73.7781),
    "KLAX": (33.9425, -118.4081),
    "KORD": (41.9742, -87.9073),
    "KATL": (33.6407, -84.4277),
    "EGLL": (51.4700, -0.4543),
}


def _nearest_airport(lat: float, lon: float, max_nm: float = 25.0) -> str | None:
    best: str | None = None
    best_dist = max_nm * 1852  # meters rough
    for icao, (alat, alon) in _AIRPORT_LOCATIONS.items():
        dlat = (lat - alat) * 111_000
        dlon = (lon - alon) * 111_000 * max(0.3, abs(math.cos(math.radians(lat))))
        dist = (dlat**2 + dlon**2) ** 0.5
        if dist < best_dist:
            best_dist = dist
            best = icao
    return best


class TelemetryStore:
    """Thread-safe async store for live flights and airport intelligence."""

    def __init__(self, window_sec: float = 600.0) -> None:
        self._lock = asyncio.Lock()
        self._window_sec = window_sec
        self._flights: dict[str, FlightRecord] = {}
        self._trajectories: dict[str, list[TrajectoryPoint]] = {}
        self._phase_tracker = PhaseTracker()
        self._airports: dict[str, AirportIntel] = {}

    async def set_metar(self, icao: str, report: MetarReport) -> None:
        inference: RunwayInference | None = None
        wind_dict: dict | None = None
        if report.wind and not report.wind.variable and report.wind.direction_deg is not None:
            wind_dict = {
                "direction_deg": report.wind.direction_deg,
                "speed_kt": report.wind.speed_kt,
                "gust_kt": report.wind.gust_kt,
            }
            if get_runways(icao) and report.wind.speed_kt > 0:
                try:
                    inference = infer_active_runway(icao, report.wind)
                except ValueError:
                    inference = None

        intel = AirportIntel(
            icao=icao,
            metar_raw=report.raw,
            wind=wind_dict,
            runway_inference=inference,
            updated_at=time.time(),
        )
        async with self._lock:
            self._airports[icao.upper()] = intel

    async def upsert_opensky_states(
        self,
        states: list[list],
        *,
        replace_snapshot: bool = False,
    ) -> int:
        """Ingest OpenSky ``states`` array rows; returns count updated."""
        now = time.time()
        updated = 0
        seen: set[str] = set()
        async with self._lock:
            for row in states:
                if not row or len(row) < 17:
                    continue
                icao24 = (row[0] or "").strip().lower()
                if not icao24:
                    continue
                seen.add(icao24)
                callsign = (row[1] or "").strip().upper() or icao24.upper()
                on_ground = bool(row[8])
                if on_ground:
                    continue
                lat, lon = row[6], row[5]
                if lat is None or lon is None:
                    continue

                alt_ft = _meters_to_ft(row[7])
                vs_fpm = _ms_to_fpm(row[11])
                speed_kt = _ms_to_kt(row[9])
                heading = row[10]

                phase_snap = self._phase_tracker.update(icao24, alt_ft, vs_fpm)
                traj = self._trajectories.setdefault(icao24, [])
                traj.append(TrajectoryPoint(lat=lat, lon=lon, alt_ft=alt_ft, timestamp=now))
                cutoff = now - self._window_sec
                self._trajectories[icao24] = [p for p in traj if (p.timestamp or now) >= cutoff]
                compressed = douglas_peucker(self._trajectories[icao24], epsilon_m=75.0)
                traj_out = [
                    {"lat": p.lat, "lon": p.lon, "alt_ft": p.alt_ft or 0}
                    for p in compressed
                ]

                airport = _nearest_airport(lat, lon)
                inferred_rwy: str | None = None
                if airport:
                    intel = self._airports.get(airport)
                    if intel and intel.runway_inference:
                        inferred_rwy = intel.runway_inference.active_runway

                self._flights[icao24] = FlightRecord(
                    icao24=icao24,
                    callsign=callsign,
                    latitude=lat,
                    longitude=lon,
                    altitude_ft=round(alt_ft, 0),
                    vertical_speed_fpm=round(vs_fpm, 0),
                    ground_speed_kt=round(speed_kt, 1) if speed_kt else None,
                    heading_deg=round(heading, 0) if heading is not None else None,
                    phase=phase_snap.phase,
                    go_around=phase_snap.go_around,
                    on_ground=on_ground,
                    trajectory=traj_out,
                    nearest_airport=airport,
                    inferred_runway=inferred_rwy,
                    updated_at=now,
                )
                updated += 1

            if replace_snapshot:
                stale = [k for k in self._flights if k not in seen]
                for k in stale:
                    del self._flights[k]
                    self._trajectories.pop(k, None)
                    self._phase_tracker.remove(k)
            self._purge_stale(now)
        return updated

    async def upsert_mock_states(self, states: list[dict]) -> int:
        """Ingest normalized dict records from the mock generator."""
        now = time.time()
        updated = 0
        async with self._lock:
            for s in states:
                icao24 = s["icao24"]
                callsign = s.get("callsign", icao24.upper())
                lat, lon = s["latitude"], s["longitude"]
                alt_ft = s["altitude_ft"]
                vs_fpm = s["vertical_speed_fpm"]

                phase_snap = self._phase_tracker.update(icao24, alt_ft, vs_fpm)
                traj = self._trajectories.setdefault(icao24, [])
                traj.append(
                    TrajectoryPoint(lat=lat, lon=lon, alt_ft=alt_ft, timestamp=now)
                )
                cutoff = now - self._window_sec
                self._trajectories[icao24] = [p for p in traj if (p.timestamp or now) >= cutoff]
                compressed = douglas_peucker(self._trajectories[icao24], epsilon_m=75.0)
                traj_out = [
                    {"lat": p.lat, "lon": p.lon, "alt_ft": p.alt_ft or 0}
                    for p in compressed
                ]

                airport = s.get("nearest_airport") or _nearest_airport(lat, lon)
                inferred_rwy = s.get("inferred_runway")
                if airport and not inferred_rwy:
                    intel = self._airports.get(airport)
                    if intel and intel.runway_inference:
                        inferred_rwy = intel.runway_inference.active_runway

                self._flights[icao24] = FlightRecord(
                    icao24=icao24,
                    callsign=callsign,
                    latitude=lat,
                    longitude=lon,
                    altitude_ft=alt_ft,
                    vertical_speed_fpm=vs_fpm,
                    ground_speed_kt=s.get("ground_speed_kt"),
                    heading_deg=s.get("heading_deg"),
                    phase=phase_snap.phase,
                    go_around=phase_snap.go_around,
                    on_ground=s.get("on_ground", False),
                    trajectory=traj_out,
                    nearest_airport=airport,
                    inferred_runway=inferred_rwy,
                    updated_at=now,
                )
                updated += 1
            self._purge_stale(now)
        return updated

    def _purge_stale(self, now: float) -> None:
        stale = [
            k
            for k, v in self._flights.items()
            if now - v.updated_at > self._window_sec
        ]
        for k in stale:
            del self._flights[k]
            self._trajectories.pop(k, None)
            self._phase_tracker.remove(k)

    async def get_flight_by_callsign(self, callsign: str) -> FlightRecord | None:
        cs = callsign.strip().upper()
        async with self._lock:
            for f in self._flights.values():
                if f.callsign.strip().upper() == cs:
                    return f
        return None

    async def get_flight_by_icao24(self, icao24: str) -> FlightRecord | None:
        key = icao24.strip().lower()
        async with self._lock:
            return self._flights.get(key)

    async def get_airport_intel(self, icao: str) -> AirportIntel | None:
        async with self._lock:
            return self._airports.get(icao.upper())

    async def flights_in_bbox(
        self,
        south: float,
        west: float,
        north: float,
        east: float,
    ) -> list[FlightRecord]:
        async with self._lock:
            out: list[FlightRecord] = []
            for f in self._flights.values():
                if f.on_ground:
                    continue
                if south <= f.latitude <= north and west <= f.longitude <= east:
                    out.append(f)
            return out

    async def flight_count(self) -> int:
        async with self._lock:
            return len(self._flights)


# Singleton used by API + ingestion
store = TelemetryStore()
