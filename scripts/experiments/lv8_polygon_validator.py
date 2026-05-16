#!/usr/bin/env python3
"""Polygon-aware LV8 benchmark validation gate (T05).

Validates solver placements using Shapely polygons. This is the binding
PASS/FAIL gate for the LV8 benchmark; the legacy AABB validator
(lv8_2sheet_claude_validate.py) remains a non-binding diagnostic tool.

Coordinate convention (matches worker/cavity_validation.py _build_placed_polygon):
  1. Rotate outer polygon around origin (0, 0) by rotation_deg.
  2. Normalize: shift so min_x=0, min_y=0.
  3. Translate by (x_mm, y_mm) from solver output.

This convention differs from the legacy AABB validator, which rotates and
translates without the normalization step. The cavity_validation.py convention
is authoritative because it is used for the binding cavity validation gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from shapely import affinity
from shapely.geometry import Polygon, box

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from worker.cavity_validation import validate_cavity_plan_v2

_EPS = 1e-3  # 0.001 mm numerical tolerance


def _build_placed_polygon(
    outer_points_mm: list[list[float]],
    x_mm: float,
    y_mm: float,
    rotation_deg: float,
) -> Polygon:
    base = Polygon(outer_points_mm)
    if not base.is_valid:
        base = base.buffer(0)
    rotated = affinity.rotate(base, float(rotation_deg), origin=(0.0, 0.0), use_radians=False)
    min_x, min_y, _, _ = rotated.bounds
    normalized = affinity.translate(rotated, xoff=-min_x, yoff=-min_y)
    placed = affinity.translate(normalized, xoff=float(x_mm), yoff=float(y_mm))
    if not placed.is_valid:
        placed = placed.buffer(0)
    return placed


def validate(
    *,
    fixture: dict[str, Any],
    prepacked_input: dict[str, Any],
    solver_output: dict[str, Any],
    cavity_plan: dict[str, Any] | None,
    required_instances: int,
    spacing_mm: float,
    margin_mm: float,
    max_sheets: int = 2,
) -> dict[str, Any]:
    """Run polygon-aware validation. Returns a dict with valid_polygon_gate and details."""
    sheet_w = float(fixture["sheet"]["width_mm"])
    sheet_h = float(fixture["sheet"]["height_mm"])
    inner_box = box(margin_mm, margin_mm, sheet_w - margin_mm, sheet_h - margin_mm)

    # Build part geometry index from prepacked input (virtual parts)
    part_outer: dict[str, list[list[float]]] = {}
    for p in prepacked_input.get("parts") or []:
        if isinstance(p, dict) and p.get("id") and p.get("outer_points_mm"):
            part_outer[str(p["id"])] = list(p["outer_points_mm"])

    placements: list[dict[str, Any]] = list(solver_output.get("placements") or [])
    unplaced: list[Any] = list(solver_output.get("unplaced") or [])
    sheets_used = int(solver_output.get("sheets_used") or 0)

    placed_instances = len(placements)
    quantity_ok = placed_instances == required_instances and len(unplaced) == 0

    issues: list[dict[str, Any]] = []
    boundary_count = 0
    overlap_count = 0
    clearance_count = 0
    missing_geometry_count = 0

    placed_by_sheet: dict[int, list[tuple[str, int, Polygon]]] = {}

    for pl in placements:
        pid = str(pl.get("part_id") or "")
        sh = int(pl.get("sheet") or 0)
        x_mm_val = float(pl.get("x_mm") or 0.0)
        y_mm_val = float(pl.get("y_mm") or 0.0)
        rot = float(pl.get("rotation_deg") or 0.0)
        inst = int(pl.get("instance") or 0)

        pts = part_outer.get(pid)
        if not pts:
            missing_geometry_count += 1
            issues.append({"code": "MISSING_OUTER_POINTS", "part_id": pid, "instance": inst})
            continue

        try:
            poly = _build_placed_polygon(pts, x_mm_val, y_mm_val, rot)
        except Exception as exc:
            missing_geometry_count += 1
            issues.append({"code": "POLYGON_BUILD_ERROR", "part_id": pid, "instance": inst, "error": str(exc)})
            continue

        if not inner_box.covers(poly):
            boundary_count += 1
            if len(issues) < 100:
                issues.append({"code": "BOUNDARY_VIOLATION", "part_id": pid, "instance": inst, "sheet": sh})

        placed_by_sheet.setdefault(sh, []).append((pid, inst, poly))

    for sh, items in placed_by_sheet.items():
        n = len(items)
        for i in range(n):
            pid_a, inst_a, poly_a = items[i]
            for j in range(i + 1, n):
                pid_b, inst_b, poly_b = items[j]
                if poly_a.intersects(poly_b):
                    ov_area = float(poly_a.intersection(poly_b).area)
                    if ov_area > _EPS:
                        overlap_count += 1
                        if len(issues) < 100:
                            issues.append({
                                "code": "POLYGON_OVERLAP",
                                "sheet": sh,
                                "part_a": pid_a, "instance_a": inst_a,
                                "part_b": pid_b, "instance_b": inst_b,
                                "overlap_area_mm2": round(ov_area, 4),
                            })
                elif spacing_mm > 0:
                    dist = float(poly_a.distance(poly_b))
                    if dist + _EPS < spacing_mm:
                        clearance_count += 1
                        if len(issues) < 100:
                            issues.append({
                                "code": "CLEARANCE_VIOLATION",
                                "sheet": sh,
                                "part_a": pid_a, "instance_a": inst_a,
                                "part_b": pid_b, "instance_b": inst_b,
                                "distance_mm": round(dist, 4),
                                "required_mm": spacing_mm,
                            })

    cavity_validation_available = False
    cavity_validation_issue_count = 0
    cavity_validation_issues_sample: list[dict[str, Any]] = []

    if cavity_plan is not None:
        plan_version = str(cavity_plan.get("version") or "")
        if plan_version == "cavity_plan_v2":
            cavity_validation_available = True
            try:
                base_parts = list(fixture.get("parts") or [])
                cv_issues = validate_cavity_plan_v2(
                    cavity_plan=cavity_plan,
                    part_records=base_parts,
                    solver_placements=placements,
                    strict=False,
                )
                cavity_validation_issue_count = len(cv_issues)
                cavity_validation_issues_sample = [
                    {"code": iss.code, "message": iss.message}
                    for iss in cv_issues[:10]
                ]
            except Exception as exc:
                cavity_validation_issue_count = 1
                cavity_validation_issues_sample = [
                    {"code": "CAVITY_VALIDATION_EXCEPTION", "message": str(exc)}
                ]

    valid_polygon_gate = (
        missing_geometry_count == 0
        and boundary_count == 0
        and overlap_count == 0
        and clearance_count == 0
        and cavity_validation_issue_count == 0
    )

    return {
        "validation_kind": "polygon-aware",
        "valid_polygon_gate": valid_polygon_gate,
        "quantity_ok": quantity_ok,
        "placed_instances": placed_instances,
        "required_instances": required_instances,
        "unplaced_count": len(unplaced),
        "sheets_used": sheets_used,
        "boundary_count": boundary_count,
        "overlap_count": overlap_count,
        "clearance_count": clearance_count,
        "missing_geometry_count": missing_geometry_count,
        "cavity_validation_available": cavity_validation_available,
        "cavity_validation_issue_count": cavity_validation_issue_count,
        "cavity_validation_issues_sample": cavity_validation_issues_sample,
        "issues_sample": issues[:50],
        "legacy_aabb_validator": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Polygon-aware LV8 benchmark validation gate.")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--prepacked-input", required=True)
    parser.add_argument("--solver-stdout", required=True)
    parser.add_argument("--cavity-plan", default=None)
    parser.add_argument("--required-instances", type=int, default=276)
    parser.add_argument("--spacing-mm", type=float, default=10.0)
    parser.add_argument("--margin-mm", type=float, default=10.0)
    parser.add_argument("--max-sheets", type=int, default=2)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    prepacked_input = json.loads(Path(args.prepacked_input).read_text(encoding="utf-8"))
    solver_output = json.loads(Path(args.solver_stdout).read_text(encoding="utf-8"))
    cavity_plan: dict[str, Any] | None = None
    if args.cavity_plan:
        p = Path(args.cavity_plan)
        if p.is_file():
            cavity_plan = json.loads(p.read_text(encoding="utf-8"))

    result = validate(
        fixture=fixture,
        prepacked_input=prepacked_input,
        solver_output=solver_output,
        cavity_plan=cavity_plan,
        required_instances=args.required_instances,
        spacing_mm=args.spacing_mm,
        margin_mm=args.margin_mm,
        max_sheets=args.max_sheets,
    )

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "valid_polygon_gate": result["valid_polygon_gate"],
        "quantity_ok": result["quantity_ok"],
        "overlap_count": result["overlap_count"],
        "boundary_count": result["boundary_count"],
        "clearance_count": result["clearance_count"],
        "cavity_validation_issue_count": result["cavity_validation_issue_count"],
    }, indent=2))
    return 0 if result["valid_polygon_gate"] else 2


if __name__ == "__main__":
    sys.exit(main())
