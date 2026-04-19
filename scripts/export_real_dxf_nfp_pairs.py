#!/usr/bin/env python3
"""Export 3 real-DXF NFP fixture skeletons (outer-only) for F2-2 proof."""

from __future__ import annotations

import importlib.util
import json
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.project.model import DxfAssetSpec, DxfProjectModel
from vrs_nesting.sparrow.input_generator import build_sparrow_inputs

SCALE = Decimal("1000000")
FIXTURE_DIR = ROOT / "poc" / "nfp_regression"

STOCK_REL = "samples/dxf_demo/stock_rect_1000x2000.dxf"
PART_REL = "samples/dxf_demo/part_arc_spline_chaining_ok.dxf"


def _require_ezdxf() -> None:
    if importlib.util.find_spec("ezdxf") is None:
        raise AssertionError(
            "ezdxf dependency missing for real DXF export. "
            "Install with: python3 -m pip install --break-system-packages ezdxf"
        )


def _round_half_away_from_zero(value_mm: float) -> int:
    scaled = Decimal(str(value_mm)) * SCALE
    if scaled >= 0:
        return int(scaled.to_integral_value(rounding=ROUND_HALF_UP))
    return -int((-scaled).to_integral_value(rounding=ROUND_HALF_UP))


def _signed_area2(points: list[list[int]]) -> int:
    area2 = 0
    for idx in range(len(points)):
        x0, y0 = points[idx]
        x1, y1 = points[(idx + 1) % len(points)]
        area2 += x0 * y1 - x1 * y0
    return area2


def _canonical_ring_from_mm(points_mm: list[list[float]]) -> list[list[int]]:
    ring: list[list[int]] = []
    for x_mm, y_mm in points_mm:
        pt = [_round_half_away_from_zero(float(x_mm)), _round_half_away_from_zero(float(y_mm))]
        if not ring or ring[-1] != pt:
            ring.append(pt)

    if len(ring) > 1 and ring[0] == ring[-1]:
        ring.pop()

    if len(ring) < 3:
        raise AssertionError(f"ring too short after canonical conversion: {ring}")

    if _signed_area2(ring) < 0:
        ring.reverse()

    start_idx = min(range(len(ring)), key=lambda idx: (ring[idx][0], ring[idx][1]))
    return ring[start_idx:] + ring[:start_idx]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _build_project() -> DxfProjectModel:
    return DxfProjectModel(
        version="dxf_v1",
        name="nfp_real_dxf_pairs_export",
        seed=0,
        time_limit_s=20,
        units="mm",
        spacing_mm=0.0,
        margin_mm=0.0,
        stocks_dxf=[
            DxfAssetSpec(
                id="stock_1",
                path=STOCK_REL,
                quantity=1,
                allowed_rotations_deg=[0],
            )
        ],
        parts_dxf=[
            DxfAssetSpec(
                id="part_1",
                path=PART_REL,
                quantity=1,
                allowed_rotations_deg=[0],
            )
        ],
    )


def main() -> int:
    _require_ezdxf()

    stock_path = ROOT / STOCK_REL
    part_path = ROOT / PART_REL
    if not stock_path.is_file():
        raise AssertionError(f"missing stock fixture: {stock_path}")
    if not part_path.is_file():
        raise AssertionError(f"missing part fixture: {part_path}")

    project = _build_project()
    _, solver_input, _ = build_sparrow_inputs(project, project_dir=ROOT)

    stocks = solver_input.get("stocks")
    parts = solver_input.get("parts")
    if not isinstance(stocks, list) or not stocks:
        raise AssertionError("solver_input.stocks missing or empty")
    if not isinstance(parts, list) or not parts:
        raise AssertionError("solver_input.parts missing or empty")

    stock_outer = _canonical_ring_from_mm(stocks[0]["outer_points"])
    part_outer = _canonical_ring_from_mm(parts[0]["outer_points"])

    fixtures: list[tuple[str, str, list[list[int]], str, list[list[int]], str]] = [
        (
            "real_dxf_pair_01_stock_x_part.json",
            "Real DXF pair #01: stock x part (outer-only)",
            stock_outer,
            STOCK_REL,
            part_outer,
            PART_REL,
        ),
        (
            "real_dxf_pair_02_part_x_stock.json",
            "Real DXF pair #02: part x stock (outer-only)",
            part_outer,
            PART_REL,
            stock_outer,
            STOCK_REL,
        ),
        (
            "real_dxf_pair_03_part_x_part.json",
            "Real DXF pair #03: part x part (outer-only)",
            part_outer,
            PART_REL,
            part_outer,
            PART_REL,
        ),
    ]

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    for filename, description, polygon_a, source_dxf_a, polygon_b, source_dxf_b in fixtures:
        payload: dict[str, Any] = {
            "description": description,
            "fixture_type": "convex",
            "polygon_a": polygon_a,
            "polygon_b": polygon_b,
            "rotation_deg_b": 0,
            "expected_nfp": [],
            "expected_vertex_count": 0,
            "source_dxf_a": source_dxf_a,
            "source_dxf_b": source_dxf_b,
            "note_outer_only": True,
        }
        out_path = FIXTURE_DIR / filename
        _write_json(out_path, payload)

    print("[OK] real DXF NFP pair fixture skeletons exported")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
