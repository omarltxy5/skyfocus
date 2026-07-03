"""
Runway inference from METAR surface wind.

Selects the runway with the greatest headwind component (standard ops preference).
"""

from __future__ import annotations

import math

from app.inference.metar import parse_metar, parse_wind
from app.inference.models import (
    MetarReport,
    RunwayInference,
    RunwayWindComponents,
    Wind,
)
from app.inference.runways_data import get_runways


def wind_components_kt(
    wind_dir_deg: float,
    wind_speed_kt: float,
    runway_heading_deg: float,
) -> tuple[float, float]:
    """
    Headwind and crosswind (knots) on a runway.

    Headwind is positive when wind opposes the landing roll (wind into the nose).
    Crosswind is positive when wind blows from the left (pilot's perspective on approach).
    """
    delta_rad = math.radians((wind_dir_deg - runway_heading_deg) % 360)
    headwind = wind_speed_kt * math.cos(delta_rad)
    crosswind = wind_speed_kt * math.sin(delta_rad)
    return headwind, crosswind


def _effective_speed_kt(wind: Wind) -> float:
    """Use gust for conservative component calc when reported."""
    if wind.gust_kt is not None and wind.gust_kt > wind.speed_kt:
        return wind.gust_kt
    return wind.speed_kt


def infer_active_runway(
    icao: str,
    wind: Wind,
    *,
    metar: MetarReport | None = None,
) -> RunwayInference:
    """
    Compare METAR wind against all runways at ``icao``; return active runway inference.

    Raises ``ValueError`` if the airport or wind direction is missing (VRB/calm).
    """
    icao = icao.upper()
    runways = get_runways(icao)
    if not runways:
        raise ValueError(f"No runway data for {icao}")

    if wind.variable or wind.direction_deg is None:
        raise ValueError("Cannot infer runway from variable (VRB) wind direction")

    speed = _effective_speed_kt(wind)
    if speed == 0:
        raise ValueError("Cannot infer runway from calm wind")

    components: list[RunwayWindComponents] = []
    for rwy in runways:
        hw, cw = wind_components_kt(
            float(wind.direction_deg),
            speed,
            rwy.heading_deg,
        )
        components.append(
            RunwayWindComponents(
                designator=rwy.designator,
                heading_deg=rwy.heading_deg,
                headwind_kt=round(hw, 1),
                crosswind_kt=round(cw, 1),
            )
        )

    # Greatest headwind wins; tie-break by lower crosswind
    best = max(components, key=lambda r: (r.headwind_kt, -abs(r.crosswind_kt)))

    return RunwayInference(
        icao=icao,
        wind=wind,
        active_runway=best.designator,
        active_heading_deg=best.heading_deg,
        headwind_kt=best.headwind_kt,
        crosswind_kt=best.crosswind_kt,
        all_runways=sorted(components, key=lambda r: -r.headwind_kt),
    )


def infer_from_metar(metar: str, icao: str | None = None) -> RunwayInference:
    """Parse METAR and infer active runway."""
    report = parse_metar(metar, icao=icao)
    if report.wind is None:
        raise ValueError("METAR contains no parseable wind group")
    return infer_active_runway(report.icao, report.wind, metar=report)


def infer_from_metar_wind_only(metar: str, icao: str) -> RunwayInference:
    """Infer using explicit ICAO when METAR body omits station id."""
    wind = parse_wind(metar)
    if wind is None:
        raise ValueError("METAR contains no parseable wind group")
    return infer_active_runway(icao, wind)
