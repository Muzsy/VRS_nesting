//! SGH-Q66 - production SheetFeasibilityHints cutover on the real solve boundary.

use std::path::PathBuf;
use std::sync::Mutex;

use vrs_solver::adapter::solve;
use vrs_solver::io::{BppReductionDiagnostics, SolverInput, SolverOutput};

static ENV_LOCK: Mutex<()> = Mutex::new(());

const BASE_GATES: &[&str] = &["VRS_SHEET_BUILDER"];
const HINT_GATES: &[&str] = &["VRS_SHEET_BUILDER", "VRS_SHEET_FEASIBILITY_HINTS"];
const SP8: &str = "artifacts/benchmarks/sgh_q51/inputs/q51_6big_sp8.json";

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("..")
        .join("..")
}

fn clear_gates() {
    for k in ["VRS_SHEET_BUILDER", "VRS_SHEET_FEASIBILITY_HINTS"] {
        std::env::remove_var(k);
    }
}

fn load(qty: i64, stock_qty: i64) -> SolverInput {
    let raw = std::fs::read_to_string(repo_root().join(SP8)).unwrap();
    let mut v: serde_json::Value = serde_json::from_str(&raw).unwrap();
    v["parts"][0]["quantity"] = serde_json::json!(qty);
    v["stocks"][0]["quantity"] = serde_json::json!(stock_qty);
    v["time_limit_s"] = serde_json::json!(8);
    serde_json::from_value(v).unwrap()
}

fn solve_with(gates: &[&str], qty: i64, stock_qty: i64) -> SolverOutput {
    let _g = ENV_LOCK.lock().unwrap();
    clear_gates();
    for k in gates {
        std::env::set_var(k, "1");
    }
    let out = solve(load(qty, stock_qty)).expect("solve");
    clear_gates();
    out
}

fn bpp(out: &SolverOutput) -> BppReductionDiagnostics {
    out.optimizer_diagnostics
        .as_ref()
        .and_then(|d| d.bpp_reduction.clone())
        .expect("bpp diagnostics")
}

#[test]
fn production_sheet_feasibility_cutover_emits_live_builder_diagnostics() {
    let off = solve_with(BASE_GATES, 6, 3);
    let on = solve_with(HINT_GATES, 6, 3);
    let d_off = bpp(&off);
    let d_on = bpp(&on);

    assert!(
        !d_off.bpp_sheet_feasibility_hints_used,
        "gate-off run must preserve the legacy builder diagnostics"
    );
    assert!(
        d_off.bpp_target_critical_distribution.is_empty(),
        "gate-off run must not emit hint target distribution"
    );

    assert!(
        d_on.bpp_sheet_feasibility_hints_used,
        "gate-on run must report live hint consumption"
    );
    assert!(
        !d_on.bpp_target_critical_distribution.is_empty(),
        "gate-on run must expose target critical distributions"
    );
    assert!(
        !d_on.bpp_sheet_target_quota.is_empty(),
        "gate-on run must expose target quotas"
    );
    assert!(
        d_on.bpp_q61_best_partial_tracker_enabled,
        "hint cutover must enable the production best-partial tracker"
    );
    assert!(
        d_on.bpp_hint_frontier_extension_applied,
        "LV8 repeated critical quota should extend the frontier under the hint gate"
    );
    assert!(
        d_on.bpp_sheet_target_quota
            .iter()
            .any(|(_, quota)| *quota > 0),
        "the live hint cutover must derive a positive per-sheet target quota"
    );
    if d_on.bpp_sheet_best_partial_critical_count > 0 {
        assert!(
            d_on.bpp_sheet_best_partial_source.is_some(),
            "non-zero best partial must record its source"
        );
    }

    let artifact = serde_json::json!({
        "gate_off": {
            "status": off.status,
            "placed": off.placements.len(),
            "max_per_sheet": d_off.bpp_max_critical_per_sheet,
            "sheet_feasibility_hints_used": d_off.bpp_sheet_feasibility_hints_used,
        },
        "gate_on": {
            "status": on.status,
            "placed": on.placements.len(),
            "max_per_sheet": d_on.bpp_max_critical_per_sheet,
            "sheet_feasibility_hints_used": d_on.bpp_sheet_feasibility_hints_used,
            "target_critical_distribution": d_on.bpp_target_critical_distribution,
            "sheet_target_quota": d_on.bpp_sheet_target_quota,
            "sheet_target_quota_met": d_on.bpp_sheet_target_quota_met,
            "sheet_best_partial_critical_count": d_on.bpp_sheet_best_partial_critical_count,
            "sheet_best_partial_source": d_on.bpp_sheet_best_partial_source,
            "hint_queue_reorder_applied": d_on.bpp_hint_queue_reorder_applied,
            "hint_frontier_extension_applied": d_on.bpp_hint_frontier_extension_applied,
            "hint_quota_abandoned_reason": d_on.bpp_hint_quota_abandoned_reason,
        }
    });
    let dir = repo_root().join("artifacts/benchmarks/sgh_q66");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(
        dir.join("sheet_feasibility_production_cutover.json"),
        serde_json::to_string_pretty(&artifact).expect("ser"),
    )
    .expect("write");
    assert!(dir
        .join("sheet_feasibility_production_cutover.json")
        .exists());
}
