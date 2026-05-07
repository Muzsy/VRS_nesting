//! CFR Union Benchmark — Strategy comparison replay
//!
//! Replays CFR snapshot files with different i_overlay Strategy variants,
//! measuring timing and verifying output equivalence against Strategy::List.
//!
//! Usage:
//!   cargo run --bin cfr_union_benchmark -- \
//!     --snapshots tmp/reports/nfp_cgal_probe/cfr_snapshots/ \
//!     --output tmp/reports/nfp_cgal_probe/cfr_benchmark_results.json

use std::cmp::Ordering;
use std::collections::BTreeSet;
use std::fs;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};

use i_overlay::core::{
    fill_rule::FillRule,
    overlay::IntOverlayOptions,
    overlay::Overlay,
    overlay_rule::OverlayRule,
    solver::{Precision, Solver, Strategy},
};
use i_overlay::i_float::int::point::IntPoint;
use i_overlay::i_shape::int::shape::{IntContour, IntShape};
use serde::{Deserialize, Serialize};

use nesting_engine::geometry::types::{cross_product_i128, Point64, Polygon64};
use nesting_engine::nfp::cfr::CfrSnapshot;

// ---------------------------------------------------------------------------
// Geometry helpers
// ---------------------------------------------------------------------------

fn signed_area2_i128(points: &[Point64]) -> i128 {
    if points.len() < 3 {
        return 0;
    }
    let mut area2 = 0_i128;
    for idx in 0..points.len() {
        let p0 = points[idx];
        let p1 = points[(idx + 1) % points.len()];
        area2 += (p0.x as i128) * (p1.y as i128) - (p1.x as i128) * (p0.y as i128);
    }
    area2
}

fn polygon_area(poly: &Polygon64) -> i128 {
    signed_area2_i128(&poly.outer).abs()
}

// ---------------------------------------------------------------------------
// OverlayBounds (copied from cfr.rs for standalone use)
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy)]
struct OverlayBounds {
    min_x: i64,
    min_y: i64,
    shift: u32,
}

impl OverlayBounds {
    fn from_polygons(polys: &[&Polygon64]) -> Option<Self> {
        let mut min_x = i64::MAX;
        let mut min_y = i64::MAX;
        let mut max_x = i64::MIN;
        let mut max_y = i64::MIN;

        for poly in polys {
            for point in &poly.outer {
                min_x = min_x.min(point.x);
                min_y = min_y.min(point.y);
                max_x = max_x.max(point.x);
                max_y = max_y.max(point.y);
            }
        }

        if min_x == i64::MAX || min_y == i64::MAX {
            return None;
        }

        let span_x = max_x.checked_sub(min_x)?;
        let span_y = max_y.checked_sub(min_y)?;
        let mut max_span = span_x.max(span_y);
        let mut shift = 0_u32;
        while max_span > i32::MAX as i64 {
            max_span = (max_span + 1) >> 1;
            shift = shift.checked_add(1)?;
        }

        Some(Self { min_x, min_y, shift })
    }

    fn encode_x(self, x: i64) -> Option<i32> {
        let translated = x.checked_sub(self.min_x)?;
        let scaled = if self.shift == 0 {
            translated
        } else {
            translated >> self.shift
        };
        i32::try_from(scaled).ok()
    }

    fn encode_y(self, y: i64) -> Option<i32> {
        let translated = y.checked_sub(self.min_y)?;
        let scaled = if self.shift == 0 {
            translated
        } else {
            translated >> self.shift
        };
        i32::try_from(scaled).ok()
    }

    fn decode_x(self, x: i32) -> Option<i64> {
        let scaled = (x as i64).checked_shl(self.shift)?;
        scaled.checked_add(self.min_x)
    }

    fn decode_y(self, y: i32) -> Option<i64> {
        let scaled = (y as i64).checked_shl(self.shift)?;
        scaled.checked_add(self.min_y)
    }
}

fn encode_polygon(poly: &Polygon64, bounds: OverlayBounds) -> Option<IntShape> {
    let mut shape: IntShape = Vec::with_capacity(1 + poly.holes.len());
    // Encode outer
    let mut outer = Vec::with_capacity(poly.outer.len());
    for point in &poly.outer {
        let x = bounds.encode_x(point.x)?;
        let ey = bounds.encode_y(point.y)?;
        outer.push(IntPoint::new(x, ey as i32));
    }
    shape.push(outer);
    // Encode holes (skip — snapshots have outer-only)
    Some(shape)
}

fn decode_contour(contour: &IntContour, bounds: OverlayBounds) -> Option<Vec<Point64>> {
    if contour.len() < 3 {
        return None;
    }
    let mut ring = Vec::with_capacity(contour.len());
    for point in contour {
        ring.push(Point64 {
            x: bounds.decode_x(point.x)?,
            y: bounds.decode_y(point.y)?,
        });
    }
    Some(ring)
}

fn decode_shape(shape: &IntShape, bounds: OverlayBounds) -> Option<Polygon64> {
    if shape.is_empty() {
        return None;
    }
    let outer = decode_contour(&shape[0], bounds)?;
    Some(Polygon64 { outer, holes: Vec::new() })
}

fn polygon_key(poly: &Polygon64) -> String {
    let area = signed_area2_i128(&poly.outer).abs();
    let min_x = poly.outer.iter().map(|p| p.x).min().unwrap_or(0);
    let min_y = poly.outer.iter().map(|p| p.y).min().unwrap_or(0);
    format!("{:020}_{:020}_{}", min_x, min_y, area)
}

fn polygons_equivalent(a: &[Polygon64], b: &[Polygon64]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let keys_a: BTreeSet<_> = a.iter().map(polygon_key).collect();
    let keys_b: BTreeSet<_> = b.iter().map(polygon_key).collect();
    keys_a == keys_b
}

// ---------------------------------------------------------------------------
// Core: run overlay with a given strategy
// ---------------------------------------------------------------------------

fn run_overlay(
    subject: &[IntShape],
    clip: &[IntShape],
    rule: OverlayRule,
    strategy: Strategy,
) -> Vec<IntShape> {
    let mut overlay = Overlay::with_shapes_options(
        subject,
        clip,
        IntOverlayOptions::keep_all_points(),
        Solver::with_strategy_and_precision(strategy, Precision::ABSOLUTE),
    );
    overlay.overlay(rule, FillRule::NonZero)
}

// ---------------------------------------------------------------------------
// Snapshot loading
// ---------------------------------------------------------------------------

fn load_snapshot(path: &Path) -> Option<(CfrSnapshot, Polygon64, Vec<Polygon64>)> {
    let json = fs::read_to_string(path).ok()?;
    let snap: CfrSnapshot = serde_json::from_str(&json).ok()?;

    let ifp = Polygon64 {
        outer: snap
            .ifp_outer
            .iter()
            .map(|&[x, y]| Point64 { x, y })
            .collect(),
        holes: Vec::new(),
    };

    let nfp_polys: Vec<Polygon64> = snap
        .nfp_outer_only
        .iter()
        .map(|ring| Polygon64 {
            outer: ring.iter().map(|&[x, y]| Point64 { x, y }).collect(),
            holes: Vec::new(),
        })
        .collect();

    Some((snap, ifp, nfp_polys))
}

// ---------------------------------------------------------------------------
// Run a single snapshot with all strategies
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Copy, PartialEq)]
enum StrategyName {
    List,
    Tree,
    Auto,
    Frag,
}

impl StrategyName {
    fn as_str(&self) -> &'static str {
        match self {
            Self::List => "List",
            Self::Tree => "Tree",
            Self::Auto => "Auto",
            Self::Frag => "Frag",
        }
    }

    fn to_strategy(&self) -> Strategy {
        match self {
            Self::List => Strategy::List,
            Self::Tree => Strategy::Tree,
            Self::Auto => Strategy::Auto,
            Self::Frag => Strategy::Frag,
        }
    }
}

#[derive(Debug, Clone)]
struct StrategyResult {
    name: StrategyName,
    union_time_ms: f64,
    diff_time_ms: f64,
    total_time_ms: f64,
    component_count: usize,
    output_equivalent_to_list: bool,
    crashed: bool,
    error: Option<String>,
}

fn run_snapshot(
    ifp: &Polygon64,
    nfp_polys: &[Polygon64],
    strat: StrategyName,
) -> StrategyResult {
    let overall_start = Instant::now();

    let mut all_polys: Vec<&Polygon64> = Vec::with_capacity(1 + nfp_polys.len());
    all_polys.push(ifp);
    all_polys.extend(nfp_polys.iter());

    let bounds = match OverlayBounds::from_polygons(&all_polys) {
        Some(b) => b,
        None => {
            return StrategyResult {
                name: strat,
                union_time_ms: 0.0,
                diff_time_ms: 0.0,
                total_time_ms: overall_start.elapsed().as_secs_f64() * 1000.0,
                component_count: 0,
                output_equivalent_to_list: false,
                crashed: true,
                error: Some("OverlayBounds::from_polygons failed".to_string()),
            };
        }
    };

    let ifp_shape = match encode_polygon(ifp, bounds) {
        Some(s) => s,
        None => {
            return StrategyResult {
                name: strat,
                union_time_ms: 0.0,
                diff_time_ms: 0.0,
                total_time_ms: overall_start.elapsed().as_secs_f64() * 1000.0,
                component_count: 0,
                output_equivalent_to_list: false,
                crashed: true,
                error: Some("IFP encode failed".to_string()),
            };
        }
    };

    let nfp_shapes: Vec<IntShape> = nfp_polys
        .iter()
        .filter_map(|poly| encode_polygon(poly, bounds))
        .collect();

    // Union step
    let union_start = Instant::now();
    let union_shapes = run_overlay(&nfp_shapes, &[], OverlayRule::Union, strat.to_strategy());
    let union_time_ms = union_start.elapsed().as_secs_f64() * 1000.0;

    // Diff step
    let diff_start = Instant::now();
    let diff_shapes = run_overlay(&[ifp_shape], &union_shapes, OverlayRule::Difference, strat.to_strategy());
    let diff_time_ms = diff_start.elapsed().as_secs_f64() * 1000.0;

    // Decode output
    let output: Vec<Polygon64> = diff_shapes
        .iter()
        .filter_map(|shape| decode_shape(shape, bounds))
        .collect();

    StrategyResult {
        name: strat,
        union_time_ms,
        diff_time_ms,
        total_time_ms: overall_start.elapsed().as_secs_f64() * 1000.0,
        component_count: output.len(),
        output_equivalent_to_list: false, // filled later
        crashed: false,
        error: None,
    }
}

// ---------------------------------------------------------------------------
// CLI
// ---------------------------------------------------------------------------

#[derive(Debug)]
struct CliArgs {
    snapshot_dir: PathBuf,
    output_path: Option<PathBuf>,
    strategies: Vec<StrategyName>,
    limit: Option<usize>,
}

fn parse_cli() -> CliArgs {
    let mut args = std::env::args().skip(1).peekable();
    let mut snapshot_dir: Option<PathBuf> = None;
    let mut output_path: Option<PathBuf> = None;
    let mut limit: Option<usize> = None;
    let mut strategies = vec![StrategyName::List, StrategyName::Tree, StrategyName::Auto, StrategyName::Frag];

    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--snapshots" => snapshot_dir = args.next().map(PathBuf::from),
            "--output" => output_path = args.next().map(PathBuf::from),
            "--strategies" => {
                if let Some(s) = args.next() {
                    strategies = s
                        .split(',')
                        .filter_map(|s| match s.trim() {
                            "List" => Some(StrategyName::List),
                            "Tree" => Some(StrategyName::Tree),
                            "Auto" => Some(StrategyName::Auto),
                            "Frag" => Some(StrategyName::Frag),
                            _ => None,
                        })
                        .collect();
                }
            }
            "--limit" => {
                if let Some(l) = args.next() {
                    limit = l.parse().ok();
                }
            }
            _ => {}
        }
    }

    CliArgs {
        snapshot_dir: snapshot_dir.unwrap_or_else(|| PathBuf::from("tmp/reports/nfp_cgal_probe/cfr_snapshots")),
        output_path,
        strategies,
        limit,
    }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

#[derive(Debug, Serialize, Deserialize)]
struct SnapshotResult {
    snapshot_file: String,
    seq: u64,
    nfp_poly_count: usize,
    nfp_total_vertices: usize,
    ifp_area: i128,
    strategies: Vec<StrategyTiming>,
    baseline_list_time_ms: f64,
    fastest_strategy: Option<String>,
    fastest_vs_list_speedup: Option<f64>,
}

#[derive(Debug, Serialize, Deserialize)]
struct StrategyTiming {
    strategy: String,
    union_time_ms: f64,
    diff_time_ms: f64,
    total_time_ms: f64,
    component_count: usize,
    equivalent_to_list: bool,
    crashed: bool,
    error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct BenchmarkResults {
    benchmark_version: String,
    total_snapshots: usize,
    strategy_comparison: Vec<SnapshotResult>,
    summary: BenchmarkSummary,
}

#[derive(Debug, Serialize, Deserialize)]
struct BenchmarkSummary {
    strategies_tested: Vec<String>,
    avg_time_by_strategy: std::collections::HashMap<String, f64>,
    avg_speedup_vs_list: std::collections::HashMap<String, f64>,
    total_crashes_by_strategy: std::collections::HashMap<String, usize>,
    recommendation: String,
}

fn main() {
    let args = parse_cli();

    println!("[CFR BENCH] Scanning: {}", args.snapshot_dir.display());
    let paths: Vec<_> = fs::read_dir(&args.snapshot_dir)
        .unwrap()
        .filter_map(|e| e.ok())
        .filter(|e| e.path().extension().map_or(false, |ex| ex == "json"))
        .map(|e| e.path())
        .collect();

    if paths.is_empty() {
        eprintln!("[CFR BENCH] No snapshot JSON files found in {}", args.snapshot_dir.display());
        std::process::exit(1);
    }

    println!("[CFR BENCH] Found {} snapshot files", paths.len());

    let mut results: Vec<SnapshotResult> = Vec::new();

    for (idx, path) in paths.iter().enumerate() {
        if let Some(limit) = args.limit {
            if idx >= limit {
                break;
            }
        }

        print!("  [{}/{}] {} ... ", idx + 1, paths.len(), path.file_name().unwrap().to_string_lossy());
        std::io::stdout().flush().unwrap();

        let (snap, ifp, nfp_polys) = match load_snapshot(path) {
            Some(s) => s,
            None => {
                println!("SKIP (load failed)");
                continue;
            }
        };

        // Run all requested strategies
        let mut timings: Vec<StrategyTiming> = Vec::new();
        let mut list_result: Option<StrategyResult> = None;

        for &strat in &args.strategies {
            let mut result = run_snapshot(&ifp, &nfp_polys, strat);

            // Compare to List output if we have it
            if strat == StrategyName::List {
                list_result = Some(result.clone());
            } else if list_result.is_some() {
                // Re-run with List to get output for comparison
                let list_polys = decode_all_to_polygons(&ifp, &nfp_polys, StrategyName::List);
                let strat_polys = decode_all_to_polygons(&ifp, &nfp_polys, strat);
                result.output_equivalent_to_list = polygons_equivalent(&list_polys[..], &strat_polys[..]);
            }

            timings.push(StrategyTiming {
                strategy: strat.as_str().to_string(),
                union_time_ms: result.union_time_ms,
                diff_time_ms: result.diff_time_ms,
                total_time_ms: result.total_time_ms,
                component_count: result.component_count,
                equivalent_to_list: result.output_equivalent_to_list,
                crashed: result.crashed,
                error: result.error,
            });
        }

        // Compute fastest vs List
        let baseline_list_time = timings
            .iter()
            .find(|t| t.strategy == "List")
            .map(|t| t.total_time_ms)
            .unwrap_or(0.0);

        let fastest = timings
            .iter()
            .filter(|t| !t.crashed)
            .min_by(|a, b| a.total_time_ms.partial_cmp(&b.total_time_ms).unwrap_or(Ordering::Equal));

        let fastest_strategy = fastest.as_ref().map(|f| f.strategy.clone());
        let fastest_vs_list_speedup = fastest
            .as_ref()
            .filter(|f| f.strategy != "List" && baseline_list_time > 0.0)
            .map(|f| baseline_list_time / f.total_time_ms);

        println!(
            "nfp={} verts={} fastest={:.2}ms {}",
            snap.nfp_poly_count,
            snap.nfp_total_vertices,
            fastest.map_or(0.0, |f| f.total_time_ms),
            fastest.as_ref().map_or("?", |f| f.strategy.as_str())
        );

        results.push(SnapshotResult {
            snapshot_file: path.file_name().unwrap().to_string_lossy().to_string(),
            seq: snap.seq,
            nfp_poly_count: snap.nfp_poly_count,
            nfp_total_vertices: snap.nfp_total_vertices,
            ifp_area: snap.ifp_area,
            strategies: timings,
            baseline_list_time_ms: baseline_list_time,
            fastest_strategy,
            fastest_vs_list_speedup,
        });
    }

    // Build summary
    let strategies_tested: Vec<String> = args.strategies.iter().map(|s| s.as_str().to_string()).collect();

    let mut avg_time_by_strategy: std::collections::HashMap<String, f64> = std::collections::HashMap::new();
    let mut total_by_strategy: std::collections::HashMap<String, (f64, usize)> = std::collections::HashMap::new();

    for r in &results {
        for t in &r.strategies {
            if !t.crashed {
                let entry = total_by_strategy.entry(t.strategy.clone()).or_insert((0.0, 0));
                entry.0 += t.total_time_ms;
                entry.1 += 1;
            }
        }
    }

    for (name, (total, count)) in &total_by_strategy {
        if *count > 0 {
            avg_time_by_strategy.insert(name.clone(), total / *count as f64);
        }
    }

    let list_avg = *avg_time_by_strategy.get("List").unwrap_or(&0.0);
    let mut avg_speedup_vs_list: std::collections::HashMap<String, f64> = std::collections::HashMap::new();
    for (name, &avg) in &avg_time_by_strategy {
        if name != "List" && list_avg > 0.0 {
            avg_speedup_vs_list.insert(name.clone(), list_avg / avg);
        }
    }

    let mut total_crashes: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    for r in &results {
        for t in &r.strategies {
            if t.crashed {
                *total_crashes.entry(t.strategy.clone()).or_insert(0) += 1;
            }
        }
    }

    // Recommendation
    let mut recommendation = String::new();
    if let Some((fastest_name, &fastest_avg)) = avg_time_by_strategy.iter().filter(|(n, _)| *n != "List").max_by(|a, b| a.1.partial_cmp(b.1).unwrap_or(Ordering::Equal)) {
        let speedup = list_avg / fastest_avg;
        if speedup > 1.1 {
            let non_equiv = results.iter().filter(|r| {
                r.strategies.iter().any(|t| t.strategy == *fastest_name && !t.equivalent_to_list)
            }).count();
            if non_equiv == 0 {
                recommendation = format!(
                    "RECOMMEND: Strategy::{} is {:.2}x faster than Strategy::List on average with equivalent output. Safe to use.",
                    fastest_name, speedup
                );
            } else {
                recommendation = format!(
                    "CAUTION: Strategy::{} is {:.2}x faster but produced non-equivalent output in {} snapshot(s). Requires validator integration before production use.",
                    fastest_name, speedup, non_equiv
                );
            }
        } else {
            recommendation = format!(
                "NO SIGNIFICANT SPEEDUP: Strategy::{} is only {:.2}x faster than List. Keep Strategy::List.",
                fastest_name, speedup
            );
        }
    } else {
        recommendation = "INCONCLUSIVE: Could not determine recommendation.".to_string();
    }

    let benchmark_results = BenchmarkResults {
        benchmark_version: "1.0.0".to_string(),
        total_snapshots: results.len(),
        strategy_comparison: results,
        summary: BenchmarkSummary {
            strategies_tested,
            avg_time_by_strategy,
            avg_speedup_vs_list,
            total_crashes_by_strategy: total_crashes,
            recommendation,
        },
    };

    let output_path = args.output_path.unwrap_or_else(|| {
        args.snapshot_dir.join("cfr_benchmark_results.json")
    });

    let json = serde_json::to_string_pretty(&benchmark_results).unwrap();
    fs::write(&output_path, &json).unwrap();
    println!("\n[CFR BENCH] Results written: {}", output_path.display());
    println!("[CFR BENCH] Recommendation: {}", benchmark_results.summary.recommendation);
}

// Helper: decode all outputs for a given strategy (reused for comparison)
fn decode_all_to_polygons(ifp: &Polygon64, nfp_polys: &[Polygon64], strat: StrategyName) -> Vec<Polygon64> {
    let mut all_polys: Vec<&Polygon64> = Vec::with_capacity(1 + nfp_polys.len());
    all_polys.push(ifp);
    all_polys.extend(nfp_polys.iter());

    let bounds = match OverlayBounds::from_polygons(&all_polys) {
        Some(b) => b,
        None => return Vec::new(),
    };

    let ifp_shape = match encode_polygon(ifp, bounds) {
        Some(s) => s,
        None => return Vec::new(),
    };

    let nfp_shapes: Vec<IntShape> = nfp_polys
        .iter()
        .filter_map(|poly| encode_polygon(poly, bounds))
        .collect();

    let union_shapes = run_overlay(&nfp_shapes, &[], OverlayRule::Union, strat.to_strategy());
    let diff_shapes = run_overlay(&[ifp_shape], &union_shapes, OverlayRule::Difference, strat.to_strategy());

    diff_shapes
        .iter()
        .filter_map(|shape| decode_shape(shape, bounds))
        .collect()
}
