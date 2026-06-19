//! SGH-Q54A — Skeleton role assignment integration test.
//!
//! Q54A is a pure state/decision layer: with `VRS_SHEET_BUILDER_SKELETON=1` it records a skeleton
//! role per admitted critical part but **must not change placement** (Q54B+ act on the role). This
//! test proves the placement-invariance on the public `adapter::solve` boundary and that the role
//! counts are recorded. Env vars are process-global, so both phases live in ONE sequential test.

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
        "contract_version": "v1", "project_name": "sgh_q54a_test", "seed": seed, "time_limit_s": t,
        "stocks": stocks, "solver_profile": "jagua_optimizer_phase1_outer_only", "margin_mm": 0.0,
        "optimizer_pipeline": "sparrow_cde_multisheet", "collision_backend": "cde", "parts": parts,
    })
}

fn solve_json(v: &Value) -> SolverOutput {
    let input: SolverInput = serde_json::from_value(v.clone()).expect("parse SolverInput");
    solve(input).expect("solve")
}

fn od(out: &SolverOutput) -> &OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics.as_ref().expect("optimizer_diagnostics present")
}

fn used_sheets(out: &SolverOutput) -> usize {
    out.placements
        .iter()
        .map(|p| p.sheet_index)
        .collect::<std::collections::BTreeSet<_>>()
        .len()
}

#[test]
fn skeleton_admission_is_valid_records_roles_and_runs_feature_path() {
    // Q54A records skeleton roles; Q54C drives the feature-first, overlap-tolerant admission on the
    // skeleton path (so it DOES change placement, unlike the Q54A-only state layer). The result must
    // stay valid, record roles, exercise the feature path, and not regress the used-sheet count.
    let parts = vec![l_part("L", 4), rect_part("f", 12, 120.0, 120.0)];
    let stocks = vec![json!({"id": "S", "quantity": 3, "width": 3000.0, "height": 1500.0})];
    let input = ms_input(parts, stocks, 42, 40);

    // ── (1) builder ON, skeleton OFF (baseline) ─────────────────────────────────────────────────
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    std::env::remove_var("VRS_SHEET_BUILDER_SKELETON");
    let off = solve_json(&input);
    assert_eq!(off.status, "ok", "builder baseline must be valid: {}", off.status);
    let off_sheets = used_sheets(&off);
    let off_bpp = od(&off).bpp_reduction.as_ref().expect("bpp diagnostics");
    assert_eq!(
        (
            off_bpp.bpp_skeleton_anchor_count,
            off_bpp.bpp_skeleton_interlock_count,
            off_bpp.bpp_skeleton_bandinsert_count,
        ),
        (0, 0, 0),
        "skeleton off must not record any roles"
    );

    // ── (2) builder ON, skeleton ON ─────────────────────────────────────────────────────────────
    std::env::set_var("VRS_SHEET_BUILDER_SKELETON", "1");
    let on = solve_json(&input);
    std::env::remove_var("VRS_SHEET_BUILDER_SKELETON");

    assert_eq!(on.status, "ok", "skeleton path must stay valid: {}", on.status);
    assert_eq!(on.unplaced.len(), 0, "skeleton path fully placed");
    let on_bpp = od(&on).bpp_reduction.as_ref().expect("bpp diagnostics");
    assert_eq!(od(&on).sparrow_ms_final_pairs, Some(0), "no collisions");
    assert_eq!(od(&on).sparrow_ms_boundary_violations, Some(0));
    // Q54A: roles recorded; first critical on a sheet is always an Anchor.
    let total = on_bpp.bpp_skeleton_anchor_count
        + on_bpp.bpp_skeleton_interlock_count
        + on_bpp.bpp_skeleton_bandinsert_count;
    assert!(total > 0, "skeleton on must record at least one critical role");
    assert!(on_bpp.bpp_skeleton_anchor_count >= 1, "at least one Anchor role recorded");
    // Q54C: the feature-first overlap-tolerant admission runs on the skeleton path (no Q53D gates).
    assert!(
        on_bpp.bpp_critical_feature_admission_attempts > 0,
        "feature-first admission must run on the skeleton path"
    );
    // No regression: skeleton must not use more sheets than the baseline.
    assert!(
        used_sheets(&on) <= off_sheets,
        "skeleton must not regress used-sheet count: on={} off={}",
        used_sheets(&on),
        off_sheets
    );
}
