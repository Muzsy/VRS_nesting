//! JG-04 jagua adapter PoC smoke binary.
//!
//! Verifies three cases via the JaguaAdapter contract:
//!   1. item_item_non_overlap — two disjoint rects → no collision
//!   2. item_item_overlap     — two overlapping rects → collision detected
//!   3. item_sheet_boundary   — item inside sheet ok; item outside sheet rejected
//!
//! Outputs stable JSON so the Python smoke script can assert on it.

use vrs_solver::adapter::JaguaAdapter;
use vrs_solver::geometry::{Point, Rect};
use vrs_solver::sheet::{stock_to_shape, Stock};

fn rect_poly(x1: f64, y1: f64, x2: f64, y2: f64) -> Vec<Point> {
    vec![
        Point { x: x1, y: y1 },
        Point { x: x2, y: y1 },
        Point { x: x2, y: y2 },
        Point { x: x1, y: y2 },
    ]
}

fn main() {
    let mut all_pass = true;
    let mut case_non_overlap = false;
    let mut case_overlap = false;
    let mut case_boundary = false;

    // -----------------------------------------------------------------------
    // Case 1: item-item non-overlap
    // Rect A = (0,0)-(50,50), Rect B = (100,0)-(150,50) — completely disjoint
    // -----------------------------------------------------------------------
    let poly_a = rect_poly(0.0, 0.0, 50.0, 50.0);
    let poly_b = rect_poly(100.0, 0.0, 150.0, 50.0);
    match JaguaAdapter::check_polygon_collision(&poly_a, &poly_b) {
        Ok(false) => {
            case_non_overlap = true;
        }
        Ok(true) => {
            eprintln!("FAIL item_item_non_overlap: expected no collision, got collision");
            all_pass = false;
        }
        Err(e) => {
            eprintln!("FAIL item_item_non_overlap: error: {e}");
            all_pass = false;
        }
    }

    // -----------------------------------------------------------------------
    // Case 2: item-item overlap
    // Rect A = (0,0)-(100,100), Rect B = (60,60)-(160,160)
    // B's corner (60,60) is strictly inside A → collision
    // -----------------------------------------------------------------------
    let poly_c = rect_poly(0.0, 0.0, 100.0, 100.0);
    let poly_d = rect_poly(60.0, 60.0, 160.0, 160.0);
    match JaguaAdapter::check_polygon_collision(&poly_c, &poly_d) {
        Ok(true) => {
            case_overlap = true;
        }
        Ok(false) => {
            eprintln!("FAIL item_item_overlap: expected collision, got no collision");
            all_pass = false;
        }
        Err(e) => {
            eprintln!("FAIL item_item_overlap: error: {e}");
            all_pass = false;
        }
    }

    // -----------------------------------------------------------------------
    // Case 3: item-sheet boundary
    // Sheet 200x200; item_inside (50,50)-(100,100) must be accepted;
    // item_outside (180,180)-(220,220) must be rejected.
    // -----------------------------------------------------------------------
    let stock = Stock {
        id: "SMOKE_SHEET".to_string(),
        quantity: 1,
        width: Some(200.0),
        height: Some(200.0),
        outer_points: None,
        holes_points: None,
        cost_per_use: None,
    };
    match stock_to_shape(&stock) {
        Ok(sheet) => {
            let inside = Rect { x1: 50.0, y1: 50.0, x2: 100.0, y2: 100.0 };
            let outside = Rect { x1: 180.0, y1: 180.0, x2: 220.0, y2: 220.0 };
            let inside_ok = JaguaAdapter::check_rect_in_sheet(inside, &sheet);
            let outside_rejected = !JaguaAdapter::check_rect_in_sheet(outside, &sheet);
            if inside_ok && outside_rejected {
                case_boundary = true;
            } else {
                eprintln!(
                    "FAIL item_sheet_boundary: inside_ok={inside_ok} outside_rejected={outside_rejected}"
                );
                all_pass = false;
            }
        }
        Err(e) => {
            eprintln!("FAIL item_sheet_boundary: sheet construction failed: {e}");
            all_pass = false;
        }
    }

    // -----------------------------------------------------------------------
    // JSON output — stable format for Python smoke assertions
    // -----------------------------------------------------------------------
    let status = if all_pass { "ok" } else { "fail" };
    let output = serde_json::json!({
        "status": status,
        "cases": {
            "item_item_non_overlap": case_non_overlap,
            "item_item_overlap": case_overlap,
            "item_sheet_boundary": case_boundary
        },
        "notes": ["f64_to_f32_conversion_used"]
    });
    println!("{}", serde_json::to_string_pretty(&output).unwrap());
    if !all_pass {
        std::process::exit(1);
    }
}
