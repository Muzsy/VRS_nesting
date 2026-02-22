use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineRequest {
    pub version: String,
    pub kerf_mm: f64,
    pub margin_mm: f64,
    pub parts: Vec<PartRequest>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartRequest {
    pub id: String,
    pub outer_points_mm: Vec<[f64; 2]>,
    pub holes_points_mm: Vec<Vec<[f64; 2]>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineResponse {
    pub version: String,
    pub parts: Vec<PartResponse>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartResponse {
    pub id: String,
    pub status: String,
    pub inflated_outer_points_mm: Vec<[f64; 2]>,
    pub inflated_holes_points_mm: Vec<Vec<[f64; 2]>>,
    pub diagnostics: Vec<Diagnostic>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Diagnostic {
    pub code: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub hole_index: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub nominal_hole_bbox_mm: Option<[f64; 4]>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub preserve_for_export: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub usable_for_nesting: Option<bool>,
    pub detail: String,
}
