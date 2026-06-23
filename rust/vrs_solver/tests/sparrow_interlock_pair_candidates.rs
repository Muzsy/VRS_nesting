//! SGH-Q57B — Interlock pair admission integration test + real-LV8 artifact.
//!
//! Drives `admit_interlock_pair` for the REAL critical LV8 part as both Anchor and Interlock candidate:
//! the Interlock role queries the pair index, converts the pair transform into a placement seed against
//! the placed anchor, validates it (boundary + clearance), and either accepts a valid seed or reports a
//! fallback to neighbour-feature candidates. Emits the artifact under `artifacts/benchmarks/sgh_q57b/`.

use std::path::PathBuf;

use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::interlock_pair::admit_interlock_pair;
use vrs_solver::rotation_policy::RotationPolicyKind;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}

fn lv8() -> Part {
    let fixture = repo_root().join("artifacts/benchmarks/sgh_q51/inputs/q51_6big_sp8.json");
    let raw = std::fs::read_to_string(&fixture).expect("read fixture");
    let doc: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let p = &doc["parts"][0];
    Part {
        id: p["id"].as_str().unwrap().to_string(),
        width: p["width"].as_f64().unwrap(),
        height: p["height"].as_f64().unwrap(),
        quantity: 6,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(p["outer_points"].clone()),
        prepared_outer_points: None,
    }
}

#[test]
fn lv8_interlock_pair_admission_is_validated_or_reports_fallback() {
    let part = lv8();
    let adm = admit_interlock_pair(&part, &part, 1500.0, 3000.0, 8.0).expect("admission");

    // The Interlock role queried the pair index.
    assert_eq!(adm.diagnostics.pair_index_queries, 1);

    // Accepted seed must be exact-boundary + clearance valid; otherwise the fallback is explicit.
    match &adm.accepted {
        Some(seed) => {
            assert!(seed.boundary_clear, "accepted seed must be boundary-clear");
            assert!(seed.cde_clear, "accepted seed must be clearance-clear");
            assert_eq!(seed.role, "interlock");
            assert!(seed.accepted_rotation_deg.is_finite());
        }
        None => {
            assert!(
                adm.diagnostics.fallback_to_feature_candidates,
                "no accepted pair seed must explicitly report the neighbour-feature fallback"
            );
        }
    }

    let dir = repo_root().join("artifacts/benchmarks/sgh_q57b");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(
        dir.join("interlock_pair_admission.json"),
        serde_json::to_string_pretty(&adm.to_diagnostics_json()).expect("ser"),
    )
    .expect("write");
    assert!(dir.join("interlock_pair_admission.json").exists());
}
