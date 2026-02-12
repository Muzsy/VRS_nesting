#!/usr/bin/env python3
"""Polygonize + clean helpers for part and stock raw geometries."""

from __future__ import annotations

from typing import Any

from vrs_nesting.geometry.clean import clean_ring


def _clean_holes(raw_holes: Any, *, min_edge_len: float, where: str) -> list[list[list[float]]]:
    if raw_holes is None:
        return []
    if not isinstance(raw_holes, list):
        raise ValueError(f"{where} must be list")

    holes: list[list[list[float]]] = []
    for idx, hole in enumerate(raw_holes):
        holes.append(clean_ring(hole, min_edge_len=min_edge_len, ccw=False, where=f"{where}[{idx}]"))
    return holes


def polygonize_part_raw(
    payload: dict[str, Any],
    *,
    min_edge_len: float = 1e-6,
) -> dict[str, Any]:
    outer_raw = payload.get("outer_points_mm")
    holes_raw = payload.get("holes_points_mm", [])

    outer = clean_ring(outer_raw, min_edge_len=min_edge_len, ccw=True, where="part.outer_points_mm")
    holes = _clean_holes(holes_raw, min_edge_len=min_edge_len, where="part.holes_points_mm")

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

    outer = clean_ring(outer_raw, min_edge_len=min_edge_len, ccw=True, where="stock.outer_points_mm")
    holes = _clean_holes(holes_raw, min_edge_len=min_edge_len, where="stock.holes_points_mm")

    return {
        "outer_points_mm": outer,
        "holes_points_mm": holes,
    }
