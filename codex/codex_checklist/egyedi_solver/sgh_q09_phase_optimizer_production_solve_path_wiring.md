# Checklist - SGH-Q09 `sgh_q09_phase_optimizer_production_solve_path_wiring`

## Dependency gate

- [x] Q08R report exists: `codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md`
- [x] Q08R report first line is `PASS`
- [x] Q08R report contains `SGH-Q09_STATUS: READY`

## Preflight reads

- [x] `AGENTS.md`
- [x] `docs/codex/overview.md`
- [x] `docs/codex/yaml_schema.md`
- [x] `docs/codex/report_standard.md`
- [x] `docs/qa/testing_guidelines.md`
- [x] `docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md`
- [x] `docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md`
- [x] `docs/egyedi_solver/sgh_q08_collision_backend_contract.md`
- [x] `canvases/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md`
- [x] `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q09_phase_optimizer_production_solve_path_wiring.yaml`
- [x] `codex/reports/egyedi_solver/sgh_q08r_exact_backend_no_silent_downgrade_fix.md`
- [x] `rust/vrs_solver/src/io.rs`
- [x] `rust/vrs_solver/src/adapter.rs`
- [x] `rust/vrs_solver/src/optimizer/multisheet.rs`
- [x] `rust/vrs_solver/src/optimizer/phase.rs`
- [x] `rust/vrs_solver/src/optimizer/working.rs`
- [x] `rust/vrs_solver/src/optimizer/initializer.rs`
- [x] `rust/vrs_solver/src/optimizer/repair.rs`

## Implementation

- [x] `OptimizerPipelineKind` optional input switch added
- [x] Missing `optimizer_pipeline` defaults to legacy behavior
- [x] Explicit `legacy_multisheet` matches implicit legacy output
- [x] Explicit `phase_optimizer` route invokes `PhaseOptimizer`
- [x] Phase route preserves `seed`, `RotationResolveContext`, and deterministic budgets
- [x] Phase route commits through `WorkingLayout::validate_and_commit`
- [x] Invalid phase commit returns `PHASE_OPTIMIZER_COMMIT_VIOLATION`
- [x] Optional phase diagnostics expose route and phase activity

## Verification

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml adapter`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::phase`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::multisheet`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml optimizer::working`
- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q09_phase_optimizer_production_solve_path_wiring.md`
