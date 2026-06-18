//! SGH-Q53A: deterministic outer-contour feature extraction for critical-admission seeding.
//!
//! The extractor is intentionally cheap and read-only: it derives feature candidates from the
//! prepared OUTER contour only, with no collision checks, no cavity/hole logic, no NFP and no
//! rotation-policy changes. Q53B+ consume these features as better placement seeds.

use super::*;

const EPS: f64 = 1e-9;
const DOMINANT_EDGE_FRACTION: f64 = 0.67;
const DOMINANT_EDGE_MEAN_MULTIPLIER: f64 = 1.25;
const CONCAVE_TURN_MIN_DEG: f64 = 8.0;
const PROTRUSION_MIN_SCORE: f64 = 0.45;
const MAX_PROTRUSIONS: usize = 8;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExtremeAxis {
    MinX,
    MaxX,
    MinY,
    MaxY,
}

#[derive(Debug, Clone)]
pub struct ContourVertex {
    pub vertex_index: usize,
    pub point: Point,
}

#[derive(Debug, Clone)]
pub struct ContourEdge {
    pub edge_index: usize,
    pub start_vertex_index: usize,
    pub end_vertex_index: usize,
    pub start: Point,
    pub end: Point,
    pub midpoint: Point,
    pub length: f64,
    pub angle_deg: f64,
}

#[derive(Debug, Clone)]
pub struct DominantEdge {
    pub edge_index: usize,
    pub length: f64,
    pub angle_deg: f64,
    pub midpoint: Point,
    pub normalized_length: f64,
}

#[derive(Debug, Clone)]
pub struct ExtremePoint {
    pub axis: ExtremeAxis,
    pub vertex_index: usize,
    pub point: Point,
    pub projection: f64,
}

#[derive(Debug, Clone)]
pub struct ConcaveVertex {
    pub vertex_index: usize,
    pub point: Point,
    pub turn_deg: f64,
    pub depth_score: f64,
}

#[derive(Debug, Clone)]
pub struct ConcaveZone {
    pub vertex_index: usize,
    pub anchor: Point,
    pub inward_angle_deg: f64,
    pub depth_score: f64,
}

#[derive(Debug, Clone)]
pub struct ProtrusionCandidate {
    pub vertex_index: usize,
    pub point: Point,
    pub outward_angle_deg: f64,
    pub prominence_score: f64,
}

#[derive(Debug, Clone)]
pub struct SheetEdgeAlignmentAngle {
    pub source_edge_index: usize,
    pub source_angle_deg: f64,
    pub rotation_seed_deg: f64,
    pub edge_length: f64,
    pub alignment_score: f64,
}

#[derive(Debug, Clone, Default)]
pub struct ContourFeatureSummary {
    pub contour_vertex_count: usize,
    pub contour_edge_count: usize,
    pub dominant_edge_count: usize,
    pub extreme_point_count: usize,
    pub concave_vertex_count: usize,
    pub concave_zone_count: usize,
    pub protrusion_candidate_count: usize,
    pub sheet_alignment_angle_count: usize,
    pub total_feature_count: usize,
    pub dominant_alignment_angles_deg: Vec<f64>,
}

#[derive(Debug, Clone, Default)]
pub struct ContourFeatureSet {
    pub vertices: Vec<ContourVertex>,
    pub edges: Vec<ContourEdge>,
    pub dominant_edges: Vec<DominantEdge>,
    pub extreme_points: Vec<ExtremePoint>,
    pub concave_vertices: Vec<ConcaveVertex>,
    pub concave_zones: Vec<ConcaveZone>,
    pub protrusion_candidates: Vec<ProtrusionCandidate>,
    pub sheet_edge_alignment_angles: Vec<SheetEdgeAlignmentAngle>,
}

impl ContourFeatureSet {
    pub fn extract(base_shape: &CdeBaseShape) -> Self {
        extract_contour_features(base_shape)
    }

    pub fn summary(&self) -> ContourFeatureSummary {
        ContourFeatureSummary {
            contour_vertex_count: self.vertices.len(),
            contour_edge_count: self.edges.len(),
            dominant_edge_count: self.dominant_edges.len(),
            extreme_point_count: self.extreme_points.len(),
            concave_vertex_count: self.concave_vertices.len(),
            concave_zone_count: self.concave_zones.len(),
            protrusion_candidate_count: self.protrusion_candidates.len(),
            sheet_alignment_angle_count: self.sheet_edge_alignment_angles.len(),
            total_feature_count: self.vertices.len()
                + self.edges.len()
                + self.dominant_edges.len()
                + self.extreme_points.len()
                + self.concave_vertices.len()
                + self.concave_zones.len()
                + self.protrusion_candidates.len()
                + self.sheet_edge_alignment_angles.len(),
            dominant_alignment_angles_deg: self
                .sheet_edge_alignment_angles
                .iter()
                .map(|a| round2(a.rotation_seed_deg))
                .collect(),
        }
    }
}

pub fn extract_contour_features(base_shape: &CdeBaseShape) -> ContourFeatureSet {
    let pts = &base_shape.local_pts;
    if pts.len() < 3 {
        return ContourFeatureSet::default();
    }

    let vertices: Vec<ContourVertex> = pts
        .iter()
        .copied()
        .enumerate()
        .map(|(vertex_index, point)| ContourVertex {
            vertex_index,
            point,
        })
        .collect();

    let signed_area = signed_polygon_area(pts);
    let orientation = if signed_area >= 0.0 { 1.0 } else { -1.0 };
    let (bbox_min_x, bbox_min_y, bbox_max_x, bbox_max_y) =
        crate::geometry::polygon_bbox(pts).unwrap_or((0.0, 0.0, 0.0, 0.0));
    let bbox_diag = ((bbox_max_x - bbox_min_x).powi(2) + (bbox_max_y - bbox_min_y).powi(2))
        .sqrt()
        .max(EPS);
    let centroid = polygon_centroid(pts);

    let mut edges: Vec<ContourEdge> = Vec::with_capacity(pts.len());
    let mut max_edge_length = 0.0_f64;
    let mut total_edge_length = 0.0_f64;
    for i in 0..pts.len() {
        let start = pts[i];
        let end = pts[(i + 1) % pts.len()];
        let dx = end.x - start.x;
        let dy = end.y - start.y;
        let length = (dx * dx + dy * dy).sqrt();
        let midpoint = Point {
            x: (start.x + end.x) * 0.5,
            y: (start.y + end.y) * 0.5,
        };
        let angle_deg = wrap_deg(dy.atan2(dx).to_degrees());
        total_edge_length += length;
        max_edge_length = max_edge_length.max(length);
        edges.push(ContourEdge {
            edge_index: i,
            start_vertex_index: i,
            end_vertex_index: (i + 1) % pts.len(),
            start,
            end,
            midpoint,
            length,
            angle_deg,
        });
    }
    let mean_edge_length = total_edge_length / edges.len() as f64;
    let dominant_threshold = (max_edge_length * DOMINANT_EDGE_FRACTION)
        .max(mean_edge_length * DOMINANT_EDGE_MEAN_MULTIPLIER);
    let dominant_edges: Vec<DominantEdge> = edges
        .iter()
        .filter(|edge| edge.length + EPS >= dominant_threshold)
        .map(|edge| DominantEdge {
            edge_index: edge.edge_index,
            length: edge.length,
            angle_deg: edge.angle_deg,
            midpoint: edge.midpoint,
            normalized_length: if max_edge_length > EPS {
                edge.length / max_edge_length
            } else {
                0.0
            },
        })
        .collect();

    let extreme_points = vec![
        extreme_point_for_axis(pts, ExtremeAxis::MinX),
        extreme_point_for_axis(pts, ExtremeAxis::MaxX),
        extreme_point_for_axis(pts, ExtremeAxis::MinY),
        extreme_point_for_axis(pts, ExtremeAxis::MaxY),
    ];

    let mut concave_vertices: Vec<ConcaveVertex> = Vec::new();
    let mut concave_zones: Vec<ConcaveZone> = Vec::new();
    let mut protrusions: Vec<ProtrusionCandidate> = Vec::new();

    for i in 0..pts.len() {
        let prev = pts[(i + pts.len() - 1) % pts.len()];
        let cur = pts[i];
        let next = pts[(i + 1) % pts.len()];
        let vin = (cur.x - prev.x, cur.y - prev.y);
        let vout = (next.x - cur.x, next.y - cur.y);
        let prev_len = norm(vin.0, vin.1).max(EPS);
        let next_len = norm(vout.0, vout.1).max(EPS);
        let cross = cross2(vin, vout);
        let dot = vin.0 * vout.0 + vin.1 * vout.1;
        let turn_deg = cross.abs().atan2(dot).to_degrees();
        let sharpness = (turn_deg / 180.0).clamp(0.0, 1.0);
        let radial_norm = distance(cur, centroid) / bbox_diag;
        let normalized_depth = (prev_len.min(next_len) / bbox_diag).clamp(0.0, 1.0);
        let is_concave = cross * orientation < -EPS && turn_deg >= CONCAVE_TURN_MIN_DEG;
        if is_concave {
            let depth_score = sharpness * normalized_depth;
            concave_vertices.push(ConcaveVertex {
                vertex_index: i,
                point: cur,
                turn_deg: round2(turn_deg),
                depth_score: round4(depth_score),
            });
            let incoming = normalize(prev.x - cur.x, prev.y - cur.y);
            let outgoing = normalize(next.x - cur.x, next.y - cur.y);
            let inward = normalize(incoming.0 + outgoing.0, incoming.1 + outgoing.1);
            concave_zones.push(ConcaveZone {
                vertex_index: i,
                anchor: cur,
                inward_angle_deg: round2(wrap_deg(inward.1.atan2(inward.0).to_degrees())),
                depth_score: round4(depth_score),
            });
            continue;
        }

        let outward = normalize(cur.x - centroid.x, cur.y - centroid.y);
        let prominence_score = 0.55 * radial_norm + 0.45 * sharpness;
        if prominence_score >= PROTRUSION_MIN_SCORE {
            protrusions.push(ProtrusionCandidate {
                vertex_index: i,
                point: cur,
                outward_angle_deg: round2(wrap_deg(outward.1.atan2(outward.0).to_degrees())),
                prominence_score: round4(prominence_score),
            });
        }
    }

    protrusions.sort_by(|a, b| {
        b.prominence_score
            .partial_cmp(&a.prominence_score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| a.vertex_index.cmp(&b.vertex_index))
    });
    protrusions.truncate(MAX_PROTRUSIONS);
    protrusions.sort_by_key(|p| p.vertex_index);

    let mut sheet_edge_alignment_angles: Vec<SheetEdgeAlignmentAngle> = dominant_edges
        .iter()
        .map(|edge| {
            let rotation_seed_deg = sheet_alignment_rotation_seed(edge.angle_deg);
            SheetEdgeAlignmentAngle {
                source_edge_index: edge.edge_index,
                source_angle_deg: round2(edge.angle_deg),
                rotation_seed_deg: round2(rotation_seed_deg),
                edge_length: edge.length,
                alignment_score: round4(edge.normalized_length),
            }
        })
        .collect();
    sheet_edge_alignment_angles.sort_by(|a, b| {
        b.alignment_score
            .partial_cmp(&a.alignment_score)
            .unwrap_or(Ordering::Equal)
            .then_with(|| a.source_edge_index.cmp(&b.source_edge_index))
    });

    ContourFeatureSet {
        vertices,
        edges,
        dominant_edges,
        extreme_points,
        concave_vertices,
        concave_zones,
        protrusion_candidates: protrusions,
        sheet_edge_alignment_angles,
    }
}

fn extreme_point_for_axis(pts: &[Point], axis: ExtremeAxis) -> ExtremePoint {
    let mut best_idx = 0usize;
    for i in 1..pts.len() {
        if cmp_axis(pts[i], pts[best_idx], axis) == Ordering::Less {
            best_idx = i;
        }
    }
    let point = pts[best_idx];
    let projection = match axis {
        ExtremeAxis::MinX | ExtremeAxis::MaxX => point.x,
        ExtremeAxis::MinY | ExtremeAxis::MaxY => point.y,
    };
    ExtremePoint {
        axis,
        vertex_index: best_idx,
        point,
        projection,
    }
}

fn cmp_axis(a: Point, b: Point, axis: ExtremeAxis) -> Ordering {
    let primary = match axis {
        ExtremeAxis::MinX => a.x.partial_cmp(&b.x).unwrap_or(Ordering::Equal),
        ExtremeAxis::MaxX => b.x.partial_cmp(&a.x).unwrap_or(Ordering::Equal),
        ExtremeAxis::MinY => a.y.partial_cmp(&b.y).unwrap_or(Ordering::Equal),
        ExtremeAxis::MaxY => b.y.partial_cmp(&a.y).unwrap_or(Ordering::Equal),
    };
    primary
        .then_with(|| a.y.partial_cmp(&b.y).unwrap_or(Ordering::Equal))
        .then_with(|| a.x.partial_cmp(&b.x).unwrap_or(Ordering::Equal))
}

fn signed_polygon_area(pts: &[Point]) -> f64 {
    if pts.len() < 3 {
        return 0.0;
    }
    let mut signed = 0.0_f64;
    for i in 0..pts.len() {
        let j = (i + 1) % pts.len();
        signed += pts[i].x * pts[j].y - pts[j].x * pts[i].y;
    }
    signed * 0.5
}

fn polygon_centroid(pts: &[Point]) -> Point {
    let signed_area = signed_polygon_area(pts);
    if signed_area.abs() <= EPS {
        let (sx, sy) = pts
            .iter()
            .fold((0.0_f64, 0.0_f64), |(sx, sy), p| (sx + p.x, sy + p.y));
        return Point {
            x: sx / pts.len() as f64,
            y: sy / pts.len() as f64,
        };
    }
    let mut cx = 0.0_f64;
    let mut cy = 0.0_f64;
    for i in 0..pts.len() {
        let j = (i + 1) % pts.len();
        let cross = pts[i].x * pts[j].y - pts[j].x * pts[i].y;
        cx += (pts[i].x + pts[j].x) * cross;
        cy += (pts[i].y + pts[j].y) * cross;
    }
    Point {
        x: cx / (6.0 * signed_area),
        y: cy / (6.0 * signed_area),
    }
}

fn norm(x: f64, y: f64) -> f64 {
    (x * x + y * y).sqrt()
}

fn normalize(x: f64, y: f64) -> (f64, f64) {
    let len = norm(x, y);
    if len <= EPS {
        (1.0, 0.0)
    } else {
        (x / len, y / len)
    }
}

fn cross2(a: (f64, f64), b: (f64, f64)) -> f64 {
    a.0 * b.1 - a.1 * b.0
}

fn distance(a: Point, b: Point) -> f64 {
    norm(a.x - b.x, a.y - b.y)
}

fn wrap_deg(mut deg: f64) -> f64 {
    while deg <= -180.0 {
        deg += 360.0;
    }
    while deg > 180.0 {
        deg -= 360.0;
    }
    deg
}

fn sheet_alignment_rotation_seed(edge_angle_deg: f64) -> f64 {
    let horizontal_seed = wrap_deg(-edge_angle_deg);
    let vertical_seed = wrap_deg(90.0 - edge_angle_deg);
    if horizontal_seed.abs() <= vertical_seed.abs() {
        horizontal_seed
    } else {
        vertical_seed
    }
}

fn round2(v: f64) -> f64 {
    (v * 100.0).round() / 100.0
}

fn round4(v: f64) -> f64 {
    (v * 10_000.0).round() / 10_000.0
}

#[cfg(test)]
mod tests {
    use super::*;

    fn part(id: &str, w: f64, h: f64, pts: serde_json::Value) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(pts),
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn rect_base() -> CdeBaseShape {
        prepare_base_shape_native(&part(
            "rect",
            120.0,
            40.0,
            serde_json::json!([[0.0, 0.0], [120.0, 0.0], [120.0, 40.0], [0.0, 40.0]]),
        ))
        .expect("rect base")
    }

    fn u_base() -> CdeBaseShape {
        prepare_base_shape_native(&part(
            "u",
            100.0,
            100.0,
            serde_json::json!([
                [0.0, 0.0],
                [100.0, 0.0],
                [100.0, 100.0],
                [70.0, 100.0],
                [70.0, 30.0],
                [30.0, 30.0],
                [30.0, 100.0],
                [0.0, 100.0]
            ]),
        ))
        .expect("u base")
    }

    fn lv8_like_base() -> CdeBaseShape {
        prepare_base_shape_native(&part(
            "lv8",
            1240.0,
            760.0,
            serde_json::json!([
                [0.0, 110.0],
                [250.0, 0.0],
                [760.0, 0.0],
                [1160.0, 80.0],
                [1240.0, 210.0],
                [1210.0, 430.0],
                [990.0, 620.0],
                [720.0, 760.0],
                [420.0, 730.0],
                [160.0, 560.0],
                [40.0, 340.0],
                [210.0, 300.0],
                [360.0, 420.0],
                [610.0, 470.0],
                [840.0, 350.0],
                [860.0, 220.0],
                [690.0, 150.0],
                [360.0, 160.0],
                [120.0, 220.0]
            ]),
        ))
        .expect("lv8-like base")
    }

    #[test]
    fn rectangle_extracts_edges_extremes_and_alignment_angles() {
        let features = extract_contour_features(&rect_base());
        assert_eq!(features.vertices.len(), 4);
        assert_eq!(features.edges.len(), 4);
        assert_eq!(features.extreme_points.len(), 4);
        assert!(
            !features.dominant_edges.is_empty(),
            "rectangle must expose dominant long edges"
        );
        assert!(
            features
                .sheet_edge_alignment_angles
                .iter()
                .all(|a| a.rotation_seed_deg.abs() <= 90.0),
            "sheet alignment angles must stay continuous, not discrete list constrained"
        );
    }

    #[test]
    fn concave_u_shape_extracts_concave_vertices_and_zones() {
        let features = extract_contour_features(&u_base());
        assert!(
            features.concave_vertices.len() >= 2,
            "U shape must expose the mouth concavity"
        );
        assert_eq!(
            features.concave_vertices.len(),
            features.concave_zones.len(),
            "every concave vertex must produce a zone"
        );
        assert!(
            features
                .protrusion_candidates
                .iter()
                .any(|p| p.prominence_score > 0.5),
            "outer tips must surface as protrusions"
        );
    }

    #[test]
    fn lv8_like_contour_produces_non_empty_feature_rich_summary() {
        let features = extract_contour_features(&lv8_like_base());
        let summary = features.summary();
        assert!(summary.contour_vertex_count >= 12);
        assert!(summary.dominant_edge_count >= 2);
        assert!(summary.protrusion_candidate_count >= 2);
        assert!(
            summary.concave_vertex_count >= 1 || summary.concave_zone_count >= 1,
            "lv8-like contour must expose at least one inward zone"
        );
        assert!(
            !summary.dominant_alignment_angles_deg.is_empty(),
            "dominant edges must produce continuous alignment seeds"
        );
    }

    #[test]
    fn extraction_is_deterministic() {
        let a = extract_contour_features(&lv8_like_base()).summary();
        let b = extract_contour_features(&lv8_like_base()).summary();
        assert_eq!(a.contour_vertex_count, b.contour_vertex_count);
        assert_eq!(a.dominant_edge_count, b.dominant_edge_count);
        assert_eq!(a.concave_vertex_count, b.concave_vertex_count);
        assert_eq!(a.protrusion_candidate_count, b.protrusion_candidate_count);
        assert_eq!(
            a.dominant_alignment_angles_deg,
            b.dominant_alignment_angles_deg
        );
    }
}
