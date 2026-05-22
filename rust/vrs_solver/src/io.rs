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
}

#[derive(Debug, Serialize)]
pub struct SolverOutput {
    pub contract_version: String,
    pub status: String,
    pub placements: Vec<Placement>,
    pub unplaced: Vec<Unplaced>,
    pub metrics: Metrics,
}

#[derive(Debug, Serialize)]
pub struct Placement {
    pub instance_id: String,
    pub part_id: String,
    pub sheet_index: usize,
    pub x: f64,
    pub y: f64,
    pub rotation_deg: i64,
}

#[derive(Debug, Serialize)]
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
