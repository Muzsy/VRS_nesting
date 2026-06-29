//! SGH-Q51 — Critical-aware constructive sheet builder integration tests.
//!
//! Exercises the opt-in `VRS_SHEET_BUILDER` path through the public `adapter::solve` boundary on
//! the `sparrow_cde_multisheet` (BPP) path. The builder seed is used only when it is complete and
//! fully feasible, otherwise it falls back to the LBF seed — so enabling it never regresses the
//! result. All tests set the same env value (no intra-binary race); the OFF path is covered by the
//! existing multisheet/density suites.

use serde_json::{json, Value};
use std::sync::{Mutex, MutexGuard};
use vrs_solver::adapter::solve;
use vrs_solver::io::{OptimizerDiagnosticsOutput, SolverInput, SolverOutput};

// These tests mutate process-global env vars (VRS_*) with DIFFERENT values per test (e.g. the Q73
// row-seed vs the Q74 edge-interlock gate), so they must run serially even under the default parallel
// test harness — otherwise one test's gate leaks into another. Acquire this lock for the whole test.
static ENV_LOCK: Mutex<()> = Mutex::new(());
fn env_guard() -> MutexGuard<'static, ()> {
    ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner())
}

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
        "contract_version": "v1", "project_name": "sgh_q51_test", "seed": seed, "time_limit_s": t,
        "stocks": stocks, "solver_profile": "jagua_optimizer_phase1_outer_only", "margin_mm": 0.0,
        "optimizer_pipeline": "sparrow_cde_multisheet", "collision_backend": "cde", "parts": parts,
    })
}

fn solve_json(v: &Value) -> SolverOutput {
    let input: SolverInput = serde_json::from_value(v.clone()).expect("parse SolverInput");
    solve(input).expect("solve")
}

fn od(out: &SolverOutput) -> &OptimizerDiagnosticsOutput {
    out.optimizer_diagnostics
        .as_ref()
        .expect("optimizer_diagnostics present")
}

#[test]
fn sheet_builder_produces_valid_layout() {
    let _env = env_guard();
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    let parts = vec![l_part("L", 4), rect_part("f", 12, 120.0, 120.0)];
    let stocks = vec![json!({"id": "S", "quantity": 3, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 42, 40));

    assert_eq!(
        out.status, "ok",
        "builder path must produce a valid layout: {}",
        out.status
    );
    assert_eq!(
        out.unplaced.len(),
        0,
        "no unplaced (fallback guarantees completeness)"
    );
    let d = od(&out);
    assert_eq!(d.sparrow_ms_final_pairs, Some(0), "no collisions");
    assert_eq!(d.sparrow_ms_boundary_violations, Some(0));
    let bpp = d.bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(
        bpp.bpp_sheet_builder_applied,
        "the builder must run when enabled"
    );
}

#[test]
fn sheet_builder_no_regression_on_fillers() {
    let _env = env_guard();
    // A filler-heavy fixture: the builder admits the (few) critical parts then fills; the result
    // must be valid and fully placed regardless of how the admission fares.
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    let parts = vec![l_part("L", 2), rect_part("f", 20, 100.0, 100.0)];
    let stocks = vec![json!({"id": "S", "quantity": 3, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 7, 40));

    assert_eq!(out.status, "ok");
    assert_eq!(out.unplaced.len(), 0);
    assert_eq!(od(&out).sparrow_ms_final_pairs, Some(0));
}

#[test]
fn forced_latest_mode_reports_lock_and_opens_multiple_sheets() {
    let _env = env_guard();
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    std::env::set_var("VRS_SHEET_BUILDER_FORCE_LATEST", "1");
    let parts = vec![rect_part("f", 80, 400.0, 200.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 42, 40));
    std::env::remove_var("VRS_SHEET_BUILDER_FORCE_LATEST");
    std::env::remove_var("VRS_SHEET_BUILDER");

    assert!(
        out.status == "ok" || out.status == "partial",
        "forced-latest run must stay on the solve boundary"
    );
    let bpp = od(&out).bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(bpp.bpp_q69_forced_latest_mode);
    assert!(!bpp.bpp_q69_native_seed_fallback_used);
    assert!(!bpp.bpp_q69_builder_random_bootstrap_used);
    assert_eq!(
        bpp.bpp_q69_seed_source.as_deref(),
        Some("builder_forced_latest")
    );
    assert!(
        bpp.bpp_sheets_opened >= 2,
        "forced-latest builder should reach multiple sheets on a 2-sheet workload"
    );
}

#[test]
fn forced_latest_anchor_policy_reports_when_center_is_not_silent_default() {
    let _env = env_guard();
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    std::env::set_var("VRS_SHEET_BUILDER_SKELETON", "1");
    std::env::set_var("VRS_FEATURE_CANDIDATES", "1");
    std::env::set_var("VRS_ANCHOR_CATALOG", "1");
    std::env::set_var("VRS_SHEET_BUILDER_FORCE_LATEST", "1");
    let parts = vec![l_part("L", 2), rect_part("f", 24, 100.0, 100.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 19, 40));
    std::env::remove_var("VRS_SHEET_BUILDER_FORCE_LATEST");
    std::env::remove_var("VRS_ANCHOR_CATALOG");
    std::env::remove_var("VRS_FEATURE_CANDIDATES");
    std::env::remove_var("VRS_SHEET_BUILDER_SKELETON");
    std::env::remove_var("VRS_SHEET_BUILDER");

    assert!(
        out.status == "ok" || out.status == "partial",
        "forced-latest anchor-policy fixture must stay on the solve boundary"
    );
    let bpp = od(&out).bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(bpp.bpp_q69_forced_latest_mode);
    if bpp.bpp_q68_anchor_competition_ran {
        assert!(
            bpp.bpp_q70_anchor_best_corner_score.is_some()
                || bpp.bpp_q70_anchor_best_center_score.is_some(),
            "Q70 diagnostics should capture anchor authority candidates once the anchor competition runs"
        );
    }
    if let Some(policy) = bpp.bpp_q61_accepted_anchor_secondary_policy.as_deref() {
        if policy.contains("center") {
            assert!(
                bpp.bpp_q70_anchor_center_override_used || bpp.bpp_q70_anchor_center_only_path,
                "center seating must now be explicit, not the silent default"
            );
        }
    }
    if let Some(gap_mm) = bpp.bpp_q71_anchor_final_min_edge_gap_mm {
        assert!(
            gap_mm <= 40.0,
            "forced-latest accepted anchor should stay flush-close to some sheet edge, got gap={gap_mm}"
        );
    }
    if bpp.bpp_q68_anchor_selected_path.as_deref() == Some("feature") {
        assert!(
            bpp.bpp_q71_anchor_final_min_edge_gap_mm.unwrap_or(999.0) <= 40.0,
            "forced-latest feature winner is only acceptable when it still stays edge-locked"
        );
    }
}

#[test]
fn forced_latest_seed_retains_all_instances_no_drop() {
    let _env = env_guard();
    // SGH-Q72: in forced-latest mode the seed handed to the optimizer must retain EVERY instance
    // (builder placements + re-inserted remainder), so the real exploration/redistribute pipeline
    // can pack them on the fixed sheets instead of the builder silently dropping parts before the
    // optimizer ever runs.
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    std::env::set_var("VRS_SHEET_BUILDER_SKELETON", "1");
    std::env::set_var("VRS_FEATURE_CANDIDATES", "1");
    std::env::set_var("VRS_ANCHOR_CATALOG", "1");
    std::env::set_var("VRS_SHEET_BUILDER_FORCE_LATEST", "1");
    // Over-subscribed 2-sheet workload so the greedy constructive builder cannot place every part in
    // its pass — this is exactly the case where the old path dropped parts; the no-drop completion
    // must re-insert the remainder into the seed.
    let total_qty = 120i64;
    let parts = vec![rect_part("f", total_qty, 400.0, 200.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 3000.0, "height": 1500.0})];
    let out = solve_json(&ms_input(parts, stocks, 42, 6));
    std::env::remove_var("VRS_SHEET_BUILDER_FORCE_LATEST");
    std::env::remove_var("VRS_ANCHOR_CATALOG");
    std::env::remove_var("VRS_FEATURE_CANDIDATES");
    std::env::remove_var("VRS_SHEET_BUILDER_SKELETON");
    std::env::remove_var("VRS_SHEET_BUILDER");

    assert!(
        out.status == "ok" || out.status == "partial",
        "no-drop forced-latest run must stay on the solve boundary"
    );
    let bpp = od(&out).bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(bpp.bpp_q69_forced_latest_mode);
    assert!(
        !bpp.bpp_q69_native_seed_fallback_used,
        "no-drop must NOT be a silent native-seed fallback (the smart critical seed is kept)"
    );
    assert!(
        bpp.bpp_q72_no_drop_seed_used,
        "forced-latest must complete the seed to a no-drop full-instance seed"
    );
    assert_eq!(
        bpp.bpp_q72_seed_instance_count_before_pipeline, total_qty as usize,
        "the seed handed to the optimizer must retain ALL instances before the pipeline runs"
    );
    assert_eq!(
        bpp.bpp_q72_seed_builder_placed_before_completion
            + bpp.bpp_q72_global_repack_reinserted_count,
        total_qty as usize,
        "builder-placed + re-inserted must account for every instance (no drop before the optimizer)"
    );
    assert!(
        bpp.bpp_q72_global_repack_reinserted_count > 0,
        "an over-subscribed greedy seed should leave parts for the no-drop completion to re-insert"
    );
}

#[test]
fn forced_latest_big_repeated_type_is_row_seeded_two_per_sheet() {
    let _env = env_guard();
    // SGH-Q73: a repeated BIG type must be distributed (fill a sheet before opening the next) at the
    // tightest CDE-clear pitch — instead of one-per-sheet at the min-bbox-width default.
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    std::env::set_var("VRS_SHEET_BUILDER_SKELETON", "1");
    std::env::set_var("VRS_FEATURE_CANDIDATES", "1");
    std::env::set_var("VRS_ANCHOR_CATALOG", "1");
    std::env::set_var("VRS_SHEET_BUILDER_FORCE_LATEST", "1");
    std::env::set_var("VRS_BIG_ROW_SEED", "1");
    // A big repeated rectangle (area well above the 4%-of-sheet threshold); two fit per 1500-wide
    // sheet, so the seeder should distribute 2 per sheet across the two sheets.
    let parts = vec![rect_part("big", 4, 600.0, 400.0), rect_part("f", 12, 120.0, 120.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 1500.0, "height": 3000.0})];
    let out = solve_json(&ms_input(parts, stocks, 42, 6));
    std::env::remove_var("VRS_BIG_ROW_SEED");
    std::env::remove_var("VRS_SHEET_BUILDER_FORCE_LATEST");
    std::env::remove_var("VRS_ANCHOR_CATALOG");
    std::env::remove_var("VRS_FEATURE_CANDIDATES");
    std::env::remove_var("VRS_SHEET_BUILDER_SKELETON");
    std::env::remove_var("VRS_SHEET_BUILDER");

    assert!(out.status == "ok" || out.status == "partial");
    let bpp = od(&out).bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(bpp.bpp_q69_forced_latest_mode);
    assert!(
        bpp.bpp_q73_big_row_seed_used,
        "forced-latest must row-seed the dominant repeated big type"
    );
    assert!(
        bpp.bpp_q73_big_row_rotation_deg.is_some(),
        "row seed must record the chosen orientation"
    );
    assert!(
        bpp.bpp_q73_big_row_copies_per_sheet >= 2,
        "two big parts must fit per 1500-wide sheet, got {}",
        bpp.bpp_q73_big_row_copies_per_sheet
    );
    assert!(
        bpp.bpp_q73_big_row_seeded_count >= 2,
        "the seeder must place at least two big copies, got {}",
        bpp.bpp_q73_big_row_seeded_count
    );
}

#[test]
fn forced_latest_edge_interlock_seed_pins_big_parts_through_pipeline() {
    let _env = env_guard();
    // SGH-Q74: the edge-anchored interlock seed must place the dominant big type AND keep it (pinned
    // fixed obstacle) through the exploration separator / gravity / sanitize — the Q73 regression was
    // that the unpinned exploration drifted the seed and ejected big parts.
    std::env::set_var("VRS_SHEET_BUILDER", "1");
    std::env::set_var("VRS_SHEET_BUILDER_SKELETON", "1");
    std::env::set_var("VRS_FEATURE_CANDIDATES", "1");
    std::env::set_var("VRS_ANCHOR_CATALOG", "1");
    std::env::set_var("VRS_SHEET_BUILDER_FORCE_LATEST", "1");
    std::env::set_var("VRS_EDGE_INTERLOCK_SEED", "1");
    // A big repeated rectangle (>4% of the sheet); two fit per 1500-wide sheet, plus fillers that the
    // pipeline must pack AROUND the pinned big parts.
    let parts = vec![rect_part("big", 4, 600.0, 400.0), rect_part("f", 12, 120.0, 120.0)];
    let stocks = vec![json!({"id": "S", "quantity": 2, "width": 1500.0, "height": 3000.0})];
    let out = solve_json(&ms_input(parts, stocks, 42, 8));
    std::env::remove_var("VRS_EDGE_INTERLOCK_SEED");
    std::env::remove_var("VRS_SHEET_BUILDER_FORCE_LATEST");
    std::env::remove_var("VRS_ANCHOR_CATALOG");
    std::env::remove_var("VRS_FEATURE_CANDIDATES");
    std::env::remove_var("VRS_SHEET_BUILDER_SKELETON");
    std::env::remove_var("VRS_SHEET_BUILDER");

    assert!(out.status == "ok" || out.status == "partial");
    let bpp = od(&out).bpp_reduction.as_ref().expect("bpp diagnostics");
    assert!(bpp.bpp_q69_forced_latest_mode);
    assert!(
        bpp.bpp_q74_edge_interlock_seed_used,
        "forced-latest must use the edge-anchored interlock seed"
    );
    assert!(
        bpp.bpp_q74_edge_interlock_locked_count >= 2,
        "the seeder must pin at least two big copies, got {}",
        bpp.bpp_q74_edge_interlock_locked_count
    );
    // Survival: at least the pinned count of big parts must remain in the final placements (the pin +
    // sanitize-protect keep them instead of ejecting them when a filler collides).
    let big_placed = out.placements.iter().filter(|p| p.part_id == "big").count();
    assert!(
        big_placed >= bpp.bpp_q74_edge_interlock_locked_count.min(2),
        "pinned big parts must survive the pipeline; big_placed={big_placed}, locked={}",
        bpp.bpp_q74_edge_interlock_locked_count
    );
}
