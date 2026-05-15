#!/usr/bin/env python3
"""Geometry validator for an LV8 cavity_prepack solver output.

Checks against the original (10 mm spacing/margin, 3000x1500 mm) target:
- placed_instances vs required_instances (276)
- sheets_used <= 2
- inter-part spacing >= 10 mm (AABB-based conservative check)
- sheet border margin >= 10 mm
- no AABB overlap between placed parts on the same sheet

This is a conservative geometric validator using axis-aligned bounding boxes
on the inflated part outlines, not exact polygon overlap. It will flag any
geometric violation that AABBs surface, and pass only when AABBs are clean.
For CAM-grade validation a polygon-aware validator should be used.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def rotate_outer(points: list[list[float]], deg: float) -> list[list[float]]:
    rad = math.radians(deg)
    c, s = math.cos(rad), math.sin(rad)
    return [[x * c - y * s, x * s + y * c] for x, y in points]


def aabb_of(points: list[list[float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def validate(
    fixture_path: Path,
    prepacked_input_path: Path,
    solver_stdout_path: Path,
    required_instances: int,
    spacing_mm: float,
    margin_mm: float,
) -> dict[str, Any]:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    prepacked = json.loads(prepacked_input_path.read_text(encoding="utf-8"))
    out = json.loads(solver_stdout_path.read_text(encoding="utf-8"))

    sheet_w = float(fixture["sheet"]["width_mm"])
    sheet_h = float(fixture["sheet"]["height_mm"])

    # Build per-part outer-points map from prepacked input.
    part_outer: dict[str, list[list[float]]] = {}
    for p in prepacked.get("parts", []):
        part_outer[p["id"]] = p.get("outer_points_mm") or []

    placements = out.get("placements", [])
    unplaced = out.get("unplaced", [])
    sheets_used = int(out.get("sheets_used") or 0)
    placed_count = len(placements)

    issues: list[dict[str, Any]] = []
    boundary_violations = 0
    aabb_overlaps = 0
    spacing_violations = 0

    placed_by_sheet: dict[int, list[tuple[str, int, tuple[float, float, float, float]]]] = {}
    for pl in placements:
        pid = str(pl["part_id"])
        sh = int(pl.get("sheet", 0))
        x = float(pl.get("x_mm", 0.0))
        y = float(pl.get("y_mm", 0.0))
        rot = float(pl.get("rotation_deg", 0.0))
        pts = part_outer.get(pid)
        if not pts:
            issues.append({"code": "MISSING_OUTER_POINTS", "part_id": pid, "instance": pl.get("instance")})
            continue
        rotated = rotate_outer(pts, rot)
        translated = [[p[0] + x, p[1] + y] for p in rotated]
        bbox = aabb_of(translated)
        # margin check (sheet border)
        if bbox[0] < margin_mm - 1e-6 or bbox[1] < margin_mm - 1e-6 \
                or bbox[2] > sheet_w - margin_mm + 1e-6 or bbox[3] > sheet_h - margin_mm + 1e-6:
            boundary_violations += 1
            issues.append({
                "code": "BOUNDARY_VIOLATION", "part_id": pid, "instance": pl.get("instance"),
                "sheet": sh, "bbox": bbox,
            })
        placed_by_sheet.setdefault(sh, []).append((pid, int(pl.get("instance", 0)), bbox))

    for sh, items in placed_by_sheet.items():
        n = len(items)
        for i in range(n):
            for j in range(i + 1, n):
                a = items[i][2]
                b = items[j][2]
                # AABB intersection?
                if a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]:
                    aabb_overlaps += 1
                    issues.append({
                        "code": "AABB_OVERLAP", "sheet": sh,
                        "a": [items[i][0], items[i][1]], "b": [items[j][0], items[j][1]],
                    })
                else:
                    # spacing check via AABB gap
                    gap_x = max(0.0, max(a[0], b[0]) - min(a[2], b[2]))
                    gap_y = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
                    gap = math.hypot(gap_x, gap_y) if gap_x and gap_y else max(gap_x, gap_y)
                    if gap + 1e-6 < spacing_mm:
                        spacing_violations += 1
                        if len([x for x in issues if x["code"] == "SPACING_VIOLATION"]) < 20:
                            issues.append({
                                "code": "SPACING_VIOLATION", "sheet": sh,
                                "a": [items[i][0], items[i][1]], "b": [items[j][0], items[j][1]],
                                "gap_mm": gap,
                            })

    placed_instances = placed_count
    quantity_ok = placed_instances == required_instances and len(unplaced) == 0

    summary = {
        "fixture_path": str(fixture_path),
        "prepacked_input_path": str(prepacked_input_path),
        "solver_stdout_path": str(solver_stdout_path),
        "required_instances": required_instances,
        "placed_instances": placed_instances,
        "unplaced_count": len(unplaced),
        "sheets_used": sheets_used,
        "spacing_mm_target": spacing_mm,
        "margin_mm_target": margin_mm,
        "boundary_violation_count": boundary_violations,
        "aabb_overlap_count": aabb_overlaps,
        "spacing_violation_count": spacing_violations,
        "quantity_ok": quantity_ok,
        "valid": (
            quantity_ok and sheets_used > 0 and sheets_used <= 2
            and boundary_violations == 0 and aabb_overlaps == 0 and spacing_violations == 0
        ),
        "validation_kind": "AABB-conservative",
        "limitations": (
            "AABB-based; does not detect concave-fit overlaps below AABB granularity. "
            "Spacing measured as gap between AABBs, which is conservative."
        ),
        "issues_sample": issues[:50],
        "issue_count_total": len(issues),
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--prepacked-input", required=True)
    parser.add_argument("--solver-stdout", required=True)
    parser.add_argument("--required-instances", type=int, default=276)
    parser.add_argument("--spacing-mm", type=float, default=10.0)
    parser.add_argument("--margin-mm", type=float, default=10.0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    summary = validate(
        Path(args.fixture),
        Path(args.prepacked_input),
        Path(args.solver_stdout),
        args.required_instances,
        args.spacing_mm,
        args.margin_mm,
    )
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({
        "valid": summary["valid"],
        "placed_instances": summary["placed_instances"],
        "required_instances": summary["required_instances"],
        "sheets_used": summary["sheets_used"],
        "boundary_violation_count": summary["boundary_violation_count"],
        "aabb_overlap_count": summary["aabb_overlap_count"],
        "spacing_violation_count": summary["spacing_violation_count"],
    }, indent=2))
    return 0 if summary["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
