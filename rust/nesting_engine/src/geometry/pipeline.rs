use geo::{Coord, Line, sweep::{Cross, Intersections, LineOrPoint}};

use crate::geometry::{
    offset::{deflate_hole, inflate_outer, inflate_part, OffsetError},
    scale::{i64_to_mm, mm_to_i64},
    types::{PartGeometry, Point64, Polygon64},
};
use crate::io::pipeline_io::{
    Diagnostic, PartRequest, PartResponse, PipelineRequest, PipelineResponse,
};

const STATUS_OK: &str = "ok";
const STATUS_HOLE_COLLAPSED: &str = "hole_collapsed";
const STATUS_SELF_INTERSECT: &str = "self_intersect";
const STATUS_ERROR: &str = "error";

const CODE_HOLE_COLLAPSED: &str = "HOLE_COLLAPSED";
const CODE_SELF_INTERSECT: &str = "SELF_INTERSECT";
const CODE_OFFSET_ERROR: &str = "OFFSET_ERROR";

/// Run the nominal->inflated geometry pipeline for every part in the request.
pub fn run_inflate_pipeline(req: PipelineRequest) -> PipelineResponse {
    let delta_mm = req.margin_mm + (req.kerf_mm * 0.5);
    let version = req.version;
    let parts = req
        .parts
        .into_iter()
        .map(|part| inflate_single_part(part, delta_mm))
        .collect();

    PipelineResponse { version, parts }
}

fn inflate_single_part(part: PartRequest, delta_mm: f64) -> PartResponse {
    let part_id = part.id.clone();
    let nominal = request_to_geometry(&part);
    // Early validation keeps SELF_INTERSECT behavior deterministic for invalid nominal input.
    if polygon_self_intersects(&nominal.polygon.outer) {
        return PartResponse {
            id: part_id,
            status: STATUS_SELF_INTERSECT.to_string(),
            inflated_outer_points_mm: Vec::new(),
            inflated_holes_points_mm: Vec::new(),
            diagnostics: vec![self_intersect_diagnostic(
                "nominal outer polygon self-intersects before inflate",
            )],
        };
    }

    match inflate_part(&nominal, delta_mm) {
        Ok(inflated) => {
            let collapsed_hole_indices = detect_collapsed_holes(&part, delta_mm);
            let mut diagnostics: Vec<Diagnostic> = collapsed_hole_indices
                .iter()
                .map(|&idx| hole_collapsed_diagnostic(&part, idx))
                .collect();
            let is_self_intersect = polygon_self_intersects(&inflated.polygon.outer);
            if is_self_intersect {
                diagnostics.push(self_intersect_diagnostic(
                    "outer polygon self-intersects after inflate",
                ));
            }
            let has_hole_collapse = !collapsed_hole_indices.is_empty();

            PartResponse {
                id: part_id,
                status: if is_self_intersect {
                    STATUS_SELF_INTERSECT.to_string()
                } else if has_hole_collapse {
                    STATUS_HOLE_COLLAPSED.to_string()
                } else {
                    STATUS_OK.to_string()
                },
                inflated_outer_points_mm: points_to_mm_pairs(&inflated.polygon.outer),
                inflated_holes_points_mm: inflated
                    .polygon
                    .holes
                    .iter()
                    .map(|hole| points_to_mm_pairs(hole))
                    .collect(),
                diagnostics,
            }
        }
        Err(OffsetError::HoleCollapsed { hole_index }) => {
            handle_hole_collapsed(part, nominal, hole_index, delta_mm)
        }
        Err(err) => PartResponse {
            id: part_id,
            status: STATUS_ERROR.to_string(),
            inflated_outer_points_mm: Vec::new(),
            inflated_holes_points_mm: Vec::new(),
            diagnostics: vec![Diagnostic {
                code: CODE_OFFSET_ERROR.to_string(),
                hole_index: None,
                nominal_hole_bbox_mm: None,
                preserve_for_export: None,
                usable_for_nesting: None,
                detail: format!("inflate_part failed: {}", offset_error_detail(&err)),
            }],
        },
    }
}

fn handle_hole_collapsed(
    part: PartRequest,
    nominal: PartGeometry,
    hole_index: usize,
    delta_mm: f64,
) -> PartResponse {
    let part_id = part.id.clone();
    let mut diagnostics = vec![hole_collapsed_diagnostic(&part, hole_index)];

    // Fallback path: inflate the outer boundary only, so feasibility can proceed.
    let fallback_polygon = Polygon64 {
        outer: nominal.polygon.outer,
        holes: Vec::new(),
    };

    match inflate_outer(&fallback_polygon, delta_mm) {
        Ok(inflated_outer_only) => {
            let is_self_intersect = polygon_self_intersects(&inflated_outer_only.outer);
            if is_self_intersect {
                diagnostics.push(self_intersect_diagnostic(
                    "outer-only fallback polygon self-intersects after inflate",
                ));
            }

            PartResponse {
                id: part_id,
                status: if is_self_intersect {
                    STATUS_SELF_INTERSECT.to_string()
                } else {
                    STATUS_HOLE_COLLAPSED.to_string()
                },
                inflated_outer_points_mm: points_to_mm_pairs(&inflated_outer_only.outer),
                inflated_holes_points_mm: Vec::new(),
                diagnostics,
            }
        }
        Err(err) => {
            diagnostics.push(Diagnostic {
                code: CODE_OFFSET_ERROR.to_string(),
                hole_index: None,
                nominal_hole_bbox_mm: None,
                preserve_for_export: None,
                usable_for_nesting: None,
                detail: format!(
                    "outer-only fallback inflate failed after hole collapse: {}",
                    offset_error_detail(&err)
                ),
            });
            PartResponse {
                id: part_id,
                status: STATUS_ERROR.to_string(),
                inflated_outer_points_mm: Vec::new(),
                inflated_holes_points_mm: Vec::new(),
                diagnostics,
            }
        }
    }
}

fn request_to_geometry(part: &PartRequest) -> PartGeometry {
    PartGeometry {
        id: part.id.clone(),
        polygon: Polygon64 {
            outer: mm_pairs_to_points(&part.outer_points_mm),
            holes: part
                .holes_points_mm
                .iter()
                .map(|hole| mm_pairs_to_points(hole))
                .collect(),
        },
    }
}

fn mm_pairs_to_points(points_mm: &[[f64; 2]]) -> Vec<Point64> {
    points_mm
        .iter()
        .map(|p| Point64 {
            x: mm_to_i64(p[0]),
            y: mm_to_i64(p[1]),
        })
        .collect()
}

fn points_to_mm_pairs(points: &[Point64]) -> Vec<[f64; 2]> {
    points
        .iter()
        .map(|p| [i64_to_mm(p.x), i64_to_mm(p.y)])
        .collect()
}

fn hole_collapsed_diagnostic(part: &PartRequest, hole_index: usize) -> Diagnostic {
    let bbox = part
        .holes_points_mm
        .get(hole_index)
        .and_then(|hole| hole_bbox_mm(hole));

    Diagnostic {
        code: CODE_HOLE_COLLAPSED.to_string(),
        hole_index: Some(hole_index),
        nominal_hole_bbox_mm: bbox,
        preserve_for_export: Some(true),
        usable_for_nesting: Some(false),
        detail: "hole collapsed in inflated geometry; nominal hole preserved for export".to_string(),
    }
}

fn detect_collapsed_holes(part: &PartRequest, delta_mm: f64) -> Vec<usize> {
    let mut collapsed = Vec::new();
    for (idx, hole) in part.holes_points_mm.iter().enumerate() {
        let hole_points = mm_pairs_to_points(hole);
        if let Err(OffsetError::HoleCollapsed { .. }) = deflate_hole(&hole_points, delta_mm) {
            collapsed.push(idx);
        }
    }
    collapsed
}

fn self_intersect_diagnostic(detail: &str) -> Diagnostic {
    Diagnostic {
        code: CODE_SELF_INTERSECT.to_string(),
        hole_index: None,
        nominal_hole_bbox_mm: None,
        preserve_for_export: None,
        usable_for_nesting: None,
        detail: detail.to_string(),
    }
}

fn hole_bbox_mm(hole: &[[f64; 2]]) -> Option<[f64; 4]> {
    let first = hole.first()?;
    let mut min_x = first[0];
    let mut min_y = first[1];
    let mut max_x = first[0];
    let mut max_y = first[1];
    for p in &hole[1..] {
        min_x = min_x.min(p[0]);
        min_y = min_y.min(p[1]);
        max_x = max_x.max(p[0]);
        max_y = max_y.max(p[1]);
    }
    Some([min_x, min_y, max_x, max_y])
}

fn offset_error_detail(err: &OffsetError) -> String {
    match err {
        OffsetError::HoleCollapsed { hole_index } => {
            format!("hole collapsed at index {hole_index}")
        }
        OffsetError::ClipperError(detail) => detail.clone(),
    }
}

fn polygon_self_intersects(points: &[Point64]) -> bool {
    if points.len() < 4 {
        return false;
    }

    let Some(segments) = polygon_segments(points) else {
        return false;
    };
    let segment_count = segments.len();
    if segment_count < 2 {
        return false;
    }

    let intersections = Intersections::<SweepSegment>::from_iter(segments);
    for (a, b, _) in intersections {
        if !segments_are_adjacent(a.idx, b.idx, segment_count) {
            return true;
        }
    }
    false
}

#[derive(Debug, Clone, Copy)]
struct SweepSegment {
    idx: usize,
    line: Line<f64>,
}

impl Cross for SweepSegment {
    type Scalar = f64;

    fn line(&self) -> LineOrPoint<Self::Scalar> {
        self.line.into()
    }
}

fn polygon_segments(points: &[Point64]) -> Option<Vec<SweepSegment>> {
    if points.len() < 3 {
        return None;
    }

    let coords: Vec<Coord<f64>> = points
        .iter()
        .map(|p| Coord {
            x: i64_to_mm(p.x),
            y: i64_to_mm(p.y),
        })
        .collect();
    let n = coords.len();
    if n < 3 {
        return None;
    }

    let mut segments = Vec::with_capacity(n);
    for i in 0..n {
        segments.push(SweepSegment {
            idx: i,
            line: Line::new(coords[i], coords[(i + 1) % n]),
        });
    }
    Some(segments)
}

fn segments_are_adjacent(a: usize, b: usize, n: usize) -> bool {
    if n < 2 || a == b {
        return true;
    }
    let diff = a.abs_diff(b);
    diff == 1 || diff == (n - 1)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bbox_from_points_mm(points: &[[f64; 2]]) -> (f64, f64) {
        let mut min_x = points[0][0];
        let mut min_y = points[0][1];
        let mut max_x = points[0][0];
        let mut max_y = points[0][1];
        for p in &points[1..] {
            min_x = min_x.min(p[0]);
            min_y = min_y.min(p[1]);
            max_x = max_x.max(p[0]);
            max_y = max_y.max(p[1]);
        }
        (max_x - min_x, max_y - min_y)
    }

    #[test]
    fn ok_case_rect_100x50() {
        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 5.0,
            parts: vec![PartRequest {
                id: "rect_100x50".to_string(),
                outer_points_mm: vec![[0.0, 0.0], [100.0, 0.0], [100.0, 50.0], [0.0, 50.0]],
                holes_points_mm: Vec::new(),
            }],
        };

        let resp = run_inflate_pipeline(req);
        assert_eq!(resp.parts.len(), 1);
        assert_eq!(resp.parts[0].status, STATUS_OK);
        let (w, h) = bbox_from_points_mm(&resp.parts[0].inflated_outer_points_mm);
        assert!(
            w >= 102.0,
            "inflated width should be >= 102.0mm, got {w:.6}mm"
        );
        assert!(
            h >= 52.0,
            "inflated height should be >= 52.0mm, got {h:.6}mm"
        );
    }

    #[test]
    fn hole_collapsed_case_with_fallback_outer() {
        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 5.0,
            parts: vec![PartRequest {
                id: "small_with_tiny_hole".to_string(),
                outer_points_mm: vec![[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]],
                holes_points_mm: vec![vec![[9.0, 9.0], [11.0, 9.0], [11.0, 11.0], [9.0, 11.0]]],
            }],
        };

        let resp = run_inflate_pipeline(req);
        assert_eq!(resp.parts.len(), 1);
        let part = &resp.parts[0];
        assert_eq!(part.status, STATUS_HOLE_COLLAPSED);
        assert!(
            !part.inflated_outer_points_mm.is_empty(),
            "fallback outer inflation must return non-empty outer points"
        );
        assert!(
            part.inflated_holes_points_mm.is_empty(),
            "fallback outer-only inflate should return no inflated holes"
        );

        let diag = part
            .diagnostics
            .iter()
            .find(|d| d.code == CODE_HOLE_COLLAPSED)
            .expect("missing HOLE_COLLAPSED diagnostic");
        assert_eq!(diag.preserve_for_export, Some(true));
        assert_eq!(diag.usable_for_nesting, Some(false));
        assert!(diag.nominal_hole_bbox_mm.is_some());
    }

    #[test]
    fn determinism_case_same_request_same_output() {
        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 5.0,
            parts: vec![PartRequest {
                id: "deterministic_part".to_string(),
                outer_points_mm: vec![[0.0, 0.0], [30.0, 0.0], [30.0, 10.0], [0.0, 10.0]],
                holes_points_mm: Vec::new(),
            }],
        };

        let resp_a = run_inflate_pipeline(req.clone());
        let resp_b = run_inflate_pipeline(req);

        let serialized_a = serde_json::to_string(&resp_a).expect("serialize response A");
        let serialized_b = serde_json::to_string(&resp_b).expect("serialize response B");
        assert_eq!(
            serialized_a, serialized_b,
            "pipeline output is not deterministic"
        );
    }

    #[test]
    fn self_intersect_bow_tie_case_returns_status_and_diagnostic() {
        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 5.0,
            parts: vec![PartRequest {
                id: "bow_tie".to_string(),
                outer_points_mm: vec![[0.0, 0.0], [10.0, 10.0], [0.0, 10.0], [10.0, 0.0]],
                holes_points_mm: Vec::new(),
            }],
        };

        let resp = run_inflate_pipeline(req);
        assert_eq!(resp.parts.len(), 1);
        let part = &resp.parts[0];
        assert_eq!(part.status, STATUS_SELF_INTERSECT);
        assert!(
            part.inflated_outer_points_mm.is_empty(),
            "self-intersect input should not return inflated outer points"
        );
        let diag = part
            .diagnostics
            .iter()
            .find(|d| d.code == CODE_SELF_INTERSECT)
            .expect("missing SELF_INTERSECT diagnostic");
        assert!(
            diag.detail.contains("self-intersects"),
            "expected meaningful diagnostic detail, got: {}",
            diag.detail
        );
    }
}
