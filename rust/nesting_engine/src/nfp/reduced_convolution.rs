use std::time::Instant;

use crate::geometry::{
    cleanup::{run_cleanup_pipeline, CleanupError},
    scale::SCALE,
    types::{cross_product_i128, Point64, Polygon64},
};

pub const RC_KERNEL_VERSION: &str = "reduced_convolution_v1";

#[derive(Debug, Clone)]
pub struct ReducedConvolutionOptions {
    pub integer_scale: i64,
    pub min_edge_length_units: i64,
    pub max_output_vertices: usize,
    pub auto_cleanup: bool,
}

impl Default for ReducedConvolutionOptions {
    fn default() -> Self {
        Self {
            integer_scale: SCALE,
            min_edge_length_units: 100,
            max_output_vertices: 50_000,
            auto_cleanup: true,
        }
    }
}

#[derive(Debug, Clone)]
pub enum RcNfpError {
    InputTooComplex { vertex_count: usize, limit: usize },
    EmptyInput,
    NotImplemented,
    ComputationFailed(String),
    OutputExceedsCap { vertex_count: usize, cap: usize },
    CleanupFailed(String),
}

#[derive(Debug, Clone)]
pub struct RcNfpResult {
    pub polygon: Option<Polygon64>,
    pub raw_vertex_count: usize,
    pub computation_time_ms: u64,
    pub error: Option<RcNfpError>,
    pub kernel_version: &'static str,
}

pub fn compute_rc_nfp(
    part_a: &Polygon64,
    part_b: &Polygon64,
    options: &ReducedConvolutionOptions,
) -> RcNfpResult {
    let started = Instant::now();

    if part_a.outer.len() < 3 || part_b.outer.len() < 3 {
        return error_result(RcNfpError::EmptyInput, started.elapsed().as_millis() as u64);
    }

    let cleaned_a = match maybe_cleanup(part_a, options.auto_cleanup) {
        Ok(poly) => poly,
        Err(err) => {
            return error_result(
                RcNfpError::CleanupFailed(cleanup_error_message(err)),
                started.elapsed().as_millis() as u64,
            )
        }
    };
    let cleaned_b = match maybe_cleanup(part_b, options.auto_cleanup) {
        Ok(poly) => poly,
        Err(err) => {
            return error_result(
                RcNfpError::CleanupFailed(cleanup_error_message(err)),
                started.elapsed().as_millis() as u64,
            )
        }
    };

    if cleaned_a.outer.len() < 3 || cleaned_b.outer.len() < 3 {
        return error_result(RcNfpError::EmptyInput, started.elapsed().as_millis() as u64);
    }

    let complexity = cleaned_a.outer.len().saturating_mul(cleaned_b.outer.len());
    let input_limit = options.max_output_vertices.saturating_mul(8);
    if complexity > input_limit {
        return error_result(
            RcNfpError::InputTooComplex {
                vertex_count: complexity,
                limit: input_limit,
            },
            started.elapsed().as_millis() as u64,
        );
    }

    // Prototype path: full reduced-convolution loop assembly is not implemented yet.
    // We compute a deterministic convex-hull envelope of Minkowski vertex sums.
    // This gives a bounded, non-panicking baseline for T05 experimentation.
    let reflected_b = reflect_polygon(&cleaned_b);

    let mut summed_points = Vec::with_capacity(
        cleaned_a
            .outer
            .len()
            .saturating_mul(reflected_b.outer.len()),
    );
    for a in &cleaned_a.outer {
        for b in &reflected_b.outer {
            summed_points.push(Point64 {
                x: a.x.saturating_add(b.x),
                y: a.y.saturating_add(b.y),
            });
        }
    }

    if summed_points.len() < 3 {
        return error_result(
            RcNfpError::NotImplemented,
            started.elapsed().as_millis() as u64,
        );
    }

    let hull = convex_hull(&summed_points);
    let raw_vertex_count = hull.len();
    if hull.len() < 3 {
        return error_result(
            RcNfpError::ComputationFailed("convex hull output is degenerate".to_string()),
            started.elapsed().as_millis() as u64,
        );
    }

    let mut output = Polygon64 {
        outer: hull,
        holes: Vec::new(),
    };

    if options.min_edge_length_units > 1 {
        output.outer = filter_short_edges(&output.outer, options.min_edge_length_units);
    }

    if output.outer.len() < 3 {
        return error_result(
            RcNfpError::ComputationFailed("edge filtering produced degenerate polygon".to_string()),
            started.elapsed().as_millis() as u64,
        );
    }

    if options.auto_cleanup {
        output = match run_cleanup_pipeline(&output, 0.1) {
            Ok(cleaned) => cleaned.polygon,
            Err(err) => {
                return error_result(
                    RcNfpError::CleanupFailed(cleanup_error_message(err)),
                    started.elapsed().as_millis() as u64,
                )
            }
        };
    }

    if output.outer.len() > options.max_output_vertices {
        return error_result(
            RcNfpError::OutputExceedsCap {
                vertex_count: output.outer.len(),
                cap: options.max_output_vertices,
            },
            started.elapsed().as_millis() as u64,
        );
    }

    RcNfpResult {
        polygon: Some(output),
        raw_vertex_count,
        computation_time_ms: started.elapsed().as_millis() as u64,
        error: None,
        kernel_version: RC_KERNEL_VERSION,
    }
}

fn maybe_cleanup(poly: &Polygon64, enabled: bool) -> Result<Polygon64, CleanupError> {
    if enabled {
        run_cleanup_pipeline(poly, 0.1).map(|res| res.polygon)
    } else {
        Ok(poly.clone())
    }
}

fn cleanup_error_message(err: CleanupError) -> String {
    match err {
        CleanupError::EmptyPolygon => "cleanup empty polygon".to_string(),
        CleanupError::InvalidOrientationAfterCleanup(msg) => {
            format!("cleanup orientation error: {msg}")
        }
        CleanupError::InsufficientVertices { count } => {
            format!("cleanup insufficient vertices: {count}")
        }
    }
}

fn reflect_polygon(poly: &Polygon64) -> Polygon64 {
    Polygon64 {
        outer: poly
            .outer
            .iter()
            .map(|p| Point64 { x: -p.x, y: -p.y })
            .collect(),
        holes: poly
            .holes
            .iter()
            .map(|ring| ring.iter().map(|p| Point64 { x: -p.x, y: -p.y }).collect())
            .collect(),
    }
}

fn convex_hull(points: &[Point64]) -> Vec<Point64> {
    let mut pts = points.to_vec();
    pts.sort_by_key(|p| (p.x, p.y));
    pts.dedup();
    if pts.len() <= 1 {
        return pts;
    }

    let mut lower: Vec<Point64> = Vec::new();
    for p in &pts {
        while lower.len() >= 2 {
            let o = lower[lower.len() - 2];
            let a = lower[lower.len() - 1];
            let cross = cross_product_i128(a.x - o.x, a.y - o.y, p.x - a.x, p.y - a.y);
            if cross <= 0 {
                lower.pop();
            } else {
                break;
            }
        }
        lower.push(*p);
    }

    let mut upper: Vec<Point64> = Vec::new();
    for p in pts.iter().rev() {
        while upper.len() >= 2 {
            let o = upper[upper.len() - 2];
            let a = upper[upper.len() - 1];
            let cross = cross_product_i128(a.x - o.x, a.y - o.y, p.x - a.x, p.y - a.y);
            if cross <= 0 {
                upper.pop();
            } else {
                break;
            }
        }
        upper.push(*p);
    }

    lower.pop();
    upper.pop();
    lower.extend(upper);
    lower
}

fn filter_short_edges(ring: &[Point64], min_edge_length_units: i64) -> Vec<Point64> {
    if ring.len() < 3 || min_edge_length_units <= 1 {
        return ring.to_vec();
    }

    let min2 = (min_edge_length_units as i128) * (min_edge_length_units as i128);
    let mut out = Vec::with_capacity(ring.len());

    for i in 0..ring.len() {
        let curr = ring[i];
        let next = ring[(i + 1) % ring.len()];
        let dx = (next.x - curr.x) as i128;
        let dy = (next.y - curr.y) as i128;
        let len2 = dx * dx + dy * dy;
        if len2 < min2 {
            continue;
        }
        out.push(curr);
    }

    if out.len() < 3 {
        ring.to_vec()
    } else {
        out
    }
}

fn error_result(err: RcNfpError, time_ms: u64) -> RcNfpResult {
    RcNfpResult {
        polygon: None,
        raw_vertex_count: 0,
        computation_time_ms: time_ms,
        error: Some(err),
        kernel_version: RC_KERNEL_VERSION,
    }
}
