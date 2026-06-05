"""Tests for sparrow_cde wiring in engine_adapter_input.

Covers:
- solver_profile / optimizer_pipeline / collision_backend forwarding
- outer_points_mm / holes_points_mm aliases in parts
- cavity_prepack_parts_to_vrs_solver_v1 schema conversion
"""
from __future__ import annotations

import pytest

from worker.engine_adapter_input import (
    EngineAdapterInputError,
    build_solver_input_from_snapshot,
    cavity_prepack_parts_to_vrs_solver_v1,
)


# ---------------------------------------------------------------------------
# Minimal snapshot factory
# ---------------------------------------------------------------------------

def _make_snapshot(
    *,
    solver_profile: str | None = None,
    optimizer_pipeline: str | None = None,
    collision_backend: str | None = None,
    parts: list[dict] | None = None,
) -> dict:
    if parts is None:
        parts = [{"id": "P1", "outer_points_mm": [[0,0],[100,0],[100,50],[0,50]], "holes_points_mm": []}]
    parts_manifest = []
    geometry_manifest = []
    for p in parts:
        pid = p["id"]
        drv = f"drv-{pid}"
        outer = p["outer_points_mm"]
        holes = p.get("holes_points_mm") or []
        parts_manifest.append({
            "part_revision_id": pid,
            "part_code": pid,
            "required_qty": 1,
            "source_geometry_revision_id": f"src-{pid}",
            "selected_nesting_derivative_id": drv,
        })
        geometry_manifest.append({
            "selected_nesting_derivative_id": drv,
            "polygon": {"outer_ring": outer, "hole_rings": holes},
            "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 100.0, "max_y": 50.0, "width": 100.0, "height": 50.0},
        })
    solver_config: dict = {"seed": 0, "time_limit_s": 30, "rotation_step_deg": 90}
    if solver_profile:
        solver_config["solver_profile"] = solver_profile
    if optimizer_pipeline:
        solver_config["optimizer_pipeline"] = optimizer_pipeline
    if collision_backend:
        solver_config["collision_backend"] = collision_backend
    return {
        "project_manifest_jsonb": {"project_name": "test"},
        "parts_manifest_jsonb": parts_manifest,
        "sheets_manifest_jsonb": [{
            "sheet_revision_id": "S1",
            "required_qty": 1,
            "width_mm": 1500.0,
            "height_mm": 3000.0,
            "is_default": True,
        }],
        "geometry_manifest_jsonb": geometry_manifest,
        "solver_config_jsonb": solver_config,
    }


# ---------------------------------------------------------------------------
# solver routing fields forwarded from solver_config
# ---------------------------------------------------------------------------

def test_solver_profile_forwarded_when_set():
    snap = _make_snapshot(solver_profile="jagua_optimizer_phase1_outer_only")
    out = build_solver_input_from_snapshot(snap)
    assert out["solver_profile"] == "jagua_optimizer_phase1_outer_only"


def test_optimizer_pipeline_forwarded_when_set():
    snap = _make_snapshot(optimizer_pipeline="sparrow_cde")
    out = build_solver_input_from_snapshot(snap)
    assert out["optimizer_pipeline"] == "sparrow_cde"


def test_collision_backend_forwarded_when_set():
    snap = _make_snapshot(collision_backend="cde")
    out = build_solver_input_from_snapshot(snap)
    assert out["collision_backend"] == "cde"


def test_all_three_routing_fields_forwarded_together():
    snap = _make_snapshot(
        solver_profile="jagua_optimizer_phase1_outer_only",
        optimizer_pipeline="sparrow_cde",
        collision_backend="cde",
    )
    out = build_solver_input_from_snapshot(snap)
    assert out["solver_profile"] == "jagua_optimizer_phase1_outer_only"
    assert out["optimizer_pipeline"] == "sparrow_cde"
    assert out["collision_backend"] == "cde"


def test_routing_fields_absent_when_not_in_solver_config():
    snap = _make_snapshot()
    out = build_solver_input_from_snapshot(snap)
    assert "solver_profile" not in out
    assert "optimizer_pipeline" not in out
    assert "collision_backend" not in out


def test_empty_string_routing_field_is_not_forwarded():
    snap = _make_snapshot()
    snap["solver_config_jsonb"]["solver_profile"] = ""
    out = build_solver_input_from_snapshot(snap)
    assert "solver_profile" not in out


# ---------------------------------------------------------------------------
# outer_points_mm / holes_points_mm aliases present in parts
# ---------------------------------------------------------------------------

def test_parts_have_outer_points_mm_alias():
    snap = _make_snapshot()
    out = build_solver_input_from_snapshot(snap)
    part = out["parts"][0]
    assert "outer_points_mm" in part
    assert part["outer_points_mm"] == part["outer_points"]


def test_parts_have_holes_points_mm_alias():
    parts = [{
        "id": "H1",
        "outer_points_mm": [[0,0],[200,0],[200,100],[0,100]],
        "holes_points_mm": [[[50,25],[100,25],[100,75],[50,75]]],
    }]
    snap = _make_snapshot(parts=parts)
    snap["geometry_manifest_jsonb"][0]["polygon"]["hole_rings"] = parts[0]["holes_points_mm"]
    snap["geometry_manifest_jsonb"][0]["bbox"] = {
        "min_x": 0.0, "min_y": 0.0, "max_x": 200.0, "max_y": 100.0,
        "width": 200.0, "height": 100.0,
    }
    out = build_solver_input_from_snapshot(snap)
    part = out["parts"][0]
    assert "holes_points_mm" in part
    assert part["holes_points_mm"] == part["holes_points"]


def test_parts_v1_keys_still_present():
    snap = _make_snapshot()
    out = build_solver_input_from_snapshot(snap)
    part = out["parts"][0]
    assert "outer_points" in part
    assert "holes_points" in part
    assert "width" in part
    assert "height" in part


# ---------------------------------------------------------------------------
# cavity_prepack_parts_to_vrs_solver_v1
# ---------------------------------------------------------------------------

def test_converts_outer_points_mm_key():
    prepack_parts = [{
        "id": "V__parent__000000",
        "quantity": 2,
        "allowed_rotations_deg": [0, 90],
        "outer_points_mm": [[0.0,0.0],[100.0,0.0],[100.0,50.0],[0.0,50.0]],
        "holes_points_mm": [],
    }]
    result = cavity_prepack_parts_to_vrs_solver_v1(prepack_parts)
    assert len(result) == 1
    p = result[0]
    assert "outer_points" in p
    assert "holes_points" in p
    assert "outer_points_mm" not in p
    assert "holes_points_mm" not in p


def test_computes_width_height_from_bbox():
    prepack_parts = [{
        "id": "V__p__000000",
        "quantity": 1,
        "allowed_rotations_deg": [0],
        "outer_points_mm": [[10.0,20.0],[110.0,20.0],[110.0,70.0],[10.0,70.0]],
        "holes_points_mm": [],
    }]
    result = cavity_prepack_parts_to_vrs_solver_v1(prepack_parts)
    p = result[0]
    assert abs(p["width"] - 100.0) < 1e-9
    assert abs(p["height"] - 50.0) < 1e-9


def test_preserves_holes_as_holes_points():
    hole = [[25.0,10.0],[75.0,10.0],[75.0,40.0],[25.0,40.0]]
    prepack_parts = [{
        "id": "V__p__000000",
        "quantity": 1,
        "allowed_rotations_deg": [0],
        "outer_points_mm": [[0.0,0.0],[100.0,0.0],[100.0,50.0],[0.0,50.0]],
        "holes_points_mm": [hole],
    }]
    result = cavity_prepack_parts_to_vrs_solver_v1(prepack_parts)
    assert result[0]["holes_points"] == [hole]


def test_raises_on_missing_outer_points():
    with pytest.raises(EngineAdapterInputError, match="outer_points_mm"):
        cavity_prepack_parts_to_vrs_solver_v1([{
            "id": "bad",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": [],
            "holes_points_mm": [],
        }])


def test_raises_on_degenerate_bbox():
    with pytest.raises(EngineAdapterInputError, match="degenerate"):
        cavity_prepack_parts_to_vrs_solver_v1([{
            "id": "bad",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": [[0.0,0.0],[0.0,0.0],[0.0,0.0]],
            "holes_points_mm": [],
        }])


def test_falls_back_to_outer_points_key_when_mm_absent():
    prepack_parts = [{
        "id": "V__p__000000",
        "quantity": 1,
        "allowed_rotations_deg": [0],
        "outer_points": [[0.0,0.0],[80.0,0.0],[80.0,60.0],[0.0,60.0]],
        "holes_points": [],
    }]
    result = cavity_prepack_parts_to_vrs_solver_v1(prepack_parts)
    p = result[0]
    assert abs(p["width"] - 80.0) < 1e-9
    assert abs(p["height"] - 60.0) < 1e-9
