//! CgalReferenceProvider — CGAL-based NFP via the external nfp_cgal_probe binary.
//!
//! **GPL licensing**: This provider is DEV/REFERENCE ONLY. It is never linked into
//! production binaries or Docker images. Configure with:
//!   NFP_ENABLE_CGAL_REFERENCE=1           — opt-in to use this provider
//!   NFP_CGAL_PROBE_BIN=/path/to/binary   — optional, defaults to
//!                                          "tools/nfp_cgal_probe/build/nfp_cgal_probe"
//!
//! This provider does NOT silently fall back to OldConcave on error.

use std::path::PathBuf;
use std::process::Command;
use std::time::Instant;

use crate::geometry::scale::i64_to_mm;
use crate::geometry::types::{Point64, Polygon64};
use crate::nfp::provider::{NfpKernel, NfpProvider, NfpProviderResult};
use crate::nfp::NfpError;

const DEFAULT_CGAL_BINARY: &str = "tools/nfp_cgal_probe/build/nfp_cgal_probe";

/// CGAL NFP provider — calls the external nfp_cgal_probe binary.
pub struct CgalReferenceProvider {
    binary_path: PathBuf,
}

impl CgalReferenceProvider {
    pub fn new() -> Self {
        Self::default()
    }
}

impl Default for CgalReferenceProvider {
    fn default() -> Self {
        let binary_path = std::env::var("NFP_CGAL_PROBE_BIN")
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from(DEFAULT_CGAL_BINARY));
        Self { binary_path }
    }
}

impl NfpProvider for CgalReferenceProvider {
    fn kernel(&self) -> NfpKernel {
        NfpKernel::CgalReference
    }

    fn kernel_name(&self) -> &'static str {
        "cgal_reference"
    }

    fn supports_holes(&self) -> bool {
        true
    }

    fn compute(
        &self,
        placed_polygon: &Polygon64,
        moving_polygon: &Polygon64,
    ) -> Result<NfpProviderResult, NfpError> {
        let start = Instant::now();

        // 1. Validate binary exists
        if !self.binary_path.exists() {
            return Err(NfpError::CgalBinaryNotFound(
                self.binary_path.display().to_string(),
            ));
        }

        // 2. Build input fixture JSON
        let input_json = build_cgal_fixture(placed_polygon, moving_polygon)?;

        // 3. Write temp input file
        let input_path = std::env::temp_dir()
            .join(format!("cgal_probe_input_{}.json", std::process::id()));
        std::fs::write(&input_path, &input_json)
            .map_err(|e| NfpError::CgalIoError(format!("failed to write temp input: {e}")))?;

        let output_path = std::env::temp_dir()
            .join(format!("cgal_probe_output_{}.json", std::process::id()));

        // 4. Spawn CGAL probe subprocess
        let output = Command::new(&self.binary_path)
            .args([
                "--fixture",
                input_path.to_str().unwrap_or(""),
                "--algorithm",
                "reduced_convolution",
                "--output-json",
                output_path.to_str().unwrap_or(""),
            ])
            .output()
            .map_err(|e| NfpError::CgalSubprocessError(format!("failed to spawn: {e}")))?;

        // Clean up input file regardless of outcome
        let _ = std::fs::remove_file(&input_path);

        // 5. Check exit code
        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr);
            return Err(NfpError::CgalNonZeroExit {
                code: output.status.code().unwrap_or(-1),
                stderr: stderr.to_string(),
            });
        }

        // 6. Read output JSON
        let output_text = std::fs::read_to_string(&output_path)
            .map_err(|e| NfpError::CgalIoError(format!("failed to read output: {e}")))?;
        let _ = std::fs::remove_file(&output_path);

        // 7. Parse output JSON
        let cgal_result: CgalProbeResult = serde_json::from_str(&output_text)
            .map_err(|e| NfpError::CgalParseError(format!("invalid JSON: {e}")))?;

        // 8. Validate CGAL status
        if cgal_result.status != "success" {
            let msg = cgal_result
                .error
                .as_ref()
                .and_then(|e| e.get("message"))
                .and_then(|v| v.as_str())
                .unwrap_or("unknown CGAL error");
            return Err(NfpError::CgalInternalError(msg.to_string()));
        }

        // 9. Validate output polygon is non-empty
        if cgal_result.outer_i64.is_empty() {
            return Err(NfpError::EmptyPolygon);
        }

        // 10. Convert CGAL i64 output to Polygon64
        let outer: Vec<Point64> = cgal_result
            .outer_i64
            .iter()
            .map(|pt| Point64 { x: pt[0], y: pt[1] })
            .collect();

        let holes: Vec<Vec<Point64>> = cgal_result
            .holes_i64
            .iter()
            .map(|ring| {
                ring.iter()
                    .map(|pt| Point64 { x: pt[0], y: pt[1] })
                    .collect()
            })
            .collect();

        let polygon = Polygon64 { outer, holes };

        let elapsed_ms = (start.elapsed().as_secs_f64() * 1000.0).round() as u64;
        let compute_time_ms = cgal_result
            .timing_ms
            .map(|t| t.round() as u64)
            .unwrap_or(elapsed_ms)
            .max(elapsed_ms);

        Ok(NfpProviderResult {
            polygon,
            compute_time_ms,
            kernel: NfpKernel::CgalReference,
            validation_status: None,
        })
    }
}

// ---------------------------------------------------------------------------
// CGAL probe JSON types
// ---------------------------------------------------------------------------

#[derive(Debug, serde::Deserialize)]
struct CgalProbeResult {
    #[serde(rename = "status")]
    status: String,
    #[serde(rename = "outer_i64")]
    outer_i64: Vec<[i64; 2]>,
    #[serde(rename = "holes_i64")]
    holes_i64: Vec<Vec<[i64; 2]>>,
    #[serde(rename = "timing_ms", default)]
    timing_ms: Option<f64>,
    #[serde(rename = "error", default)]
    error: Option<serde_json::Value>,
}

// ---------------------------------------------------------------------------
// Input fixture builder
// ---------------------------------------------------------------------------

fn build_cgal_fixture(
    placed_polygon: &Polygon64,
    moving_polygon: &Polygon64,
) -> Result<String, NfpError> {
    let fixture = CgalFixture {
        fixture_version: "nfp_pair_fixture_v1".to_string(),
        pair_id: "provider_runtime_pair".to_string(),
        part_a: FixturePart {
            part_id: "placed".to_string(),
            points_mm: polygon_to_mm_points(&placed_polygon.outer),
            holes_mm: placed_polygon
                .holes
                .iter()
                .map(|hole| polygon_to_mm_points(hole))
                .collect(),
        },
        part_b: FixturePart {
            part_id: "moving".to_string(),
            points_mm: polygon_to_mm_points(&moving_polygon.outer),
            holes_mm: moving_polygon
                .holes
                .iter()
                .map(|hole| polygon_to_mm_points(hole))
                .collect(),
        },
    };

    serde_json::to_string(&fixture)
        .map_err(|e| NfpError::CgalParseError(format!("failed to serialise fixture: {e}")))
}

fn polygon_to_mm_points(ring: &[Point64]) -> Vec<[f64; 2]> {
    ring.iter()
        .map(|p| {
            let x_mm = i64_to_mm(p.x);
            let y_mm = i64_to_mm(p.y);
            [x_mm, y_mm]
        })
        .collect()
}

// ---------------------------------------------------------------------------
// CGAL fixture JSON types (matches nfp_pair_fixture_v1 schema)
// ---------------------------------------------------------------------------

#[derive(Debug, serde::Serialize)]
struct CgalFixture {
    #[serde(rename = "fixture_version")]
    fixture_version: String,
    #[serde(rename = "pair_id")]
    pair_id: String,
    #[serde(rename = "part_a")]
    part_a: FixturePart,
    #[serde(rename = "part_b")]
    part_b: FixturePart,
}

#[derive(Debug, serde::Serialize)]
struct FixturePart {
    #[serde(rename = "part_id")]
    part_id: String,
    #[serde(rename = "points_mm")]
    points_mm: Vec<[f64; 2]>,
    #[serde(rename = "holes_mm")]
    holes_mm: Vec<Vec<[f64; 2]>>,
}
