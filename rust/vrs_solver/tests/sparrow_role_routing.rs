//! SGH-Q55B — Role-routed candidate generation integration test.
//!
//! On the skeleton path the co-movable critical admission routes candidate generation by skeleton
//! role and fills per-role diagnostics. (The anchor role currently seats via the direct-insert path;
//! making the sheet-edge anchor primary is Q55C.) This proves the routing is live and no-regression.

use serde_json::{json, Value};
use vrs_solver::adapter::solve;
use vrs_solver::io::{OptimizerDiagnosticsOutput, SolverInput, SolverOutput};

fn l_part(id: &str, qty: i64) -> Value {
    json!({
        "id": id, "quantity": qty, "width": 1000.0, "height": 1000.0,
        "allowed_rotations_deg": [0, 90, 180, 270],
        "outer_points": [[0.0,0.0],[1000.0,0.0],[1000.0,300.0],[300.0,300.0],[300.0,1000.0],[0.0,1000.0]]
    })
}
fn rect_part(id: &str, qty: i64, w: f64, h: f64) -> Value {
    json!({ "id": id, "quantity": qty, "width": w, "height": h,
        "allowed_rotations_deg": [0,90,180,270], "outer_points": [[0.0,0.0],[w,0.0],[w,h],[0.0,h]] })
}
fn ms_input(parts: Vec<Value>, stocks: Vec<Value>) -> Value {
    json!({ "contract_version":"v1","project_name":"q55b","seed":42,"time_limit_s":40,
        "stocks":stocks,"solver_profile":"jagua_optimizer_phase1_outer_only","margin_mm":0.0,
        "optimizer_pipeline":"sparrow_cde_multisheet","collision_backend":"cde","parts":parts })
}
fn solve_json(v: &Value) -> SolverOutput {
    solve(serde_json::from_value::<SolverInput>(v.clone()).expect("parse")).expect("solve")
}
fn od(out: &SolverOutput) -> &OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics.as_ref().expect("diag")
}

#[test]
fn role_routing_fills_per_role_counts_and_no_regression() {
    let input = ms_input(
        vec![l_part("L", 4), rect_part("f", 12, 120.0, 120.0)],
        vec![json!({"id":"S","quantity":3,"width":3000.0,"height":1500.0})],
    );

    // skeleton OFF baseline.
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    std::env::remove_var("VRS_SHEET_BUILDER_SKELETON");
    let off = solve_json(&input);
    assert_eq!(off.status, "ok");
    let off_sheets = off
        .placements
        .iter()
        .map(|p| p.sheet_index)
        .collect::<std::collections::BTreeSet<_>>()
        .len();
    let ob = od(&off).bpp_reduction.as_ref().expect("bpp");
    assert_eq!(
        (
            ob.bpp_role_interlock_generated,
            ob.bpp_role_band_insert_generated
        ),
        (0, 0),
        "skeleton off must not route by role"
    );

    // skeleton ON.
    std::env::set_var("VRS_SHEET_BUILDER_SKELETON", "1");
    let on = solve_json(&input);
    std::env::remove_var("VRS_SHEET_BUILDER_SKELETON");
    assert_eq!(on.status, "ok");
    assert_eq!(on.unplaced.len(), 0);
    assert_eq!(od(&on).sparrow_ms_final_pairs, Some(0));
    let b = od(&on).bpp_reduction.as_ref().expect("bpp");
    // The role-routed co-movable admission generates candidates for the interlock/band roles.
    assert!(
        b.bpp_role_interlock_generated + b.bpp_role_band_insert_generated > 0,
        "role-routed candidate generation must be live on the skeleton path"
    );
    // No regression on used-sheet count.
    let on_sheets = on
        .placements
        .iter()
        .map(|p| p.sheet_index)
        .collect::<std::collections::BTreeSet<_>>()
        .len();
    assert!(
        on_sheets <= off_sheets,
        "skeleton must not regress used sheets: on={on_sheets} off={off_sheets}"
    );
}
