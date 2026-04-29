#!/usr/bin/env python3
"""Smoke for cavity T3 pure worker-side prepack module."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from worker.cavity_prepack import build_cavity_prepacked_engine_input  # noqa: E402


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _build_payload() -> tuple[dict[str, object], dict[str, object]]:
    base_parts = [
        {
            "id": "parent-a",
            "quantity": 1,
            "allowed_rotations_deg": [0, 90],
            "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0),
            "holes_points_mm": [_rect(2.0, 2.0, 12.0, 12.0)],
        },
        {
            "id": "child-a",
            "quantity": 3,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 3.0, 3.0),
            "holes_points_mm": [],
        },
    ]
    base_engine_input = {
        "version": "nesting_engine_v2",
        "seed": 1,
        "time_limit_sec": 10,
        "sheet": {"width_mm": 100.0, "height_mm": 100.0, "kerf_mm": 0.0, "spacing_mm": 0.0, "margin_mm": 0.0},
        "parts": base_parts,
    }
    snapshot_row = {
        "parts_manifest_jsonb": [
            {
                "part_revision_id": "parent-a",
                "part_code": "PARENT_A",
                "required_qty": 1,
                "source_geometry_revision_id": "src-parent-a",
                "selected_nesting_derivative_id": "drv-parent-a",
            },
            {
                "part_revision_id": "child-a",
                "part_code": "CHILD_A",
                "required_qty": 3,
                "source_geometry_revision_id": "src-child-a",
                "selected_nesting_derivative_id": "drv-child-a",
            },
        ]
    }
    return snapshot_row, base_engine_input


def main() -> int:
    snapshot_row, base_engine_input = _build_payload()
    out_input, cavity_plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot_row,
        base_engine_input=base_engine_input,
        enabled=True,
    )

    _assert(cavity_plan.get("version") == "cavity_plan_v1", "invalid cavity plan version")
    _assert(cavity_plan.get("enabled") is True, "cavity plan must be enabled")

    out_parts = out_input.get("parts")
    _assert(isinstance(out_parts, list), "output parts must be list")
    virtual_parts = [part for part in out_parts if str(part.get("id", "")).startswith("__cavity_composite__")]
    _assert(len(virtual_parts) == 1, f"expected exactly one virtual parent, got {len(virtual_parts)}")
    _assert(virtual_parts[0].get("holes_points_mm") == [], "virtual parent must be outer-only")

    virtual_map = cavity_plan.get("virtual_parts")
    _assert(isinstance(virtual_map, dict) and len(virtual_map) == 1, "expected one virtual_part mapping")
    first_virtual = next(iter(virtual_map.values()))
    internal = first_virtual.get("internal_placements")
    _assert(isinstance(internal, list) and len(internal) >= 1, "expected at least one internal placement")

    quantity_delta = cavity_plan.get("quantity_delta")
    _assert(isinstance(quantity_delta, dict) and "child-a" in quantity_delta, "missing child quantity_delta")
    child_delta = quantity_delta["child-a"]
    _assert(int(child_delta.get("original_required_qty") or 0) == 3, "child original qty mismatch")
    _assert(int(child_delta.get("internal_qty") or 0) >= 1, "child internal reservation missing")
    _assert(int(child_delta.get("top_level_qty", -1)) >= 0, "child top-level qty invalid")

    print("[smoke_cavity_t3_worker_cavity_prepack_v1] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
