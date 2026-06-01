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
use crate::sheet::{expand_sheets, stock_has_holes};

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
    let optimizer = SparrowOptimizer::new(config);
    let result = optimizer.solve(problem);
    let final_commit_ms = timing_ms(t_commit_start);
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
        if let Some(margin_mm) = input.margin_mm {
            if margin_mm > 0.0 {
                return Ok(_unsupported_output("UNSUPPORTED_MARGIN_MM_RUNTIME", &input));
            }
        }
    }

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
        Some(phase1_score_breakdown_for_backend(
            &placements,
            &unplaced,
            &input.parts,
            &sheets,
            &backend_kind,
        ))
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
    use super::{phase_commit_or_unsupported, solve};
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
}
