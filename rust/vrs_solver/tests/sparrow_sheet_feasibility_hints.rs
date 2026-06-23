//! SGH-Q58A — SheetFeasibilityHints integration test + real-LV8 artifact.

use std::path::PathBuf;

use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::sheet_feasibility::{build_sheet_feasibility_hints, CapacityStatus};
use vrs_solver::rotation_policy::RotationPolicyKind;

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

#[test]
fn lv8_sheet_feasibility_hints_are_sound_and_labelled() {
    let parts = vec![lv8(6), rect("filler", 40.0, 40.0, 60)];
    let h = build_sheet_feasibility_hints(&parts, 1500.0, 3000.0, 5.0, 8.0).expect("hints");

    assert!(h.sheet_count_area_lower_bound >= 1, "area lower bound must be >= 1");
    assert_eq!(h.diagnostics.usable_sheet_area_basis, "margin_shrunk");

    let lv8h = h
        .critical_part_type_hints
        .iter()
        .find(|c| c.part_id.starts_with("Lv8"))
        .expect("lv8 critical hint");
    assert_eq!(lv8h.quantity, 6);
    let sum: usize = lv8h.target_distribution.iter().sum();
    assert_eq!(sum, 6, "distribution covers full quantity");
    assert!(!matches!(lv8h.status, CapacityStatus::ProvenByFocusedTest), "no proof claims in Q58A");

    assert!(
        h.danger_parts.iter().any(|d| d.part_id.starts_with("Lv8")),
        "LV8 large repeated critical must be a danger part"
    );

    let dir = repo_root().join("artifacts/benchmarks/sgh_q58a");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(
        dir.join("sheet_feasibility_hints.json"),
        serde_json::to_string_pretty(&h.to_diagnostics_json()).expect("ser"),
    )
    .expect("write");
    assert!(dir.join("sheet_feasibility_hints.json").exists());
}
