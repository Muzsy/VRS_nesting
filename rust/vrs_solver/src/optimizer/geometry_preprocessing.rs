use crate::geometry::{polygon_area, polygon_bbox, Point};

/// Flags indicating which backends can process a prepared shape.
#[derive(Debug, Clone, PartialEq)]
pub struct BackendReadiness {
    /// Bbox backend always ready.
    pub bbox: bool,
    /// JaguaPolygonExact backend: SPolygon can be built from the cleaned vertex list.
    pub jagua_polygon: bool,
    /// CDE backend requires hazard registration; not yet supported in VRS.
    pub cde: bool,
}

/// Metadata produced by the geometry preprocessing pipeline.
#[derive(Debug, Clone)]
pub struct PreparedShape {
    /// Cleaned vertex count (after deduplication).
    pub vertex_count: usize,
    /// Axis-aligned bounding box (min_x, min_y, max_x, max_y), or None if polygon was empty.
    pub bbox: Option<(f64, f64, f64, f64)>,
    /// Shoelace area (always ≥ 0).
    pub area: f64,
    /// True for polygon shapes; false for rectangles.
    pub has_irregular_shape: bool,
    /// Simplification tolerance applied, or None if no simplification was performed.
    /// TODO: QUALITY_RISK — Douglas-Peucker / offset simplification not yet implemented.
    pub simplification_tolerance: Option<f64>,
    /// Which collision backends can process this shape.
    pub backend_readiness: BackendReadiness,
}

/// Preprocess an arbitrary polygon: validate, deduplicate consecutive duplicates,
/// compute bbox and area metadata.
///
/// Returns Err if the polygon is invalid (< 3 points, zero area) or degenerate
/// after cleanup.
pub fn preprocess_polygon(points: &[Point]) -> Result<PreparedShape, String> {
    if points.len() < 3 {
        return Err(format!(
            "polygon must have at least 3 points, got {}",
            points.len()
        ));
    }

    let deduped = dedup_consecutive(points);

    if deduped.len() < 3 {
        return Err(format!(
            "polygon became degenerate after deduplication: {} vertices remain",
            deduped.len()
        ));
    }

    let area = polygon_area(&deduped);
    if area < 1e-12 {
        return Err(format!(
            "polygon has zero or near-zero area ({:.2e}); cannot be used for collision",
            area
        ));
    }

    let bbox = polygon_bbox(&deduped);

    Ok(PreparedShape {
        vertex_count: deduped.len(),
        bbox,
        area,
        has_irregular_shape: true,
        simplification_tolerance: None,
        backend_readiness: BackendReadiness {
            bbox: true,
            jagua_polygon: true,
            cde: false,
        },
    })
}

/// Preprocess a rectangle with the given dimensions.
///
/// Returns Err if dimensions are not strictly positive.
pub fn preprocess_rect(w: f64, h: f64) -> Result<PreparedShape, String> {
    if w <= 0.0 || h <= 0.0 {
        return Err(format!("rect dimensions must be > 0, got {}×{}", w, h));
    }
    Ok(PreparedShape {
        vertex_count: 4,
        bbox: Some((0.0, 0.0, w, h)),
        area: w * h,
        has_irregular_shape: false,
        simplification_tolerance: None,
        backend_readiness: BackendReadiness {
            bbox: true,
            jagua_polygon: true,
            cde: false,
        },
    })
}

/// Remove consecutive duplicate points (including closing duplicate if last == first).
///
/// Two points are considered equal if both coordinates differ by less than 1e-12.
fn dedup_consecutive(points: &[Point]) -> Vec<Point> {
    if points.is_empty() {
        return vec![];
    }
    let mut out: Vec<Point> = Vec::with_capacity(points.len());
    out.push(points[0]);
    for i in 1..points.len() {
        let prev = out[out.len() - 1];
        let curr = points[i];
        if (curr.x - prev.x).abs() > 1e-12 || (curr.y - prev.y).abs() > 1e-12 {
            out.push(curr);
        }
    }
    // Remove closing duplicate (last == first).
    if out.len() >= 2 {
        let first = out[0];
        let last = out[out.len() - 1];
        if (last.x - first.x).abs() < 1e-12 && (last.y - first.y).abs() < 1e-12 {
            out.pop();
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn pt(x: f64, y: f64) -> Point {
        Point { x, y }
    }

    // -------------------------------------------------------------------------
    // geometry_preprocessing_rejects_invalid_polygon
    // -------------------------------------------------------------------------

    #[test]
    fn geometry_preprocessing_rejects_invalid_polygon() {
        // < 3 points
        assert!(preprocess_polygon(&[]).is_err());
        assert!(preprocess_polygon(&[pt(0.0, 0.0)]).is_err());
        assert!(preprocess_polygon(&[pt(0.0, 0.0), pt(1.0, 0.0)]).is_err());

        // 3 collinear points → zero area
        let collinear = [pt(0.0, 0.0), pt(1.0, 0.0), pt(2.0, 0.0)];
        assert!(
            preprocess_polygon(&collinear).is_err(),
            "collinear polygon (zero area) must be rejected"
        );
    }

    // -------------------------------------------------------------------------
    // geometry_preprocessing_dedupes_consecutive_duplicate_points
    // -------------------------------------------------------------------------

    #[test]
    fn geometry_preprocessing_dedupes_consecutive_duplicate_points() {
        // Square with repeated (0,0) vertex
        let pts = [
            pt(0.0, 0.0),
            pt(0.0, 0.0), // duplicate
            pt(10.0, 0.0),
            pt(10.0, 10.0),
            pt(0.0, 10.0),
        ];
        let result = preprocess_polygon(&pts).expect("valid polygon after dedup");
        assert_eq!(result.vertex_count, 4, "duplicate vertex must be removed");
        assert!((result.area - 100.0).abs() < 1e-9, "area must be preserved");
        assert!(
            result.backend_readiness.jagua_polygon,
            "jagua_polygon must be ready"
        );
    }

    #[test]
    fn geometry_preprocessing_dedupes_closing_duplicate() {
        // Polygon where last point == first (closing vertex)
        let pts = [
            pt(0.0, 0.0),
            pt(10.0, 0.0),
            pt(10.0, 10.0),
            pt(0.0, 10.0),
            pt(0.0, 0.0), // closing duplicate
        ];
        let result = preprocess_polygon(&pts).expect("valid polygon after dedup");
        assert_eq!(result.vertex_count, 4, "closing duplicate must be removed");
    }

    #[test]
    fn geometry_preprocessing_valid_polygon_metadata() {
        // L-shape: 6 vertices, area = 100*50 + 50*50 = 7500 (wait, let me compute)
        // L-shape: (0,0),(100,0),(100,50),(50,50),(50,100),(0,100)
        // area via shoelace: should be 100*100 - 50*50 = 7500
        let pts = [
            pt(0.0, 0.0),
            pt(100.0, 0.0),
            pt(100.0, 50.0),
            pt(50.0, 50.0),
            pt(50.0, 100.0),
            pt(0.0, 100.0),
        ];
        let result = preprocess_polygon(&pts).expect("valid L-shape polygon");
        assert_eq!(result.vertex_count, 6);
        assert!(result.has_irregular_shape);
        assert!(
            (result.area - 7500.0).abs() < 1e-6,
            "L-shape area must be 7500, got {}",
            result.area
        );
        assert!(result.backend_readiness.bbox);
        assert!(result.backend_readiness.jagua_polygon);
        assert!(
            !result.backend_readiness.cde,
            "CDE backend not yet supported"
        );
        assert!(
            result.simplification_tolerance.is_none(),
            "no simplification applied"
        );
    }

    #[test]
    fn geometry_preprocessing_rect_valid() {
        let result = preprocess_rect(100.0, 50.0).expect("valid rect");
        assert_eq!(result.vertex_count, 4);
        assert!(!result.has_irregular_shape);
        assert!((result.area - 5000.0).abs() < 1e-9);
        assert_eq!(result.bbox, Some((0.0, 0.0, 100.0, 50.0)));
        assert!(result.backend_readiness.bbox);
        assert!(result.backend_readiness.jagua_polygon);
    }

    #[test]
    fn geometry_preprocessing_rect_rejects_zero_dims() {
        assert!(preprocess_rect(0.0, 10.0).is_err());
        assert!(preprocess_rect(10.0, 0.0).is_err());
        assert!(preprocess_rect(-1.0, 10.0).is_err());
    }
}
