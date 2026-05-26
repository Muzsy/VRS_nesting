# Checklist - SGH-Q11 `sgh_q11_backend_aware_scoring_separator`

## Dependency gate

- [x] Q10 report exists: `codex/reports/egyedi_solver/sgh_q10_collision_backend_policy_production_wiring.md`
- [x] Q10 report first line is `PASS`
- [x] Q10 report contains `SGH-Q11_STATUS: READY`

## Preflight reads

- [x] `AGENTS.md`
- [x] `docs/codex/overview.md`
- [x] `docs/codex/yaml_schema.md`
- [x] `docs/codex/report_standard.md`
- [x] `docs/qa/testing_guidelines.md`
- [x] `docs/egyedi_solver/sgh_q00_quality_feature_gap_matrix.md`
- [x] `docs/egyedi_solver/sgh_q01_corrected_task_roadmap.md`
- [x] `docs/egyedi_solver/sgh_q10_collision_backend_policy_contract.md`
- [x] `rust/vrs_solver/src/io.rs`
- [x] `rust/vrs_solver/src/adapter.rs`
- [x] `rust/vrs_solver/src/optimizer/phase.rs`
- [x] `rust/vrs_solver/src/optimizer/repair.rs`
- [x] `rust/vrs_solver/src/optimizer/score.rs`
- [x] `rust/vrs_solver/src/optimizer/moves.rs`
- [x] `rust/vrs_solver/src/optimizer/separator.rs`
- [x] `rust/vrs_solver/src/optimizer/explore.rs`
- [x] `rust/vrs_solver/src/optimizer/compress.rs`
- [x] `rust/vrs_solver/src/optimizer/bpp_phase.rs`

## Implementation

- [x] `PhaseConfig.collision_backend: CollisionBackendKind` added (default `Bbox`)
- [x] `phase_config_from_input` propagates `collision_backend` from `SolverInput`
- [x] `validate_placements_for_backend` added to `repair.rs` — central no-fallback helper with sentinel pattern
- [x] `score_layout_from_violations` extracted as `pub(super)` helper in `score.rs`
- [x] `ScoreModel::score_with_backend` added — `Bbox` is bit-identical to `score()`
- [x] `MoveExecutor.collision_backend` field added (default `Bbox`)
- [x] `MoveExecutor::new_with_backend_and_rotation_context` constructor added
- [x] `MoveExecutor::commit_gate_ok` uses `validate_placements_for_backend`
- [x] `MoveExecutor::run_separator_fix` passes `collision_backend` to `VrsSeparatorConfig`
- [x] `VrsSeparatorConfig.collision_backend` field added (default `Bbox`)
- [x] `VrsCollisionTracker::build_with_model` takes `collision_backend` parameter
- [x] `compute_backend_decisions` free function added in `separator.rs` — routes Bbox/Exact/Cde
- [x] Separator Q11 transitional loss: `Unsupported` → hard penalty `1_000_000.0`
- [x] `ExplorationPhase::run` uses backend-aware validation, scoring, separator config
- [x] `LargeItemSwapDisruption` uses `new_with_backend_and_rotation_context`
- [x] `CompressionPhase::run` uses backend-aware validation and scoring
- [x] `BppPhase::run` uses backend-aware validation and scoring

## Required tests (12)

- [x] `separator_config_backend_default_bbox` (separator.rs)
- [x] `separator_tracker_exact_notch_pair_loss_zero_when_bbox_positive` (separator.rs)
- [x] `same_seed_same_backend_is_deterministic` (separator.rs)
- [x] `phase_config_defaults_collision_backend_bbox` (phase.rs)
- [x] `adapter_phase_optimizer_passes_collision_backend_to_phase_config` (adapter.rs)
- [x] `score_with_backend_bbox_matches_legacy_score` (score.rs)
- [x] `score_with_backend_exact_notch_false_positive_removed` (score.rs)
- [x] `move_executor_backend_aware_commit_gate_rejects_exact_unsupported` (moves.rs)
- [x] `exploration_phase_uses_backend_aware_validation_for_exact` (explore.rs)
- [x] `compression_phase_uses_backend_aware_validation_for_exact` (compress.rs)
- [x] `bpp_phase_uses_backend_aware_commit_gate_for_exact` (bpp_phase.rs)
- [x] `explicit_exact_no_silent_bbox_fallback_in_internal_search` (repair.rs)

## Verification

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib`
- [x] `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md`
