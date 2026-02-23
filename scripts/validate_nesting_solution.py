#!/usr/bin/env python3
"""Validate VRS nesting outputs (legacy v1 and nesting_engine v2)."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from vrs_nesting.validate.solution_validator import (  # noqa: E402
    ValidationError as LegacyValidationError,
    resolve_paths as legacy_resolve_paths,
    validate_nesting_solution as legacy_validate_nesting_solution,
)

EPS = 1e-6

try:  # optional, best-effort narrow-phase
    import i_overlay as _i_overlay  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    _i_overlay = None

try:  # optional narrow-phase fallback
    from shapely.geometry import Polygon as _ShapelyPolygon
except Exception:  # pragma: no cover - optional dependency
    _ShapelyPolygon = None


class ValidationError(RuntimeError):
    """Raised when validator detects an invariant violation."""


@dataclass(frozen=True)
class PartSpecV2:
    part_id: str
    outer_points: list[tuple[float, float]]


@dataclass(frozen=True)
class PlacementGeomV2:
    part_id: str
    instance: int
    sheet: int
    points: list[tuple[float, float]]
    bbox: tuple[float, float, float, float]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValidationError(f"missing file: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid json {path}: line={exc.lineno} col={exc.colno}") from exc
    if not isinstance(payload, dict):
        raise ValidationError(f"top-level json object required: {path}")
    return payload


def _parse_point(raw: Any, where: str) -> tuple[float, float]:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValidationError(f"{where} must be [x,y]")
    x, y = raw
    if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
        raise ValidationError(f"{where} coordinates must be numeric")
    return float(x), float(y)


def _parse_outer_points(raw: Any, where: str) -> list[tuple[float, float]]:
    if not isinstance(raw, list) or len(raw) < 3:
        raise ValidationError(f"{where} must be list with at least 3 points")
    points = [_parse_point(pt, f"{where}[{idx}]") for idx, pt in enumerate(raw)]
    return points


def _transform_points(
    points: list[tuple[float, float]],
    rotation_deg: float,
    tx: float,
    ty: float,
) -> list[tuple[float, float]]:
    radians = math.radians(rotation_deg)
    c = math.cos(radians)
    s = math.sin(radians)
    transformed: list[tuple[float, float]] = []
    for px, py in points:
        rx = (px * c) - (py * s)
        ry = (px * s) + (py * c)
        transformed.append((rx + tx, ry + ty))
    return transformed


def _bbox(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [pt[0] for pt in points]
    ys = [pt[1] for pt in points]
    return min(xs), min(ys), max(xs), max(ys)


def _aabb_overlap(
    lhs: tuple[float, float, float, float],
    rhs: tuple[float, float, float, float],
) -> bool:
    lminx, lminy, lmaxx, lmaxy = lhs
    rminx, rminy, rmaxx, rmaxy = rhs
    if lmaxx <= rminx + EPS:
        return False
    if rmaxx <= lminx + EPS:
        return False
    if lmaxy <= rminy + EPS:
        return False
    if rmaxy <= lminy + EPS:
        return False
    return True


def _i_overlay_overlap(
    lhs_points: list[tuple[float, float]],
    rhs_points: list[tuple[float, float]],
) -> bool | None:
    if _i_overlay is None:
        return None
    intersects = getattr(_i_overlay, "intersects", None)
    if not callable(intersects):
        return None
    try:
        return bool(intersects(lhs_points, rhs_points))
    except Exception:  # pragma: no cover - API best-effort
        return None


def _shapely_overlap(
    lhs_points: list[tuple[float, float]],
    rhs_points: list[tuple[float, float]],
) -> bool | None:
    if _ShapelyPolygon is None:
        return None
    try:
        lhs_poly = _ShapelyPolygon(lhs_points)
        rhs_poly = _ShapelyPolygon(rhs_points)
    except Exception:  # pragma: no cover - defensive conversion
        return None
    if lhs_poly.is_empty or rhs_poly.is_empty or not lhs_poly.is_valid or not rhs_poly.is_valid:
        return None
    return bool(lhs_poly.intersection(rhs_poly).area > EPS)


def _build_part_specs_v2(input_payload: dict[str, Any]) -> dict[str, PartSpecV2]:
    if input_payload.get("version") != "nesting_engine_v2":
        raise ValidationError("input.version must be nesting_engine_v2")
    parts = input_payload.get("parts")
    if not isinstance(parts, list) or not parts:
        raise ValidationError("input.parts must be non-empty list")

    specs: dict[str, PartSpecV2] = {}
    for idx, part in enumerate(parts):
        if not isinstance(part, dict):
            raise ValidationError(f"input.parts[{idx}] must be object")
        part_id = str(part.get("id", "")).strip()
        if not part_id:
            raise ValidationError(f"input.parts[{idx}].id must be non-empty")
        if part_id in specs:
            raise ValidationError(f"duplicate part id in input: {part_id}")
        outer_points = _parse_outer_points(part.get("outer_points_mm"), f"input.parts[{idx}].outer_points_mm")
        specs[part_id] = PartSpecV2(part_id=part_id, outer_points=outer_points)
    return specs


def validate_nesting_engine_v2(input_path: Path, output_path: Path) -> None:
    input_payload = _read_json(input_path)
    output_payload = _read_json(output_path)

    part_specs = _build_part_specs_v2(input_payload)

    sheet = input_payload.get("sheet")
    if not isinstance(sheet, dict):
        raise ValidationError("input.sheet must be object")

    width_mm = sheet.get("width_mm")
    height_mm = sheet.get("height_mm")
    margin_mm = sheet.get("margin_mm", 0.0)
    for key, value in (("width_mm", width_mm), ("height_mm", height_mm), ("margin_mm", margin_mm)):
        if not isinstance(value, (int, float)):
            raise ValidationError(f"input.sheet.{key} must be numeric")
    width_mm = float(width_mm)
    height_mm = float(height_mm)
    margin_mm = float(margin_mm)
    if width_mm <= 0 or height_mm <= 0:
        raise ValidationError("input.sheet width/height must be > 0")
    if margin_mm < 0:
        raise ValidationError("input.sheet.margin_mm must be >= 0")

    if output_payload.get("version") != "nesting_engine_v2":
        raise ValidationError("output.version must be nesting_engine_v2")
    placements = output_payload.get("placements")
    if not isinstance(placements, list):
        raise ValidationError("output.placements must be list")

    placed_by_sheet: dict[int, list[PlacementGeomV2]] = defaultdict(list)
    for idx, placement in enumerate(placements):
        if not isinstance(placement, dict):
            raise ValidationError(f"output.placements[{idx}] must be object")
        part_id = str(placement.get("part_id", "")).strip()
        if not part_id:
            raise ValidationError(f"output.placements[{idx}].part_id must be non-empty")
        if part_id not in part_specs:
            raise ValidationError(f"unknown part_id in placement: {part_id}")

        instance = placement.get("instance")
        sheet_index = placement.get("sheet")
        x_mm = placement.get("x_mm")
        y_mm = placement.get("y_mm")
        rotation_deg = placement.get("rotation_deg")

        if not isinstance(instance, int) or instance < 0:
            raise ValidationError(f"output.placements[{idx}].instance must be non-negative int")
        if not isinstance(sheet_index, int) or sheet_index < 0:
            raise ValidationError(f"output.placements[{idx}].sheet must be non-negative int")
        if not isinstance(x_mm, (int, float)) or not isinstance(y_mm, (int, float)):
            raise ValidationError(f"output.placements[{idx}] x_mm/y_mm must be numeric")
        if not isinstance(rotation_deg, (int, float)):
            raise ValidationError(f"output.placements[{idx}].rotation_deg must be numeric")

        transformed = _transform_points(
            part_specs[part_id].outer_points,
            float(rotation_deg),
            float(x_mm),
            float(y_mm),
        )
        bbox = _bbox(transformed)
        min_x, min_y, max_x, max_y = bbox

        lower = margin_mm - EPS
        upper_x = (width_mm - margin_mm) + EPS
        upper_y = (height_mm - margin_mm) + EPS
        if min_x < lower or min_y < lower or max_x > upper_x or max_y > upper_y:
            raise ValidationError(
                "out-of-bounds placement: "
                f"part={part_id} instance={instance} sheet={sheet_index} "
                f"bbox=({min_x:.3f},{min_y:.3f},{max_x:.3f},{max_y:.3f}) "
                f"bounds=({margin_mm:.3f},{margin_mm:.3f},{width_mm - margin_mm:.3f},{height_mm - margin_mm:.3f})"
            )

        placed_by_sheet[sheet_index].append(
            PlacementGeomV2(
                part_id=part_id,
                instance=instance,
                sheet=sheet_index,
                points=transformed,
                bbox=bbox,
            )
        )

    for sheet_index, items in placed_by_sheet.items():
        for left_idx in range(len(items)):
            left = items[left_idx]
            for right_idx in range(left_idx + 1, len(items)):
                right = items[right_idx]
                if not _aabb_overlap(left.bbox, right.bbox):
                    continue

                narrow_phase = _i_overlay_overlap(left.points, right.points)
                if narrow_phase is False:
                    continue
                if narrow_phase is None:
                    narrow_phase = _shapely_overlap(left.points, right.points)
                    if narrow_phase is False:
                        continue
                raise ValidationError(
                    "overlap detected: "
                    f"sheet={sheet_index} "
                    f"{left.part_id}#{left.instance} vs {right.part_id}#{right.instance}"
                )


def _validate_legacy_v1(
    run_dir: Path | None,
    input_path: Path | None,
    output_path: Path | None,
) -> tuple[Path, Path]:
    try:
        resolved_input, resolved_output = legacy_resolve_paths(run_dir, input_path, output_path)
        legacy_validate_nesting_solution(resolved_input, resolved_output)
        return resolved_input, resolved_output
    except LegacyValidationError as exc:
        raise ValidationError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise ValidationError(str(exc)) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate nesting outputs (legacy v1 + nesting_engine v2)")

    parser.add_argument("--run-dir", default=None, help="Legacy v1 run dir (solver_input.json + solver_output.json)")
    parser.add_argument("--input", default=None, help="Legacy v1 solver_input.json path")
    parser.add_argument("--output", default=None, help="Legacy v1 solver_output.json path")

    parser.add_argument("--input-v2", default=None, help="io_contract_v2 input JSON path")
    parser.add_argument("--output-v2", default=None, help="io_contract_v2 output JSON path")
    parser.add_argument(
        "output_v2_positional",
        nargs="?",
        default=None,
        help="Shortcut for --output-v2 (use with optional --input-v2)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    run_dir = Path(args.run_dir).resolve() if args.run_dir else None
    input_v1 = Path(args.input).resolve() if args.input else None
    output_v1 = Path(args.output).resolve() if args.output else None

    output_v2_arg = args.output_v2
    if args.output_v2_positional is not None:
        if output_v2_arg is not None:
            print("FAIL: use either --output-v2 or positional output path, not both", file=sys.stderr)
            return 2
        output_v2_arg = args.output_v2_positional

    legacy_requested = (run_dir is not None) or (input_v1 is not None) or (output_v1 is not None)
    v2_requested = (args.input_v2 is not None) or (output_v2_arg is not None)
    if legacy_requested and v2_requested:
        print("FAIL: do not mix legacy (--run-dir/--input/--output) and v2 (--input-v2/--output-v2) flags", file=sys.stderr)
        return 2

    try:
        if legacy_requested:
            resolved_input, resolved_output = _validate_legacy_v1(run_dir, input_v1, output_v1)
            print("PASS: nesting solution is valid")
            print(f" input={resolved_input}")
            print(f" output={resolved_output}")
            return 0

        if output_v2_arg is None:
            raise ValidationError("provide legacy flags OR --output-v2 (or positional output path)")

        output_v2 = Path(output_v2_arg).resolve()
        if args.input_v2:
            input_v2 = Path(args.input_v2).resolve()
        else:
            input_v2 = ROOT_DIR / "poc" / "nesting_engine" / "sample_input_v2.json"

        validate_nesting_engine_v2(input_v2, output_v2)
        print("PASS: nesting_engine_v2 solution is valid")
        print(f" input={input_v2}")
        print(f" output={output_v2}")
        return 0
    except ValidationError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: unexpected validator error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
