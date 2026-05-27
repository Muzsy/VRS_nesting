# Checklist — SGH-Q15 Cavity prepack v2 solver-hole-free contract hardening

## Dependency gate

- [x] `codex/reports/egyedi_solver/sgh_q14_cde_touching_semantics_parity_fix.md` first line: `PASS`
- [x] Q14 report contains `SGH-Q15_STATUS: READY`

## Audit

- [x] `build_cavity_prepacked_engine_input_v2` confirmed in `worker/cavity_prepack.py`
- [x] Virtual parts built with `"holes_points_mm": []` (line 1024)
- [x] Remaining top-level parts built with `"holes_points_mm": []` (line 1041)
- [x] `_rotation_shapes` uses outer-only proxy: `base_poly = _to_polygon(part.outer_points_mm, [])`
- [x] `validate_prepack_solver_input_hole_free` raises `CavityPrepackGuardError` on hole passthrough
- [x] Production wiring in `main.py`: prepack → gate → solver → validate_cavity_plan_v2

## Solver-input hole-free invariant

- [x] `build_cavity_prepacked_engine_input_v2(enabled=True)` → all parts have `holes_points_mm == []`
- [x] Virtual composite solver parts: `holes_points_mm == []`
- [x] Remaining top-level non-holed parts: `holes_points_mm == []`
- [x] `validate_prepack_solver_input_hole_free` gate blocks any hole passthrough

## Production boundary gate

- [x] `validate_prepack_solver_input_hole_free` wired in `main.py` line 1722
- [x] Raises `CavityPrepackGuardError("CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN: ...")` on failure
- [x] No silent hole passthrough on the prepack production path

## Metadata preservation

- [x] `cavity_plan_v2` keys present: `version`, `virtual_parts`, `placement_trees`, `instance_bases`, `quantity_delta`, `diagnostics`, `summary`
- [x] `quantity_delta`: `internal_qty + top_level_qty == original_required_qty` for all parts
- [x] `placement_trees` tree nodes carry: `part_revision_id`, `instance`, `kind`, `x_local_mm`, `y_local_mm`, `rotation_deg`, `parent_cavity_index`, `children`

## Expansion / normalizer gate

- [x] `_flatten_cavity_plan_v2_tree` expands virtual parent to `top_level_parent` row
- [x] Internal children emitted as `internal_cavity` rows with correct absolute coords
- [x] No `__cavity_composite__` IDs leak into projection output

## Cavity validation gate

- [x] `validate_cavity_plan_v2` wired in `main.py` lines 2002–2007
- [x] Raises `CavityValidationError` (strict=True) on child-outside-cavity
- [x] Raises/reports `CAVITY_CHILD_CHILD_OVERLAP` on sibling overlap
- [x] Raises `CavityValidationError` on quantity mismatch

## No main solver hole-aware CDE

- [x] Q15 does NOT introduce CDE hole-aware collision in the main solver
- [x] Q15 does NOT pass `holes_points_mm` to the Rust/main solver
- [x] Q15 does NOT replace `cavity_prepack_v2`
- [x] Documentation explicitly states: "The main solver remains outer-only after cavity_prepack_v2"

## Required tests (10/10 passing)

- [x] `test_cavity_prepack_v2_outputs_hole_free_solver_input`
- [x] `test_cavity_prepack_v2_virtual_parent_has_empty_holes_points`
- [x] `test_cavity_prepack_v2_remaining_top_level_parts_have_empty_holes_points`
- [x] `test_validate_prepack_solver_input_hole_free_rejects_any_holes`
- [x] `test_cavity_prepack_v2_preserves_placement_tree_metadata`
- [x] `test_cavity_prepack_v2_quantity_delta_matches_internal_and_top_level`
- [x] `test_result_normalizer_expands_virtual_parent_to_internal_cavity_rows`
- [x] `test_validate_cavity_plan_v2_rejects_child_outside_cavity`
- [x] `test_validate_cavity_plan_v2_rejects_child_child_overlap`
- [x] `test_production_worker_rejects_or_blocks_hole_passthrough_without_prepack`

## Verify

- [x] `python3 -m pytest tests worker -q -k "cavity or prepack or normalizer"` → 45 passed
- [x] `python3 -m pytest -q` → 376 passed, 0 failed
- [x] `./scripts/verify.sh --report ...` → PASS
