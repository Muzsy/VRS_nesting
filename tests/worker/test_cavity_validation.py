from __future__ import annotations

import pytest

from worker.cavity_validation import (
    CavityValidationError,
    validate_cavity_plan_v2,
)


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _base_plan(
    *,
    virtual_id: str,
    parent_part_id: str,
    parent_instance: int,
    tree_children: list[dict[str, object]],
    quantity_delta: dict[str, dict[str, int]],
) -> dict[str, object]:
    return {
        "version": "cavity_plan_v2",
        "enabled": True,
        "policy": {"mode": "recursive_cavity_prepack", "max_cavity_depth": 3},
        "virtual_parts": {
            virtual_id: {
                "kind": "parent_composite",
                "parent_part_revision_id": parent_part_id,
                "parent_instance": parent_instance,
                "source_geometry_revision_id": f"geo-{parent_part_id}",
                "selected_nesting_derivative_id": f"drv-{parent_part_id}",
            }
        },
        "placement_trees": {
            virtual_id: {
                "node_id": f"node:{parent_part_id}:{parent_instance}",
                "part_revision_id": parent_part_id,
                "instance": parent_instance,
                "kind": "top_level_virtual_parent",
                "parent_node_id": None,
                "parent_cavity_index": None,
                "x_local_mm": 0.0,
                "y_local_mm": 0.0,
                "rotation_deg": 0,
                "placement_origin_ref": "bbox_min_corner",
                "children": tree_children,
            }
        },
        "instance_bases": {},
        "quantity_delta": quantity_delta,
        "diagnostics": [],
        "summary": {},
    }


def test_valid_single_level_passes() -> None:
    part_records = [
        {"part_id": "P", "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0), "holes_points_mm": [_rect(2.0, 2.0, 18.0, 18.0)]},
        {"part_id": "C", "outer_points_mm": _rect(0.0, 0.0, 4.0, 4.0), "holes_points_mm": []},
    ]
    plan = _base_plan(
        virtual_id="__cavity_composite__P__000000",
        parent_part_id="P",
        parent_instance=0,
        tree_children=[
            {
                "node_id": "node:C:0",
                "part_revision_id": "C",
                "instance": 0,
                "kind": "internal_cavity_child",
                "parent_node_id": "node:P:0",
                "parent_cavity_index": 0,
                "x_local_mm": 3.0,
                "y_local_mm": 3.0,
                "rotation_deg": 0,
                "placement_origin_ref": "bbox_min_corner",
                "children": [],
            }
        ],
        quantity_delta={
            "P": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
            "C": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
        },
    )
    solver_placements = [
        {
            "part_id": "__cavity_composite__P__000000",
            "x_mm": 100.0,
            "y_mm": 50.0,
            "rotation_deg": 0.0,
        }
    ]
    issues = validate_cavity_plan_v2(
        cavity_plan=plan,
        part_records=part_records,
        solver_placements=solver_placements,
        strict=True,
    )
    assert issues == []


def test_child_outside_cavity_fails() -> None:
    part_records = [
        {"part_id": "P", "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0), "holes_points_mm": [_rect(2.0, 2.0, 18.0, 18.0)]},
        {"part_id": "C", "outer_points_mm": _rect(0.0, 0.0, 4.0, 4.0), "holes_points_mm": []},
    ]
    plan = _base_plan(
        virtual_id="__cavity_composite__P__000000",
        parent_part_id="P",
        parent_instance=0,
        tree_children=[
            {
                "node_id": "node:C:0",
                "part_revision_id": "C",
                "instance": 0,
                "kind": "internal_cavity_child",
                "parent_node_id": "node:P:0",
                "parent_cavity_index": 0,
                "x_local_mm": 15.0,
                "y_local_mm": 15.0,
                "rotation_deg": 0,
                "placement_origin_ref": "bbox_min_corner",
                "children": [],
            }
        ],
        quantity_delta={
            "P": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
            "C": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
        },
    )
    solver_placements = [{"part_id": "__cavity_composite__P__000000", "x_mm": 0.0, "y_mm": 0.0, "rotation_deg": 0.0}]

    with pytest.raises(CavityValidationError) as exc_info:
        validate_cavity_plan_v2(
            cavity_plan=plan,
            part_records=part_records,
            solver_placements=solver_placements,
            strict=True,
        )
    assert "CAVITY_CHILD_OUTSIDE_PARENT_CAVITY" in str(exc_info.value)


def test_child_child_overlap_fails() -> None:
    part_records = [
        {"part_id": "P", "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0), "holes_points_mm": [_rect(2.0, 2.0, 18.0, 18.0)]},
        {"part_id": "C1", "outer_points_mm": _rect(0.0, 0.0, 8.0, 8.0), "holes_points_mm": []},
        {"part_id": "C2", "outer_points_mm": _rect(0.0, 0.0, 8.0, 8.0), "holes_points_mm": []},
    ]
    plan = _base_plan(
        virtual_id="__cavity_composite__P__000000",
        parent_part_id="P",
        parent_instance=0,
        tree_children=[
            {
                "node_id": "node:C1:0",
                "part_revision_id": "C1",
                "instance": 0,
                "kind": "internal_cavity_child",
                "parent_node_id": "node:P:0",
                "parent_cavity_index": 0,
                "x_local_mm": 2.0,
                "y_local_mm": 2.0,
                "rotation_deg": 0,
                "placement_origin_ref": "bbox_min_corner",
                "children": [],
            },
            {
                "node_id": "node:C2:0",
                "part_revision_id": "C2",
                "instance": 0,
                "kind": "internal_cavity_child",
                "parent_node_id": "node:P:0",
                "parent_cavity_index": 0,
                "x_local_mm": 6.0,
                "y_local_mm": 6.0,
                "rotation_deg": 0,
                "placement_origin_ref": "bbox_min_corner",
                "children": [],
            },
        ],
        quantity_delta={
            "P": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
            "C1": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
            "C2": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
        },
    )
    solver_placements = [{"part_id": "__cavity_composite__P__000000", "x_mm": 0.0, "y_mm": 0.0, "rotation_deg": 0.0}]

    issues = validate_cavity_plan_v2(
        cavity_plan=plan,
        part_records=part_records,
        solver_placements=solver_placements,
        strict=False,
    )
    codes = [issue.code for issue in issues]
    assert "CAVITY_CHILD_CHILD_OVERLAP" in codes


def test_quantity_mismatch_fails() -> None:
    part_records = [
        {"part_id": "P", "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0), "holes_points_mm": [_rect(2.0, 2.0, 18.0, 18.0)]},
        {"part_id": "C", "outer_points_mm": _rect(0.0, 0.0, 4.0, 4.0), "holes_points_mm": []},
    ]
    plan = _base_plan(
        virtual_id="__cavity_composite__P__000000",
        parent_part_id="P",
        parent_instance=0,
        tree_children=[
            {
                "node_id": "node:C:0",
                "part_revision_id": "C",
                "instance": 0,
                "kind": "internal_cavity_child",
                "parent_node_id": "node:P:0",
                "parent_cavity_index": 0,
                "x_local_mm": 3.0,
                "y_local_mm": 3.0,
                "rotation_deg": 0,
                "placement_origin_ref": "bbox_min_corner",
                "children": [],
            }
        ],
        quantity_delta={
            "P": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
            "C": {"original_required_qty": 2, "internal_qty": 2, "top_level_qty": 0},
        },
    )
    solver_placements = [{"part_id": "__cavity_composite__P__000000", "x_mm": 0.0, "y_mm": 0.0, "rotation_deg": 0.0}]

    with pytest.raises(CavityValidationError) as exc_info:
        validate_cavity_plan_v2(
            cavity_plan=plan,
            part_records=part_records,
            solver_placements=solver_placements,
            strict=True,
        )
    assert "CAVITY_QUANTITY_MISMATCH" in str(exc_info.value)


def test_matrjoska_valid_three_level() -> None:
    part_records = [
        {"part_id": "A", "outer_points_mm": _rect(0.0, 0.0, 40.0, 40.0), "holes_points_mm": [_rect(5.0, 5.0, 35.0, 35.0)]},
        {"part_id": "B", "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0), "holes_points_mm": [_rect(2.0, 2.0, 18.0, 18.0)]},
        {"part_id": "C", "outer_points_mm": _rect(0.0, 0.0, 4.0, 4.0), "holes_points_mm": []},
    ]
    plan = _base_plan(
        virtual_id="__cavity_composite__A__000000",
        parent_part_id="A",
        parent_instance=0,
        tree_children=[
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
                        "x_local_mm": 3.0,
                        "y_local_mm": 3.0,
                        "rotation_deg": 0,
                        "placement_origin_ref": "bbox_min_corner",
                        "children": [],
                    }
                ],
            }
        ],
        quantity_delta={
            "A": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
            "B": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
            "C": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
        },
    )
    solver_placements = [{"part_id": "__cavity_composite__A__000000", "x_mm": 100.0, "y_mm": 100.0, "rotation_deg": 0.0}]
    issues = validate_cavity_plan_v2(
        cavity_plan=plan,
        part_records=part_records,
        solver_placements=solver_placements,
        strict=True,
    )
    assert issues == []


def test_strict_false_returns_issues() -> None:
    part_records = [
        {"part_id": "P", "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0), "holes_points_mm": [_rect(2.0, 2.0, 18.0, 18.0)]},
        {"part_id": "C", "outer_points_mm": _rect(0.0, 0.0, 4.0, 4.0), "holes_points_mm": []},
    ]
    plan = _base_plan(
        virtual_id="__cavity_composite__P__000000",
        parent_part_id="P",
        parent_instance=0,
        tree_children=[
            {
                "node_id": "node:C:0",
                "part_revision_id": "C",
                "instance": 0,
                "kind": "internal_cavity_child",
                "parent_node_id": "node:P:0",
                "parent_cavity_index": 0,
                "x_local_mm": 20.0,
                "y_local_mm": 20.0,
                "rotation_deg": 0,
                "placement_origin_ref": "bbox_min_corner",
                "children": [],
            }
        ],
        quantity_delta={
            "P": {"original_required_qty": 1, "internal_qty": 0, "top_level_qty": 1},
            "C": {"original_required_qty": 1, "internal_qty": 1, "top_level_qty": 0},
        },
    )
    solver_placements = [{"part_id": "__cavity_composite__P__000000", "x_mm": 0.0, "y_mm": 0.0, "rotation_deg": 0.0}]

    issues = validate_cavity_plan_v2(
        cavity_plan=plan,
        part_records=part_records,
        solver_placements=solver_placements,
        strict=False,
    )
    assert issues
    codes = [issue.code for issue in issues]
    assert "CAVITY_CHILD_OUTSIDE_PARENT_CAVITY" in codes
