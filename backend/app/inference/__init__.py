"""Inference engine: METAR, runway, phase, trajectory compression."""

from app.inference.metar import parse_metar, parse_wind
from app.inference.models import (
    FlightPhase,
    MetarReport,
    PhaseSnapshot,
    RunwayInference,
    TrajectoryPoint,
    Wind,
)
from app.inference.phase import PhaseTracker, classify_phase
from app.inference.runway import infer_active_runway, infer_from_metar, wind_components_kt
from app.inference.trajectory import douglas_peucker, douglas_peucker_latlon

__all__ = [
    "FlightPhase",
    "MetarReport",
    "PhaseSnapshot",
    "PhaseTracker",
    "RunwayInference",
    "TrajectoryPoint",
    "Wind",
    "classify_phase",
    "douglas_peucker",
    "douglas_peucker_latlon",
    "infer_active_runway",
    "infer_from_metar",
    "parse_metar",
    "parse_wind",
    "wind_components_kt",
]
