"""
Runway headings from OurAirports (backend/data/runways.json).

Built via: python scripts/build_runways_db.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.inference.models import RunwayInfo

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "runways.json"

# Legacy alias — populated after load()
RUNWAY_DATABASE: dict[str, list[RunwayInfo]] = {}


class RunwayIndex:
    def __init__(self) -> None:
        self._by_icao: dict[str, list[RunwayInfo]] = {}
        self._loaded = False

    def load(self) -> None:
        global RUNWAY_DATABASE
        if self._loaded:
            return
        if not DATA_PATH.exists():
            logger.warning(
                "runways.json missing — run: python scripts/build_runways_db.py"
            )
            self._loaded = True
            return

        raw = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        for icao, items in (raw.get("runways") or {}).items():
            runways: list[RunwayInfo] = []
            for item in items:
                runways.append(
                    RunwayInfo(
                        designator=item["designator"],
                        heading_deg=float(item["heading_deg"]),
                    )
                )
            if runways:
                self._by_icao[icao.upper()] = runways

        RUNWAY_DATABASE = self._by_icao
        self._loaded = True
        logger.info("Runway index loaded: %d airports", len(self._by_icao))

    def get(self, icao: str) -> list[RunwayInfo]:
        self.load()
        return self._by_icao.get(icao.upper(), [])

    def has(self, icao: str) -> bool:
        self.load()
        return icao.upper() in self._by_icao

    def count(self) -> int:
        self.load()
        return len(self._by_icao)


runway_index = RunwayIndex()


def get_runways(icao: str) -> list[RunwayInfo]:
    return runway_index.get(icao)
