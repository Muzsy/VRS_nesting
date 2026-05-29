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
