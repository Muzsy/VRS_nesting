#!/usr/bin/env python3
"""Smoke proof: real DXF pairs -> fixture rings + golden NFP equality."""

from __future__ import annotations

import importlib.util
import json
import subprocess
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
STOCK_REL = "samples/dxf_demo/stock_rect_1000x2000.dxf"
PART_REL = "samples/dxf_demo/part_arc_spline_chaining_ok.dxf"
FIXTURE_PATHS = [
    ROOT / "poc" / "nfp_regression" / "real_dxf_pair_01_stock_x_part.json",
    ROOT / "poc" / "nfp_regression" / "real_dxf_pair_02_part_x_stock.json",
    ROOT / "poc" / "nfp_regression" / "real_dxf_pair_03_part_x_part.json",
]


def _require_ezdxf() -> None:
    if importlib.util.find_spec("ezdxf") is None:
        raise AssertionError(
            "ezdxf dependency missing for real DXF smoke. "
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


def _load_fixture(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise AssertionError(f"missing fixture: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid fixture JSON {path}: line={exc.lineno} col={exc.colno}") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"fixture top-level must be object: {path}")
    return payload


def _build_project() -> DxfProjectModel:
    return DxfProjectModel(
        version="dxf_v1",
        name="nfp_real_dxf_pairs_smoke",
        seed=0,
        time_limit_s=20,
        units="mm",
        spacing_mm=0.0,
        margin_mm=0.0,
        stocks_dxf=[DxfAssetSpec(id="stock_1", path=STOCK_REL, quantity=1, allowed_rotations_deg=[0])],
        parts_dxf=[DxfAssetSpec(id="part_1", path=PART_REL, quantity=1, allowed_rotations_deg=[0])],
    )


def _ensure_nfp_fixture_bin() -> Path:
    cargo_manifest = ROOT / "rust" / "nesting_engine" / "Cargo.toml"
    bin_path = ROOT / "rust" / "nesting_engine" / "target" / "release" / "nfp_fixture"
    if bin_path.is_file():
        return bin_path

    cmd = [
        "cargo",
        "build",
        "--release",
        "--manifest-path",
        str(cargo_manifest),
        "--bin",
        "nfp_fixture",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise AssertionError(
            "failed to build nfp_fixture: "
            f"rc={proc.returncode} stderr={proc.stderr.strip()}"
        )
    if not bin_path.is_file():
        raise AssertionError(f"nfp_fixture binary missing after build: {bin_path}")
    return bin_path


def _compute_nfp(bin_path: Path, fixture_payload: dict[str, Any]) -> dict[str, Any]:
    proc = subprocess.run(
        [str(bin_path)],
        cwd=ROOT,
        input=json.dumps(fixture_payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"nfp_fixture failed rc={proc.returncode}: {proc.stderr.strip()}")
    if not proc.stdout.strip():
        raise AssertionError("nfp_fixture produced empty stdout")
    try:
        output = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"invalid nfp_fixture stdout JSON: line={exc.lineno} col={exc.colno}") from exc
    if not isinstance(output, dict):
        raise AssertionError("nfp_fixture stdout top-level must be object")
    return output


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

    holes = parts[0].get("holes_points")
    if not isinstance(holes, list) or len(holes) < 1:
        raise AssertionError("expected at least one part hole from real DXF import")

    fixtures = [_load_fixture(path) for path in FIXTURE_PATHS]

    expected_pairs = [
        (stock_outer, part_outer),
        (part_outer, stock_outer),
        (part_outer, part_outer),
    ]

    for idx, fixture in enumerate(fixtures):
        expected_a, expected_b = expected_pairs[idx]
        polygon_a = fixture.get("polygon_a")
        polygon_b = fixture.get("polygon_b")
        if polygon_a != expected_a:
            raise AssertionError(f"fixture #{idx + 1} polygon_a mismatch vs DXF canonical ring")
        if polygon_b != expected_b:
            raise AssertionError(f"fixture #{idx + 1} polygon_b mismatch vs DXF canonical ring")

    bin_path = _ensure_nfp_fixture_bin()

    for idx, fixture in enumerate(fixtures):
        output = _compute_nfp(bin_path, fixture)
        expected_nfp = fixture.get("expected_nfp")
        expected_vertex_count = fixture.get("expected_vertex_count")

        if output.get("nfp_outer") != expected_nfp:
            raise AssertionError(f"fixture #{idx + 1} computed NFP != expected_nfp")
        if output.get("vertex_count") != expected_vertex_count:
            raise AssertionError(f"fixture #{idx + 1} vertex_count mismatch")

    print("[OK] real DXF NFP pairs smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
