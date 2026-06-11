//! SGH-Q35 — Part-part spacing final validator tests.
//!
//! Proves the validator uses the FULL transformed part polygon (not a bbox proxy),
//! compares only same-sheet placements, treats touching/overlap as distance 0, and
//! handles rotation and invalid polygons conservatively.

use serde_json::json;
use vrs_solver::io::Placement;
use vrs_solver::item::Part;
use vrs_solver::technology::spacing::{
    count_part_spacing_violations, find_part_spacing_violations,
};

// ── Helpers ──────────────────────────────────────────────────────────────────

fn rect_part(id: &str, w: f64, h: f64) -> Part {
    serde_json::from_value(json!({
        "id": id, "width": w, "height": h, "quantity": 1,
        "allowed_rotations_deg": [0],
        "outer_points": [[0.0,0.0],[w,0.0],[w,h],[0.0,h]]
    }))
    .expect("parse rect part")
}

fn rect_part_no_polygon(id: &str, w: f64, h: f64) -> Part {
    serde_json::from_value(json!({
        "id": id, "width": w, "height": h, "quantity": 1,
        "allowed_rotations_deg": [0]
    }))
    .expect("parse rect part (no polygon)")
}

/// width/height 100×100 but a small triangle polygon — bbox and polygon disagree.
fn triangle_part(id: &str) -> Part {
    serde_json::from_value(json!({
        "id": id, "width": 100.0, "height": 100.0, "quantity": 1,
        "allowed_rotations_deg": [0],
        "outer_points": [[0.0,0.0],[20.0,0.0],[0.0,20.0]]
    }))
    .expect("parse triangle part")
}

fn invalid_part(id: &str) -> Part {
    // outer_points with only 2 points → PolygonExtraction::Invalid.
    serde_json::from_value(json!({
        "id": id, "width": 20.0, "height": 20.0, "quantity": 1,
        "allowed_rotations_deg": [0],
        "outer_points": [[0.0,0.0],[1.0,1.0]]
    }))
    .expect("parse invalid part")
}

fn pl(instance_id: &str, part_id: &str, sheet: usize, x: f64, y: f64, rot: f64) -> Placement {
    Placement {
        instance_id: instance_id.to_string(),
        part_id: part_id.to_string(),
        sheet_index: sheet,
        x,
        y,
        rotation_deg: rot,
    }
}

// ── Test 1: rectangles spacing ok ─────────────────────────────────────────────

#[test]
fn rectangles_spacing_ok() {
    let parts = vec![rect_part("P", 20.0, 20.0)];
    let placements = vec![
        pl("A", "P", 0, 0.0, 0.0, 0.0),
        pl("B", "P", 0, 25.0, 0.0, 0.0), // gap = 5.0 exactly
    ];
    assert_eq!(count_part_spacing_violations(&placements, &parts, 5.0), 0);
}

// ── Test 2: rectangles spacing violation ──────────────────────────────────────

#[test]
fn rectangles_spacing_violation() {
    let parts = vec![rect_part("P", 20.0, 20.0)];
    let placements = vec![
        pl("A", "P", 0, 0.0, 0.0, 0.0),
        pl("B", "P", 0, 24.9, 0.0, 0.0), // gap = 4.9 < 5.0
    ];
    let v = find_part_spacing_violations(&placements, &parts, 5.0);
    assert_eq!(v.len(), 1);
    assert!((v[0].distance_mm - 4.9).abs() < 1e-3, "distance {}", v[0].distance_mm);
    assert_eq!(v[0].required_spacing_mm, 5.0);
}

// ── Test 3: touching parts violate positive spacing ───────────────────────────

#[test]
fn touching_parts_violate_positive_spacing() {
    let parts = vec![rect_part("P", 20.0, 20.0)];
    let placements = vec![
        pl("A", "P", 0, 0.0, 0.0, 0.0),
        pl("B", "P", 0, 20.0, 0.0, 0.0), // touching at x=20 → distance 0
    ];
    assert_eq!(count_part_spacing_violations(&placements, &parts, 1.0), 1);
}

// ── Test 4: same geometry with spacing 0 is ok ────────────────────────────────

#[test]
fn touching_with_zero_spacing_ok() {
    let parts = vec![rect_part("P", 20.0, 20.0)];
    let placements = vec![
        pl("A", "P", 0, 0.0, 0.0, 0.0),
        pl("B", "P", 0, 20.0, 0.0, 0.0),
    ];
    assert_eq!(count_part_spacing_violations(&placements, &parts, 0.0), 0);
}

// ── Test 5: different sheets ignored ──────────────────────────────────────────

#[test]
fn different_sheets_ignored() {
    let parts = vec![rect_part("P", 20.0, 20.0)];
    let placements = vec![
        pl("A", "P", 0, 0.0, 0.0, 0.0),
        pl("B", "P", 1, 0.0, 0.0, 0.0), // same coords but different sheet
    ];
    assert_eq!(count_part_spacing_violations(&placements, &parts, 100.0), 0);
}

// ── Test 6: non-rect polygon proves non-bbox behavior ─────────────────────────

#[test]
fn non_rect_polygon_proves_non_bbox() {
    // Two triangles (small polygons) inside large 100×100 declared bboxes.
    // Polygon distance is large (~28); bbox distance would be 0 (overlapping bboxes).
    let parts = vec![triangle_part("T")];
    let placements = vec![
        pl("A", "T", 0, 0.0, 0.0, 0.0),
        pl("B", "T", 0, 30.0, 30.0, 0.0),
    ];
    // A bbox-based validator would flag a violation (bboxes overlap). The polygon
    // validator must NOT, since actual triangle distance >> 5.
    let v = find_part_spacing_violations(&placements, &parts, 5.0);
    assert!(v.is_empty(), "polygon distance >= 5; expected no violation, got {v:?}");
}

#[test]
fn non_rect_polygon_close_violates() {
    // Triangles placed so their actual polygons are < 5 apart.
    let parts = vec![triangle_part("T")];
    let placements = vec![
        pl("A", "T", 0, 0.0, 0.0, 0.0),   // hypotenuse near x+y=20
        pl("B", "T", 0, 22.0, 0.0, 0.0),  // its (0,0)->world (22,0): close to A's edge
    ];
    let v = find_part_spacing_violations(&placements, &parts, 5.0);
    assert_eq!(v.len(), 1, "close triangles must violate, got {v:?}");
}

// ── Test 7: rotated polygon spacing ───────────────────────────────────────────

#[test]
fn rotated_polygon_spacing() {
    let parts = vec![triangle_part("T")];

    // B rotated 45° but placed far away → no violation.
    let far = vec![
        pl("A", "T", 0, 0.0, 0.0, 0.0),
        pl("B", "T", 0, 60.0, 60.0, 45.0),
    ];
    assert!(
        find_part_spacing_violations(&far, &parts, 5.0).is_empty(),
        "rotated triangle far away must not violate"
    );

    // B rotated 45° but placed adjacent to A → violation.
    let near = vec![
        pl("A", "T", 0, 0.0, 0.0, 0.0),
        pl("B", "T", 0, 2.0, 2.0, 45.0),
    ];
    assert_eq!(
        find_part_spacing_violations(&near, &parts, 5.0).len(),
        1,
        "rotated triangle adjacent must violate"
    );
}

// ── Rectangle fallback (no outer_points) still works ──────────────────────────

#[test]
fn rectangle_fallback_spacing() {
    let parts = vec![rect_part_no_polygon("R", 20.0, 20.0)];
    // gap = 5 → ok
    let ok = vec![
        pl("A", "R", 0, 0.0, 0.0, 0.0),
        pl("B", "R", 0, 25.0, 0.0, 0.0),
    ];
    assert_eq!(count_part_spacing_violations(&ok, &parts, 5.0), 0);
    // gap = 3 → violation
    let bad = vec![
        pl("A", "R", 0, 0.0, 0.0, 0.0),
        pl("B", "R", 0, 23.0, 0.0, 0.0),
    ];
    assert_eq!(count_part_spacing_violations(&bad, &parts, 5.0), 1);
}

// ── Test 8: invalid polygon conservative violation ────────────────────────────

#[test]
fn invalid_polygon_conservative_violation() {
    let parts = vec![invalid_part("BAD"), rect_part("GOOD", 20.0, 20.0)];
    let placements = vec![
        pl("A", "BAD", 0, 0.0, 0.0, 0.0),
        pl("B", "GOOD", 0, 100.0, 100.0, 0.0), // far away, but BAD is invalid
    ];
    // Invalid polygon must be treated conservatively as a violation, not silently ok.
    assert_eq!(count_part_spacing_violations(&placements, &parts, 5.0), 1);
}
