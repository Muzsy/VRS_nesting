#!/usr/bin/env python3
"""Smoke checks for geometry polygonize + clean + offset pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.geometry.offset import offset_part_geometry, offset_stock_geometry
from vrs_nesting.geometry.polygonize import polygonize_part_raw, polygonize_stock_raw


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_poly(payload: dict, where: str) -> Polygon:
    poly = Polygon(payload["outer_points_mm"], payload.get("holes_points_mm", []))
    if poly.is_empty or not poly.is_valid:
        raise AssertionError(f"{where} polygon invalid")
    return poly


def main() -> int:
    part_raw = _load(ROOT / "samples" / "geometry" / "part_raw_dirty.json")
    stock_raw = _load(ROOT / "samples" / "geometry" / "stock_raw_shape.json")

    part_clean = polygonize_part_raw(part_raw, min_edge_len=1e-4)
    stock_clean = polygonize_stock_raw(stock_raw, min_edge_len=1e-4)

    part_base_poly = _as_poly(part_clean, "part_clean")
    stock_base_poly = _as_poly(stock_clean, "stock_clean")

    if part_base_poly.exterior.is_ccw is not True:
        raise AssertionError("part outer ring must be CCW after clean")

    part_prepared = offset_part_geometry(part_clean, spacing_mm=2.0)
    stock_prepared = offset_stock_geometry(stock_clean, margin_mm=2.0, spacing_mm=2.0)

    part_prepared_poly = _as_poly(part_prepared, "part_prepared")
    stock_prepared_poly = _as_poly(stock_prepared, "stock_prepared")

    if part_prepared_poly.area <= part_base_poly.area:
        raise AssertionError("part offset should increase effective area")
    if stock_prepared_poly.area >= stock_base_poly.area:
        raise AssertionError("stock inset should reduce usable area")

    print("[OK] geometry pipeline smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
