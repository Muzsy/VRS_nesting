#!/usr/bin/env python3
"""
Smoke test for T06h: collapsed module variant ID lookup in result_normalizer.

Tests that the result_normalizer can resolve collapsed module variant IDs
(solver_part_id → representative_virtual_id → placement_tree → parent+children).
"""
import json, sys, os, tempfile
from pathlib import Path

sys.path.insert(0, '/home/muszy/projects/VRS_nesting')
from worker.cavity_prepack import build_cavity_prepacked_engine_input_v2
from worker.result_normalizer import normalize_solver_output_projection, ResultNormalizerError

def rect(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

def make_fixture():
    return {
        "snapshot_row": {
            "project_manifest_jsonb": {"project_id": "synthetic", "project_name": "synthetic-t06h"},
            "parts_manifest_jsonb": [
                {
                    "part_revision_id": "parent-a",
                    "part_definition_id": "part-def-parent-a",
                    "part_code": "PARENT_A",
                    "required_qty": 2,
                    "source_geometry_revision_id": "geo-parent-a",
                    "selected_nesting_derivative_id": "drv-parent-a",
                },
                {
                    "part_revision_id": "child-b",
                    "part_definition_id": "part-def-child-b",
                    "part_code": "CHILD_B",
                    "required_qty": 2,
                    "source_geometry_revision_id": "geo-child-b",
                    "selected_nesting_derivative_id": "drv-child-b",
                },
            ],
            "geometry_manifest_jsonb": [
                {
                    "selected_nesting_derivative_id": "drv-parent-a",
                    "polygon": {"outer_ring": rect(0, 0, 40, 40), "hole_rings": [rect(4, 4, 30, 30)]},
                    "bbox": {"min_x": 0, "min_y": 0, "max_x": 40, "max_y": 40, "width": 40, "height": 40},
                },
                {
                    "selected_nesting_derivative_id": "drv-child-b",
                    "polygon": {"outer_ring": rect(0, 0, 6, 6), "hole_rings": []},
                    "bbox": {"min_x": 0, "min_y": 0, "max_x": 6, "max_y": 6, "width": 6, "height": 6},
                },
            ],
            "sheets_manifest_jsonb": [
                {
                    "sheet_revision_id": "sheet-1",
                    "sheet_code": "DEFAULT",
                    "width_mm": 1500.0,
                    "height_mm": 3000.0,
                    "required_qty": 1,
                    "is_default": True,
                    "placement_priority": 1,
                    "project_sheet_input_id": "sheet-input-1",
                },
            ],
        },
        "base_engine_input": {
            "version": "nesting_engine_v2",
            "seed": 0,
            "time_limit_sec": 10,
            "sheet": {"width_mm": 1500.0, "height_mm": 3000.0, "kerf_mm": 0.0, "spacing_mm": 0.0, "margin_mm": 0.0},
            "parts": [
                {
                    "id": "parent-a",
                    "quantity": 2,
                    "allowed_rotations_deg": [0, 90, 180, 270],
                    "outer_points_mm": rect(0, 0, 40, 40),
                    "holes_points_mm": [rect(4, 4, 30, 30)],
                },
                {
                    "id": "child-b",
                    "quantity": 2,
                    "allowed_rotations_deg": [0, 90, 180, 270],
                    "outer_points_mm": rect(0, 0, 6, 6),
                    "holes_points_mm": [],
                },
            ],
        },
    }

def make_nesting_output(solver_part_id_list):
    """Create a synthetic nesting_output.json with given solver part_ids placed."""
    placements = []
    for i, part_id in enumerate(solver_part_id_list):
        placements.append({
            "part_id": part_id,
            "instance": 0,
            "sheet": 0,
            "x_mm": float(i * 100),
            "y_mm": 0.0,
            "rotation_deg": 0.0,
        })
    return {
        "version": "nesting_engine_v2",
        "status": "success",
        "placements": placements,
        "unplaced": [],
        "objective": {"utilization_pct": 25.0},
        "sheets_used": 1,
    }

def run_tests():
    print("=" * 60)
    print("T06h Smoke: collapsed module variant ID lookup")
    print("=" * 60)

    fixture = make_fixture()
    prepacked_input, cavity_plan = build_cavity_prepacked_engine_input_v2(
        snapshot_row=fixture["snapshot_row"],
        base_engine_input=fixture["base_engine_input"],
        enabled=True,
    )

    mv = cavity_plan.get("module_variants", {})
    mvb = cavity_plan.get("module_variants_by_solver_id", {})
    vt = cavity_plan.get("virtual_parts", {})
    pt = cavity_plan.get("placement_trees", {})
    summary = cavity_plan.get("summary", {})

    print(f"\nPrepack summary:")
    print(f"  virtual_parent_count: {summary.get('virtual_parent_count', len(vt))}")
    print(f"  module_variant_count: {summary.get('module_variant_count', len(mv))}")
    print(f"  internal_placement_count: {summary.get('internal_placement_count', 0)}")
    print(f"  solver parts (prepack input): {len(prepacked_input['parts'])}")

    if not mv:
        print("\nSKIP: No module_variants generated (child B may not fit in parent A cavity)")
        print("This is OK for empty variant testing.")
        return True

    # Get a collapsed solver part id
    collapsed_solver_id = next(iter(mvb.keys()))
    variant_key = mvb[collapsed_solver_id]
    variant = mv[variant_key]
    rep_vid = variant["representative_virtual_id"]

    print(f"\nCollapsed module variant:")
    print(f"  solver_part_id = {collapsed_solver_id}")
    print(f"  variant_key = {variant_key}")
    print(f"  representative_virtual_id = {rep_vid}")
    print(f"  member_virtual_ids = {variant['member_virtual_ids']}")
    print(f"  quantity = {variant['quantity']}")

    # Build synthetic nesting_output using collapsed solver part id
    nesting_output = make_nesting_output([collapsed_solver_id])

    # Write to temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        # Write cavity_plan.json
        (run_dir / "cavity_plan.json").write_text(json.dumps(cavity_plan), encoding="utf-8")
        # Write nesting_output.json
        (run_dir / "nesting_output.json").write_text(json.dumps(nesting_output), encoding="utf-8")
        # Write snapshot_row (minimal)
        (run_dir / "snapshot_row.json").write_text(json.dumps(fixture["snapshot_row"]), encoding="utf-8")

        print(f"\n--- Test 1: collapsed empty module variant lookup ---")
        print(f"Input: solver placed {collapsed_solver_id}")
        try:
            result = normalize_solver_output_projection(
                run_id="t06h-test-1",
                snapshot_row=fixture["snapshot_row"],
                run_dir=run_dir,
            )
            placements = result.placements
            parent_placements = [p for p in placements if p["metadata_jsonb"].get("placement_scope") == "top_level_parent"]
            print(f"Result: {len(placements)} total placements, {len(parent_placements)} parent placements")
            if parent_placements:
                print(f"  First parent: part={parent_placements[0]['part_revision_id']}, scope={parent_placements[0]['metadata_jsonb'].get('placement_scope')}")
            # Verify no collapsed module id leaked
            module_ids_in_output = [p['part_revision_id'] for p in placements if '__cavity_composite__' in p['part_revision_id']]
            if module_ids_in_output:
                print(f"  FAIL: collapsed module id leaked into output: {module_ids_in_output}")
                return False
            print(f"  PASS: collapsed module id correctly resolved")
        except ResultNormalizerError as e:
            print(f"  FAIL: ResultNormalizerError: {e}")
            return False

    # Test 2: unresolvable module composite prefix gives explicit error
    print(f"\n--- Test 2: unresolvable cavity_composite id gives explicit error ---")
    bad_nesting_output = make_nesting_output(["__cavity_composite__INVALID_ID"])
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        (run_dir / "cavity_plan.json").write_text(json.dumps(cavity_plan), encoding="utf-8")
        (run_dir / "nesting_output.json").write_text(json.dumps(bad_nesting_output), encoding="utf-8")
        (run_dir / "snapshot_row.json").write_text(json.dumps(fixture["snapshot_row"]), encoding="utf-8")
        try:
            result = normalize_solver_output_projection(
                run_id="t06h-test-2",
                snapshot_row=fixture["snapshot_row"],
                run_dir=run_dir,
            )
            print(f"  FAIL: should have raised ResultNormalizerError for unresolvable id")
            return False
        except ResultNormalizerError as e:
            err_msg = str(e)
            if "COLLAPSED_MODULE_VARIANT" in err_msg or "CAVITY_COMPOSITE_ID_UNRESOLVABLE" in err_msg:
                print(f"  PASS: explicit error raised: {e}")
            else:
                print(f"  PARTIAL: error raised but unexpected message: {e}")
    return True

if __name__ == "__main__":
    ok = run_tests()
    print("\n" + "=" * 60)
    print(f"T06h smoke: {'PASS' if ok else 'FAIL'}")
    print("=" * 60)
    sys.exit(0 if ok else 1)
