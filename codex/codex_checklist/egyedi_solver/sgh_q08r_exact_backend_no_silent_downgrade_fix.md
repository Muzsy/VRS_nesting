# Checklist - SGH-Q08R `sgh_q08r_exact_backend_no_silent_downgrade_fix`

## Dependency gate

- [x] Q08 report exists: `codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md`
- [x] Q08 report first line is `PASS`

## Preflight reads

- [x] `AGENTS.md`
- [x] `docs/codex/overview.md`
- [x] `docs/codex/yaml_schema.md`
- [x] `docs/codex/report_standard.md`
- [x] `docs/qa/testing_guidelines.md`
- [x] `docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md`
- [x] `docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md`
- [x] `docs/egyedi_solver/sgh_q08_collision_backend_contract.md`
- [x] `canvases/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md`
- [x] `codex/reports/egyedi_solver/sgh_q08_collision_backend_geometry_preprocessing.md`
- [x] `canvases/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md`
- [x] `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q08r_exact_backend_no_silent_downgrade_fix.yaml`
- [x] `rust/vrs_solver/src/optimizer/collision_backend.rs`
- [x] `rust/vrs_solver/src/optimizer/geometry_preprocessing.rs`
- [x] `rust/vrs_solver/src/optimizer/repair.rs`

## Implementation

- [x] Three-state polygon extraction: `Absent`, `Invalid`, `Valid`
- [x] Invalid exact geometry returns `Unsupported`
- [x] `polygons_collide` returns `Result<bool, reason>`
- [x] Exact backend rect path uses rotation-aware world rectangle polygon
- [x] Exact boundary path uses polygon-within-sheet for rect and polygon items
- [x] Touching edge/corner policy is explicit: no positive-area overlap means `NoCollision`
- [x] Bbox backend remains unchanged
- [x] CDE backend remains `Unsupported`

## Regression tests

- [x] `exact_backend_malformed_outer_points_returns_unsupported_not_bbox_fallback`
- [x] `exact_backend_degenerate_polygon_returns_unsupported_not_no_collision`
- [x] `exact_backend_rotated_rect_vs_rect_uses_true_rotated_geometry_not_aabb`
- [x] `exact_backend_rotated_rect_vs_irregular_uses_true_rotated_geometry_not_aabb`
- [x] `exact_backend_rect_boundary_check_is_rotation_aware`
- [x] `touching_rect_edges_are_not_collision`
- [x] `touching_rect_corners_are_not_collision`
- [x] `positive_area_overlap_is_collision`
- [x] `invalid_polygon_does_not_become_no_collision`
- [x] `bbox_backend_still_matches_existing_behavior`
- [x] `cde_backend_still_returns_unsupported`

## Verification

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::geometry_preprocessing`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::repair`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md`
