use serde::{Deserialize, Serialize};

use crate::item::Part;
use crate::sheet::Stock;

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

#[derive(Debug, Clone, Serialize)]
pub struct Placement {
    pub instance_id: String,
    pub part_id: String,
    pub sheet_index: usize,
    pub x: f64,
    pub y: f64,
    pub rotation_deg: i64,
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
