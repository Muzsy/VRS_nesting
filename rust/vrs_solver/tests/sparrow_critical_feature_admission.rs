//! SGH-Q53D - feature-first critical admission integration tests.

use serde_json::{json, Value};
use vrs_solver::adapter::solve;
use vrs_solver::io::{OptimizerDiagnosticsOutput, SolverInput, SolverOutput};

fn l_part(id: &str, qty: i64) -> Value {
    json!({
        "id": id, "quantity": qty, "width": 1000.0, "height": 1000.0,
        "allowed_rotations_deg": [0, 90, 180, 270],
        "outer_points": [
            [0.0, 0.0], [1000.0, 0.0], [1000.0, 300.0],
            [300.0, 300.0], [300.0, 1000.0], [0.0, 1000.0]
        ]
    })
}

fn rect_part(id: &str, qty: i64, w: f64, h: f64) -> Value {
    json!({
        "id": id, "quantity": qty, "width": w, "height": h,
        "allowed_rotations_deg": [0, 90, 180, 270],
        "outer_points": [[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]]
    })
}

fn ms_input(parts: Vec<Value>, stocks: Vec<Value>, seed: i64, t: i64) -> Value {
    json!({
        "contract_version": "v1",
        "project_name": "sgh_q53d_test",
        "seed": seed,
        "time_limit_s": t,
        "stocks": stocks,
        "solver_profile": "jagua_optimizer_phase1_outer_only",
        "margin_mm": 0.0,
        "optimizer_pipeline": "sparrow_cde_multisheet",
        "collision_backend": "cde",
        "parts": parts,
    })
}

fn solve_json(v: &Value) -> SolverOutput {
    let input: SolverInput = serde_json::from_value(v.clone()).expect("parse SolverInput");
    solve(input).expect("solve")
}

fn od(out: &SolverOutput) -> &OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics.as_ref().expect("optimizer_diagnostics present")
}

fn enable_feature_builder() {
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    std::env::set_var("VRS_SHEET_BUILDER_FEATURE_CRITICAL", "1");
    std::env::set_var("VRS_FEATURE_CANDIDATES", "1");
    std::env::set_var("VRS_BPP_DENSITY_SAMPLES", "40");
    std::env::remove_var("VRS_ADMISSION_DENSITY_BIAS");
}

#[test]
fn critical_feature_admission_builder_records_feature_first_attempts() {
    enable_feature_builder();
    let parts = vec![l_part("L", 4), rect_part("f", 12, 120.0, 120.0)];
    let stocks = vec![json!({"id": "S", "quantity": 3, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 42, 40));

    assert_eq!(out.status, "ok");
    assert_eq!(out.unplaced.len(), 0);
    let d = od(&out);
    assert_eq!(d.sparrow_ms_final_pairs, Some(0));
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0));
    let bpp = d.bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(bpp.bpp_sheet_builder_applied);
    assert!(
        bpp.bpp_critical_feature_admission_attempts > 0,
        "feature-first critical admission should run at least once"
    );
    assert!(
        bpp.bpp_feature_candidates_generated > 0,
        "critical feature admission should generate contour-feature candidates"
    );
}

#[test]
fn critical_feature_admission_builder_reports_close_reason_and_fallback_metrics() {
    enable_feature_builder();
    let parts = vec![l_part("L", 5), rect_part("f", 8, 140.0, 140.0)];
    let stocks = vec![json!({"id": "S", "quantity": 4, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 7, 40));

    assert_eq!(out.status, "ok");
    let d = od(&out);
    assert_eq!(d.sparrow_ms_final_pairs, Some(0));
    let bpp = d.bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(
        bpp.bpp_critical_phase_close_reason.is_some(),
        "critical phase must report why it closed"
    );
    assert!(
        bpp.bpp_bbox_corner_candidates_generated >= bpp.bpp_bbox_corner_candidates_accepted,
        "fallback bbox counters must remain explicit and monotone"
    );
    assert!(
        bpp.bpp_critical_candidate_rejection_summary.is_some()
            || bpp.bpp_accepted_feature_pair_type.is_some(),
        "either a feature pair is accepted or rejection reasons are recorded"
    );
}
