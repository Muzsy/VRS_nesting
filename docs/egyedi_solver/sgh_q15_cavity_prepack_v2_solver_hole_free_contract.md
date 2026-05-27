# SGH-Q15 — Cavity prepack v2 solver-hole-free contract

## Status

**PASS** — MAIN_SOLVER_MUST_BE_HOLE_FREE invariant proven and hardened. 376 tests pass.

## Overview

SGH-Q15 hardens the contract that the main VRS nesting solver receives only
hole-free (outer-only) parts after `cavity_prepack_v2`. It does **not** introduce
CDE hole-aware collision in the main solver.

## Architecture

```text
base input:  parts may have holes_points_mm (from DXF/geometry manifest)
prepack:     build_cavity_prepacked_engine_input_v2(enabled=True)
               → virtual_parts (outer-only solver proxies, holes_points_mm=[])
               → remaining top-level parts (holes_points_mm=[])
gate:        validate_prepack_solver_input_hole_free(solver_input)
               → raises CavityPrepackGuardError if any part has holes
solver:      receives outer-only input — NOT hole-aware
post-solve:  validate_cavity_plan_v2 → verifies child containment, no overlap
normalizer:  _flatten_cavity_plan_v2_tree → expands virtual parent solver
             placement into top_level_parent + internal_cavity placement rows
```

## MAIN_SOLVER_MUST_BE_HOLE_FREE Invariant

After `build_cavity_prepacked_engine_input_v2(enabled=True)`:

```text
out_input["parts"][*]["holes_points_mm"] == []
```

This applies to:
- Virtual module/parent composite solver parts
- Remaining top-level non-holed parts
- Any generated solver part

The prepack builds virtual parts with `"holes_points_mm": []` explicitly and
strips hole geometry from remaining top-level parts.

## Production Boundary Gate

`validate_prepack_solver_input_hole_free(engine_input)` is called in `main.py`
at line 1722 when `profile_resolution.requested_part_in_part_policy == "prepack"`.
It raises `CavityPrepackGuardError("CAVITY_PREPACK_TOP_LEVEL_HOLES_REMAIN: ...")`.

No silent hole passthrough reaches the main solver on the prepack path.

## Cavity Metadata Preserved in cavity_plan_v2

```text
version         = "cavity_plan_v2"
virtual_parts   — solver ID → parent_part_revision_id, parent_instance, etc.
placement_trees — solver ID → recursive node tree (parent + internal_cavity children)
instance_bases  — per part_revision_id: internal_reserved_count, top_level_instance_base
quantity_delta  — per part_revision_id: original_required_qty, internal_qty, top_level_qty
diagnostics     — per-cavity prepack decision log
summary         — aggregate stats
```

Invariant: `internal_qty + top_level_qty == original_required_qty` for every part.

## Expansion (result_normalizer)

`_flatten_cavity_plan_v2_tree` recursively walks each placement tree node:

```text
root node (top_level_virtual_parent):
  → placement_scope: "top_level_parent"  (absolute solver x/y/rotation)
child node (internal_cavity_child):
  → placement_scope: "internal_cavity"   (abs = parent_abs + local_offset)
  → metadata: parent_part_revision_id, parent_instance, cavity_tree_depth
```

Virtual composite IDs (`__cavity_composite__*`) never appear in projection output.

## Cavity Validation Gate

`validate_cavity_plan_v2` runs after solving (main.py line 2002). It checks:

```text
CAVITY_CHILD_OUTSIDE_PARENT_CAVITY  — child placed outside selected cavity polygon
CAVITY_CHILD_CHILD_OVERLAP          — two sibling children overlap in same cavity
CAVITY_QUANTITY_MISMATCH            — tree child count != quantity_delta.internal_qty
CAVITY_TREE_DEPTH_EXCEEDED          — nesting depth > max_depth (default 3)
```

When `strict=True` (production), any issue raises `CavityValidationError` and
the run is not marked successful.

## What Q15 Is Not

```text
Q15 does NOT implement CDE hole-aware item collision in the main solver.
Q15 does NOT pass part holes to the Rust/main solver.
Q15 does NOT replace cavity_prepack_v2.
Q15 does NOT introduce new cavity placement optimization.
Q15 does NOT refactor DXF/preflight.
```

Cavity semantics live entirely in prepack + cavity_plan_v2 + validation + expansion.

## Modified Files

```text
tests/worker/test_cavity_prepack.py            — 7 Q15 contract hardening tests added
tests/worker/test_cavity_validation.py         — 2 Q15 contract hardening tests added
tests/worker/test_result_normalizer_cavity_plan.py — 1 Q15 contract hardening test added
```

No production code changes were required — the contract was already implemented.
Q15 adds explicit test coverage proving the invariants hold.

## Required Tests (10/10 passing)

```text
test_cavity_prepack_v2_outputs_hole_free_solver_input
test_cavity_prepack_v2_virtual_parent_has_empty_holes_points
test_cavity_prepack_v2_remaining_top_level_parts_have_empty_holes_points
test_validate_prepack_solver_input_hole_free_rejects_any_holes
test_cavity_prepack_v2_preserves_placement_tree_metadata
test_cavity_prepack_v2_quantity_delta_matches_internal_and_top_level
test_result_normalizer_expands_virtual_parent_to_internal_cavity_rows
test_validate_cavity_plan_v2_rejects_child_outside_cavity
test_validate_cavity_plan_v2_rejects_child_child_overlap
test_production_worker_rejects_or_blocks_hole_passthrough_without_prepack
```

## Acceptance Outcome

376 tests pass (10 new Q15, 366 pre-existing). verify.sh exits 0.
