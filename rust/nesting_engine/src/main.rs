mod export;
mod feasibility;
mod geometry;
mod io;
mod multi_bin;
mod placement;

use std::io::{self as stdio, BufReader, BufWriter, Write};
use std::time::Instant;

use serde::Deserialize;

use crate::{
    export::build_output_v2,
    geometry::{scale::mm_to_i64, types::{Point64, Polygon64}},
    geometry::pipeline::run_inflate_pipeline,
    io::pipeline_io::{PartRequest, PipelineRequest},
    multi_bin::{MultiSheetResult, greedy_multi_sheet},
    placement::blf::{InflatedPartSpec, UnplacedItem, bbox_area},
};

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.iter().any(|a| a == "--version") {
        println!("nesting_engine {}", env!("CARGO_PKG_VERSION"));
        return;
    }

    if args.iter().any(|a| a == "--help") {
        println!("Usage: nesting_engine [--version] [--help] [inflate-parts] [nest]");
        println!("NFP-based nesting engine (scaffold)");
        return;
    }

    if args.len() >= 2 && args[1] == "inflate-parts" {
        if let Err(err) = run_inflate_parts() {
            eprintln!("nesting_engine inflate-parts: {err}");
            std::process::exit(1);
        }
        return;
    }
    if args.len() >= 2 && args[1] == "nest" {
        if let Err(err) = run_nest() {
            eprintln!("nesting_engine nest: {err}");
            std::process::exit(1);
        }
        return;
    }

    eprintln!("nesting_engine: no input");
    std::process::exit(1);
}

fn run_inflate_parts() -> Result<(), String> {
    let stdin = stdio::stdin();
    let reader = BufReader::new(stdin.lock());
    let req: PipelineRequest = serde_json::from_reader(reader)
        .map_err(|err| format!("invalid PipelineRequest JSON on stdin: {err}"))?;

    let resp = run_inflate_pipeline(req);

    let stdout = stdio::stdout();
    let mut writer = BufWriter::new(stdout.lock());
    serde_json::to_writer(&mut writer, &resp)
        .map_err(|err| format!("failed to write PipelineResponse JSON: {err}"))?;
    writer
        .write_all(b"\n")
        .map_err(|err| format!("failed to finalize output: {err}"))?;
    writer
        .flush()
        .map_err(|err| format!("failed to flush output: {err}"))?;
    Ok(())
}

#[derive(Debug, Clone, Deserialize)]
struct NestInput {
    version: String,
    seed: u64,
    time_limit_sec: u64,
    sheet: NestSheet,
    parts: Vec<NestInputPart>,
}

#[derive(Debug, Clone, Deserialize)]
struct NestSheet {
    width_mm: f64,
    height_mm: f64,
    kerf_mm: f64,
    margin_mm: f64,
}

#[derive(Debug, Clone, Deserialize)]
struct NestInputPart {
    id: String,
    quantity: usize,
    allowed_rotations_deg: Vec<i32>,
    outer_points_mm: Vec<[f64; 2]>,
    holes_points_mm: Vec<Vec<[f64; 2]>>,
}

fn run_nest() -> Result<(), String> {
    let started = Instant::now();
    let stdin = stdio::stdin();
    let reader = BufReader::new(stdin.lock());
    let input: NestInput = serde_json::from_reader(reader)
        .map_err(|err| format!("invalid io_contract_v2 input JSON on stdin: {err}"))?;

    if input.version != "nesting_engine_v2" {
        return Err(format!(
            "unsupported input version '{}', expected 'nesting_engine_v2'",
            input.version
        ));
    }

    let pipe_req = PipelineRequest {
        version: "pipeline_v1".to_string(),
        kerf_mm: input.sheet.kerf_mm,
        margin_mm: input.sheet.margin_mm,
        parts: input
            .parts
            .iter()
            .map(|p| PartRequest {
                id: p.id.clone(),
                outer_points_mm: p.outer_points_mm.clone(),
                holes_points_mm: p.holes_points_mm.clone(),
            })
            .collect(),
        stocks: Vec::new(),
    };
    let pipe_resp = run_inflate_pipeline(pipe_req);

    let mut specs: Vec<InflatedPartSpec> = Vec::new();
    let mut forced_unplaced: Vec<UnplacedItem> = Vec::new();

    for part in &input.parts {
        let resp = pipe_resp
            .parts
            .iter()
            .find(|r| r.id == part.id)
            .ok_or_else(|| format!("missing inflate response for part '{}'", part.id))?;

        if (resp.status == "ok" || resp.status == "hole_collapsed")
            && !resp.inflated_outer_points_mm.is_empty()
        {
            let holes = if resp.status == "hole_collapsed" {
                Vec::new()
            } else {
                resp.inflated_holes_points_mm
                    .iter()
                    .map(|hole| {
                        hole.iter()
                            .map(|p| Point64 {
                                x: mm_to_i64(p[0]),
                                y: mm_to_i64(p[1]),
                            })
                            .collect()
                    })
                    .collect()
            };
            let inflated = Polygon64 {
                outer: resp
                    .inflated_outer_points_mm
                    .iter()
                    .map(|p| Point64 {
                        x: mm_to_i64(p[0]),
                        y: mm_to_i64(p[1]),
                    })
                    .collect(),
                holes,
            };
            let nominal_outer: Vec<Point64> = part
                .outer_points_mm
                .iter()
                .map(|p| Point64 {
                    x: mm_to_i64(p[0]),
                    y: mm_to_i64(p[1]),
                })
                .collect();
            specs.push(InflatedPartSpec {
                id: part.id.clone(),
                quantity: part.quantity,
                allowed_rotations_deg: part.allowed_rotations_deg.clone(),
                inflated_polygon: inflated,
                nominal_bbox_area: bbox_area(&nominal_outer),
            });
        } else {
            for instance in 0..part.quantity {
                forced_unplaced.push(UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: "PART_NEVER_FITS_SHEET".to_string(),
                });
            }
        }
    }

    let min_x_mm = input.sheet.margin_mm;
    let min_y_mm = input.sheet.margin_mm;
    let max_x_mm = (input.sheet.width_mm - input.sheet.margin_mm).max(min_x_mm);
    let max_y_mm = (input.sheet.height_mm - input.sheet.margin_mm).max(min_y_mm);
    let bin = Polygon64 {
        outer: vec![
            Point64 {
                x: mm_to_i64(min_x_mm),
                y: mm_to_i64(min_y_mm),
            },
            Point64 {
                x: mm_to_i64(max_x_mm),
                y: mm_to_i64(min_y_mm),
            },
            Point64 {
                x: mm_to_i64(max_x_mm),
                y: mm_to_i64(max_y_mm),
            },
            Point64 {
                x: mm_to_i64(min_x_mm),
                y: mm_to_i64(max_y_mm),
            },
        ],
        holes: Vec::new(),
    };

    let mut result: MultiSheetResult = greedy_multi_sheet(&specs, &bin, 1.0, input.time_limit_sec);
    result.unplaced.extend(forced_unplaced);
    result
        .unplaced
        .sort_by(|a, b| a.part_id.cmp(&b.part_id).then(a.instance.cmp(&b.instance)));

    let utilization_pct = compute_utilization_pct(&input, &result);
    let elapsed = started.elapsed().as_secs_f64();
    let out = build_output_v2(input.seed, elapsed, utilization_pct, &result);

    let stdout = stdio::stdout();
    let mut writer = BufWriter::new(stdout.lock());
    serde_json::to_writer(&mut writer, &out)
        .map_err(|err| format!("failed to write nest output JSON: {err}"))?;
    writer
        .write_all(b"\n")
        .map_err(|err| format!("failed to finalize nest output: {err}"))?;
    writer
        .flush()
        .map_err(|err| format!("failed to flush nest output: {err}"))?;
    Ok(())
}

fn compute_utilization_pct(input: &NestInput, result: &MultiSheetResult) -> f64 {
    let sheet_area = input.sheet.width_mm * input.sheet.height_mm;
    if sheet_area <= 0.0 || result.sheets_used == 0 {
        return 0.0;
    }

    let mut area_by_id = std::collections::BTreeMap::new();
    for p in &input.parts {
        let holes_area: f64 = p
            .holes_points_mm
            .iter()
            .map(|hole| polygon_area_mm2(hole))
            .sum();
        area_by_id.insert(
            p.id.clone(),
            (polygon_area_mm2(&p.outer_points_mm) - holes_area).max(0.0),
        );
    }
    let used_area: f64 = result
        .placed
        .iter()
        .map(|pl| area_by_id.get(&pl.part_id).copied().unwrap_or(0.0))
        .sum();
    ((used_area / (sheet_area * result.sheets_used as f64)) * 100.0).clamp(0.0, 100.0)
}

fn polygon_area_mm2(pts: &[[f64; 2]]) -> f64 {
    if pts.len() < 3 {
        return 0.0;
    }
    let mut sum = 0.0;
    for i in 0..pts.len() {
        let [x0, y0] = pts[i];
        let [x1, y1] = pts[(i + 1) % pts.len()];
        sum += x0 * y1 - x1 * y0;
    }
    sum.abs() * 0.5
}
