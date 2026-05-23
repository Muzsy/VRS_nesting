use jagua_rs::geometry::primitives::{Edge as JagEdge, Point as JagPoint, SPolygon};
use serde::Deserialize;

pub const EPS: f64 = 1e-9;

#[derive(Debug, Deserialize, Clone)]
#[serde(untagged)]
pub enum PointInput {
    Pair([f64; 2]),
    Obj { x: f64, y: f64 },
}

#[derive(Debug, Clone, Copy)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}

#[derive(Debug, Clone, Copy)]
pub struct Rect {
    pub x1: f64,
    pub y1: f64,
    pub x2: f64,
    pub y2: f64,
}

pub fn point_from_input(raw: &PointInput) -> Point {
    match raw {
        PointInput::Pair([x, y]) => Point { x: *x, y: *y },
        PointInput::Obj { x, y } => Point { x: *x, y: *y },
    }
}

pub fn polygon_bbox(points: &[Point]) -> Option<(f64, f64, f64, f64)> {
    if points.is_empty() {
        return None;
    }
    let mut min_x = points[0].x;
    let mut max_x = points[0].x;
    let mut min_y = points[0].y;
    let mut max_y = points[0].y;
    for p in points.iter().skip(1) {
        if p.x < min_x {
            min_x = p.x;
        }
        if p.x > max_x {
            max_x = p.x;
        }
        if p.y < min_y {
            min_y = p.y;
        }
        if p.y > max_y {
            max_y = p.y;
        }
    }
    Some((min_x, min_y, max_x, max_y))
}

pub fn to_jag_point(p: Point) -> JagPoint {
    JagPoint(p.x as f32, p.y as f32)
}

pub fn to_jag_polygon(points: &[Point], label: &str) -> Result<SPolygon, String> {
    let vertices: Vec<JagPoint> = points.iter().copied().map(to_jag_point).collect();
    SPolygon::new(vertices).map_err(|e| format!("{label}: {e}"))
}

pub fn jag_edge_from_points(a: Point, b: Point) -> Option<JagEdge> {
    JagEdge::try_new(to_jag_point(a), to_jag_point(b)).ok()
}

pub fn rect_area(width: f64, height: f64) -> f64 {
    width * height
}

pub fn rect_corners(rect: Rect) -> [Point; 4] {
    [
        Point {
            x: rect.x1,
            y: rect.y1,
        },
        Point {
            x: rect.x2,
            y: rect.y1,
        },
        Point {
            x: rect.x2,
            y: rect.y2,
        },
        Point {
            x: rect.x1,
            y: rect.y2,
        },
    ]
}

pub fn rect_edges(rect: Rect) -> [(Point, Point); 4] {
    let c = rect_corners(rect);
    [(c[0], c[1]), (c[1], c[2]), (c[2], c[3]), (c[3], c[0])]
}
