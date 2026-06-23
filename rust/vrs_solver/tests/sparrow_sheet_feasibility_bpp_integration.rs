//! SGH-Q58B — SheetFeasibilityHints → BPP/sheet-builder integration test + artifact.
//!
//! Builds the Q58A hints for the real LV8 family, derives per-sheet target quotas, and exercises the
//! best-partial preservation invariant on a focused sheet-attempt sequence: a valid 2/3 partial found
//! first must never be displaced by a later valid 1/3 result. Emits the artifact under
//! `artifacts/benchmarks/sgh_q58b/`.

use std::path::PathBuf;

use vrs_solver::item::Part;
use vrs_solver::optimizer::sparrow::sheet_feasibility::build_sheet_feasibility_hints;
use vrs_solver::optimizer::sparrow::sheet_feasibility_bpp::{
    build_hint_diagnostics, hint_aware_critical_order, sheet_target_quotas, BestPartialTracker,
    CriticalIncumbent,
};
use vrs_solver::rotation_policy::RotationPolicyKind;

fn repo_root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join("..")
}

fn lv8(qty: i64) -> Part {
    let fixture = repo_root().join("artifacts/benchmarks/sgh_q51/inputs/q51_6big_sp8.json");
    let raw = std::fs::read_to_string(&fixture).expect("read fixture");
    let doc: serde_json::Value = serde_json::from_str(&raw).expect("parse");
    let p = &doc["parts"][0];
    Part {
        id: p["id"].as_str().unwrap().to_string(),
        width: p["width"].as_f64().unwrap(),
        height: p["height"].as_f64().unwrap(),
        quantity: qty,
        allowed_rotations_deg: vec![],
        rotation_policy: Some(RotationPolicyKind::Continuous),
        holes_points: None,
        prepared_holes_points: None,
        outer_points: Some(p["outer_points"].clone()),
        prepared_outer_points: None,
    }
}

#[test]
fn lv8_hint_integration_preserves_best_partial_and_reports_quota() {
    let parts = vec![lv8(6)];
    let hints = build_sheet_feasibility_hints(&parts, 1500.0, 3000.0, 5.0, 8.0).expect("hints");

    let quotas = sheet_target_quotas(&hints);
    assert!(!quotas.is_empty(), "must derive at least one target quota");
    let order = hint_aware_critical_order(&hints);
    assert!(order.iter().any(|id| id.starts_with("Lv8")), "LV8 must be in the hint-aware order");
    let diag = build_hint_diagnostics(&hints, true);
    assert!(diag.hints_used);

    // Focused sheet-attempt sequence (the values stand in for exact-validated upstream layouts):
    //   sheet 0: try quota=3 → find a valid 2/3, then a deeper attempt only yields a valid 1/3.
    // The best-partial tracker must keep the 2/3.
    let mut tracker = BestPartialTracker::new();
    let mut attempts: Vec<serde_json::Value> = Vec::new();

    // attempt A: valid 2/3
    let took_a = tracker.offer(CriticalIncumbent {
        critical_count: 2,
        placed_area: 2.0 * 1_846_000.0,
        free_space_score: 1.2e6,
        hint_target_met: false,
        source: "anchor+interlock".to_string(),
    });
    attempts.push(serde_json::json!({
        "attempt": "anchor+interlock", "critical_placed": 2, "became_incumbent": took_a,
        "best_partial_count": tracker.best_critical_count()
    }));

    // attempt B: valid 1/3 (must NOT displace the 2/3)
    let took_b = tracker.offer(CriticalIncumbent {
        critical_count: 1,
        placed_area: 1_846_000.0,
        free_space_score: 2.5e6,
        hint_target_met: true,
        source: "anchor_only".to_string(),
    });
    attempts.push(serde_json::json!({
        "attempt": "anchor_only", "critical_placed": 1, "became_incumbent": took_b,
        "best_partial_count": tracker.best_critical_count()
    }));

    assert!(!took_b, "valid 1/3 must NOT displace the valid 2/3 incumbent");
    assert_eq!(tracker.best_critical_count(), 2, "best partial stays at 2/3");

    let target_quota = quotas
        .iter()
        .find(|q| q.part_id.starts_with("Lv8"))
        .map(|q| q.target_per_sheet)
        .unwrap_or(0);

    let artifact = serde_json::json!({
        "critical_distribution_hint": diag.target_critical_distribution
            .iter().map(|(id, d)| serde_json::json!({"part_id": id, "distribution": d})).collect::<Vec<_>>(),
        "hint_aware_order": order,
        "sheet_attempts": [{
            "sheet_index": 0,
            "target_quota": target_quota,
            "critical_candidates_attempted": 2,
            "critical_placed": tracker.best_critical_count(),
            "best_partial_count": tracker.best_critical_count(),
            "best_partial_source": tracker.best().map(|b| b.source.clone()),
            "quota_met": tracker.best_critical_count() >= target_quota,
            "abandoned_reason": "deeper_attempt_only_yielded_1_of_3",
            "attempts": attempts,
        }],
        "best_partial_downgrades_rejected": tracker.downgrades_rejected(),
    });
    let dir = repo_root().join("artifacts/benchmarks/sgh_q58b");
    std::fs::create_dir_all(&dir).expect("mkdir");
    std::fs::write(
        dir.join("sheet_builder_hints_integration.json"),
        serde_json::to_string_pretty(&artifact).expect("ser"),
    )
    .expect("write");
    assert!(dir.join("sheet_builder_hints_integration.json").exists());
}
