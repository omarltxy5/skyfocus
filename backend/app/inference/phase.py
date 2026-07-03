"""
Flight phase state machine from altitude and vertical speed.

Go-around (per spec): on approach below 2,500 ft AGL with rate of climb > +2,000 fpm.
Altitude inputs are assumed MSL or AGL consistently; default thresholds suit terminal area feeds.
"""

from __future__ import annotations

from app.inference.models import FlightPhase, PhaseSnapshot

# Phase classification thresholds (feet / fpm)
APPROACH_ALT_FT = 3_000
GO_AROUND_ALT_FT = 2_500
GO_AROUND_VS_FPM = 2_000
CRUISE_ALT_MIN_FT = 3_000
VS_CLIMB_FPM = 500
VS_DESCENT_FPM = -500


def classify_phase(
    altitude_ft: float,
    vertical_speed_fpm: float,
    *,
    previous: PhaseSnapshot | None = None,
) -> PhaseSnapshot:
    """
    Determine current flight phase and go-around flag.

    ``previous`` should be the last snapshot for the same aircraft (same callsign/icao24).
    """
    prev_phase = previous.phase if previous else None
    go_around = False

    # Go-around: was approaching low, now aggressive climb
    if (
        prev_phase == FlightPhase.APPROACH
        and altitude_ft < GO_AROUND_ALT_FT
        and vertical_speed_fpm > GO_AROUND_VS_FPM
    ):
        return PhaseSnapshot(
            phase=FlightPhase.GO_AROUND,
            go_around=True,
            altitude_ft=altitude_ft,
            vertical_speed_fpm=vertical_speed_fpm,
            previous_phase=prev_phase,
        )

    # Sustained go-around until off approach profile (climb above threshold or level off low)
    if prev_phase == FlightPhase.GO_AROUND:
        if vertical_speed_fpm > GO_AROUND_VS_FPM and altitude_ft < APPROACH_ALT_FT:
            return PhaseSnapshot(
                phase=FlightPhase.GO_AROUND,
                go_around=True,
                altitude_ft=altitude_ft,
                vertical_speed_fpm=vertical_speed_fpm,
                previous_phase=prev_phase,
            )
        # Fall through to normal classification after escape

    phase = _classify_base(altitude_ft, vertical_speed_fpm)

    return PhaseSnapshot(
        phase=phase,
        go_around=False,
        altitude_ft=altitude_ft,
        vertical_speed_fpm=vertical_speed_fpm,
        previous_phase=prev_phase,
    )


def _classify_base(altitude_ft: float, vertical_speed_fpm: float) -> FlightPhase:
    if altitude_ft < APPROACH_ALT_FT:
        if vertical_speed_fpm >= VS_CLIMB_FPM:
            return FlightPhase.CLIMB
        if vertical_speed_fpm <= VS_DESCENT_FPM:
            return FlightPhase.APPROACH
        # Shallow vertical rate near surface — treat as approach segment
        return FlightPhase.APPROACH

    if vertical_speed_fpm >= VS_CLIMB_FPM:
        return FlightPhase.CLIMB
    if vertical_speed_fpm <= VS_DESCENT_FPM:
        return FlightPhase.DESCENT

    if altitude_ft >= CRUISE_ALT_MIN_FT:
        return FlightPhase.CRUISE

    # Between approach ceiling and cruise floor with level flight
    return FlightPhase.CRUISE


class PhaseTracker:
    """Per-aircraft phase memory for streaming telemetry."""

    def __init__(self) -> None:
        self._last: dict[str, PhaseSnapshot] = {}

    def update(
        self,
        aircraft_id: str,
        altitude_ft: float,
        vertical_speed_fpm: float,
    ) -> PhaseSnapshot:
        prev = self._last.get(aircraft_id)
        snap = classify_phase(altitude_ft, vertical_speed_fpm, previous=prev)
        self._last[aircraft_id] = snap
        return snap

    def get(self, aircraft_id: str) -> PhaseSnapshot | None:
        return self._last.get(aircraft_id)

    def remove(self, aircraft_id: str) -> None:
        self._last.pop(aircraft_id, None)
