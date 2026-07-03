"""In-memory index over OurAirports-derived airport JSON."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "airports.json"


@dataclass(frozen=True)
class AirportRecord:
    icao: str
    name: str
    latitude: float
    longitude: float
    elevation_ft: int | None
    type: str
    iso_country: str = ""
    municipality: str | None = None
    iata_code: str | None = None


class AirportIndex:
    def __init__(self) -> None:
        self._by_icao: dict[str, AirportRecord] = {}
        self._all: list[AirportRecord] = []
        self._hubs: list[str] = []
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        if not DATA_PATH.exists():
            logger.warning(
                "airports.json missing — run: python scripts/build_airports_db.py"
            )
            self._loaded = True
            return

        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        self._hubs = list(raw.get("hubs") or [])
        for item in raw.get("airports") or []:
            rec = AirportRecord(
                icao=item["icao"],
                name=item["name"],
                latitude=float(item["latitude"]),
                longitude=float(item["longitude"]),
                elevation_ft=item.get("elevation_ft"),
                type=item["type"],
                iso_country=item.get("iso_country", ""),
                municipality=item.get("municipality"),
                iata_code=item.get("iata_code"),
            )
            self._by_icao[rec.icao] = rec
            self._all.append(rec)
        self._loaded = True
        logger.info("Airport index loaded: %d airports", len(self._all))

    def get(self, icao: str) -> AirportRecord | None:
        self.load()
        return self._by_icao.get(icao.upper())

    def query_bbox(
        self,
        min_lat: float,
        min_lon: float,
        max_lat: float,
        max_lon: float,
        *,
        limit: int = 2000,
    ) -> list[AirportRecord]:
        self.load()
        out: list[AirportRecord] = []
        for a in self._all:
            if min_lat <= a.latitude <= max_lat and min_lon <= a.longitude <= max_lon:
                out.append(a)
                if len(out) >= limit:
                    break
        return out

    def top_hubs(self, n: int = 500) -> list[AirportRecord]:
        self.load()
        out: list[AirportRecord] = []
        for icao in self._hubs[:n]:
            rec = self._by_icao.get(icao)
            if rec:
                out.append(rec)
        return out

    def count(self) -> int:
        self.load()
        return len(self._all)

    def nearest(self, lat: float, lon: float) -> AirportRecord | None:
        """Return the closest medium/large airport in the index."""
        self.load()
        if not self._all:
            return None
        best: AirportRecord | None = None
        best_score = float("inf")
        for a in self._all:
            dlat = (a.latitude - lat) * 111_000
            dlon = (a.longitude - lon) * 111_000 * max(0.3, abs(math.cos(math.radians(lat))))
            score = dlat * dlat + dlon * dlon
            if score < best_score:
                best_score = score
                best = a
        return best


airport_index = AirportIndex()
