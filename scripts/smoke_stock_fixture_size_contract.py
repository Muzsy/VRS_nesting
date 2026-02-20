#!/usr/bin/env python3
"""Smoke check: stock_rect_1000x2000 fixture should resolve to ~1000x2000 mm stock."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.project.model import DxfAssetSpec, DxfProjectModel
from vrs_nesting.sparrow.input_generator import build_sparrow_inputs


def _assert_close(actual: float, expected: float, *, tol: float, label: str) -> None:
    if abs(actual - expected) > tol:
        raise AssertionError(f"{label} mismatch: expected ~{expected} mm (+/- {tol}), got {actual} mm")


def main() -> int:
    stock_fixture = ROOT / "samples" / "dxf_demo" / "stock_rect_1000x2000.dxf"
    part_fixture = ROOT / "samples" / "dxf_demo" / "part_arc_spline_chaining_ok.dxf"
    if not stock_fixture.is_file():
        raise AssertionError(f"missing fixture: {stock_fixture}")
    if not part_fixture.is_file():
        raise AssertionError(f"missing fixture: {part_fixture}")

    project = DxfProjectModel(
        version="dxf_v1",
        name="smoke_stock_fixture_size_contract",
        seed=0,
        time_limit_s=10,
        units="mm",
        spacing_mm=0.0,
        margin_mm=0.0,
        stocks_dxf=[DxfAssetSpec(id="stock_1", path=str(stock_fixture), quantity=1, allowed_rotations_deg=[0])],
        parts_dxf=[DxfAssetSpec(id="part_1", path=str(part_fixture), quantity=1, allowed_rotations_deg=[0])],
    )

    _sparrow_instance, solver_input, _meta = build_sparrow_inputs(project, project_dir=ROOT)
    stocks = solver_input.get("stocks")
    if not isinstance(stocks, list) or not stocks:
        raise AssertionError("solver_input.stocks is empty")
    stock = stocks[0]
    width = float(stock.get("width") or 0.0)
    height = float(stock.get("height") or 0.0)
    if width <= 0 or height <= 0:
        raise AssertionError(f"invalid stock dimensions: width={width}, height={height}")

    _assert_close(width, 1000.0, tol=1.0, label="stock width")
    _assert_close(height, 2000.0, tol=1.0, label="stock height")

    print("[OK] stock fixture size contract passed")
    print(f" width_mm={width}")
    print(f" height_mm={height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
