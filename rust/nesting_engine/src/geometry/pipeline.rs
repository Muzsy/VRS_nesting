use geo::{
    sweep::{Cross, Intersections, LineOrPoint},
    Coord, Line,
};

use crate::geometry::{
    float_policy::{GEOM_EPS_MM, cmp_eps, eq_eps},
    offset::{deflate_hole, inflate_outer, inflate_part, OffsetError},
    scale::{i64_to_mm, mm_to_i64},
    types::{PartGeometry, Point64, Polygon64},
};
use crate::io::pipeline_io::{
    Diagnostic, PartRequest, PartResponse, PipelineRequest, PipelineResponse, StockRequest,
    StockResponse,
};
use std::cmp::Ordering;

const STATUS_OK: &str = "ok";
const STATUS_HOLE_COLLAPSED: &str = "hole_collapsed";
const STATUS_SELF_INTERSECT: &str = "self_intersect";
const STATUS_ERROR: &str = "error";

const CODE_HOLE_COLLAPSED: &str = "HOLE_COLLAPSED";
const CODE_SELF_INTERSECT: &str = "SELF_INTERSECT";
const CODE_OFFSET_ERROR: &str = "OFFSET_ERROR";

/// Run the nominal->inflated geometry pipeline for every part in the request.
pub fn run_inflate_pipeline(req: PipelineRequest) -> PipelineResponse {
    let spacing_effective_mm = req.spacing_mm.unwrap_or(req.kerf_mm);
    let inflate_delta_mm = spacing_effective_mm * 0.5;
    let bin_offset_mm = inflate_delta_mm - req.margin_mm;
    let version = req.version;
    let parts = req
        .parts
        .into_iter()
        .map(|part| inflate_single_part(part, inflate_delta_mm))
        .collect();
    let stocks = req
        .stocks
        .into_iter()
        .map(|stock| inflate_single_stock(stock, bin_offset_mm, inflate_delta_mm))
        .collect();

    PipelineResponse {
        version,
        parts,
        stocks,
    }
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
            if !collapsed_hole_indices.is_empty() {
                let diagnostics: Vec<Diagnostic> = collapsed_hole_indices
                    .iter()
                    .map(|&idx| hole_collapsed_diagnostic(&part, idx))
                    .collect();
                return build_hole_collapsed_outer_only_response(
                    part_id,
                    nominal.polygon.outer,
                    delta_mm,
                    diagnostics,
                    "outer-only fallback inflate failed after detect_collapsed_holes",
                );
            }

            let mut diagnostics = Vec::new();
            let is_self_intersect = polygon_self_intersects(&inflated.polygon.outer);
            if is_self_intersect {
                diagnostics.push(self_intersect_diagnostic(
                    "outer polygon self-intersects after inflate",
                ));
            }

            PartResponse {
                id: part_id,
                status: if is_self_intersect {
                    STATUS_SELF_INTERSECT.to_string()
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

fn inflate_single_stock(
    stock: StockRequest,
    bin_offset_mm: f64,
    inflate_delta_mm: f64,
) -> StockResponse {
    let stock_id = stock.id.clone();
    let nominal = Polygon64 {
        outer: mm_pairs_to_points(&stock.outer_points_mm),
        holes: stock
            .holes_points_mm
            .iter()
            .map(|hole| mm_pairs_to_points(hole))
            .collect(),
    };

    if polygon_self_intersects(&nominal.outer) {
        return StockResponse {
            id: stock_id,
            status: STATUS_SELF_INTERSECT.to_string(),
            usable_outer_points_mm: Vec::new(),
            usable_holes_points_mm: Vec::new(),
            diagnostics: vec![self_intersect_diagnostic(
                "nominal stock outer polygon self-intersects before offset",
            )],
        };
    }
    for (hole_idx, hole) in nominal.holes.iter().enumerate() {
        if polygon_self_intersects(hole) {
            return StockResponse {
                id: stock_id,
                status: STATUS_SELF_INTERSECT.to_string(),
                usable_outer_points_mm: Vec::new(),
                usable_holes_points_mm: Vec::new(),
                diagnostics: vec![Diagnostic {
                    code: CODE_SELF_INTERSECT.to_string(),
                    hole_index: Some(hole_idx),
                    nominal_hole_bbox_mm: hole_bbox_mm(
                        stock
                            .holes_points_mm
                            .get(hole_idx)
                            .map(Vec::as_slice)
                            .unwrap_or(&[]),
                    ),
                    preserve_for_export: None,
                    usable_for_nesting: None,
                    detail: "nominal stock hole polygon self-intersects before offset".to_string(),
                }],
            };
        }
    }

    let outer_only = Polygon64 {
        outer: nominal.outer.clone(),
        holes: Vec::new(),
    };
    let usable_outer = match inflate_outer(&outer_only, bin_offset_mm) {
        Ok(usable_outer) => usable_outer,
        Err(err) => {
            return StockResponse {
                id: stock_id,
                status: STATUS_ERROR.to_string(),
                usable_outer_points_mm: Vec::new(),
                usable_holes_points_mm: Vec::new(),
                diagnostics: vec![Diagnostic {
                    code: CODE_OFFSET_ERROR.to_string(),
                    hole_index: None,
                    nominal_hole_bbox_mm: None,
                    preserve_for_export: None,
                    usable_for_nesting: None,
                    detail: format!("inflate_outer failed for stock outer: {}", offset_error_detail(&err)),
                }],
            };
        }
    };

    let mut expanded_holes_mm = Vec::with_capacity(stock.holes_points_mm.len());
    for (hole_idx, hole_mm) in stock.holes_points_mm.iter().enumerate() {
        match inflate_stock_hole_obstacle(hole_mm, inflate_delta_mm) {
            Ok(expanded_hole_mm) => expanded_holes_mm.push(expanded_hole_mm),
            Err(err) => {
                return StockResponse {
                    id: stock_id,
                    status: STATUS_ERROR.to_string(),
                    usable_outer_points_mm: Vec::new(),
                    usable_holes_points_mm: Vec::new(),
                    diagnostics: vec![Diagnostic {
                        code: CODE_OFFSET_ERROR.to_string(),
                        hole_index: Some(hole_idx),
                        nominal_hole_bbox_mm: hole_bbox_mm(hole_mm),
                        preserve_for_export: None,
                        usable_for_nesting: None,
                        detail: format!(
                            "inflate_outer failed for stock hole obstacle: {}",
                            offset_error_detail(&err)
                        ),
                    }],
                };
            }
        }
    }

    let outer_self_intersect = polygon_self_intersects(&usable_outer.outer);
    let hole_self_intersect_idx = expanded_holes_mm
        .iter()
        .position(|hole| polygon_self_intersects(&mm_pairs_to_points(hole)));

    let mut diagnostics = Vec::new();
    if outer_self_intersect {
        diagnostics.push(self_intersect_diagnostic(
            "usable stock outer polygon self-intersects after offset",
        ));
    }
    if let Some(hole_idx) = hole_self_intersect_idx {
        diagnostics.push(Diagnostic {
            code: CODE_SELF_INTERSECT.to_string(),
            hole_index: Some(hole_idx),
            nominal_hole_bbox_mm: hole_bbox_mm(
                stock
                    .holes_points_mm
                    .get(hole_idx)
                    .map(Vec::as_slice)
                    .unwrap_or(&[]),
            ),
            preserve_for_export: None,
            usable_for_nesting: None,
            detail: "usable stock hole polygon self-intersects after offset".to_string(),
        });
    }

    StockResponse {
        id: stock_id,
        status: if outer_self_intersect || hole_self_intersect_idx.is_some() {
            STATUS_SELF_INTERSECT.to_string()
        } else {
            STATUS_OK.to_string()
        },
        usable_outer_points_mm: points_to_mm_pairs(&usable_outer.outer),
        usable_holes_points_mm: expanded_holes_mm,
        diagnostics,
    }
}

fn inflate_stock_hole_obstacle(
    hole_mm: &[[f64; 2]],
    inflate_delta_mm: f64,
) -> Result<Vec<[f64; 2]>, OffsetError> {
    let hole_polygon = Polygon64 {
        outer: mm_pairs_to_points(hole_mm),
        holes: Vec::new(),
    };
    let expanded = inflate_outer(&hole_polygon, inflate_delta_mm)?;
    if expanded.outer.is_empty() {
        return Err(OffsetError::ClipperError(
            "stock hole obstacle offset produced empty outer".to_string(),
        ));
    }
    Ok(canonicalize_mm_ring_start(points_to_mm_pairs(&expanded.outer)))
}

fn handle_hole_collapsed(
    part: PartRequest,
    nominal: PartGeometry,
    hole_index: usize,
    delta_mm: f64,
) -> PartResponse {
    build_hole_collapsed_outer_only_response(
        part.id.clone(),
        nominal.polygon.outer,
        delta_mm,
        vec![hole_collapsed_diagnostic(&part, hole_index)],
        "outer-only fallback inflate failed after hole collapse",
    )
}

fn build_hole_collapsed_outer_only_response(
    part_id: String,
    nominal_outer: Vec<Point64>,
    delta_mm: f64,
    mut diagnostics: Vec<Diagnostic>,
    offset_error_context: &str,
) -> PartResponse {
    let fallback_polygon = Polygon64 {
        outer: nominal_outer,
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
                detail: format!("{offset_error_context}: {}", offset_error_detail(&err)),
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
        detail: "hole collapsed in inflated geometry; nominal hole preserved for export"
            .to_string(),
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
        min_x = min_with_policy(min_x, p[0]);
        min_y = min_with_policy(min_y, p[1]);
        max_x = max_with_policy(max_x, p[0]);
        max_y = max_with_policy(max_y, p[1]);
    }
    Some([min_x, min_y, max_x, max_y])
}

fn min_with_policy(current: f64, candidate: f64) -> f64 {
    match cmp_eps(candidate, current, GEOM_EPS_MM) {
        Ordering::Less => candidate,
        Ordering::Equal => {
            if candidate.total_cmp(&current) == Ordering::Less {
                candidate
            } else {
                current
            }
        }
        Ordering::Greater => current,
    }
}

fn max_with_policy(current: f64, candidate: f64) -> f64 {
    match cmp_eps(candidate, current, GEOM_EPS_MM) {
        Ordering::Greater => candidate,
        Ordering::Equal => {
            if candidate.total_cmp(&current) == Ordering::Greater {
                candidate
            } else {
                current
            }
        }
        Ordering::Less => current,
    }
}

fn canonicalize_mm_ring_start(mut ring: Vec<[f64; 2]>) -> Vec<[f64; 2]> {
    if ring.len() < 2 {
        return ring;
    }
    if eq_eps(ring[0][0], ring[ring.len() - 1][0], GEOM_EPS_MM)
        && eq_eps(ring[0][1], ring[ring.len() - 1][1], GEOM_EPS_MM)
    {
        ring.pop();
    }
    if ring.is_empty() {
        return ring;
    }
    let mut min_idx = 0usize;
    for idx in 1..ring.len() {
        let ax = mm_to_i64(ring[idx][0]);
        let ay = mm_to_i64(ring[idx][1]);
        let bx = mm_to_i64(ring[min_idx][0]);
        let by = mm_to_i64(ring[min_idx][1]);
        if (ax, ay) < (bx, by) {
            min_idx = idx;
        }
    }
    ring.rotate_left(min_idx);
    ring
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

    fn bounds_from_points_mm(points: &[[f64; 2]]) -> (f64, f64, f64, f64) {
        let mut min_x = points[0][0];
        let mut min_y = points[0][1];
        let mut max_x = points[0][0];
        let mut max_y = points[0][1];
        for p in &points[1..] {
            min_x = min_with_policy(min_x, p[0]);
            min_y = min_with_policy(min_y, p[1]);
            max_x = max_with_policy(max_x, p[0]);
            max_y = max_with_policy(max_y, p[1]);
        }
        (min_x, min_y, max_x, max_y)
    }

    #[test]
    fn ok_case_rect_100x50() {
        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 5.0,
            spacing_mm: Some(2.0),
            parts: vec![PartRequest {
                id: "rect_100x50".to_string(),
                outer_points_mm: vec![[0.0, 0.0], [100.0, 0.0], [100.0, 50.0], [0.0, 50.0]],
                holes_points_mm: Vec::new(),
            }],
            stocks: Vec::new(),
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
            spacing_mm: Some(12.0),
            parts: vec![PartRequest {
                id: "small_with_tiny_hole".to_string(),
                outer_points_mm: vec![[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]],
                holes_points_mm: vec![vec![[9.0, 9.0], [11.0, 9.0], [11.0, 11.0], [9.0, 11.0]]],
            }],
            stocks: Vec::new(),
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
    fn hole_collapsed_detect_path_forces_outer_only_nesting_geometry() {
        let part = PartRequest {
            id: "detect_collapsed_with_surviving_hole".to_string(),
            outer_points_mm: vec![[0.0, 0.0], [80.0, 0.0], [80.0, 80.0], [0.0, 80.0]],
            holes_points_mm: vec![
                vec![[10.0, 10.0], [11.0, 10.0], [11.0, 11.0], [10.0, 11.0]],
                vec![[30.0, 30.0], [50.0, 30.0], [50.0, 50.0], [30.0, 50.0]],
            ],
        };
        let delta_mm = 1.1;

        let nominal = request_to_geometry(&part);
        assert!(
            inflate_part(&nominal, delta_mm).is_ok(),
            "test setup must hit detect path (inflate_part stays ok)"
        );
        let collapsed_indices = detect_collapsed_holes(&part, delta_mm);
        assert!(
            !collapsed_indices.is_empty(),
            "test setup must include a detect_collapsed_holes hit"
        );

        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 1.0,
            spacing_mm: Some(2.2),
            parts: vec![part],
            stocks: Vec::new(),
        };
        let resp = run_inflate_pipeline(req);
        assert_eq!(resp.parts.len(), 1);
        let part_resp = &resp.parts[0];
        assert_eq!(part_resp.status, STATUS_HOLE_COLLAPSED);
        assert!(
            !part_resp.inflated_outer_points_mm.is_empty(),
            "hole_collapsed detect path must still provide outer-only envelope"
        );
        assert!(
            part_resp.inflated_holes_points_mm.is_empty(),
            "hole_collapsed detect path must strip all holes from nesting geometry"
        );

        let hole_diags: Vec<&Diagnostic> = part_resp
            .diagnostics
            .iter()
            .filter(|d| d.code == CODE_HOLE_COLLAPSED)
            .collect();
        assert!(
            !hole_diags.is_empty(),
            "hole_collapsed detect path must emit HOLE_COLLAPSED diagnostics"
        );
        assert!(
            hole_diags.iter().all(|d| d.preserve_for_export == Some(true)
                && d.usable_for_nesting == Some(false)),
            "HOLE_COLLAPSED diagnostics must keep preserve_for_export=true and usable_for_nesting=false"
        );
    }

    #[test]
    fn determinism_case_same_request_same_output() {
        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 5.0,
            spacing_mm: None,
            parts: vec![PartRequest {
                id: "deterministic_part".to_string(),
                outer_points_mm: vec![[0.0, 0.0], [30.0, 0.0], [30.0, 10.0], [0.0, 10.0]],
                holes_points_mm: Vec::new(),
            }],
            stocks: Vec::new(),
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
    fn pipeline_float_policy_hole_bbox_near_equal_bounds_are_stable() {
        let hole = vec![
            [10.0, 10.0],
            [20.0, 10.0],
            [20.0 + 5e-10, 20.0],
            [10.0, 20.0],
        ];
        let bbox_a = hole_bbox_mm(&hole).expect("bbox must exist");
        let bbox_b = hole_bbox_mm(&hole).expect("bbox must exist");
        assert_eq!(bbox_a, bbox_b);
    }

    #[test]
    fn pipeline_float_policy_stock_hole_obstacle_ring_start_is_canonical() {
        let hole = vec![[10.0, 10.0], [30.0, 10.0], [30.0, 30.0], [10.0, 30.0]];
        let expanded = inflate_stock_hole_obstacle(&hole, 1.0).expect("stock hole inflate must work");
        let first = expanded.first().expect("expanded ring must not be empty");
        let min_pt = expanded
            .iter()
            .min_by_key(|p| (mm_to_i64(p[0]), mm_to_i64(p[1])))
            .expect("expanded ring must have min point");
        assert_eq!(mm_to_i64(first[0]), mm_to_i64(min_pt[0]));
        assert_eq!(mm_to_i64(first[1]), mm_to_i64(min_pt[1]));
    }

    #[test]
    fn pipeline_float_policy_repeated_request_is_byte_identical() {
        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 5.0,
            spacing_mm: Some(0.6),
            parts: vec![PartRequest {
                id: "near_hole".to_string(),
                outer_points_mm: vec![[0.0, 0.0], [60.0, 0.0], [60.0, 60.0], [0.0, 60.0]],
                holes_points_mm: vec![vec![
                    [19.9999996, 20.0],
                    [40.0000004, 20.0],
                    [40.0000004, 40.0],
                    [19.9999996, 40.0],
                ]],
            }],
            stocks: Vec::new(),
        };

        let out_a = serde_json::to_string(&run_inflate_pipeline(req.clone())).expect("serialize A");
        let out_b = serde_json::to_string(&run_inflate_pipeline(req)).expect("serialize B");
        assert_eq!(out_a, out_b);
    }

    #[test]
    fn self_intersect_bow_tie_case_returns_status_and_diagnostic() {
        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 5.0,
            spacing_mm: None,
            parts: vec![PartRequest {
                id: "bow_tie".to_string(),
                outer_points_mm: vec![[0.0, 0.0], [10.0, 10.0], [0.0, 10.0], [10.0, 0.0]],
                holes_points_mm: Vec::new(),
            }],
            stocks: Vec::new(),
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

    #[test]
    fn stock_irregular_with_hole_is_deterministic_and_offsets_in_correct_direction() {
        let nominal_outer = vec![
            [0.0, 0.0],
            [160.0, 0.0],
            [180.0, 55.0],
            [135.0, 120.0],
            [45.0, 110.0],
            [0.0, 45.0],
        ];
        let nominal_hole = vec![[55.0, 35.0], [90.0, 35.0], [90.0, 65.0], [55.0, 65.0]];

        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 2.0,
            margin_mm: 3.0,
            spacing_mm: Some(4.0),
            parts: Vec::new(),
            stocks: vec![StockRequest {
                id: "irregular_stock_1".to_string(),
                outer_points_mm: nominal_outer.clone(),
                holes_points_mm: vec![nominal_hole.clone()],
            }],
        };

        let resp_a = run_inflate_pipeline(req.clone());
        let resp_b = run_inflate_pipeline(req);
        let serialized_a = serde_json::to_vec(&resp_a).expect("serialize response A");
        let serialized_b = serde_json::to_vec(&resp_b).expect("serialize response B");
        assert_eq!(
            serialized_a, serialized_b,
            "stock pipeline output is not deterministic"
        );

        assert_eq!(resp_a.stocks.len(), 1);
        let stock = &resp_a.stocks[0];
        assert_eq!(stock.status, STATUS_OK);
        assert_eq!(stock.usable_holes_points_mm.len(), 1);

        let (nom_outer_w, nom_outer_h) = bbox_from_points_mm(&nominal_outer);
        let (usable_outer_w, usable_outer_h) = bbox_from_points_mm(&stock.usable_outer_points_mm);
        assert!(
            usable_outer_w < nom_outer_w,
            "stock outer width must shrink after deflate"
        );
        assert!(
            usable_outer_h < nom_outer_h,
            "stock outer height must shrink after deflate"
        );

        let (nom_hole_w, nom_hole_h) = bbox_from_points_mm(&nominal_hole);
        let (usable_hole_w, usable_hole_h) = bbox_from_points_mm(&stock.usable_holes_points_mm[0]);
        assert!(
            usable_hole_w > nom_hole_w,
            "stock hole width must grow after inflate"
        );
        assert!(
            usable_hole_h > nom_hole_h,
            "stock hole height must grow after inflate"
        );
    }

    #[test]
    fn stock_outer_inflates_when_margin_below_half_spacing() {
        let nominal_outer = vec![[0.0, 0.0], [100.0, 0.0], [100.0, 60.0], [0.0, 60.0]];
        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 1.0,
            spacing_mm: Some(4.0),
            parts: Vec::new(),
            stocks: vec![StockRequest {
                id: "inflating_stock".to_string(),
                outer_points_mm: nominal_outer.clone(),
                holes_points_mm: Vec::new(),
            }],
        };

        let resp = run_inflate_pipeline(req);
        assert_eq!(resp.stocks.len(), 1);
        let stock = &resp.stocks[0];
        assert_eq!(stock.status, STATUS_OK);

        let (nom_outer_w, nom_outer_h) = bbox_from_points_mm(&nominal_outer);
        let (usable_outer_w, usable_outer_h) = bbox_from_points_mm(&stock.usable_outer_points_mm);
        assert!(
            usable_outer_w > nom_outer_w,
            "stock outer width must grow when margin < spacing/2"
        );
        assert!(
            usable_outer_h > nom_outer_h,
            "stock outer height must grow when margin < spacing/2"
        );

        let (min_x, min_y, max_x, max_y) = bounds_from_points_mm(&stock.usable_outer_points_mm);
        assert!(min_x < 0.0 && min_y < 0.0, "inflated stock min bounds should be negative");
        assert!(
            max_x > 100.0 && max_y > 60.0,
            "inflated stock max bounds should exceed nominal outer bounds"
        );
    }

    #[test]
    fn stock_hole_inflate_uses_spacing_half_without_margin_component() {
        let nominal_hole = vec![[40.0, 40.0], [60.0, 40.0], [60.0, 60.0], [40.0, 60.0]];
        let req = PipelineRequest {
            version: "pipeline_v1".to_string(),
            kerf_mm: 0.2,
            margin_mm: 10.0,
            spacing_mm: Some(4.0),
            parts: Vec::new(),
            stocks: vec![StockRequest {
                id: "stock_hole_spacing_only".to_string(),
                outer_points_mm: vec![[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 100.0]],
                holes_points_mm: vec![nominal_hole.clone()],
            }],
        };

        let resp = run_inflate_pipeline(req);
        assert_eq!(resp.stocks.len(), 1);
        let stock = &resp.stocks[0];
        assert_eq!(stock.status, STATUS_OK);
        assert_eq!(stock.usable_holes_points_mm.len(), 1);

        let (nom_hole_w, nom_hole_h) = bbox_from_points_mm(&nominal_hole);
        let (usable_hole_w, usable_hole_h) = bbox_from_points_mm(&stock.usable_holes_points_mm[0]);
        assert!(
            usable_hole_w > (nom_hole_w + 3.5) && usable_hole_w < (nom_hole_w + 5.0),
            "hole width growth should track spacing/2 (expected about +4mm), got {usable_hole_w}"
        );
        assert!(
            usable_hole_h > (nom_hole_h + 3.5) && usable_hole_h < (nom_hole_h + 5.0),
            "hole height growth should track spacing/2 (expected about +4mm), got {usable_hole_h}"
        );
    }
}
