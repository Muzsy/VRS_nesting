/// Single point in scaled integer coordinates (1 unit = 1 µm = 1/SCALE mm).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Point64 {
    pub x: i64,
    pub y: i64,
}

/// Closed polygon: list of points; the last point implicitly connects back to the first.
/// Outer boundary must be counter-clockwise (CCW).
/// Holes must be clockwise (CW).
#[derive(Debug, Clone)]
pub struct Polygon64 {
    pub outer: Vec<Point64>,
    pub holes: Vec<Vec<Point64>>,
}

/// Geometry of a single part (nominal or inflated).
#[derive(Debug, Clone)]
pub struct PartGeometry {
    pub id: String,
    pub polygon: Polygon64,
}
