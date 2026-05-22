use jagua_rs::geometry::geo_traits::CollidesWith;
use jagua_rs::geometry::primitives::SPolygon;
use serde::Deserialize;

use crate::geometry::{
    jag_edge_from_points, point_from_input, polygon_bbox, rect_corners, rect_edges, to_jag_point,
    to_jag_polygon, EPS, PointInput, Rect,
};

#[derive(Debug, Deserialize, Clone)]
pub struct Stock {
    pub id: String,
    pub quantity: i64,
    pub width: Option<f64>,
    pub height: Option<f64>,
    pub outer_points: Option<Vec<PointInput>>,
    pub holes_points: Option<Vec<Vec<PointInput>>>,
}

#[derive(Debug, Clone)]
pub struct SheetShape {
    pub min_x: f64,
    pub min_y: f64,
    pub max_x: f64,
    pub max_y: f64,
    pub width: f64,
    pub height: f64,
    pub _outer_poly: SPolygon,
    pub hole_polys: Vec<SPolygon>,
}

pub fn stock_to_shape(stock: &Stock) -> Result<SheetShape, String> {
    use crate::geometry::Point;

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

    let outer_poly = to_jag_polygon(&outer, &format!("stock {} outer_points", stock.id))?;
    let mut hole_polys = Vec::new();
    for (idx, hole) in holes.iter().enumerate() {
        hole_polys.push(to_jag_polygon(
            hole,
            &format!("stock {} holes_points[{idx}]", stock.id),
        )?);
    }

    Ok(SheetShape {
        min_x,
        min_y,
        max_x,
        max_y,
        width: bbox_w,
        height: bbox_h,
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

pub fn rect_inside_sheet_shape(rect: Rect, sheet: &SheetShape) -> bool {
    if rect.x1 < sheet.min_x - EPS
        || rect.y1 < sheet.min_y - EPS
        || rect.x2 > sheet.max_x + EPS
        || rect.y2 > sheet.max_y + EPS
    {
        return false;
    }

    let corners = rect_corners(rect);
    let rect_edges_arr = rect_edges(rect);
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
