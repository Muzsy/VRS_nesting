//! SGH-Q26 — Single-sheet Sparrow validation suite.
//!
//! Staged validation for the production native `sparrow_cde` path, exercised
//! through the public crate boundary (`vrs_solver::adapter::solve` +
//! `vrs_solver::io::SolverInput`). Every scenario is a deliberately
//! **single-sheet** problem: exactly one stock with `quantity = 1`.
//!
//! Scope (SGH-Q26): this is a validation/correctness/stability suite only — no
//! solver algorithm changes, no compression, no multi-sheet gate, and no full
//! LV8 density benchmark. Positive fixtures must reach `status == "ok"`; the
//! negative overcapacity fixture must honestly report a partial/unsupported
//! result with diagnostics (never a silent `ok`).
//!
//! Diagnostics asserted on every positive fixture:
//!   - optimizer_diagnostics.pipeline_used == "sparrow_cde"
//!   - sparrow_invoked / sparrow_converged == Some(true)
//!   - sparrow_native_model_active / sparrow_native_tracker_active == Some(true)
//!   - sparrow_old_core_used == Some(false)
//!   - sparrow_compression_passes == Some(0)
//!   - loss_bbox_proxy_used_as_primary == Some(false)
//!   - collision_backend_diagnostics.backend_used == "cde_adapter"
//!   - collision_backend_diagnostics.bbox_fallback_queries == 0

use serde_json::Value;

use vrs_solver::adapter::solve;
use vrs_solver::io::{SolverInput, SolverOutput};

// ---------------------------------------------------------------------------
// Fixture loading + helpers
// ---------------------------------------------------------------------------

fn fixture_path(name: &str) -> std::path::PathBuf {
    std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/sgh_q26_single_sheet_validation")
        .join(name)
}

fn load_value(name: &str) -> Value {
    let raw = std::fs::read_to_string(fixture_path(name))
        .unwrap_or_else(|e| panic!("read fixture {name}: {e}"));
    serde_json::from_str(&raw).unwrap_or_else(|e| panic!("parse fixture {name}: {e}"))
}

/// Total requested instance count = sum of part quantities.
fn requested_count(v: &Value) -> usize {
    v["parts"]
        .as_array()
        .expect("parts array")
        .iter()
        .map(|p| p["quantity"].as_i64().expect("part.quantity") as usize)
        .sum()
}

/// Single-sheet contract guard: exactly one stock entry with quantity == 1.
fn assert_single_stock_quantity_one(v: &Value) {
    let stocks = v["stocks"].as_array().expect("stocks array");
    assert_eq!(stocks.len(), 1, "fixture must have exactly one stock entry");
    assert_eq!(
        stocks[0]["quantity"].as_i64(),
        Some(1),
        "the single stock must have quantity == 1"
    );
    assert_eq!(
        v["solver_profile"].as_str(),
        Some("jagua_optimizer_phase1_outer_only"),
        "fixture must use the production Phase1 profile"
    );
    assert_eq!(
        v["optimizer_pipeline"].as_str(),
        Some("sparrow_cde"),
        "fixture must route through optimizer_pipeline=sparrow_cde"
    );
    assert_eq!(
        v["collision_backend"].as_str(),
        Some("cde"),
        "fixture must route through collision_backend=cde"
    );
    assert_eq!(
        v["margin_mm"].as_f64(),
        Some(0.0),
        "single-sheet fixtures use margin_mm=0.0"
    );
}

fn solve_json(v: &Value) -> SolverOutput {
    let input: SolverInput =
        serde_json::from_value(v.clone()).expect("deserialize SolverInput from fixture");
    solve(input).expect("adapter::solve returns Ok(SolverOutput)")
}

/// Native Sparrow diagnostics that must hold for every positive `sparrow_cde` solve.
fn assert_native_sparrow_diagnostics(out: &SolverOutput) {
    let diag = out
        .optimizer_diagnostics
        .as_ref()
        .expect("optimizer_diagnostics present for sparrow_cde");
    assert_eq!(diag.pipeline_used, "sparrow_cde", "pipeline_used");
    assert_eq!(diag.sparrow_invoked, Some(true), "sparrow_invoked");
    assert_eq!(diag.sparrow_converged, Some(true), "sparrow_converged");
    assert_eq!(
        diag.sparrow_native_model_active,
        Some(true),
        "sparrow_native_model_active"
    );
    assert_eq!(
        diag.sparrow_native_tracker_active,
        Some(true),
        "sparrow_native_tracker_active"
    );
    assert_eq!(
        diag.sparrow_old_core_used,
        Some(false),
        "sparrow_old_core_used must be false"
    );
    assert_eq!(
        diag.sparrow_compression_passes,
        Some(0),
        "compression must be inactive (0 passes)"
    );
    assert_eq!(
        diag.loss_bbox_proxy_used_as_primary,
        Some(false),
        "bbox proxy must not be the primary production loss"
    );
}

/// CDE collision-backend diagnostics that must hold for every positive solve.
fn assert_cde_backend_diagnostics(out: &SolverOutput) {
    let b = out
        .collision_backend_diagnostics
        .as_ref()
        .expect("collision_backend_diagnostics present for sparrow_cde");
    assert_eq!(b.backend_used, "cde_adapter", "backend_used");
    assert_eq!(
        b.bbox_fallback_queries, 0,
        "no bbox fallback queries on the CDE path"
    );
}

/// Full positive single-sheet assertion bundle.
fn assert_positive_single_sheet_ok(out: &SolverOutput, requested: usize) {
    assert_eq!(out.status, "ok", "positive fixture must reach status==ok");
    assert_eq!(out.metrics.unplaced_count, 0, "unplaced_count must be 0");
    assert_eq!(
        out.metrics.placed_count, requested,
        "placed_count must equal requested_count"
    );
    assert!(
        out.placements.iter().all(|p| p.sheet_index == 0),
        "every placement must be on sheet_index 0"
    );
    assert_eq!(
        out.metrics.sheet_count_used, 1,
        "sheet_count_used must be exactly 1"
    );
    assert_native_sparrow_diagnostics(out);
    assert_cde_backend_diagnostics(out);
}

/// Deterministic same-seed equality: identical status, counts, and ordered placements.
fn assert_same_ordered_output(a: &SolverOutput, b: &SolverOutput) {
    assert_eq!(
        a.status, b.status,
        "status must match across same-seed runs"
    );
    assert_eq!(
        a.metrics.placed_count, b.metrics.placed_count,
        "placed_count must match"
    );
    assert_eq!(
        a.metrics.unplaced_count, b.metrics.unplaced_count,
        "unplaced_count must match"
    );
    assert_eq!(
        a.metrics.sheet_count_used, b.metrics.sheet_count_used,
        "sheet_count_used must match"
    );
    assert_eq!(
        a.placements.len(),
        b.placements.len(),
        "placement record count must match"
    );
    for (pa, pb) in a.placements.iter().zip(b.placements.iter()) {
        assert_eq!(pa.instance_id, pb.instance_id, "ordered instance_id");
        assert_eq!(pa.part_id, pb.part_id, "ordered part_id");
        assert_eq!(pa.sheet_index, pb.sheet_index, "ordered sheet_index");
        assert!((pa.x - pb.x).abs() < 1e-6, "x within epsilon");
        assert!((pa.y - pb.y).abs() < 1e-6, "y within epsilon");
        assert!(
            (pa.rotation_deg - pb.rotation_deg).abs() < 1e-6,
            "rotation_deg within epsilon"
        );
    }
}

// ---------------------------------------------------------------------------
// Level 1 — tiny / easy single-sheet
// ---------------------------------------------------------------------------

#[test]
fn q26_single_sheet_tiny_rectangles_all_placed() {
    let v = load_value("tiny_rectangles.json");
    assert_single_stock_quantity_one(&v);
    let requested = requested_count(&v);
    let out = solve_json(&v);
    assert_positive_single_sheet_ok(&out, requested);
}

// ---------------------------------------------------------------------------
// Level 2 — rotation required + irregular strict-CDE
// ---------------------------------------------------------------------------

#[test]
fn q26_single_sheet_requires_90_degree_rotation_all_placed() {
    let v = load_value("rotation_90_required.json");
    assert_single_stock_quantity_one(&v);
    let requested = requested_count(&v);
    let out = solve_json(&v);
    assert_positive_single_sheet_ok(&out, requested);

    // Part P (350x150) is wider than the 300-wide sheet at 0°, so it can only be
    // placed when rotated 90°/270°. Proves the rotation axis is actually used.
    let p = out
        .placements
        .iter()
        .find(|pl| pl.part_id == "P")
        .expect("part P placed");
    let rot = ((p.rotation_deg % 360.0) + 360.0) % 360.0;
    assert!(
        (rot - 90.0).abs() < 1e-6 || (rot - 270.0).abs() < 1e-6,
        "part P must be placed at 90° or 270° (got {rot})"
    );
}

#[test]
fn q26_single_sheet_strict_cde_irregular_l_shape_mix_all_placed() {
    let v = load_value("irregular_l_shape_mix.json");
    assert_single_stock_quantity_one(&v);
    // Sanity: the irregular part carries an explicit outer polygon (honored by CDE).
    let l_part = v["parts"]
        .as_array()
        .unwrap()
        .iter()
        .find(|p| p["id"] == "L")
        .expect("L part present");
    assert!(
        l_part["outer_points"]
            .as_array()
            .map_or(false, |a| a.len() >= 5),
        "L part must define a concave outer polygon"
    );
    let requested = requested_count(&v);
    let out = solve_json(&v);
    assert_positive_single_sheet_ok(&out, requested);
}

// ---------------------------------------------------------------------------
// Level 3 — medium single-sheet
// ---------------------------------------------------------------------------

#[test]
fn q26_single_sheet_medium_rect_mix_all_placed() {
    let v = load_value("medium_rect_mix.json");
    assert_single_stock_quantity_one(&v);
    let requested = requested_count(&v);
    assert!(
        (15..=30).contains(&requested),
        "medium rect mix should hold 15-30 instances (got {requested})"
    );
    let out = solve_json(&v);
    assert_positive_single_sheet_ok(&out, requested);
}

#[test]
fn q26_single_sheet_medium_mixed_rotations_all_placed() {
    let v = load_value("medium_mixed_rotations.json");
    assert_single_stock_quantity_one(&v);
    let requested = requested_count(&v);
    assert!(
        (15..=35).contains(&requested),
        "medium mixed rotations should hold 15-35 instances (got {requested})"
    );
    let out = solve_json(&v);
    assert_positive_single_sheet_ok(&out, requested);
}

// ---------------------------------------------------------------------------
// Level 4A — serious synthetic 40-80 instance single sheet
// ---------------------------------------------------------------------------

#[test]
fn q26_single_sheet_serious_synthetic_40_to_80_instances_all_placed() {
    let v = load_value("serious_synthetic_single_sheet.json");
    assert_single_stock_quantity_one(&v);
    let requested = requested_count(&v);
    assert!(
        (40..=80).contains(&requested),
        "serious synthetic must hold 40-80 instances (got {requested})"
    );
    let out = solve_json(&v);
    assert_positive_single_sheet_ok(&out, requested);
}

// ---------------------------------------------------------------------------
// Determinism — same seed, same ordered output
// ---------------------------------------------------------------------------

#[test]
fn q26_single_sheet_deterministic_same_seed_same_output() {
    let v = load_value("medium_rect_mix.json");
    assert_single_stock_quantity_one(&v);
    let requested = requested_count(&v);
    let out_a = solve_json(&v);
    let out_b = solve_json(&v);
    assert_positive_single_sheet_ok(&out_a, requested);
    assert_positive_single_sheet_ok(&out_b, requested);
    assert_same_ordered_output(&out_a, &out_b);
}

// ---------------------------------------------------------------------------
// Negative — overcapacity must report partial/unsupported honestly
// ---------------------------------------------------------------------------

#[test]
fn q26_single_sheet_negative_overcapacity_reports_partial_with_diagnostics() {
    let v = load_value("negative_overcapacity.json");
    assert_single_stock_quantity_one(&v);
    let out = solve_json(&v);

    // Honest non-ok result: never silently "ok" when the instances cannot all be
    // placed feasibly on one sheet. The native Sparrow core keeps every item in an
    // (overlapping / boundary-violating) layout and reports it as non-feasible, so
    // the authoritative signal is the status + non-convergence diagnostics — this
    // test deliberately does NOT require any item to be reported unplaced.
    assert_ne!(
        out.status, "ok",
        "overcapacity must NOT report ok (status={})",
        out.status
    );
    assert!(
        out.status == "partial" || out.status == "unsupported",
        "overcapacity status must be partial or unsupported (got {})",
        out.status
    );

    // Diagnostics are preserved on the partial/unsupported path.
    let diag = out
        .optimizer_diagnostics
        .as_ref()
        .expect("optimizer_diagnostics preserved on overcapacity");
    assert_eq!(diag.pipeline_used, "sparrow_cde");
    assert_eq!(diag.sparrow_invoked, Some(true), "sparrow was invoked");
    assert_eq!(
        diag.sparrow_converged,
        Some(false),
        "overcapacity must NOT report convergence"
    );
    assert_eq!(
        diag.sparrow_old_core_used,
        Some(false),
        "old core not used even on the negative path"
    );
    // Residual infeasibility evidence: unresolved collisions and/or boundary
    // violations remain (the layout could not be made feasible on one sheet).
    let residual_pairs = diag.sparrow_collision_graph_final_pairs.unwrap_or(0);
    let residual_boundary = diag.sparrow_boundary_violations_final.unwrap_or(0);
    assert!(
        residual_pairs > 0 || residual_boundary > 0,
        "overcapacity must leave residual collisions/boundary violations \
         (final_pairs={residual_pairs}, final_boundary={residual_boundary})"
    );

    // The CDE backend diagnostics are still surfaced honestly on the negative path.
    let b = out
        .collision_backend_diagnostics
        .as_ref()
        .expect("collision_backend_diagnostics preserved on overcapacity");
    assert_eq!(b.backend_used, "cde_adapter");
    assert_eq!(b.bbox_fallback_queries, 0);
}

// ---------------------------------------------------------------------------
// SGH-Q28 — Dense 191-instance incremental-session benchmark gate
// ---------------------------------------------------------------------------

/// Benchmark gate: 191-instance LV8-derived single-sheet problem with
/// incremental CDE session reuse (T02-T04). Marked `#[ignore]` because it
/// runs for up to 90 s; invoke explicitly with `-- --ignored` or
/// `--test-threads=1 --include-ignored`.
///
/// Pass criteria:
///   - `sparrow_dense_real_run == true`        (SparrowDenseLargeScale fired)
///   - `sparrow_iterations >= 1`               (at least one full separation iteration)
///   - `sparrow_collision_graph_final_pairs < 200`  (pairs down from seeding ~298)
#[test]
#[ignore]
fn q28_dense_191_incremental_session_speedup() {
    let fixture_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/sgh_q28_dense191_benchmark/dense_191_lv8_derived.json");
    let raw =
        std::fs::read_to_string(&fixture_path).unwrap_or_else(|e| panic!("read Q28 fixture: {e}"));
    let fixture: serde_json::Value =
        serde_json::from_str(&raw).unwrap_or_else(|e| panic!("parse Q28 fixture: {e}"));

    let input = SolverInput {
        contract_version: fixture["contract_version"]
            .as_str()
            .unwrap_or("v1")
            .to_string(),
        project_name: "q28_dense_191_incremental_session_speedup".to_string(),
        seed: 17,
        time_limit_s: 90,
        stocks: serde_json::from_value(fixture["stocks"].clone()).expect("deserialize stocks"),
        parts: serde_json::from_value(fixture["parts"].clone()).expect("deserialize parts"),
        optimizer_pipeline: Some(vrs_solver::io::OptimizerPipelineKind::SparrowCde),
        collision_backend: Some(vrs_solver::io::CollisionBackendKind::Cde),
        solver_profile: Some("jagua_optimizer_phase1_outer_only".to_string()),
        margin_mm: None,
        spacing_mm: None,
        kerf_mm: None,
        rotation_policy: None,
    };

    let total_instances: usize = input.parts.iter().map(|p| p.quantity as usize).sum();
    assert_eq!(
        total_instances, 191,
        "fixture must have exactly 191 instances"
    );

    let out = solve(input).expect("adapter::solve returns Ok");

    let diag = out
        .optimizer_diagnostics
        .as_ref()
        .expect("optimizer_diagnostics must be present");

    assert_eq!(diag.pipeline_used, "sparrow_cde", "pipeline_used");
    assert_eq!(
        diag.sparrow_native_model_active,
        Some(true),
        "native model active"
    );
    assert_eq!(
        diag.sparrow_native_tracker_active,
        Some(true),
        "native tracker active"
    );
    assert_eq!(diag.sparrow_old_core_used, Some(false), "old core not used");

    let dense_real_run = diag.sparrow_dense_real_run;
    assert_eq!(
        dense_real_run,
        Some(true),
        "sparrow_dense_real_run must be true for 191-instance input (got {dense_real_run:?})"
    );

    let iterations = diag.sparrow_iterations.unwrap_or(0);
    assert!(
        iterations >= 1,
        "sparrow_iterations must be >= 1 (got {iterations}); \
         at least one full separation iteration must complete in 90s"
    );

    let final_pairs = diag
        .sparrow_collision_graph_final_pairs
        .unwrap_or(usize::MAX);
    assert!(
        final_pairs < 200,
        "sparrow_collision_graph_final_pairs must be < 200 (got {final_pairs}); \
         pairs must trend down from seeding (~298 typical)"
    );
}
