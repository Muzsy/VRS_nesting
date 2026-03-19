#!/usr/bin/env python3
"""H1-E5-T1 smoke: engine adapter input mapping (H1 minimum)."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.engine_adapter_input import (  # noqa: E402
    EngineAdapterInputError,
    build_solver_input_from_snapshot,
    solver_input_sha256,
)


def _base_snapshot() -> dict:
    return {
        "project_manifest_jsonb": {
            "project_id": "p1",
            "project_name": "Project One",
        },
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-1",
                "part_revision_id": "part-rev-1",
                "part_code": "PART-001",
                "required_qty": 4,
                "placement_priority": 10,
                "selected_nesting_derivative_id": "deriv-1",
            }
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
            }
        ],
        "solver_config_jsonb": {
            "seed": 7,
            "time_limit_s": 75,
            "rotation_step_deg": 90,
            "allow_free_rotation": False,
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
    payload = build_solver_input_from_snapshot(snapshot)

    if payload.get("contract_version") != "v1":
        raise RuntimeError("contract_version must be v1")
    if payload.get("project_name") != "Project One":
        raise RuntimeError("project_name mismatch")
    if payload.get("seed") != 7:
        raise RuntimeError("seed mismatch")
    if payload.get("time_limit_s") != 75:
        raise RuntimeError("time_limit_s mismatch")

    stocks = payload.get("stocks")
    if not isinstance(stocks, list) or len(stocks) != 1:
        raise RuntimeError("stocks mapping failed")
    stock = stocks[0]
    if stock.get("width") != 3000.0 or stock.get("height") != 1500.0:
        raise RuntimeError("stock bbox mapping failed")

    parts = payload.get("parts")
    if not isinstance(parts, list) or len(parts) != 1:
        raise RuntimeError("parts mapping failed")
    part = parts[0]
    if part.get("id") != "part-rev-1":
        raise RuntimeError("part id mismatch")
    if part.get("quantity") != 4:
        raise RuntimeError("part quantity mismatch")
    if part.get("allowed_rotations_deg") != [0, 90, 180, 270]:
        raise RuntimeError("rotation mapping mismatch")
    if part.get("width") != 400.0 or part.get("height") != 200.0:
        raise RuntimeError("part bbox mapping mismatch")
    if not isinstance(part.get("outer_points"), list) or len(part["outer_points"]) < 3:
        raise RuntimeError("part outer_points missing")
    if not isinstance(part.get("holes_points"), list) or len(part["holes_points"]) != 1:
        raise RuntimeError("part holes_points mapping mismatch")

    payload_second = build_solver_input_from_snapshot(deepcopy(snapshot))
    hash_first = solver_input_sha256(payload)
    hash_second = solver_input_sha256(payload_second)
    if hash_first != hash_second:
        raise RuntimeError("deterministic hash mismatch")

    unsupported_step = _base_snapshot()
    unsupported_step["solver_config_jsonb"]["rotation_step_deg"] = 45
    _expect_error(
        lambda: build_solver_input_from_snapshot(unsupported_step),
        "unsupported rotation policy",
    )

    allow_free = _base_snapshot()
    allow_free["solver_config_jsonb"]["allow_free_rotation"] = True
    _expect_error(
        lambda: build_solver_input_from_snapshot(allow_free),
        "allow_free_rotation=true",
    )

    missing_geometry = _base_snapshot()
    missing_geometry["geometry_manifest_jsonb"] = []
    _expect_error(
        lambda: build_solver_input_from_snapshot(missing_geometry),
        "missing geometry manifest",
    )

    missing_bbox = _base_snapshot()
    del missing_bbox["geometry_manifest_jsonb"][0]["bbox"]["width"]
    _expect_error(
        lambda: build_solver_input_from_snapshot(missing_bbox),
        "bbox.width",
    )

    print("PASS: H1-E5-T1 engine adapter input mapping smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
