//! JG-15 irregular sheet capability spike.
//!
//! Investigates whether the current code supports L-shaped (irregular/concave)
//! sheet boundaries natively, or whether a custom boundary validator is required.
//!
//! Tests:
//!   positive_control — item 20×20 at (10,10): fully inside L-shape → expect PASS
//!   negative_control — item 20×20 at (60,60): in L-shape notch → expect FAIL
//!
//! L-shape: (0,0)→(100,0)→(100,50)→(50,50)→(50,100)→(0,100)
//! Notch area: x∈[50,100], y∈[50,100] (top-right 50×50 corner missing from sheet)
//!
//! Outputs one line per finding, grep-able for decision:
//!   NATIVE_BOUNDARY_SUPPORT: YES | NO
//!   OWN_BOUNDARY_VALIDATOR_REQUIRED: YES | NO
//!   L_SHAPE_BOUNDARY_VIOLATION_DETECTED: YES | NO
//!   CURRENT_BBOX_ONLY_RISK_DETECTED: YES | NO
//!   DECISION: ...

use jagua_rs::geometry::geo_traits::CollidesWith;
use vrs_solver::geometry::{jag_edge_from_points, rect_corners, rect_edges, to_jag_point, Rect};
use vrs_solver::sheet::{rect_inside_sheet_shape, stock_to_shape, Stock};

fn make_l_shape_stock() -> Stock {
    Stock {
        id: "L1".to_string(),
        quantity: 1,
        width: None,
        height: None,
        outer_points: Some(vec![
            vrs_solver::geometry::PointInput::Pair([0.0, 0.0]),
            vrs_solver::geometry::PointInput::Pair([100.0, 0.0]),
            vrs_solver::geometry::PointInput::Pair([100.0, 50.0]),
            vrs_solver::geometry::PointInput::Pair([50.0, 50.0]),
            vrs_solver::geometry::PointInput::Pair([50.0, 100.0]),
            vrs_solver::geometry::PointInput::Pair([0.0, 100.0]),
        ]),
        holes_points: None,
    }
}

/// Boundary check using _outer_poly (the unused-by-current-code SPolygon).
/// Returns true only if ALL corners of rect are inside the outer polygon AND
/// no edge of the rect crosses any edge of the outer polygon.
fn rect_inside_outer_poly(rect: Rect, stock: &vrs_solver::sheet::SheetShape) -> bool {
    let corners = rect_corners(rect);
    for c in corners {
        if !stock._outer_poly.collides_with(&to_jag_point(c)) {
            return false;
        }
    }
    let r_edges = rect_edges(rect);
    for (a, b) in r_edges {
        let Some(re) = jag_edge_from_points(a, b) else { continue };
        for outer_edge in stock._outer_poly.edge_iter() {
            if re.collides_with(&outer_edge) {
                return false;
            }
        }
    }
    true
}

fn main() {
    let stock = make_l_shape_stock();
    let sheet = match stock_to_shape(&stock) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("ERROR: failed to build L-shape sheet: {e}");
            std::process::exit(1);
        }
    };

    // Positive control: item 20×20 at (10,10) — fully inside L-shape
    let pos_rect = Rect { x1: 10.0, y1: 10.0, x2: 30.0, y2: 30.0 };
    let pos_bbox = rect_inside_sheet_shape(pos_rect, &sheet);
    let pos_l = rect_inside_outer_poly(pos_rect, &sheet);

    // Negative control: item 20×20 at (60,60) — in the notch (outside L-shape)
    let neg_rect = Rect { x1: 60.0, y1: 60.0, x2: 80.0, y2: 80.0 };
    let neg_bbox = rect_inside_sheet_shape(neg_rect, &sheet);
    let neg_l = rect_inside_outer_poly(neg_rect, &sheet);

    println!("--- JG-15 Irregular Sheet Capability Spike ---");
    println!();
    println!("L-shape: (0,0)→(100,0)→(100,50)→(50,50)→(50,100)→(0,100)");
    println!("Notch:   x∈[50,100] y∈[50,100] (missing corner)");
    println!();
    println!("positive_control (10,10)→(30,30): bbox={pos_bbox} outer_poly={pos_l}");
    println!("negative_control (60,60)→(80,80): bbox={neg_bbox} outer_poly={neg_l}");
    println!();

    // --- Decision lines (grep-able) ---

    // _outer_poly is built in stock_to_shape but rect_inside_sheet_shape does not use it.
    // There is no native jagua-rs container/bin API exposed — only SPolygon + CollidesWith
    // primitives which we use manually here.
    println!("NATIVE_BOUNDARY_SUPPORT: NO");

    // Custom validator using _outer_poly + CollidesWith works and is required.
    let own_validator_required = neg_bbox && !neg_l;
    println!("OWN_BOUNDARY_VALIDATOR_REQUIRED: {}", if own_validator_required { "YES" } else { "NO" });

    // The L-shape boundary violation is correctly detected by outer_poly check.
    let violation_detected = !neg_l;
    println!("L_SHAPE_BOUNDARY_VIOLATION_DETECTED: {}", if violation_detected { "YES" } else { "NO" });

    // The current bbox-only check incorrectly passes the notch placement.
    let bbox_risk = neg_bbox;
    println!("CURRENT_BBOX_ONLY_RISK_DETECTED: {}", if bbox_risk { "YES" } else { "NO" });

    // Positive control must pass both checks.
    let positive_ok = pos_bbox && pos_l;
    println!("POSITIVE_CONTROL_PASS: {}", if positive_ok { "YES" } else { "NO" });

    let decision = if pos_l && !neg_l && neg_bbox {
        "OWN_BOUNDARY_VALIDATOR_PLUS_JAGUA_COLLISION"
    } else if !pos_l {
        "REVISE"
    } else {
        "REVISE"
    };
    println!("DECISION: {decision}");
    println!();

    if !positive_ok || !violation_detected || !bbox_risk {
        eprintln!("ERROR: unexpected spike result — manual review required");
        std::process::exit(1);
    }

    println!("Spike complete.");
}
