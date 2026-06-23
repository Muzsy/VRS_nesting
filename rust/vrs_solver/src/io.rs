use serde::{Deserialize, Serialize, Serializer};

use crate::item::Part;
use crate::rotation_policy::RotationPolicyKind;
use crate::sheet::Stock;

/// Serialize a rotation_deg f64 as an integer when it is a whole number,
/// to preserve backward-compatible JSON output (90 not 90.0).
fn serialize_rotation_deg<S: Serializer>(val: &f64, s: S) -> Result<S::Ok, S::Error> {
    let rounded = val.round();
    if (val - rounded).abs() < 1e-9 {
        s.serialize_i64(rounded as i64)
    } else {
        s.serialize_f64(*val)
    }
}

#[derive(Debug, Deserialize)]
pub struct SolverInput {
    pub contract_version: String,
    pub project_name: String,
    pub seed: i64,
    pub time_limit_s: i64,
    pub stocks: Vec<Stock>,
    pub parts: Vec<Part>,
    #[serde(default)]
    pub solver_profile: Option<String>,
    /// Parsed but not applied at runtime: Rust solver does not shrink placements by margin.
    /// Non-zero margin_mm with Phase 1 profile returns UNSUPPORTED_MARGIN_MM_RUNTIME.
    /// Python exact validator applies margin_mm independently (JG-05 deviation).
    #[serde(default)]
    pub margin_mm: Option<f64>,
    /// SGH-Q33: minimum part-to-part separation (mm). Defaults to margin_mm when absent.
    /// Centralized in TechnologyClearancePolicy — diagnostic only, not applied as geometry offset.
    #[serde(default)]
    pub spacing_mm: Option<f64>,
    /// SGH-Q33: laser / tool kerf width (mm). Defaults to 0.0 when absent.
    /// Centralized in TechnologyClearancePolicy — diagnostic only, not applied as geometry offset.
    #[serde(default)]
    pub kerf_mm: Option<f64>,
    /// Global rotation policy default. Applied when a part has no part-level policy
    /// and no allowed_rotations_deg. Optional; backward-compatible (default: Orthogonal).
    #[serde(default)]
    pub rotation_policy: Option<RotationPolicyKind>,
    /// Optional production optimizer routing. Missing value preserves the legacy
    /// Phase1 MultiSheetManager path.
    #[serde(default)]
    pub optimizer_pipeline: Option<OptimizerPipelineKind>,
    /// Optional collision backend policy. Missing value defaults to Bbox (backward-compatible).
    /// Explicit jagua_polygon_exact: no silent downgrade on invalid geometry.
    /// Explicit cde: genuine CDE final commit supported; opt-in; outer-only in main solver.
    /// CDE per-call/session performance is not addressed here.
    #[serde(default)]
    pub collision_backend: Option<CollisionBackendKind>,
}

#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum OptimizerPipelineKind {
    LegacyMultisheet,
    PhaseOptimizer,
    /// SGH-Q22: Sparrow-style separation kernel with explicit infeasible state.
    SparrowExperimental,
    /// SGH-Q23: production Sparrow path. CDE-first by contract — forces the CDE
    /// geometry backend, forbids LBF/finite-candidate fallback, and never falls
    /// back to a legacy solver. A failure returns unsupported/partial with full
    /// diagnostics preserved. Legacy pipelines remain explicit opt-in only.
    SparrowCde,
    /// SGH-Q32: Sparrow-native finite-stock heterogeneous multisheet manager.
    /// CDE-first by contract. Manages a pool of available sheets (heterogeneous
    /// rectangles allowed), generates candidate sheet subsets, and runs the
    /// native Sparrow core on each subset. Returns the best valid incumbent:
    /// full feasible (all placed, final_pairs=0, boundary_violations=0) or a
    /// collision-free partial with explicit STOCK_EXHAUSTED_PARTIAL/
    /// INSUFFICIENT_STOCK_CAPACITY unplaced reasons when stock is exhausted.
    /// Never falls back to legacy multisheet manager or Python wrapper.
    SparrowCdeMultisheet,
}

impl Default for OptimizerPipelineKind {
    fn default() -> Self {
        Self::LegacyMultisheet
    }
}

/// Q10: explicit collision backend selection. Missing value defaults to Bbox (backward-compatible).
#[derive(Debug, Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum CollisionBackendKind {
    Bbox,
    JaguaPolygonExact,
    Cde,
}

impl Default for CollisionBackendKind {
    fn default() -> Self {
        Self::Bbox
    }
}

#[derive(Debug, Serialize)]
pub struct SolverOutput {
    pub contract_version: String,
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub unsupported_reason: Option<String>,
    pub placements: Vec<Placement>,
    pub unplaced: Vec<Unplaced>,
    pub metrics: Metrics,
    /// Score breakdown for Phase1 profile (JG-19). Absent for legacy profiles.
    /// Adding this optional field is non-breaking: existing callers ignore unknown keys.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub score_breakdown: Option<ScoreBreakdownOutput>,
    /// Optional optimizer routing diagnostics for explicit production pipeline audits.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub optimizer_diagnostics: Option<OptimizerDiagnosticsOutput>,
    /// Optional collision backend diagnostics (Q10).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub collision_backend_diagnostics: Option<CollisionBackendDiagnosticsOutput>,
}

/// Auditálható score breakdown in the JSON output (JG-19).
/// Only present when solver_profile=jagua_optimizer_phase1_outer_only.
#[derive(Debug, Serialize)]
pub struct ScoreBreakdownOutput {
    pub total_cost: f64,
    pub placed_area_contribution: f64,
    pub unplaced_contribution: f64,
    /// Sheet cost contribution = sheet_cost_total * sheet_count_penalty_per_sheet.
    pub sheet_cost_contribution: f64,
    /// Sum of cost_per_use for all used sheet slots (default 1.0/sheet).
    pub sheet_cost_total: f64,
    /// placed_area / total usable area of used sheets. 0.0 if no sheets used.
    pub usable_area_utilization: f64,
    pub overlap_contribution: f64,
    pub boundary_contribution: f64,
    pub compactness_contribution: f64,
}

/// SGH-Q44 schema version for the per-attempt multisheet diagnostics array.
/// Bump when the field set of `SparrowMsAttemptDiagnostics` changes.
pub const SPARROW_MS_ATTEMPT_DIAGNOSTICS_SCHEMA_VERSION: u32 = 1;

/// SGH-Q44: per-attempt diagnostics for one finite-stock multisheet subset attempt.
///
/// One record is emitted for every `run_core_attempt` invocation inside
/// `run_finite_stock_multisheet`. All `cde_*_delta` and `collision_severity_*_delta`
/// fields are computed by snapshotting the thread-local CDE observability counters
/// immediately before and after the attempt (core solve + sanitize + scoring), so the
/// per-attempt deltas sum to the aggregated `collision_backend_diagnostics` counters
/// (minus the small residual spent in the post-loop margin/spacing validators, which is
/// reported separately by the Q44 extractor). Purely additive instrumentation — it does
/// not change any solver decision.
#[derive(Debug, Serialize, Clone, Default)]
pub struct SparrowMsAttemptDiagnostics {
    // ── identity / schedule ──────────────────────────────────────────────────
    pub attempt_index: usize,
    pub subset_ord: usize,
    pub subset_indices_original: Vec<usize>,
    pub subset_size: usize,
    pub subset_signature: String,
    pub is_full_pool: bool,
    pub is_second_to_last: bool,
    pub allocated_time_limit_s: f64,
    pub actual_runtime_ms: f64,
    pub remaining_budget_before_s: f64,
    pub remaining_budget_after_s: f64,
    pub deadline_hit_after_attempt: bool,
    // ── core outcome ─────────────────────────────────────────────────────────
    pub core_invoked: bool,
    pub core_feasible: bool,
    pub core_status: String,
    pub core_final_pairs: usize,
    pub core_boundary_violations: usize,
    // ── sanitize ─────────────────────────────────────────────────────────────
    pub placed_before_sanitize: usize,
    pub unplaced_before_sanitize: usize,
    pub placed_after_sanitize: usize,
    pub unplaced_after_sanitize: usize,
    pub sanitized: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sanitize_reason: Option<String>,
    // ── candidate / incumbent ────────────────────────────────────────────────
    pub used_sheet_indices_original: Vec<usize>,
    pub used_sheet_count: usize,
    pub used_sheet_area: f64,
    pub placed_part_area: f64,
    pub utilization_pct: f64,
    pub candidate_score: f64,
    pub became_incumbent: bool,
    pub incumbent_reason: String,
    pub stop_reason: String,
    // ── sparrow / search activity (from this attempt's SparrowDiagnostics) ────
    pub sparrow_iterations: usize,
    pub sparrow_moves_attempted: usize,
    pub sparrow_moves_accepted: usize,
    pub sparrow_rollbacks: usize,
    pub sparrow_search_position_calls: usize,
    pub sparrow_search_position_samples: usize,
    pub search_position_global_samples_evaluated: usize,
    pub search_position_focused_samples_evaluated: usize,
    pub search_position_coord_descent_steps: usize,
    pub sparrow_graph_full_rebuilds: usize,
    pub sparrow_graph_incremental_updates: usize,
    pub sparrow_graph_edges_recomputed: usize,
    pub sparrow_graph_edges_pruned_by_broadphase: usize,
    pub sparrow_collision_graph_initial_pairs: usize,
    pub sparrow_collision_graph_final_pairs: usize,
    pub sparrow_boundary_violations_initial: usize,
    pub sparrow_boundary_violations_final: usize,
    pub sparrow_initial_raw_loss: f64,
    pub sparrow_initial_weighted_loss: f64,
    pub sparrow_final_raw_loss: f64,
    pub sparrow_final_weighted_loss: f64,
    pub sparrow_best_infeasible_raw_loss: f64,
    pub sparrow_best_infeasible_weighted_loss: f64,
    pub sparrow_exploration_best_feasible_found: bool,
    // ── per-attempt CDE counter deltas (snapshot after − before) ─────────────
    pub cde_engine_builds_delta: usize,
    pub cde_batch_candidate_queries_delta: usize,
    pub cde_batch_engine_builds_delta: usize,
    pub cde_batch_hazards_registered_delta: usize,
    pub cde_batch_collisions_returned_delta: usize,
    pub cde_candidate_session_builds_delta: usize,
    pub cde_candidate_session_reuses_delta: usize,
    pub collision_severity_pair_queries_delta: usize,
    pub collision_severity_boundary_queries_delta: usize,
}

/// SGH-Q45: diagnostics for the coroush-style BPP sheet-reduction multisheet path.
/// One record per solve when the BPP path runs. Field names are stable and documented
/// in `codex/reports/egyedi_solver/sgh_q45_bpp_full276_min_sheets.md`.
#[derive(Debug, Serialize, Clone, Default)]
pub struct BppReductionDiagnostics {
    pub bpp_reduction_active: bool,
    pub bpp_initial_sheet_count: usize,
    pub bpp_final_sheet_count: usize,
    pub bpp_area_lower_bound: usize,
    pub bpp_elimination_attempts: usize,
    pub bpp_elimination_successes: usize,
    pub bpp_elimination_failures: usize,
    pub bpp_candidate_sheets_tried: usize,
    pub bpp_failed_candidate_sheets: usize,
    pub bpp_displaced_items_total: usize,
    pub bpp_displaced_lbf_clear_count: usize,
    pub bpp_displaced_fallback_count: usize,
    pub bpp_receiving_sheet_count_total: usize,
    pub bpp_separator_calls: usize,
    pub bpp_transfer_attempts: usize,
    pub bpp_transfer_successes: usize,
    pub bpp_swap_attempts: usize,
    pub bpp_swap_successes: usize,
    pub bpp_compaction_calls: usize,
    pub bpp_compaction_successes: usize,
    pub bpp_perturbation_attempts: usize,
    pub bpp_perturbation_successes: usize,
    pub bpp_incumbent_updates: usize,
    pub bpp_restore_count: usize,
    pub bpp_runtime_ms: f64,
    /// Minimality classification: AREA_LOWER_BOUND_MATCHED | GAP_TO_AREA_LOWER_BOUND |
    /// BEST_FOUND_NOT_PROVEN_MINIMAL.
    pub bpp_minimality_status: String,
    pub bpp_gap_to_area_lower_bound: usize,
    // ── SGH-Q46 M2: gravity / bottom-left compaction post-pass ───────────────
    pub bpp_gravity_compaction_applied: bool,
    pub bpp_gravity_compaction_sweeps: usize,
    pub bpp_gravity_moved_total_mm: f64,
    // ── SGH-Q46 M3: fixed-sheet region-compression (Sparrow Alg.13 adaptation) ─
    pub bpp_region_compression_applied: bool,
    pub bpp_region_compression_attempts: usize,
    pub bpp_region_compression_accepts: usize,
    pub bpp_region_compression_freed_area_mm2: f64,
    // ── SGH-Q48: interlock-aware density compaction (opt-in VRS_BPP_DENSITY_COMPACT) ──
    pub bpp_density_compaction_applied: bool,
    pub bpp_density_moves_accepted: usize,
    /// Clear candidates whose bbox overlapped a neighbour (interlock candidates) — generated.
    pub bpp_interlock_candidates_generated: usize,
    /// Accepted density moves whose placement is bbox-overlapping a neighbour (interlock kept).
    pub bpp_interlock_candidates_accepted: usize,
    // ── SGH-Q49: density-pass budget allocation ──────────────────────────────
    /// Wall time (ms) spent in the BPP sheet-reduction loop (before the density pass).
    pub bpp_reduction_time_ms: f64,
    /// Wall time (ms) spent in the density compaction pass.
    pub bpp_density_time_ms: f64,
    /// Density sweeps completed (multi-sweep, T3).
    pub bpp_density_sweeps: usize,
    /// Distinct part placements re-evaluated by the density pass (T3).
    pub bpp_density_parts_processed: usize,
    // ── SGH-Q50: density-guided LNS sheet-drop pass (opt-in VRS_BPP_LNS) ──────
    pub bpp_lns_applied: bool,
    /// Sheet-elimination attempts (one per least-utilized sheet tried).
    pub bpp_lns_attempts: usize,
    /// Sheets actually dropped by the LNS (the headline metric).
    pub bpp_lns_sheets_dropped: usize,
    /// Ruined parts successfully re-inserted onto other sheets.
    pub bpp_lns_parts_reinserted: usize,
    /// Perturbed restarts consumed across all attempts.
    pub bpp_lns_restarts: usize,
    // ── SGH-Q53B: feature candidate diagnostics ─────────────────────────────
    pub bpp_feature_candidates_generated: usize,
    pub bpp_feature_candidates_accepted: usize,
    pub bpp_bbox_corner_candidates_generated: usize,
    pub bpp_bbox_corner_candidates_accepted: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bpp_accepted_feature_pair_type: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bpp_feature_refine_seed_rotation_deg: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bpp_feature_refine_refined_rotation_deg: Option<f64>,
    pub bpp_feature_refine_iterations: usize,
    pub bpp_feature_refine_successes: usize,
    pub bpp_feature_refine_failures: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bpp_feature_refine_rejection_reason: Option<String>,
    pub bpp_critical_feature_admission_attempts: usize,
    pub bpp_critical_feature_admission_successes: usize,
    pub bpp_critical_feature_admission_failures: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bpp_critical_phase_close_reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bpp_critical_candidate_rejection_summary: Option<String>,
    // ── SGH-Q51: critical-aware constructive sheet builder (opt-in VRS_SHEET_BUILDER) ──
    pub bpp_sheet_builder_applied: bool,
    /// Critical parts admitted anchor-first during construction.
    pub bpp_critical_admitted: usize,
    /// Critical admission failures (deferred to a later sheet).
    pub bpp_critical_deferred: usize,
    /// Sheets opened by the constructive builder.
    pub bpp_sheets_opened: usize,
    /// Max critical parts admitted onto a single sheet (the headline: 3 big curved per sheet?).
    pub bpp_max_critical_per_sheet: usize,
    // ── SGH-Q54A: skeleton role assignment (opt-in VRS_SHEET_BUILDER_SKELETON) ──
    /// Critical parts admitted in each skeleton role (anchor / interlock / band-insert).
    pub bpp_skeleton_anchor_count: usize,
    pub bpp_skeleton_interlock_count: usize,
    pub bpp_skeleton_bandinsert_count: usize,
    // ── SGH-Q55B: role-routed candidate generation (per-role candidate counts) ──
    pub bpp_role_anchor_generated: usize,
    pub bpp_role_anchor_accepted: usize,
    pub bpp_role_interlock_generated: usize,
    pub bpp_role_interlock_accepted: usize,
    pub bpp_role_band_insert_generated: usize,
    pub bpp_role_band_insert_accepted: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bpp_role_candidate_rejection_summary: Option<String>,
    // ── SGH-Q55C: band-insert (third big part into the preserved free-space slot) ──
    pub bpp_band_slot_found: bool,
    // ── SGH-Q61: Q56–Q60 module consumption in the real critical-admission path ──
    // Q56C SheetEdgePlacementCatalog (Anchor role)
    #[serde(default)]
    pub bpp_q61_anchor_catalog_consulted: bool,
    #[serde(default)]
    pub bpp_q61_anchor_catalog_candidates_generated: usize,
    #[serde(default)]
    pub bpp_q61_anchor_catalog_accepted: usize,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub bpp_q61_accepted_anchor_source: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub bpp_q61_accepted_anchor_secondary_policy: Option<String>,
    // Q57B PairCompatibilityIndex / interlock_pair (Interlock role)
    #[serde(default)]
    pub bpp_q61_pair_index_consulted: bool,
    #[serde(default)]
    pub bpp_q61_pair_candidates_generated: usize,
    #[serde(default)]
    pub bpp_q61_pair_candidates_accepted: usize,
    #[serde(default)]
    pub bpp_q61_interlock_fallback_to_neighbour: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub bpp_q61_pair_rejection_summary: Option<String>,
    // Q59 true-extreme slot-edge BandInsert
    #[serde(default)]
    pub bpp_q61_band_insert_true_extreme_consulted: bool,
    #[serde(default)]
    pub bpp_q61_slot_edge_candidates_generated: usize,
    #[serde(default)]
    pub bpp_q61_slot_edge_candidates_accepted: usize,
    #[serde(default)]
    pub bpp_q61_fallback_to_bbox_band_insert: bool,
    // Q58B best-partial preservation
    #[serde(default)]
    pub bpp_q61_best_partial_tracker_enabled: bool,
    #[serde(default)]
    pub bpp_q61_best_partial_max_critical_count: usize,
    #[serde(default)]
    pub bpp_q61_best_partial_downgrades_rejected: usize,
    // Q60 simultaneous critical admission
    #[serde(default)]
    pub bpp_q61_simultaneous_critical_consulted: bool,
    #[serde(default)]
    pub bpp_q61_simultaneous_group_attempts: usize,
    #[serde(default)]
    pub bpp_q61_previous_group_parts_moved: bool,
}

/// SGH-Q47: per-part-type shape-profile decision diagnostics. One record per unique `part_id`,
/// emitted in `priority_rank` order. Proves the profile actually drives ordering/budget and shows
/// placement success per type. Decision-support evidence only — no collision/rotation semantics.
#[derive(Debug, Serialize, Clone)]
pub struct ShapeProfileDiagnostics {
    pub part_id: String,
    /// Non-exclusive class labels (e.g. ["large_anchor","concave_like","high_interlock_potential"]).
    pub classes: Vec<String>,
    pub priority_score: f64,
    /// 0-based rank among part types by `priority_score` (desc); 0 = placed earliest.
    pub priority_rank: usize,
    pub search_budget_multiplier: f64,
    pub declared_quantity: usize,
    /// Expanded instances of this type that entered the solver.
    pub instance_count: usize,
    /// Instances of this type present in the final emitted layout.
    pub placed_count: usize,
    pub fill_ratio: f64,
    pub convexity_ratio: f64,
    pub aspect_ratio: f64,
    pub sheet_area_ratio: f64,
    pub contour_vertex_count: usize,
    pub contour_edge_count: usize,
    pub dominant_edge_count: usize,
    pub extreme_point_count: usize,
    pub concave_vertex_count: usize,
    pub concave_zone_count: usize,
    pub protrusion_candidate_count: usize,
    pub sheet_alignment_angle_count: usize,
    pub contour_feature_total_count: usize,
    pub dominant_alignment_angles_deg: Vec<f64>,
}

#[derive(Debug, Serialize)]
pub struct OptimizerDiagnosticsOutput {
    pub pipeline_used: String,
    pub phase_optimizer_invoked: bool,
    pub exploration_iterations: usize,
    pub compression_iterations: usize,
    pub bpp_attempts: usize,
    /// Q20: rotation refinement diagnostics (compression phase, Continuous policy only).
    pub rotation_refinement_enabled: bool,
    pub rotation_refinement_attempts: usize,
    pub rotation_refinement_accepts: usize,
    pub rotation_refinement_rejections: usize,
    /// Best score improvement from a single accepted refinement. 0.0 if no accepts.
    pub rotation_refinement_best_delta: f64,
    /// Q20R: search_position diagnostics (accumulated across exploration + compression).
    pub search_position_calls: usize,
    pub search_position_global_samples_evaluated: usize,
    pub search_position_focused_samples_evaluated: usize,
    pub search_position_samples_unsupported: usize,
    pub search_position_refined_samples: usize,
    pub search_position_coord_descent_steps: usize,
    pub search_position_lbf_fallback_used: usize,
    /// 0.0 when no calls were made (sentinel f64::MAX → 0.0 in adapter).
    pub search_position_best_eval: f64,
    /// Q21: collision severity engine diagnostics.
    pub collision_severity_backend: String,
    pub collision_severity_enabled: bool,
    pub collision_severity_pair_queries: usize,
    pub collision_severity_boundary_queries: usize,
    pub collision_severity_probe_queries: usize,
    pub collision_severity_backend_confirmed_collisions: usize,
    pub collision_severity_backend_confirmed_no_collisions: usize,
    pub collision_severity_unsupported_queries: usize,
    pub collision_severity_bbox_proxy_uses: usize,
    /// Q21R1: extended severity diagnostics.
    pub collision_severity_probe_pair_queries: usize,
    pub collision_severity_probe_boundary_queries: usize,
    pub collision_severity_probe_resolved: usize,
    pub collision_severity_probe_unresolved: usize,
    pub collision_severity_probe_unsupported: usize,
    pub collision_severity_min_resolution_mm: f64,
    pub collision_severity_max_resolution_mm: f64,
    pub collision_severity_avg_resolution_mm: f64,
    /// Per-phase wall-clock timing. Only populated when VRS_CDE_OBSERVABILITY_TIMING=1.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub phase_optimizer_exploration_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub phase_optimizer_compression_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub phase_optimizer_bpp_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub phase_optimizer_final_commit_ms: Option<f64>,
    /// SGH-Q22 Sparrow kernel diagnostics. Populated only for sparrow_experimental.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_invoked: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_seed_placements: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_seed_unplaced: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_initial_raw_loss: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_initial_weighted_loss: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_final_raw_loss: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_final_weighted_loss: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_best_infeasible_raw_loss: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_best_infeasible_weighted_loss: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_iterations: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_moves_attempted: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_moves_accepted: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_rollbacks: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_gls_weight_updates: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_converged: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_collision_graph_initial_pairs: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_collision_graph_final_pairs: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_boundary_violations_initial: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_boundary_violations_final: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_search_position_calls: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_search_position_samples: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_severity_pair_queries: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_severity_boundary_queries: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_severity_probe_queries: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_lbf_fallback_used: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_workers: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_worker_passes: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_worker_candidates_evaluated: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_worker_commits: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_worker_rollbacks: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_worker_best_loss: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_multi_target_items_attempted: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_multi_target_items_accepted: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_multi_target_items_rejected: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_topk_target_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_graph_full_rebuilds: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_graph_incremental_updates: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_graph_edges_recomputed: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_graph_edges_pruned_by_broadphase: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_graph_debug_rebuilds: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_graph_debug_rebuild_mismatches: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_exploration_restarts: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_exploration_seed_strategies: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_exploration_disruptions: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_exploration_stagnation_events: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_exploration_best_raw_loss: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_exploration_best_weighted_loss: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_exploration_best_feasible_found: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_compression_passes: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_compression_candidates_evaluated: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_compression_accepts: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_compression_rejects: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_fixed_sheet_objective_before: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_fixed_sheet_objective_after: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_fixed_sheet_objective_delta: Option<f64>,
    /// SGH-Q24: production loss-model identity used for the search (e.g.
    /// `CdeSeparationLoss`). For production `sparrow_cde` this must NOT be
    /// `BboxAreaLoss` — the authoritative search loss is the CDE batch
    /// separation distance, never bbox area.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub loss_model_used: Option<String>,
    /// SGH-Q24: true only if a bbox-area proxy is the PRIMARY production loss.
    /// Must be `false` for production `sparrow_cde`.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub loss_bbox_proxy_used_as_primary: Option<bool>,
    // ── SGH-Q24R5 native-model cutover proof flags ──────────────────────────
    /// True when production `sparrow_cde` ran on the native Sparrow model
    /// (SparrowProblem/Layout/Solution/Optimizer), not the old VRS core.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_native_model_active: Option<bool>,
    /// True when the native `SparrowCollisionTracker` was the production tracker.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_native_tracker_active: Option<bool>,
    /// Must be false: the old VRS core (WorkingLayout/VrsCollisionTracker) was not used.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_old_core_used: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_native_problem_instances: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_native_tracker_full_rebuilds: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_native_tracker_incremental_updates: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_dense_guard_used: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_dense_real_run: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_dense_partial_reason: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_dense_validated_placements: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_dense_unresolved_instances: Option<Vec<String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_dense_final_validation_ran: Option<bool>,
    // ── SGH-Q29 CDE hotspot profiler fields (present only when SGH_Q29_CDE_PROFILE=1) ──
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_profiling_enabled: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_profile_search_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_profile_session_build_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_profile_deregister_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_profile_candidate_transform_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_profile_cde_query_collect_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_profile_hazard_loss_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_profile_boundary_check_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_profile_broadphase_reject_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_profile_early_termination_count: Option<usize>,
    // ── SGH-Q30 reusable search profiler (present only when SGH_Q30_SEARCH_PROFILE=1) ──
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_profile_enabled: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_native_search_calls: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_evaluate_sample_calls: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_candidates_evaluated: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_global_samples_generated: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_focused_samples_generated: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_coord_descent_runs: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_coord_descent_steps: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_best_samples_insert_attempts: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_best_samples_inserted: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_best_samples_dedup_rejects: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_early_termination_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_broadphase_reject_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_search_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_sample_generation_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_best_samples_insert_dedup_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_coord_descent_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_evaluate_sample_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_candidate_transform_prepare_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_cde_query_collect_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_boundary_check_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_session_build_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30_deregister_reregister_ms: Option<f64>,
    // ── SGH-Q30-R1 exclusive timing tree (present only when SGH_Q30_R1_EXCLUSIVE_PROFILE=1) ──
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_exclusive_enabled: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_prepare_base_shape_native_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_fixed_shapes_clone_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_sheet_order_build_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_best_samples_best_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_best_samples_clone_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_coord_descent_ask_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_coord_descent_tell_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_search_accounted_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_search_unaccounted_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_search_unaccounted_ratio_pct: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_total_solver_runtime_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_adapter_solve_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_sparrow_optimizer_solve_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_seed_lbf_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_tracker_initial_build_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_exploration_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_separator_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_separator_iteration_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_worker_competition_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_worker_pass_total_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_tracker_final_validation_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_output_mapping_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_other_solver_unaccounted_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_other_solver_unaccounted_ratio_pct: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_evaluate_sample_calls_from_focused: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_evaluate_sample_calls_from_global: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_evaluate_sample_calls_from_coord_descent: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_best_samples_best_calls: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_best_samples_clone_calls: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_coord_descent_ask_calls: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_coord_descent_tell_calls: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_sheet_loop_iterations: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_worker_passes: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_worker_candidates_evaluated: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q30r1_worker_candidates_accepted: Option<usize>,
    // ── Q31 base-shape cache diagnostics ─────────────────────────────────────
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q31_base_shape_cache_build_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q31_base_shape_cache_hits: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q31_base_shape_cache_misses: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q31_base_shape_cache_unique_parts: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q31_base_shape_cache_reused_instances: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q31_prepare_base_shape_native_hotpath_calls: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q31_prepare_base_shape_native_hotpath_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q31_tracker_transform_from_base_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q31_search_base_shape_cache_hits: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_q31_lbf_base_shape_cache_hits: Option<usize>,
    // ── SGH-Q32 finite-stock multisheet manager diagnostics ──────────────────
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_active: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_status: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_available_sheet_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_used_sheet_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_used_sheet_indices: Option<Vec<usize>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_used_sheet_area: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_placed_part_area: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_utilization_pct: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_total_instances: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_placed_instances: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_unplaced_instances: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_attempts: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_candidate_subsets: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_best_full_solution_found: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_stock_exhausted: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_final_pairs: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_boundary_violations: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_runtime_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_requested_time_limit_s: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_deadline_hit: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_best_score: Option<f64>,
    // ── SGH-Q44 per-attempt multisheet diagnostics ───────────────────────────
    /// One entry per `run_core_attempt`. Stable field name and schema documented
    /// in `codex/reports/egyedi_solver/sgh_q44_per_attempt_multisheet_diagnostics.md`.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_attempt_diagnostics: Option<Vec<SparrowMsAttemptDiagnostics>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_attempt_diagnostics_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub sparrow_ms_attempt_diagnostics_schema_version: Option<u32>,
    // ── SGH-Q45 BPP sheet-reduction multisheet diagnostics ───────────────────
    /// Present when the coroush-style BPP sheet-reduction path produced the layout.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bpp_reduction: Option<BppReductionDiagnostics>,
    // ── SGH-Q47 shape-profile priority-layer decision diagnostics ────────────
    /// One record per unique part type (priority_rank order). Present when the BPP path ran.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub shape_profiles: Option<Vec<ShapeProfileDiagnostics>>,
    // ── SGH-Q33 technology clearance policy diagnostics ──────────────────────
    /// True when TechnologyClearancePolicy was active for this run.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_policy_active: Option<bool>,
    // ── SGH-Q34 sheet margin enforcement diagnostics ─────────────────────────
    /// True when effective_sheet_margin_mm() > 0 and was applied to solver sheets.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_sheet_margin_applied: Option<bool>,
    /// Number of expanded solver sheets that received margin shrink.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_margin_applied_sheet_count: Option<usize>,
    /// Sum of margin-shrunk usable areas of all used sheets (mm²).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_margin_usable_sheet_area: Option<f64>,
    /// Sum of original physical areas of all used sheets (mm²).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_margin_physical_used_sheet_area: Option<f64>,
    /// Count of final placements whose rotated bbox violates the margin-inset boundary.
    /// Must be 0 for a valid ok output.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_margin_violation_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_margin_mm: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_mm: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_kerf_mm: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_effective_sheet_margin_mm: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_effective_part_spacing_mm: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_effective_kerf_mm: Option<f64>,
    // ── SGH-Q35 part-part spacing final validator diagnostics ────────────────
    /// True when effective_part_spacing_mm() > 0 (spacing gate active).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_part_spacing_applied: Option<bool>,
    /// effective_part_spacing_mm() (kerf_mm is NOT included).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_part_spacing_mm: Option<f64>,
    /// Number of part-part spacing violation pairs found by the final validator.
    /// Must be 0 for a valid ok output.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_violation_count: Option<usize>,
    /// Number of unique placements removed by the spacing safety net.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_safety_net_removed_count: Option<usize>,
    // ── SGH-Q36 spacing-aware solver geometry diagnostics ────────────────────
    /// True when the solver used spacing-expanded part-part collision geometry.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_geometry_applied: Option<bool>,
    /// The half-spacing outward offset applied to part contours (`spacing_mm / 2`).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_mm: Option<f64>,
    /// Unique parts for which a spacing-expanded base shape was built.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_part_count: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_cache_hits: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_cache_misses: Option<usize>,
    /// Instances whose spacing offset could not be built (UNSUPPORTED_SPACING_OFFSET_Q36).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_failure_count: Option<usize>,
    /// Always true: sheet boundary/container checks use ORIGINAL geometry.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_boundary_uses_original_geometry: Option<bool>,
    /// Always true: output/export uses ORIGINAL geometry.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_output_uses_original_geometry: Option<bool>,
    // ── SGH-Q37 measurement-hardening timing / inventory diagnostics ─────────
    /// Wall-time (ms) building the spacing-expanded base-shape cache.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_build_ms: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_avg_ms_per_part: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_max_ms_per_part: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_input_vertex_count_total: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_output_vertex_count_total: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_area_ratio_avg: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_offset_area_ratio_max: Option<f64>,
    /// Wall-time (ms) of the Q34-R1 margin final validator.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_margin_final_validator_ms: Option<f64>,
    /// Wall-time (ms) of the Q35 spacing final validator.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_spacing_final_validator_ms: Option<f64>,
    /// Wall-time (ms) applying the margin + spacing safety nets + result recompute.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_safety_net_ms: Option<f64>,
    /// SGH-Q40/Q41: the unified single-geometry margin/spacing model is active (spacing is baked
    /// into the part offset geometry and margin into the signed sheet inset; the inner solver runs
    /// as a plain nester). True for every multisheet pipeline run under the Q40 model.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_unified_geometry_model_active: Option<bool>,
    /// SGH-Q40/Q41: signed solver-sheet inset actually applied = `margin − spacing/2`
    /// (positive shrinks inward, negative grows outward, 0 = physical sheet unchanged).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_solver_sheet_inset_mm: Option<f64>,
    /// SGH-Q40/Q41: spacing value passed to the INNER Sparrow/CDE core (always 0 under the unified
    /// model — spacing is carried by the offset part geometry, not the inner loop).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub technology_inner_spacing_mm: Option<f64>,
}

/// Q10: collision backend audit output (optional, skip when absent).
/// Q18A: extended with CDE observability fields (all optional, backward-compatible).
#[derive(Debug, Serialize)]
pub struct CollisionBackendDiagnosticsOutput {
    pub backend_used: String,
    pub unsupported_queries: usize,
    pub bbox_fallback_queries: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub final_commit_backend_used: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub final_commit_unsupported_queries: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub final_commit_bbox_fallback_queries: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_pair_queries: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_boundary_queries: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_total_queries: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_engine_builds: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_collision_results: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_no_collision_results: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_unsupported_results: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_prepare_failures: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_cross_sheet_skipped: Option<usize>,
    /// SGH-Q23: pair queries resolved as NoCollision by the AABB broad-phase
    /// pre-check, without building a CDEngine (query reduction evidence).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_broadphase_pruned: Option<usize>,
    /// SGH-Q23R1: solve-scoped cache metrics (hits skip the CDEngine build).
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_cache_pair_hits: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_cache_pair_misses: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_cache_boundary_hits: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_cache_boundary_misses: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_cache_prepared_hits: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_cache_prepared_misses: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_cache_invalidations: Option<usize>,
    /// SGH-Q23R2 single-engine multi-hazard batch candidate evaluation metrics.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_batch_candidate_queries: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_batch_engine_builds: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_batch_hazards_registered: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_batch_collisions_returned: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_pairwise_fallback_queries: Option<usize>,
    /// SGH-Q24R1 per-target-search CDE session reuse metrics.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_candidate_session_builds: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_candidate_session_reuses: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub cde_observability_scope: Option<String>,
    /// Only populated when VRS_CDE_OBSERVABILITY_TIMING=1 is set.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub final_commit_validation_ms: Option<f64>,
}

/// SGH-Q07: rotation_deg migrated from i64 to f64 to support continuous/non-orthogonal rotation.
/// Serializer outputs integer angles without ".0" for backward-compatible JSON.
/// Breaking/near-breaking: JSON output changes from `90` to `90` (same) for integer angles;
/// non-integer angles serialize as `45.0` etc. (new capability, not breaking existing callers).
#[derive(Debug, Clone, Serialize)]
pub struct Placement {
    pub instance_id: String,
    pub part_id: String,
    pub sheet_index: usize,
    pub x: f64,
    pub y: f64,
    #[serde(serialize_with = "serialize_rotation_deg")]
    pub rotation_deg: f64,
}

#[derive(Debug, Clone, Serialize)]
pub struct Unplaced {
    pub instance_id: String,
    pub part_id: String,
    pub reason: String,
}

#[derive(Debug, Serialize)]
pub struct Metrics {
    pub placed_count: usize,
    pub unplaced_count: usize,
    pub sheet_count_used: usize,
    pub seed: i64,
    pub time_limit_s: i64,
    pub project_name: String,
}
