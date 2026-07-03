"""
METAR wind parser (NOAA / aviation routine text).

Extracts surface wind group (dddss[Ggg]KT or MPS). Does not decode full METAR.
"""

from __future__ import annotations

import re

from app.inference.models import MetarReport, Wind

# Wind group after optional RMK/visibility — first surface wind token in body
_WIND_PATTERN = re.compile(
    r"(?:^|\s)"
    r"(?P<dir>VRB|\d{3})"
    r"(?P<speed>\d{2,3})"
    r"(?:G(?P<gust>\d{2,3}))?"
    r"(?P<unit>KT|MPS)"
    r"(?:\s|$)",
    re.IGNORECASE,
)

_CALM_PATTERN = re.compile(r"(?:^|\s)00000KT(?:\s|$)", re.IGNORECASE)

# Station + optional SPECI/COR + DDHHMMZ
_ICAO_TIME = re.compile(
    r"^(?:METAR\s+)?(?P<icao>[A-Z]{4})\s+(?P<time>\d{6}Z)",
    re.IGNORECASE,
)


def _mps_to_kt(speed: float) -> float:
    return speed * 1.94384


def parse_wind(metar: str) -> Wind | None:
    """Parse the first surface wind group from a METAR string."""
    text = metar.strip().upper()

    if _CALM_PATTERN.search(text):
        return Wind(direction_deg=0, speed_kt=0.0, gust_kt=None, variable=False)

    match = _WIND_PATTERN.search(text)
    if not match:
        return None

    direction_raw = match.group("dir")
    speed_raw = float(match.group("speed"))
    gust_raw = match.group("gust")
    unit = match.group("unit").upper()

    if unit == "MPS":
        speed_kt = _mps_to_kt(speed_raw)
        gust_kt = _mps_to_kt(float(gust_raw)) if gust_raw else None
    else:
        speed_kt = speed_raw
        gust_kt = float(gust_raw) if gust_raw else None

    if direction_raw == "VRB":
        return Wind(
            direction_deg=None,
            speed_kt=speed_kt,
            gust_kt=gust_kt,
            variable=True,
        )

    direction_deg = int(direction_raw)
    if direction_deg == 0 and speed_kt == 0:
        return Wind(direction_deg=0, speed_kt=0.0, gust_kt=gust_kt, variable=False)

    return Wind(
        direction_deg=direction_deg,
        speed_kt=speed_kt,
        gust_kt=gust_kt,
        variable=False,
    )


def parse_metar(metar: str, icao: str | None = None) -> MetarReport:
    """
    Parse wind (and optional station/time) from a METAR line.

    If ``icao`` is omitted, attempts to read the 4-letter station id from the text.
    """
    text = metar.strip()
    upper = text.upper()

    station = icao.upper() if icao else None
    obs_time: str | None = None

    header = _ICAO_TIME.match(upper.replace("METAR ", "", 1) if upper.startswith("METAR ") else upper)
    if header:
        station = station or header.group("icao").upper()
        obs_time = header.group("time")

    if not station:
        # Fallback: first token that looks like ICAO in METAR body
        tokens = upper.split()
        for tok in tokens[:3]:
            if len(tok) == 4 and tok.isalpha():
                station = tok
                break

    if not station:
        raise ValueError("Cannot determine ICAO station from METAR")

    return MetarReport(
        icao=station,
        raw=text,
        wind=parse_wind(text),
        observation_time=obs_time,
    )
