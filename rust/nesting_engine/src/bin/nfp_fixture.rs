use std::io::{self, BufReader, BufWriter, Write};

use nesting_engine::geometry::types::{is_convex, signed_area2_i128, Point64, Polygon64};
use nesting_engine::nfp::concave::compute_concave_nfp_default;
use nesting_engine::nfp::convex::compute_convex_nfp;
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize)]
struct FixtureInput {
    polygon_a: Vec<[i64; 2]>,
    polygon_b: Vec<[i64; 2]>,
}

#[derive(Debug, Serialize)]
struct FixtureOutput {
    nfp_outer: Vec<[i64; 2]>,
    vertex_count: usize,
}

fn to_polygon(points: &[[i64; 2]]) -> Polygon64 {
    Polygon64 {
        outer: points
            .iter()
            .map(|p| Point64 { x: p[0], y: p[1] })
            .collect(),
        holes: Vec::new(),
    }
}

fn canonicalize_ring(points: &[Point64]) -> Vec<Point64> {
    let mut ring = points.to_vec();
    if ring.len() > 1 && ring.first() == ring.last() {
        ring.pop();
    }
    if ring.is_empty() {
        return ring;
    }

    if signed_area2_i128(&ring) < 0 {
        ring.reverse();
    }

    if let Some((start_idx, _)) = ring
        .iter()
        .enumerate()
        .min_by_key(|(_, p)| (p.x, p.y))
    {
        ring.rotate_left(start_idx);
    }

    ring
}

fn run() -> Result<(), String> {
    let stdin = io::stdin();
    let reader = BufReader::new(stdin.lock());
    let input: FixtureInput =
        serde_json::from_reader(reader).map_err(|err| format!("invalid fixture JSON: {err}"))?;

    let a = to_polygon(&input.polygon_a);
    let b = to_polygon(&input.polygon_b);

    let nfp = if !is_convex(&a.outer) || !is_convex(&b.outer) {
        compute_concave_nfp_default(&a, &b)
    } else {
        compute_convex_nfp(&a, &b)
    }
    .map_err(|err| format!("NFP computation failed: {err}"))?;

    let canonical = canonicalize_ring(&nfp.outer);
    let output = FixtureOutput {
        vertex_count: canonical.len(),
        nfp_outer: canonical.iter().map(|p| [p.x, p.y]).collect(),
    };

    let stdout = io::stdout();
    let mut writer = BufWriter::new(stdout.lock());
    serde_json::to_writer(&mut writer, &output)
        .map_err(|err| format!("failed to serialize output JSON: {err}"))?;
    writer
        .write_all(b"\n")
        .map_err(|err| format!("failed to flush newline: {err}"))?;
    writer
        .flush()
        .map_err(|err| format!("failed to flush stdout: {err}"))?;

    Ok(())
}

fn main() {
    if let Err(err) = run() {
        eprintln!("nfp_fixture: {err}");
        std::process::exit(1);
    }
}
