#!/usr/bin/env python3
"""H3-Quality-T3 smoke: snapshot -> nesting_engine_v2 adapter mapping."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.engine_adapter_input import (  # noqa: E402
    EngineAdapterInputError,
    build_nesting_engine_input_from_snapshot,
    nesting_engine_input_sha256,
)


def _base_snapshot() -> dict:
    return {
        "project_manifest_jsonb": {"project_id": "p1", "project_name": "Project One"},
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-2",
                "part_revision_id": "part-rev-2",
                "part_code": "PART-002",
                "required_qty": 2,
                "placement_priority": 20,
                "selected_nesting_derivative_id": "deriv-2",
            },
            {
                "project_part_requirement_id": "req-1",
                "part_revision_id": "part-rev-1",
                "part_code": "PART-001",
                "required_qty": 4,
                "placement_priority": 10,
                "selected_nesting_derivative_id": "deriv-1",
            },
        ],
        "sheets_manifest_jsonb": [
            {
                "project_sheet_input_id": "sheet-input-1",
                "sheet_revision_id": "sheet-rev-1",
                "sheet_code": "SHEET-001",
                "required_qty": 2,
                "is_default": True,
                "placement_priority": 0,
                "width_mm": 3000.0,
                "height_mm": 1500.0,
            }
        ],
        "geometry_manifest_jsonb": [
            {
                "selected_nesting_derivative_id": "deriv-1",
                "polygon": {
                    "outer_ring": [[0.0, 0.0], [400.0, 0.0], [400.0, 200.0], [0.0, 200.0]],
                    "hole_rings": [[[100.0, 50.0], [140.0, 50.0], [140.0, 90.0], [100.0, 90.0]]],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 400.0,
                    "max_y": 200.0,
                    "width": 400.0,
                    "height": 200.0,
                },
            },
            {
                "selected_nesting_derivative_id": "deriv-2",
                "polygon": {
                    "outer_ring": [[0.0, 0.0], [300.0, 0.0], [300.0, 180.0], [0.0, 180.0]],
                    "hole_rings": [],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 300.0,
                    "max_y": 180.0,
                    "width": 300.0,
                    "height": 180.0,
                },
            },
        ],
        "solver_config_jsonb": {
            "seed": 7,
            "time_limit_s": 75,
            "rotation_step_deg": 45,
            "allow_free_rotation": False,
            "kerf_mm": 0.2,
            "spacing_mm": 0.4,
            "margin_mm": 2.0,
        },
    }


def _expect_error(fn, expected_substring: str) -> None:
    try:
        fn()
    except EngineAdapterInputError as exc:
        detail = str(exc)
        if expected_substring not in detail:
            raise RuntimeError(f"unexpected error detail: {detail!r}")
        return
    raise RuntimeError("expected EngineAdapterInputError")


def main() -> int:
    snapshot = _base_snapshot()
    payload = build_nesting_engine_input_from_snapshot(snapshot)

    if payload.get("version") != "nesting_engine_v2":
        raise RuntimeError("version must be nesting_engine_v2")
    if payload.get("seed") != 7:
        raise RuntimeError("seed mismatch")
    if payload.get("time_limit_sec") != 75:
        raise RuntimeError("time_limit_sec mismatch")

    sheet = payload.get("sheet")
    if not isinstance(sheet, dict):
        raise RuntimeError("sheet mapping failed")
    if sheet.get("width_mm") != 3000.0 or sheet.get("height_mm") != 1500.0:
        raise RuntimeError("sheet size mapping failed")
    if sheet.get("kerf_mm") != 0.2 or sheet.get("spacing_mm") != 0.4 or sheet.get("margin_mm") != 2.0:
        raise RuntimeError("sheet manufacturing mapping failed")

    parts = payload.get("parts")
    if not isinstance(parts, list) or len(parts) != 2:
        raise RuntimeError("parts mapping failed")

    part_1 = parts[0]
    if part_1.get("id") != "part-rev-1":
        raise RuntimeError("deterministic part sort mismatch")
    if part_1.get("quantity") != 4:
        raise RuntimeError("part quantity mismatch")
    if part_1.get("allowed_rotations_deg") != [0, 45, 90, 135, 180, 225, 270, 315]:
        raise RuntimeError("45-degree rotation policy mapping mismatch")
    if not isinstance(part_1.get("outer_points_mm"), list) or len(part_1["outer_points_mm"]) < 3:
        raise RuntimeError("part outer_points_mm missing")
    if not isinstance(part_1.get("holes_points_mm"), list) or len(part_1["holes_points_mm"]) != 1:
        raise RuntimeError("part holes_points_mm mapping mismatch")

    payload_second = build_nesting_engine_input_from_snapshot(deepcopy(snapshot))
    hash_first = nesting_engine_input_sha256(payload)
    hash_second = nesting_engine_input_sha256(payload_second)
    if hash_first != hash_second:
        raise RuntimeError("deterministic v2 hash mismatch")

    allow_free = _base_snapshot()
    allow_free["solver_config_jsonb"]["allow_free_rotation"] = True
    _expect_error(
        lambda: build_nesting_engine_input_from_snapshot(allow_free),
        "allow_free_rotation=true",
    )

    multi_sheet = _base_snapshot()
    multi_sheet["sheets_manifest_jsonb"].append(
        {
            "project_sheet_input_id": "sheet-input-2",
            "sheet_revision_id": "sheet-rev-2",
            "sheet_code": "SHEET-002",
            "required_qty": 1,
            "is_default": False,
            "placement_priority": 1,
            "width_mm": 2500.0,
            "height_mm": 1250.0,
        }
    )
    _expect_error(
        lambda: build_nesting_engine_input_from_snapshot(multi_sheet),
        "multiple sheet families",
    )

    missing_geometry = _base_snapshot()
    missing_geometry["geometry_manifest_jsonb"] = []
    _expect_error(
        lambda: build_nesting_engine_input_from_snapshot(missing_geometry),
        "missing geometry manifest",
    )

    missing_outer_ring = _base_snapshot()
    del missing_outer_ring["geometry_manifest_jsonb"][0]["polygon"]["outer_ring"]
    _expect_error(
        lambda: build_nesting_engine_input_from_snapshot(missing_outer_ring),
        "polygon.outer_ring",
    )

    empty_parts = _base_snapshot()
    empty_parts["parts_manifest_jsonb"] = []
    _expect_error(
        lambda: build_nesting_engine_input_from_snapshot(empty_parts),
        "parts_manifest_jsonb is empty",
    )

    print("PASS: H3-Quality-T3 snapshot -> nesting_engine_v2 adapter smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
