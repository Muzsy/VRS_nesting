use std::fs;
use std::path::PathBuf;
use std::sync::mpsc;
use std::thread;
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use nesting_engine::geometry::{
    scale::mm_to_i64,
    types::{is_convex, Point64, Polygon64},
};
use nesting_engine::nfp::{
    concave::compute_concave_nfp_default, convex::compute_convex_nfp, NfpError,
};
use serde::{Deserialize, Serialize};

const DEFAULT_FIXTURE: &str = "tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json";
const DEFAULT_TIMEOUT_MS: u64 = 5000;

#[derive(Debug)]
struct CliArgs {
    fixture: PathBuf,
    timeout_ms: u64,
    part_a_only: bool,
    part_b_only: bool,
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
    benchmark_version: String,
    fixture: String,
    pair_a_id: String,
    pair_b_id: String,
    timestamp_utc: String,
    decomposition: DecompositionMetrics,
    nfp_computation: NfpComputationMetrics,
    verdict: String,
}

#[derive(Debug, Serialize)]
struct DecompositionMetrics {
    fragment_count_a: usize,
    fragment_count_b: usize,
    pair_count: usize,
    decomposition_time_ms: u128,
    error: Option<String>,
}

#[derive(Debug, Serialize)]
struct NfpComputationMetrics {
    fragment_union_time_ms: u128,
    cleanup_time_ms: u128,
    total_time_ms: u128,
    output_vertex_count: usize,
    output_loop_count: usize,
    timed_out: bool,
    error: Option<String>,
    nfp_error_kind: Option<String>,
}

#[derive(Debug)]
struct ComputeOutput {
    polygon: Polygon64,
    elapsed_ms: u128,
}

fn parse_args(raw: &[String]) -> Result<CliArgs, String> {
    let mut fixture = PathBuf::from(DEFAULT_FIXTURE);
    let mut timeout_ms = DEFAULT_TIMEOUT_MS;
    let mut part_a_only = false;
    let mut part_b_only = false;
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
        if arg == "--part-a-only" {
            part_a_only = true;
            idx += 1;
            continue;
        }
        if arg == "--part-b-only" {
            part_b_only = true;
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
        if arg == "--timeout-ms" {
            idx += 1;
            if idx >= raw.len() {
                return Err("missing value for --timeout-ms".to_string());
            }
            timeout_ms = parse_u64("--timeout-ms", &raw[idx])?;
            idx += 1;
            continue;
        }
        if let Some(value) = arg.strip_prefix("--timeout-ms=") {
            timeout_ms = parse_u64("--timeout-ms", value)?;
            idx += 1;
            continue;
        }

        return Err(format!("unknown argument: {arg}"));
    }

    if part_a_only && part_b_only {
        return Err("--part-a-only and --part-b-only cannot be used together".to_string());
    }

    Ok(CliArgs {
        fixture,
        timeout_ms,
        part_a_only,
        part_b_only,
        output_json,
    })
}

fn parse_u64(flag: &str, value: &str) -> Result<u64, String> {
    value
        .trim()
        .parse::<u64>()
        .map_err(|_| format!("invalid value for {flag}: '{value}'"))
}

fn print_help() {
    println!("nfp_pair_benchmark");
    println!("  --fixture <path>     (default: {DEFAULT_FIXTURE})");
    println!("  --timeout-ms <N>     (default: {DEFAULT_TIMEOUT_MS})");
    println!("  --part-a-only");
    println!("  --part-b-only");
    println!("  --output-json        (default output is human-readable)");
}

fn print_human_summary(output: &BenchmarkOutput) {
    println!("NFP pair benchmark");
    println!("  fixture: {}", output.fixture);
    println!("  pair: {} x {}", output.pair_a_id, output.pair_b_id);
    println!(
        "  fragments: A={} B={} pair_count={}",
        output.decomposition.fragment_count_a,
        output.decomposition.fragment_count_b,
        output.decomposition.pair_count
    );
    println!(
        "  verdict: {} (time_ms={})",
        output.verdict, output.nfp_computation.total_time_ms
    );
    if output.nfp_computation.timed_out {
        println!("  timeout: true");
    }
    if let Some(kind) = &output.nfp_computation.nfp_error_kind {
        println!("  nfp_error_kind: {kind}");
    }
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

fn nfp_error_kind(err: NfpError) -> String {
    match err {
        NfpError::EmptyPolygon => "EmptyPolygon",
        NfpError::NotConvex => "NotConvex",
        NfpError::NotSimpleOutput => "NotSimpleOutput",
        NfpError::OrbitLoopDetected => "OrbitLoopDetected",
        NfpError::OrbitDeadEnd => "OrbitDeadEnd",
        NfpError::OrbitMaxStepsReached => "OrbitMaxStepsReached",
        NfpError::OrbitNotClosed => "OrbitNotClosed",
        NfpError::DecompositionFailed => "DecompositionFailed",
    }
    .to_string()
}

fn estimate_fragment_count(poly: &Polygon64) -> usize {
    if is_convex(&poly.outer) {
        1
    } else {
        poly.outer.len().saturating_sub(2).max(1)
    }
}

fn run_nfp_compute_with_timeout(
    a: Polygon64,
    b: Polygon64,
    timeout_ms: u64,
) -> Result<Result<ComputeOutput, NfpError>, ()> {
    let (tx, rx) = mpsc::channel();
    let _handle = thread::spawn(move || {
        let started = Instant::now();
        let result = if !is_convex(&a.outer) || !is_convex(&b.outer) {
            compute_concave_nfp_default(&a, &b)
        } else {
            compute_convex_nfp(&a, &b)
        };

        let mapped = result.map(|polygon| ComputeOutput {
            polygon,
            elapsed_ms: started.elapsed().as_millis(),
        });
        let _ = tx.send(mapped);
    });

    match rx.recv_timeout(Duration::from_millis(timeout_ms)) {
        Ok(result) => Ok(result),
        Err(mpsc::RecvTimeoutError::Timeout) => Err(()),
        Err(mpsc::RecvTimeoutError::Disconnected) => Ok(Err(NfpError::DecompositionFailed)),
    }
}

fn now_utc_string() -> String {
    match SystemTime::now().duration_since(UNIX_EPOCH) {
        Ok(dur) => format!("{}", dur.as_secs()),
        Err(_) => "0".to_string(),
    }
}

fn run(args: CliArgs) -> Result<BenchmarkOutput, String> {
    let raw = fs::read_to_string(&args.fixture)
        .map_err(|err| format!("failed to read fixture '{}': {err}", args.fixture.display()))?;
    let fixture: PairFixture = serde_json::from_str(&raw)
        .map_err(|err| format!("invalid fixture JSON '{}': {err}", args.fixture.display()))?;

    let poly_a = fixture_part_to_polygon(&fixture.part_a)?;
    let poly_b = fixture_part_to_polygon(&fixture.part_b)?;

    let decomposition_started = Instant::now();
    let fragment_count_a = estimate_fragment_count(&poly_a);
    let fragment_count_b = estimate_fragment_count(&poly_b);
    let pair_count = fragment_count_a.saturating_mul(fragment_count_b);
    let decomposition_time_ms = decomposition_started.elapsed().as_millis();

    let decomposition = DecompositionMetrics {
        fragment_count_a,
        fragment_count_b,
        pair_count,
        decomposition_time_ms,
        error: None,
    };

    let (bench_a, bench_b) = if args.part_a_only {
        (poly_a.clone(), poly_a.clone())
    } else if args.part_b_only {
        (poly_b.clone(), poly_b.clone())
    } else {
        (poly_a.clone(), poly_b.clone())
    };

    let total_started = Instant::now();
    let computed = run_nfp_compute_with_timeout(bench_a, bench_b, args.timeout_ms);

    let mut nfp = NfpComputationMetrics {
        fragment_union_time_ms: 0,
        cleanup_time_ms: 0,
        total_time_ms: total_started.elapsed().as_millis(),
        output_vertex_count: 0,
        output_loop_count: 0,
        timed_out: false,
        error: None,
        nfp_error_kind: None,
    };

    let verdict = match computed {
        Err(()) => {
            nfp.timed_out = true;
            nfp.total_time_ms = args.timeout_ms as u128;
            nfp.error = Some(format!("timeout after {}ms", args.timeout_ms));
            "TIMEOUT".to_string()
        }
        Ok(Err(err)) => {
            let kind = nfp_error_kind(err);
            nfp.error = Some(format!("nfp error: {kind}"));
            nfp.nfp_error_kind = Some(kind.clone());
            nfp.total_time_ms = total_started.elapsed().as_millis();
            if err == NfpError::DecompositionFailed {
                "DECOMPOSITION_FAILED".to_string()
            } else {
                "ERROR".to_string()
            }
        }
        Ok(Ok(out)) => {
            nfp.total_time_ms = out.elapsed_ms;
            nfp.fragment_union_time_ms = out.elapsed_ms;
            nfp.output_vertex_count = out.polygon.outer.len();
            nfp.output_loop_count = 1 + out.polygon.holes.len();
            "SUCCESS".to_string()
        }
    };

    Ok(BenchmarkOutput {
        benchmark_version: "nfp_pair_benchmark_v1".to_string(),
        fixture: fixture.pair_id,
        pair_a_id: fixture.part_a.part_id,
        pair_b_id: fixture.part_b.part_id,
        timestamp_utc: now_utc_string(),
        decomposition,
        nfp_computation: nfp,
        verdict,
    })
}

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let args = match parse_args(&raw) {
        Ok(v) => v,
        Err(err) => {
            eprintln!("nfp_pair_benchmark: {err}");
            print_help();
            std::process::exit(1);
        }
    };

    let output_json = args.output_json;
    match run(args) {
        Ok(output) => {
            if output_json {
                if let Ok(s) = serde_json::to_string(&output) {
                    println!("{s}");
                } else {
                    eprintln!("nfp_pair_benchmark: failed to serialize output");
                    std::process::exit(1);
                }
            } else {
                print_human_summary(&output);
            }
        }
        Err(err) => {
            eprintln!("nfp_pair_benchmark: {err}");
            std::process::exit(1);
        }
    }
}
