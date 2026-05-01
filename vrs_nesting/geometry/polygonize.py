#!/usr/bin/env python3
"""Polygonize + clean helpers for part and stock raw geometries."""

from __future__ import annotations

import math
from typing import Any

from vrs_nesting.geometry.clean import clean_ring, rdp_tol_mm_from_env

ARC_TOLERANCE_MM = 0.2
CURVE_FLATTEN_TOLERANCE_MM = ARC_TOLERANCE_MM
ARC_POLYGONIZE_MIN_SEGMENTS = 12


def _clean_holes(
    raw_holes: Any,
    *,
    min_edge_len: float,
    where: str,
    simplify_tol_mm: float | None = None,
) -> list[list[list[float]]]:
    if raw_holes is None:
        return []
    if not isinstance(raw_holes, list):
        raise ValueError(f"{where} must be list")

    holes: list[list[list[float]]] = []
    for idx, hole in enumerate(raw_holes):
        holes.append(
            clean_ring(
                hole,
                min_edge_len=min_edge_len,
                ccw=False,
                simplify_tol_mm=simplify_tol_mm,
                where=f"{where}[{idx}]",
            )
        )
    return holes


def polygonize_part_raw(
    payload: dict[str, Any],
    *,
    min_edge_len: float = 1e-6,
) -> dict[str, Any]:
    outer_raw = payload.get("outer_points_mm")
    holes_raw = payload.get("holes_points_mm", [])
    if outer_raw is None:
        raise ValueError("part.outer_points_mm is required")

    simplify_tol_mm = rdp_tol_mm_from_env()
    outer = clean_ring(
        outer_raw,
        min_edge_len=min_edge_len,
        ccw=True,
        simplify_tol_mm=simplify_tol_mm,
        where="part.outer_points_mm",
    )
    holes = _clean_holes(
        holes_raw,
        min_edge_len=min_edge_len,
        where="part.holes_points_mm",
        simplify_tol_mm=simplify_tol_mm,
    )

    return {
        "outer_points_mm": outer,
        "holes_points_mm": holes,
    }


def polygonize_stock_raw(
    payload: dict[str, Any],
    *,
    min_edge_len: float = 1e-6,
) -> dict[str, Any]:
    outer_raw = payload.get("outer_points_mm")
    holes_raw = payload.get("holes_points_mm", [])
    if outer_raw is None:
        raise ValueError("stock.outer_points_mm is required")

    simplify_tol_mm = rdp_tol_mm_from_env()
    outer = clean_ring(
        outer_raw,
        min_edge_len=min_edge_len,
        ccw=True,
        simplify_tol_mm=simplify_tol_mm,
        where="stock.outer_points_mm",
    )
    holes = _clean_holes(
        holes_raw,
        min_edge_len=min_edge_len,
        where="stock.holes_points_mm",
        simplify_tol_mm=simplify_tol_mm,
    )

    return {
        "outer_points_mm": outer,
        "holes_points_mm": holes,
    }


def arc_to_points(
    *,
    center_x: float,
    center_y: float,
    radius: float,
    start_angle_deg: float,
    end_angle_deg: float,
    max_chord_error_mm: float = CURVE_FLATTEN_TOLERANCE_MM,
    min_segments: int = ARC_POLYGONIZE_MIN_SEGMENTS,
    wrap_ccw: bool = False,
) -> list[list[float]]:
    if radius <= 0:
        raise ValueError("radius must be > 0")
    if max_chord_error_mm <= 0:
        raise ValueError("max_chord_error_mm must be > 0")
    if min_segments < 2:
        raise ValueError("min_segments must be >= 2")

    raw_span_deg = float(end_angle_deg) - float(start_angle_deg)
    if wrap_ccw:
        # DXF ARC is always CCW; end < start means wrap around 360°
        span_deg = raw_span_deg % 360.0
        if abs(span_deg) < 1e-9:
            span_deg = 360.0
        direction = 1.0
    else:
        span_deg = raw_span_deg
        if abs(span_deg) < 1e-9:
            span_deg = 360.0
        direction = 1.0 if span_deg >= 0 else -1.0
    span_rad = math.radians(abs(span_deg))

    if max_chord_error_mm >= 2 * radius:
        max_step = span_rad
    else:
        max_step = 2.0 * math.acos(max(0.0, 1.0 - (max_chord_error_mm / radius)))
    max_step = max(max_step, 1e-6)

    segments = max(min_segments, int(math.ceil(span_rad / max_step)))

    points: list[list[float]] = []
    start_rad = math.radians(start_angle_deg)
    step = span_rad / float(segments)
    for idx in range(segments + 1):
        angle = start_rad + (direction * step * idx)
        x = center_x + (radius * math.cos(angle))
        y = center_y + (radius * math.sin(angle))
        points.append([float(x), float(y)])
    return points
