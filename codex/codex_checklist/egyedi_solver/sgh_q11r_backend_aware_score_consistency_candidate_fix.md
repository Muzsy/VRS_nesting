# SGH-Q11R Checklist — Backend-aware score consistency + candidate evaluation fix

## Dependency gate

- [x] `codex/reports/egyedi_solver/sgh_q11_backend_aware_scoring_separator.md` exists.
- [x] First line is `PASS`.
- [x] Q11 readiness is treated as superseded until Q11R verifies green.

## Implementation checklist

- [x] `PhaseOptimizer::run()` initial/final/result score uses `score_with_backend(..., &config.collision_backend)`.
- [x] `ExplorationPhase::run()` initial/incumbent score uses `score_with_backend`.
- [x] `CompressionPhase::run()` initial/incumbent score uses `score_with_backend`.
- [x] Phase1 adapter `score_breakdown` uses selected backend policy.
- [x] `VrsSeparator::find_best_candidate_for_target()` ranks candidates using backend-aware candidate loss.
- [x] Bbox separator path keeps the legacy fast bbox behavior.
- [x] Exact separator path uses `placement_within_sheet` and `placement_overlaps` for candidate evaluation.
- [x] CDE candidate path rejects/hard-fails instead of silently downgrading.
- [x] `SheetEliminationEngine` carries `CollisionBackendKind`.
- [x] Legacy constructors default to Bbox.
- [x] `BppPhase::run()` passes `config.collision_backend` into `SheetEliminationEngine`.
- [x] Sheet elimination commit/fallback/LBF paths use backend-aware validation where needed.

## Tests added/updated

- [x] `bbox_default_still_matches_legacy_score`
- [x] `phase_optimizer_score_uses_backend_for_exact_notch`
- [x] `exploration_initial_score_uses_backend`
- [x] `compression_initial_score_uses_backend`
- [x] `adapter_score_breakdown_uses_selected_backend`
- [x] `separator_exact_candidate_loss_ignores_bbox_false_positive`
- [x] `sheet_elimination_engine_passes_backend_to_separator_fallback`
- [x] `sheet_elimination_exact_lbf_candidate_does_not_reject_bbox_false_positive`
- [x] `sheet_elimination_exact_commit_gate_no_silent_bbox_fallback`
- [x] `cde_internal_paths_reject_or_hard_penalty_no_silent_success`

## Verification status

- [x] Static code/audit grep was run in packaging environment.
- [ ] Rust tests were run in packaging environment.
- [ ] `./scripts/verify.sh` was run in packaging environment.

Packaging environment did not contain `cargo`/`rustc`, so the Rust test and project verify gates must be run locally before marking Q11R as PASS.
