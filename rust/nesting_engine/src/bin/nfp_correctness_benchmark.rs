use std::fs;
use std::path::{Path, PathBuf};

use nesting_engine::geometry::{
    scale::{i64_to_mm, mm_to_i64, TOUCH_TOL},
    types::{cross_product_i128, is_ccw, Point64, Polygon64},
};
use nesting_engine::nfp::{
    minkowski_cleanup::{run_minkowski_cleanup, CleanupOptions},
    reduced_convolution::{compute_rc_nfp, ReducedConvolutionOptions},
};
use serde::{Deserialize, Serialize};

const DEFAULT_FIXTURE: &str = "tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum NfpSource {
    ReducedConvolutionV1,
    MockExact,
    ExternalJson,
}

#[derive(Debug, Clone)]
struct CliArgs {
    fixture: PathBuf,
    nfp_source: NfpSource,
    nfp_json: Option<PathBuf>,
    sample_inside: usize,
    sample_outside: usize,
    sample_boundary: usize,
    boundary_perturbation_mm: f64,
    output_json: bool,
}

#[derive(Debug, Deserialize)]
struct PairFixture {
    pair_id: String,
    part_a: FixturePart,
    part_b: FixturePart,
}

#[derive(Debug, Deserialize)]
struct FixturePart {
    points_mm: Vec<[f64; 2]>,
    #[serde(default)]
    holes_mm: Vec<Vec<[f64; 2]>>,
}

#[derive(Debug, Serialize)]
struct BenchmarkOutput {
    benchmark_version: &'static str,
    nfp_source: &'static str,
    pair_id: String,
    sample_count_inside: usize,
    sample_count_outside: usize,
    sample_count_boundary: usize,
    false_positive_count: usize,
    false_negative_count: usize,
    false_positive_rate: f64,
    false_negative_rate: f64,
    boundary_penetration_max_mm: f64,
    correctness_verdict: String,
    nfp_was_available: bool,
    notes: String,
    /// True if the NFP polygon has at least one hole ring.
    boundary_holes_supported: bool,
    /// Number of boundary samples taken from the outer ring.
    outer_boundary_samples: usize,
    /// Number of boundary samples taken from hole rings.
    hole_boundary_samples: usize,
    /// Maximum penetration on the outer boundary (mm).
    outer_boundary_penetration_max_mm: f64,
    /// Maximum penetration on hole boundaries (mm).
    hole_boundary_penetration_max_mm: f64,
    /// Number of hole boundary samples that returned exact collision.
    hole_boundary_collision_count: usize,
    /// Number of hole boundary samples that did NOT return collision.
    hole_boundary_non_collision_count: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum PointLocation {
    Outside,
    Inside,
    OnBoundary,
}

#[derive(Debug, Clone, Copy)]
struct BoundarySample {
    point: Point64,
    outward_nx: f64,
    outward_ny: f64,
    /// True if this sample was taken from a hole ring, false if from outer ring.
    is_hole: bool,
}

#[derive(Debug, Clone, Copy)]
struct Aabb {
    min_x: i64,
    min_y: i64,
    max_x: i64,
    max_y: i64,
}

#[derive(Debug, Clone, Copy)]
struct Lcg {
    state: u64,
}

impl Lcg {
    fn new(seed: u64) -> Self {
        Self { state: seed.max(1) }
    }

    fn next_u64(&mut self) -> u64 {
        self.state = self
            .state
            .wrapping_mul(6364136223846793005)
            .wrapping_add(1442695040888963407);
        self.state
    }

    fn next_f64(&mut self) -> f64 {
        let x = self.next_u64() >> 11;
        (x as f64) / ((1u64 << 53) as f64)
    }

    fn range_i64(&mut self, min: i64, max: i64) -> i64 {
        if min >= max {
            return min;
        }
        let span = (max as i128 - min as i128 + 1) as u128;
        let v = (self.next_u64() as u128) % span;
        min.saturating_add(v as i64)
    }
}

fn parse_args(raw: &[String]) -> Result<CliArgs, String> {
    let mut fixture = PathBuf::from(DEFAULT_FIXTURE);
    let mut nfp_source = NfpSource::ReducedConvolutionV1;
    let mut nfp_json: Option<PathBuf> = None;
    let mut sample_inside = 1000usize;
    let mut sample_outside = 1000usize;
    let mut sample_boundary = 200usize;
    let mut boundary_perturbation_mm = 0.01f64;
    let mut output_json = false;

    let mut idx = 0usize;
    while idx < raw.len() {
        let arg = &raw[idx];
        if arg == "--help" || arg == "-h" {
            print_help();
            std::process::exit(0);
        }
        if arg == "--output-json" {
            output_json = true;
            idx += 1;
            continue;
        }
        if arg == "--fixture" {
            idx += 1;
            if idx >= raw.len() {
                return Err("missing value for --fixture".to_string());
            }
            fixture = PathBuf::from(&raw[idx]);
            idx += 1;
            continue;
        }
        if let Some(v) = arg.strip_prefix("--fixture=") {
            fixture = PathBuf::from(v);
            idx += 1;
            continue;
        }
        if arg == "--nfp-source" {
            idx += 1;
            if idx >= raw.len() {
                return Err("missing value for --nfp-source".to_string());
            }
            nfp_source = parse_nfp_source(&raw[idx])?;
            idx += 1;
            continue;
        }
        if let Some(v) = arg.strip_prefix("--nfp-source=") {
            nfp_source = parse_nfp_source(v)?;
            idx += 1;
            continue;
        }
        if arg == "--nfp-json" {
            idx += 1;
            if idx >= raw.len() {
                return Err("missing value for --nfp-json".to_string());
            }
            nfp_json = Some(PathBuf::from(&raw[idx]));
            idx += 1;
            continue;
        }
        if let Some(v) = arg.strip_prefix("--nfp-json=") {
            nfp_json = Some(PathBuf::from(v));
            idx += 1;
            continue;
        }
        if arg == "--sample-inside" {
            idx += 1;
            if idx >= raw.len() {
                return Err("missing value for --sample-inside".to_string());
            }
            sample_inside = parse_usize("--sample-inside", &raw[idx])?;
            idx += 1;
            continue;
        }
        if let Some(v) = arg.strip_prefix("--sample-inside=") {
            sample_inside = parse_usize("--sample-inside", v)?;
            idx += 1;
            continue;
        }
        if arg == "--sample-outside" {
            idx += 1;
            if idx >= raw.len() {
                return Err("missing value for --sample-outside".to_string());
            }
            sample_outside = parse_usize("--sample-outside", &raw[idx])?;
            idx += 1;
            continue;
        }
        if let Some(v) = arg.strip_prefix("--sample-outside=") {
            sample_outside = parse_usize("--sample-outside", v)?;
            idx += 1;
            continue;
        }
        if arg == "--sample-boundary" {
            idx += 1;
            if idx >= raw.len() {
                return Err("missing value for --sample-boundary".to_string());
            }
            sample_boundary = parse_usize("--sample-boundary", &raw[idx])?;
            idx += 1;
            continue;
        }
        if let Some(v) = arg.strip_prefix("--sample-boundary=") {
            sample_boundary = parse_usize("--sample-boundary", v)?;
            idx += 1;
            continue;
        }
        if arg == "--boundary-perturbation" {
            idx += 1;
            if idx >= raw.len() {
                return Err("missing value for --boundary-perturbation".to_string());
            }
            boundary_perturbation_mm = parse_f64("--boundary-perturbation", &raw[idx])?;
            idx += 1;
            continue;
        }
        if let Some(v) = arg.strip_prefix("--boundary-perturbation=") {
            boundary_perturbation_mm = parse_f64("--boundary-perturbation", v)?;
            idx += 1;
            continue;
        }

        return Err(format!("unknown argument: {arg}"));
    }

    Ok(CliArgs {
        fixture,
        nfp_source,
        nfp_json,
        sample_inside,
        sample_outside,
        sample_boundary,
        boundary_perturbation_mm,
        output_json,
    })
}

fn parse_nfp_source(value: &str) -> Result<NfpSource, String> {
    match value {
        "reduced_convolution_v1" => Ok(NfpSource::ReducedConvolutionV1),
        "mock_exact" => Ok(NfpSource::MockExact),
        "external_json" => Ok(NfpSource::ExternalJson),
        _ => Err(format!("invalid --nfp-source value: '{value}'")),
    }
}

fn parse_usize(flag: &str, value: &str) -> Result<usize, String> {
    value
        .trim()
        .parse::<usize>()
        .map_err(|_| format!("invalid value for {flag}: '{value}'"))
}

fn parse_f64(flag: &str, value: &str) -> Result<f64, String> {
    value
        .trim()
        .parse::<f64>()
        .map_err(|_| format!("invalid value for {flag}: '{value}'"))
}

fn print_help() {
    println!("nfp_correctness_benchmark");
    println!("  --fixture <path>                (default: {DEFAULT_FIXTURE})");
    println!(
        "  --nfp-source <src>              reduced_convolution_v1 | mock_exact | external_json"
    );
    println!("  --nfp-json <path>               (required when --nfp-source=external_json)");
    println!("  --sample-inside <N>             (default: 1000)");
    println!("  --sample-outside <N>            (default: 1000)");
    println!("  --sample-boundary <N>           (default: 200)");
    println!("  --boundary-perturbation <mm>    (default: 0.01)");
    println!("  --output-json");
}

fn read_fixture(path: &Path) -> Result<String, String> {
    if path.exists() {
        return fs::read_to_string(path)
            .map_err(|err| format!("failed to read fixture '{}': {err}", path.display()));
    }

    let fallback = Path::new("../..").join(path);
    if fallback.exists() {
        return fs::read_to_string(&fallback).map_err(|err| {
            format!(
                "failed to read fixture fallback '{}': {err}",
                fallback.display()
            )
        });
    }

    Err(format!(
        "fixture not found at '{}' or '{}'",
        path.display(),
        fallback.display()
    ))
}

fn fixture_part_to_polygon(part: &FixturePart) -> Result<Polygon64, String> {
    if part.points_mm.len() < 3 {
        return Err(format!(
            "fixture part has insufficient outer points: {}",
            part.points_mm.len()
        ));
    }

    let outer: Vec<Point64> = part
        .points_mm
        .iter()
        .map(|p| Point64 {
            x: mm_to_i64(p[0]),
            y: mm_to_i64(p[1]),
        })
        .collect();

    let holes: Vec<Vec<Point64>> = part
        .holes_mm
        .iter()
        .map(|ring| {
            ring.iter()
                .map(|p| Point64 {
                    x: mm_to_i64(p[0]),
                    y: mm_to_i64(p[1]),
                })
                .collect::<Vec<Point64>>()
        })
        .collect();

    Ok(Polygon64 { outer, holes })
}

fn translated(poly: &Polygon64, by: Point64) -> Polygon64 {
    Polygon64 {
        outer: poly
            .outer
            .iter()
            .map(|p| Point64 {
                x: p.x.saturating_add(by.x),
                y: p.y.saturating_add(by.y),
            })
            .collect(),
        holes: poly
            .holes
            .iter()
            .map(|ring| {
                ring.iter()
                    .map(|p| Point64 {
                        x: p.x.saturating_add(by.x),
                        y: p.y.saturating_add(by.y),
                    })
                    .collect()
            })
            .collect(),
    }
}

fn exact_collision_check(part_a: &Polygon64, part_b: &Polygon64, placement: &Point64) -> bool {
    let moved_b = translated(part_b, *placement);
    let aabb_a = aabb_from_polygon64(part_a);
    let aabb_b = aabb_from_polygon64(&moved_b);
    if !aabb_overlaps(&aabb_a, &aabb_b) {
        return false;
    }
    polygons_intersect_or_touch(part_a, &moved_b)
}

fn polygon_rings(poly: &Polygon64) -> impl Iterator<Item = &[Point64]> {
    std::iter::once(poly.outer.as_slice()).chain(poly.holes.iter().map(Vec::as_slice))
}

fn polygons_intersect_or_touch(a: &Polygon64, b: &Polygon64) -> bool {
    if a.outer.len() < 3 || b.outer.len() < 3 {
        return true;
    }

    for ring_a in polygon_rings(a) {
        for ring_b in polygon_rings(b) {
            if ring_intersects_ring_or_touch(ring_a, ring_b) {
                return true;
            }
        }
    }

    point_in_polygon(a.outer[0], b) != PointLocation::Outside
        || point_in_polygon(b.outer[0], a) != PointLocation::Outside
}

fn ring_intersects_ring_or_touch(a: &[Point64], b: &[Point64]) -> bool {
    if a.len() < 2 || b.len() < 2 {
        return false;
    }
    for i in 0..a.len() {
        let a0 = a[i];
        let a1 = a[(i + 1) % a.len()];
        for j in 0..b.len() {
            let b0 = b[j];
            let b1 = b[(j + 1) % b.len()];
            if segments_intersect_or_touch(a0, a1, b0, b1) {
                return true;
            }
        }
    }
    false
}

fn segments_intersect_or_touch(a0: Point64, a1: Point64, b0: Point64, b1: Point64) -> bool {
    let o1 = orient(a0, a1, b0);
    let o2 = orient(a0, a1, b1);
    let o3 = orient(b0, b1, a0);
    let o4 = orient(b0, b1, a1);

    if o1 == 0 && point_on_segment_inclusive(a0, a1, b0) {
        return true;
    }
    if o2 == 0 && point_on_segment_inclusive(a0, a1, b1) {
        return true;
    }
    if o3 == 0 && point_on_segment_inclusive(b0, b1, a0) {
        return true;
    }
    if o4 == 0 && point_on_segment_inclusive(b0, b1, a1) {
        return true;
    }
    o1 != o2 && o3 != o4
}

fn orient(a: Point64, b: Point64, c: Point64) -> i8 {
    let v = cross_product_i128(b.x - a.x, b.y - a.y, c.x - a.x, c.y - a.y);
    if v > 0 {
        1
    } else if v < 0 {
        -1
    } else {
        0
    }
}

fn point_in_polygon(point: Point64, poly: &Polygon64) -> PointLocation {
    match point_in_ring(point, &poly.outer) {
        PointLocation::Outside => PointLocation::Outside,
        PointLocation::OnBoundary => PointLocation::OnBoundary,
        PointLocation::Inside => {
            for hole in &poly.holes {
                match point_in_ring(point, hole) {
                    PointLocation::Outside => {}
                    PointLocation::OnBoundary => return PointLocation::OnBoundary,
                    PointLocation::Inside => return PointLocation::Outside,
                }
            }
            PointLocation::Inside
        }
    }
}

fn point_in_ring(point: Point64, ring: &[Point64]) -> PointLocation {
    if ring.len() < 3 {
        return PointLocation::Outside;
    }

    for idx in 0..ring.len() {
        let start = ring[idx];
        let end = ring[(idx + 1) % ring.len()];
        if point_on_segment_inclusive(start, end, point) {
            return PointLocation::OnBoundary;
        }
    }

    let mut winding = 0_i32;
    for idx in 0..ring.len() {
        let start = ring[idx];
        let end = ring[(idx + 1) % ring.len()];

        if start.y <= point.y {
            if end.y > point.y {
                let cross = cross_product_i128(
                    end.x - start.x,
                    end.y - start.y,
                    point.x - start.x,
                    point.y - start.y,
                );
                if cross > 0 {
                    winding += 1;
                }
            }
        } else if end.y <= point.y {
            let cross = cross_product_i128(
                end.x - start.x,
                end.y - start.y,
                point.x - start.x,
                point.y - start.y,
            );
            if cross < 0 {
                winding -= 1;
            }
        }
    }

    if winding == 0 {
        PointLocation::Outside
    } else {
        PointLocation::Inside
    }
}

fn point_on_segment_inclusive(a: Point64, b: Point64, p: Point64) -> bool {
    let cross = cross_product_i128(b.x - a.x, b.y - a.y, p.x - a.x, p.y - a.y);
    if cross != 0 {
        return false;
    }

    let min_x = a.x.min(b.x);
    let max_x = a.x.max(b.x);
    let min_y = a.y.min(b.y);
    let max_y = a.y.max(b.y);
    p.x >= min_x && p.x <= max_x && p.y >= min_y && p.y <= max_y
}

fn aabb_from_polygon64(poly: &Polygon64) -> Aabb {
    let first = poly
        .outer
        .first()
        .copied()
        .unwrap_or(Point64 { x: 0, y: 0 });
    let mut min_x = first.x;
    let mut min_y = first.y;
    let mut max_x = first.x;
    let mut max_y = first.y;
    for p in &poly.outer[1..] {
        min_x = min_x.min(p.x);
        min_y = min_y.min(p.y);
        max_x = max_x.max(p.x);
        max_y = max_y.max(p.y);
    }
    Aabb {
        min_x,
        min_y,
        max_x,
        max_y,
    }
}

fn aabb_overlaps(a: &Aabb, b: &Aabb) -> bool {
    a.max_x.saturating_add(TOUCH_TOL) >= b.min_x.saturating_sub(TOUCH_TOL)
        && b.max_x.saturating_add(TOUCH_TOL) >= a.min_x.saturating_sub(TOUCH_TOL)
        && a.max_y.saturating_add(TOUCH_TOL) >= b.min_y.saturating_sub(TOUCH_TOL)
        && b.max_y.saturating_add(TOUCH_TOL) >= a.min_y.saturating_sub(TOUCH_TOL)
}

fn sample_points_inside(poly: &Polygon64, n: usize, seed: u64) -> Vec<Point64> {
    sample_points_by_location(poly, n, seed, PointLocation::Inside)
}

fn sample_points_outside(poly: &Polygon64, n: usize, seed: u64) -> Vec<Point64> {
    sample_points_by_location(poly, n, seed, PointLocation::Outside)
}

fn sample_points_by_location(
    poly: &Polygon64,
    n: usize,
    seed: u64,
    target: PointLocation,
) -> Vec<Point64> {
    let bbox = aabb_from_polygon64(poly);
    let expand_x = (bbox.max_x - bbox.min_x).abs().max(mm_to_i64(10.0));
    let expand_y = (bbox.max_y - bbox.min_y).abs().max(mm_to_i64(10.0));
    let min_x = bbox.min_x.saturating_sub(expand_x);
    let max_x = bbox.max_x.saturating_add(expand_x);
    let min_y = bbox.min_y.saturating_sub(expand_y);
    let max_y = bbox.max_y.saturating_add(expand_y);

    let mut rng = Lcg::new(seed);
    let mut out = Vec::with_capacity(n);
    let max_iter = n.saturating_mul(400).max(1_000);

    for _ in 0..max_iter {
        if out.len() >= n {
            break;
        }
        let p = Point64 {
            x: rng.range_i64(min_x, max_x),
            y: rng.range_i64(min_y, max_y),
        };
        let loc = point_in_polygon(p, poly);
        if loc == target {
            out.push(p);
        }
    }

    out
}

fn placement_sampling_box(part_a: &Polygon64, part_b: &Polygon64) -> Polygon64 {
    let a = aabb_from_polygon64(part_a);
    let b = aabb_from_polygon64(part_b);
    let margin = mm_to_i64(20.0);
    let min_x = a.min_x.saturating_sub(b.max_x).saturating_sub(margin);
    let max_x = a.max_x.saturating_sub(b.min_x).saturating_add(margin);
    let min_y = a.min_y.saturating_sub(b.max_y).saturating_sub(margin);
    let max_y = a.max_y.saturating_sub(b.min_y).saturating_add(margin);
    Polygon64 {
        outer: vec![
            Point64 { x: min_x, y: min_y },
            Point64 { x: max_x, y: min_y },
            Point64 { x: max_x, y: max_y },
            Point64 { x: min_x, y: max_y },
        ],
        holes: Vec::new(),
    }
}

fn sample_points_by_collision(
    part_a: &Polygon64,
    part_b: &Polygon64,
    n_inside: usize,
    n_outside: usize,
    seed: u64,
) -> (Vec<Point64>, Vec<Point64>, Polygon64) {
    let box_poly = placement_sampling_box(part_a, part_b);
    let bbox = aabb_from_polygon64(&box_poly);
    let mut rng = Lcg::new(seed);
    let mut inside = Vec::with_capacity(n_inside);
    let mut outside = Vec::with_capacity(n_outside);
    let max_iter = (n_inside.saturating_add(n_outside))
        .saturating_mul(600)
        .max(5_000);

    for _ in 0..max_iter {
        if inside.len() >= n_inside && outside.len() >= n_outside {
            break;
        }
        let p = Point64 {
            x: rng.range_i64(bbox.min_x, bbox.max_x),
            y: rng.range_i64(bbox.min_y, bbox.max_y),
        };
        let collides = exact_collision_check(part_a, part_b, &p);
        if collides {
            if inside.len() < n_inside {
                inside.push(p);
            }
        } else if outside.len() < n_outside {
            outside.push(p);
        }
    }

    (inside, outside, box_poly)
}

/// Sample boundary points from a single ring with a given outward-normal orientation.
/// For outer rings: outward points away from polygon interior (ccw).
/// For hole rings: outward points into the hole interior (hole is CW, so inward normal = outward for the hole space).
fn sample_ring_boundary(
    ring: &[Point64],
    is_hole: bool,
    n: usize,
    rng: &mut Lcg,
) -> Vec<BoundarySample> {
    if ring.len() < 2 {
        return Vec::new();
    }

    // For outer ring (CCW): outward normal = left side of edge direction.
    // For hole ring (CW): outward normal = right side of edge direction (points into hole interior).
    // We want the normal that points AWAY from the filled region:
    //   - outer ring: outward normal points outside the polygon
    //   - hole ring: outward normal points inside the hole (toward the "outside" of the hole)
    // For a hole ring (CW), the left-hand normal points into the filled region,
    // so we flip: use right-hand normal for holes.
    let _ccw = is_ccw(ring);
    let flip = is_hole;

    let mut out = Vec::with_capacity(n);
    for _ in 0..n {
        let edge_idx = (rng.next_u64() as usize) % ring.len();
        let p0 = ring[edge_idx];
        let p1 = ring[(edge_idx + 1) % ring.len()];
        let t = rng.next_f64();
        let x = p0.x as f64 + (p1.x - p0.x) as f64 * t;
        let y = p0.y as f64 + (p1.y - p0.y) as f64 * t;

        let dx = (p1.x - p0.x) as f64;
        let dy = (p1.y - p0.y) as f64;
        let len = (dx * dx + dy * dy).sqrt();
        let (nx, ny) = if len == 0.0 {
            (0.0, 0.0)
        } else {
            // Standard outward normal for CCW ring = (dy, -dx)
            let nx = dy / len;
            let ny = -dx / len;
            if flip {
                (-nx, -ny)
            } else {
                (nx, ny)
            }
        };

        out.push(BoundarySample {
            point: Point64 {
                x: x.round() as i64,
                y: y.round() as i64,
            },
            outward_nx: nx,
            outward_ny: ny,
            is_hole,
        });
    }

    out
}

/// Sample boundary points from a polygon, covering both outer ring and all hole rings.
/// Allocation: at least half of samples from outer ring; remainder split across holes.
fn sample_polygon_boundary(poly: &Polygon64, total_n: usize, seed: u64) -> Vec<BoundarySample> {
    if poly.outer.len() < 2 && poly.holes.iter().all(|h| h.len() < 2) {
        return Vec::new();
    }

    let mut rng = Lcg::new(seed);
    let mut out = Vec::with_capacity(total_n);

    let has_holes = !poly.holes.is_empty();

    if has_holes {
        // Distribute: 50% outer, 50% holes (split evenly across hole rings).
        let outer_n = total_n / 2;
        let hole_n = total_n.saturating_sub(outer_n);
        let per_hole = hole_n / poly.holes.len().max(1);

        // Outer ring samples
        for s in sample_ring_boundary(&poly.outer, false, outer_n, &mut rng) {
            out.push(s);
        }

        // Hole ring samples
        for hole in &poly.holes {
            let n_this_hole = per_hole.min(hole.len().saturating_sub(1).max(1));
            for s in sample_ring_boundary(hole, true, n_this_hole, &mut rng) {
                out.push(s);
            }
        }

        // If we still have room (due to rounding), fill remaining from outer
        while out.len() < total_n {
            for s in sample_ring_boundary(&poly.outer, false, 1, &mut rng) {
                if out.len() >= total_n {
                    break;
                }
                out.push(s);
            }
            // Safety break if something went wrong
            if out.is_empty() {
                break;
            }
        }
    } else {
        // No holes: all samples from outer
        for s in sample_ring_boundary(&poly.outer, false, total_n, &mut rng) {
            out.push(s);
        }
    }

    out
}

fn sample_points_on_boundary(poly: &Polygon64, n: usize, seed: u64) -> Vec<BoundarySample> {
    sample_polygon_boundary(poly, n, seed)
}

fn offset_point(base: Point64, nx: f64, ny: f64, units: i64, sign: f64) -> Point64 {
    let du = units as f64 * sign;
    Point64 {
        x: (base.x as f64 + nx * du).round() as i64,
        y: (base.y as f64 + ny * du).round() as i64,
    }
}

fn run(args: CliArgs) -> Result<BenchmarkOutput, String> {
    let raw = read_fixture(&args.fixture)?;
    let fixture: PairFixture = serde_json::from_str(&raw)
        .map_err(|err| format!("invalid fixture JSON '{}': {err}", args.fixture.display()))?;

    let part_a = fixture_part_to_polygon(&fixture.part_a)?;
    let part_b = fixture_part_to_polygon(&fixture.part_b)?;

    let mut notes = Vec::new();
    let mut nfp_was_available = false;
    let nfp_polygon: Option<Polygon64> = match args.nfp_source {
        NfpSource::ReducedConvolutionV1 => {
            let rc = compute_rc_nfp(&part_a, &part_b, &ReducedConvolutionOptions::default());
            match rc.polygon {
                Some(raw_poly) => {
                    let cleanup = run_minkowski_cleanup(&raw_poly, &CleanupOptions::default());
                    if cleanup.is_valid {
                        nfp_was_available = true;
                        cleanup.polygon
                    } else {
                        notes.push("cleanup invalid; nfp unavailable".to_string());
                        None
                    }
                }
                None => {
                    notes.push("reduced_convolution returned no polygon".to_string());
                    None
                }
            }
        }
        NfpSource::MockExact => {
            nfp_was_available = true;
            None
        }
        NfpSource::ExternalJson => {
            let nfp_json_path = args
                .nfp_json
                .as_ref()
                .ok_or_else(|| "--nfp-json required when --nfp-source=external_json".to_string())?;

            let raw_json = fs::read_to_string(nfp_json_path).map_err(|err| {
                format!(
                    "failed to read --nfp-json '{}': {err}",
                    nfp_json_path.display()
                )
            })?;

            let probe_result: serde_json::Value = serde_json::from_str(&raw_json)
                .map_err(|err| format!("invalid JSON in '{}': {err}", nfp_json_path.display()))?;

            // Validate schema
            if probe_result.get("schema").and_then(|v| v.as_str())
                != Some("nfp_cgal_probe_result_v1")
            {
                notes.push("WARNING: JSON schema mismatch, proceeding anyway".to_string());
            }

            let status = probe_result
                .get("status")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown");
            if status != "success" {
                let err_msg = probe_result
                    .get("error")
                    .and_then(|v| v.get("message"))
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown");
                return Err(format!("external JSON has status='{status}': {err_msg}"));
            }

            let scale = probe_result
                .get("scale")
                .and_then(|v| v.as_i64())
                .unwrap_or(1_000_000);

            // Parse outer_i64
            let outer_i64 = probe_result
                .get("outer_i64")
                .and_then(|v| v.as_array())
                .ok_or_else(|| "missing or invalid outer_i64 in external JSON".to_string())?;

            let outer: Vec<Point64> = outer_i64
                .iter()
                .map(|pt| {
                    let arr = pt.as_array().ok_or("outer_i64 point is not array")?;
                    let x: i64 = arr.get(0).and_then(|v| v.as_i64()).ok_or("invalid x")?;
                    let y: i64 = arr.get(1).and_then(|v| v.as_i64()).ok_or("invalid y")?;
                    Ok(Point64 {
                        x: x * 1_000_000 / scale,
                        y: y * 1_000_000 / scale,
                    })
                })
                .collect::<Result<Vec<_>, _>>()
                .map_err(|e: String| format!("failed to parse outer_i64: {e}"))?;

            if outer.len() < 3 {
                return Err("outer_i64 has fewer than 3 vertices".to_string());
            }

            // Parse holes_i64 (hole-aware support)
            let holes: Vec<Vec<Point64>> = probe_result
                .get("holes_i64")
                .and_then(|v| v.as_array())
                .map(|holes_arr| {
                    holes_arr
                        .iter()
                        .filter_map(|hole_ring| {
                            let ring = hole_ring.as_array()?;
                            let pts: Vec<Point64> = ring
                                .iter()
                                .filter_map(|pt| {
                                    let arr = pt.as_array()?;
                                    let x: i64 = arr.get(0).and_then(|v| v.as_i64())?;
                                    let y: i64 = arr.get(1).and_then(|v| v.as_i64())?;
                                    Some(Point64 {
                                        x: x * 1_000_000 / scale,
                                        y: y * 1_000_000 / scale,
                                    })
                                })
                                .collect();
                            if pts.len() >= 3 {
                                Some(pts)
                            } else {
                                None
                            }
                        })
                        .collect()
                })
                .unwrap_or_default();

            if !holes.is_empty() {
                notes.push(format!(
                    "HOLES_AWARE: {} hole(s) parsed from holes_i64, hole-aware containment active",
                    holes.len()
                ));
            }

            nfp_was_available = true;
            Some(Polygon64 { outer, holes })
        }
    };

    let mut false_positive_count = 0usize;
    let mut false_negative_count = 0usize;
    let _boundary_penetration_max_mm = 0.0f64;

    let (inside_samples, outside_samples, boundary_samples) = match args.nfp_source {
        NfpSource::MockExact => {
            let (inside, outside, box_poly) = sample_points_by_collision(
                &part_a,
                &part_b,
                args.sample_inside,
                args.sample_outside,
                0xCAFE_BABE_21,
            );
            (
                inside,
                outside,
                sample_points_on_boundary(&box_poly, args.sample_boundary, 0xCAFE_BABE_22),
            )
        }
        NfpSource::ReducedConvolutionV1 => {
            if let Some(poly) = &nfp_polygon {
                (
                    sample_points_inside(poly, args.sample_inside, 0xCAFE_BABE_01),
                    sample_points_outside(poly, args.sample_outside, 0xCAFE_BABE_02),
                    sample_points_on_boundary(poly, args.sample_boundary, 0xCAFE_BABE_03),
                )
            } else {
                // Fallback sampling when polygon is unavailable (mostly for NOT_AVAILABLE path).
                let box_poly = Polygon64 {
                    outer: vec![
                        Point64 {
                            x: mm_to_i64(-50.0),
                            y: mm_to_i64(-50.0),
                        },
                        Point64 {
                            x: mm_to_i64(50.0),
                            y: mm_to_i64(-50.0),
                        },
                        Point64 {
                            x: mm_to_i64(50.0),
                            y: mm_to_i64(50.0),
                        },
                        Point64 {
                            x: mm_to_i64(-50.0),
                            y: mm_to_i64(50.0),
                        },
                    ],
                    holes: Vec::new(),
                };
                (
                    sample_points_inside(&box_poly, args.sample_inside, 0xCAFE_BABE_11),
                    sample_points_outside(&box_poly, args.sample_outside, 0xCAFE_BABE_12),
                    sample_points_on_boundary(&box_poly, args.sample_boundary, 0xCAFE_BABE_13),
                )
            }
        }
        NfpSource::ExternalJson => {
            // Uses the same sampling as ReducedConvolutionV1 since ExternalJson also populates nfp_polygon
            if let Some(poly) = &nfp_polygon {
                (
                    sample_points_inside(poly, args.sample_inside, 0xCAFE_BABE_31),
                    sample_points_outside(poly, args.sample_outside, 0xCAFE_BABE_32),
                    sample_points_on_boundary(poly, args.sample_boundary, 0xCAFE_BABE_33),
                )
            } else {
                return Err(
                    "ExternalJson: nfp_polygon is None despite setting nfp_was_available=true"
                        .to_string(),
                );
            }
        }
    };

    for point in &inside_samples {
        let exact = exact_collision_check(&part_a, &part_b, point);
        if !exact {
            false_negative_count += 1;
        }
    }

    for point in &outside_samples {
        let exact = exact_collision_check(&part_a, &part_b, point);
        if exact {
            false_positive_count += 1;
        }
    }
    let mut boundary_penetration_max_mm = 0.0f64;
    let mut outer_boundary_penetration_max_mm = 0.0f64;
    let mut hole_boundary_penetration_max_mm = 0.0f64;
    let mut hole_boundary_collision_count = 0usize;
    let mut hole_boundary_non_collision_count = 0usize;

    let perturb_units = mm_to_i64(args.boundary_perturbation_mm.max(0.0));
    if perturb_units > 0 {
        for sample in &boundary_samples {
            let outside_pt = offset_point(
                sample.point,
                sample.outward_nx,
                sample.outward_ny,
                perturb_units,
                1.0,
            );
            let inside_pt = offset_point(
                sample.point,
                sample.outward_nx,
                sample.outward_ny,
                perturb_units,
                -1.0,
            );

            let out_exact = exact_collision_check(&part_a, &part_b, &outside_pt);
            let in_exact = exact_collision_check(&part_a, &part_b, &inside_pt);

            if !in_exact || out_exact {
                let pen_mm = i64_to_mm(perturb_units);
                boundary_penetration_max_mm = boundary_penetration_max_mm.max(pen_mm);
                if sample.is_hole {
                    hole_boundary_penetration_max_mm = hole_boundary_penetration_max_mm.max(pen_mm);
                } else {
                    outer_boundary_penetration_max_mm =
                        outer_boundary_penetration_max_mm.max(pen_mm);
                }
            }

            // Count hole boundary collisions for diagnostics
            if sample.is_hole {
                if out_exact {
                    hole_boundary_collision_count += 1;
                } else {
                    hole_boundary_non_collision_count += 1;
                }
            }
        }
    }
    let total_samples = inside_samples.len().saturating_add(outside_samples.len());
    let false_positive_rate = if total_samples == 0 {
        0.0
    } else {
        false_positive_count as f64 / total_samples as f64
    };
    let false_negative_rate = if total_samples == 0 {
        0.0
    } else {
        false_negative_count as f64 / total_samples as f64
    };

    let correctness_verdict =
        if args.nfp_source == NfpSource::ReducedConvolutionV1 && !nfp_was_available {
            "NOT_AVAILABLE".to_string()
        } else if false_positive_rate > 0.0 {
            "FAIL_FALSE_POSITIVE".to_string()
        } else if false_negative_rate > 0.01 {
            "FAIL_FALSE_NEGATIVE".to_string()
        } else if false_negative_rate < 0.001 {
            "PASS".to_string()
        } else {
            "MARGINAL".to_string()
        };

    let notes = if notes.is_empty() {
        if correctness_verdict == "PASS" {
            "false_positive_rate=0.0 and false_negative_rate<0.001".to_string()
        } else if correctness_verdict == "MARGINAL" {
            "false_positive_rate=0.0 and conservative false_negative_rate<0.01".to_string()
        } else {
            "validator completed".to_string()
        }
    } else {
        notes.join("; ")
    };

    let boundary_holes_supported = nfp_polygon
        .as_ref()
        .map(|p| !p.holes.is_empty())
        .unwrap_or(false);

    let outer_boundary_samples = boundary_samples.iter().filter(|s| !s.is_hole).count();
    let hole_boundary_samples = boundary_samples.iter().filter(|s| s.is_hole).count();

    Ok(BenchmarkOutput {
        benchmark_version: "nfp_correctness_v1",
        nfp_source: match args.nfp_source {
            NfpSource::ReducedConvolutionV1 => "reduced_convolution_v1",
            NfpSource::MockExact => "mock_exact",
            NfpSource::ExternalJson => "external_json",
        },
        pair_id: fixture.pair_id,
        sample_count_inside: inside_samples.len(),
        sample_count_outside: outside_samples.len(),
        sample_count_boundary: boundary_samples.len(),
        false_positive_count,
        false_negative_count,
        false_positive_rate,
        false_negative_rate,
        boundary_penetration_max_mm,
        correctness_verdict,
        nfp_was_available,
        notes,
        boundary_holes_supported,
        outer_boundary_samples,
        hole_boundary_samples,
        outer_boundary_penetration_max_mm,
        hole_boundary_penetration_max_mm,
        hole_boundary_collision_count,
        hole_boundary_non_collision_count,
    })
}

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let args = match parse_args(&raw) {
        Ok(v) => v,
        Err(err) => {
            eprintln!("nfp_correctness_benchmark: {err}");
            print_help();
            std::process::exit(1);
        }
    };

    let output_json = args.output_json;
    match run(args) {
        Ok(output) => {
            if output_json {
                match serde_json::to_string(&output) {
                    Ok(s) => println!("{s}"),
                    Err(err) => {
                        eprintln!("nfp_correctness_benchmark: serialize failed: {err}");
                        std::process::exit(1);
                    }
                }
            } else {
                println!(
                    "pair={} source={} verdict={} fp_rate={:.6} fn_rate={:.6}",
                    output.pair_id,
                    output.nfp_source,
                    output.correctness_verdict,
                    output.false_positive_rate,
                    output.false_negative_rate
                );
            }
        }
        Err(err) => {
            eprintln!("nfp_correctness_benchmark: {err}");
            std::process::exit(1);
        }
    }
}
