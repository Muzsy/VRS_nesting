use std::fs;
use std::path::{Path, PathBuf};
use std::sync::mpsc;
use std::thread;
use std::time::{Duration, Instant};

use nesting_engine::geometry::{
    scale::mm_to_i64,
    types::{Point64, Polygon64},
};
use nesting_engine::nfp::reduced_convolution::{
    compute_rc_nfp, RcNfpError, ReducedConvolutionOptions, RC_KERNEL_VERSION,
};
use serde::{Deserialize, Serialize};

const DEFAULT_FIXTURE: &str = "tests/fixtures/nesting_engine/nfp_pairs/lv8_pair_01.json";
const DEFAULT_TIMEOUT_MS: u64 = 10_000;

#[derive(Debug)]
struct CliArgs {
    fixture: PathBuf,
    timeout_ms: u64,
    compare_baseline: bool,
    output_json: bool,
}

#[derive(Debug, Deserialize)]
struct PairFixture {
    pair_id: String,
    part_a: FixturePart,
    part_b: FixturePart,
    #[serde(default)]
    baseline_metrics: Option<BaselineMetrics>,
}

#[derive(Debug, Deserialize)]
struct FixturePart {
    part_id: String,
    points_mm: Vec<[f64; 2]>,
    #[serde(default)]
    holes_mm: Vec<Vec<[f64; 2]>>,
}

#[derive(Debug, Deserialize)]
struct BaselineMetrics {
    #[serde(default)]
    fragment_count_a: Option<usize>,
    #[serde(default)]
    fragment_count_b: Option<usize>,
    #[serde(default)]
    expected_pair_count: Option<usize>,
    #[serde(default)]
    verdict: Option<String>,
}

#[derive(Debug, Serialize)]
struct BenchmarkOutput {
    benchmark_version: &'static str,
    fixture: String,
    pair_a_id: String,
    pair_b_id: String,
    kernel: &'static str,
    rc_result: RcResultOutput,
    comparison_to_baseline: ComparisonToBaseline,
    verdict: String,
}

#[derive(Debug, Serialize)]
struct RcResultOutput {
    success: bool,
    error: Option<String>,
    raw_vertex_count: usize,
    computation_time_ms: u64,
    kernel_version: &'static str,
    polygon: Option<Vec<[i64; 2]>>,
}

#[derive(Debug, Serialize)]
struct ComparisonToBaseline {
    baseline_verdict: Option<String>,
    baseline_fragment_count_a: Option<usize>,
    baseline_fragment_count_b: Option<usize>,
    baseline_pair_count: Option<usize>,
    rc_avoids_fragment_explosion: Option<bool>,
    time_ratio: Option<f64>,
}

fn parse_args(raw: &[String]) -> Result<CliArgs, String> {
    let mut fixture = PathBuf::from(DEFAULT_FIXTURE);
    let mut timeout_ms = DEFAULT_TIMEOUT_MS;
    let mut compare_baseline = false;
    let mut output_json = false;

    let mut idx = 0usize;
    while idx < raw.len() {
        let arg = &raw[idx];
        if arg == "--help" || arg == "-h" {
            print_help();
            std::process::exit(0);
        }
        if arg == "--compare-baseline" {
            compare_baseline = true;
            idx += 1;
            continue;
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

    Ok(CliArgs {
        fixture,
        timeout_ms,
        compare_baseline,
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
    println!("nfp_rc_prototype_benchmark");
    println!("  --fixture <path>       (default: {DEFAULT_FIXTURE})");
    println!("  --timeout-ms <N>       (default: {DEFAULT_TIMEOUT_MS})");
    println!("  --compare-baseline");
    println!("  --output-json          (default output is human-readable)");
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

fn rc_error_kind(err: &RcNfpError) -> String {
    match err {
        RcNfpError::InputTooComplex { .. } => "InputTooComplex".to_string(),
        RcNfpError::EmptyInput => "EmptyInput".to_string(),
        RcNfpError::NotImplemented => "NotImplemented".to_string(),
        RcNfpError::ComputationFailed(_) => "ComputationFailed".to_string(),
        RcNfpError::OutputExceedsCap { .. } => "OutputExceedsCap".to_string(),
        RcNfpError::CleanupFailed(_) => "CleanupFailed".to_string(),
    }
}

fn rc_error_message(err: &RcNfpError) -> String {
    match err {
        RcNfpError::InputTooComplex {
            vertex_count,
            limit,
        } => format!("InputTooComplex(vertex_count={vertex_count}, limit={limit})"),
        RcNfpError::EmptyInput => "EmptyInput".to_string(),
        RcNfpError::NotImplemented => "NotImplemented".to_string(),
        RcNfpError::ComputationFailed(msg) => format!("ComputationFailed({msg})"),
        RcNfpError::OutputExceedsCap { vertex_count, cap } => {
            format!("OutputExceedsCap(vertex_count={vertex_count}, cap={cap})")
        }
        RcNfpError::CleanupFailed(msg) => format!("CleanupFailed({msg})"),
    }
}

fn read_fixture_with_fallback(path: &Path) -> Result<String, String> {
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

fn compute_with_timeout(
    a: Polygon64,
    b: Polygon64,
    timeout_ms: u64,
) -> Result<nesting_engine::nfp::reduced_convolution::RcNfpResult, ()> {
    let (tx, rx) = mpsc::channel();

    let _handle = thread::spawn(move || {
        let options = ReducedConvolutionOptions::default();
        let out = compute_rc_nfp(&a, &b, &options);
        let _ = tx.send(out);
    });

    match rx.recv_timeout(Duration::from_millis(timeout_ms)) {
        Ok(result) => Ok(result),
        Err(mpsc::RecvTimeoutError::Timeout) => Err(()),
        Err(mpsc::RecvTimeoutError::Disconnected) => Err(()),
    }
}

fn run(args: CliArgs) -> Result<BenchmarkOutput, String> {
    let raw = read_fixture_with_fallback(&args.fixture)?;
    let fixture: PairFixture = serde_json::from_str(&raw)
        .map_err(|err| format!("invalid fixture JSON '{}': {err}", args.fixture.display()))?;

    let poly_a = fixture_part_to_polygon(&fixture.part_a)?;
    let poly_b = fixture_part_to_polygon(&fixture.part_b)?;

    let started = Instant::now();
    let rc = compute_with_timeout(poly_a, poly_b, args.timeout_ms);

    let (rc_result, verdict) = match rc {
        Err(()) => (
            RcResultOutput {
                success: false,
                error: Some(format!("timeout after {}ms", args.timeout_ms)),
                raw_vertex_count: 0,
                computation_time_ms: args.timeout_ms,
                kernel_version: RC_KERNEL_VERSION,
                polygon: None,
            },
            "TIMEOUT".to_string(),
        ),
        Ok(out) => {
            if let Some(err) = &out.error {
                let kind = rc_error_kind(err);
                let message = rc_error_message(err);
                (
                    RcResultOutput {
                        success: false,
                        error: Some(message),
                        raw_vertex_count: out.raw_vertex_count,
                        computation_time_ms: out.computation_time_ms,
                        kernel_version: out.kernel_version,
                        polygon: None,
                    },
                    if kind == "NotImplemented" {
                        "NOT_IMPLEMENTED".to_string()
                    } else {
                        "ERROR".to_string()
                    },
                )
            } else {
                let polygon = out.polygon.as_ref().map(|poly| {
                    poly.outer
                        .iter()
                        .map(|p| [p.x, p.y])
                        .collect::<Vec<[i64; 2]>>()
                });
                (
                    RcResultOutput {
                        success: true,
                        error: None,
                        raw_vertex_count: out.raw_vertex_count,
                        computation_time_ms: out.computation_time_ms,
                        kernel_version: out.kernel_version,
                        polygon,
                    },
                    "SUCCESS".to_string(),
                )
            }
        }
    };

    let baseline = fixture.baseline_metrics;
    let (baseline_verdict, baseline_fragment_count_a, baseline_fragment_count_b, baseline_pair_count) =
        if let Some(bm) = baseline {
            (
                bm.verdict,
                bm.fragment_count_a,
                bm.fragment_count_b,
                bm.expected_pair_count,
            )
        } else {
            (None, None, None, None)
        };

    let comparison_to_baseline = if args.compare_baseline {
        ComparisonToBaseline {
            baseline_verdict,
            baseline_fragment_count_a,
            baseline_fragment_count_b,
            baseline_pair_count,
            rc_avoids_fragment_explosion: baseline_pair_count
                .map(|pairs| rc_result.raw_vertex_count > 0 && rc_result.raw_vertex_count < pairs),
            time_ratio: if rc_result.computation_time_ms > 0 {
                Some(started.elapsed().as_millis() as f64 / rc_result.computation_time_ms as f64)
            } else {
                None
            },
        }
    } else {
        ComparisonToBaseline {
            baseline_verdict,
            baseline_fragment_count_a,
            baseline_fragment_count_b,
            baseline_pair_count,
            rc_avoids_fragment_explosion: None,
            time_ratio: None,
        }
    };

    Ok(BenchmarkOutput {
        benchmark_version: "nfp_rc_prototype_v1",
        fixture: fixture.pair_id,
        pair_a_id: fixture.part_a.part_id,
        pair_b_id: fixture.part_b.part_id,
        kernel: RC_KERNEL_VERSION,
        rc_result,
        comparison_to_baseline,
        verdict,
    })
}

fn print_human_summary(output: &BenchmarkOutput) {
    println!("RC prototype benchmark");
    println!("  fixture: {}", output.fixture);
    println!("  pair: {} x {}", output.pair_a_id, output.pair_b_id);
    println!("  kernel: {}", output.kernel);
    println!(
        "  verdict: {} (raw_vc={}, time_ms={})",
        output.verdict, output.rc_result.raw_vertex_count, output.rc_result.computation_time_ms
    );
    if let Some(err) = &output.rc_result.error {
        println!("  error: {err}");
    }
}

fn main() {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let args = match parse_args(&raw) {
        Ok(v) => v,
        Err(err) => {
            eprintln!("nfp_rc_prototype_benchmark: {err}");
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
                    eprintln!("nfp_rc_prototype_benchmark: failed to serialize output");
                    std::process::exit(1);
                }
            } else {
                print_human_summary(&output);
            }
        }
        Err(err) => {
            eprintln!("nfp_rc_prototype_benchmark: {err}");
            std::process::exit(1);
        }
    }
}
