#!/usr/bin/env python3
"""Geometry ring cleanup utilities for deterministic preprocessing."""

from __future__ import annotations

import math
import os
from typing import Iterable

POINT_CLOSE_EPSILON = 1e-9
AREA_MIN_EPSILON = 1e-12

# RDP-simplify opt-in tolerance (mm). Read once per call via the helper
# `rdp_tol_mm_from_env()`; default (unset / invalid / <= 0) disables
# simplification entirely so baseline behavior is unchanged.
RDP_SIMPLIFY_ENV_VAR = "NESTING_ENGINE_RDP_SIMPLIFY_TOL_MM"
# Upper bound: we refuse tolerances above this because they risk collapsing
# real feature geometry; the CAD import tolerance (0.2 mm) is the intended
# operating range, and anything beyond 1.0 mm should be an explicit decision.
RDP_SIMPLIFY_MAX_TOL_MM = 1.0


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
    xf = float(x)
    yf = float(y)
    if not math.isfinite(xf) or not math.isfinite(yf):
        raise GeometryCleanError("GEO_POINT_TYPE", f"{where} coordinates must be finite")
    return xf, yf


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def points_are_close(a: tuple[float, float], b: tuple[float, float], epsilon: float) -> bool:
    if epsilon < 0:
        raise GeometryCleanError("GEO_PARAM_RANGE", "epsilon must be >= 0")
    return _dist(a, b) <= epsilon


def normalize_input_ring(
    points: Iterable[object],
    *,
    where: str = "ring",
    close_epsilon: float = POINT_CLOSE_EPSILON,
) -> list[tuple[float, float]]:
    if close_epsilon < 0:
        raise GeometryCleanError("GEO_PARAM_RANGE", "close_epsilon must be >= 0")

    parsed = [_as_point(point, f"{where}[{idx}]") for idx, point in enumerate(points)]
    if len(parsed) < 3:
        raise GeometryCleanError("GEO_RING_TOO_SHORT", f"{where} must contain at least 3 points")

    if points_are_close(parsed[0], parsed[-1], close_epsilon):
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

    dedupe_epsilon = max(float(min_edge_len), POINT_CLOSE_EPSILON)
    ring = normalize_input_ring(points, where=where, close_epsilon=dedupe_epsilon)

    deduped: list[tuple[float, float]] = []
    for point in ring:
        if not deduped or _dist(point, deduped[-1]) >= dedupe_epsilon:
            deduped.append(point)

    if len(deduped) >= 2 and _dist(deduped[0], deduped[-1]) < dedupe_epsilon:
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


def _signed_area_tuples(ring: list[tuple[float, float]]) -> float:
    """Shoelace area on a tuple-list ring (no normalization, no copy)."""
    n = len(ring)
    if n < 3:
        return 0.0
    area = 0.0
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def _rdp_open_polyline(
    points: list[tuple[float, float]],
    tol_mm: float,
) -> list[tuple[float, float]]:
    """Iterative (stack-based) Ramer-Douglas-Peucker on an open polyline.

    Deterministic: inner loop uses a fixed ascending index range, so on
    equal-distance ties the earliest index wins, and stack-order of
    processing does not affect the final `keep` set.
    """
    n = len(points)
    if n < 3:
        return list(points)
    keep = [False] * n
    keep[0] = True
    keep[n - 1] = True
    tol2 = tol_mm * tol_mm
    stack: list[tuple[int, int]] = [(0, n - 1)]
    while stack:
        i0, i1 = stack.pop()
        if i1 - i0 < 2:
            continue
        ax, ay = points[i0]
        bx, by = points[i1]
        abx = bx - ax
        aby = by - ay
        seg_len2 = abx * abx + aby * aby
        max_d2 = 0.0
        max_i = -1
        for i in range(i0 + 1, i1):
            px, py = points[i]
            if seg_len2 > 0.0:
                cross = (px - ax) * aby - (py - ay) * abx
                d2 = (cross * cross) / seg_len2
            else:
                # Degenerate anchor segment: distance from anchor point a.
                dx = px - ax
                dy = py - ay
                d2 = dx * dx + dy * dy
            if d2 > max_d2:
                max_d2 = d2
                max_i = i
        if max_d2 > tol2 and max_i >= 0:
            keep[max_i] = True
            stack.append((i0, max_i))
            stack.append((max_i, i1))
    return [points[i] for i in range(n) if keep[i]]


def simplify_ring_rdp(
    points: list[tuple[float, float]],
    tol_mm: float,
    *,
    where: str = "ring",
) -> list[tuple[float, float]]:
    """Ramer-Douglas-Peucker simplification on a closed ring.

    For closed rings we pick two anchor vertices -- index 0 and the vertex
    farthest from index 0 -- split the ring into two open polylines at
    those anchors, apply RDP to each half, and concatenate. This preserves
    the ring's "topology" (start/close) without breaking determinism.

    If the simplified ring would drop below 3 vertices or collapse to
    near-zero area, this function returns the input unchanged. That means
    opting in to RDP can never produce a degenerate ring error that the
    un-simplified pipeline would not also produce.
    """
    if tol_mm <= 0.0:
        return list(points)
    n = len(points)
    if n < 4:
        return list(points)

    # Pick the vertex farthest from index 0 as the second RDP anchor.
    # Ties: earliest index wins (deterministic).
    far_idx = 0
    far_d2 = 0.0
    ax, ay = points[0]
    for i in range(1, n):
        dx = points[i][0] - ax
        dy = points[i][1] - ay
        d2 = dx * dx + dy * dy
        if d2 > far_d2:
            far_d2 = d2
            far_idx = i
    if far_idx == 0:
        return list(points)

    # Half A: index 0 .. far_idx (open polyline with both endpoints kept).
    half_a = _rdp_open_polyline(points[0:far_idx + 1], tol_mm)
    # Half B: index far_idx .. n-1 .. 0 (wraps around the ring, also open).
    half_b = _rdp_open_polyline(points[far_idx:] + [points[0]], tol_mm)

    # Drop the shared endpoints: half_a ends with points[far_idx], half_b
    # starts with points[far_idx] and ends with points[0]. Concatenate as
    # open segments and drop the trailing points[0] to return an unclosed
    # ring (matches input convention).
    simplified = half_a[:-1] + half_b[:-1]

    if len(simplified) < 3:
        return list(points)

    # Degenerate area guard: keep the original ring rather than throwing,
    # so the opt-in flag can't introduce a GEO_RING_DEGENERATE that would
    # otherwise not occur.
    if abs(_signed_area_tuples(simplified)) < AREA_MIN_EPSILON:
        return list(points)

    return simplified


def rdp_tol_mm_from_env() -> float | None:
    """Return the RDP-simplify tolerance from the environment, or None.

    Returns None if the env var is unset, empty, non-numeric, non-finite,
    or out of the accepted range (0, RDP_SIMPLIFY_MAX_TOL_MM]. A None
    return value signals "do not apply RDP" so callers can preserve
    baseline behavior by default.
    """
    raw = os.environ.get(RDP_SIMPLIFY_ENV_VAR)
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        tol = float(raw)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(tol):
        return None
    if tol <= 0.0 or tol > RDP_SIMPLIFY_MAX_TOL_MM:
        return None
    return tol


def clean_ring(
    points: Iterable[object],
    *,
    min_edge_len: float = 1e-6,
    ccw: bool | None = None,
    simplify_tol_mm: float | None = None,
    where: str = "ring",
) -> list[list[float]]:
    ring = dedupe_and_prune_ring(points, min_edge_len=min_edge_len, where=where)
    if simplify_tol_mm is not None and simplify_tol_mm > 0.0:
        ring = simplify_ring_rdp(ring, simplify_tol_mm, where=where)
    if ccw is not None:
        ring = orient_ring(ring, ccw=ccw, where=where)
    area_epsilon = max(float(min_edge_len) * float(min_edge_len), AREA_MIN_EPSILON)
    if abs(signed_area(ring, where=where)) < area_epsilon:
        raise GeometryCleanError("GEO_RING_DEGENERATE", f"{where} has near-zero area")
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
