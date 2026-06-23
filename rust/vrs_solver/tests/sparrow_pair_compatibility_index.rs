//! SGH-Q57A — PairCompatibilityIndex integration test + real-LV8 diagnostics artifact.
//!
//! Loads the REAL critical LV8 part (quantity 6) and builds the critical-only pair index, proving:
//! a same-part flip candidate is generated, candidates carry rotation + relative transform metadata,
//! valid (clear) candidates exist, and tiny filler pairs are excluded. Emits the artifact under
//! `artifacts/benchmarks/sgh_q57a/`.

use std::path::PathBuf;

use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::quantify::pair_matrix::{
    build_pair_compatibility_index, PairCandidateSource, PairIndexConfig,
};
use vrs_solver::rotation_policy::RotationPolicyKind;

const SHEET_W: f64 = 1500.0;
const SHEET_H: f64 = 3000.0;
const SPACING_MM: f64 = 8.0;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}

fn lv8(qty: i64) -> Part {
    let fixture = repo_root().join("artifacts/benchmarks/sgh_q51/inputs/q51_6big_sp8.json");
    let raw = std::fs::read_to_string(&fixture).expect("read fixture");
    let doc: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let p = &doc["parts"][0];
    Part {
        id: p["id"].as_str().unwrap().to_string(),
        width: p["width"].as_f64().unwrap(),
        height: p["height"].as_f64().unwrap(),
        quantity: qty,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(p["outer_points"].clone()),
        prepared_outer_points: None,
    }
}

fn tiny(id: &str) -> Part {
    Part {
        id: id.to_string(),
        width: 22.0,
        height: 22.0,
        quantity: 40,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(serde_json::json!([[0.0, 0.0], [22.0, 0.0], [22.0, 22.0], [0.0, 22.0]])),
        prepared_outer_points: None,
    }
}

#[test]
fn lv8_pair_index_has_same_part_critical_candidate_and_excludes_filler() {
    let parts = vec![lv8(6), tiny("tiny_filler")];
    let index = build_pair_compatibility_index(&parts, SHEET_W, SHEET_H, SPACING_MM, PairIndexConfig::default())
        .expect("pair index");

    // Same-part critical candidate present (no hard-coded part name in the builder).
    assert!(
        index.candidates.iter().any(|c| c.part_a_id.starts_with("Lv8")
            && c.part_b_id.starts_with("Lv8")
            && c.candidate_source == PairCandidateSource::SamePartFlip),
        "LV8 must yield a same-part flip pair candidate"
    );
    // Tiny filler excluded from the critical-only index.
    assert!(
        index.candidates.iter().all(|c| c.part_a_id != "tiny_filler" && c.part_b_id != "tiny_filler"),
        "tiny filler must be excluded"
    );
    // At least one valid (cde + spacing clear) candidate.
    assert!(index.valid_candidates() >= 1, "at least one valid pair candidate required");
    // Rotation + transform metadata present.
    for c in &index.candidates {
        assert!(c.rotation_a_deg.is_finite() && c.rotation_b_deg.is_finite());
        assert!(c.relative_dx.is_finite() && c.relative_dy.is_finite());
    }

    let dir = repo_root().join("artifacts/benchmarks/sgh_q57a");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(
        dir.join("pair_compatibility_index.json"),
        serde_json::to_string_pretty(&index.to_diagnostics_json()).expect("ser"),
    )
    .expect("write");
    assert!(dir.join("pair_compatibility_index.json").exists());
}
