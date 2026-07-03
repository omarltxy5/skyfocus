"""Shared types for the inference engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class FlightPhase(StrEnum):
    CLIMB = "climb"
    CRUISE = "cruise"
    DESCENT = "descent"
    APPROACH = "approach"
    GO_AROUND = "go_around"


@dataclass(frozen=True)
class Wind:
    """Surface wind from METAR (direction is meteorological 'from' degrees)."""

    direction_deg: int | None  # None when VRB
    speed_kt: float
    gust_kt: float | None = None
    variable: bool = False


@dataclass(frozen=True)
class MetarReport:
    icao: str
    raw: str
    wind: Wind | None
    observation_time: str | None = None


@dataclass(frozen=True)
class RunwayInfo:
    designator: str
    heading_deg: float


@dataclass
class RunwayWindComponents:
    designator: str
    heading_deg: float
    headwind_kt: float
    crosswind_kt: float


@dataclass
class RunwayInference:
    icao: str
    wind: Wind
    active_runway: str
    active_heading_deg: float
    headwind_kt: float
    crosswind_kt: float
    all_runways: list[RunwayWindComponents] = field(default_factory=list)


@dataclass
class PhaseSnapshot:
    phase: FlightPhase
    go_around: bool
    altitude_ft: float
    vertical_speed_fpm: float
    previous_phase: FlightPhase | None = None


@dataclass(frozen=True)
class TrajectoryPoint:
    lat: float
    lon: float
    alt_ft: float | None = None
    timestamp: float | None = None
