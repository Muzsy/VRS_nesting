#!/usr/bin/env python3
"""Geometry ring cleanup utilities for deterministic preprocessing."""

from __future__ import annotations

import math
from typing import Iterable


class GeometryCleanError(ValueError):
    """Deterministic geometry clean error with stable code + message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _as_point(raw: object, where: str) -> tuple[float, float]:
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        raise GeometryCleanError("GEO_POINT_TYPE", f"{where} must be [x, y]")
    x, y = raw
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise GeometryCleanError("GEO_POINT_TYPE", f"{where} coordinates must be numeric")
    return float(x), float(y)


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def points_are_close(a: tuple[float, float], b: tuple[float, float], epsilon: float) -> bool:
    if epsilon < 0:
        raise GeometryCleanError("GEO_PARAM_RANGE", "epsilon must be >= 0")
    return _dist(a, b) <= epsilon


def normalize_input_ring(points: Iterable[object], *, where: str = "ring") -> list[tuple[float, float]]:
    parsed = [_as_point(point, f"{where}[{idx}]") for idx, point in enumerate(points)]
    if len(parsed) < 3:
        raise GeometryCleanError("GEO_RING_TOO_SHORT", f"{where} must contain at least 3 points")

    if parsed[0] == parsed[-1]:
        parsed = parsed[:-1]

    if len(parsed) < 3:
        raise GeometryCleanError("GEO_RING_TOO_SHORT", f"{where} must contain at least 3 unique points")
    return parsed


def dedupe_and_prune_ring(
    points: Iterable[object],
    *,
    min_edge_len: float = 1e-6,
    where: str = "ring",
) -> list[tuple[float, float]]:
    if min_edge_len < 0:
        raise GeometryCleanError("GEO_PARAM_RANGE", "min_edge_len must be >= 0")

    ring = normalize_input_ring(points, where=where)

    deduped: list[tuple[float, float]] = []
    for point in ring:
        if not deduped or _dist(point, deduped[-1]) > 0:
            deduped.append(point)

    if len(deduped) >= 2 and _dist(deduped[0], deduped[-1]) == 0:
        deduped = deduped[:-1]

    if len(deduped) < 3:
        raise GeometryCleanError("GEO_RING_DEGENERATE", f"{where} collapsed after dedupe")

    pruned: list[tuple[float, float]] = [deduped[0]]
    for point in deduped[1:]:
        if _dist(point, pruned[-1]) >= min_edge_len:
            pruned.append(point)

    if len(pruned) >= 2 and _dist(pruned[0], pruned[-1]) < min_edge_len:
        pruned = pruned[:-1]

    if len(pruned) < 3:
        raise GeometryCleanError("GEO_RING_DEGENERATE", f"{where} collapsed after short-edge prune")

    return pruned


def signed_area(points: Iterable[object], *, where: str = "ring") -> float:
    ring = normalize_input_ring(points, where=where)
    area = 0.0
    for idx, (x1, y1) in enumerate(ring):
        x2, y2 = ring[(idx + 1) % len(ring)]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def orient_ring(points: Iterable[object], *, ccw: bool, where: str = "ring") -> list[tuple[float, float]]:
    ring = normalize_input_ring(points, where=where)
    area = signed_area(ring, where=where)
    if ccw and area < 0:
        return list(reversed(ring))
    if not ccw and area > 0:
        return list(reversed(ring))
    return ring


def clean_ring(
    points: Iterable[object],
    *,
    min_edge_len: float = 1e-6,
    ccw: bool | None = None,
    where: str = "ring",
) -> list[list[float]]:
    ring = dedupe_and_prune_ring(points, min_edge_len=min_edge_len, where=where)
    if ccw is not None:
        ring = orient_ring(ring, ccw=ccw, where=where)
    return [[x, y] for x, y in ring]


def close_ring_if_needed(
    points: Iterable[object],
    *,
    close_epsilon: float = 1e-6,
    where: str = "ring",
) -> list[list[float]]:
    if close_epsilon < 0:
        raise GeometryCleanError("GEO_PARAM_RANGE", "close_epsilon must be >= 0")

    ring = normalize_input_ring(points, where=where)
    if not points_are_close(ring[0], ring[-1], close_epsilon):
        raise GeometryCleanError("GEO_RING_OPEN", f"{where} is not closed within epsilon={close_epsilon}")
    return [[x, y] for x, y in ring]
