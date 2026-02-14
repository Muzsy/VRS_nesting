#!/usr/bin/env python3
"""Spacing/margin offset helpers for prepared part and stock geometries."""

from __future__ import annotations

from typing import Any

from shapely.geometry import MultiPolygon, Polygon
from shapely.ops import unary_union


class GeometryOffsetError(ValueError):
    """Deterministic geometry offset error with stable code + message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _to_closed_ring(points: Any, where: str) -> list[tuple[float, float]]:
    if not isinstance(points, list):
        raise GeometryOffsetError("GEO_POLYGON_TYPE", f"{where} must be list")
    ring: list[tuple[float, float]] = []
    for idx, point in enumerate(points):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise GeometryOffsetError("GEO_POLYGON_TYPE", f"{where}[{idx}] must be [x, y]")
        x, y = point
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise GeometryOffsetError("GEO_POLYGON_TYPE", f"{where}[{idx}] coordinates must be numeric")
        ring.append((float(x), float(y)))

    if len(ring) < 3:
        raise GeometryOffsetError("GEO_POLYGON_RANGE", f"{where} must have at least 3 points")

    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def _as_polygon(outer_points: Any, holes_points: Any, where: str) -> Polygon:
    outer = _to_closed_ring(outer_points, f"{where}.outer")

    holes: list[list[tuple[float, float]]] = []
    if holes_points is not None:
        if not isinstance(holes_points, list):
            raise GeometryOffsetError("GEO_POLYGON_TYPE", f"{where}.holes must be list")
        for idx, hole in enumerate(holes_points):
            holes.append(_to_closed_ring(hole, f"{where}.holes[{idx}]"))

    polygon = Polygon(outer, holes)
    if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
        raise GeometryOffsetError("GEO_POLYGON_INVALID", f"{where} polygon invalid or empty")
    return polygon


def _largest_polygon(geom: Any, where: str) -> Polygon:
    if geom is None or geom.is_empty:
        raise GeometryOffsetError("GEO_OFFSET_EMPTY", f"{where} geometry became empty after offset")

    if isinstance(geom, Polygon):
        return geom

    if isinstance(geom, MultiPolygon):
        biggest = max(geom.geoms, key=lambda p: p.area, default=None)
        if biggest is None or biggest.is_empty:
            raise GeometryOffsetError("GEO_OFFSET_EMPTY", f"{where} multipolygon has no usable area")
        return biggest

    if hasattr(geom, "geoms"):
        polys = [g for g in geom.geoms if isinstance(g, Polygon)]
        if not polys:
            raise GeometryOffsetError("GEO_OFFSET_EMPTY", f"{where} has no polygon output")
        return max(polys, key=lambda p: p.area)

    raise GeometryOffsetError("GEO_OFFSET_TYPE", f"{where} returned unsupported geometry type")


def _polygon_to_payload(poly: Polygon) -> dict[str, Any]:
    outer = [[float(x), float(y)] for x, y in list(poly.exterior.coords)[:-1]]
    holes = [
        [[float(x), float(y)] for x, y in list(ring.coords)[:-1]]
        for ring in poly.interiors
    ]
    return {
        "outer_points_mm": outer,
        "holes_points_mm": holes,
    }


def polygon_bbox(payload: dict[str, Any]) -> tuple[float, float, float, float]:
    outer = payload.get("outer_points_mm")
    if not isinstance(outer, list) or not outer:
        raise GeometryOffsetError("GEO_POLYGON_TYPE", "outer_points_mm must be non-empty list")
    ring = _to_closed_ring(outer, "bbox.outer")
    xs = [pt[0] for pt in ring[:-1]]
    ys = [pt[1] for pt in ring[:-1]]
    return min(xs), min(ys), max(xs), max(ys)


def offset_part_geometry(
    payload: dict[str, Any],
    *,
    spacing_mm: float,
) -> dict[str, Any]:
    if spacing_mm < 0:
        raise GeometryOffsetError("GEO_PARAM_RANGE", "spacing_mm must be >= 0")

    base = _as_polygon(payload.get("outer_points_mm"), payload.get("holes_points_mm", []), "part")
    dist = float(spacing_mm) / 2.0
    expanded = base.buffer(dist, join_style="mitre")
    poly = _largest_polygon(expanded, "part")
    return _polygon_to_payload(poly)


def offset_stock_geometry(
    payload: dict[str, Any],
    *,
    margin_mm: float,
    spacing_mm: float,
) -> dict[str, Any]:
    if margin_mm < 0:
        raise GeometryOffsetError("GEO_PARAM_RANGE", "margin_mm must be >= 0")
    if spacing_mm < 0:
        raise GeometryOffsetError("GEO_PARAM_RANGE", "spacing_mm must be >= 0")

    clearance = float(margin_mm) + (float(spacing_mm) / 2.0)
    base = _as_polygon(payload.get("outer_points_mm"), payload.get("holes_points_mm", []), "stock")

    usable_outer = _largest_polygon(base.buffer(-clearance, join_style="mitre"), "stock.outer")

    holes_payload = payload.get("holes_points_mm", [])
    expanded_holes = []
    for idx, hole in enumerate(holes_payload):
        hpoly = _as_polygon(hole, [], f"stock.hole[{idx}]")
        expanded_holes.append(hpoly.buffer(clearance, join_style="mitre"))

    if expanded_holes:
        usable = usable_outer.difference(unary_union(expanded_holes))
    else:
        usable = usable_outer

    poly = _largest_polygon(usable, "stock.usable")
    return _polygon_to_payload(poly)
