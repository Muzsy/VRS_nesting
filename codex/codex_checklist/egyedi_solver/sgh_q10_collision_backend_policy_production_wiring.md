# Checklist - SGH-Q10 `sgh_q10_collision_backend_policy_production_wiring`

## Dependency gate

- [x] Q09 report exists: `codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md`
- [x] Q09 report first line is `PASS`
- [x] Q09 report contains `SGH-Q10_STATUS: READY`

## Preflight reads

- [x] `AGENTS.md`
- [x] `docs/codex/overview.md`
- [x] `docs/codex/yaml_schema.md`
- [x] `docs/codex/report_standard.md`
- [x] `docs/qa/testing_guidelines.md`
- [x] `docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md`
- [x] `docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md`
- [x] `docs/egyedi_solver/sgh_q08_collision_backend_contract.md`
- [x] `docs/egyedi_solver/sgh_q09_phase_optimizer_production_wiring_contract.md`
- [x] `canvases/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md`
- [x] `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q10_collision_backend_policy_production_wiring.yaml`
- [x] `codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md`
- [x] `rust/vrs_solver/src/io.rs`
- [x] `rust/vrs_solver/src/adapter.rs`
- [x] `rust/vrs_solver/src/optimizer/collision_backend.rs`
- [x] `rust/vrs_solver/src/optimizer/repair.rs`
- [x] `rust/vrs_solver/src/optimizer/working.rs`
- [x] `rust/vrs_solver/src/optimizer/phase.rs`

## Pre-audit

- [x] `rg -n "find_violations\(|find_violations_with_backend|validate_and_commit|CollisionBackend|BboxCollisionBackend|JaguaPolygonExactBackend|CdeCollisionBackend" rust/vrs_solver/src` executed and documented in report

## Implementation

- [x] `CollisionBackendKind` enum added to `io.rs` (Bbox, JaguaPolygonExact, Cde)
- [x] `SolverInput.collision_backend: Option<CollisionBackendKind>` — missing = Bbox default
- [x] `CollisionBackendDiagnosticsOutput` added to `io.rs`
- [x] `SolverOutput.collision_backend_diagnostics: Option<CollisionBackendDiagnosticsOutput>`
- [x] `BackendValidationDiagnostics` struct added to `collision_backend.rs`
- [x] `BackendValidationResult` struct added to `repair.rs`
- [x] `validate_placements_with_backend_checked` added to `repair.rs` — no silent bbox fallback
- [x] `WorkingCommitError::UnsupportedBackend` variant added to `working.rs`
- [x] `BackendCommitResult` struct added to `working.rs`
- [x] `WorkingLayout::validate_and_commit_with_backend` added — bbox/jagua_polygon_exact/cde dispatch
- [x] Existing `working.rs` tests updated for non-irrefutable patterns
- [x] `adapter.rs`: `resolve_backend_kind` helper
- [x] `adapter.rs`: `backend_err_reason` helper
- [x] `adapter.rs`: `diag_output_from` helper
- [x] `adapter.rs`: LegacyMultisheet path has backend gate for non-bbox backends
- [x] `adapter.rs`: PhaseOptimizer path replaces double validation with single `validate_and_commit_with_backend`
- [x] `adapter.rs`: `_unsupported_output` updated for new `collision_backend_diagnostics` field
- [x] `adapter.rs`: `make_input` test helper updated with `collision_backend: None`

## Required tests (9)

- [x] `solver_input_collision_backend_defaults_to_bbox`
- [x] `explicit_bbox_matches_implicit_default_output`
- [x] `phase_optimizer_with_bbox_backend_preserves_q09_behavior`
- [x] `jagua_polygon_exact_backend_can_be_selected_in_solver_input`
- [x] `jagua_polygon_exact_invalid_outer_points_returns_unsupported_not_bbox_fallback`
- [x] `cde_backend_returns_unsupported_not_bbox_fallback`
- [x] `backend_validation_bbox_matches_find_violations` (repair.rs)
- [x] `backend_validation_reports_unsupported_count` (repair.rs)
- [x] `same_seed_same_backend_is_deterministic`
- [x] `jagua_polygon_exact_l_shape_notch_does_not_report_bbox_false_positive` (optional, included)

## Verification

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::collision_backend`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::working`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md`
