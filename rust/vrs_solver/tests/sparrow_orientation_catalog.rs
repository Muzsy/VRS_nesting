//! SGH-Q56A — OrientationCatalog integration test + real-LV8 diagnostics artifact.
//!
//! Loads the REAL critical large LV8 part (`Lv8_11612_6db`) from the Q51 fixture, routes it through
//! the production `SparrowProblem` construction (real spacing → genuine spacing-expanded contour),
//! and proves the per-part `OrientationCatalog`:
//!   - is non-empty and feature-derived for a continuous part;
//!   - traces at least one candidate to a real contour edge;
//!   - computes extrema from the spacing-expanded contour (not part.width/height);
//!   - exposes at least one genuinely fractional (non-orthogonal) candidate.
//!
//! Emits the diagnostics artifact under `artifacts/benchmarks/sgh_q56a/`.

use std::path::PathBuf;

use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::orientation_catalog::{
    build_orientation_catalog_for_part, OrientationCandidateKind,
};
use vrs_solver::rotation_policy::RotationPolicyKind;

const SHEET_W: f64 = 1500.0;
const SHEET_H: f64 = 3000.0;
const SPACING_MM: f64 = 8.0;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn load_lv8_critical_part() -> Part {
    let fixture = repo_root().join("artifacts/benchmarks/sgh_q51/inputs/q51_6big_sp8.json");
    let raw = std::fs::read_to_string(&fixture)
        .unwrap_or_else(|e| panic!("read fixture {}: {e}", fixture.display()));
    let doc: serde_json::Value = serde_json::from_str(&raw).expect("parse fixture json");
    let p = &doc["parts"][0];
    let id = p["id"].as_str().expect("part id").to_string();
    let width = p["width"].as_f64().expect("part width");
    let height = p["height"].as_f64().expect("part height");
    let outer_points = p["outer_points"].clone();
    assert!(
        outer_points.as_array().map(|a| a.len()).unwrap_or(0) > 8,
        "real LV8 part must carry a genuine outer contour"
    );
    Part {
        id,
        width,
        height,
        quantity: 1,
        allowed_rotations_deg: vec![],
        // Continuous: the rotation candidates must come from the real contour geometry, never snaps.
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(outer_points),
        prepared_outer_points: None,
    }
}

fn out_dir() -> PathBuf {
    let d = repo_root().join("artifacts/benchmarks/sgh_q56a");
    std::fs::create_dir_all(&d).expect("create out dir");
    d
}

#[test]
fn lv8_critical_orientation_catalog_is_feature_derived_and_spacing_aware() {
    let part = load_lv8_critical_part();
    let cat = build_orientation_catalog_for_part(&part, SHEET_W, SHEET_H, SPACING_MM)
        .expect("orientation catalog for real LV8 part");

    // 1) non-empty + continuous.
    assert!(cat.continuous_rotation, "LV8 part must be continuous");
    assert!(
        !cat.candidates.is_empty(),
        "LV8 catalog must expose orientation candidates"
    );
    // 2) feature-derived alignment candidates exist and trace to a real contour edge.
    let traced = cat
        .candidates
        .iter()
        .filter(|c| {
            matches!(
                c.kind,
                OrientationCandidateKind::SheetVerticalAlignment
                    | OrientationCandidateKind::SheetHorizontalAlignment
            )
        })
        .any(|c| c.source_edge_index.is_some());
    assert!(
        traced,
        "at least one alignment candidate must trace to a real contour edge"
    );
    // 3) min-width candidate present.
    assert!(
        cat.diagnostics.min_width_candidate_count >= 1,
        "LV8 catalog must expose a min-width candidate"
    );
    // 4) extrema came from the spacing-expanded contour.
    assert!(
        cat.diagnostics.extrema_from_spacing_expanded,
        "extrema must be derived from the spacing-expanded contour"
    );
    assert!(
        !cat.extrema_samples.is_empty(),
        "LV8 catalog must emit extrema samples"
    );
    // 5) at least one genuinely fractional candidate (LV8 is not axis-aligned at its min-width).
    assert!(
        cat.candidates.iter().any(|c| c.is_fractional),
        "LV8 critical part must expose at least one fractional (non-orthogonal) candidate"
    );

    // Emit the diagnostics artifact.
    let json = cat.to_diagnostics_json();
    let path = out_dir().join("orientation_catalog_lv8_critical.json");
    std::fs::write(
        &path,
        serde_json::to_string_pretty(&json).expect("serialize catalog json"),
    )
    .unwrap_or_else(|e| panic!("write artifact {}: {e}", path.display()));
    assert!(path.exists(), "artifact must be written");
}
