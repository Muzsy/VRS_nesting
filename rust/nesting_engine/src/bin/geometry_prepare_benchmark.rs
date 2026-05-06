use std::fs;
use std::path::PathBuf;

use nesting_engine::geometry::{
    cleanup::{run_cleanup_pipeline, CleanupResult},
    scale::mm_to_i64,
    simplify::{topology_preserving_rdp, SimplifyResult},
    types::{Point64, Polygon64},
};
use serde::{Deserialize, Serialize};

const DEFAULT_FIXTURE: &str = "tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json";
const DEFAULT_RDP_EPSILON_MM: f64 = 0.1;
const DEFAULT_COLLINEAR_THRESHOLD_DEG: f64 = 0.5;

#[derive(Debug)]
struct CliArgs {
    fixture: PathBuf,
    rdp_epsilon_mm: f64,
    collinear_threshold_deg: f64,
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
    part_id: String,
    points_mm: Vec<[f64; 2]>,
    #[serde(default)]
    holes_mm: Vec<Vec<[f64; 2]>>,
}

#[derive(Debug, Serialize)]
struct BenchmarkOutput {
    input_fixture: String,
    rdp_epsilon_mm: f64,
    collinear_threshold_deg: f64,
    part_a: PartOutput,
    part_b: PartOutput,
    pair_fragment_count_estimate: PairFragmentEstimate,
}

#[derive(Debug, Serialize)]
struct PartOutput {
    part_id: String,
    cleanup: CleanupMetrics,
    simplify: SimplifyMetrics,
}

#[derive(Debug, Serialize)]
struct CleanupMetrics {
    vertex_count_before: usize,
    vertex_count_after: usize,
    null_edges_removed: usize,
    duplicate_vertices_removed: usize,
    collinear_merged: usize,
    orientation_fixed: bool,
}

#[derive(Debug, Serialize)]
struct SimplifyMetrics {
    vertex_count_before: usize,
    vertex_count_after: usize,
    reflex_vertex_count_before: usize,
    reflex_vertex_count_after: usize,
    area_delta_mm2: f64,
    bbox_delta_mm: f64,
    max_deviation_mm: f64,
    topology_changed: bool,
    simplification_ratio: f64,
}

#[derive(Debug, Serialize)]
struct PairFragmentEstimate {
    before_cleanup: usize,
    after_cleanup: usize,
    after_simplify: usize,
    reduction_ratio: f64,
}

fn parse_args(raw: &[String]) -> Result<CliArgs, String> {
    let mut fixture = PathBuf::from(DEFAULT_FIXTURE);
    let mut rdp_epsilon_mm = DEFAULT_RDP_EPSILON_MM;
    let mut collinear_threshold_deg = DEFAULT_COLLINEAR_THRESHOLD_DEG;
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
        if let Some(value) = arg.strip_prefix("--fixture=") {
            fixture = PathBuf::from(value);
            idx += 1;
            continue;
        }
        if arg == "--rdp-epsilon" {
            idx += 1;
            if idx >= raw.len() {
                return Err("missing value for --rdp-epsilon".to_string());
            }
            rdp_epsilon_mm = parse_f64("--rdp-epsilon", &raw[idx])?;
            idx += 1;
            continue;
        }
        if let Some(value) = arg.strip_prefix("--rdp-epsilon=") {
            rdp_epsilon_mm = parse_f64("--rdp-epsilon", value)?;
            idx += 1;
            continue;
        }
        if arg == "--collinear-threshold" {
            idx += 1;
            if idx >= raw.len() {
                return Err("missing value for --collinear-threshold".to_string());
            }
            collinear_threshold_deg = parse_f64("--collinear-threshold", &raw[idx])?;
            idx += 1;
            continue;
        }
        if let Some(value) = arg.strip_prefix("--collinear-threshold=") {
            collinear_threshold_deg = parse_f64("--collinear-threshold", value)?;
            idx += 1;
            continue;
        }

        return Err(format!("unknown argument: {arg}"));
    }

    Ok(CliArgs {
        fixture,
        rdp_epsilon_mm,
        collinear_threshold_deg,
        output_json,
    })
}

fn parse_f64(flag: &str, value: &str) -> Result<f64, String> {
    value
        .trim()
        .parse::<f64>()
        .map_err(|_| format!("invalid value for {flag}: '{value}'"))
}

fn print_help() {
    println!("geometry_prepare_benchmark");
    println!("  --fixture <path>          (default: {DEFAULT_FIXTURE})");
    println!("  --rdp-epsilon <mm>        (default: {DEFAULT_RDP_EPSILON_MM})");
    println!("  --collinear-threshold <°> (default: {DEFAULT_COLLINEAR_THRESHOLD_DEG})");
    println!("  --output-json");
}

fn fixture_part_to_polygon(part: &FixturePart) -> Result<Polygon64, String> {
    if part.points_mm.len() < 3 {
        return Err(format!(
            "fixture part '{}' has insufficient outer points: {}",
            part.part_id,
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

fn cleanup_to_metrics(result: &CleanupResult) -> CleanupMetrics {
    CleanupMetrics {
        vertex_count_before: result.vertex_count_before,
        vertex_count_after: result.vertex_count_after,
        null_edges_removed: result.null_edges_removed,
        duplicate_vertices_removed: result.duplicate_vertices_removed,
        collinear_merged: result.collinear_merged,
        orientation_fixed: result.orientation_fixed,
    }
}

fn simplify_to_metrics(result: &SimplifyResult) -> SimplifyMetrics {
    SimplifyMetrics {
        vertex_count_before: result.vertex_count_before,
        vertex_count_after: result.vertex_count_after,
        reflex_vertex_count_before: result.reflex_vertex_count_before,
        reflex_vertex_count_after: result.reflex_vertex_count_after,
        area_delta_mm2: result.area_delta_mm2,
        bbox_delta_mm: result.bbox_delta_mm,
        max_deviation_mm: result.max_deviation_mm,
        topology_changed: result.topology_changed,
        simplification_ratio: result.simplification_ratio,
    }
}

fn process_part(
    part: &FixturePart,
    collinear_threshold_deg: f64,
    rdp_epsilon_mm: f64,
) -> Result<(PartOutput, usize, usize, usize), String> {
    let polygon = fixture_part_to_polygon(part)?;
    let before_vc = polygon.outer.len();

    let cleanup = run_cleanup_pipeline(&polygon, collinear_threshold_deg)
        .map_err(|err| format!("cleanup failed for {}: {err:?}", part.part_id))?;

    let simplify = topology_preserving_rdp(&cleanup.polygon, rdp_epsilon_mm)
        .map_err(|err| format!("simplify failed for {}: {err:?}", part.part_id))?;

    let output = PartOutput {
        part_id: part.part_id.clone(),
        cleanup: cleanup_to_metrics(&cleanup),
        simplify: simplify_to_metrics(&simplify),
    };

    Ok((
        output,
        before_vc,
        cleanup.vertex_count_after,
        simplify.vertex_count_after,
    ))
}

fn run(args: CliArgs) -> Result<(), String> {
    let raw = fs::read_to_string(&args.fixture)
        .map_err(|err| format!("failed to read fixture '{}': {err}", args.fixture.display()))?;
    let fixture: PairFixture = serde_json::from_str(&raw)
        .map_err(|err| format!("invalid fixture JSON '{}': {err}", args.fixture.display()))?;

    let (part_a, a_before, a_after_cleanup, a_after_simplify) = process_part(
        &fixture.part_a,
        args.collinear_threshold_deg,
        args.rdp_epsilon_mm,
    )?;
    let (part_b, b_before, b_after_cleanup, b_after_simplify) = process_part(
        &fixture.part_b,
        args.collinear_threshold_deg,
        args.rdp_epsilon_mm,
    )?;

    let before_cleanup = a_before.saturating_mul(b_before);
    let after_cleanup = a_after_cleanup.saturating_mul(b_after_cleanup);
    let after_simplify = a_after_simplify.saturating_mul(b_after_simplify);

    let output = BenchmarkOutput {
        input_fixture: fixture.pair_id,
        rdp_epsilon_mm: args.rdp_epsilon_mm,
        collinear_threshold_deg: args.collinear_threshold_deg,
        part_a,
        part_b,
        pair_fragment_count_estimate: PairFragmentEstimate {
            before_cleanup,
            after_cleanup,
            after_simplify,
            reduction_ratio: if before_cleanup == 0 {
                1.0
            } else {
                after_simplify as f64 / before_cleanup as f64
            },
        },
    };

    if args.output_json {
        let s = serde_json::to_string(&output)
            .map_err(|err| format!("failed to serialize output JSON: {err}"))?;
        println!("{s}");
    } else {
        println!(
            "fixture={} A: {}->{} B: {}->{} ratio={:.4}",
            output.input_fixture,
            output.part_a.cleanup.vertex_count_before,
            output.part_a.simplify.vertex_count_after,
            output.part_b.cleanup.vertex_count_before,
            output.part_b.simplify.vertex_count_after,
            output.pair_fragment_count_estimate.reduction_ratio,
        );
    }

    Ok(())
}

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let args = match parse_args(&raw) {
        Ok(a) => a,
        Err(err) => {
            eprintln!("geometry_prepare_benchmark: {err}");
            print_help();
            std::process::exit(1);
        }
    };

    if let Err(err) = run(args) {
        eprintln!("geometry_prepare_benchmark: {err}");
        std::process::exit(1);
    }
}
