use jagua_rs::geometry::geo_traits::CollidesWith;
use jagua_rs::geometry::primitives::SPolygon;
use serde::Deserialize;

use crate::geometry::{
    jag_edge_from_points, point_from_input, polygon_area, polygon_bbox, rect_corners, rect_edges,
    to_jag_point, to_jag_polygon, Point, PointInput, Rect, EPS,
};

#[derive(Debug, Deserialize, Clone)]
pub struct Stock {
    pub id: String,
    pub quantity: i64,
    pub width: Option<f64>,
    pub height: Option<f64>,
    pub outer_points: Option<Vec<PointInput>>,
    pub holes_points: Option<Vec<Vec<PointInput>>>,
    /// Per-use cost for sheet-choice scoring (JG-19 V1 proxy).
    /// Default (None) → 1.0. Remnant stocks should be assigned a value < 1.0
    /// so the score model prefers them over full new sheets.
    /// This is a V1 nesting proxy; it is not a final inventory/costing field.
    #[serde(default)]
    pub cost_per_use: Option<f64>,
}

#[derive(Debug, Clone)]
pub struct SheetShape {
    pub min_x: f64,
    pub min_y: f64,
    pub max_x: f64,
    pub max_y: f64,
    pub width: f64,
    pub height: f64,
    /// True when stock was defined via explicit outer_points (possibly concave).
    /// When true, rect_inside_sheet_shape also checks corners/edges against _outer_poly.
    pub has_irregular_outer: bool,
    /// Outer polygon area in input units² (shoelace formula; equals width*height for rectangles).
    pub area: f64,
    /// Original polygon vertices in input order. Non-empty only when has_irregular_outer=true.
    /// Used by candidate generation for vertex-near, edge-near, and interior sampling.
    pub outer_vertices: Vec<Point>,
    /// Per-use cost for sheet-choice scoring (JG-19 V1 proxy). Default 1.0.
    /// Set from Stock.cost_per_use; clamped to >= 0.0.
    pub cost_per_use: f64,
    pub _outer_poly: SPolygon,
    pub hole_polys: Vec<SPolygon>,
}

/// Returns true if the stock has at least one non-empty hole polygon.
pub fn stock_has_holes(stock: &Stock) -> bool {
    match &stock.holes_points {
        Some(holes) => !holes.is_empty(),
        None => false,
    }
}

pub fn stock_to_shape(stock: &Stock) -> Result<SheetShape, String> {
    use crate::geometry::Point;

    let has_irregular_outer = stock.outer_points.is_some();

    let outer: Vec<Point> = if let Some(raw_outer) = &stock.outer_points {
        if raw_outer.len() < 3 {
            return Err(format!(
                "stock {} outer_points must have >=3 points",
                stock.id
            ));
        }
        raw_outer.iter().map(point_from_input).collect()
    } else {
        let w = stock
            .width
            .ok_or_else(|| format!("stock {} missing width", stock.id))?;
        let h = stock
            .height
            .ok_or_else(|| format!("stock {} missing height", stock.id))?;
        if w <= 0.0 || h <= 0.0 {
            return Err(format!("stock {} width/height must be > 0", stock.id));
        }
        vec![
            Point { x: 0.0, y: 0.0 },
            Point { x: w, y: 0.0 },
            Point { x: w, y: h },
            Point { x: 0.0, y: h },
        ]
    };

    let holes: Vec<Vec<crate::geometry::Point>> = match &stock.holes_points {
        None => Vec::new(),
        Some(raw_holes) => {
            let mut parsed = Vec::new();
            for hole in raw_holes {
                if hole.len() < 3 {
                    return Err(format!(
                        "stock {} hole polygon must have >=3 points",
                        stock.id
                    ));
                }
                parsed.push(hole.iter().map(point_from_input).collect());
            }
            parsed
        }
    };

    let (min_x, min_y, max_x, max_y) =
        polygon_bbox(&outer).ok_or_else(|| format!("stock {} outer polygon is empty", stock.id))?;
    let bbox_w = max_x - min_x;
    let bbox_h = max_y - min_y;
    if bbox_w <= 0.0 || bbox_h <= 0.0 {
        return Err(format!("stock {} outer polygon has invalid bbox", stock.id));
    }

    let area = polygon_area(&outer);
    let outer_poly = to_jag_polygon(&outer, &format!("stock {} outer_points", stock.id))?;
    let mut hole_polys = Vec::new();
    for (idx, hole) in holes.iter().enumerate() {
        hole_polys.push(to_jag_polygon(
            hole,
            &format!("stock {} holes_points[{idx}]", stock.id),
        )?);
    }

    let outer_vertices = if has_irregular_outer {
        outer.clone()
    } else {
        Vec::new()
    };
    let cost_per_use = stock.cost_per_use.unwrap_or(1.0).max(0.0);

    Ok(SheetShape {
        min_x,
        min_y,
        max_x,
        max_y,
        width: bbox_w,
        height: bbox_h,
        has_irregular_outer,
        area,
        outer_vertices,
        cost_per_use,
        _outer_poly: outer_poly,
        hole_polys,
    })
}

pub fn expand_sheets(stocks: &[Stock]) -> Result<Vec<SheetShape>, String> {
    let mut out = Vec::new();
    for stock in stocks {
        if stock.quantity <= 0 {
            continue;
        }
        let shape = stock_to_shape(stock)?;
        for _ in 0..stock.quantity {
            out.push(shape.clone());
        }
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::geometry::PointInput;

    fn rect_stock(id: &str, qty: i64, w: f64, h: f64) -> Stock {
        Stock {
            id: id.to_string(),
            quantity: qty,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }
    }

    fn l_shape_stock(id: &str, qty: i64) -> Stock {
        // L-shape: 100×100 bbox, notch at top-right 50×50
        // outer_points: (0,0)→(100,0)→(100,50)→(50,50)→(50,100)→(0,100)
        let pts = vec![
            PointInput::Pair([0.0, 0.0]),
            PointInput::Pair([100.0, 0.0]),
            PointInput::Pair([100.0, 50.0]),
            PointInput::Pair([50.0, 50.0]),
            PointInput::Pair([50.0, 100.0]),
            PointInput::Pair([0.0, 100.0]),
        ];
        Stock {
            id: id.to_string(),
            quantity: qty,
            width: None,
            height: None,
            outer_points: Some(pts),
            holes_points: None,
            cost_per_use: None,
        }
    }

    fn make_rect(x1: f64, y1: f64, x2: f64, y2: f64) -> Rect {
        Rect { x1, y1, x2, y2 }
    }

    #[test]
    fn expand_sheets_stable_order_and_quantity() {
        // Stock A (qty=2) then Stock B (qty=1) → 3 sheets: [A#0, A#1, B#0]
        let stocks = vec![
            rect_stock("A", 2, 100.0, 50.0),
            rect_stock("B", 1, 200.0, 80.0),
        ];
        let sheets = expand_sheets(&stocks).expect("expand_sheets");
        assert_eq!(
            sheets.len(),
            3,
            "total expanded sheets must equal sum of quantities"
        );
        for i in 0..2 {
            assert!((sheets[i].width - 100.0).abs() < 1e-9, "sheets[{i}] width");
            assert!((sheets[i].height - 50.0).abs() < 1e-9, "sheets[{i}] height");
        }
        assert!((sheets[2].width - 200.0).abs() < 1e-9, "sheets[2] width");
        assert!((sheets[2].height - 80.0).abs() < 1e-9, "sheets[2] height");
    }

    #[test]
    fn expand_sheets_zero_quantity_skipped() {
        let stocks = vec![
            rect_stock("X", 0, 100.0, 100.0),
            rect_stock("Y", 1, 50.0, 50.0),
        ];
        let sheets = expand_sheets(&stocks).expect("expand_sheets");
        assert_eq!(sheets.len(), 1);
        assert!((sheets[0].width - 50.0).abs() < 1e-9);
    }

    #[test]
    fn rect_stock_has_irregular_outer_false() {
        let stocks = vec![rect_stock("R", 1, 100.0, 80.0)];
        let sheets = expand_sheets(&stocks).expect("expand_sheets");
        assert!(
            !sheets[0].has_irregular_outer,
            "rectangular stock must have has_irregular_outer=false"
        );
        assert!(
            (sheets[0].area - 8000.0).abs() < 1e-6,
            "rect area=100*80=8000"
        );
    }

    #[test]
    fn l_shape_stock_has_irregular_outer_true() {
        let stocks = vec![l_shape_stock("L", 1)];
        let sheets = expand_sheets(&stocks).expect("expand_sheets");
        let s = &sheets[0];
        assert!(
            s.has_irregular_outer,
            "L-shape stock must have has_irregular_outer=true"
        );
        // L-shape area: 100*100 bbox minus 50*50 notch = 10000 - 2500 = 7500
        assert!(
            (s.area - 7500.0).abs() < 1e-4,
            "L-shape area must be ~7500, got {}",
            s.area
        );
        assert!((s.width - 100.0).abs() < 1e-9);
        assert!((s.height - 100.0).abs() < 1e-9);
    }

    #[test]
    fn l_shape_positive_control_inside() {
        // Item 20×20 at (10,10)→(30,30): fully inside bottom-left of L — must be accepted
        let stocks = vec![l_shape_stock("L", 1)];
        let sheets = expand_sheets(&stocks).expect("expand_sheets");
        let rect = make_rect(10.0, 10.0, 30.0, 30.0);
        assert!(
            rect_inside_sheet_shape(rect, &sheets[0]),
            "positive control inside L-shape must be accepted"
        );
    }

    #[test]
    fn l_shape_origin_placement_accepted() {
        // Item at (0,0)→(20,15): corner (0,0) is exactly on the polygon vertex.
        // Must be accepted — the interior of the rect is inside the L-shape.
        let stocks = vec![l_shape_stock("L", 1)];
        let sheets = expand_sheets(&stocks).expect("expand_sheets");
        let rect = make_rect(0.0, 0.0, 20.0, 15.0);
        assert!(
            rect_inside_sheet_shape(rect, &sheets[0]),
            "origin placement with corner on poly vertex must be accepted"
        );
    }

    #[test]
    fn l_shape_negative_control_notch() {
        // Item 20×20 at (60,60)→(80,80): in the notch (top-right) — bbox passes but outer poly must reject
        let stocks = vec![l_shape_stock("L", 1)];
        let sheets = expand_sheets(&stocks).expect("expand_sheets");
        let rect = make_rect(60.0, 60.0, 80.0, 80.0);
        assert!(
            !rect_inside_sheet_shape(rect, &sheets[0]),
            "notch placement must be rejected by outer polygon check"
        );
    }

    #[test]
    fn rectangular_stock_boundary_regression() {
        // Rectangular stock: item inside → accepted; item outside → rejected
        let stocks = vec![rect_stock("R", 1, 100.0, 80.0)];
        let sheets = expand_sheets(&stocks).expect("expand_sheets");
        let inside = make_rect(10.0, 10.0, 50.0, 40.0);
        assert!(
            rect_inside_sheet_shape(inside, &sheets[0]),
            "inside rect accepted"
        );
        let outside = make_rect(90.0, 70.0, 110.0, 90.0);
        assert!(
            !rect_inside_sheet_shape(outside, &sheets[0]),
            "outside rect rejected"
        );
    }

    #[test]
    fn stock_has_holes_detection() {
        let no_holes = rect_stock("A", 1, 100.0, 100.0);
        assert!(!stock_has_holes(&no_holes));

        let with_holes = Stock {
            id: "B".to_string(),
            quantity: 1,
            width: Some(100.0),
            height: Some(100.0),
            outer_points: None,
            holes_points: Some(vec![vec![
                PointInput::Pair([10.0, 10.0]),
                PointInput::Pair([20.0, 10.0]),
                PointInput::Pair([20.0, 20.0]),
            ]]),
            cost_per_use: None,
        };
        assert!(stock_has_holes(&with_holes));
    }
}

pub fn rect_inside_sheet_shape(rect: Rect, sheet: &SheetShape) -> bool {
    // Fast bbox precheck
    if rect.x1 < sheet.min_x - EPS
        || rect.y1 < sheet.min_y - EPS
        || rect.x2 > sheet.max_x + EPS
        || rect.y2 > sheet.max_y + EPS
    {
        return false;
    }

    let corners = rect_corners(rect);
    let rect_edges_arr = rect_edges(rect);

    // Irregular outer boundary check: all corners must be inside _outer_poly,
    // and no rect edge may cross an outer polygon edge.
    if sheet.has_irregular_outer {
        // jagua SPolygon.collides_with semantics for points exactly on the polygon
        // boundary (vertex or edge) are undefined and empirically return false.
        // JagEdge.collides_with also triggers for collinear overlap (touching edges).
        // Both are handled by using a slightly inset rect for all irregular checks:
        // we test whether the *interior* of the rect is inside the polygon.
        // INSET must survive f64→f32 narrowing in to_jag_point: 1e-6 >> f32 eps (~1.2e-7).
        const INSET: f64 = 1e-6;
        let ir = Rect {
            x1: rect.x1 + INSET,
            y1: rect.y1 + INSET,
            x2: rect.x2 - INSET,
            y2: rect.y2 - INSET,
        };
        let inset_corners = rect_corners(ir);
        let inset_edges = rect_edges(ir);
        for ic in inset_corners {
            if !sheet._outer_poly.collides_with(&to_jag_point(ic)) {
                return false;
            }
        }
        for re in inset_edges {
            let Some(rect_edge) = jag_edge_from_points(re.0, re.1) else {
                continue;
            };
            for outer_edge in sheet._outer_poly.edge_iter() {
                if rect_edge.collides_with(&outer_edge) {
                    return false;
                }
            }
        }
    }

    // Container hole exclusion
    for hole in &sheet.hole_polys {
        for c in corners {
            if hole.collides_with(&to_jag_point(c)) {
                return false;
            }
        }
        for re in rect_edges_arr {
            let Some(rect_edge) = jag_edge_from_points(re.0, re.1) else {
                continue;
            };
            for hole_edge in hole.edge_iter() {
                if rect_edge.collides_with(&hole_edge) {
                    return false;
                }
            }
        }
    }

    true
}
