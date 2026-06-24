//! SGH-Q56B — PartAnalysis / ShapeProfileV2 integration test + real-LV8 diagnostics artifact.
//!
//! Routes a representative part set (the REAL critical LV8 part + a synthetic medium part + a
//! synthetic tiny filler) through the production `SparrowProblem` construction and proves the derived
//! `PartAnalysis` layer:
//!   - reuses the existing `PartShapeProfile` values (not a parallel/conflicting system);
//!   - tags the LV8 part as large / critical / edge-alignable; the tiny part as filler (never anchor);
//!   - records `hole_free_solver_input`;
//!   - produces a deterministic fit-difficulty score.
//!
//! Emits the summary artifact under `artifacts/benchmarks/sgh_q56b/`.

use std::path::PathBuf;

use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::part_analysis::{
    build_part_analyses_for_parts, summarize_part_analyses, ShapeTag,
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
    Part {
        id: p["id"].as_str().expect("part id").to_string(),
        width: p["width"].as_f64().expect("width"),
        height: p["height"].as_f64().expect("height"),
        quantity: 6,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(p["outer_points"].clone()),
        prepared_outer_points: None,
    }
}

fn rect(id: &str, w: f64, h: f64, qty: i64) -> Part {
    Part {
        id: id.to_string(),
        width: w,
        height: h,
        quantity: qty,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(serde_json::json!([[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]])),
        prepared_outer_points: None,
    }
}

fn out_dir() -> PathBuf {
    let d = repo_root().join("artifacts/benchmarks/sgh_q56b");
    std::fs::create_dir_all(&d).expect("create out dir");
    d
}

#[test]
fn lv8_part_analysis_layer_tags_and_scores_are_sound() {
    let parts = vec![
        load_lv8_critical_part(),
        rect("medium_structural", 600.0, 400.0, 2),
        rect("tiny_filler", 25.0, 25.0, 30),
    ];
    let analyses =
        build_part_analyses_for_parts(&parts, SHEET_W, SHEET_H, SPACING_MM).expect("part analyses");
    assert_eq!(analyses.len(), 3, "one analysis per unique part type");

    let lv8 = analyses
        .iter()
        .find(|a| a.part_id.starts_with("Lv8"))
        .expect("lv8 analysis");
    let tiny = analyses
        .iter()
        .find(|a| a.part_id == "tiny_filler")
        .expect("tiny analysis");

    // LV8: large / critical / edge-alignable; reuses profile values; hole-free.
    assert!(
        lv8.has_tag(ShapeTag::LargeAnchor),
        "LV8 must be large_anchor"
    );
    assert!(
        lv8.has_tag(ShapeTag::EdgeAlignable),
        "LV8 must be edge_alignable"
    );
    assert_eq!(lv8.diagnostics.criticality_tier, "critical");
    assert!(
        lv8.hole_free_solver_input,
        "LV8 solver input must be hole-free"
    );
    assert!(
        lv8.shape_profile.quantity == 6,
        "profile values are reused verbatim"
    );
    assert!(lv8.fit_difficulty.score >= 0.0 && lv8.fit_difficulty.score <= 1.0);

    // Tiny filler must never be an anchor.
    assert!(
        tiny.has_tag(ShapeTag::TinyFiller),
        "tiny part must be tiny_filler"
    );
    assert!(
        !tiny.has_tag(ShapeTag::LargeAnchor),
        "tiny filler must not be large_anchor"
    );
    assert!(!tiny.has_tag(ShapeTag::CriticalLarge));

    // Determinism: rebuild and compare LV8 fit-difficulty.
    let again =
        build_part_analyses_for_parts(&parts, SHEET_W, SHEET_H, SPACING_MM).expect("rebuild");
    let lv8b = again.iter().find(|a| a.part_id.starts_with("Lv8")).unwrap();
    assert_eq!(
        lv8.fit_difficulty.score, lv8b.fit_difficulty.score,
        "fit-difficulty deterministic"
    );

    // Emit the summary artifact.
    let summary = summarize_part_analyses(&analyses);
    let path = out_dir().join("part_analysis_summary.json");
    std::fs::write(&path, serde_json::to_string_pretty(&summary).expect("ser"))
        .unwrap_or_else(|e| panic!("write {}: {e}", path.display()));
    assert!(path.exists());
}
