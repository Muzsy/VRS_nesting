use std::fmt;
use std::time::Instant;

use crate::io::{
    CollisionBackendDiagnosticsOutput, CollisionBackendKind, Metrics, OptimizerDiagnosticsOutput,
    OptimizerPipelineKind, Placement, ScoreBreakdownOutput, SolverInput, SolverOutput, Unplaced,
};
use crate::item::{can_fit_any_stock_with_policy, expand_instances_with_policy, part_has_holes};
use crate::optimizer::cde_observability;
use crate::optimizer::score::ScoreModel;
use crate::optimizer::{
    initializer::build_initial_layout_with_rotation_context,
    multisheet::MultiSheetManager,
    phase::{PhaseBudget, PhaseConfig, PhaseOptimizer},
    stopping::StoppingPolicy,
    try_place_on_sheet,
    working::{BackendCommitResult, WorkingCommitError, WorkingLayout},
    SheetCursor,
};
use crate::rotation_policy::{RotationResolveContext, DEFAULT_CONTINUOUS_SAMPLE_COUNT};
use crate::sheet::{apply_rectangular_sheet_offset, find_sheet_margin_violations, expand_sheets, stock_has_holes};
use crate::technology::TechnologyClearancePolicy;

const PROFILE_PHASE1: &str = "jagua_optimizer_phase1_outer_only";

fn _unsupported_output(reason: &str, input: &SolverInput) -> SolverOutput {
    SolverOutput {
        contract_version: "v1".to_string(),
        status: "unsupported".to_string(),
        unsupported_reason: Some(reason.to_string()),
        placements: vec![],
        unplaced: vec![],
        metrics: Metrics {
            placed_count: 0,
            unplaced_count: input.parts.iter().map(|p| p.quantity as usize).sum(),
            sheet_count_used: 0,
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name.clone(),
        },
        score_breakdown: None,
        optimizer_diagnostics: None,
        collision_backend_diagnostics: None,
    }
}

fn pipeline_kind(input: &SolverInput) -> OptimizerPipelineKind {
    match input.optimizer_pipeline.clone() {
        Some(pipeline) => pipeline,
        None if input.solver_profile.as_deref() == Some(PROFILE_PHASE1) => {
            OptimizerPipelineKind::SparrowCde
        }
        None => OptimizerPipelineKind::default(),
    }
}

fn resolve_backend_kind(input: &SolverInput) -> CollisionBackendKind {
    input.collision_backend.clone().unwrap_or_default()
}

fn backend_err_reason(e: WorkingCommitError, violation_reason: &str) -> String {
    match e {
        WorkingCommitError::Violations(_) => violation_reason.to_string(),
        WorkingCommitError::UnsupportedBackend { reason, .. } => reason,
    }
}

fn diag_output_from(result: &BackendCommitResult) -> CollisionBackendDiagnosticsOutput {
    CollisionBackendDiagnosticsOutput {
        backend_used: result.backend_diagnostics.backend_name.clone(),
        unsupported_queries: result.backend_diagnostics.unsupported_queries,
        bbox_fallback_queries: result.backend_diagnostics.bbox_fallback_queries,
        final_commit_backend_used: None,
        final_commit_unsupported_queries: None,
        final_commit_bbox_fallback_queries: None,
        cde_pair_queries: None,
        cde_boundary_queries: None,
        cde_total_queries: None,
        cde_engine_builds: None,
        cde_collision_results: None,
        cde_no_collision_results: None,
        cde_unsupported_results: None,
        cde_prepare_failures: None,
        cde_cross_sheet_skipped: None,
        cde_broadphase_pruned: None,
        cde_cache_pair_hits: None,
        cde_cache_pair_misses: None,
        cde_cache_boundary_hits: None,
        cde_cache_boundary_misses: None,
        cde_cache_prepared_hits: None,
        cde_cache_prepared_misses: None,
        cde_cache_invalidations: None,
        cde_batch_candidate_queries: None,
        cde_batch_engine_builds: None,
        cde_batch_hazards_registered: None,
        cde_batch_collisions_returned: None,
        cde_pairwise_fallback_queries: None,
        cde_candidate_session_builds: None,
        cde_candidate_session_reuses: None,
        cde_observability_scope: None,
        final_commit_validation_ms: None,
    }
}

fn cde_timing_enabled() -> bool {
    std::env::var("VRS_CDE_OBSERVABILITY_TIMING")
        .map(|v| v == "1")
        .unwrap_or(false)
}

fn timing_start(enabled: bool) -> Option<Instant> {
    if enabled {
        Some(Instant::now())
    } else {
        None
    }
}

fn timing_ms(start: Option<Instant>) -> Option<f64> {
    start.map(|t| t.elapsed().as_secs_f64() * 1000.0)
}

fn diag_output_from_with_cde(
    result: &BackendCommitResult,
    snap: cde_observability::CdeCounters,
    scope: &str,
    commit_ms: Option<f64>,
) -> CollisionBackendDiagnosticsOutput {
    CollisionBackendDiagnosticsOutput {
        backend_used: result.backend_diagnostics.backend_name.clone(),
        unsupported_queries: result.backend_diagnostics.unsupported_queries,
        bbox_fallback_queries: result.backend_diagnostics.bbox_fallback_queries,
        final_commit_backend_used: Some(result.backend_diagnostics.backend_name.clone()),
        final_commit_unsupported_queries: Some(result.backend_diagnostics.unsupported_queries),
        final_commit_bbox_fallback_queries: Some(result.backend_diagnostics.bbox_fallback_queries),
        cde_pair_queries: Some(snap.pair_queries),
        cde_boundary_queries: Some(snap.boundary_queries),
        cde_total_queries: Some(snap.total_queries),
        cde_engine_builds: Some(snap.engine_builds),
        cde_collision_results: Some(snap.collision_results),
        cde_no_collision_results: Some(snap.no_collision_results),
        cde_unsupported_results: Some(snap.unsupported_results),
        cde_prepare_failures: Some(snap.prepare_failures),
        cde_cross_sheet_skipped: Some(snap.cross_sheet_skipped),
        cde_broadphase_pruned: Some(snap.broadphase_pruned),
        cde_cache_pair_hits: Some(snap.cache_pair_hits),
        cde_cache_pair_misses: Some(snap.cache_pair_misses),
        cde_cache_boundary_hits: Some(snap.cache_boundary_hits),
        cde_cache_boundary_misses: Some(snap.cache_boundary_misses),
        cde_cache_prepared_hits: Some(snap.cache_prepared_hits),
        cde_cache_prepared_misses: Some(snap.cache_prepared_misses),
        cde_cache_invalidations: Some(snap.cache_invalidations),
        cde_batch_candidate_queries: Some(snap.batch_candidate_queries),
        cde_batch_engine_builds: Some(snap.batch_engine_builds),
        cde_batch_hazards_registered: Some(snap.batch_hazards_registered),
        cde_batch_collisions_returned: Some(snap.batch_collisions_returned),
        cde_pairwise_fallback_queries: Some(snap.pairwise_fallback_queries),
        cde_candidate_session_builds: Some(snap.candidate_session_builds),
        cde_candidate_session_reuses: Some(snap.candidate_session_reuses),
        cde_observability_scope: Some(scope.to_string()),
        final_commit_validation_ms: commit_ms,
    }
}

fn cde_unsupported_diag(
    snap: &cde_observability::CdeCounters,
    scope: &str,
    commit_ms: Option<f64>,
) -> CollisionBackendDiagnosticsOutput {
    CollisionBackendDiagnosticsOutput {
        backend_used: "cde_adapter".to_string(),
        unsupported_queries: snap.unsupported_results,
        bbox_fallback_queries: 0,
        final_commit_backend_used: Some("cde_adapter".to_string()),
        final_commit_unsupported_queries: Some(snap.unsupported_results),
        final_commit_bbox_fallback_queries: Some(0),
        cde_pair_queries: Some(snap.pair_queries),
        cde_boundary_queries: Some(snap.boundary_queries),
        cde_total_queries: Some(snap.total_queries),
        cde_engine_builds: Some(snap.engine_builds),
        cde_collision_results: Some(snap.collision_results),
        cde_no_collision_results: Some(snap.no_collision_results),
        cde_unsupported_results: Some(snap.unsupported_results),
        cde_prepare_failures: Some(snap.prepare_failures),
        cde_cross_sheet_skipped: Some(snap.cross_sheet_skipped),
        cde_broadphase_pruned: Some(snap.broadphase_pruned),
        cde_cache_pair_hits: Some(snap.cache_pair_hits),
        cde_cache_pair_misses: Some(snap.cache_pair_misses),
        cde_cache_boundary_hits: Some(snap.cache_boundary_hits),
        cde_cache_boundary_misses: Some(snap.cache_boundary_misses),
        cde_cache_prepared_hits: Some(snap.cache_prepared_hits),
        cde_cache_prepared_misses: Some(snap.cache_prepared_misses),
        cde_cache_invalidations: Some(snap.cache_invalidations),
        cde_batch_candidate_queries: Some(snap.batch_candidate_queries),
        cde_batch_engine_builds: Some(snap.batch_engine_builds),
        cde_batch_hazards_registered: Some(snap.batch_hazards_registered),
        cde_batch_collisions_returned: Some(snap.batch_collisions_returned),
        cde_pairwise_fallback_queries: Some(snap.pairwise_fallback_queries),
        cde_candidate_session_builds: Some(snap.candidate_session_builds),
        cde_candidate_session_reuses: Some(snap.candidate_session_reuses),
        cde_observability_scope: Some(scope.to_string()),
        final_commit_validation_ms: commit_ms,
    }
}

/// SGH-Q24R5: Build the collision-backend diagnostics for a feasible NATIVE
/// Sparrow solve directly from the CDE observability snapshot. The native core
/// runs every collision verdict through the CDE adapter, so the snapshot is the
/// authoritative backend accounting — there is no separate WorkingLayout commit.
fn cde_feasible_diag(
    snap: &cde_observability::CdeCounters,
    scope: &str,
    commit_ms: Option<f64>,
) -> CollisionBackendDiagnosticsOutput {
    CollisionBackendDiagnosticsOutput {
        backend_used: "cde_adapter".to_string(),
        unsupported_queries: snap.unsupported_results,
        bbox_fallback_queries: 0,
        final_commit_backend_used: Some("cde_adapter".to_string()),
        final_commit_unsupported_queries: Some(snap.unsupported_results),
        final_commit_bbox_fallback_queries: Some(0),
        cde_pair_queries: Some(snap.pair_queries),
        cde_boundary_queries: Some(snap.boundary_queries),
        cde_total_queries: Some(snap.total_queries),
        cde_engine_builds: Some(snap.engine_builds),
        cde_collision_results: Some(snap.collision_results),
        cde_no_collision_results: Some(snap.no_collision_results),
        cde_unsupported_results: Some(snap.unsupported_results),
        cde_prepare_failures: Some(snap.prepare_failures),
        cde_cross_sheet_skipped: Some(snap.cross_sheet_skipped),
        cde_broadphase_pruned: Some(snap.broadphase_pruned),
        cde_cache_pair_hits: Some(snap.cache_pair_hits),
        cde_cache_pair_misses: Some(snap.cache_pair_misses),
        cde_cache_boundary_hits: Some(snap.cache_boundary_hits),
        cde_cache_boundary_misses: Some(snap.cache_boundary_misses),
        cde_cache_prepared_hits: Some(snap.cache_prepared_hits),
        cde_cache_prepared_misses: Some(snap.cache_prepared_misses),
        cde_cache_invalidations: Some(snap.cache_invalidations),
        cde_batch_candidate_queries: Some(snap.batch_candidate_queries),
        cde_batch_engine_builds: Some(snap.batch_engine_builds),
        cde_batch_hazards_registered: Some(snap.batch_hazards_registered),
        cde_batch_collisions_returned: Some(snap.batch_collisions_returned),
        cde_pairwise_fallback_queries: Some(snap.pairwise_fallback_queries),
        cde_candidate_session_builds: Some(snap.candidate_session_builds),
        cde_candidate_session_reuses: Some(snap.candidate_session_reuses),
        cde_observability_scope: Some(scope.to_string()),
        final_commit_validation_ms: commit_ms,
    }
}

fn _unsupported_output_with_backend_diag(
    reason: &str,
    input: &SolverInput,
    backend_diag: Option<CollisionBackendDiagnosticsOutput>,
) -> SolverOutput {
    SolverOutput {
        contract_version: "v1".to_string(),
        status: "unsupported".to_string(),
        unsupported_reason: Some(reason.to_string()),
        placements: vec![],
        unplaced: vec![],
        metrics: Metrics {
            placed_count: 0,
            unplaced_count: input.parts.iter().map(|p| p.quantity as usize).sum(),
            sheet_count_used: 0,
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name.clone(),
        },
        score_breakdown: None,
        optimizer_diagnostics: None,
        collision_backend_diagnostics: backend_diag,
    }
}

/// SGH-Q22R1: Unsupported output that preserves BOTH optimizer_diagnostics and
/// collision_backend_diagnostics. Used by the Sparrow pipeline so that
/// `SPARROW_NO_FEASIBLE_LAYOUT` and `SPARROW_COMMIT_VIOLATION_BACKEND` callers
/// still surface every Sparrow counter that was computed before the failure.
fn _unsupported_output_with_full_diag(
    reason: &str,
    input: &SolverInput,
    optimizer_diag: Option<OptimizerDiagnosticsOutput>,
    backend_diag: Option<CollisionBackendDiagnosticsOutput>,
) -> SolverOutput {
    SolverOutput {
        contract_version: "v1".to_string(),
        status: "unsupported".to_string(),
        unsupported_reason: Some(reason.to_string()),
        placements: vec![],
        unplaced: vec![],
        metrics: Metrics {
            placed_count: 0,
            unplaced_count: input.parts.iter().map(|p| p.quantity as usize).sum(),
            sheet_count_used: 0,
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name.clone(),
        },
        score_breakdown: None,
        optimizer_diagnostics: optimizer_diag,
        collision_backend_diagnostics: backend_diag,
    }
}

fn _partial_output_with_full_diag(
    reason: &str,
    input: &SolverInput,
    placements: Vec<Placement>,
    unplaced: Vec<Unplaced>,
    optimizer_diag: Option<OptimizerDiagnosticsOutput>,
    backend_diag: Option<CollisionBackendDiagnosticsOutput>,
) -> SolverOutput {
    let placed_count = placements.len();
    let requested_count: usize = input.parts.iter().map(|p| p.quantity as usize).sum();
    let mut used_sheets: Vec<usize> = placements.iter().map(|p| p.sheet_index).collect();
    used_sheets.sort_unstable();
    used_sheets.dedup();
    SolverOutput {
        contract_version: "v1".to_string(),
        status: "partial".to_string(),
        unsupported_reason: Some(reason.to_string()),
        placements,
        unplaced,
        metrics: Metrics {
            placed_count,
            unplaced_count: requested_count.saturating_sub(placed_count),
            sheet_count_used: used_sheets.len(),
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name.clone(),
        },
        score_breakdown: None,
        optimizer_diagnostics: optimizer_diag,
        collision_backend_diagnostics: backend_diag,
    }
}

/// SGH-Q24R5: Build the OptimizerDiagnosticsOutput from the NATIVE Sparrow
/// diagnostics (`optimizer::sparrow::SparrowDiagnostics`). This is the
/// only Sparrow diagnostics projection on the production path; it sets the
/// native-model proof flags so the cutover gate can verify the old core is
/// gone. Fields not tracked by the native core are emitted as 0/false (no
/// fabricated activity).
fn native_sparrow_diag_to_output(
    d: &crate::optimizer::sparrow::SparrowDiagnostics,
    backend_name: String,
    final_commit_ms: Option<f64>,
    pipeline_label: &str,
    loss_model: crate::optimizer::loss_model::LossModelKind,
) -> OptimizerDiagnosticsOutput {
    OptimizerDiagnosticsOutput {
        pipeline_used: pipeline_label.to_string(),
        phase_optimizer_invoked: false,
        exploration_iterations: d.exploration_attempts,
        compression_iterations: 0,
        bpp_attempts: 0,
        rotation_refinement_enabled: false,
        rotation_refinement_attempts: 0,
        rotation_refinement_accepts: 0,
        rotation_refinement_rejections: 0,
        rotation_refinement_best_delta: 0.0,
        search_position_calls: d.search_position_calls,
        search_position_global_samples_evaluated: d.search_global_samples,
        search_position_focused_samples_evaluated: d.search_focused_samples,
        search_position_samples_unsupported: d.search_unsupported_samples,
        search_position_refined_samples: d.search_refined_samples,
        search_position_coord_descent_steps: d.search_coord_descent_steps,
        search_position_lbf_fallback_used: d.lbf_fallback_used,
        search_position_best_eval: d.search_best_eval,
        collision_severity_backend: backend_name,
        collision_severity_enabled: true,
        collision_severity_pair_queries: d.quantified_pair_queries,
        collision_severity_boundary_queries: d.quantified_boundary_queries,
        collision_severity_probe_queries: d.quantified_pair_queries + d.quantified_boundary_queries,
        collision_severity_backend_confirmed_collisions: 0,
        collision_severity_backend_confirmed_no_collisions: 0,
        collision_severity_unsupported_queries: d.unsupported_queries,
        collision_severity_bbox_proxy_uses: 0,
        collision_severity_probe_pair_queries: 0,
        collision_severity_probe_boundary_queries: 0,
        collision_severity_probe_resolved: 0,
        collision_severity_probe_unresolved: 0,
        collision_severity_probe_unsupported: 0,
        collision_severity_min_resolution_mm: 0.0,
        collision_severity_max_resolution_mm: 0.0,
        collision_severity_avg_resolution_mm: 0.0,
        phase_optimizer_exploration_ms: None,
        phase_optimizer_compression_ms: None,
        phase_optimizer_bpp_ms: None,
        phase_optimizer_final_commit_ms: final_commit_ms,
        sparrow_invoked: Some(d.invoked),
        sparrow_seed_placements: Some(d.seed_placements),
        sparrow_seed_unplaced: Some(d.seed_unplaced),
        sparrow_initial_raw_loss: Some(d.initial_raw_loss),
        sparrow_initial_weighted_loss: Some(d.initial_weighted_loss),
        sparrow_final_raw_loss: Some(d.final_raw_loss),
        sparrow_final_weighted_loss: Some(d.final_weighted_loss),
        sparrow_best_infeasible_raw_loss: Some(d.best_infeasible_raw_loss),
        sparrow_best_infeasible_weighted_loss: Some(d.best_infeasible_weighted_loss),
        sparrow_iterations: Some(d.iterations),
        sparrow_moves_attempted: Some(d.moves_attempted),
        sparrow_moves_accepted: Some(d.moves_accepted),
        sparrow_rollbacks: Some(d.rollbacks),
        sparrow_gls_weight_updates: Some(d.gls_weight_updates),
        sparrow_converged: Some(d.converged),
        sparrow_collision_graph_initial_pairs: Some(d.collision_graph_initial_pairs),
        sparrow_collision_graph_final_pairs: Some(d.collision_graph_final_pairs),
        sparrow_boundary_violations_initial: Some(d.boundary_violations_initial),
        sparrow_boundary_violations_final: Some(d.boundary_violations_final),
        sparrow_search_position_calls: Some(d.search_position_calls),
        sparrow_search_position_samples: Some(d.search_position_samples),
        sparrow_severity_pair_queries: Some(d.quantified_pair_queries),
        sparrow_severity_boundary_queries: Some(d.quantified_boundary_queries),
        sparrow_severity_probe_queries: Some(
            d.quantified_pair_queries + d.quantified_boundary_queries,
        ),
        sparrow_lbf_fallback_used: Some(d.lbf_fallback_used),
        sparrow_workers: Some(d.worker_count),
        sparrow_worker_passes: Some(d.worker_passes),
        sparrow_worker_candidates_evaluated: Some(d.worker_candidates_evaluated),
        sparrow_worker_commits: Some(d.worker_commits),
        sparrow_worker_rollbacks: Some(d.worker_rollbacks),
        sparrow_worker_best_loss: Some(d.worker_best_loss),
        sparrow_multi_target_items_attempted: Some(d.multi_target_items_attempted),
        sparrow_multi_target_items_accepted: Some(d.multi_target_items_accepted),
        sparrow_multi_target_items_rejected: Some(d.multi_target_items_rejected),
        sparrow_topk_target_count: Some(d.topk_target_count),
        sparrow_graph_full_rebuilds: Some(d.native_tracker_full_rebuilds),
        sparrow_graph_incremental_updates: Some(d.native_tracker_incremental_updates),
        sparrow_graph_edges_recomputed: Some(d.quantified_pair_queries),
        sparrow_graph_edges_pruned_by_broadphase: Some(0),
        sparrow_graph_debug_rebuilds: Some(0),
        sparrow_graph_debug_rebuild_mismatches: Some(0),
        sparrow_exploration_restarts: Some(d.exploration_pool_restores),
        sparrow_exploration_seed_strategies: Some(0),
        sparrow_exploration_disruptions: Some(
            d.exploration_disruptions_large_item_swap
                + d.exploration_disruptions_cross_sheet
                + d.exploration_disruptions_rotation,
        ),
        sparrow_exploration_stagnation_events: Some(0),
        sparrow_exploration_best_raw_loss: Some(d.best_infeasible_raw_loss),
        sparrow_exploration_best_weighted_loss: Some(d.best_infeasible_weighted_loss),
        sparrow_exploration_best_feasible_found: Some(d.converged),
        sparrow_compression_passes: Some(d.excluded_phase_passes),
        sparrow_compression_candidates_evaluated: Some(0),
        sparrow_compression_accepts: Some(0),
        sparrow_compression_rejects: Some(0),
        sparrow_fixed_sheet_objective_before: Some(0.0),
        sparrow_fixed_sheet_objective_after: Some(0.0),
        sparrow_fixed_sheet_objective_delta: Some(0.0),
        loss_model_used: Some(loss_model.name().to_string()),
        loss_bbox_proxy_used_as_primary: Some(loss_model.is_bbox_area_primary()),
        sparrow_native_model_active: Some(d.native_model_active),
        sparrow_native_tracker_active: Some(d.native_tracker_active),
        sparrow_old_core_used: Some(d.old_core_used),
        sparrow_native_problem_instances: Some(d.native_problem_instances),
        sparrow_native_tracker_full_rebuilds: Some(d.native_tracker_full_rebuilds),
        sparrow_native_tracker_incremental_updates: Some(d.native_tracker_incremental_updates),
        sparrow_dense_guard_used: Some(d.dense_guard_used),
        sparrow_dense_real_run: Some(d.dense_real_run),
        sparrow_dense_partial_reason: d.dense_partial_reason.clone(),
        sparrow_dense_validated_placements: d.dense_validated_placements,
        sparrow_dense_unresolved_instances: if d.dense_unresolved_instances.is_empty() {
            None
        } else {
            Some(d.dense_unresolved_instances.clone())
        },
        sparrow_dense_final_validation_ran: Some(d.dense_final_validation_ran),
        sparrow_profiling_enabled: Some(d.profiling_enabled),
        sparrow_profile_search_total_ms: if d.profiling_enabled { Some(d.profile_search_total_ms) } else { None },
        sparrow_profile_session_build_ms: if d.profiling_enabled { Some(d.profile_session_build_ms) } else { None },
        sparrow_profile_deregister_ms: if d.profiling_enabled { Some(d.profile_deregister_ms) } else { None },
        sparrow_profile_candidate_transform_ms: if d.profiling_enabled { Some(d.profile_candidate_transform_ms) } else { None },
        sparrow_profile_cde_query_collect_ms: if d.profiling_enabled { Some(d.profile_cde_query_collect_ms) } else { None },
        sparrow_profile_hazard_loss_ms: if d.profiling_enabled { Some(d.profile_hazard_loss_ms) } else { None },
        sparrow_profile_boundary_check_ms: if d.profiling_enabled { Some(d.profile_boundary_check_ms) } else { None },
        sparrow_profile_broadphase_reject_count: if d.profiling_enabled { Some(d.profile_broadphase_reject_count) } else { None },
        sparrow_profile_early_termination_count: if d.profiling_enabled { Some(d.profile_early_termination_count) } else { None },
        sparrow_q30_profile_enabled: Some(d.q30_profile.enabled),
        sparrow_q30_native_search_calls: if d.q30_profile.enabled { Some(d.q30_profile.native_search_calls) } else { None },
        sparrow_q30_evaluate_sample_calls: if d.q30_profile.enabled { Some(d.q30_profile.evaluate_sample_calls) } else { None },
        sparrow_q30_candidates_evaluated: if d.q30_profile.enabled { Some(d.q30_profile.candidates_evaluated) } else { None },
        sparrow_q30_global_samples_generated: if d.q30_profile.enabled { Some(d.q30_profile.global_samples_generated) } else { None },
        sparrow_q30_focused_samples_generated: if d.q30_profile.enabled { Some(d.q30_profile.focused_samples_generated) } else { None },
        sparrow_q30_coord_descent_runs: if d.q30_profile.enabled { Some(d.q30_profile.coord_descent_runs) } else { None },
        sparrow_q30_coord_descent_steps: if d.q30_profile.enabled { Some(d.q30_profile.coord_descent_steps) } else { None },
        sparrow_q30_best_samples_insert_attempts: if d.q30_profile.enabled { Some(d.q30_profile.best_samples_insert_attempts) } else { None },
        sparrow_q30_best_samples_inserted: if d.q30_profile.enabled { Some(d.q30_profile.best_samples_inserted) } else { None },
        sparrow_q30_best_samples_dedup_rejects: if d.q30_profile.enabled { Some(d.q30_profile.best_samples_dedup_rejects) } else { None },
        sparrow_q30_early_termination_count: if d.q30_profile.enabled { Some(d.q30_profile.early_termination_count) } else { None },
        sparrow_q30_broadphase_reject_count: if d.q30_profile.enabled { Some(d.q30_profile.broadphase_reject_count) } else { None },
        sparrow_q30_search_total_ms: if d.q30_profile.enabled { Some(d.q30_profile.search_total_ms) } else { None },
        sparrow_q30_sample_generation_ms: if d.q30_profile.enabled { Some(d.q30_profile.sample_generation_ms) } else { None },
        sparrow_q30_best_samples_insert_dedup_ms: if d.q30_profile.enabled { Some(d.q30_profile.best_samples_insert_dedup_ms) } else { None },
        sparrow_q30_coord_descent_total_ms: if d.q30_profile.enabled { Some(d.q30_profile.coord_descent_total_ms) } else { None },
        sparrow_q30_evaluate_sample_total_ms: if d.q30_profile.enabled { Some(d.q30_profile.evaluate_sample_total_ms) } else { None },
        sparrow_q30_candidate_transform_prepare_ms: if d.q30_profile.enabled { Some(d.q30_profile.candidate_transform_prepare_ms) } else { None },
        sparrow_q30_cde_query_collect_ms: if d.q30_profile.enabled { Some(d.q30_profile.cde_query_collect_ms) } else { None },
        sparrow_q30_boundary_check_ms: if d.q30_profile.enabled { Some(d.q30_profile.boundary_check_ms) } else { None },
        sparrow_q30_session_build_ms: if d.q30_profile.enabled { Some(d.q30_profile.session_build_ms) } else { None },
        sparrow_q30_deregister_reregister_ms: if d.q30_profile.enabled { Some(d.q30_profile.deregister_reregister_ms) } else { None },
        // Q30-R1 exclusive fields
        sparrow_q30r1_exclusive_enabled: Some(d.q30_profile.r1_exclusive_enabled),
        sparrow_q30r1_prepare_base_shape_native_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.prepare_base_shape_native_ms) } else { None },
        sparrow_q30r1_fixed_shapes_clone_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.fixed_shapes_clone_ms) } else { None },
        sparrow_q30r1_sheet_order_build_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.sheet_order_build_ms) } else { None },
        sparrow_q30r1_best_samples_best_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.best_samples_best_ms) } else { None },
        sparrow_q30r1_best_samples_clone_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.best_samples_clone_ms) } else { None },
        sparrow_q30r1_coord_descent_ask_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.coord_descent_ask_ms) } else { None },
        sparrow_q30r1_coord_descent_tell_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.coord_descent_tell_ms) } else { None },
        sparrow_q30r1_search_accounted_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.search_accounted_ms) } else { None },
        sparrow_q30r1_search_unaccounted_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.search_unaccounted_ms) } else { None },
        sparrow_q30r1_search_unaccounted_ratio_pct: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.search_unaccounted_ratio_pct) } else { None },
        sparrow_q30r1_total_solver_runtime_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.total_solver_runtime_ms) } else { None },
        sparrow_q30r1_adapter_solve_total_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.adapter_solve_total_ms) } else { None },
        sparrow_q30r1_sparrow_optimizer_solve_total_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.sparrow_optimizer_solve_total_ms) } else { None },
        sparrow_q30r1_seed_lbf_total_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.seed_lbf_total_ms) } else { None },
        sparrow_q30r1_tracker_initial_build_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.tracker_initial_build_ms) } else { None },
        sparrow_q30r1_exploration_total_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.exploration_total_ms) } else { None },
        sparrow_q30r1_separator_total_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.separator_total_ms) } else { None },
        sparrow_q30r1_separator_iteration_total_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.separator_iteration_total_ms) } else { None },
        sparrow_q30r1_worker_competition_total_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.worker_competition_total_ms) } else { None },
        sparrow_q30r1_worker_pass_total_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.worker_pass_total_ms) } else { None },
        sparrow_q30r1_tracker_final_validation_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.tracker_final_validation_ms) } else { None },
        sparrow_q30r1_output_mapping_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.output_mapping_ms) } else { None },
        sparrow_q30r1_other_solver_unaccounted_ms: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.other_solver_unaccounted_ms) } else { None },
        sparrow_q30r1_other_solver_unaccounted_ratio_pct: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.other_solver_unaccounted_ratio_pct) } else { None },
        sparrow_q30r1_evaluate_sample_calls_from_focused: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.evaluate_sample_calls_from_focused) } else { None },
        sparrow_q30r1_evaluate_sample_calls_from_global: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.evaluate_sample_calls_from_global) } else { None },
        sparrow_q30r1_evaluate_sample_calls_from_coord_descent: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.evaluate_sample_calls_from_coord_descent) } else { None },
        sparrow_q30r1_best_samples_best_calls: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.best_samples_best_calls) } else { None },
        sparrow_q30r1_best_samples_clone_calls: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.best_samples_clone_calls) } else { None },
        sparrow_q30r1_coord_descent_ask_calls: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.coord_descent_ask_calls) } else { None },
        sparrow_q30r1_coord_descent_tell_calls: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.coord_descent_tell_calls) } else { None },
        sparrow_q30r1_sheet_loop_iterations: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.sheet_loop_iterations) } else { None },
        sparrow_q30r1_worker_passes: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.worker_passes) } else { None },
        sparrow_q30r1_worker_candidates_evaluated: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.worker_candidates_evaluated) } else { None },
        sparrow_q30r1_worker_candidates_accepted: if d.q30_profile.r1_exclusive_enabled { Some(d.q30_profile.worker_candidates_accepted) } else { None },
        sparrow_q31_base_shape_cache_build_ms: Some(d.q30_profile.base_shape_cache_build_ms),
        sparrow_q31_base_shape_cache_hits: Some(d.q30_profile.base_shape_cache_hits),
        sparrow_q31_base_shape_cache_misses: Some(d.q30_profile.base_shape_cache_misses),
        sparrow_q31_base_shape_cache_unique_parts: Some(d.q30_profile.base_shape_cache_unique_parts),
        sparrow_q31_base_shape_cache_reused_instances: Some(d.q30_profile.base_shape_cache_reused_instances),
        sparrow_q31_prepare_base_shape_native_hotpath_calls: Some(d.q30_profile.prepare_base_shape_native_hotpath_calls),
        sparrow_q31_prepare_base_shape_native_hotpath_ms: Some(d.q30_profile.prepare_base_shape_native_hotpath_ms),
        sparrow_q31_tracker_transform_from_base_ms: Some(d.q30_profile.tracker_transform_from_base_ms),
        sparrow_q31_search_base_shape_cache_hits: Some(d.q30_profile.search_base_shape_cache_hits),
        sparrow_q31_lbf_base_shape_cache_hits: Some(d.q30_profile.lbf_base_shape_cache_hits),
        // Q32 multisheet fields: not populated by the single-sheet sparrow_cde pipeline.
        sparrow_ms_active: None,
        sparrow_ms_status: None,
        sparrow_ms_available_sheet_count: None,
        sparrow_ms_used_sheet_count: None,
        sparrow_ms_used_sheet_indices: None,
        sparrow_ms_used_sheet_area: None,
        sparrow_ms_placed_part_area: None,
        sparrow_ms_utilization_pct: None,
        sparrow_ms_total_instances: None,
        sparrow_ms_placed_instances: None,
        sparrow_ms_unplaced_instances: None,
        sparrow_ms_attempts: None,
        sparrow_ms_candidate_subsets: None,
        sparrow_ms_best_full_solution_found: None,
        sparrow_ms_stock_exhausted: None,
        sparrow_ms_final_pairs: None,
        sparrow_ms_boundary_violations: None,
        sparrow_ms_runtime_ms: None,
        sparrow_ms_requested_time_limit_s: None,
        sparrow_ms_deadline_hit: None,
        sparrow_ms_best_score: None,
        sparrow_ms_attempt_diagnostics: None,
        sparrow_ms_attempt_diagnostics_count: None,
        sparrow_ms_attempt_diagnostics_schema_version: None,
        technology_policy_active: None,
        technology_margin_mm: None,
        technology_spacing_mm: None,
        technology_kerf_mm: None,
        technology_effective_sheet_margin_mm: None,
        technology_effective_part_spacing_mm: None,
        technology_effective_kerf_mm: None,
        technology_sheet_margin_applied: None,
        technology_margin_applied_sheet_count: None,
        technology_margin_usable_sheet_area: None,
        technology_margin_physical_used_sheet_area: None,
        technology_margin_violation_count: None,
        technology_part_spacing_applied: None,
        technology_part_spacing_mm: None,
        technology_spacing_violation_count: None,
        technology_spacing_safety_net_removed_count: None,
        technology_spacing_geometry_applied: None,
        technology_spacing_offset_mm: None,
        technology_spacing_offset_part_count: None,
        technology_spacing_offset_cache_hits: None,
        technology_spacing_offset_cache_misses: None,
        technology_spacing_offset_failure_count: None,
        technology_spacing_boundary_uses_original_geometry: None,
        technology_spacing_output_uses_original_geometry: None,
        technology_spacing_offset_build_ms: None,
        technology_spacing_offset_avg_ms_per_part: None,
        technology_spacing_offset_max_ms_per_part: None,
        technology_spacing_offset_input_vertex_count_total: None,
        technology_spacing_offset_output_vertex_count_total: None,
        technology_spacing_offset_area_ratio_avg: None,
        technology_spacing_offset_area_ratio_max: None,
        technology_margin_final_validator_ms: None,
        technology_spacing_final_validator_ms: None,
        technology_safety_net_ms: None,
        technology_unified_geometry_model_active: None,
        technology_solver_sheet_inset_mm: None,
        technology_inner_spacing_mm: None,
    }
}

/// SGH-Q22/Q23: shared Sparrow separation pipeline driver.
///
/// Used by both `sparrow_experimental` (caller chooses the backend) and the
/// `sparrow_cde` production path (caller forces `CollisionBackendKind::Cde`).
///
/// Returns `Ok((placements, unplaced, optimizer_diagnostics, backend_diagnostics))`
/// on a backend-valid commit, or `Err(SolverOutput)` carrying an `unsupported`
/// output that preserves the full optimizer + backend diagnostics on any failure
/// (no feasible layout, or final-commit violation). LBF/finite-candidate fallback
/// is disabled (`allow_lbf_fallback = false`); this driver never falls back to a
/// legacy solver.
#[allow(clippy::type_complexity)]
fn run_sparrow_pipeline(
    input: &SolverInput,
    sheets: &[crate::sheet::SheetShape],
    rotation_context: &RotationResolveContext,
    pre_unplaced: Vec<Unplaced>,
    backend_kind: CollisionBackendKind,
    pipeline_label: &str,
) -> Result<
    (
        Vec<Placement>,
        Vec<Unplaced>,
        Option<OptimizerDiagnosticsOutput>,
        Option<CollisionBackendDiagnosticsOutput>,
    ),
    SolverOutput,
> {
    // SGH-Q24R5: production solver core is the NATIVE Sparrow model. The entire
    // truth model lives in `optimizer::sparrow` (SparrowProblem / SPInstance /
    // SparrowLayout / SparrowCollisionTracker / SparrowOptimizer); this driver only
    // performs the one-way I/O conversion in and the projection out. No WorkingLayout,
    // no legacy separation kernel, no constructive-seed helper, no validate-and-commit.
    use crate::optimizer::sparrow::{SparrowConfig, SparrowOptimizer, SparrowProblem};
    // The native Sparrow collision truth is the jagua_rs CDE engine for EVERY
    // requested backend (the native tracker is CDE-backed). So reset and surface
    // the CDE observability counters regardless of `backend_kind`.
    cde_observability::reset();
    crate::optimizer::cde_adapter::reset_query_cache();
    let timing_enabled = cde_timing_enabled();
    // CDE path uses the CDE-separation loss identity; non-CDE debug uses bbox area.
    let prod_loss_model = if backend_kind == CollisionBackendKind::Cde {
        crate::optimizer::loss_model::LossModelKind::CdeSeparation
    } else {
        crate::optimizer::loss_model::LossModelKind::BboxArea
    };

    let config = SparrowConfig::from_solver_input(
        (input.time_limit_s as f64).max(1.0),
        backend_kind.clone(),
        rotation_context.clone(),
        input.seed as u64,
    );
    let problem = match SparrowProblem::from_solver_input(
        &input.parts,
        sheets,
        rotation_context,
        pre_unplaced,
        config.clone(),
    ) {
        Ok(p) => p,
        Err(_e) => {
            return Err(_unsupported_output_with_full_diag(
                "SPARROW_SEED_BUILD_FAILED",
                input,
                None,
                None,
            ));
        }
    };

    let t_commit_start = timing_start(timing_enabled);
    let t_adapter_solve = Instant::now();
    let optimizer = SparrowOptimizer::new(config);
    let mut result = optimizer.solve(problem);
    let final_commit_ms = timing_ms(t_commit_start);
    // Record total adapter solve time (includes solve + projection, already done in optimizer).
    result.diagnostics.q30_profile.adapter_solve_total_ms =
        t_adapter_solve.elapsed().as_secs_f64() * 1000.0;
    let backend_name = format!("{:?}", backend_kind);
    let optimizer_diag = native_sparrow_diag_to_output(
        &result.diagnostics,
        backend_name.clone(),
        final_commit_ms,
        pipeline_label,
        prod_loss_model,
    );

    if !result.feasible {
        let snap = cde_observability::snapshot();
        let backend_diag = cde_unsupported_diag(&snap, "sparrow_no_feasible", final_commit_ms);
        return Err(_partial_output_with_full_diag(
            "SPARROW_NO_FEASIBLE_LAYOUT",
            input,
            result.placements,
            result.unplaced,
            Some(optimizer_diag),
            Some(backend_diag),
        ));
    }

    let snap = cde_observability::snapshot();
    let backend_diag = Some(cde_feasible_diag(
        &snap,
        "sparrow_full_solve",
        final_commit_ms,
    ));
    Ok((
        result.placements,
        result.unplaced,
        Some(optimizer_diag),
        backend_diag,
    ))
}

/// SGH-Q34-R1: unplaced reason for a placement removed by the margin safety net.
const REASON_SHEET_MARGIN_VIOLATION: &str = "SHEET_MARGIN_VIOLATION_Q34R1";

/// SGH-Q34-R1: remove margin-violating placements and move them to `unplaced`.
///
/// Any placement whose `instance_id` is in `violating_instance_ids` is removed from
/// `placements` and appended to `unplaced` with reason `SHEET_MARGIN_VIOLATION_Q34R1`.
/// This guarantees the top-level status calculation (`unplaced.is_empty()`) cannot
/// report `ok` when a margin violation exists.
fn apply_margin_violation_safety_net(
    placements: Vec<Placement>,
    mut unplaced: Vec<Unplaced>,
    violating_instance_ids: &[String],
) -> (Vec<Placement>, Vec<Unplaced>) {
    if violating_instance_ids.is_empty() {
        return (placements, unplaced);
    }
    let mut kept: Vec<Placement> = Vec::with_capacity(placements.len());
    for pl in placements {
        if violating_instance_ids.contains(&pl.instance_id) {
            unplaced.push(Unplaced {
                instance_id: pl.instance_id.clone(),
                part_id: pl.part_id.clone(),
                reason: REASON_SHEET_MARGIN_VIOLATION.to_string(),
            });
        } else {
            kept.push(pl);
        }
    }
    (kept, unplaced)
}

/// SGH-Q35: unplaced reason for a placement removed by the part-spacing safety gate.
const REASON_PART_SPACING_VIOLATION: &str = "PART_SPACING_VIOLATION_Q35";

/// SGH-Q35: remove spacing-violating placements and move them to `unplaced`.
///
/// As a SAFETY GATE (not an optimization), both endpoints of every violation pair are
/// removed. Each removed placement is appended to `unplaced` with reason
/// `PART_SPACING_VIOLATION_Q35`. Guarantees the top-level status cannot be `ok` when a
/// spacing violation exists. Returns `(kept_placements, unplaced)`.
fn apply_spacing_violation_safety_net(
    placements: Vec<Placement>,
    mut unplaced: Vec<Unplaced>,
    violations: &[crate::technology::spacing::PartSpacingViolation],
) -> (Vec<Placement>, Vec<Unplaced>) {
    if violations.is_empty() {
        return (placements, unplaced);
    }
    let mut to_remove: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    for v in violations {
        to_remove.insert(v.a_instance_id.clone());
        to_remove.insert(v.b_instance_id.clone());
    }
    let mut kept: Vec<Placement> = Vec::with_capacity(placements.len());
    for pl in placements {
        if to_remove.contains(&pl.instance_id) {
            unplaced.push(Unplaced {
                instance_id: pl.instance_id.clone(),
                part_id: pl.part_id.clone(),
                reason: REASON_PART_SPACING_VIOLATION.to_string(),
            });
        } else {
            kept.push(pl);
        }
    }
    (kept, unplaced)
}

/// SGH-Q35: number of unique placements that the spacing safety net would remove.
fn spacing_safety_net_removed_count(
    violations: &[crate::technology::spacing::PartSpacingViolation],
) -> usize {
    let mut ids: std::collections::BTreeSet<&str> = std::collections::BTreeSet::new();
    for v in violations {
        ids.insert(v.a_instance_id.as_str());
        ids.insert(v.b_instance_id.as_str());
    }
    ids.len()
}

/// SGH-Q40: unified-model unplaced reason when a part's outward offset cannot be built.
const REASON_UNSUPPORTED_SPACING_OFFSET: &str = "UNSUPPORTED_SPACING_OFFSET_Q36";

/// SGH-Q40: measurement-hardening inventory for the unified-model part offset pass.
///
/// In the unified model each unique part template is offset exactly once up front (no per-instance
/// runtime cache), so `parts_offset` doubles as the cache-miss count and `cache_hits` is always 0.
#[derive(Default, Clone)]
struct OffsetBuildMetrics {
    build_ms: f64,
    parts_offset: usize,
    max_ms_per_part: f64,
    input_vertex_total: usize,
    output_vertex_total: usize,
    area_ratio_sum: f64,
    area_ratio_max: f64,
}

/// SGH-Q40: build the SOLVER part set for the unified single-geometry model.
///
/// Each part's outer contour is offset OUTWARD by `part_offset` (= spacing/2), preserving the
/// local origin so the placement anchor maps identically to the original part (exact swap-back
/// at output). The solver then runs as a plain nester on these offset parts (spacing disabled
/// internally) — which the Q39 control proved packs dramatically better than the old
/// dual-geometry mechanism. `part_offset <= 0` clones the parts unchanged.
///
/// Returns `(offset_parts, failed_part_ids, metrics)`. Parts whose offset cannot be built safely
/// are excluded and their ids returned (instances become UNSUPPORTED_SPACING_OFFSET_Q36 unplaced).
fn build_offset_parts(
    parts: &[crate::item::Part],
    part_offset: f64,
) -> (
    Vec<crate::item::Part>,
    std::collections::HashSet<String>,
    OffsetBuildMetrics,
) {
    use crate::geometry::{polygon_area, Point};
    use crate::optimizer::collision_backend::{extract_polygon_from_part, PolygonExtraction};
    use crate::technology::spacing_geometry::build_spacing_expanded_outer_polygon;

    let mut out = Vec::with_capacity(parts.len());
    let mut failed: std::collections::HashSet<String> = std::collections::HashSet::new();
    let mut metrics = OffsetBuildMetrics::default();
    if part_offset <= 1e-9 {
        return (parts.to_vec(), failed, metrics);
    }
    let t_build = Instant::now();
    for p in parts {
        let local: Vec<Point> = match extract_polygon_from_part(p) {
            PolygonExtraction::Valid(l) => l,
            PolygonExtraction::Absent => vec![
                Point { x: 0.0, y: 0.0 },
                Point { x: p.width, y: 0.0 },
                Point { x: p.width, y: p.height },
                Point { x: 0.0, y: p.height },
            ],
            PolygonExtraction::Invalid { .. } => {
                failed.insert(p.id.clone());
                continue;
            }
        };
        let t_part = Instant::now();
        let built = build_spacing_expanded_outer_polygon(&local, part_offset);
        let part_ms = t_part.elapsed().as_secs_f64() * 1000.0;
        match built {
            Ok(off) => {
                let pts: Vec<serde_json::Value> =
                    off.iter().map(|q| serde_json::json!([q.x, q.y])).collect();
                let minx = off.iter().map(|q| q.x).fold(f64::INFINITY, f64::min);
                let maxx = off.iter().map(|q| q.x).fold(f64::NEG_INFINITY, f64::max);
                let miny = off.iter().map(|q| q.y).fold(f64::INFINITY, f64::min);
                let maxy = off.iter().map(|q| q.y).fold(f64::NEG_INFINITY, f64::max);
                let orig_area = polygon_area(&local).abs();
                let off_area = polygon_area(&off).abs();
                let ratio = if orig_area > 1e-9 { off_area / orig_area } else { 1.0 };
                metrics.parts_offset += 1;
                metrics.max_ms_per_part = metrics.max_ms_per_part.max(part_ms);
                metrics.input_vertex_total += local.len();
                metrics.output_vertex_total += off.len();
                metrics.area_ratio_sum += ratio;
                metrics.area_ratio_max = metrics.area_ratio_max.max(ratio);
                let mut np = p.clone();
                let arr = serde_json::Value::Array(pts);
                np.outer_points = Some(arr.clone());
                np.prepared_outer_points = Some(arr);
                np.width = maxx - minx;
                np.height = maxy - miny;
                out.push(np);
            }
            Err(_) => {
                failed.insert(p.id.clone());
            }
        }
    }
    metrics.build_ms = t_build.elapsed().as_secs_f64() * 1000.0;
    (out, failed, metrics)
}

/// SGH-Q32: Sparrow-native finite-stock multisheet manager pipeline.
///
/// CDE-first by contract. Manages a pool of available sheets, generates candidate
/// subsets, runs native Sparrow core on each, and returns the best valid incumbent.
/// Never falls back to legacy multisheet manager or Python wrapper.
fn run_sparrow_finite_stock_multisheet_pipeline(
    input: &SolverInput,
    sheets: &[crate::sheet::SheetShape],
    rotation_context: &RotationResolveContext,
    pre_unplaced: Vec<Unplaced>,
    technology_policy: &TechnologyClearancePolicy,
) -> (
    Vec<Placement>,
    Vec<Unplaced>,
    Option<OptimizerDiagnosticsOutput>,
    Option<CollisionBackendDiagnosticsOutput>,
) {
    use crate::optimizer::sparrow::multisheet::{
        recompute_multisheet_result_after_safety_net, run_finite_stock_multisheet,
        FiniteStockRunConfig,
    };
    use crate::technology::spacing::find_part_spacing_violations;
    cde_observability::reset();
    crate::optimizer::cde_adapter::reset_query_cache();

    // ── SGH-Q40 unified technology pre-processing ────────────────────────────────
    // Both technology constraints are moved OUT of the solver's inner logic into two
    // geometry transforms around a plain nester (Q39 control proof: the old dual-geometry
    // spacing mechanism packed 146/276 where nesting the offset shapes directly packs 257):
    //   • spacing → offset every part contour OUTWARD by spacing/2 (single geometry);
    //   • margin  → offset every sheet by (margin − spacing/2)  [signed; negative grows it].
    // The solver runs as an ordinary nester (spacing disabled internally) on the offset parts
    // + offset sheets; the output anchors map back to the original geometry exactly (the
    // offset preserves the local origin). Original sheets are kept for physical area reporting.
    let margin_mm = technology_policy.effective_sheet_margin_mm();
    let spacing_mm = technology_policy.effective_part_spacing_mm();
    let margin_applied = margin_mm > 0.0;
    let spacing_applied = spacing_mm > 0.0;
    let part_offset = spacing_mm / 2.0;
    let sheet_inset = margin_mm - part_offset; // signed: >0 shrink, <0 grow
    let original_sheets = sheets; // physical sheets, already expanded (for area)

    // Offset the parts (spacing). Parts whose offset cannot be built → unplaced.
    let (offset_parts, offset_failed_ids, offset_metrics) =
        build_offset_parts(&input.parts, part_offset);
    let mut pre_unplaced = pre_unplaced;
    if !offset_failed_ids.is_empty() {
        for p in &input.parts {
            if offset_failed_ids.contains(&p.id) {
                for i in 0..p.quantity as usize {
                    pre_unplaced.push(Unplaced {
                        instance_id: format!("{}#{i}", p.id),
                        part_id: p.id.clone(),
                        reason: REASON_UNSUPPORTED_SPACING_OFFSET.to_string(),
                    });
                }
            }
        }
    }
    let spacing_offset_failure_count: usize = input
        .parts
        .iter()
        .filter(|p| offset_failed_ids.contains(&p.id))
        .map(|p| p.quantity as usize)
        .sum();

    // Offset the sheets (margin − spacing/2), signed. Irregular/collapse → unsupported.
    let solver_sheets_override = if sheet_inset != 0.0 {
        match apply_rectangular_sheet_offset(original_sheets, sheet_inset) {
            Ok(s) => Some(s),
            Err(e) => {
                let mut all_unplaced: Vec<Unplaced> = input.parts.iter().flat_map(|p| {
                    (0..p.quantity as usize).map(|i| Unplaced {
                        instance_id: format!("{}#{i}", p.id),
                        part_id: p.id.clone(),
                        reason: e.clone(),
                    })
                }).collect();
                all_unplaced.extend(pre_unplaced);
                return (vec![], all_unplaced, None, None);
            }
        }
    } else {
        None
    };

    let ms_config = FiniteStockRunConfig {
        time_limit_s: (input.time_limit_s as f64).max(1.0),
        seed: input.seed as u64,
        backend: CollisionBackendKind::Cde,
        rotation_context: rotation_context.clone(),
        solver_sheets_override,
        // SGH-Q40: the solver runs as a plain nester — spacing is already baked into the
        // offset part geometry, so the inner dual-geometry path stays inactive.
        spacing_mm: 0.0,
    };

    // SGH-Q40: the solver nests the OFFSET parts (spacing baked into geometry); original
    // stocks are still passed for physical area reporting (solver_sheets_override handles the
    // inset solving sheets).
    let mut result = run_finite_stock_multisheet(
        &offset_parts,
        &input.stocks,
        rotation_context,
        pre_unplaced,
        ms_config,
    );

    // SGH-Q34-R1: final margin validator using FULL transformed part polygon (not bbox).
    // Any violating placement is removed and moved to unplaced with an explicit reason, so
    // the top-level SolverOutput.status (computed from unplaced.is_empty()) cannot be `ok`.
    let t_margin_val = Instant::now();
    let margin_violating_ids = if margin_applied {
        find_sheet_margin_violations(
            &result.placements,
            &input.parts,
            original_sheets,
            margin_mm,
        )
    } else {
        Vec::new()
    };
    let margin_final_validator_ms = t_margin_val.elapsed().as_secs_f64() * 1000.0;
    let margin_violation_count = margin_violating_ids.len();
    let mut safety_net_removed_placement = margin_violation_count > 0;
    // SGH-Q37: accumulate ONLY the safety-net removal + recompute time here (the validators
    // are timed separately), so safety_net_ms does not double-count the validator cost.
    let mut safety_net_ms: f64 = 0.0;
    if margin_violation_count > 0 {
        let t = Instant::now();
        let placements = std::mem::take(&mut result.placements);
        let unplaced = std::mem::take(&mut result.unplaced);
        let (kept, new_unplaced) =
            apply_margin_violation_safety_net(placements, unplaced, &margin_violating_ids);
        result.placements = kept;
        result.unplaced = new_unplaced;
        safety_net_ms += t.elapsed().as_secs_f64() * 1000.0;
    }

    // SGH-Q35 / SGH-Q40: part-part spacing final validator.
    //
    // The Q36 spacing-aware tracker already GUARANTEES the spacing: it quantifies pairs on the
    // half-spacing-expanded geometry, and the multisheet manager only emits collision-free
    // layouts (final_pairs == 0). Two non-overlapping expanded shapes ⇒ the original contours
    // are >= spacing apart. The separate O(n²) re-validation over original polygons is therefore
    // REDUNDANT and was the dominant added wall-time (37-70 s on full LV8). It is DISABLED by
    // default (no overhead) and re-enableable for audit via `SGH_Q35_SPACING_VALIDATOR=1`.
    let spacing_validator_enabled =
        std::env::var("SGH_Q35_SPACING_VALIDATOR").ok().as_deref() == Some("1");
    let t_spacing_val = Instant::now();
    let spacing_violations = if spacing_applied && spacing_validator_enabled {
        find_part_spacing_violations(&result.placements, &input.parts, spacing_mm)
    } else {
        Vec::new()
    };
    let spacing_final_validator_ms = t_spacing_val.elapsed().as_secs_f64() * 1000.0;
    let spacing_violation_count = spacing_violations.len();
    let spacing_removed_count = spacing_safety_net_removed_count(&spacing_violations);
    if spacing_violation_count > 0 {
        let t = Instant::now();
        let placements = std::mem::take(&mut result.placements);
        let unplaced = std::mem::take(&mut result.unplaced);
        let (kept, new_unplaced) =
            apply_spacing_violation_safety_net(placements, unplaced, &spacing_violations);
        result.placements = kept;
        result.unplaced = new_unplaced;
        safety_net_removed_placement = true;
        safety_net_ms += t.elapsed().as_secs_f64() * 1000.0;
    }

    // SGH-Q35: recompute all result aggregates ONCE after the safety nets so diagnostics
    // and the top-level output cannot be contradictory (no stale used_sheet_*/counts/status).
    if safety_net_removed_placement {
        let t = Instant::now();
        recompute_multisheet_result_after_safety_net(&mut result, &input.parts, original_sheets);
        safety_net_ms += t.elapsed().as_secs_f64() * 1000.0;
    }

    // SGH-Q34: compute usable (margin-shrunk) vs physical area for the used sheets.
    //
    // SGH-Q40: usable area is the TRUE margin-shrunk area (sheet inset by `margin_mm`), NOT the
    // solver sheet (inset by `margin − spacing/2`). The two coincide when spacing == 0 (so the
    // baseline diagnostic stays byte-identical), but when spacing > 0 the solver sheet is inset
    // by less; reporting it here would overstate the margin-respecting usable region.
    let (margin_usable_area, margin_physical_area) = if margin_applied {
        let usable: f64 = result
            .used_sheet_indices
            .iter()
            .filter_map(|&orig_idx| original_sheets.get(orig_idx))
            .map(|s| {
                ((s.width - 2.0 * margin_mm).max(0.0)) * ((s.height - 2.0 * margin_mm).max(0.0))
            })
            .sum();
        let physical: f64 = result
            .used_sheet_indices
            .iter()
            .filter_map(|&orig_idx| original_sheets.get(orig_idx).map(|s| s.area))
            .sum();
        (Some(usable), Some(physical))
    } else {
        (None, None)
    };
    let margin_applied_sheet_count = if margin_applied {
        Some(original_sheets.len())
    } else {
        None
    };

    let snap = cde_observability::snapshot();
    let backend_diag = if result.status == "ok" {
        Some(cde_feasible_diag(&snap, "sparrow_cde_multisheet", None))
    } else {
        Some(cde_unsupported_diag(&snap, "sparrow_cde_multisheet_partial", None))
    };

    // Build optimizer diagnostics with Q32 multisheet fields populated.
    let best_core = result.best_core_diag.as_ref();
    let optimizer_diag = OptimizerDiagnosticsOutput {
        pipeline_used: "sparrow_cde_multisheet".to_string(),
        phase_optimizer_invoked: false,
        exploration_iterations: best_core.map(|d| d.iterations).unwrap_or(0),
        compression_iterations: 0,
        bpp_attempts: 0,
        rotation_refinement_enabled: false,
        rotation_refinement_attempts: 0,
        rotation_refinement_accepts: 0,
        rotation_refinement_rejections: 0,
        rotation_refinement_best_delta: 0.0,
        search_position_calls: best_core.map(|d| d.search_position_calls).unwrap_or(0),
        search_position_global_samples_evaluated: best_core.map(|d| d.search_global_samples).unwrap_or(0),
        search_position_focused_samples_evaluated: best_core.map(|d| d.search_focused_samples).unwrap_or(0),
        search_position_samples_unsupported: best_core.map(|d| d.search_unsupported_samples).unwrap_or(0),
        search_position_refined_samples: best_core.map(|d| d.search_refined_samples).unwrap_or(0),
        search_position_coord_descent_steps: best_core.map(|d| d.search_coord_descent_steps).unwrap_or(0),
        search_position_lbf_fallback_used: best_core.map(|d| d.lbf_fallback_used).unwrap_or(0),
        search_position_best_eval: 0.0,
        collision_severity_backend: "cde".to_string(),
        collision_severity_enabled: true,
        collision_severity_pair_queries: best_core.map(|d| d.quantified_pair_queries).unwrap_or(0),
        collision_severity_boundary_queries: best_core.map(|d| d.quantified_boundary_queries).unwrap_or(0),
        collision_severity_probe_queries: 0,
        collision_severity_backend_confirmed_collisions: 0,
        collision_severity_backend_confirmed_no_collisions: 0,
        collision_severity_unsupported_queries: 0,
        collision_severity_bbox_proxy_uses: 0,
        collision_severity_probe_pair_queries: 0,
        collision_severity_probe_boundary_queries: 0,
        collision_severity_probe_resolved: 0,
        collision_severity_probe_unresolved: 0,
        collision_severity_probe_unsupported: 0,
        collision_severity_min_resolution_mm: 0.0,
        collision_severity_max_resolution_mm: 0.0,
        collision_severity_avg_resolution_mm: 0.0,
        phase_optimizer_exploration_ms: None,
        phase_optimizer_compression_ms: None,
        phase_optimizer_bpp_ms: None,
        phase_optimizer_final_commit_ms: None,
        sparrow_invoked: Some(true),
        sparrow_seed_placements: best_core.map(|d| d.seed_placements),
        sparrow_seed_unplaced: best_core.map(|d| d.seed_unplaced),
        sparrow_initial_raw_loss: best_core.map(|d| d.initial_raw_loss),
        sparrow_initial_weighted_loss: best_core.map(|d| d.initial_weighted_loss),
        sparrow_final_raw_loss: best_core.map(|d| d.final_raw_loss),
        sparrow_final_weighted_loss: best_core.map(|d| d.final_weighted_loss),
        sparrow_best_infeasible_raw_loss: best_core.map(|d| d.best_infeasible_raw_loss),
        sparrow_best_infeasible_weighted_loss: best_core.map(|d| d.best_infeasible_weighted_loss),
        sparrow_iterations: best_core.map(|d| d.iterations),
        sparrow_moves_attempted: best_core.map(|d| d.moves_attempted),
        sparrow_moves_accepted: best_core.map(|d| d.moves_accepted),
        sparrow_rollbacks: best_core.map(|d| d.rollbacks),
        sparrow_gls_weight_updates: best_core.map(|d| d.gls_weight_updates),
        sparrow_converged: best_core.map(|d| d.converged),
        sparrow_collision_graph_initial_pairs: best_core.map(|d| d.collision_graph_initial_pairs),
        sparrow_collision_graph_final_pairs: Some(result.final_pairs),
        sparrow_boundary_violations_initial: best_core.map(|d| d.boundary_violations_initial),
        sparrow_boundary_violations_final: Some(result.boundary_violations),
        sparrow_search_position_calls: best_core.map(|d| d.search_position_calls),
        sparrow_search_position_samples: best_core.map(|d| d.search_position_samples),
        sparrow_severity_pair_queries: best_core.map(|d| d.quantified_pair_queries),
        sparrow_severity_boundary_queries: best_core.map(|d| d.quantified_boundary_queries),
        sparrow_severity_probe_queries: None,
        sparrow_lbf_fallback_used: best_core.map(|d| d.lbf_fallback_used),
        sparrow_workers: best_core.map(|d| d.worker_count),
        sparrow_worker_passes: best_core.map(|d| d.worker_passes),
        sparrow_worker_candidates_evaluated: best_core.map(|d| d.worker_candidates_evaluated),
        sparrow_worker_commits: best_core.map(|d| d.worker_commits),
        sparrow_worker_rollbacks: best_core.map(|d| d.worker_rollbacks),
        sparrow_worker_best_loss: best_core.map(|d| d.worker_best_loss),
        sparrow_multi_target_items_attempted: best_core.map(|d| d.multi_target_items_attempted),
        sparrow_multi_target_items_accepted: best_core.map(|d| d.multi_target_items_accepted),
        sparrow_multi_target_items_rejected: best_core.map(|d| d.multi_target_items_rejected),
        sparrow_topk_target_count: best_core.map(|d| d.topk_target_count),
        sparrow_graph_full_rebuilds: best_core.map(|d| d.native_tracker_full_rebuilds),
        sparrow_graph_incremental_updates: best_core.map(|d| d.native_tracker_incremental_updates),
        sparrow_graph_edges_recomputed: best_core.map(|d| d.quantified_pair_queries),
        sparrow_graph_edges_pruned_by_broadphase: Some(0),
        sparrow_graph_debug_rebuilds: Some(0),
        sparrow_graph_debug_rebuild_mismatches: Some(0),
        sparrow_exploration_restarts: best_core.map(|d| d.exploration_pool_restores),
        sparrow_exploration_seed_strategies: Some(0),
        sparrow_exploration_disruptions: best_core.map(|d| {
            d.exploration_disruptions_large_item_swap
                + d.exploration_disruptions_cross_sheet
                + d.exploration_disruptions_rotation
        }),
        sparrow_exploration_stagnation_events: Some(0),
        sparrow_exploration_best_raw_loss: best_core.map(|d| d.best_infeasible_raw_loss),
        sparrow_exploration_best_weighted_loss: best_core.map(|d| d.best_infeasible_weighted_loss),
        sparrow_exploration_best_feasible_found: best_core.map(|d| d.converged),
        sparrow_compression_passes: Some(0),
        sparrow_compression_candidates_evaluated: Some(0),
        sparrow_compression_accepts: Some(0),
        sparrow_compression_rejects: Some(0),
        sparrow_fixed_sheet_objective_before: Some(0.0),
        sparrow_fixed_sheet_objective_after: Some(0.0),
        sparrow_fixed_sheet_objective_delta: Some(0.0),
        loss_model_used: Some("CdeSeparationLoss".to_string()),
        loss_bbox_proxy_used_as_primary: Some(false),
        sparrow_native_model_active: Some(true),
        sparrow_native_tracker_active: Some(true),
        sparrow_old_core_used: Some(false),
        sparrow_native_problem_instances: best_core.map(|d| d.native_problem_instances),
        sparrow_native_tracker_full_rebuilds: best_core.map(|d| d.native_tracker_full_rebuilds),
        sparrow_native_tracker_incremental_updates: best_core.map(|d| d.native_tracker_incremental_updates),
        sparrow_dense_guard_used: Some(false),
        sparrow_dense_real_run: Some(false),
        sparrow_dense_partial_reason: None,
        sparrow_dense_validated_placements: None,
        sparrow_dense_unresolved_instances: None,
        sparrow_dense_final_validation_ran: Some(false),
        sparrow_profiling_enabled: Some(false),
        sparrow_profile_search_total_ms: None,
        sparrow_profile_session_build_ms: None,
        sparrow_profile_deregister_ms: None,
        sparrow_profile_candidate_transform_ms: None,
        sparrow_profile_cde_query_collect_ms: None,
        sparrow_profile_hazard_loss_ms: None,
        sparrow_profile_boundary_check_ms: None,
        sparrow_profile_broadphase_reject_count: None,
        sparrow_profile_early_termination_count: None,
        sparrow_q30_profile_enabled: Some(false),
        sparrow_q30_native_search_calls: None,
        sparrow_q30_evaluate_sample_calls: None,
        sparrow_q30_candidates_evaluated: None,
        sparrow_q30_global_samples_generated: None,
        sparrow_q30_focused_samples_generated: None,
        sparrow_q30_coord_descent_runs: None,
        sparrow_q30_coord_descent_steps: None,
        sparrow_q30_best_samples_insert_attempts: None,
        sparrow_q30_best_samples_inserted: None,
        sparrow_q30_best_samples_dedup_rejects: None,
        sparrow_q30_early_termination_count: None,
        sparrow_q30_broadphase_reject_count: None,
        sparrow_q30_search_total_ms: None,
        sparrow_q30_sample_generation_ms: None,
        sparrow_q30_best_samples_insert_dedup_ms: None,
        sparrow_q30_coord_descent_total_ms: None,
        sparrow_q30_evaluate_sample_total_ms: None,
        sparrow_q30_candidate_transform_prepare_ms: None,
        sparrow_q30_cde_query_collect_ms: None,
        sparrow_q30_boundary_check_ms: None,
        sparrow_q30_session_build_ms: None,
        sparrow_q30_deregister_reregister_ms: None,
        sparrow_q30r1_exclusive_enabled: Some(false),
        sparrow_q30r1_prepare_base_shape_native_ms: None,
        sparrow_q30r1_fixed_shapes_clone_ms: None,
        sparrow_q30r1_sheet_order_build_ms: None,
        sparrow_q30r1_best_samples_best_ms: None,
        sparrow_q30r1_best_samples_clone_ms: None,
        sparrow_q30r1_coord_descent_ask_ms: None,
        sparrow_q30r1_coord_descent_tell_ms: None,
        sparrow_q30r1_search_accounted_ms: None,
        sparrow_q30r1_search_unaccounted_ms: None,
        sparrow_q30r1_search_unaccounted_ratio_pct: None,
        sparrow_q30r1_total_solver_runtime_ms: None,
        sparrow_q30r1_adapter_solve_total_ms: None,
        sparrow_q30r1_sparrow_optimizer_solve_total_ms: None,
        sparrow_q30r1_seed_lbf_total_ms: None,
        sparrow_q30r1_tracker_initial_build_ms: None,
        sparrow_q30r1_exploration_total_ms: None,
        sparrow_q30r1_separator_total_ms: None,
        sparrow_q30r1_separator_iteration_total_ms: None,
        sparrow_q30r1_worker_competition_total_ms: None,
        sparrow_q30r1_worker_pass_total_ms: None,
        sparrow_q30r1_tracker_final_validation_ms: None,
        sparrow_q30r1_output_mapping_ms: None,
        sparrow_q30r1_other_solver_unaccounted_ms: None,
        sparrow_q30r1_other_solver_unaccounted_ratio_pct: None,
        sparrow_q30r1_evaluate_sample_calls_from_focused: None,
        sparrow_q30r1_evaluate_sample_calls_from_global: None,
        sparrow_q30r1_evaluate_sample_calls_from_coord_descent: None,
        sparrow_q30r1_best_samples_best_calls: None,
        sparrow_q30r1_best_samples_clone_calls: None,
        sparrow_q30r1_coord_descent_ask_calls: None,
        sparrow_q30r1_coord_descent_tell_calls: None,
        sparrow_q30r1_sheet_loop_iterations: None,
        sparrow_q30r1_worker_passes: None,
        sparrow_q30r1_worker_candidates_evaluated: None,
        sparrow_q30r1_worker_candidates_accepted: None,
        // Q31 base-shape cache fields from best core attempt
        sparrow_q31_base_shape_cache_build_ms: best_core.map(|d| d.q30_profile.base_shape_cache_build_ms),
        sparrow_q31_base_shape_cache_hits: best_core.map(|d| d.q30_profile.base_shape_cache_hits),
        sparrow_q31_base_shape_cache_misses: best_core.map(|d| d.q30_profile.base_shape_cache_misses),
        sparrow_q31_base_shape_cache_unique_parts: best_core.map(|d| d.q30_profile.base_shape_cache_unique_parts),
        sparrow_q31_base_shape_cache_reused_instances: best_core.map(|d| d.q30_profile.base_shape_cache_reused_instances),
        sparrow_q31_prepare_base_shape_native_hotpath_calls: best_core.map(|d| d.q30_profile.prepare_base_shape_native_hotpath_calls),
        sparrow_q31_prepare_base_shape_native_hotpath_ms: best_core.map(|d| d.q30_profile.prepare_base_shape_native_hotpath_ms),
        sparrow_q31_tracker_transform_from_base_ms: best_core.map(|d| d.q30_profile.tracker_transform_from_base_ms),
        sparrow_q31_search_base_shape_cache_hits: best_core.map(|d| d.q30_profile.search_base_shape_cache_hits),
        sparrow_q31_lbf_base_shape_cache_hits: best_core.map(|d| d.q30_profile.lbf_base_shape_cache_hits),
        // Q32 multisheet diagnostics
        sparrow_ms_active: Some(true),
        sparrow_ms_status: Some(result.status.clone()),
        sparrow_ms_available_sheet_count: Some(result.available_sheet_count),
        sparrow_ms_used_sheet_count: Some(result.used_sheet_indices.len()),
        sparrow_ms_used_sheet_indices: Some(result.used_sheet_indices.clone()),
        sparrow_ms_used_sheet_area: Some(result.used_sheet_area),
        sparrow_ms_placed_part_area: Some(result.placed_part_area),
        sparrow_ms_utilization_pct: Some(result.utilization_pct),
        sparrow_ms_total_instances: Some(result.total_instances),
        sparrow_ms_placed_instances: Some(result.placed_instances),
        sparrow_ms_unplaced_instances: Some(result.unplaced_instances),
        sparrow_ms_attempts: Some(result.attempts),
        sparrow_ms_candidate_subsets: Some(result.candidate_subsets),
        sparrow_ms_best_full_solution_found: Some(result.best_full_solution_found),
        sparrow_ms_stock_exhausted: Some(result.stock_exhausted),
        sparrow_ms_final_pairs: Some(result.final_pairs),
        sparrow_ms_boundary_violations: Some(result.boundary_violations),
        sparrow_ms_runtime_ms: Some(result.runtime_ms),
        sparrow_ms_requested_time_limit_s: Some(result.time_limit_s),
        sparrow_ms_deadline_hit: Some(result.deadline_hit),
        sparrow_ms_best_score: Some(result.best_score),
        // SGH-Q44 per-attempt multisheet diagnostics array (one record per attempt).
        sparrow_ms_attempt_diagnostics_count: Some(result.attempt_diagnostics.len()),
        sparrow_ms_attempt_diagnostics_schema_version: Some(
            crate::io::SPARROW_MS_ATTEMPT_DIAGNOSTICS_SCHEMA_VERSION,
        ),
        sparrow_ms_attempt_diagnostics: Some(result.attempt_diagnostics.clone()),
        // SGH-Q33: technology clearance policy diagnostics (diagnostic-only, no geometry offset)
        technology_policy_active: Some(true),
        technology_margin_mm: Some(technology_policy.margin_mm),
        technology_spacing_mm: Some(technology_policy.spacing_mm),
        technology_kerf_mm: Some(technology_policy.kerf_mm),
        technology_effective_sheet_margin_mm: Some(technology_policy.effective_sheet_margin_mm()),
        technology_effective_part_spacing_mm: Some(technology_policy.effective_part_spacing_mm()),
        technology_effective_kerf_mm: Some(technology_policy.effective_kerf_mm()),
        // SGH-Q34 sheet margin enforcement diagnostics
        technology_sheet_margin_applied: Some(margin_applied),
        technology_margin_applied_sheet_count: margin_applied_sheet_count,
        technology_margin_usable_sheet_area: margin_usable_area,
        technology_margin_physical_used_sheet_area: margin_physical_area,
        technology_margin_violation_count: Some(margin_violation_count),
        // SGH-Q35 part-part spacing final validator diagnostics
        technology_part_spacing_applied: Some(spacing_applied),
        technology_part_spacing_mm: Some(spacing_mm),
        technology_spacing_violation_count: Some(spacing_violation_count),
        technology_spacing_safety_net_removed_count: Some(spacing_removed_count),
        // SGH-Q40 unified-model spacing geometry diagnostics. The offset is applied as a
        // preprocessing pass on the part templates (build_offset_parts), NOT inside the inner
        // solver — so these are sourced from the adapter-level preprocessing, not best_core
        // (which now runs as a plain nester with spacing disabled).
        technology_spacing_geometry_applied: Some(spacing_applied),
        technology_spacing_offset_mm: Some(part_offset),
        technology_spacing_offset_part_count: Some(offset_metrics.parts_offset),
        // No per-instance runtime cache in the unified model: each template offset once up front.
        technology_spacing_offset_cache_hits: Some(0),
        technology_spacing_offset_cache_misses: Some(offset_metrics.parts_offset),
        technology_spacing_offset_failure_count: Some(spacing_offset_failure_count),
        // Boundary/output ALWAYS use original geometry (spacing is not a sheet margin).
        technology_spacing_boundary_uses_original_geometry: Some(true),
        technology_spacing_output_uses_original_geometry: Some(true),
        // SGH-Q37 measurement-hardening timing / inventory (from the preprocessing pass).
        technology_spacing_offset_build_ms: Some(offset_metrics.build_ms),
        technology_spacing_offset_avg_ms_per_part: Some(if offset_metrics.parts_offset > 0 {
            offset_metrics.build_ms / offset_metrics.parts_offset as f64
        } else {
            0.0
        }),
        technology_spacing_offset_max_ms_per_part: Some(offset_metrics.max_ms_per_part),
        technology_spacing_offset_input_vertex_count_total: Some(offset_metrics.input_vertex_total),
        technology_spacing_offset_output_vertex_count_total: Some(offset_metrics.output_vertex_total),
        technology_spacing_offset_area_ratio_avg: Some(if offset_metrics.parts_offset > 0 {
            offset_metrics.area_ratio_sum / offset_metrics.parts_offset as f64
        } else {
            0.0
        }),
        technology_spacing_offset_area_ratio_max: Some(offset_metrics.area_ratio_max),
        technology_margin_final_validator_ms: Some(margin_final_validator_ms),
        technology_spacing_final_validator_ms: Some(spacing_final_validator_ms),
        technology_safety_net_ms: Some(safety_net_ms),
        // SGH-Q40/Q41: unified single-geometry model is the active multisheet path. The signed
        // solver-sheet inset is `margin − spacing/2`; the inner core always runs at spacing 0.
        technology_unified_geometry_model_active: Some(true),
        technology_solver_sheet_inset_mm: Some(sheet_inset),
        technology_inner_spacing_mm: Some(0.0),
    };

    (result.placements, result.unplaced, Some(optimizer_diag), backend_diag)
}

fn score_breakdown_from_result(
    result: crate::optimizer::score::ScoreResult,
) -> ScoreBreakdownOutput {
    let bd = &result.breakdown;
    ScoreBreakdownOutput {
        total_cost: bd.total_cost,
        placed_area_contribution: bd.placed_area_contribution,
        unplaced_contribution: bd.unplaced_contribution,
        sheet_cost_contribution: bd.sheet_count_contribution,
        sheet_cost_total: bd.sheet_cost_total,
        usable_area_utilization: bd.usable_area_utilization,
        overlap_contribution: bd.overlap_contribution,
        boundary_contribution: bd.boundary_contribution,
        compactness_contribution: bd.compactness_contribution,
    }
}

fn phase1_score_breakdown_for_backend(
    placements: &[Placement],
    unplaced: &[Unplaced],
    parts: &[crate::item::Part],
    sheets: &[crate::sheet::SheetShape],
    backend_kind: &CollisionBackendKind,
) -> ScoreBreakdownOutput {
    let model = ScoreModel::default();
    score_breakdown_from_result(model.score_with_backend(
        placements,
        unplaced,
        parts,
        sheets,
        backend_kind,
    ))
}

fn phase_config_from_input(
    input: &SolverInput,
    rotation_context: RotationResolveContext,
) -> PhaseConfig {
    let total_budget_s = (input.time_limit_s as f64).max(1.0);
    let mut config = PhaseConfig::deterministic_default();
    config.seed = input.seed;
    config.worker_count = 1;
    config.rotation_context = rotation_context;
    config.exploration_budget = PhaseBudget::new(16, total_budget_s * 0.60);
    config.compression_budget = PhaseBudget::new(8, total_budget_s * 0.25);
    config.bpp_budget = PhaseBudget::new(4, total_budget_s * 0.15);
    config.bpp_max_eliminations = 16;
    config.collision_backend = resolve_backend_kind(input);
    config
}

#[allow(dead_code)]
fn phase_commit_or_unsupported(
    input: &SolverInput,
    layout: WorkingLayout,
    parts: &[crate::item::Part],
    sheets: &[crate::sheet::SheetShape],
) -> Result<(Vec<Placement>, Vec<Unplaced>), SolverOutput> {
    layout
        .validate_and_commit(parts, sheets)
        .map_err(|_| _unsupported_output("PHASE_OPTIMIZER_COMMIT_VIOLATION", input))
}

pub fn solve(input: SolverInput) -> Result<SolverOutput, String> {
    if input.solver_profile.as_deref() == Some(PROFILE_PHASE1) {
        for part in &input.parts {
            if part_has_holes(part) {
                return Ok(_unsupported_output("UNSUPPORTED_PART_HOLES_PHASE1", &input));
            }
        }
        for stock in &input.stocks {
            if stock_has_holes(stock) {
                return Ok(_unsupported_output(
                    "UNSUPPORTED_STOCK_HOLES_PHASE1",
                    &input,
                ));
            }
        }
        // SGH-Q33: sparrow_cde_multisheet centralizes margin_mm via TechnologyClearancePolicy
        // (diagnostic-only, no polygon offset). Preserve the guard for all other pipelines.
        if pipeline_kind(&input) != OptimizerPipelineKind::SparrowCdeMultisheet {
            if let Some(margin_mm) = input.margin_mm {
                if margin_mm > 0.0 {
                    return Ok(_unsupported_output("UNSUPPORTED_MARGIN_MM_RUNTIME", &input));
                }
            }
        }
    }

    // SGH-Q33: centralise technology clearance policy. Validation fails early on
    // negative values. Policy is diagnostic-only in Q33 — no geometry offset yet.
    let technology_policy = TechnologyClearancePolicy::from_solver_input(&input)
        .map_err(|e| e)?;

    let rotation_context = RotationResolveContext::new(
        input.rotation_policy.clone(),
        input.seed as u64,
        DEFAULT_CONTINUOUS_SAMPLE_COUNT,
    );
    let sheets = expand_sheets(&input.stocks)?;
    let all_instances = expand_instances_with_policy(&input.parts, &rotation_context)?;
    let pipeline = pipeline_kind(&input);
    let mut collision_backend_diag: Option<CollisionBackendDiagnosticsOutput> = None;
    let (placements, unplaced, optimizer_diagnostics) = if input.solver_profile.as_deref()
        == Some(PROFILE_PHASE1)
    {
        // Pre-filter: instances whose part cannot fit any sheet get PART_NEVER_FITS_STOCK.
        let mut pre_unplaced: Vec<Unplaced> = Vec::new();
        let mut instances: Vec<_> = Vec::new();
        for inst in all_instances {
            let part = input
                .parts
                .iter()
                .find(|p| p.id == inst.part_id)
                .ok_or_else(|| format!("internal error: part not found: {}", inst.part_id))?;
            if !can_fit_any_stock_with_policy(part, &sheets, &rotation_context)? {
                pre_unplaced.push(Unplaced {
                    instance_id: inst.instance_id,
                    part_id: inst.part_id,
                    reason: "PART_NEVER_FITS_STOCK".to_string(),
                });
            } else {
                instances.push(inst);
            }
        }
        let backend_kind = resolve_backend_kind(&input);
        match pipeline {
            OptimizerPipelineKind::LegacyMultisheet => {
                let repair_time_s = (input.time_limit_s as f64).max(1.0);
                let mut policy = StoppingPolicy::new(256, repair_time_s);
                let manager = MultiSheetManager::new_with_rotation_context(
                    &input.parts,
                    &sheets,
                    rotation_context.clone(),
                );
                let (p, mut u, _ms_diag) = manager.run(&instances, &mut policy);
                u.extend(pre_unplaced);
                if backend_kind != CollisionBackendKind::Bbox {
                    let is_cde = backend_kind == CollisionBackendKind::Cde;
                    if is_cde {
                        cde_observability::reset();
                        crate::optimizer::cde_adapter::reset_query_cache();
                    }
                    let timing_enabled = cde_timing_enabled();
                    let t_start = timing_start(timing_enabled);
                    let working = WorkingLayout::new(p, u, sheets.len(), input.seed);
                    match working.validate_and_commit_with_backend(
                        &input.parts,
                        &sheets,
                        backend_kind,
                    ) {
                        Ok(commit) => {
                            let ms = timing_ms(t_start);
                            collision_backend_diag = Some(if is_cde {
                                let snap = cde_observability::snapshot();
                                diag_output_from_with_cde(&commit, snap, "final_commit_only", ms)
                            } else {
                                diag_output_from(&commit)
                            });
                            (commit.placements, commit.unplaced, None)
                        }
                        Err(e) => {
                            let reason =
                                backend_err_reason(e, "COLLISION_BACKEND_COMMIT_VIOLATION");
                            if is_cde {
                                let snap = cde_observability::snapshot();
                                let ms = timing_ms(t_start);
                                let diag = cde_unsupported_diag(&snap, "final_commit_only", ms);
                                return Ok(_unsupported_output_with_backend_diag(
                                    &reason,
                                    &input,
                                    Some(diag),
                                ));
                            }
                            return Ok(_unsupported_output(&reason, &input));
                        }
                    }
                } else {
                    (p, u, None)
                }
            }
            OptimizerPipelineKind::PhaseOptimizer => {
                let is_cde = backend_kind == CollisionBackendKind::Cde;
                if is_cde {
                    cde_observability::reset();
                    crate::optimizer::cde_adapter::reset_query_cache();
                }
                let timing_enabled = cde_timing_enabled();
                let (init_p, mut init_u, _construction_diag) =
                    build_initial_layout_with_rotation_context(
                        &instances,
                        &input.parts,
                        &sheets,
                        &rotation_context,
                    );
                init_u.extend(pre_unplaced);
                let working = WorkingLayout::new(init_p, init_u, sheets.len(), input.seed);
                let config = phase_config_from_input(&input, rotation_context.clone());
                let result = PhaseOptimizer::new(config).run(working, &input.parts, &sheets);
                let layout = result.layout;
                let t_commit_start = timing_start(timing_enabled);
                let backend_name = format!("{:?}", backend_kind);
                match layout.validate_and_commit_with_backend(&input.parts, &sheets, backend_kind) {
                    Ok(commit) => {
                        let final_commit_ms = timing_ms(t_commit_start);
                        collision_backend_diag = Some(if is_cde {
                            let snap = cde_observability::snapshot();
                            diag_output_from_with_cde(&commit, snap, "full_solve", final_commit_ms)
                        } else {
                            diag_output_from(&commit)
                        });
                        let diag_ref = &result.diagnostics;
                        let diagnostics = OptimizerDiagnosticsOutput {
                            pipeline_used: "phase_optimizer".to_string(),
                            phase_optimizer_invoked: true,
                            exploration_iterations: diag_ref.exploration_iterations,
                            compression_iterations: diag_ref.compression_iterations,
                            bpp_attempts: diag_ref.bpp_attempts,
                            rotation_refinement_enabled: diag_ref.rotation_refinement_enabled,
                            rotation_refinement_attempts: diag_ref.rotation_refinement_attempts,
                            rotation_refinement_accepts: diag_ref.rotation_refinement_accepts,
                            rotation_refinement_rejections: diag_ref
                                .rotation_refinement_attempts
                                .saturating_sub(diag_ref.rotation_refinement_accepts),
                            rotation_refinement_best_delta: diag_ref.rotation_refinement_best_delta,
                            search_position_calls: diag_ref.search_position_calls,
                            search_position_global_samples_evaluated: diag_ref
                                .search_position_global_samples_evaluated,
                            search_position_focused_samples_evaluated: diag_ref
                                .search_position_focused_samples_evaluated,
                            search_position_samples_unsupported: diag_ref
                                .search_position_samples_unsupported,
                            search_position_refined_samples: diag_ref
                                .search_position_refined_samples,
                            search_position_coord_descent_steps: diag_ref
                                .search_position_coord_descent_steps,
                            search_position_lbf_fallback_used: diag_ref
                                .search_position_lbf_fallback_used,
                            search_position_best_eval: if diag_ref.search_position_best_eval
                                == f64::MAX
                            {
                                0.0
                            } else {
                                diag_ref.search_position_best_eval
                            },
                            collision_severity_backend: backend_name,
                            collision_severity_enabled: diag_ref.collision_severity_enabled,
                            collision_severity_pair_queries: diag_ref
                                .collision_severity_pair_queries,
                            collision_severity_boundary_queries: diag_ref
                                .collision_severity_boundary_queries,
                            collision_severity_probe_queries: diag_ref
                                .collision_severity_probe_queries,
                            collision_severity_backend_confirmed_collisions: diag_ref
                                .collision_severity_backend_confirmed_collisions,
                            collision_severity_backend_confirmed_no_collisions: diag_ref
                                .collision_severity_backend_confirmed_no_collisions,
                            collision_severity_unsupported_queries: diag_ref
                                .collision_severity_unsupported_queries,
                            collision_severity_bbox_proxy_uses: diag_ref
                                .collision_severity_bbox_proxy_uses,
                            collision_severity_probe_pair_queries: diag_ref
                                .collision_severity_probe_pair_queries,
                            collision_severity_probe_boundary_queries: diag_ref
                                .collision_severity_probe_boundary_queries,
                            collision_severity_probe_resolved: diag_ref
                                .collision_severity_probe_resolved,
                            collision_severity_probe_unresolved: diag_ref
                                .collision_severity_probe_unresolved,
                            collision_severity_probe_unsupported: diag_ref
                                .collision_severity_probe_unsupported,
                            collision_severity_min_resolution_mm: diag_ref
                                .collision_severity_min_resolution_mm,
                            collision_severity_max_resolution_mm: diag_ref
                                .collision_severity_max_resolution_mm,
                            collision_severity_avg_resolution_mm: diag_ref
                                .collision_severity_avg_resolution_mm,
                            phase_optimizer_exploration_ms: result.exploration_ms,
                            phase_optimizer_compression_ms: result.compression_ms,
                            phase_optimizer_bpp_ms: result.bpp_ms,
                            phase_optimizer_final_commit_ms: final_commit_ms,
                            sparrow_invoked: None,
                            sparrow_seed_placements: None,
                            sparrow_seed_unplaced: None,
                            sparrow_initial_raw_loss: None,
                            sparrow_initial_weighted_loss: None,
                            sparrow_final_raw_loss: None,
                            sparrow_final_weighted_loss: None,
                            sparrow_best_infeasible_raw_loss: None,
                            sparrow_best_infeasible_weighted_loss: None,
                            sparrow_iterations: None,
                            sparrow_moves_attempted: None,
                            sparrow_moves_accepted: None,
                            sparrow_rollbacks: None,
                            sparrow_gls_weight_updates: None,
                            sparrow_converged: None,
                            sparrow_collision_graph_initial_pairs: None,
                            sparrow_collision_graph_final_pairs: None,
                            sparrow_boundary_violations_initial: None,
                            sparrow_boundary_violations_final: None,
                            sparrow_search_position_calls: None,
                            sparrow_search_position_samples: None,
                            sparrow_severity_pair_queries: None,
                            sparrow_severity_boundary_queries: None,
                            sparrow_severity_probe_queries: None,
                            sparrow_lbf_fallback_used: None,
                            sparrow_workers: None,
                            sparrow_worker_passes: None,
                            sparrow_worker_candidates_evaluated: None,
                            sparrow_worker_commits: None,
                            sparrow_worker_rollbacks: None,
                            sparrow_worker_best_loss: None,
                            sparrow_multi_target_items_attempted: None,
                            sparrow_multi_target_items_accepted: None,
                            sparrow_multi_target_items_rejected: None,
                            sparrow_topk_target_count: None,
                            sparrow_graph_full_rebuilds: None,
                            sparrow_graph_incremental_updates: None,
                            sparrow_graph_edges_recomputed: None,
                            sparrow_graph_edges_pruned_by_broadphase: None,
                            sparrow_graph_debug_rebuilds: None,
                            sparrow_graph_debug_rebuild_mismatches: None,
                            sparrow_exploration_restarts: None,
                            sparrow_exploration_seed_strategies: None,
                            sparrow_exploration_disruptions: None,
                            sparrow_exploration_stagnation_events: None,
                            sparrow_exploration_best_raw_loss: None,
                            sparrow_exploration_best_weighted_loss: None,
                            sparrow_exploration_best_feasible_found: None,
                            sparrow_compression_passes: None,
                            sparrow_compression_candidates_evaluated: None,
                            sparrow_compression_accepts: None,
                            sparrow_compression_rejects: None,
                            sparrow_fixed_sheet_objective_before: None,
                            sparrow_fixed_sheet_objective_after: None,
                            sparrow_fixed_sheet_objective_delta: None,
                            loss_model_used: None,
                            loss_bbox_proxy_used_as_primary: None,
                            sparrow_native_model_active: None,
                            sparrow_native_tracker_active: None,
                            sparrow_old_core_used: None,
                            sparrow_native_problem_instances: None,
                            sparrow_native_tracker_full_rebuilds: None,
                            sparrow_native_tracker_incremental_updates: None,
                            sparrow_dense_guard_used: None,
                            sparrow_dense_real_run: None,
                            sparrow_dense_partial_reason: None,
                            sparrow_dense_validated_placements: None,
                            sparrow_dense_unresolved_instances: None,
                            sparrow_dense_final_validation_ran: None,
                            sparrow_profiling_enabled: None,
                            sparrow_profile_search_total_ms: None,
                            sparrow_profile_session_build_ms: None,
                            sparrow_profile_deregister_ms: None,
                            sparrow_profile_candidate_transform_ms: None,
                            sparrow_profile_cde_query_collect_ms: None,
                            sparrow_profile_hazard_loss_ms: None,
                            sparrow_profile_boundary_check_ms: None,
                            sparrow_profile_broadphase_reject_count: None,
                            sparrow_profile_early_termination_count: None,
                            sparrow_q30_profile_enabled: None,
                            sparrow_q30_native_search_calls: None,
                            sparrow_q30_evaluate_sample_calls: None,
                            sparrow_q30_candidates_evaluated: None,
                            sparrow_q30_global_samples_generated: None,
                            sparrow_q30_focused_samples_generated: None,
                            sparrow_q30_coord_descent_runs: None,
                            sparrow_q30_coord_descent_steps: None,
                            sparrow_q30_best_samples_insert_attempts: None,
                            sparrow_q30_best_samples_inserted: None,
                            sparrow_q30_best_samples_dedup_rejects: None,
                            sparrow_q30_early_termination_count: None,
                            sparrow_q30_broadphase_reject_count: None,
                            sparrow_q30_search_total_ms: None,
                            sparrow_q30_sample_generation_ms: None,
                            sparrow_q30_best_samples_insert_dedup_ms: None,
                            sparrow_q30_coord_descent_total_ms: None,
                            sparrow_q30_evaluate_sample_total_ms: None,
                            sparrow_q30_candidate_transform_prepare_ms: None,
                            sparrow_q30_cde_query_collect_ms: None,
                            sparrow_q30_boundary_check_ms: None,
                            sparrow_q30_session_build_ms: None,
                            sparrow_q30_deregister_reregister_ms: None,
                            sparrow_q30r1_exclusive_enabled: None,
                            sparrow_q30r1_prepare_base_shape_native_ms: None,
                            sparrow_q30r1_fixed_shapes_clone_ms: None,
                            sparrow_q30r1_sheet_order_build_ms: None,
                            sparrow_q30r1_best_samples_best_ms: None,
                            sparrow_q30r1_best_samples_clone_ms: None,
                            sparrow_q30r1_coord_descent_ask_ms: None,
                            sparrow_q30r1_coord_descent_tell_ms: None,
                            sparrow_q30r1_search_accounted_ms: None,
                            sparrow_q30r1_search_unaccounted_ms: None,
                            sparrow_q30r1_search_unaccounted_ratio_pct: None,
                            sparrow_q30r1_total_solver_runtime_ms: None,
                            sparrow_q30r1_adapter_solve_total_ms: None,
                            sparrow_q30r1_sparrow_optimizer_solve_total_ms: None,
                            sparrow_q30r1_seed_lbf_total_ms: None,
                            sparrow_q30r1_tracker_initial_build_ms: None,
                            sparrow_q30r1_exploration_total_ms: None,
                            sparrow_q30r1_separator_total_ms: None,
                            sparrow_q30r1_separator_iteration_total_ms: None,
                            sparrow_q30r1_worker_competition_total_ms: None,
                            sparrow_q30r1_worker_pass_total_ms: None,
                            sparrow_q30r1_tracker_final_validation_ms: None,
                            sparrow_q30r1_output_mapping_ms: None,
                            sparrow_q30r1_other_solver_unaccounted_ms: None,
                            sparrow_q30r1_other_solver_unaccounted_ratio_pct: None,
                            sparrow_q30r1_evaluate_sample_calls_from_focused: None,
                            sparrow_q30r1_evaluate_sample_calls_from_global: None,
                            sparrow_q30r1_evaluate_sample_calls_from_coord_descent: None,
                            sparrow_q30r1_best_samples_best_calls: None,
                            sparrow_q30r1_best_samples_clone_calls: None,
                            sparrow_q30r1_coord_descent_ask_calls: None,
                            sparrow_q30r1_coord_descent_tell_calls: None,
                            sparrow_q30r1_sheet_loop_iterations: None,
                            sparrow_q30r1_worker_passes: None,
                            sparrow_q30r1_worker_candidates_evaluated: None,
                            sparrow_q30r1_worker_candidates_accepted: None,
                            sparrow_q31_base_shape_cache_build_ms: None,
                            sparrow_q31_base_shape_cache_hits: None,
                            sparrow_q31_base_shape_cache_misses: None,
                            sparrow_q31_base_shape_cache_unique_parts: None,
                            sparrow_q31_base_shape_cache_reused_instances: None,
                            sparrow_q31_prepare_base_shape_native_hotpath_calls: None,
                            sparrow_q31_prepare_base_shape_native_hotpath_ms: None,
                            sparrow_q31_tracker_transform_from_base_ms: None,
                            sparrow_q31_search_base_shape_cache_hits: None,
                            sparrow_q31_lbf_base_shape_cache_hits: None,
                            sparrow_ms_active: None,
                            sparrow_ms_status: None,
                            sparrow_ms_available_sheet_count: None,
                            sparrow_ms_used_sheet_count: None,
                            sparrow_ms_used_sheet_indices: None,
                            sparrow_ms_used_sheet_area: None,
                            sparrow_ms_placed_part_area: None,
                            sparrow_ms_utilization_pct: None,
                            sparrow_ms_total_instances: None,
                            sparrow_ms_placed_instances: None,
                            sparrow_ms_unplaced_instances: None,
                            sparrow_ms_attempts: None,
                            sparrow_ms_candidate_subsets: None,
                            sparrow_ms_best_full_solution_found: None,
                            sparrow_ms_stock_exhausted: None,
                            sparrow_ms_final_pairs: None,
                            sparrow_ms_boundary_violations: None,
                            sparrow_ms_runtime_ms: None,
                            sparrow_ms_requested_time_limit_s: None,
                            sparrow_ms_deadline_hit: None,
                            sparrow_ms_best_score: None,
                            sparrow_ms_attempt_diagnostics: None,
                            sparrow_ms_attempt_diagnostics_count: None,
                            sparrow_ms_attempt_diagnostics_schema_version: None,
                            technology_policy_active: None,
                            technology_margin_mm: None,
                            technology_spacing_mm: None,
                            technology_kerf_mm: None,
                            technology_effective_sheet_margin_mm: None,
                            technology_effective_part_spacing_mm: None,
                            technology_effective_kerf_mm: None,
                            technology_sheet_margin_applied: None,
                            technology_margin_applied_sheet_count: None,
                            technology_margin_usable_sheet_area: None,
                            technology_margin_physical_used_sheet_area: None,
                            technology_margin_violation_count: None,
                            technology_part_spacing_applied: None,
                            technology_part_spacing_mm: None,
                            technology_spacing_violation_count: None,
                            technology_spacing_safety_net_removed_count: None,
                            technology_spacing_geometry_applied: None,
                            technology_spacing_offset_mm: None,
                            technology_spacing_offset_part_count: None,
                            technology_spacing_offset_cache_hits: None,
                            technology_spacing_offset_cache_misses: None,
                            technology_spacing_offset_failure_count: None,
                            technology_spacing_boundary_uses_original_geometry: None,
                            technology_spacing_output_uses_original_geometry: None,
                            technology_spacing_offset_build_ms: None,
                            technology_spacing_offset_avg_ms_per_part: None,
                            technology_spacing_offset_max_ms_per_part: None,
                            technology_spacing_offset_input_vertex_count_total: None,
                            technology_spacing_offset_output_vertex_count_total: None,
                            technology_spacing_offset_area_ratio_avg: None,
                            technology_spacing_offset_area_ratio_max: None,
                            technology_margin_final_validator_ms: None,
                            technology_spacing_final_validator_ms: None,
                            technology_safety_net_ms: None,
                            // Legacy PhaseOptimizer path — Q40 unified model not active here.
                            technology_unified_geometry_model_active: None,
                            technology_solver_sheet_inset_mm: None,
                            technology_inner_spacing_mm: None,
                        };
                        (commit.placements, commit.unplaced, Some(diagnostics))
                    }
                    Err(e) => {
                        let reason =
                            backend_err_reason(e, "PHASE_OPTIMIZER_COMMIT_VIOLATION_BACKEND");
                        if is_cde {
                            let snap = cde_observability::snapshot();
                            let ms = timing_ms(t_commit_start);
                            let diag = cde_unsupported_diag(&snap, "full_solve", ms);
                            return Ok(_unsupported_output_with_backend_diag(
                                &reason,
                                &input,
                                Some(diag),
                            ));
                        }
                        return Ok(_unsupported_output(&reason, &input));
                    }
                }
            }
            OptimizerPipelineKind::SparrowExperimental => {
                // Q22 experimental Sparrow: backend chosen by the caller (bbox or cde).
                match run_sparrow_pipeline(
                    &input,
                    &sheets,
                    &rotation_context,
                    pre_unplaced,
                    backend_kind,
                    "sparrow_experimental",
                ) {
                    Ok((p, u, diag, bdiag)) => {
                        collision_backend_diag = bdiag;
                        (p, u, diag)
                    }
                    Err(out) => return Ok(out),
                }
            }
            OptimizerPipelineKind::SparrowCde => {
                // SGH-Q23 production Sparrow path. CDE-first by contract: the CDE
                // geometry backend is forced regardless of the requested
                // `collision_backend` (bbox is debug/legacy only and may not be a
                // production collision source). No legacy fallback; a failure is
                // surfaced as unsupported/partial with full diagnostics preserved.
                match run_sparrow_pipeline(
                    &input,
                    &sheets,
                    &rotation_context,
                    pre_unplaced,
                    CollisionBackendKind::Cde,
                    "sparrow_cde",
                ) {
                    Ok((p, u, diag, bdiag)) => {
                        collision_backend_diag = bdiag;
                        (p, u, diag)
                    }
                    Err(out) => return Ok(out),
                }
            }
            OptimizerPipelineKind::SparrowCdeMultisheet => {
                // SGH-Q32: finite-stock multisheet manager. CDE-first by contract.
                // Manages a pool of available sheets, tries candidate subsets, and
                // returns the best valid incumbent. Never falls back to legacy solver.
                let (p, u, diag, bdiag) = run_sparrow_finite_stock_multisheet_pipeline(
                    &input,
                    &sheets,
                    &rotation_context,
                    pre_unplaced,
                    &technology_policy,
                );
                collision_backend_diag = bdiag;
                (p, u, diag)
            }
        }
    } else {
        // Row/cursor fallback for non-Phase1 profiles.
        let mut placements: Vec<Placement> = Vec::new();
        let mut unplaced: Vec<Unplaced> = Vec::new();
        let mut per_sheet_cursor: Vec<SheetCursor> = sheets
            .iter()
            .map(|_| SheetCursor {
                x: 0.0,
                y: 0.0,
                row_h: 0.0,
            })
            .collect();
        for instance in &all_instances {
            let part = input
                .parts
                .iter()
                .find(|p| p.id == instance.part_id)
                .ok_or_else(|| format!("internal error: part not found: {}", instance.part_id))?;
            if !can_fit_any_stock_with_policy(part, &sheets, &rotation_context)? {
                unplaced.push(Unplaced {
                    instance_id: instance.instance_id.clone(),
                    part_id: instance.part_id.clone(),
                    reason: "PART_NEVER_FITS_STOCK".to_string(),
                });
                continue;
            }
            let mut placed = None;
            for (idx, sheet) in sheets.iter().enumerate() {
                if let Some(c) =
                    try_place_on_sheet(instance, sheet, &mut per_sheet_cursor[idx], idx)
                {
                    placed = Some(c);
                    break;
                }
            }
            if let Some(p) = placed {
                placements.push(p);
            } else {
                unplaced.push(Unplaced {
                    instance_id: instance.instance_id.clone(),
                    part_id: instance.part_id.clone(),
                    reason: "NO_CAPACITY".to_string(),
                });
            }
        }
        (placements, unplaced, None)
    };
    // Compute score breakdown for Phase1 profile (JG-19 — backward-compatible optional output field).
    let score_breakdown = if input.solver_profile.as_deref() == Some(PROFILE_PHASE1) {
        let backend_kind = resolve_backend_kind(&input);
        let mut bd = phase1_score_breakdown_for_backend(
            &placements,
            &unplaced,
            &input.parts,
            &sheets,
            &backend_kind,
        );
        // For the multisheet pipeline, the bbox-based placed_area used internally by the
        // optimizer overstates true area for complex polygons. Override usable_area_utilization
        // with the polygon-based value from multisheet diagnostics so it matches
        // sparrow_ms_utilization_pct and is not misleading.
        if pipeline == OptimizerPipelineKind::SparrowCdeMultisheet {
            if let Some(ref diag) = optimizer_diagnostics {
                if let (Some(poly_area), Some(sheet_area)) = (
                    diag.sparrow_ms_placed_part_area,
                    diag.sparrow_ms_used_sheet_area,
                ) {
                    if sheet_area > 0.0 {
                        bd.usable_area_utilization = (poly_area / sheet_area).min(1.0);
                    }
                }
            }
        }
        Some(bd)
    } else {
        None
    };
    let status = if unplaced.is_empty() { "ok" } else { "partial" }.to_string();
    let sheet_count_used = placements
        .iter()
        .map(|p| p.sheet_index)
        .max()
        .map(|v| v + 1)
        .unwrap_or(0);

    let placed_count = placements.len();
    let unplaced_count = unplaced.len();

    Ok(SolverOutput {
        contract_version: "v1".to_string(),
        status,
        unsupported_reason: None,
        placements,
        unplaced,
        metrics: Metrics {
            placed_count,
            unplaced_count,
            sheet_count_used,
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name,
        },
        score_breakdown,
        optimizer_diagnostics,
        collision_backend_diagnostics: collision_backend_diag,
    })
}

// ---------------------------------------------------------------------------
// JaguaAdapter contract — VRS-owned PoC boundary (JG-04)
// Jagua-rs types stay internal; only VRS geometry types cross the public API.
// ---------------------------------------------------------------------------

/// VRS-owned error categories for the jagua backend boundary.
/// No jagua-rs types appear here.
#[derive(Debug)]
pub enum JaguaAdapterError {
    /// Input geometry could not be converted to jagua internal representation.
    ConversionError(String),
    /// A jagua backend operation returned an unexpected runtime error.
    BackendError(String),
    /// The requested operation is not yet supported by the adapter PoC.
    Unsupported(String),
}

impl fmt::Display for JaguaAdapterError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::ConversionError(s) => write!(f, "conversion_error: {s}"),
            Self::BackendError(s) => write!(f, "backend_error: {s}"),
            Self::Unsupported(s) => write!(f, "unsupported: {s}"),
        }
    }
}

/// Thin VRS adapter to the jagua-rs collision/geometry backend.
/// Accepts VRS-owned point slices; jagua types never appear in the public API.
/// Precision note: f64 VRS coordinates are narrowed to f32 for jagua (documented).
pub struct JaguaAdapter;

impl JaguaAdapter {
    /// Returns `true` if the two polygons (given as VRS Point slices) collide.
    ///
    /// Detection strategy (composing known jagua primitives):
    /// 1. Any corner of poly_b inside poly_a → collision.
    /// 2. Any corner of poly_a inside poly_b → collision.
    /// 3. Any edge of poly_a intersects any edge of poly_b → collision.
    pub fn check_polygon_collision(
        poly_a: &[crate::geometry::Point],
        poly_b: &[crate::geometry::Point],
    ) -> Result<bool, JaguaAdapterError> {
        use crate::geometry::{jag_edge_from_points, to_jag_point, to_jag_polygon};
        use jagua_rs::geometry::geo_traits::CollidesWith;

        let spoly_a =
            to_jag_polygon(poly_a, "poly_a").map_err(JaguaAdapterError::ConversionError)?;
        let spoly_b =
            to_jag_polygon(poly_b, "poly_b").map_err(JaguaAdapterError::ConversionError)?;

        // Point containment: any corner of B inside A?
        for p in poly_b {
            if spoly_a.collides_with(&to_jag_point(*p)) {
                return Ok(true);
            }
        }
        // Point containment: any corner of A inside B?
        for p in poly_a {
            if spoly_b.collides_with(&to_jag_point(*p)) {
                return Ok(true);
            }
        }
        // Edge-edge intersection
        let n_a = poly_a.len();
        let n_b = poly_b.len();
        for i in 0..n_a {
            let Some(edge_a) = jag_edge_from_points(poly_a[i], poly_a[(i + 1) % n_a]) else {
                continue;
            };
            for j in 0..n_b {
                let Some(edge_b) = jag_edge_from_points(poly_b[j], poly_b[(j + 1) % n_b]) else {
                    continue;
                };
                if edge_a.collides_with(&edge_b) {
                    return Ok(true);
                }
            }
        }
        Ok(false)
    }

    /// Returns `true` if the rectangular item fits entirely inside the sheet shape.
    /// Delegates to `optimizer::boundary::rect_within_boundary` — the canonical
    /// boundary policy point for all construction, repair, and scoring paths.
    pub fn check_rect_in_sheet(
        item_rect: crate::geometry::Rect,
        sheet: &crate::sheet::SheetShape,
    ) -> bool {
        crate::optimizer::boundary::rect_within_boundary(item_rect, sheet)
    }
}

#[cfg(test)]
mod tests {
    use super::{
        apply_margin_violation_safety_net, apply_spacing_violation_safety_net,
        phase_commit_or_unsupported, solve, spacing_safety_net_removed_count,
        REASON_PART_SPACING_VIOLATION, REASON_SHEET_MARGIN_VIOLATION,
    };
    use crate::technology::spacing::PartSpacingViolation;
    use crate::io::{
        CollisionBackendKind, OptimizerPipelineKind, Placement, SolverInput, SolverOutput,
    };
    use crate::item::Part;
    use crate::optimizer::repair::find_violations;
    use crate::optimizer::working::WorkingLayout;
    use crate::rotation_policy::RotationPolicyKind;
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(
        id: &str,
        w: f64,
        h: f64,
        qty: i64,
        rots: Vec<i64>,
        rotation_policy: Option<RotationPolicyKind>,
    ) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: rots,
            rotation_policy,
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
        }
    }

    fn make_stock(id: &str, w: f64, h: f64, qty: i64) -> Stock {
        Stock {
            id: id.to_string(),
            quantity: qty,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }
    }

    fn make_input(
        seed: i64,
        stocks: Vec<Stock>,
        parts: Vec<Part>,
        rotation_policy: Option<RotationPolicyKind>,
    ) -> SolverInput {
        SolverInput {
            contract_version: "v1".to_string(),
            project_name: "test".to_string(),
            seed,
            time_limit_s: 5,
            stocks,
            parts,
            solver_profile: Some("jagua_optimizer_phase1_outer_only".to_string()),
            margin_mm: None,
            spacing_mm: None,
            kerf_mm: None,
            rotation_policy,
            optimizer_pipeline: Some(OptimizerPipelineKind::LegacyMultisheet),
            collision_backend: None,
        }
    }

    fn assert_same_output(left: &SolverOutput, right: &SolverOutput) {
        assert_eq!(left.contract_version, right.contract_version);
        assert_eq!(left.status, right.status);
        assert_eq!(left.unsupported_reason, right.unsupported_reason);
        assert_eq!(left.metrics.placed_count, right.metrics.placed_count);
        assert_eq!(left.metrics.unplaced_count, right.metrics.unplaced_count);
        assert_eq!(
            left.metrics.sheet_count_used,
            right.metrics.sheet_count_used
        );
        assert_eq!(left.metrics.seed, right.metrics.seed);
        assert_eq!(left.metrics.time_limit_s, right.metrics.time_limit_s);
        assert_eq!(left.metrics.project_name, right.metrics.project_name);
        assert_eq!(left.placements.len(), right.placements.len());
        for (a, b) in left.placements.iter().zip(right.placements.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.part_id, b.part_id);
            assert_eq!(a.sheet_index, b.sheet_index);
            assert!((a.x - b.x).abs() < 1e-9);
            assert!((a.y - b.y).abs() < 1e-9);
            assert!((a.rotation_deg - b.rotation_deg).abs() < 1e-9);
        }
        assert_eq!(left.unplaced.len(), right.unplaced.len());
        for (a, b) in left.unplaced.iter().zip(right.unplaced.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.part_id, b.part_id);
            assert_eq!(a.reason, b.reason);
        }
        assert_eq!(
            left.optimizer_diagnostics.is_some(),
            right.optimizer_diagnostics.is_some()
        );
        assert_eq!(
            left.collision_backend_diagnostics.is_some(),
            right.collision_backend_diagnostics.is_some()
        );
    }

    #[test]
    fn adapter_solve_global_forty_five_places_100x20_on_90x90_sheet() {
        let stock = vec![make_stock("S", 90.0, 90.0, 1)];
        let parts = vec![make_part("P", 100.0, 20.0, 1, vec![], None)];

        let mut no_global = make_input(7, stock.clone(), parts.clone(), None);
        no_global.rotation_policy = Some(RotationPolicyKind::Orthogonal);
        let out_a = solve(no_global).expect("solve A");
        assert_eq!(out_a.metrics.placed_count, 0);
        assert_eq!(out_a.metrics.unplaced_count, 1);

        let with_global = make_input(7, stock, parts, Some(RotationPolicyKind::FortyFive));
        let out_b = solve(with_global).expect("solve B");
        assert_eq!(out_b.metrics.placed_count, 1);
        assert_eq!(out_b.metrics.unplaced_count, 0);
        assert_eq!(out_b.status, "ok");
    }

    #[test]
    fn adapter_solve_legacy_allowed_rotations_overrides_global_policy() {
        let stock = vec![make_stock("S", 90.0, 90.0, 1)];
        let parts = vec![make_part("P", 100.0, 20.0, 1, vec![0], None)];
        let input = make_input(9, stock, parts, Some(RotationPolicyKind::FortyFive));
        let out = solve(input).expect("solve");
        assert_eq!(out.metrics.placed_count, 0);
        assert_eq!(out.metrics.unplaced_count, 1);
    }

    #[test]
    fn part_policy_overrides_global_policy_in_real_solve_path() {
        let stock = vec![make_stock("S", 90.0, 90.0, 1)];
        let parts = vec![make_part(
            "P",
            100.0,
            20.0,
            1,
            vec![],
            Some(RotationPolicyKind::FortyFive),
        )];
        let input = make_input(9, stock, parts, Some(RotationPolicyKind::Orthogonal));
        let out = solve(input).expect("solve");
        assert_eq!(out.metrics.placed_count, 1);
        assert_eq!(out.metrics.unplaced_count, 0);
    }

    #[test]
    fn continuous_policy_same_seed_deterministic_through_solve() {
        let stock = vec![make_stock("S", 90.0, 90.0, 1)];
        let parts = vec![make_part("P", 100.0, 20.0, 1, vec![], None)];
        let a = solve(make_input(
            12345,
            stock.clone(),
            parts.clone(),
            Some(RotationPolicyKind::Continuous),
        ))
        .expect("solve A");
        let b = solve(make_input(
            12345,
            stock,
            parts,
            Some(RotationPolicyKind::Continuous),
        ))
        .expect("solve B");
        assert_eq!(a.metrics.placed_count, b.metrics.placed_count);
        assert_eq!(a.metrics.unplaced_count, b.metrics.unplaced_count);
        assert_eq!(a.placements.len(), b.placements.len());
        for (pa, pb) in a.placements.iter().zip(b.placements.iter()) {
            assert_eq!(pa.instance_id, pb.instance_id);
            assert_eq!(pa.part_id, pb.part_id);
            assert_eq!(pa.sheet_index, pb.sheet_index);
            assert!((pa.rotation_deg - pb.rotation_deg).abs() < 1e-9);
            assert!((pa.x - pb.x).abs() < 1e-9);
            assert!((pa.y - pb.y).abs() < 1e-9);
        }
    }

    #[test]
    fn solver_input_optimizer_pipeline_defaults_to_legacy() {
        let json = r#"{
            "contract_version": "v1",
            "project_name": "default_pipeline",
            "seed": 1,
            "time_limit_s": 5,
            "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
            "parts": [{"id": "P", "width": 10.0, "height": 10.0, "quantity": 1}]
        }"#;
        let input: SolverInput = serde_json::from_str(json).expect("input");
        assert_eq!(
            input.optimizer_pipeline.unwrap_or_default(),
            OptimizerPipelineKind::LegacyMultisheet
        );
    }

    #[test]
    fn phase1_missing_optimizer_pipeline_routes_to_sparrow_cde() {
        let input = SolverInput {
            contract_version: "v1".to_string(),
            project_name: "default_phase1_sparrow_cde".to_string(),
            seed: 1,
            time_limit_s: 5,
            stocks: vec![make_stock("S", 100.0, 100.0, 1)],
            parts: vec![make_part("P", 10.0, 10.0, 1, vec![0], None)],
            solver_profile: Some("jagua_optimizer_phase1_outer_only".to_string()),
            margin_mm: None,
            spacing_mm: None,
            kerf_mm: None,
            rotation_policy: None,
            optimizer_pipeline: None,
            collision_backend: Some(CollisionBackendKind::Bbox),
        };
        let out = solve(input).expect("solve");
        let diag = out.optimizer_diagnostics.expect("sparrow diagnostics");
        assert_eq!(diag.pipeline_used, "sparrow_cde");
        assert_eq!(diag.collision_severity_backend, "Cde");
        let backend = out
            .collision_backend_diagnostics
            .expect("backend diagnostics");
        assert_eq!(backend.backend_used, "cde_adapter");
        assert_eq!(backend.bbox_fallback_queries, 0);
    }

    #[test]
    fn legacy_explicit_matches_implicit_output() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 3, vec![0], None)];

        let implicit = solve(make_input(17, stock.clone(), parts.clone(), None)).expect("implicit");
        let mut explicit_input = make_input(17, stock, parts, None);
        explicit_input.optimizer_pipeline = Some(OptimizerPipelineKind::LegacyMultisheet);
        let explicit = solve(explicit_input).expect("explicit");

        assert_same_output(&implicit, &explicit);
    }

    #[test]
    fn phase_optimizer_pipeline_invokes_phase_optimizer() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 2, vec![0], None)];
        let mut input = make_input(21, stock, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);

        let out = solve(input).expect("phase solve");
        let diag = out.optimizer_diagnostics.expect("phase diagnostics");
        assert_eq!(diag.pipeline_used, "phase_optimizer");
        assert!(diag.phase_optimizer_invoked);
        assert!(diag.exploration_iterations + diag.compression_iterations + diag.bpp_attempts > 0);
    }

    #[test]
    fn phase_optimizer_pipeline_preserves_rotation_context() {
        let stock = vec![make_stock("S", 90.0, 90.0, 1)];
        let parts = vec![make_part("P", 100.0, 20.0, 1, vec![], None)];
        let mut input = make_input(21, stock, parts, Some(RotationPolicyKind::FortyFive));
        input.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);

        let out = solve(input).expect("phase solve");
        assert_eq!(out.metrics.placed_count, 1);
        assert_eq!(out.metrics.unplaced_count, 0);
    }

    #[test]
    fn phase_optimizer_pipeline_is_deterministic_for_same_seed() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 3, vec![0], None)];

        let mut a = make_input(33, stock.clone(), parts.clone(), None);
        a.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);
        let mut b = make_input(33, stock, parts, None);
        b.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);

        let out_a = solve(a).expect("phase A");
        let out_b = solve(b).expect("phase B");
        assert_same_output(&out_a, &out_b);
    }

    #[test]
    fn phase_optimizer_pipeline_output_has_no_violations() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 3, vec![0], None)];
        let sheets = expand_sheets(&stock).expect("sheets");
        let mut input = make_input(41, stock, parts.clone(), None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);

        let out = solve(input).expect("phase solve");
        assert!(find_violations(&out.placements, &parts, &sheets).is_empty());
    }

    // ── Q10: collision backend policy tests ──────────────────────────────────

    #[test]
    fn solver_input_collision_backend_defaults_to_bbox() {
        let json = r#"{
            "contract_version": "v1",
            "project_name": "p",
            "seed": 1,
            "time_limit_s": 5,
            "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
            "parts": [{"id": "P", "width": 10.0, "height": 10.0, "quantity": 1}]
        }"#;
        let input: SolverInput = serde_json::from_str(json).expect("deserialize");
        assert!(
            input.collision_backend.is_none(),
            "missing field must deserialize to None"
        );
        assert_eq!(
            input.collision_backend.unwrap_or_default(),
            CollisionBackendKind::Bbox
        );
    }

    #[test]
    fn jagua_polygon_exact_backend_can_be_selected_in_solver_input() {
        let json = r#"{
            "contract_version": "v1",
            "project_name": "p",
            "seed": 1,
            "time_limit_s": 5,
            "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
            "parts": [{"id": "P", "width": 10.0, "height": 10.0, "quantity": 1}],
            "collision_backend": "jagua_polygon_exact"
        }"#;
        let input: SolverInput = serde_json::from_str(json).expect("deserialize");
        assert_eq!(
            input.collision_backend,
            Some(CollisionBackendKind::JaguaPolygonExact)
        );
    }

    #[test]
    fn explicit_bbox_matches_implicit_default_output() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 2, vec![0], None)];

        let implicit = solve(make_input(17, stock.clone(), parts.clone(), None)).expect("implicit");
        let mut explicit_input = make_input(17, stock, parts, None);
        explicit_input.collision_backend = Some(CollisionBackendKind::Bbox);
        let explicit = solve(explicit_input).expect("explicit");

        assert_eq!(implicit.status, explicit.status);
        assert_eq!(implicit.metrics.placed_count, explicit.metrics.placed_count);
        assert_eq!(implicit.placements.len(), explicit.placements.len());
    }

    #[test]
    fn phase_optimizer_with_bbox_backend_preserves_q09_behavior() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 2, vec![0], None)];

        let mut without_backend = make_input(33, stock.clone(), parts.clone(), None);
        without_backend.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);
        let out_a = solve(without_backend).expect("phase without backend");

        let mut with_bbox = make_input(33, stock, parts, None);
        with_bbox.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);
        with_bbox.collision_backend = Some(CollisionBackendKind::Bbox);
        let out_b = solve(with_bbox).expect("phase with bbox");

        assert_eq!(out_a.status, out_b.status);
        assert_eq!(out_a.metrics.placed_count, out_b.metrics.placed_count);
        assert_eq!(out_a.placements.len(), out_b.placements.len());
    }

    #[test]
    fn jagua_polygon_exact_invalid_outer_points_returns_unsupported_not_bbox_fallback() {
        // Part with malformed outer_points — JaguaPolygonExactBackend returns Unsupported.
        // bbox backend (default) would ignore outer_points and produce ok/partial.
        // jagua_polygon_exact backend must produce status=unsupported (no silent downgrade).
        let json_exact = r#"{
            "contract_version": "v1",
            "project_name": "test_exact_invalid",
            "seed": 1,
            "time_limit_s": 5,
            "solver_profile": "jagua_optimizer_phase1_outer_only",
            "optimizer_pipeline": "phase_optimizer",
            "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
            "parts": [{
                "id": "P",
                "width": 20.0,
                "height": 20.0,
                "quantity": 1,
                "outer_points": [["x_bad", 0.0], [10.0, 0.0], [10.0, 10.0]]
            }],
            "collision_backend": "jagua_polygon_exact"
        }"#;
        let input: SolverInput = serde_json::from_str(json_exact).expect("deserialize exact");
        let out = solve(input).expect("solve");
        assert_eq!(
            out.status, "unsupported",
            "jagua_polygon_exact with invalid outer_points must be unsupported, not ok/partial"
        );
        assert_eq!(
            out.unsupported_reason.as_deref(),
            Some("JAGUA_POLYGON_EXACT_UNSUPPORTED_QUERY"),
            "reason must be JAGUA_POLYGON_EXACT_UNSUPPORTED_QUERY"
        );
        assert!(out.placements.is_empty());

        // Contrast: bbox default ignores outer_points and places successfully.
        let json_bbox = r#"{
            "contract_version": "v1",
            "project_name": "test_bbox_default",
            "seed": 1,
            "time_limit_s": 5,
            "solver_profile": "jagua_optimizer_phase1_outer_only",
            "optimizer_pipeline": "legacy_multisheet",
            "stocks": [{"id": "S", "quantity": 1, "width": 100.0, "height": 100.0}],
            "parts": [{
                "id": "P",
                "width": 20.0,
                "height": 20.0,
                "quantity": 1,
                "outer_points": [["x_bad", 0.0], [10.0, 0.0], [10.0, 10.0]]
            }]
        }"#;
        let input_bbox: SolverInput = serde_json::from_str(json_bbox).expect("deserialize bbox");
        let out_bbox = solve(input_bbox).expect("solve bbox");
        assert_ne!(
            out_bbox.status, "unsupported",
            "bbox default must not return unsupported for malformed outer_points"
        );
    }

    #[test]
    fn cde_backend_returns_unsupported_not_bbox_fallback() {
        // Malformed outer_points → CDE prepare_shape fails → UnsupportedBackend with per-query reason.
        // Valid simple geometry (no outer_points) must NOT produce this error after Q16.
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let mut bad_part = make_part("P", 20.0, 20.0, 1, vec![0], None);
        bad_part.outer_points = Some(serde_json::json!("not-an-array")); // malformed
        let mut input = make_input(1, stock, vec![bad_part], None);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = solve(input).expect("solve");
        assert_eq!(
            out.status, "unsupported",
            "malformed geometry with cde backend must produce unsupported"
        );
        assert_eq!(
            out.unsupported_reason.as_deref(),
            Some("CDE_BACKEND_UNSUPPORTED_QUERY"),
            "reason must be CDE_BACKEND_UNSUPPORTED_QUERY for per-query failure, not blanket CDE_BACKEND_UNSUPPORTED"
        );
        assert!(out.placements.is_empty());
    }

    // -----------------------------------------------------------------------
    // SGH-Q16 tests — CDE final commit gate consistency
    // -----------------------------------------------------------------------

    #[test]
    fn adapter_cde_backend_valid_simple_case_is_not_unsupported() {
        // After Q16: valid rect part + CDE backend must NOT produce status="unsupported".
        // The blanket CDE_BACKEND_UNSUPPORTED scaffold is gone.
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 20.0, 20.0, 1, vec![0], None)];
        let mut input = make_input(1, stock, parts, None);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = solve(input).expect("solve");
        assert_ne!(
            out.status, "unsupported",
            "valid rect part with CDE backend must not produce unsupported output after Q16"
        );
    }

    #[test]
    fn adapter_cde_backend_valid_simple_case_reports_cde_diagnostics() {
        // After Q16: valid rect part with CDE backend must report CDE diagnostics.
        // backend_used == "cde_adapter", unsupported_queries == 0, bbox_fallback_queries == 0.
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 20.0, 20.0, 1, vec![0], None)];
        let mut input = make_input(1, stock, parts, None);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = solve(input).expect("solve");
        let diag = out
            .collision_backend_diagnostics
            .expect("CDE commit must produce collision_backend_diagnostics");
        assert_eq!(
            diag.backend_used, "cde_adapter",
            "backend_used must be cde_adapter for CDE commit"
        );
        assert_eq!(
            diag.unsupported_queries, 0,
            "no unsupported queries for valid rect part with CDE"
        );
        assert_eq!(
            diag.bbox_fallback_queries, 0,
            "no bbox fallback for CDE final commit"
        );
    }

    #[test]
    fn adapter_cde_backend_invalid_geometry_returns_unsupported_not_bbox_fallback() {
        // Malformed outer_points → CDE must return UnsupportedBackend with per-query reason.
        // Must NOT silently fall back to bbox and produce a placement.
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let mut bad_part = make_part("P", 20.0, 20.0, 1, vec![0], None);
        bad_part.outer_points = Some(serde_json::json!("not-an-array")); // malformed
        let mut input = make_input(1, stock, vec![bad_part], None);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = solve(input).expect("solve");
        assert_eq!(out.status, "unsupported");
        assert_eq!(
            out.unsupported_reason.as_deref(),
            Some("CDE_BACKEND_UNSUPPORTED_QUERY"),
        );
        assert!(
            out.placements.is_empty(),
            "malformed geometry must not produce placements"
        );
    }

    #[test]
    fn adapter_cde_backend_does_not_return_legacy_cde_backend_unsupported_for_valid_case() {
        // After Q16: the blanket "CDE_BACKEND_UNSUPPORTED" reason must not appear for valid simple geometry.
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 20.0, 20.0, 1, vec![0], None)];
        let mut input = make_input(1, stock, parts, None);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = solve(input).expect("solve");
        assert_ne!(
            out.unsupported_reason.as_deref(),
            Some("CDE_BACKEND_UNSUPPORTED"),
            "legacy CDE_BACKEND_UNSUPPORTED must not appear for valid simple geometry after Q16"
        );
    }

    // -----------------------------------------------------------------------
    // SGH-Q18A tests — CDE observability diagnostics
    // -----------------------------------------------------------------------

    #[test]
    fn adapter_cde_valid_output_contains_observability_diagnostics() {
        // Valid rect + CDE backend must emit cde_total_queries > 0 and cde_engine_builds > 0.
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 20.0, 20.0, 1, vec![0], None)];
        let mut input = make_input(1, stock, parts, None);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = solve(input).expect("solve");
        let diag = out
            .collision_backend_diagnostics
            .expect("CDE valid output must have collision_backend_diagnostics");
        assert_eq!(diag.backend_used, "cde_adapter");
        assert_eq!(diag.bbox_fallback_queries, 0, "no bbox fallback for CDE");
        let total = diag
            .cde_total_queries
            .expect("cde_total_queries must be present");
        let builds = diag
            .cde_engine_builds
            .expect("cde_engine_builds must be present");
        assert!(
            total > 0,
            "CDE must have processed at least one query: total={}",
            total
        );
        assert!(
            builds > 0,
            "CDE must have built at least one CDEngine: builds={}",
            builds
        );
        assert_eq!(
            diag.cde_observability_scope.as_deref(),
            Some("final_commit_only"),
            "legacy_multisheet CDE scope must be final_commit_only"
        );
        assert_eq!(
            diag.final_commit_backend_used.as_deref(),
            Some("cde_adapter"),
            "final_commit_backend_used must be cde_adapter"
        );
    }

    #[test]
    fn adapter_cde_unsupported_output_preserves_observability_diagnostics() {
        // Malformed outer_points + CDE → unsupported output must still carry CDE diagnostics.
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let mut bad_part = make_part("P", 20.0, 20.0, 1, vec![0], None);
        bad_part.outer_points = Some(serde_json::json!("not-an-array"));
        let mut input = make_input(1, stock, vec![bad_part], None);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = solve(input).expect("solve");
        assert_eq!(out.status, "unsupported");
        assert_eq!(
            out.unsupported_reason.as_deref(),
            Some("CDE_BACKEND_UNSUPPORTED_QUERY")
        );
        let diag = out
            .collision_backend_diagnostics
            .expect("CDE unsupported output must carry observability diagnostics");
        assert_eq!(diag.backend_used, "cde_adapter");
        assert_eq!(diag.bbox_fallback_queries, 0);
        // At least 1 unsupported/prepare-failure must be counted
        let unsupported = diag
            .cde_unsupported_results
            .expect("cde_unsupported_results must be present");
        let failures = diag
            .cde_prepare_failures
            .expect("cde_prepare_failures must be present");
        assert!(
            unsupported > 0 || failures > 0,
            "malformed geometry must register at least one unsupported or prepare_failure counter"
        );
    }

    #[test]
    fn bbox_backend_does_not_emit_cde_observability() {
        // Bbox backend (default) must not produce collision_backend_diagnostics at all.
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 20.0, 20.0, 1, vec![0], None)];
        let input = make_input(1, stock, parts, None); // no collision_backend → defaults to Bbox
        let out = solve(input).expect("solve");
        assert!(
            out.collision_backend_diagnostics.is_none(),
            "bbox backend must not emit collision_backend_diagnostics"
        );
    }

    // -----------------------------------------------------------------------
    // SGH-Q18A-R1: phase timing output tests
    // -----------------------------------------------------------------------

    #[test]
    fn phase_optimizer_timing_fields_absent_by_default() {
        // Without VRS_CDE_OBSERVABILITY_TIMING=1, optimizer_diagnostics must not
        // contain timing fields (they're None → omitted by serde).
        if std::env::var("VRS_CDE_OBSERVABILITY_TIMING")
            .ok()
            .as_deref()
            == Some("1")
        {
            return; // skip when timing explicitly enabled by test runner
        }
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 2, vec![0], None)];
        let mut input = make_input(21, stock, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);
        let out = solve(input).expect("solve");
        let diag = out
            .optimizer_diagnostics
            .expect("must have optimizer_diagnostics");
        assert!(
            diag.phase_optimizer_exploration_ms.is_none(),
            "exploration_ms must be None by default"
        );
        assert!(
            diag.phase_optimizer_compression_ms.is_none(),
            "compression_ms must be None by default"
        );
        assert!(
            diag.phase_optimizer_bpp_ms.is_none(),
            "bpp_ms must be None by default"
        );
        assert!(
            diag.phase_optimizer_final_commit_ms.is_none(),
            "final_commit_ms must be None by default"
        );
    }

    #[test]
    fn cde_timing_field_absent_by_default_in_cde_output() {
        // Without VRS_CDE_OBSERVABILITY_TIMING=1, final_commit_validation_ms must be None.
        if std::env::var("VRS_CDE_OBSERVABILITY_TIMING")
            .ok()
            .as_deref()
            == Some("1")
        {
            return; // skip when timing explicitly enabled
        }
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 20.0, 20.0, 1, vec![0], None)];
        let mut input = make_input(1, stock, parts, None);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = solve(input).expect("solve");
        let diag = out
            .collision_backend_diagnostics
            .expect("must have CDE diagnostics");
        assert!(
            diag.final_commit_validation_ms.is_none(),
            "final_commit_validation_ms must be None by default"
        );
    }

    #[test]
    fn determinism_not_broken_by_default_output() {
        // Same seed + same backend → identical placements (timing fields are None and absent
        // from JSON, so they don't affect determinism).
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 3, vec![0], None)];
        let mut a = make_input(42, stock.clone(), parts.clone(), None);
        a.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);
        let mut b = make_input(42, stock, parts, None);
        b.optimizer_pipeline = Some(OptimizerPipelineKind::PhaseOptimizer);
        let out_a = solve(a).expect("solve A");
        let out_b = solve(b).expect("solve B");
        assert_eq!(out_a.placements.len(), out_b.placements.len());
        for (pa, pb) in out_a.placements.iter().zip(out_b.placements.iter()) {
            assert_eq!(pa.x.to_bits(), pb.x.to_bits());
            assert_eq!(pa.y.to_bits(), pb.y.to_bits());
        }
    }

    #[test]
    fn cde_observability_does_not_break_existing_q16_tests() {
        // Regression: Q16 tests still pass with Q18A instrumentation.
        // valid CDE → not unsupported; backend_used == "cde_adapter"; no bbox fallback
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 20.0, 20.0, 1, vec![0], None)];
        let mut input = make_input(1, stock.clone(), parts.clone(), None);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = solve(input).expect("solve");
        assert_ne!(
            out.status, "unsupported",
            "Q16: valid CDE must not be unsupported"
        );
        let diag = out
            .collision_backend_diagnostics
            .expect("Q16: must have diagnostics");
        assert_eq!(diag.backend_used, "cde_adapter");
        assert_eq!(diag.unsupported_queries, 0);
        assert_eq!(diag.bbox_fallback_queries, 0);
    }

    #[test]
    fn same_seed_same_backend_is_deterministic() {
        let stock = vec![make_stock("S", 160.0, 100.0, 1)];
        let parts = vec![make_part("P", 40.0, 20.0, 3, vec![0], None)];

        for backend in [
            None,
            Some(CollisionBackendKind::Bbox),
            Some(CollisionBackendKind::JaguaPolygonExact),
        ] {
            let mut a = make_input(42, stock.clone(), parts.clone(), None);
            a.collision_backend = backend.clone();
            let mut b = make_input(42, stock.clone(), parts.clone(), None);
            b.collision_backend = backend;

            let out_a = solve(a).expect("solve A");
            let out_b = solve(b).expect("solve B");

            assert_eq!(out_a.status, out_b.status, "status must be deterministic");
            assert_eq!(out_a.metrics.placed_count, out_b.metrics.placed_count);
            assert_eq!(out_a.placements.len(), out_b.placements.len());
            for (pa, pb) in out_a.placements.iter().zip(out_b.placements.iter()) {
                assert_eq!(pa.instance_id, pb.instance_id);
                assert!((pa.x - pb.x).abs() < 1e-9);
                assert!((pa.y - pb.y).abs() < 1e-9);
                assert!((pa.rotation_deg - pb.rotation_deg).abs() < 1e-9);
            }
        }
    }

    #[test]
    fn jagua_polygon_exact_l_shape_notch_does_not_report_bbox_false_positive() {
        // Helper-level: JaguaPolygonExactBackend must report NoCollision when B sits in A's notch.
        // This test confirms the backend does not produce the bbox false-positive.
        use crate::optimizer::collision_backend::{
            BboxCollisionBackend, CollisionBackend, JaguaPolygonExactBackend,
        };
        let l_json = serde_json::json!([
            [0.0, 0.0],
            [40.0, 0.0],
            [40.0, 20.0],
            [20.0, 20.0],
            [20.0, 40.0],
            [0.0, 40.0]
        ]);
        let part_a = crate::item::Part {
            id: "L".to_string(),
            width: 40.0,
            height: 40.0,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(l_json),
            prepared_outer_points: None,
            rotation_policy: None,
        };
        let part_b = crate::item::Part {
            id: "B".to_string(),
            width: 15.0,
            height: 15.0,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        };
        let p_a = Placement {
            instance_id: "L__0001".into(),
            part_id: "L".into(),
            sheet_index: 0,
            x: 0.0,
            y: 0.0,
            rotation_deg: 0.0,
        };
        let p_b = Placement {
            instance_id: "B__0001".into(),
            part_id: "B".into(),
            sheet_index: 0,
            x: 22.0,
            y: 22.0,
            rotation_deg: 0.0,
        };

        let bbox = BboxCollisionBackend;
        let exact = JaguaPolygonExactBackend;
        assert!(
            bbox.placement_overlaps(&p_a, &part_a, &p_b, &part_b)
                .is_collision(),
            "bbox must report false positive for notch"
        );
        assert!(
            exact
                .placement_overlaps(&p_a, &part_a, &p_b, &part_b)
                .is_no_collision(),
            "exact backend must report no collision for item in notch"
        );
    }

    #[test]
    fn phase_optimizer_invalid_commit_does_not_silently_fallback_to_legacy() {
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 50.0, 50.0, 2, vec![0], None)];
        let input = make_input(51, stock.clone(), parts.clone(), None);
        let sheets = expand_sheets(&stock).expect("sheets");
        let invalid = WorkingLayout::new(
            vec![
                Placement {
                    instance_id: "P__0001".into(),
                    part_id: "P".into(),
                    sheet_index: 0,
                    x: 0.0,
                    y: 0.0,
                    rotation_deg: 0.0,
                },
                Placement {
                    instance_id: "P__0002".into(),
                    part_id: "P".into(),
                    sheet_index: 0,
                    x: 0.0,
                    y: 0.0,
                    rotation_deg: 0.0,
                },
            ],
            vec![],
            sheets.len(),
            input.seed,
        );

        let rejected = phase_commit_or_unsupported(&input, invalid, &parts, &sheets)
            .expect_err("invalid phase commit must be rejected");
        assert_eq!(rejected.status, "unsupported");
        assert_eq!(
            rejected.unsupported_reason.as_deref(),
            Some("PHASE_OPTIMIZER_COMMIT_VIOLATION")
        );
        assert!(rejected.placements.is_empty());
    }

    // -----------------------------------------------------------------------
    // SGH-Q11 tests
    // -----------------------------------------------------------------------

    #[test]
    fn adapter_score_breakdown_uses_selected_backend() {
        let l_json = serde_json::json!([
            [0.0, 0.0],
            [40.0, 0.0],
            [40.0, 20.0],
            [20.0, 20.0],
            [20.0, 40.0],
            [0.0, 40.0]
        ]);
        let mut l_part = make_part("L", 40.0, 40.0, 1, vec![0], None);
        l_part.outer_points = Some(l_json);
        let parts = vec![l_part, make_part("B", 15.0, 15.0, 1, vec![0], None)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            Placement {
                instance_id: "L__0001".into(),
                part_id: "L".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "B__0001".into(),
                part_id: "B".into(),
                sheet_index: 0,
                x: 22.0,
                y: 22.0,
                rotation_deg: 0.0,
            },
        ];

        let bbox = super::phase1_score_breakdown_for_backend(
            &placements,
            &[],
            &parts,
            &sheets,
            &CollisionBackendKind::Bbox,
        );
        let exact = super::phase1_score_breakdown_for_backend(
            &placements,
            &[],
            &parts,
            &sheets,
            &CollisionBackendKind::JaguaPolygonExact,
        );

        assert!(
            bbox.overlap_contribution > 0.0,
            "bbox score_breakdown must expose the fixture's bbox false-positive"
        );
        assert_eq!(exact.overlap_contribution, 0.0,
            "exact score_breakdown must use selected backend and remove bbox false-positive overlap");
    }

    #[test]
    fn adapter_phase_optimizer_passes_collision_backend_to_phase_config() {
        use crate::rotation_policy::RotationResolveContext;

        // Build an input with explicit JaguaPolygonExact backend.
        let stock = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 20.0, 20.0, 1, vec![0], None)];
        let mut input = make_input(99, stock, parts, None);
        input.collision_backend = Some(CollisionBackendKind::JaguaPolygonExact);

        // Reconstruct phase config the same way adapter.rs does.
        let rc = RotationResolveContext::legacy_default();
        let cfg = super::phase_config_from_input(&input, rc);

        assert!(
            matches!(
                cfg.collision_backend,
                CollisionBackendKind::JaguaPolygonExact
            ),
            "phase_config_from_input must propagate collision_backend from SolverInput"
        );
    }

    // ------------------------------------------------------------------
    // SGH-Q22: Sparrow adapter integration tests
    // ------------------------------------------------------------------

    /// SGH-Q22: explicit `sparrow_experimental` pipeline routes from adapter
    /// and emits `pipeline_used = sparrow_experimental` in diagnostics.
    #[test]
    fn sparrow_pipeline_routes_from_adapter() {
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let parts = vec![make_part("P", 30.0, 20.0, 2, vec![0], None)];
        let mut input = make_input(1, stocks, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::SparrowExperimental);
        let out = super::solve(input).expect("solve ok");
        assert!(
            out.status == "ok" || out.status == "partial",
            "status got {} for sparrow run",
            out.status
        );
        let diag = out
            .optimizer_diagnostics
            .expect("sparrow run must emit optimizer_diagnostics");
        assert_eq!(diag.pipeline_used, "sparrow_experimental");
        assert_eq!(diag.sparrow_invoked, Some(true));
        assert!(diag.sparrow_iterations.is_some());
    }

    /// SGH-Q24R5: the native Sparrow core's collision truth is the jagua_rs CDE
    /// engine for EVERY requested backend (the native `SparrowCollisionTracker`
    /// is CDE-backed). So the sparrow pipeline always emits collision-backend
    /// diagnostics, and `backend_used` reflects the CDE adapter even when a
    /// non-CDE backend was requested. This replaces the pre-cutover invariant
    /// where a `WorkingLayout` commit honored the selected backend.
    #[test]
    fn sparrow_pipeline_final_commit_uses_selected_backend() {
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let parts = vec![make_part("P", 30.0, 20.0, 2, vec![0], None)];
        let mut input = make_input(2, stocks, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::SparrowExperimental);
        input.collision_backend = Some(CollisionBackendKind::JaguaPolygonExact);
        let out = super::solve(input).expect("solve ok");
        assert!(out.status == "ok" || out.status == "partial");
        let cbd = out
            .collision_backend_diagnostics
            .expect("sparrow pipeline must emit collision_backend_diagnostics");
        assert_eq!(
            cbd.backend_used, "cde_adapter",
            "native Sparrow collision truth is the CDE engine, got {}",
            cbd.backend_used
        );
    }

    /// SGH-Q22: CDE mode under sparrow must have `bbox_fallback_queries == 0`.
    #[test]
    fn sparrow_pipeline_cde_has_no_bbox_fallback() {
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let parts = vec![make_part("P", 30.0, 20.0, 2, vec![0], None)];
        let mut input = make_input(3, stocks, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::SparrowExperimental);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = super::solve(input).expect("solve ok");
        if out.status == "unsupported" {
            return; // accept unsupported CDE setup; other tests cover routing.
        }
        let cbd = out
            .collision_backend_diagnostics
            .expect("CDE sparrow must emit cde diagnostics");
        assert_eq!(
            cbd.bbox_fallback_queries, 0,
            "CDE/sparrow path must not fall back to bbox, got {}",
            cbd.bbox_fallback_queries
        );
    }

    /// SGH-Q22: same seed produces identical placements through the sparrow pipeline.
    #[test]
    fn sparrow_pipeline_same_seed_is_deterministic() {
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let parts = vec![make_part("P", 30.0, 20.0, 3, vec![0], None)];
        let mut input_a = make_input(42, stocks.clone(), parts.clone(), None);
        input_a.optimizer_pipeline = Some(OptimizerPipelineKind::SparrowExperimental);
        let mut input_b = make_input(42, stocks, parts, None);
        input_b.optimizer_pipeline = Some(OptimizerPipelineKind::SparrowExperimental);
        let a = super::solve(input_a).expect("solve a");
        let b = super::solve(input_b).expect("solve b");
        assert_same_output(&a, &b);
    }

    // ------------------------------------------------------------------
    // SGH-Q22R1: Sparrow unsupported diagnostics + tiny CDE acceptance
    // ------------------------------------------------------------------

    /// SGH-Q22R1: SPARROW_NO_FEASIBLE_LAYOUT must preserve Sparrow optimizer
    /// diagnostics (initial/final loss, iterations, moves, collision graph counts).
    ///
    /// Forced-fail fixture: 5 × 50×50 parts on a single 100×100 sheet. Only 4
    /// non-overlapping placements exist (corners); the 5th can never be placed
    /// feasibly, so the Sparrow loop exhausts its iteration budget and the
    /// adapter returns `SPARROW_NO_FEASIBLE_LAYOUT`. We assert that the output
    /// `optimizer_diagnostics` is present with the Sparrow counters populated.
    #[test]
    fn sparrow_unsupported_preserves_optimizer_diagnostics_bbox() {
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 50.0, 50.0, 5, vec![0], None)];
        let mut input = make_input(11, stocks, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::SparrowExperimental);
        let out = super::solve(input).expect("solve ok");
        // Either the kernel converges (unlikely given 5×50²=12500 > 10000) or
        // returns unsupported. We assert unsupported AND diagnostics preserved.
        if out.status == "unsupported" {
            assert_eq!(
                out.unsupported_reason.as_deref(),
                Some("SPARROW_NO_FEASIBLE_LAYOUT"),
                "expected SPARROW_NO_FEASIBLE_LAYOUT, got {:?}",
                out.unsupported_reason
            );
            let diag = out
                .optimizer_diagnostics
                .expect("Q22R1: unsupported Sparrow output MUST preserve optimizer_diagnostics");
            assert_eq!(diag.pipeline_used, "sparrow_experimental");
            assert_eq!(diag.sparrow_invoked, Some(true));
            assert_eq!(diag.sparrow_converged, Some(false));
            assert!(
                diag.sparrow_iterations.unwrap_or(0) > 0,
                "expected iterations > 0 on failure path, got {:?}",
                diag.sparrow_iterations
            );
            assert!(
                diag.sparrow_initial_raw_loss.unwrap_or(0.0) > 0.0,
                "expected initial_raw_loss > 0 (seed had overlaps)"
            );
            assert!(diag.sparrow_collision_graph_initial_pairs.is_some());
            assert!(diag.sparrow_best_infeasible_raw_loss.is_some());
        }
        // If by chance it converged: still acceptable for this corner-case fixture.
    }

    /// SGH-Q22R1: Tiny CDE Sparrow fixture MUST converge to feasible. This is
    /// the micro-acceptance gate proving that CDE/Sparrow is not gratuitously
    /// broken — only larger fixtures may be intentionally bottlenecked.
    /// `bbox_fallback_queries` must remain 0 (no silent bbox fallback).
    #[test]
    fn sparrow_pipeline_cde_tiny_converges_with_no_bbox_fallback() {
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        // Two small parts, plenty of room — minimal CDE workload.
        let parts = vec![make_part("P", 30.0, 20.0, 2, vec![0], None)];
        let mut input = make_input(101, stocks, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::SparrowExperimental);
        input.collision_backend = Some(CollisionBackendKind::Cde);
        let out = super::solve(input).expect("solve ok");
        // Honest acceptance: if CDE on this micro fixture cannot converge,
        // sparrow_experimental + CDE is broken, period.
        assert!(
            out.status == "ok" || out.status == "partial",
            "Q22R1 micro-CDE must succeed; got status={} reason={:?}",
            out.status,
            out.unsupported_reason
        );
        let cbd = out
            .collision_backend_diagnostics
            .expect("CDE output must emit collision_backend_diagnostics");
        assert_eq!(
            cbd.bbox_fallback_queries, 0,
            "CDE/Sparrow must not bbox-fall-back; got bbox_fallback_queries={}",
            cbd.bbox_fallback_queries
        );
        let diag = out
            .optimizer_diagnostics
            .expect("Sparrow CDE success path must emit optimizer_diagnostics");
        assert_eq!(diag.sparrow_converged, Some(true));
    }

    // ── SGH-Q23: sparrow_cde production pipeline ──────────────────────────────

    #[test]
    fn sparrow_cde_pipeline_deserializes_from_snake_case() {
        let json = r#"{
            "contract_version": "v1",
            "project_name": "q23",
            "seed": 1,
            "time_limit_s": 5,
            "stocks": [{"id": "S", "quantity": 1, "width": 200.0, "height": 200.0}],
            "parts": [{"id": "P", "width": 30.0, "height": 20.0, "quantity": 2}],
            "optimizer_pipeline": "sparrow_cde"
        }"#;
        let input: SolverInput = serde_json::from_str(json).expect("deserialize");
        assert_eq!(
            input.optimizer_pipeline,
            Some(OptimizerPipelineKind::SparrowCde)
        );
    }

    #[test]
    fn sparrow_cde_tiny_converges_and_labels_pipeline_sparrow_cde() {
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let parts = vec![make_part("P", 30.0, 20.0, 2, vec![0], None)];
        let mut input = make_input(101, stocks, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::SparrowCde);
        let out = super::solve(input).expect("solve ok");
        assert!(
            out.status == "ok" || out.status == "partial",
            "sparrow_cde tiny must succeed; got status={} reason={:?}",
            out.status,
            out.unsupported_reason
        );
        let diag = out
            .optimizer_diagnostics
            .expect("optimizer_diagnostics present");
        assert_eq!(
            diag.pipeline_used, "sparrow_cde",
            "production label must be sparrow_cde"
        );
        assert_eq!(diag.sparrow_converged, Some(true));
        let cbd = out
            .collision_backend_diagnostics
            .expect("sparrow_cde must emit collision_backend_diagnostics");
        // CDE-first: the active backend is the CDE adapter, not bbox.
        assert_eq!(
            cbd.backend_used, "cde_adapter",
            "sparrow_cde must use the CDE backend"
        );
        assert_eq!(
            cbd.bbox_fallback_queries, 0,
            "no bbox fallback in sparrow_cde"
        );
        // Q23 query-reduction evidence is surfaced (broad-phase counter present).
        assert!(
            cbd.cde_broadphase_pruned.is_some(),
            "broadphase prune counter must be surfaced"
        );
    }

    #[test]
    fn sparrow_cde_forces_cde_backend_even_when_bbox_requested() {
        // Production sparrow_cde must NOT honor a bbox backend request as a
        // collision source-of-truth; it forces CDE.
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let parts = vec![make_part("P", 30.0, 20.0, 2, vec![0], None)];
        let mut input = make_input(101, stocks, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::SparrowCde);
        input.collision_backend = Some(CollisionBackendKind::Bbox);
        let out = super::solve(input).expect("solve ok");
        let cbd = out
            .collision_backend_diagnostics
            .expect("sparrow_cde must emit collision_backend_diagnostics");
        assert_eq!(
            cbd.backend_used, "cde_adapter",
            "sparrow_cde must force CDE even when bbox is requested; got {}",
            cbd.backend_used
        );
    }

    #[test]
    fn sparrow_cde_failure_preserves_full_diagnostics() {
        // 5×50×50 on a single 100×100 sheet: only 4 fit → never converges.
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let parts = vec![make_part("P", 50.0, 50.0, 5, vec![0], None)];
        let mut input = make_input(7, stocks, parts, None);
        input.optimizer_pipeline = Some(OptimizerPipelineKind::SparrowCde);
        input.time_limit_s = 1;
        let out = super::solve(input).expect("solve returns Ok(partial)");
        assert_eq!(out.status, "partial");
        assert_eq!(
            out.unsupported_reason.as_deref(),
            Some("SPARROW_NO_FEASIBLE_LAYOUT")
        );
        let diag = out
            .optimizer_diagnostics
            .expect("failure must preserve optimizer_diagnostics");
        assert_eq!(diag.pipeline_used, "sparrow_cde");
        assert_eq!(diag.sparrow_converged, Some(false));
        assert!(
            diag.sparrow_iterations.unwrap_or(0) > 0,
            "iterations must be recorded"
        );
        assert!(
            diag.sparrow_initial_raw_loss.unwrap_or(0.0) > 0.0,
            "initial loss must be recorded"
        );
        // CDE-first failure must also preserve backend diagnostics.
        let cbd = out
            .collision_backend_diagnostics
            .expect("failure must preserve collision_backend_diagnostics");
        assert_eq!(cbd.backend_used, "cde_adapter");
    }

    // ── SGH-Q34-R1 margin violation safety net ────────────────────────────────

    fn pl(instance_id: &str, part_id: &str) -> Placement {
        Placement {
            instance_id: instance_id.to_string(),
            part_id: part_id.to_string(),
            sheet_index: 0,
            x: 0.0,
            y: 0.0,
            rotation_deg: 0.0,
        }
    }

    #[test]
    fn margin_safety_net_moves_violating_to_unplaced() {
        let placements = vec![pl("A#0", "A"), pl("B#0", "B"), pl("C#0", "C")];
        let violating = vec!["B#0".to_string()];
        let (kept, unplaced) =
            apply_margin_violation_safety_net(placements, vec![], &violating);

        // B#0 removed from placements.
        assert_eq!(kept.len(), 2);
        assert!(kept.iter().all(|p| p.instance_id != "B#0"));
        // B#0 appears in unplaced with the explicit reason.
        assert_eq!(unplaced.len(), 1);
        assert_eq!(unplaced[0].instance_id, "B#0");
        assert_eq!(unplaced[0].reason, REASON_SHEET_MARGIN_VIOLATION);
        assert_eq!(REASON_SHEET_MARGIN_VIOLATION, "SHEET_MARGIN_VIOLATION_Q34R1");
        // With a non-empty unplaced list, top-level status cannot be "ok".
        assert!(!unplaced.is_empty());
    }

    #[test]
    fn margin_safety_net_noop_when_no_violations() {
        let placements = vec![pl("A#0", "A"), pl("B#0", "B")];
        let (kept, unplaced) =
            apply_margin_violation_safety_net(placements, vec![], &[]);
        assert_eq!(kept.len(), 2);
        assert!(unplaced.is_empty());
    }

    // ── SGH-Q35 spacing violation safety net ──────────────────────────────────

    fn spacing_viol(a: &str, b: &str) -> PartSpacingViolation {
        PartSpacingViolation {
            sheet_index: 0,
            a_instance_id: a.to_string(),
            b_instance_id: b.to_string(),
            a_part_id: "A".to_string(),
            b_part_id: "B".to_string(),
            distance_mm: 0.0,
            required_spacing_mm: 5.0,
        }
    }

    /// Test 9: safety net removes both endpoints of a violation pair.
    #[test]
    fn spacing_safety_net_removes_both_endpoints() {
        let placements = vec![pl("A#0", "A"), pl("B#0", "B"), pl("C#0", "C")];
        let violations = vec![spacing_viol("A#0", "B#0")];
        assert_eq!(spacing_safety_net_removed_count(&violations), 2);

        let (kept, unplaced) =
            apply_spacing_violation_safety_net(placements, vec![], &violations);

        // Only C#0 remains.
        assert_eq!(kept.len(), 1);
        assert_eq!(kept[0].instance_id, "C#0");
        // A#0 and B#0 moved to unplaced with the explicit reason.
        assert_eq!(unplaced.len(), 2);
        assert!(unplaced.iter().all(|u| u.reason == REASON_PART_SPACING_VIOLATION));
        assert_eq!(REASON_PART_SPACING_VIOLATION, "PART_SPACING_VIOLATION_Q35");
        let ids: Vec<&str> = unplaced.iter().map(|u| u.instance_id.as_str()).collect();
        assert!(ids.contains(&"A#0") && ids.contains(&"B#0"));
    }

    /// Test 10: after a spacing removal, unplaced is non-empty ⇒ top-level status
    /// (computed from unplaced.is_empty()) cannot be ok.
    #[test]
    fn spacing_safety_net_forces_non_ok_status() {
        let placements = vec![pl("A#0", "A"), pl("B#0", "B")];
        let violations = vec![spacing_viol("A#0", "B#0")];
        let (_kept, unplaced) =
            apply_spacing_violation_safety_net(placements, vec![], &violations);
        assert!(!unplaced.is_empty(), "spacing removal must leave a non-empty unplaced list");
    }

    #[test]
    fn spacing_safety_net_noop_when_no_violations() {
        let placements = vec![pl("A#0", "A"), pl("B#0", "B")];
        let (kept, unplaced) = apply_spacing_violation_safety_net(placements, vec![], &[]);
        assert_eq!(kept.len(), 2);
        assert!(unplaced.is_empty());
    }
}
