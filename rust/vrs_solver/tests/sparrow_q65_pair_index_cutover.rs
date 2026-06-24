//! SGH-Q65 - live PairCompatibilityIndex artifact for the production Interlock cutover.
//!
//! This test uses the real cached `SPInstance` data path and a live placed anchor, then records the
//! ranked pair candidates that the production Interlock branch will consume.

use std::path::PathBuf;

use vrs_solver::io::CollisionBackendKind;
use vrs_solver::item::{dims_for_rotation, placement_anchor_from_rect_min, Part};
use vrs_solver::optimizer::sparrow::interlock_pair::admit_interlock_pair_against_live_anchor;
use vrs_solver::optimizer::sparrow::{SparrowConfig, SparrowPlacement, SparrowProblem};
use vrs_solver::rotation_policy::{RotationPolicyKind, RotationResolveContext};
use vrs_solver::sheet::{stock_to_shape, Stock};

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn lv8_pair_part() -> Part {
    let fixture = repo_root().join("artifacts/benchmarks/sgh_q51/inputs/q51_6big_sp0.json");
    let raw = std::fs::read_to_string(&fixture).expect("read fixture");
    let doc: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let p = &doc["parts"][0];
    Part {
        id: p["id"].as_str().unwrap().to_string(),
        width: p["width"].as_f64().unwrap(),
        height: p["height"].as_f64().unwrap(),
        quantity: 2,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(p["outer_points"].clone()),
        prepared_outer_points: None,
    }
}

#[test]
fn production_pair_index_cutover_emits_live_pair_diagnostics() {
    let part = lv8_pair_part();
    let stock = Stock {
        id: "S".into(),
        quantity: 1,
        width: Some(1500.0),
        height: Some(3000.0),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    };
    let sheet = stock_to_shape(&stock).expect("sheet");
    let rotation_context =
        RotationResolveContext::new(Some(RotationPolicyKind::Continuous), 42, 24);
    let cfg = SparrowConfig::from_solver_input(
        30.0,
        CollisionBackendKind::Cde,
        rotation_context.clone(),
        42,
    );
    let problem = SparrowProblem::from_solver_input(
        &[part],
        std::slice::from_ref(&sheet),
        &rotation_context,
        Vec::new(),
        cfg,
    )
    .expect("problem");
    assert!(problem.instances.len() >= 2, "need 2 live instances");
    let anchor_inst = &problem.instances[0];
    let candidate_inst = &problem.instances[1];
    let rot = anchor_inst
        .orientation_catalog
        .candidates
        .first()
        .map(|c| c.angle_deg)
        .unwrap_or(0.0);
    let anchor_rect_min_x = sheet.min_x + 5.0;
    let anchor_rect_min_y = sheet.min_y + 5.0;
    let (anchor_x, anchor_y) = placement_anchor_from_rect_min(
        anchor_rect_min_x,
        anchor_rect_min_y,
        anchor_inst.part.width,
        anchor_inst.part.height,
        rot,
    );
    let anchor_placement = SparrowPlacement {
        instance_idx: 0,
        sheet_index: 0,
        x: anchor_x,
        y: anchor_y,
        rotation_deg: rot,
    };
    let (rw, rh) = dims_for_rotation(anchor_inst.part.width, anchor_inst.part.height, rot);
    let occupied = vec![[
        anchor_rect_min_x,
        anchor_rect_min_y,
        anchor_rect_min_x + rw,
        anchor_rect_min_y + rh,
    ]];
    let adm = admit_interlock_pair_against_live_anchor(
        anchor_inst,
        &anchor_placement,
        candidate_inst,
        &occupied,
        [sheet.min_x, sheet.min_y, sheet.max_x, sheet.max_y],
    )
    .expect("live pair admission");

    assert_eq!(adm.diagnostics.pair_index_queries, 1);
    assert!(
        adm.diagnostics.pair_candidates_generated > 0
            || adm.diagnostics.rejection_pair_not_found > 0,
        "live pair path must generate candidates or report pair-not-found explicitly"
    );
    assert!(
        adm.diagnostics.pair_candidates_valid <= adm.diagnostics.pair_candidates_generated,
        "valid candidate count cannot exceed generated count"
    );
    if let Some(seed) = &adm.accepted {
        assert!(seed.boundary_clear);
        assert!(seed.cde_clear);
        assert!(!seed.accepted_candidate_source.is_empty());
    } else {
        assert!(
            adm.diagnostics.fallback_to_feature_candidates,
            "no accepted live pair seed must report fallback"
        );
    }

    let dir = repo_root().join("artifacts/benchmarks/sgh_q65");
    std::fs::create_dir_all(&dir).unwrap();
    std::fs::write(
        dir.join("interlock_pair_production_cutover.json"),
        serde_json::to_string_pretty(&adm.to_diagnostics_json()).unwrap(),
    )
    .unwrap();
    assert!(dir.join("interlock_pair_production_cutover.json").exists());
}
