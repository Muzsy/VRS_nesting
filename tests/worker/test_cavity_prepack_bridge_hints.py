"""SGH-Q56B2 — CavityPrepackBridgeHints contract tests + diagnostics artifact.

Proves the explicit worker→solver cavity-prepack bridge contract:
  - enabled prepack on a holed parent yields a hole-free solver input (validation passes);
  - the hole-free validator rejects any residual top-level holes;
  - cavity_plan_v2 is present and the bridge diagnostics report it;
  - the disabled path is explicit and never fakes a hole-free guarantee;
  - the compact bridge block is audit-friendly.

No cavity packing is re-implemented here and no existing prepack behavior is modified.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from worker.cavity_prepack import (
    CavityPrepackGuardError,
    build_cavity_prepacked_engine_input_v2,
    cavity_prepack_bridge_block,
    compute_cavity_prepack_bridge_hints,
    validate_prepack_solver_input_hole_free,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _snapshot_for_parts(parts: list[dict[str, object]]) -> dict[str, object]:
    parts_manifest: list[dict[str, object]] = []
    geometry_manifest: list[dict[str, object]] = []
    for item in parts:
        part_id = str(item["id"])
        part_code = str(item.get("part_code") or part_id)
        source_geom = f"src-{part_id}"
        derivative_id = f"drv-{part_id}"
        outer = deepcopy(item["outer_points_mm"])
        holes = deepcopy(item.get("holes_points_mm") or [])
        parts_manifest.append(
            {
                "part_revision_id": part_id,
                "part_code": part_code,
                "required_qty": int(item["quantity"]),
                "source_geometry_revision_id": source_geom,
                "selected_nesting_derivative_id": derivative_id,
            }
        )
        geometry_manifest.append(
            {
                "selected_nesting_derivative_id": derivative_id,
                "polygon": {"outer_ring": outer, "hole_rings": holes},
                "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 100.0, "max_y": 100.0, "width": 100.0, "height": 100.0},
            }
        )
    return {
        "parts_manifest_jsonb": parts_manifest,
        "geometry_manifest_jsonb": geometry_manifest,
    }


def _base_input(parts: list[dict[str, object]]) -> dict[str, object]:
    return {
        "version": "nesting_engine_v2",
        "seed": 1,
        "time_limit_sec": 10,
        "sheet": {"width_mm": 100.0, "height_mm": 100.0, "kerf_mm": 0.0, "spacing_mm": 0.0, "margin_mm": 0.0},
        "parts": deepcopy(parts),
    }


def _holed_parent_parts() -> list[dict[str, object]]:
    return [
        {
            "id": "parent-a",
            "quantity": 1,
            "allowed_rotations_deg": [0, 90],
            "outer_points_mm": _rect(0.0, 0.0, 60.0, 60.0),
            "holes_points_mm": [_rect(10.0, 10.0, 50.0, 50.0)],
        },
        {
            "id": "child-a",
            "quantity": 4,
            "allowed_rotations_deg": [0, 90],
            "outer_points_mm": _rect(0.0, 0.0, 15.0, 15.0),
        },
    ]


def test_enabled_prepack_yields_hole_free_solver_input_and_bridge_hints() -> None:
    parts = _holed_parent_parts()
    snapshot = _snapshot_for_parts(parts)
    base_input = _base_input(parts)

    out_input, plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot,
        base_engine_input=base_input,
        enabled=True,
    )

    # Solver input must be hole-free at top level (the validator must not raise).
    validate_prepack_solver_input_hole_free(out_input)

    hints = compute_cavity_prepack_bridge_hints(
        base_engine_input=base_input,
        solver_engine_input=out_input,
        cavity_plan=plan,
        requested=True,
        enabled=True,
    )
    assert hints["cavity_prepack_enabled"] is True
    assert hints["hole_free_validation_passed"] is True
    assert hints["solver_top_level_holes_remaining"] == 0
    assert hints["hole_bearing_input_part_count"] >= 1
    assert hints["cavity_plan_v2_present"] is True
    assert hints["cavity_prepack_version"] == "cavity_plan_v2"
    assert hints["bridge_status"] == "enabled_passed"
    assert hints["bridge_errors"] == []

    # Emit the artifact.
    out_dir = REPO_ROOT / "artifacts" / "benchmarks" / "sgh_q56b2"
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact = {"hints": hints, "block": cavity_prepack_bridge_block(hints)}
    (out_dir / "cavity_prepack_bridge_hints.json").write_text(json.dumps(artifact, indent=2, sort_keys=True))
    assert (out_dir / "cavity_prepack_bridge_hints.json").exists()


def test_validator_rejects_residual_top_level_holes() -> None:
    engine_input = {
        "version": "nesting_engine_v2",
        "parts": [
            {"id": "still-holed", "outer_points_mm": _rect(0, 0, 10, 10), "holes_points_mm": [_rect(2, 2, 8, 8)]},
        ],
    }
    with pytest.raises(CavityPrepackGuardError):
        validate_prepack_solver_input_hole_free(engine_input)

    hints = compute_cavity_prepack_bridge_hints(
        base_engine_input=engine_input,
        solver_engine_input=engine_input,
        cavity_plan={"version": "cavity_plan_v2", "placement_trees": {}, "virtual_parts": {}},
        requested=True,
        enabled=True,
    )
    assert hints["hole_free_validation_passed"] is False
    assert hints["solver_top_level_holes_remaining"] == 1
    assert hints["bridge_status"] == "failed"
    assert hints["bridge_errors"], "a residual-hole failure must be recorded"


def test_disabled_path_is_explicit_and_does_not_fake_hole_free() -> None:
    parts = _holed_parent_parts()
    snapshot = _snapshot_for_parts(parts)
    base_input = _base_input(parts)

    out_input, plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot,
        base_engine_input=base_input,
        enabled=False,
    )
    # Disabled path leaves the input semantically unchanged (still holed).
    hints = compute_cavity_prepack_bridge_hints(
        base_engine_input=base_input,
        solver_engine_input=out_input,
        cavity_plan=plan,
        requested=False,
        enabled=False,
    )
    assert hints["cavity_prepack_enabled"] is False
    assert hints["bridge_status"] == "disabled"
    # The base input genuinely has holes, so the disabled path must NOT claim a hole-free guarantee.
    assert hints["hole_bearing_input_part_count"] >= 1
    assert hints["hole_free_validation_passed"] is False
    assert any("disabled" in w for w in hints["bridge_warnings"])


def test_bridge_block_is_compact_and_audit_friendly() -> None:
    hints = compute_cavity_prepack_bridge_hints(
        base_engine_input={"parts": []},
        solver_engine_input={"parts": []},
        cavity_plan={"version": "cavity_plan_v2", "placement_trees": {}},
        requested=True,
        enabled=True,
    )
    block = cavity_prepack_bridge_block(hints)["cavity_prepack_bridge"]
    assert set(block.keys()) == {
        "requested",
        "enabled",
        "version",
        "hole_free_validation_passed",
        "solver_top_level_holes_remaining",
        "cavity_plan_v2_present",
        "status",
    }
    assert block["version"] == "cavity_plan_v2"
