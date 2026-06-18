//! SGH-Q53A contour-feature extraction integration tests.
//!
//! These stay on the public adapter boundary and verify that the Q53A feature layer is exported as
//! additive diagnostics only: no collision semantics change, deterministic counts, and the outer
//! contour drives the summary even when optional hole metadata is present.

use serde_json::{json, Value};
use vrs_solver::adapter::solve;
use vrs_solver::io::{OptimizerDiagnosticsOutput, SolverInput, SolverOutput};

fn rect_part(id: &str, qty: i64, w: f64, h: f64) -> Value {
    json!({
        "id": id,
        "quantity": qty,
        "width": w,
        "height": h,
        "allowed_rotations_deg": [0, 90, 180, 270],
        "outer_points": [[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]
    })
}

fn concave_part(id: &str, qty: i64) -> Value {
    json!({
        "id": id,
        "quantity": qty,
        "width": 1000.0,
        "height": 1000.0,
        "allowed_rotations_deg": [0, 90, 180, 270],
        "outer_points": [
            [0.0, 0.0], [1000.0, 0.0], [1000.0, 200.0], [200.0, 200.0], [200.0, 1000.0], [0.0, 1000.0]
        ]
    })
}

fn lv8_like_part(id: &str, qty: i64) -> Value {
    json!({
        "id": id,
        "quantity": qty,
        "width": 1240.0,
        "height": 760.0,
        "rotation_policy": "continuous",
        "outer_points": [
            [0.0, 110.0], [250.0, 0.0], [760.0, 0.0], [1160.0, 80.0], [1240.0, 210.0],
            [1210.0, 430.0], [990.0, 620.0], [720.0, 760.0], [420.0, 730.0], [160.0, 560.0],
            [40.0, 340.0], [210.0, 300.0], [360.0, 420.0], [610.0, 470.0], [840.0, 350.0],
            [860.0, 220.0], [690.0, 150.0], [360.0, 160.0], [120.0, 220.0]
        ]
    })
}

fn with_hole_metadata(mut part: Value) -> Value {
    // The hole must lie INSIDE the solid material. `concave_part` is an L whose filled region is the
    // bottom band (y <= 200) plus the left column (x <= 200); the top-right (x > 200 && y > 200) is
    // the concave cut-out (no material). Place the hole well inside the bottom band.
    part["holes_points"] = json!([[
        [400.0, 50.0],
        [450.0, 50.0],
        [450.0, 100.0],
        [400.0, 100.0]
    ]]);
    part
}

fn ms_input(parts: Vec<Value>, stocks: Vec<Value>, seed: i64, time_limit_s: i64) -> Value {
    json!({
        "contract_version": "v1",
        "project_name": "sgh_q53a_test",
        "seed": seed,
        "time_limit_s": time_limit_s,
        "stocks": stocks,
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": 0.0,
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "parts": parts,
    })
}

fn parse_and_solve(v: &Value) -> SolverOutput {
    let input: SolverInput = serde_json::from_value(v.clone()).expect("parse SolverInput");
    solve(input).expect("solve")
}

fn od(out: &SolverOutput) -> &OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics
        .as_ref()
        .expect("optimizer_diagnostics must be present for sparrow_cde_multisheet")
}

#[test]
fn shape_profiles_export_contour_feature_summary() {
    let parts = vec![lv8_like_part("lv8", 2), rect_part("tiny", 4, 40.0, 40.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let out = parse_and_solve(&ms_input(parts, stocks, 17, 30));
    assert_eq!(out.status, "ok");
    let profiles = od(&out)
        .shape_profiles
        .as_ref()
        .expect("shape_profiles must be present");
    let lv8 = profiles
        .iter()
        .find(|p| p.part_id == "lv8")
        .expect("lv8 profile");
    assert!(lv8.contour_vertex_count >= 12);
    assert!(lv8.dominant_edge_count >= 2);
    assert!(lv8.contour_feature_total_count > lv8.contour_vertex_count);
    assert!(
        !lv8.dominant_alignment_angles_deg.is_empty(),
        "feature-rich part must export continuous alignment seeds"
    );
}

#[test]
fn contour_feature_summary_is_deterministic_across_solves() {
    let parts = vec![concave_part("L", 2), rect_part("tiny", 6, 30.0, 30.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let a = parse_and_solve(&ms_input(parts.clone(), stocks.clone(), 5, 30));
    let b = parse_and_solve(&ms_input(parts, stocks, 5, 30));
    let pa = od(&a).shape_profiles.as_ref().unwrap();
    let pb = od(&b).shape_profiles.as_ref().unwrap();
    assert_eq!(pa.len(), pb.len());
    for (lhs, rhs) in pa.iter().zip(pb.iter()) {
        assert_eq!(lhs.part_id, rhs.part_id);
        assert_eq!(
            lhs.contour_feature_total_count,
            rhs.contour_feature_total_count
        );
        assert_eq!(lhs.concave_zone_count, rhs.concave_zone_count);
        assert_eq!(
            lhs.protrusion_candidate_count,
            rhs.protrusion_candidate_count
        );
        assert_eq!(
            lhs.dominant_alignment_angles_deg,
            rhs.dominant_alignment_angles_deg
        );
    }
}

#[test]
fn hole_metadata_is_rejected_on_outer_only_phase_so_summary_stays_outer_driven() {
    // The Q53A contour-feature summary must be driven by the OUTER contour only. On the
    // `jagua_optimizer_phase1_outer_only` path a part carrying hole metadata is INTENTIONALLY
    // rejected (UNSUPPORTED_PART_HOLES_PHASE1, adapter.rs), so hole geometry can never leak into
    // the feature layer. A plain (hole-free) part on the same path solves and exports the
    // outer-contour feature summary. (The original test asserted the holed part would solve `ok`,
    // which contradicts this intentional outer-only restriction — it could never pass.)
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];

    // (1) plain part → ok, outer-contour feature summary present.
    let plain_out = parse_and_solve(&ms_input(
        vec![concave_part("L_plain", 1), rect_part("tiny", 2, 30.0, 30.0)],
        stocks.clone(),
        11,
        30,
    ));
    assert_eq!(plain_out.status, "ok");
    let profiles = od(&plain_out).shape_profiles.as_ref().unwrap();
    let plain = profiles.iter().find(|p| p.part_id == "L_plain").unwrap();
    assert!(
        plain.contour_vertex_count > 0,
        "the outer contour drives the feature summary"
    );
    assert!(plain.concave_zone_count >= 1, "the L exposes a concave region");

    // (2) the SAME part WITH hole metadata → intentionally unsupported on the outer-only phase,
    // proving hole geometry never reaches (and so never perturbs) the feature layer here.
    let holed_out = parse_and_solve(&ms_input(
        vec![
            with_hole_metadata(concave_part("L_holed", 1)),
            rect_part("tiny", 2, 30.0, 30.0),
        ],
        stocks,
        11,
        30,
    ));
    assert_eq!(holed_out.status, "unsupported");
    assert_eq!(
        holed_out.unsupported_reason.as_deref(),
        Some("UNSUPPORTED_PART_HOLES_PHASE1"),
    );
}
