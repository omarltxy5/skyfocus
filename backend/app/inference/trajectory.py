"""
Trajectory compression via the Douglas–Peucker algorithm.

Operates in local meters (equirectangular) so ``epsilon_m`` is geographic distance.
"""

from __future__ import annotations

import math

from app.inference.models import TrajectoryPoint

_EARTH_RADIUS_M = 6_371_000.0


def _to_local_meters(
    lat: float,
    lon: float,
    ref_lat: float,
    ref_lon: float,
) -> tuple[float, float]:
    lat_rad = math.radians(ref_lat)
    x = math.radians(lon - ref_lon) * math.cos(lat_rad) * _EARTH_RADIUS_M
    y = math.radians(lat - ref_lat) * _EARTH_RADIUS_M
    return x, y


def _perpendicular_distance_m(
    point: tuple[float, float],
    line_start: tuple[float, float],
    line_end: tuple[float, float],
) -> float:
    px, py = point
    x1, y1 = line_start
    x2, y2 = line_end

    dx = x2 - x1
    dy = y2 - y1
    seg_len_sq = dx * dx + dy * dy

    if seg_len_sq == 0:
        return math.hypot(px - x1, py - y1)

    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg_len_sq))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _douglas_peucker_indices(
    coords: list[tuple[float, float]],
    epsilon_m: float,
) -> list[int]:
    if len(coords) <= 2:
        return list(range(len(coords)))

    start = 0
    end = len(coords) - 1
    keep: set[int] = {start, end}

    stack: list[tuple[int, int]] = [(start, end)]

    while stack:
        s, e = stack.pop()
        if e <= s + 1:
            continue

        seg_start = coords[s]
        seg_end = coords[e]
        max_dist = 0.0
        index = -1

        for i in range(s + 1, e):
            dist = _perpendicular_distance_m(coords[i], seg_start, seg_end)
            if dist > max_dist:
                max_dist = dist
                index = i

        if max_dist > epsilon_m and index != -1:
            keep.add(index)
            stack.append((s, index))
            stack.append((index, e))

    return sorted(keep)


def douglas_peucker(
    points: list[TrajectoryPoint],
    epsilon_m: float = 50.0,
) -> list[TrajectoryPoint]:
    """
    Return a simplified trajectory preserving endpoints and bends > ``epsilon_m``.

    Args:
        points: Ordered trajectory (oldest → newest).
        epsilon_m: Maximum perpendicular deviation (meters) for intermediate points.
    """
    if len(points) <= 2:
        return list(points)

    ref_lat = points[0].lat
    ref_lon = points[0].lon
    local = [_to_local_meters(p.lat, p.lon, ref_lat, ref_lon) for p in points]
    indices = _douglas_peucker_indices(local, epsilon_m)
    return [points[i] for i in indices]


def douglas_peucker_latlon(
    coordinates: list[tuple[float, float]],
    epsilon_m: float = 50.0,
) -> list[tuple[float, float]]:
    """Simplify a list of (lat, lon) pairs."""
    pts = [TrajectoryPoint(lat=lat, lon=lon) for lat, lon in coordinates]
    simplified = douglas_peucker(pts, epsilon_m=epsilon_m)
    return [(p.lat, p.lon) for p in simplified]
