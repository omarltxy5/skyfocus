#!/usr/bin/env python3
"""
Download OurAirports airports.csv and build backend/data/airports.json.

Filter: type in (medium_airport, large_airport) with a valid 4-letter gps_code (ICAO).
"""

from __future__ import annotations

import csv
import json
import sys
import urllib.request
from pathlib import Path

OURAIRPORTS_CSV = (
    "https://davidmegginson.github.io/ourairports-data/airports.csv"
)
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_PATH = DATA_DIR / "airports.json"
ALLOWED_TYPES = frozenset({"medium_airport", "large_airport"})


def _valid_icao(gps_code: str) -> str | None:
    code = (gps_code or "").strip().upper()
    if len(code) != 4 or not code.isalpha():
        return None
    return code


def _hub_score(row: dict) -> int:
    score = 100 if row["type"] == "large_airport" else 50
    if (row.get("scheduled_service") or "").lower() == "yes":
        score += 20
    if (row.get("iata_code") or "").strip():
        score += 10
    return score


def build(csv_path: Path | None = None) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if csv_path is None:
        csv_path = DATA_DIR / "airports.csv"
        print(f"Downloading {OURAIRPORTS_CSV} ...")
        urllib.request.urlretrieve(OURAIRPORTS_CSV, csv_path)

    airports: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("type") not in ALLOWED_TYPES:
                continue
            icao = _valid_icao(row.get("gps_code", ""))
            if not icao:
                continue
            try:
                lat = float(row["latitude_deg"])
                lon = float(row["longitude_deg"])
            except (TypeError, ValueError):
                continue
            elev_raw = row.get("elevation_ft", "")
            elevation_ft: int | None = None
            if elev_raw not in (None, ""):
                try:
                    elevation_ft = int(float(elev_raw))
                except ValueError:
                    elevation_ft = None

            airports.append(
                {
                    "icao": icao,
                    "name": (row.get("name") or icao).strip(),
                    "latitude": lat,
                    "longitude": lon,
                    "elevation_ft": elevation_ft,
                    "type": row["type"],
                    "iso_country": (row.get("iso_country") or "").strip(),
                    "municipality": (row.get("municipality") or "").strip() or None,
                    "iata_code": (row.get("iata_code") or "").strip() or None,
                    "scheduled_service": (row.get("scheduled_service") or "").strip(),
                    "_score": _hub_score(row),
                }
            )

    ranked = sorted(airports, key=lambda a: (-a["_score"], a["icao"]))
    hubs = [a["icao"] for a in ranked[:500]]
    for a in airports:
        del a["_score"]

    payload = {
        "version": 1,
        "source": "OurAirports",
        "count": len(airports),
        "hubs": hubs,
        "airports": airports,
    }
    OUT_PATH.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {len(airports)} airports, {len(hubs)} hubs -> {OUT_PATH}")
    return payload


if __name__ == "__main__":
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    build(src)
    print("Building runways index...")
    import subprocess

    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_runways_db.py")],
        check=True,
    )
