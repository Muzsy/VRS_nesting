#!/usr/bin/env python3
"""Smoke for cavity T5 result normalizer expansion."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.result_normalizer import normalize_solver_output_projection  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _snapshot() -> dict[str, Any]:
    return {
        "project_manifest_jsonb": {"project_id": "p-smoke", "project_name": "Cavity T5 Smoke"},
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-parent",
                "part_revision_id": "parent-a",
                "part_definition_id": "part-def-parent",
                "part_code": "PARENT_A",
                "required_qty": 1,
                "placement_priority": 1,
                "selected_nesting_derivative_id": "drv-parent-a",
                "source_geometry_revision_id": "geo-parent-a",
            },
            {
                "project_part_requirement_id": "req-child",
                "part_revision_id": "child-a",
                "part_definition_id": "part-def-child",
                "part_code": "CHILD_A",
                "required_qty": 3,
                "placement_priority": 2,
                "selected_nesting_derivative_id": "drv-child-a",
                "source_geometry_revision_id": "geo-child-a",
            },
        ],
        "sheets_manifest_jsonb": [
            {
                "project_sheet_input_id": "sheet-input-1",
                "sheet_revision_id": "sheet-rev-1",
                "sheet_code": "SHEET-001",
                "required_qty": 1,
                "is_default": True,
                "placement_priority": 0,
                "width_mm": 120.0,
                "height_mm": 120.0,
            }
        ],
        "geometry_manifest_jsonb": [
            {
                "selected_nesting_derivative_id": "drv-parent-a",
                "polygon": {
                    "outer_ring": _rect(0.0, 0.0, 20.0, 20.0),
                    "hole_rings": [_rect(2.0, 2.0, 12.0, 12.0)],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 20.0,
                    "max_y": 20.0,
                    "width": 20.0,
                    "height": 20.0,
                },
            },
            {
                "selected_nesting_derivative_id": "drv-child-a",
                "polygon": {"outer_ring": _rect(0.0, 0.0, 3.0, 3.0), "hole_rings": []},
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 3.0,
                    "max_y": 3.0,
                    "width": 3.0,
                    "height": 3.0,
                },
            },
        ],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_case(tmp: Path) -> None:
    run_dir = tmp / "run-1"
    _write_json(
        run_dir / "nesting_output.json",
        {
            "version": "nesting_engine_v2",
            "status": "partial",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "__cavity_composite__parent-a__000000",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 40.0,
                    "y_mm": 50.0,
                    "rotation_deg": 90.0,
                },
                {
                    "part_id": "child-a",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 10.0,
                    "y_mm": 15.0,
                    "rotation_deg": 0.0,
                },
            ],
            "unplaced": [{"part_id": "child-a", "instance": 1, "reason": "TIME_LIMIT"}],
            "objective": {"utilization_pct": 42.0},
            "meta": {},
        },
    )
    _write_json(
        run_dir / "cavity_plan.json",
        {
            "version": "cavity_plan_v1",
            "enabled": True,
            "policy": {},
            "virtual_parts": {
                "__cavity_composite__parent-a__000000": {
                    "kind": "parent_composite",
                    "parent_part_revision_id": "parent-a",
                    "parent_instance": 0,
                    "source_geometry_revision_id": "geo-parent-a",
                    "selected_nesting_derivative_id": "drv-parent-a",
                    "internal_placements": [
                        {
                            "child_part_revision_id": "child-a",
                            "child_instance": 0,
                            "cavity_index": 0,
                            "x_local_mm": 2.0,
                            "y_local_mm": 4.0,
                            "rotation_deg": 180,
                            "placement_origin_ref": "bbox_min_corner",
                        }
                    ],
                    "cavity_diagnostics": [],
                }
            },
            "instance_bases": {"child-a": {"internal_reserved_count": 1, "top_level_instance_base": 1}},
            "quantity_delta": {"child-a": {"original_required_qty": 3, "internal_qty": 1, "top_level_qty": 2}},
            "diagnostics": [],
        },
    )

    projection = normalize_solver_output_projection(run_id="run-1", snapshot_row=_snapshot(), run_dir=run_dir)
    _assert(projection.summary.placed_count == 3, f"placed_count mismatch: {projection.summary.placed_count}")
    _assert(projection.summary.unplaced_count == 1, f"unplaced_count mismatch: {projection.summary.unplaced_count}")

    payload = json.dumps(
        {
            "placements": projection.placements,
            "unplaced": projection.unplaced,
            "metrics": projection.metrics,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    _assert("__cavity_composite__" not in payload, "virtual part id leaked to projection")

    by_instance: dict[str, dict[str, Any]] = {}
    for row in projection.placements:
        transform = row.get("transform_jsonb")
        _assert(isinstance(transform, dict), "missing transform_jsonb")
        by_instance[str(transform.get("instance_id"))] = row

    _assert("parent-a:0" in by_instance, "mapped parent placement missing")
    _assert("child-a:0" in by_instance, "internal child placement missing")
    _assert("child-a:1" in by_instance, "top-level child offset placement missing")

    internal = by_instance["child-a:0"]
    internal_tf = internal["transform_jsonb"]
    _assert(isinstance(internal_tf, dict), "internal transform missing")
    _assert(abs(float(internal_tf["x"]) - 36.0) < 1e-6, f"internal x mismatch: {internal_tf}")
    _assert(abs(float(internal_tf["y"]) - 52.0) < 1e-6, f"internal y mismatch: {internal_tf}")
    _assert(abs(float(internal_tf["rotation_deg"]) - 270.0) < 1e-6, f"internal rot mismatch: {internal_tf}")

    child_unplaced = next(
        (
            row
            for row in projection.unplaced
            if str(row.get("part_revision_id") or "") == "child-a" and str(row.get("reason") or "") == "TIME_LIMIT"
        ),
        None,
    )
    _assert(child_unplaced is not None, "child unplaced row missing")
    child_unplaced_meta = child_unplaced["metadata_jsonb"]
    _assert(isinstance(child_unplaced_meta, dict), "child unplaced metadata missing")
    _assert(child_unplaced_meta.get("instance_ids") == ["child-a:2"], f"unplaced offset mismatch: {child_unplaced_meta}")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="smoke_cavity_t5_result_normalizer_expansion_"))
    try:
        _run_case(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("[smoke_cavity_t5_result_normalizer_expansion] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
