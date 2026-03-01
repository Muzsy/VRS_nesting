#!/usr/bin/env python3
"""Generate real-DXF-derived outer-only fixtures for nesting_engine_v2 quality benchmark."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from vrs_nesting.project.model import DxfAssetSpec, DxfProjectModel
from vrs_nesting.sparrow.input_generator import build_sparrow_inputs

DEFAULT_STOCK_REL = "samples/dxf_demo/stock_rect_1000x2000.dxf"
DEFAULT_PART_REL = "samples/dxf_demo/part_arc_spline_chaining_ok.dxf"
DEFAULT_OUT_200 = "poc/nesting_engine/real_dxf_quality_200_outer_only_v2.json"
DEFAULT_OUT_500 = "poc/nesting_engine/real_dxf_quality_500_outer_only_v2.json"
DEFAULT_TIME_LIMIT_SEC = 300
DEFAULT_SEED = 77
DEFAULT_KERF_MM = 0.2
DEFAULT_SPACING_MM = 2.0
DEFAULT_MARGIN_MM = 5.0
DEFAULT_ROTATIONS = [0, 90, 180, 270]


def _require_ezdxf() -> None:
    if importlib.util.find_spec("ezdxf") is None:
        raise AssertionError(
            "ezdxf dependency missing for real DXF fixture generation. "
            "Install with: python3 -m pip install --break-system-packages ezdxf"
        )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _as_points(value: Any, where: str) -> list[list[float]]:
    if not isinstance(value, list):
        raise AssertionError(f"{where} must be an array")
    out: list[list[float]] = []
    for idx, point in enumerate(value):
        if not isinstance(point, list) or len(point) != 2:
            raise AssertionError(f"{where}[{idx}] must be [x,y]")
        x_raw, y_raw = point
        if isinstance(x_raw, bool) or isinstance(y_raw, bool):
            raise AssertionError(f"{where}[{idx}] must be numeric")
        if not isinstance(x_raw, (int, float)) or not isinstance(y_raw, (int, float)):
            raise AssertionError(f"{where}[{idx}] must be numeric")
        out.append([float(x_raw), float(y_raw)])
    return out


def _signed_area2(points: list[list[float]]) -> float:
    area2 = 0.0
    for idx in range(len(points)):
        x0, y0 = points[idx]
        x1, y1 = points[(idx + 1) % len(points)]
        area2 += x0 * y1 - x1 * y0
    return area2


def _normalize_number(value: float) -> float | int:
    rounded_int = round(value)
    if abs(value - rounded_int) < 1e-9:
        return int(rounded_int)
    rounded = round(value, 6)
    rounded_int = round(rounded)
    if abs(rounded - rounded_int) < 1e-9:
        return int(rounded_int)
    return rounded


def _canonical_ring_mm(points_mm: list[list[float]], *, ensure_ccw: bool) -> list[list[float | int]]:
    ring: list[list[float]] = []
    for x_mm, y_mm in points_mm:
        point = [float(x_mm), float(y_mm)]
        if not ring or ring[-1] != point:
            ring.append(point)

    if len(ring) > 1 and ring[0] == ring[-1]:
        ring.pop()

    if len(ring) < 3:
        raise AssertionError(f"ring too short after dedupe: len={len(ring)}")

    if ensure_ccw and _signed_area2(ring) < 0.0:
        ring.reverse()

    min_x = min(point[0] for point in ring)
    min_y = min(point[1] for point in ring)
    shifted = [[point[0] - min_x, point[1] - min_y] for point in ring]

    start_idx = min(range(len(shifted)), key=lambda idx: (shifted[idx][0], shifted[idx][1]))
    ordered = shifted[start_idx:] + shifted[:start_idx]
    return [[_normalize_number(x), _normalize_number(y)] for x, y in ordered]


def _aabb_size(points_mm: list[list[float | int]]) -> tuple[float | int, float | int]:
    xs = [float(point[0]) for point in points_mm]
    ys = [float(point[1]) for point in points_mm]
    width = _normalize_number(max(xs) - min(xs))
    height = _normalize_number(max(ys) - min(ys))
    if float(width) <= 0.0 or float(height) <= 0.0:
        raise AssertionError(f"invalid non-positive sheet size from stock polygon: {width}x{height}")
    return width, height


def _build_project(
    stock_rel: str,
    part_rel: str,
    spacing_mm: float,
    margin_mm: float,
) -> DxfProjectModel:
    return DxfProjectModel(
        version="dxf_v1",
        name="nesting_engine_real_dxf_quality_fixture_gen",
        seed=0,
        time_limit_s=20,
        units="mm",
        spacing_mm=spacing_mm,
        margin_mm=margin_mm,
        stocks_dxf=[
            DxfAssetSpec(
                id="stock_1",
                path=stock_rel,
                quantity=1,
                allowed_rotations_deg=[0],
            )
        ],
        parts_dxf=[
            DxfAssetSpec(
                id="part_1",
                path=part_rel,
                quantity=1,
                allowed_rotations_deg=[0],
            )
        ],
    )


def _build_fixture_payload(
    *,
    stock_outer_mm: list[list[float | int]],
    part_outer_mm: list[list[float | int]],
    count: int,
    time_limit_sec: int,
    seed: int,
    kerf_mm: float,
    spacing_mm: float,
    margin_mm: float,
    rotations: list[int],
) -> dict[str, Any]:
    if count <= 0:
        raise AssertionError("count must be > 0")
    if time_limit_sec <= 0:
        raise AssertionError("time_limit_sec must be > 0")
    if seed < 0:
        raise AssertionError("seed must be >= 0")
    if not rotations:
        raise AssertionError("allowed rotations must not be empty")

    width_mm, height_mm = _aabb_size(stock_outer_mm)
    parts: list[dict[str, Any]] = []
    for idx in range(1, count + 1):
        parts.append(
            {
                "id": f"real_dxf_part__i{idx:06d}",
                "quantity": 1,
                "allowed_rotations_deg": list(rotations),
                "outer_points_mm": part_outer_mm,
                "holes_points_mm": [],
            }
        )

    return {
        "version": "nesting_engine_v2",
        "seed": int(seed),
        "time_limit_sec": int(time_limit_sec),
        "sheet": {
            "width_mm": width_mm,
            "height_mm": height_mm,
            "kerf_mm": float(kerf_mm),
            "margin_mm": float(margin_mm),
            "spacing_mm": float(spacing_mm),
        },
        "parts": parts,
    }


def _resolve_rel(path_value: str) -> str:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = (ROOT / candidate).resolve()
    if not candidate.is_file():
        raise AssertionError(f"missing DXF input: {path_value}")
    try:
        return str(candidate.relative_to(ROOT))
    except ValueError:
        return str(candidate)


def _parse_rotations(value: str) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    chunks = [chunk.strip() for chunk in value.split(",") if chunk.strip()]
    if not chunks:
        raise AssertionError("--rotations must contain at least one integer")
    for chunk in chunks:
        try:
            rot = int(chunk)
        except ValueError as exc:
            raise AssertionError(f"invalid rotation value: {chunk!r}") from exc
        rot_norm = rot % 360
        if rot_norm not in {0, 90, 180, 270}:
            raise AssertionError(f"rotation must be one of 0,90,180,270 (got {rot})")
        if rot_norm not in seen:
            out.append(rot_norm)
            seen.add(rot_norm)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-dxf", default=DEFAULT_STOCK_REL, help="Stock DXF input path")
    parser.add_argument("--part-dxf", default=DEFAULT_PART_REL, help="Part DXF input path")
    parser.add_argument("--out-200", default=DEFAULT_OUT_200, help="Output fixture JSON for 200 parts")
    parser.add_argument("--out-500", default=DEFAULT_OUT_500, help="Output fixture JSON for 500 parts")
    parser.add_argument(
        "--time-limit-sec",
        type=int,
        default=DEFAULT_TIME_LIMIT_SEC,
        help="time_limit_sec for generated fixtures (default: 300)",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="seed for generated fixtures")
    parser.add_argument("--kerf-mm", type=float, default=DEFAULT_KERF_MM, help="sheet kerf_mm")
    parser.add_argument("--spacing-mm", type=float, default=DEFAULT_SPACING_MM, help="sheet spacing_mm")
    parser.add_argument("--margin-mm", type=float, default=DEFAULT_MARGIN_MM, help="sheet margin_mm")
    parser.add_argument(
        "--rotations",
        default="0,90,180,270",
        help="allowed_rotations_deg CSV, values in {0,90,180,270}",
    )
    args = parser.parse_args(argv)

    _require_ezdxf()
    if args.time_limit_sec <= 0:
        raise AssertionError("--time-limit-sec must be > 0")
    if args.seed < 0:
        raise AssertionError("--seed must be >= 0")
    if args.kerf_mm < 0.0:
        raise AssertionError("--kerf-mm must be >= 0")
    if args.spacing_mm < 0.0:
        raise AssertionError("--spacing-mm must be >= 0")
    if args.margin_mm < 0.0:
        raise AssertionError("--margin-mm must be >= 0")

    stock_rel = _resolve_rel(args.stock_dxf)
    part_rel = _resolve_rel(args.part_dxf)
    out_200 = Path(args.out_200)
    if not out_200.is_absolute():
        out_200 = ROOT / out_200
    out_500 = Path(args.out_500)
    if not out_500.is_absolute():
        out_500 = ROOT / out_500
    rotations = _parse_rotations(args.rotations)

    project = _build_project(
        stock_rel=stock_rel,
        part_rel=part_rel,
        spacing_mm=float(args.spacing_mm),
        margin_mm=float(args.margin_mm),
    )
    _, solver_input, _ = build_sparrow_inputs(project, project_dir=ROOT)

    stocks = solver_input.get("stocks")
    parts = solver_input.get("parts")
    if not isinstance(stocks, list) or not stocks:
        raise AssertionError("solver_input.stocks missing or empty")
    if not isinstance(parts, list) or not parts:
        raise AssertionError("solver_input.parts missing or empty")

    stock_outer_src = _as_points(stocks[0].get("outer_points"), "solver_input.stocks[0].outer_points")
    part_outer_src = _as_points(parts[0].get("outer_points"), "solver_input.parts[0].outer_points")
    stock_outer = _canonical_ring_mm(stock_outer_src, ensure_ccw=True)
    part_outer = _canonical_ring_mm(part_outer_src, ensure_ccw=True)

    fixture_200 = _build_fixture_payload(
        stock_outer_mm=stock_outer,
        part_outer_mm=part_outer,
        count=200,
        time_limit_sec=int(args.time_limit_sec),
        seed=int(args.seed),
        kerf_mm=float(args.kerf_mm),
        spacing_mm=float(args.spacing_mm),
        margin_mm=float(args.margin_mm),
        rotations=rotations,
    )
    fixture_500 = _build_fixture_payload(
        stock_outer_mm=stock_outer,
        part_outer_mm=part_outer,
        count=500,
        time_limit_sec=int(args.time_limit_sec),
        seed=int(args.seed),
        kerf_mm=float(args.kerf_mm),
        spacing_mm=float(args.spacing_mm),
        margin_mm=float(args.margin_mm),
        rotations=rotations,
    )

    _write_json(out_200, fixture_200)
    _write_json(out_500, fixture_500)

    # Basic sanity check to guarantee produced JSON is loadable.
    _read_json(out_200)
    _read_json(out_500)

    print(f"[OK] real DXF quality fixture (200) written: {out_200}")
    print(f"[OK] real DXF quality fixture (500) written: {out_500}")
    print(f"[INFO] stock={stock_rel} part={part_rel}")
    print(f"[INFO] time_limit_sec={args.time_limit_sec} spacing_mm={args.spacing_mm} margin_mm={args.margin_mm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
