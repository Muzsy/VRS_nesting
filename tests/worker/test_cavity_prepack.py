from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from worker.cavity_prepack import (
    CavityPrepackGuardError,
    _empty_plan_v2,
    build_cavity_prepacked_engine_input,
    build_cavity_prepacked_engine_input_v2,
    validate_prepack_solver_input_hole_free,
)


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


def test_disabled_mode_returns_semantically_unchanged_input() -> None:
    parts = [
        {
            "id": "parent-a",
            "quantity": 1,
            "allowed_rotations_deg": [0, 90],
            "outer_points_mm": _rect(0.0, 0.0, 10.0, 10.0),
            "holes_points_mm": [_rect(2.0, 2.0, 8.0, 8.0)],
        }
    ]
    snapshot = _snapshot_for_parts(parts)
    base_input = _base_input(parts)
    original = deepcopy(base_input)

    out_input, plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot,
        base_engine_input=base_input,
        enabled=False,
    )

    assert out_input == original
    assert plan["version"] == "cavity_plan_v1"
    assert plan["enabled"] is False
    assert plan["virtual_parts"] == {}
    assert plan["quantity_delta"] == {}


def test_tiny_hole_has_virtual_parent_but_no_internal_child() -> None:
    parts = [
        {
            "id": "parent-a",
            "part_code": "PARENT_A",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 10.0, 10.0),
            "holes_points_mm": [_rect(4.0, 4.0, 5.0, 5.0)],
        },
        {
            "id": "child-a",
            "part_code": "CHILD_A",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 2.0, 2.0),
            "holes_points_mm": [],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    out_input, plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot,
        base_engine_input=_base_input(parts),
        enabled=True,
    )

    out_parts = out_input["parts"]
    assert isinstance(out_parts, list)
    assert all(part["id"] != "parent-a" for part in out_parts)
    virtual_ids = [str(part["id"]) for part in out_parts if str(part["id"]).startswith("__cavity_composite__")]
    assert len(virtual_ids) == 1
    virtual_part = next(part for part in out_parts if str(part["id"]) == virtual_ids[0])
    assert virtual_part["holes_points_mm"] == []
    child = next(part for part in out_parts if part["id"] == "child-a")
    assert int(child["quantity"]) == 1

    vp = plan["virtual_parts"][virtual_ids[0]]
    assert vp["internal_placements"] == []
    assert vp["cavity_diagnostics"][0]["status"] == "not_used_no_child_fit"


def test_usable_cavity_reserves_child_quantity_and_creates_instance_bases() -> None:
    parts = [
        {
            "id": "parent-a",
            "part_code": "PARENT_A",
            "quantity": 1,
            "allowed_rotations_deg": [0, 90],
            "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0),
            "holes_points_mm": [_rect(2.0, 2.0, 10.0, 10.0)],
        },
        {
            "id": "child-a",
            "part_code": "CHILD_A",
            "quantity": 3,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 3.0, 3.0),
            "holes_points_mm": [],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    out_input, plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot,
        base_engine_input=_base_input(parts),
        enabled=True,
    )

    virtual_id = next(key for key in plan["virtual_parts"].keys() if key.startswith("__cavity_composite__parent-a__"))
    internal = plan["virtual_parts"][virtual_id]["internal_placements"]
    assert len(internal) >= 1

    reserved = int(plan["quantity_delta"]["child-a"]["internal_qty"])
    top_level_qty = int(plan["quantity_delta"]["child-a"]["top_level_qty"])
    assert reserved >= 1
    assert top_level_qty == 3 - reserved
    assert plan["instance_bases"]["child-a"]["top_level_instance_base"] == reserved

    out_child = next((part for part in out_input["parts"] if part["id"] == "child-a"), None)
    if top_level_qty == 0:
        assert out_child is None
    else:
        assert out_child is not None
        assert int(out_child["quantity"]) == top_level_qty
    assert all(int(p["quantity"]) == 1 for p in out_input["parts"] if str(p["id"]).startswith("__cavity_composite__"))


def test_multiple_parent_instances_get_stable_virtual_ids() -> None:
    parts = [
        {
            "id": "parent-a",
            "part_code": "PARENT_A",
            "quantity": 2,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0),
            "holes_points_mm": [_rect(2.0, 2.0, 12.0, 12.0)],
        },
        {
            "id": "child-a",
            "part_code": "CHILD_A",
            "quantity": 2,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 3.0, 3.0),
            "holes_points_mm": [],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    out_input, plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot,
        base_engine_input=_base_input(parts),
        enabled=True,
    )
    ids = sorted(str(part["id"]) for part in out_input["parts"] if str(part["id"]).startswith("__cavity_composite__"))
    assert ids == [
        "__cavity_composite__parent-a__000000",
        "__cavity_composite__parent-a__000001",
    ]
    assert sorted(plan["virtual_parts"].keys()) == ids


def test_deterministic_output_for_identical_input() -> None:
    parts = [
        {
            "id": "parent-a",
            "part_code": "PARENT_A",
            "quantity": 2,
            "allowed_rotations_deg": [0, 90],
            "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0),
            "holes_points_mm": [_rect(2.0, 2.0, 12.0, 12.0)],
        },
        {
            "id": "child-a",
            "part_code": "CHILD_A",
            "quantity": 4,
            "allowed_rotations_deg": [0, 90],
            "outer_points_mm": _rect(0.0, 0.0, 2.0, 4.0),
            "holes_points_mm": [],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    base = _base_input(parts)
    out_a = build_cavity_prepacked_engine_input(snapshot_row=snapshot, base_engine_input=base, enabled=True)
    out_b = build_cavity_prepacked_engine_input(snapshot_row=snapshot, base_engine_input=base, enabled=True)
    assert out_a == out_b


def test_holed_child_diagnostic_is_outer_proxy_used() -> None:
    parts = [
        {
            "id": "parent-a",
            "part_code": "PARENT_A",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0),
            "holes_points_mm": [_rect(2.0, 2.0, 12.0, 12.0)],
        },
        {
            "id": "child-hole",
            "part_code": "CHILD_HOLE",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 8.0, 8.0),
            "holes_points_mm": [_rect(2.0, 2.0, 4.0, 4.0)],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    _out_input, plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot,
        base_engine_input=_base_input(parts),
        enabled=True,
    )
    diagnostics = [item for item in plan["diagnostics"] if isinstance(item, dict)]
    outer_proxy_diags = [item for item in diagnostics if str(item.get("code") or "") == "child_has_holes_outer_proxy_used"]
    assert len(outer_proxy_diags) >= 1
    first = outer_proxy_diags[0]
    assert first.get("child_part_revision_id") == "child-hole"
    assert int(first.get("hole_count") or 0) == 1


def test_no_filename_or_special_case_hardcode() -> None:
    src = Path(__file__).resolve().parents[2] / "worker" / "cavity_prepack.py"
    text = src.read_text(encoding="utf-8")
    assert "OTSZOG_BODYPAD" not in text
    assert "NEGYZET" not in text
    assert "MACSKANYELV" not in text


def test_guard_passes_if_no_top_level_holes() -> None:
    engine_input = {
        "parts": [
            {"id": "__cavity_composite__parent-a__000000", "holes_points_mm": [], "quantity": 1},
            {"id": "child-a", "holes_points_mm": [], "quantity": 2},
        ]
    }
    validate_prepack_solver_input_hole_free(engine_input)


def test_guard_fails_if_holes_remain() -> None:
    engine_input = {
        "parts": [
            {
                "id": "parent-a",
                "holes_points_mm": [_rect(1.0, 1.0, 2.0, 2.0)],
                "quantity": 1,
            }
        ]
    }
    with pytest.raises(CavityPrepackGuardError) as exc_info:
        validate_prepack_solver_input_hole_free(engine_input)
    msg = str(exc_info.value)
    assert "CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN" in msg
    assert "parent-a" in msg


def test_guard_reports_all_violating_parts() -> None:
    engine_input = {
        "parts": [
            {"id": "p-1", "holes_points_mm": [_rect(1.0, 1.0, 2.0, 2.0)], "quantity": 1},
            {"id": "p-2", "holes_points_mm": [], "quantity": 1},
            {"id": "p-3", "holes_points_mm": [_rect(3.0, 3.0, 4.0, 4.0)], "quantity": 1},
        ]
    }
    with pytest.raises(CavityPrepackGuardError) as exc_info:
        validate_prepack_solver_input_hole_free(engine_input)
    msg = str(exc_info.value)
    assert "p-1" in msg
    assert "p-3" in msg
    assert "p-2" not in msg


def test_holed_child_enters_candidate_list() -> None:
    parts = [
        {
            "id": "parent-a",
            "part_code": "PARENT_A",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 100.0, 100.0),
            "holes_points_mm": [_rect(10.0, 10.0, 90.0, 90.0)],
        },
        {
            "id": "child-b",
            "part_code": "CHILD_B",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0),
            "holes_points_mm": [_rect(5.0, 5.0, 15.0, 15.0)],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    out_input, plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot,
        base_engine_input=_base_input(parts),
        enabled=True,
    )
    virtual = next(iter(plan["virtual_parts"].values()))
    internal = virtual["internal_placements"]
    assert len(internal) >= 1
    assert internal[0]["child_part_revision_id"] == "child-b"
    assert int(plan["quantity_delta"]["child-b"]["internal_qty"]) >= 1
    out_parts = out_input["parts"]
    assert all(part["id"] != "child-b" for part in out_parts)


def test_v1_solid_child_behavior_unchanged() -> None:
    parts = [
        {
            "id": "parent-a",
            "part_code": "PARENT_A",
            "quantity": 1,
            "allowed_rotations_deg": [0, 90],
            "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0),
            "holes_points_mm": [_rect(2.0, 2.0, 10.0, 10.0)],
        },
        {
            "id": "child-solid",
            "part_code": "CHILD_SOLID",
            "quantity": 3,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 3.0, 3.0),
            "holes_points_mm": [],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    out_input, plan = build_cavity_prepacked_engine_input(
        snapshot_row=snapshot,
        base_engine_input=_base_input(parts),
        enabled=True,
    )
    virtual_id = next(key for key in plan["virtual_parts"] if key.startswith("__cavity_composite__parent-a__"))
    internal = plan["virtual_parts"][virtual_id]["internal_placements"]
    assert len(internal) >= 1
    reserved = int(plan["quantity_delta"]["child-solid"]["internal_qty"])
    top_level_qty = int(plan["quantity_delta"]["child-solid"]["top_level_qty"])
    assert top_level_qty == 3 - reserved
    diagnostics = [item for item in plan["diagnostics"] if isinstance(item, dict)]
    codes = [str(item.get("code") or "") for item in diagnostics]
    assert "child_has_holes_outer_proxy_used" not in codes
    if top_level_qty > 0:
        top_child = next(part for part in out_input["parts"] if part["id"] == "child-solid")
        assert int(top_child["quantity"]) == top_level_qty


def test_v2_matrjoska_three_level() -> None:
    parts = [
        {
            "id": "A",
            "part_code": "A",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 120.0, 120.0),
            "holes_points_mm": [_rect(10.0, 10.0, 90.0, 90.0)],
        },
        {
            "id": "B",
            "part_code": "B",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 80.0, 80.0),
            "holes_points_mm": [_rect(10.0, 10.0, 70.0, 70.0)],
        },
        {
            "id": "C",
            "part_code": "C",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 30.0, 30.0),
            "holes_points_mm": [],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    out_input, plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot,
        base_engine_input=_base_input(parts),
        enabled=True,
    )

    assert plan["version"] == "cavity_plan_v2"
    assert all(part["holes_points_mm"] == [] for part in out_input["parts"])

    top_level_ids = {str(part["id"]) for part in out_input["parts"]}
    assert "C" not in top_level_ids

    virtual_a = next(key for key in plan["placement_trees"] if key.startswith("__cavity_composite__A__"))
    root = plan["placement_trees"][virtual_a]
    root_children = [child for child in root.get("children", []) if isinstance(child, dict)]
    b_node = next(child for child in root_children if str(child.get("part_revision_id") or "") == "B")
    b_children = [child for child in b_node.get("children", []) if isinstance(child, dict)]
    assert any(str(child.get("part_revision_id") or "") == "C" for child in b_children)


def test_v2_cycle_protection() -> None:
    parts = [
        {
            "id": "A",
            "part_code": "A",
            "quantity": 2,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 120.0, 120.0),
            "holes_points_mm": [_rect(10.0, 10.0, 90.0, 90.0)],
        }
    ]
    snapshot = _snapshot_for_parts(parts)
    out_input, plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot,
        base_engine_input=_base_input(parts),
        enabled=True,
    )

    assert all(part["holes_points_mm"] == [] for part in out_input["parts"])
    for tree in plan["placement_trees"].values():
        children = [child for child in tree.get("children", []) if isinstance(child, dict)]
        assert children == []
    assert int(plan["quantity_delta"]["A"]["internal_qty"]) == 0
    assert int(plan["quantity_delta"]["A"]["top_level_qty"]) == 2


def test_v2_quantity_invariant() -> None:
    parts = [
        {
            "id": "A",
            "part_code": "A",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 120.0, 120.0),
            "holes_points_mm": [_rect(10.0, 10.0, 90.0, 90.0)],
        },
        {
            "id": "B",
            "part_code": "B",
            "quantity": 2,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 80.0, 80.0),
            "holes_points_mm": [_rect(10.0, 10.0, 70.0, 70.0)],
        },
        {
            "id": "C",
            "part_code": "C",
            "quantity": 4,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 20.0, 20.0),
            "holes_points_mm": [],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    _out_input, plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot,
        base_engine_input=_base_input(parts),
        enabled=True,
    )

    for part in parts:
        part_id = str(part["id"])
        original = int(part["quantity"])
        metrics = plan["quantity_delta"][part_id]
        internal_qty = int(metrics["internal_qty"])
        top_level_qty = int(metrics["top_level_qty"])
        assert internal_qty + top_level_qty == original


def test_v2_disabled_mode() -> None:
    parts = [
        {
            "id": "A",
            "part_code": "A",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 120.0, 120.0),
            "holes_points_mm": [_rect(10.0, 10.0, 90.0, 90.0)],
        }
    ]
    snapshot = _snapshot_for_parts(parts)
    base_input = _base_input(parts)
    out_input, plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot,
        base_engine_input=base_input,
        enabled=False,
    )

    assert out_input == base_input
    assert plan["version"] == "cavity_plan_v2"
    assert plan["enabled"] is False
    assert plan["virtual_parts"] == {}
    assert plan["placement_trees"] == {}
    assert plan["instance_bases"] == {}
    assert plan["quantity_delta"] == {}
    assert plan["diagnostics"] == []
    assert plan["summary"] == {}


def test_v2_max_depth_respected() -> None:
    parts = [
        {
            "id": "A",
            "part_code": "A",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 120.0, 120.0),
            "holes_points_mm": [_rect(10.0, 10.0, 90.0, 90.0)],
        },
        {
            "id": "B",
            "part_code": "B",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 80.0, 80.0),
            "holes_points_mm": [_rect(10.0, 10.0, 70.0, 70.0)],
        },
        {
            "id": "C",
            "part_code": "C",
            "quantity": 1,
            "allowed_rotations_deg": [0],
            "outer_points_mm": _rect(0.0, 0.0, 30.0, 30.0),
            "holes_points_mm": [],
        },
    ]
    snapshot = _snapshot_for_parts(parts)
    out_input, plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=snapshot,
        base_engine_input=_base_input(parts),
        enabled=True,
        max_cavity_depth=1,
    )

    virtual_a = next(key for key in plan["placement_trees"] if key.startswith("__cavity_composite__A__"))
    root = plan["placement_trees"][virtual_a]
    root_children = [child for child in root.get("children", []) if isinstance(child, dict)]
    b_node = next(child for child in root_children if str(child.get("part_revision_id") or "") == "B")
    assert b_node.get("children") == []

    top_level_ids = {str(part["id"]) for part in out_input["parts"]}
    assert "C" in top_level_ids


def test_empty_plan_v2_enabled_schema() -> None:
    plan = _empty_plan_v2(enabled=True, max_cavity_depth=4)
    assert plan["version"] == "cavity_plan_v2"
    assert plan["enabled"] is True
    assert plan["policy"]["mode"] == "recursive_cavity_prepack"
    assert plan["policy"]["max_cavity_depth"] == 4
    assert plan["virtual_parts"] == {}
    assert plan["placement_trees"] == {}
    assert plan["instance_bases"] == {}
    assert plan["quantity_delta"] == {}
    assert plan["diagnostics"] == []
    assert plan["summary"] == {}
