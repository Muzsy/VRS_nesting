//! SGH-Q67 - focused artifact runner for simultaneous critical production cutover evidence.

use std::path::PathBuf;

use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::critical_simultaneous::admit_critical_group;
use vrs_solver::rotation_policy::RotationPolicyKind;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn rect_part(id: &str, width: f64, height: f64, qty: i64) -> Part {
    Part {
        id: id.to_string(),
        width,
        height,
        quantity: qty,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(serde_json::json!([
            [0.0, 0.0],
            [width, 0.0],
            [width, height],
            [0.0, height]
        ])),
        prepared_outer_points: None,
    }
}

#[test]
fn q67_focused_runner_writes_artifact() {
    let pair = admit_critical_group(
        &rect_part("q67_rect_pair", 300.0, 200.0, 2),
        2,
        1500.0,
        3000.0,
        5.0,
        0.0,
    )
    .expect("pair");
    let triple = admit_critical_group(
        &rect_part("q67_rect_triple", 700.0, 2400.0, 3),
        3,
        1500.0,
        3000.0,
        5.0,
        8.0,
    )
    .expect("triple");

    assert!(
        pair.full_success,
        "the focused pair helper run must succeed"
    );
    assert_eq!(
        triple.best_partial_count, 2,
        "the focused triple helper run must preserve the valid 2-part partial"
    );

    let artifact = serde_json::json!({
        "pair_helper": pair.to_diagnostics_json(),
        "triple_helper": triple.to_diagnostics_json(),
        "summary": {
            "pair_full_success": pair.full_success,
            "triple_full_success": triple.full_success,
            "triple_best_partial_count": triple.best_partial_count,
            "triple_best_partial_source": triple.best_partial_source,
        }
    });
    let dir = repo_root().join("artifacts/benchmarks/sgh_q67");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(
        dir.join("simultaneous_critical_production_cutover.json"),
        serde_json::to_string_pretty(&artifact).expect("ser"),
    )
    .expect("write");
    assert!(dir
        .join("simultaneous_critical_production_cutover.json")
        .exists());
}
