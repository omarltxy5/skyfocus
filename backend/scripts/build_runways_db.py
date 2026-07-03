#!/usr/bin/env python3
"""Build backend/data/runways.json from OurAirports runways.csv."""

from __future__ import annotations

import csv
import json
import sys
import urllib.request
from pathlib import Path

RUNWAYS_CSV_URL = "https://davidmegginson.github.io/ourairports-data/runways.csv"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
AIRPORTS_PATH = DATA_DIR / "airports.json"
OUT_PATH = DATA_DIR / "runways.json"


def build(airports_path: Path | None = None, csv_path: Path | None = None) -> dict:
    airports_path = airports_path or AIRPORTS_PATH
    if not airports_path.exists():
        raise FileNotFoundError(f"Run {ROOT / 'scripts' / 'build_airports_db.py'} first")

    allowed: set[str] = set()
    raw_airports = json.loads(airports_path.read_text(encoding="utf-8"))
    for item in raw_airports.get("airports") or []:
        allowed.add(item["icao"].upper())

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if csv_path is None:
        csv_path = DATA_DIR / "runways.csv"
        print(f"Downloading {RUNWAYS_CSV_URL} ...")
        urllib.request.urlretrieve(RUNWAYS_CSV_URL, csv_path)

    by_icao: dict[str, dict[str, float]] = {}

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            icao = (row.get("airport_ident") or "").strip().upper()
            if icao not in allowed:
                continue
            if (row.get("closed") or "").strip() == "1":
                continue

            ends = (
                (row.get("le_ident"), row.get("le_heading_degT")),
                (row.get("he_ident"), row.get("he_heading_degT")),
            )
            for ident, heading_raw in ends:
                if not ident or not heading_raw:
                    continue
                try:
                    heading = round(float(heading_raw)) % 360
                except ValueError:
                    continue
                designator = ident.strip().upper()
                by_icao.setdefault(icao, {})[designator] = float(heading)

    runways_out: dict[str, list[dict]] = {}
    for icao, rwys in sorted(by_icao.items()):
        runways_out[icao] = [
            {"designator": d, "heading_deg": h} for d, h in sorted(rwys.items())
        ]

    payload = {
        "version": 1,
        "source": "OurAirports",
        "airport_count": len(runways_out),
        "runways": runways_out,
    }
    OUT_PATH.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote runways for {len(runways_out)} airports -> {OUT_PATH}")
    return payload


if __name__ == "__main__":
    ap = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    cp = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    build(ap, cp)
