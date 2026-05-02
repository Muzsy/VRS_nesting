from __future__ import annotations

import json
from pathlib import Path

import pytest

from worker.result_normalizer import (
    ResultNormalizerError,
    _load_enabled_cavity_plan,
    normalize_solver_output_projection,
)


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _write_nesting_output(run_dir: Path, payload: dict[str, object]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "nesting_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_cavity_plan(run_dir: Path, payload: dict[str, object]) -> None:
    (run_dir / "cavity_plan.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _snapshot() -> dict[str, object]:
    return {
        "project_manifest_jsonb": {"project_id": "p1", "project_name": "Result Normalizer Cavity Test"},
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
                "required_qty": 4,
                "placement_priority": 2,
                "selected_nesting_derivative_id": "drv-child-a",
                "source_geometry_revision_id": "geo-child-a",
            },
            {
                "project_part_requirement_id": "req-plain",
                "part_revision_id": "plain-a",
                "part_definition_id": "part-def-plain",
                "part_code": "PLAIN_A",
                "required_qty": 3,
                "placement_priority": 3,
                "selected_nesting_derivative_id": "drv-plain-a",
                "source_geometry_revision_id": "geo-plain-a",
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
                "width_mm": 200.0,
                "height_mm": 200.0,
            }
        ],
        "geometry_manifest_jsonb": [
            {
                "selected_nesting_derivative_id": "drv-parent-a",
                "polygon": {
                    "outer_ring": _rect(0.0, 0.0, 20.0, 20.0),
                    "hole_rings": [_rect(5.0, 5.0, 15.0, 15.0)],
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
                "polygon": {
                    "outer_ring": _rect(0.0, 0.0, 3.0, 3.0),
                    "hole_rings": [],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 3.0,
                    "max_y": 3.0,
                    "width": 3.0,
                    "height": 3.0,
                },
            },
            {
                "selected_nesting_derivative_id": "drv-plain-a",
                "polygon": {
                    "outer_ring": _rect(0.0, 0.0, 5.0, 5.0),
                    "hole_rings": [],
                },
                "bbox": {
                    "min_x": 0.0,
                    "min_y": 0.0,
                    "max_x": 5.0,
                    "max_y": 5.0,
                    "width": 5.0,
                    "height": 5.0,
                },
            },
        ],
    }


def _snapshot_matrjoska() -> dict[str, object]:
    return {
        "project_manifest_jsonb": {"project_id": "p2", "project_name": "Result Normalizer Cavity V2 Matrjoska"},
        "parts_manifest_jsonb": [
            {
                "project_part_requirement_id": "req-a",
                "part_revision_id": "A",
                "part_definition_id": "part-def-a",
                "part_code": "A",
                "required_qty": 1,
                "placement_priority": 1,
                "selected_nesting_derivative_id": "drv-a",
                "source_geometry_revision_id": "geo-a",
            },
            {
                "project_part_requirement_id": "req-b",
                "part_revision_id": "B",
                "part_definition_id": "part-def-b",
                "part_code": "B",
                "required_qty": 1,
                "placement_priority": 2,
                "selected_nesting_derivative_id": "drv-b",
                "source_geometry_revision_id": "geo-b",
            },
            {
                "project_part_requirement_id": "req-c",
                "part_revision_id": "C",
                "part_definition_id": "part-def-c",
                "part_code": "C",
                "required_qty": 1,
                "placement_priority": 3,
                "selected_nesting_derivative_id": "drv-c",
                "source_geometry_revision_id": "geo-c",
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
                "width_mm": 500.0,
                "height_mm": 500.0,
            }
        ],
        "geometry_manifest_jsonb": [
            {
                "selected_nesting_derivative_id": "drv-a",
                "polygon": {"outer_ring": _rect(0.0, 0.0, 40.0, 40.0), "hole_rings": [_rect(5.0, 5.0, 35.0, 35.0)]},
                "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 40.0, "max_y": 40.0, "width": 40.0, "height": 40.0},
            },
            {
                "selected_nesting_derivative_id": "drv-b",
                "polygon": {"outer_ring": _rect(0.0, 0.0, 20.0, 20.0), "hole_rings": [_rect(2.0, 2.0, 18.0, 18.0)]},
                "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 20.0, "max_y": 20.0, "width": 20.0, "height": 20.0},
            },
            {
                "selected_nesting_derivative_id": "drv-c",
                "polygon": {"outer_ring": _rect(0.0, 0.0, 4.0, 4.0), "hole_rings": []},
                "bbox": {"min_x": 0.0, "min_y": 0.0, "max_x": 4.0, "max_y": 4.0, "width": 4.0, "height": 4.0},
            },
        ],
    }


def _instance_map(placements: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    out: dict[str, dict[str, object]] = {}
    for row in placements:
        transform = row.get("transform_jsonb")
        assert isinstance(transform, dict)
        instance_id = str(transform.get("instance_id"))
        out[instance_id] = row
    return out


def test_cavity_plan_expands_virtual_parent_and_offsets_instances(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-with-cavity"
    _write_nesting_output(
        run_dir,
        {
            "version": "nesting_engine_v2",
            "status": "partial",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "__cavity_composite__parent-a__000000",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 50.0,
                    "y_mm": 60.0,
                    "rotation_deg": 90.0,
                },
                {
                    "part_id": "child-a",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 10.0,
                    "y_mm": 11.0,
                    "rotation_deg": 0.0,
                },
                {
                    "part_id": "plain-a",
                    "instance": 2,
                    "sheet": 0,
                    "x_mm": 5.0,
                    "y_mm": 6.0,
                    "rotation_deg": 0.0,
                },
            ],
            "unplaced": [
                {"part_id": "child-a", "instance": 1, "reason": "TIME_LIMIT"},
                {"part_id": "__cavity_composite__parent-a__000000", "instance": 0, "reason": "NO_FIT"},
            ],
            "objective": {"utilization_pct": 55.0},
            "meta": {"source": "unit-test"},
        },
    )
    _write_cavity_plan(
        run_dir,
        {
            "version": "cavity_plan_v1",
            "enabled": True,
            "policy": {
                "mode": "auto_prepack",
                "top_level_hole_policy": "solidify_parent_outer",
                "usable_cavity_source": "inflated_or_deflated_hole_from_pipeline",
                "quantity_allocation": "internal_first_deterministic",
            },
            "virtual_parts": {
                "__cavity_composite__parent-a__000000": {
                    "kind": "parent_composite",
                    "parent_part_revision_id": "parent-a",
                    "parent_instance": 1,
                    "internal_placements": [
                        {
                            "child_part_revision_id": "child-a",
                            "child_instance": 0,
                            "cavity_index": 0,
                            "x_local_mm": 2.0,
                            "y_local_mm": 4.0,
                            "rotation_deg": 180,
                            "placement_origin_ref": "bbox_min_corner",
                        },
                        {
                            "child_part_revision_id": "child-a",
                            "child_instance": 1,
                            "cavity_index": 0,
                            "x_local_mm": 0.0,
                            "y_local_mm": 0.0,
                            "rotation_deg": 0,
                            "placement_origin_ref": "bbox_min_corner",
                        },
                    ],
                    "cavity_diagnostics": [],
                }
            },
            "instance_bases": {
                "child-a": {"internal_reserved_count": 2, "top_level_instance_base": 2}
            },
            "quantity_delta": {
                "child-a": {"original_required_qty": 4, "internal_qty": 2, "top_level_qty": 2}
            },
            "diagnostics": [],
        },
    )

    projection = normalize_solver_output_projection(run_id="run-with-cavity", snapshot_row=_snapshot(), run_dir=run_dir)
    assert projection.summary.placed_count == 5
    assert projection.summary.unplaced_count == 2
    assert projection.summary.used_sheet_count == 1

    by_instance = _instance_map(projection.placements)
    parent_row = by_instance["parent-a:1"]
    assert parent_row["part_revision_id"] == "parent-a"
    parent_meta = parent_row["metadata_jsonb"]
    assert isinstance(parent_meta, dict)
    assert parent_meta["placement_scope"] == "top_level_parent"
    assert parent_meta["cavity_plan_version"] == "cavity_plan_v1"

    internal_row_0 = by_instance["child-a:0"]
    t0 = internal_row_0["transform_jsonb"]
    assert isinstance(t0, dict)
    assert float(t0["x"]) == 46.0
    assert float(t0["y"]) == 62.0
    assert float(t0["rotation_deg"]) == 270.0
    internal_meta_0 = internal_row_0["metadata_jsonb"]
    assert isinstance(internal_meta_0, dict)
    assert internal_meta_0["placement_scope"] == "internal_cavity"
    assert internal_meta_0["parent_part_revision_id"] == "parent-a"
    assert internal_meta_0["parent_instance"] == 1

    internal_row_1 = by_instance["child-a:1"]
    t1 = internal_row_1["transform_jsonb"]
    assert isinstance(t1, dict)
    assert float(t1["x"]) == 50.0
    assert float(t1["y"]) == 60.0
    assert float(t1["rotation_deg"]) == 90.0

    top_child_row = by_instance["child-a:2"]
    top_child_meta = top_child_row["metadata_jsonb"]
    assert isinstance(top_child_meta, dict)
    assert top_child_meta["placement_scope"] == "top_level"
    assert int(top_child_meta["top_level_instance_base"]) == 2
    assert int(top_child_meta["solver_instance"]) == 0

    plain_row = by_instance["plain-a:2"]
    plain_meta = plain_row["metadata_jsonb"]
    assert isinstance(plain_meta, dict)
    assert plain_meta["placement_scope"] == "top_level"
    assert int(plain_meta["top_level_instance_base"]) == 0

    unplaced_map = {(row["part_revision_id"], row.get("reason")): row for row in projection.unplaced}
    assert ("child-a", "TIME_LIMIT") in unplaced_map
    assert ("parent-a", "NO_FIT") in unplaced_map
    child_unplaced_meta = unplaced_map[("child-a", "TIME_LIMIT")]["metadata_jsonb"]
    assert isinstance(child_unplaced_meta, dict)
    assert child_unplaced_meta["instance_ids"] == ["child-a:3"]
    parent_unplaced_meta = unplaced_map[("parent-a", "NO_FIT")]["metadata_jsonb"]
    assert isinstance(parent_unplaced_meta, dict)
    assert parent_unplaced_meta["instance_ids"] == ["parent-a:1"]

    assert "__cavity_composite__" not in json.dumps(projection.placements, ensure_ascii=False)
    assert "__cavity_composite__" not in json.dumps(projection.unplaced, ensure_ascii=False)
    metrics_jsonb = projection.metrics.get("metrics_jsonb")
    assert isinstance(metrics_jsonb, dict)
    cavity_meta = metrics_jsonb.get("cavity_plan")
    assert isinstance(cavity_meta, dict)
    assert cavity_meta["enabled"] is True
    assert cavity_meta["version"] == "cavity_plan_v1"


def test_missing_or_disabled_cavity_plan_keeps_legacy_v2_shape(tmp_path: Path) -> None:
    snapshot = _snapshot()
    payload = {
        "version": "nesting_engine_v2",
        "status": "ok",
        "sheets_used": 1,
        "placements": [
            {
                "part_id": "child-a",
                "instance": 3,
                "sheet": 0,
                "x_mm": 12.5,
                "y_mm": 20.0,
                "rotation_deg": 0.0,
            }
        ],
        "unplaced": [{"part_id": "child-a", "instance": 4, "reason": "TIME_LIMIT"}],
        "objective": {"utilization_pct": 10.0},
        "meta": {},
    }

    run_missing = tmp_path / "run-missing-cavity-plan"
    _write_nesting_output(run_missing, payload)
    projection_missing = normalize_solver_output_projection(
        run_id="run-missing-cavity-plan",
        snapshot_row=snapshot,
        run_dir=run_missing,
    )
    placement_meta_missing = projection_missing.placements[0]["metadata_jsonb"]
    assert isinstance(placement_meta_missing, dict)
    assert placement_meta_missing["instance"] == 3
    assert "placement_scope" not in placement_meta_missing
    assert projection_missing.unplaced[0]["metadata_jsonb"]["instance_ids"] == ["child-a:4"]  # type: ignore[index]

    run_disabled = tmp_path / "run-disabled-cavity-plan"
    _write_nesting_output(run_disabled, payload)
    _write_cavity_plan(
        run_disabled,
        {
            "version": "cavity_plan_v1",
            "enabled": False,
            "policy": {},
            "virtual_parts": {},
            "instance_bases": {},
            "quantity_delta": {},
            "diagnostics": [],
        },
    )
    projection_disabled = normalize_solver_output_projection(
        run_id="run-disabled-cavity-plan",
        snapshot_row=snapshot,
        run_dir=run_disabled,
    )

    assert projection_missing.placements == projection_disabled.placements
    assert projection_missing.unplaced == projection_disabled.unplaced
    metrics_missing = projection_missing.metrics.get("metrics_jsonb")
    metrics_disabled = projection_disabled.metrics.get("metrics_jsonb")
    assert isinstance(metrics_missing, dict)
    assert isinstance(metrics_disabled, dict)
    assert "cavity_plan" not in metrics_missing
    assert "cavity_plan" not in metrics_disabled


def test_load_enabled_cavity_plan_accepts_v2(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-v2"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_cavity_plan(
        run_dir,
        {
            "version": "cavity_plan_v2",
            "enabled": True,
            "policy": {"mode": "recursive_cavity_prepack"},
            "virtual_parts": {},
            "placement_trees": {},
            "instance_bases": {},
            "quantity_delta": {},
            "diagnostics": [],
            "summary": {},
        },
    )
    loaded = _load_enabled_cavity_plan(run_dir)
    assert isinstance(loaded, dict)
    assert loaded["version"] == "cavity_plan_v2"
    assert loaded["enabled"] is True


def test_load_enabled_cavity_plan_rejects_unknown_version(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-invalid-version"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_cavity_plan(
        run_dir,
        {
            "version": "cavity_plan_v3",
            "enabled": True,
            "policy": {},
            "virtual_parts": {},
            "instance_bases": {},
            "quantity_delta": {},
            "diagnostics": [],
        },
    )
    with pytest.raises(ResultNormalizerError) as exc_info:
        _load_enabled_cavity_plan(run_dir)
    assert "invalid cavity_plan version" in str(exc_info.value)


def test_v2_single_level_flatten_correct_abs_coords(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-v2-single"
    _write_nesting_output(
        run_dir,
        {
            "version": "nesting_engine_v2",
            "status": "ok",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "__cavity_composite__parent-a__000000",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 50.0,
                    "y_mm": 60.0,
                    "rotation_deg": 0.0,
                }
            ],
            "unplaced": [],
            "objective": {"utilization_pct": 20.0},
            "meta": {},
        },
    )
    _write_cavity_plan(
        run_dir,
        {
            "version": "cavity_plan_v2",
            "enabled": True,
            "policy": {"mode": "recursive_cavity_prepack", "max_cavity_depth": 3},
            "virtual_parts": {
                "__cavity_composite__parent-a__000000": {
                    "kind": "parent_composite",
                    "parent_part_revision_id": "parent-a",
                    "parent_instance": 0,
                    "source_geometry_revision_id": "geo-parent-a",
                    "selected_nesting_derivative_id": "drv-parent-a",
                }
            },
            "placement_trees": {
                "__cavity_composite__parent-a__000000": {
                    "node_id": "node:parent-a:0",
                    "part_revision_id": "parent-a",
                    "instance": 0,
                    "kind": "top_level_virtual_parent",
                    "parent_node_id": None,
                    "parent_cavity_index": None,
                    "x_local_mm": 0.0,
                    "y_local_mm": 0.0,
                    "rotation_deg": 0,
                    "placement_origin_ref": "bbox_min_corner",
                    "children": [
                        {
                            "node_id": "node:child-a:0",
                            "part_revision_id": "child-a",
                            "instance": 0,
                            "kind": "internal_cavity_child",
                            "parent_node_id": "node:parent-a:0",
                            "parent_cavity_index": 0,
                            "x_local_mm": 2.0,
                            "y_local_mm": 4.0,
                            "rotation_deg": 90,
                            "placement_origin_ref": "bbox_min_corner",
                            "children": [],
                        }
                    ],
                }
            },
            "instance_bases": {
                "parent-a": {"internal_reserved_count": 0, "top_level_instance_base": 0},
                "child-a": {"internal_reserved_count": 1, "top_level_instance_base": 1},
            },
            "quantity_delta": {
                "parent-a": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
                "child-a": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
                "plain-a": {"original_required_qty": 0, "internal_qty": 0, "top_level_qty": 0},
            },
            "diagnostics": [],
            "summary": {},
        },
    )

    projection = normalize_solver_output_projection(run_id="run-v2-single", snapshot_row=_snapshot(), run_dir=run_dir)
    by_instance = _instance_map(projection.placements)
    parent = by_instance["parent-a:0"]
    child = by_instance["child-a:0"]
    parent_t = parent["transform_jsonb"]
    child_t = child["transform_jsonb"]
    assert isinstance(parent_t, dict)
    assert isinstance(child_t, dict)
    assert float(parent_t["x"]) == 50.0
    assert float(parent_t["y"]) == 60.0
    assert float(parent_t["rotation_deg"]) == 0.0
    assert float(child_t["x"]) == 52.0
    assert float(child_t["y"]) == 64.0
    assert float(child_t["rotation_deg"]) == 90.0
    child_meta = child["metadata_jsonb"]
    assert isinstance(child_meta, dict)
    assert int(child_meta["cavity_tree_depth"]) == 1


def test_v2_matrjoska_flatten_all_three_levels(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-v2-matrjoska"
    _write_nesting_output(
        run_dir,
        {
            "version": "nesting_engine_v2",
            "status": "ok",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "__cavity_composite__A__000000",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 100.0,
                    "y_mm": 100.0,
                    "rotation_deg": 0.0,
                }
            ],
            "unplaced": [],
            "objective": {"utilization_pct": 30.0},
            "meta": {},
        },
    )
    _write_cavity_plan(
        run_dir,
        {
            "version": "cavity_plan_v2",
            "enabled": True,
            "policy": {"mode": "recursive_cavity_prepack", "max_cavity_depth": 3},
            "virtual_parts": {
                "__cavity_composite__A__000000": {
                    "kind": "parent_composite",
                    "parent_part_revision_id": "A",
                    "parent_instance": 0,
                    "source_geometry_revision_id": "geo-a",
                    "selected_nesting_derivative_id": "drv-a",
                }
            },
            "placement_trees": {
                "__cavity_composite__A__000000": {
                    "node_id": "node:A:0",
                    "part_revision_id": "A",
                    "instance": 0,
                    "kind": "top_level_virtual_parent",
                    "parent_node_id": None,
                    "parent_cavity_index": None,
                    "x_local_mm": 0.0,
                    "y_local_mm": 0.0,
                    "rotation_deg": 0,
                    "placement_origin_ref": "bbox_min_corner",
                    "children": [
                        {
                            "node_id": "node:B:0",
                            "part_revision_id": "B",
                            "instance": 0,
                            "kind": "internal_cavity_child",
                            "parent_node_id": "node:A:0",
                            "parent_cavity_index": 0,
                            "x_local_mm": 10.0,
                            "y_local_mm": 10.0,
                            "rotation_deg": 0,
                            "placement_origin_ref": "bbox_min_corner",
                            "children": [
                                {
                                    "node_id": "node:C:0",
                                    "part_revision_id": "C",
                                    "instance": 0,
                                    "kind": "internal_cavity_child",
                                    "parent_node_id": "node:B:0",
                                    "parent_cavity_index": 0,
                                    "x_local_mm": 2.0,
                                    "y_local_mm": 1.0,
                                    "rotation_deg": 90,
                                    "placement_origin_ref": "bbox_min_corner",
                                    "children": [],
                                }
                            ],
                        }
                    ],
                }
            },
            "instance_bases": {
                "A": {"internal_reserved_count": 0, "top_level_instance_base": 0},
                "B": {"internal_reserved_count": 1, "top_level_instance_base": 1},
                "C": {"internal_reserved_count": 1, "top_level_instance_base": 1},
            },
            "quantity_delta": {
                "A": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
                "B": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
                "C": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
            },
            "diagnostics": [],
            "summary": {},
        },
    )

    projection = normalize_solver_output_projection(
        run_id="run-v2-matrjoska",
        snapshot_row=_snapshot_matrjoska(),
        run_dir=run_dir,
    )
    by_instance = _instance_map(projection.placements)
    assert set(by_instance.keys()) == {"A:0", "B:0", "C:0"}
    b_t = by_instance["B:0"]["transform_jsonb"]
    c_t = by_instance["C:0"]["transform_jsonb"]
    assert isinstance(b_t, dict)
    assert isinstance(c_t, dict)
    assert float(b_t["x"]) == 110.0
    assert float(b_t["y"]) == 110.0
    assert float(b_t["rotation_deg"]) == 0.0
    assert float(c_t["x"]) == 112.0
    assert float(c_t["y"]) == 111.0
    assert float(c_t["rotation_deg"]) == 90.0
    c_meta = by_instance["C:0"]["metadata_jsonb"]
    assert isinstance(c_meta, dict)
    assert int(c_meta["cavity_tree_depth"]) == 2


def test_v2_rotated_parent_child_transform(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-v2-rot"
    _write_nesting_output(
        run_dir,
        {
            "version": "nesting_engine_v2",
            "status": "ok",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "__cavity_composite__parent-a__000000",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 50.0,
                    "y_mm": 60.0,
                    "rotation_deg": 90.0,
                }
            ],
            "unplaced": [],
            "objective": {"utilization_pct": 20.0},
            "meta": {},
        },
    )
    _write_cavity_plan(
        run_dir,
        {
            "version": "cavity_plan_v2",
            "enabled": True,
            "policy": {"mode": "recursive_cavity_prepack", "max_cavity_depth": 3},
            "virtual_parts": {
                "__cavity_composite__parent-a__000000": {
                    "kind": "parent_composite",
                    "parent_part_revision_id": "parent-a",
                    "parent_instance": 1,
                    "source_geometry_revision_id": "geo-parent-a",
                    "selected_nesting_derivative_id": "drv-parent-a",
                }
            },
            "placement_trees": {
                "__cavity_composite__parent-a__000000": {
                    "node_id": "node:parent-a:1",
                    "part_revision_id": "parent-a",
                    "instance": 1,
                    "kind": "top_level_virtual_parent",
                    "parent_node_id": None,
                    "parent_cavity_index": None,
                    "x_local_mm": 0.0,
                    "y_local_mm": 0.0,
                    "rotation_deg": 0,
                    "placement_origin_ref": "bbox_min_corner",
                    "children": [
                        {
                            "node_id": "node:child-a:0",
                            "part_revision_id": "child-a",
                            "instance": 0,
                            "kind": "internal_cavity_child",
                            "parent_node_id": "node:parent-a:1",
                            "parent_cavity_index": 0,
                            "x_local_mm": 2.0,
                            "y_local_mm": 4.0,
                            "rotation_deg": 180,
                            "placement_origin_ref": "bbox_min_corner",
                            "children": [],
                        }
                    ],
                }
            },
            "instance_bases": {
                "parent-a": {"internal_reserved_count": 0, "top_level_instance_base": 0},
                "child-a": {"internal_reserved_count": 1, "top_level_instance_base": 1},
            },
            "quantity_delta": {
                "parent-a": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
                "child-a": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
            },
            "diagnostics": [],
            "summary": {},
        },
    )

    projection = normalize_solver_output_projection(run_id="run-v2-rot", snapshot_row=_snapshot(), run_dir=run_dir)
    by_instance = _instance_map(projection.placements)
    child = by_instance["child-a:0"]
    t = child["transform_jsonb"]
    assert isinstance(t, dict)
    assert float(t["x"]) == 46.0
    assert float(t["y"]) == 62.0
    assert float(t["rotation_deg"]) == 270.0


def test_v2_quantity_mismatch_raises_ResultNormalizerError(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-v2-mismatch"
    _write_nesting_output(
        run_dir,
        {
            "version": "nesting_engine_v2",
            "status": "ok",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "__cavity_composite__parent-a__000000",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 50.0,
                    "y_mm": 60.0,
                    "rotation_deg": 0.0,
                }
            ],
            "unplaced": [],
            "objective": {"utilization_pct": 20.0},
            "meta": {},
        },
    )
    _write_cavity_plan(
        run_dir,
        {
            "version": "cavity_plan_v2",
            "enabled": True,
            "policy": {"mode": "recursive_cavity_prepack", "max_cavity_depth": 3},
            "virtual_parts": {
                "__cavity_composite__parent-a__000000": {
                    "kind": "parent_composite",
                    "parent_part_revision_id": "parent-a",
                    "parent_instance": 0,
                    "source_geometry_revision_id": "geo-parent-a",
                    "selected_nesting_derivative_id": "drv-parent-a",
                }
            },
            "placement_trees": {
                "__cavity_composite__parent-a__000000": {
                    "node_id": "node:parent-a:0",
                    "part_revision_id": "parent-a",
                    "instance": 0,
                    "kind": "top_level_virtual_parent",
                    "parent_node_id": None,
                    "parent_cavity_index": None,
                    "x_local_mm": 0.0,
                    "y_local_mm": 0.0,
                    "rotation_deg": 0,
                    "placement_origin_ref": "bbox_min_corner",
                    "children": [
                        {
                            "node_id": "node:child-a:0",
                            "part_revision_id": "child-a",
                            "instance": 0,
                            "kind": "internal_cavity_child",
                            "parent_node_id": "node:parent-a:0",
                            "parent_cavity_index": 0,
                            "x_local_mm": 2.0,
                            "y_local_mm": 4.0,
                            "rotation_deg": 0,
                            "placement_origin_ref": "bbox_min_corner",
                            "children": [],
                        }
                    ],
                }
            },
            "instance_bases": {
                "parent-a": {"internal_reserved_count": 0, "top_level_instance_base": 0},
                "child-a": {"internal_reserved_count": 2, "top_level_instance_base": 2},
            },
            "quantity_delta": {
                "parent-a": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
                "child-a": {"original_required_qty": 2, "internal_qty": 2, "top_level_qty": 0},
            },
            "diagnostics": [],
            "summary": {},
        },
    )

    with pytest.raises(ResultNormalizerError) as exc_info:
        normalize_solver_output_projection(run_id="run-v2-mismatch", snapshot_row=_snapshot(), run_dir=run_dir)
    assert "CAVITY_QUANTITY_MISMATCH" in str(exc_info.value)


def test_v1_cavity_plan_unchanged(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-v1-compat"
    _write_nesting_output(
        run_dir,
        {
            "version": "nesting_engine_v2",
            "status": "ok",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "__cavity_composite__parent-a__000000",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 50.0,
                    "y_mm": 60.0,
                    "rotation_deg": 90.0,
                }
            ],
            "unplaced": [],
            "objective": {"utilization_pct": 20.0},
            "meta": {},
        },
    )
    _write_cavity_plan(
        run_dir,
        {
            "version": "cavity_plan_v1",
            "enabled": True,
            "policy": {},
            "virtual_parts": {
                "__cavity_composite__parent-a__000000": {
                    "kind": "parent_composite",
                    "parent_part_revision_id": "parent-a",
                    "parent_instance": 1,
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
                }
            },
            "instance_bases": {"child-a": {"internal_reserved_count": 1, "top_level_instance_base": 1}},
            "quantity_delta": {"child-a": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0}},
            "diagnostics": [],
        },
    )

    projection = normalize_solver_output_projection(run_id="run-v1-compat", snapshot_row=_snapshot(), run_dir=run_dir)
    by_instance = _instance_map(projection.placements)
    child = by_instance["child-a:0"]
    t = child["transform_jsonb"]
    assert isinstance(t, dict)
    assert float(t["x"]) == 46.0
    assert float(t["y"]) == 62.0
    assert float(t["rotation_deg"]) == 270.0
    child_meta = child["metadata_jsonb"]
    assert isinstance(child_meta, dict)
    assert "cavity_tree_depth" not in child_meta


def test_v2_metrics_contain_cavity_plan_summary(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-v2-metrics-summary"
    _write_nesting_output(
        run_dir,
        {
            "version": "nesting_engine_v2",
            "status": "ok",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "__cavity_composite__parent-a__000000",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 50.0,
                    "y_mm": 60.0,
                    "rotation_deg": 0.0,
                }
            ],
            "unplaced": [],
            "objective": {"utilization_pct": 20.0},
            "meta": {},
        },
    )
    _write_cavity_plan(
        run_dir,
        {
            "version": "cavity_plan_v2",
            "enabled": True,
            "policy": {"mode": "recursive_cavity_prepack", "max_cavity_depth": 4},
            "virtual_parts": {
                "__cavity_composite__parent-a__000000": {
                    "kind": "parent_composite",
                    "parent_part_revision_id": "parent-a",
                    "parent_instance": 0,
                    "source_geometry_revision_id": "geo-parent-a",
                    "selected_nesting_derivative_id": "drv-parent-a",
                }
            },
            "placement_trees": {
                "__cavity_composite__parent-a__000000": {
                    "node_id": "node:parent-a:0",
                    "part_revision_id": "parent-a",
                    "instance": 0,
                    "kind": "top_level_virtual_parent",
                    "parent_node_id": None,
                    "parent_cavity_index": None,
                    "x_local_mm": 0.0,
                    "y_local_mm": 0.0,
                    "rotation_deg": 0,
                    "placement_origin_ref": "bbox_min_corner",
                    "children": [
                        {
                            "node_id": "node:child-a:0",
                            "part_revision_id": "child-a",
                            "instance": 0,
                            "kind": "internal_cavity_child",
                            "parent_node_id": "node:parent-a:0",
                            "parent_cavity_index": 0,
                            "x_local_mm": 3.0,
                            "y_local_mm": 4.0,
                            "rotation_deg": 90,
                            "placement_origin_ref": "bbox_min_corner",
                            "children": [],
                        }
                    ],
                }
            },
            "instance_bases": {
                "parent-a": {"internal_reserved_count": 0, "top_level_instance_base": 0},
                "child-a": {"internal_reserved_count": 1, "top_level_instance_base": 1},
            },
            "quantity_delta": {
                "parent-a": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
                "child-a": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
            },
            "diagnostics": [
                {"code": "child_has_holes_outer_proxy_used"},
                {"code": "child_has_holes_outer_proxy_used"},
                {"code": "some_other_diag"},
            ],
            "summary": {"usable_cavity_count": 7, "used_cavity_count": 2},
        },
    )

    projection = normalize_solver_output_projection(run_id="run-v2-metrics-summary", snapshot_row=_snapshot(), run_dir=run_dir)
    metrics_jsonb = projection.metrics.get("metrics_jsonb")
    assert isinstance(metrics_jsonb, dict)
    cavity_plan = metrics_jsonb.get("cavity_plan")
    assert isinstance(cavity_plan, dict)

    assert cavity_plan["enabled"] is True
    assert cavity_plan["version"] == "cavity_plan_v2"
    assert cavity_plan["cavity_plan_version"] == "cavity_plan_v2"
    assert int(cavity_plan["virtual_parent_count"]) == 1
    assert int(cavity_plan["placement_tree_count"]) == 1
    assert int(cavity_plan["max_cavity_depth"]) == 4
    assert int(cavity_plan["usable_cavity_count"]) == 7
    assert int(cavity_plan["used_cavity_count"]) == 2
    assert int(cavity_plan["internal_placement_count"]) == 1
    assert int(cavity_plan["nested_internal_placement_count"]) == 0
    assert int(cavity_plan["top_level_holes_removed_count"]) == 1
    assert int(cavity_plan["holed_child_proxy_count"]) == 2
    assert int(cavity_plan["total_internal_qty"]) == 1
    assert cavity_plan["quantity_delta_summary"] == {
        "parent-a": {"original": 1, "internal": 0, "top_level": 1},
        "child-a": {"original": 1, "internal": 1, "top_level": 0},
    }
    assert cavity_plan["diagnostics_by_code"] == {
        "child_has_holes_outer_proxy_used": 2,
        "some_other_diag": 1,
    }


def test_v1_metrics_unchanged(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-v1-metrics-shape"
    _write_nesting_output(
        run_dir,
        {
            "version": "nesting_engine_v2",
            "status": "ok",
            "sheets_used": 1,
            "placements": [
                {
                    "part_id": "__cavity_composite__parent-a__000000",
                    "instance": 0,
                    "sheet": 0,
                    "x_mm": 50.0,
                    "y_mm": 60.0,
                    "rotation_deg": 0.0,
                }
            ],
            "unplaced": [],
            "objective": {"utilization_pct": 20.0},
            "meta": {},
        },
    )
    _write_cavity_plan(
        run_dir,
        {
            "version": "cavity_plan_v1",
            "enabled": True,
            "policy": {},
            "virtual_parts": {
                "__cavity_composite__parent-a__000000": {
                    "kind": "parent_composite",
                    "parent_part_revision_id": "parent-a",
                    "parent_instance": 1,
                    "internal_placements": [],
                }
            },
            "instance_bases": {},
            "quantity_delta": {},
            "diagnostics": [{"code": "child_has_holes_outer_proxy_used"}],
        },
    )

    projection = normalize_solver_output_projection(run_id="run-v1-metrics-shape", snapshot_row=_snapshot(), run_dir=run_dir)
    metrics_jsonb = projection.metrics.get("metrics_jsonb")
    assert isinstance(metrics_jsonb, dict)
    cavity_plan = metrics_jsonb.get("cavity_plan")
    assert isinstance(cavity_plan, dict)
    assert cavity_plan == {
        "enabled": True,
        "version": "cavity_plan_v1",
        "virtual_parent_count": 1,
    }
