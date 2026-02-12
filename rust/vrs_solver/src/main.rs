use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;

#[derive(Debug, Deserialize)]
struct SolverInput {
    contract_version: String,
    project_name: String,
    seed: i64,
    time_limit_s: i64,
    stocks: Vec<Stock>,
    parts: Vec<Part>,
}

#[derive(Debug, Deserialize, Clone)]
struct Stock {
    id: String,
    width: f64,
    height: f64,
    quantity: i64,
}

#[derive(Debug, Deserialize, Clone)]
struct Part {
    id: String,
    width: f64,
    height: f64,
    quantity: i64,
    #[serde(default)]
    allow_rotation: bool,
}

#[derive(Debug, Serialize)]
struct SolverOutput {
    contract_version: String,
    status: String,
    placements: Vec<Placement>,
    unplaced: Vec<Unplaced>,
    metrics: Metrics,
}

#[derive(Debug, Serialize)]
struct Placement {
    instance_id: String,
    part_id: String,
    sheet_index: usize,
    x: f64,
    y: f64,
    rotation_deg: i64,
}

#[derive(Debug, Serialize)]
struct Unplaced {
    instance_id: String,
    part_id: String,
    reason: String,
}

#[derive(Debug, Serialize)]
struct Metrics {
    placed_count: usize,
    unplaced_count: usize,
    sheet_count_used: usize,
    seed: i64,
    time_limit_s: i64,
    project_name: String,
}

#[derive(Debug)]
struct Instance {
    instance_id: String,
    part_id: String,
    width: f64,
    height: f64,
    allow_rotation: bool,
}

#[derive(Debug)]
struct SheetCursor {
    x: f64,
    y: f64,
    row_h: f64,
}

fn parse_args() -> Result<HashMap<String, String>, String> {
    let mut args = std::env::args().skip(1);
    let mut out = HashMap::new();
    while let Some(k) = args.next() {
        if !k.starts_with("--") {
            return Err(format!("unexpected argument: {k}"));
        }
        let v = args
            .next()
            .ok_or_else(|| format!("missing value for argument: {k}"))?;
        out.insert(k, v);
    }
    Ok(out)
}

fn can_fit_any_stock(part: &Part, stocks: &[Stock]) -> bool {
    for stock in stocks {
        if part.width <= stock.width && part.height <= stock.height {
            return true;
        }
        if part.allow_rotation && part.height <= stock.width && part.width <= stock.height {
            return true;
        }
    }
    false
}

fn expand_instances(parts: &[Part]) -> Vec<Instance> {
    let mut instances = Vec::new();
    for part in parts {
        for idx in 0..part.quantity {
            instances.push(Instance {
                instance_id: format!("{}__{:04}", part.id, idx + 1),
                part_id: part.id.clone(),
                width: part.width,
                height: part.height,
                allow_rotation: part.allow_rotation,
            });
        }
    }
    instances.sort_by(|a, b| a.instance_id.cmp(&b.instance_id));
    instances
}

fn try_place_on_sheet(
    instance: &Instance,
    sheet_w: f64,
    sheet_h: f64,
    cursor: &mut SheetCursor,
    sheet_index: usize,
) -> Option<Placement> {
    let mut variants = vec![(instance.width, instance.height, 0i64)];
    if instance.allow_rotation && (instance.width - instance.height).abs() > f64::EPSILON {
        variants.push((instance.height, instance.width, 90));
    }

    for (w, h, rot) in variants {
        let mut x = cursor.x;
        let mut y = cursor.y;
        let mut row_h = cursor.row_h;

        if x + w > sheet_w {
            x = 0.0;
            y += row_h;
            row_h = 0.0;
        }

        if y + h > sheet_h {
            continue;
        }

        let placed = Placement {
            instance_id: instance.instance_id.clone(),
            part_id: instance.part_id.clone(),
            sheet_index,
            x,
            y,
            rotation_deg: rot,
        };

        cursor.x = x + w;
        if h > row_h {
            row_h = h;
        }
        cursor.row_h = row_h;
        cursor.y = y;
        return Some(placed);
    }

    None
}

fn main() -> Result<(), String> {
    let args = parse_args()?;
    let input_path = args
        .get("--input")
        .ok_or_else(|| "--input is required".to_string())?;
    let output_path = args
        .get("--output")
        .ok_or_else(|| "--output is required".to_string())?;

    let content = fs::read_to_string(input_path)
        .map_err(|e| format!("failed to read input json {input_path}: {e}"))?;
    let input: SolverInput =
        serde_json::from_str(&content).map_err(|e| format!("invalid input json: {e}"))?;

    if input.contract_version != "v1" {
        return Err("unsupported contract_version; expected v1".to_string());
    }

    let mut sheets = Vec::new();
    for stock in &input.stocks {
        if stock.quantity < 1 {
            continue;
        }
        for _ in 0..stock.quantity {
            sheets.push((stock.id.clone(), stock.width, stock.height));
        }
    }

    let instances = expand_instances(&input.parts);
    let mut placements: Vec<Placement> = Vec::new();
    let mut unplaced: Vec<Unplaced> = Vec::new();

    let mut per_sheet_cursor: Vec<SheetCursor> = sheets
        .iter()
        .map(|_| SheetCursor {
            x: 0.0,
            y: 0.0,
            row_h: 0.0,
        })
        .collect();

    for instance in &instances {
        let part = input
            .parts
            .iter()
            .find(|p| p.id == instance.part_id)
            .ok_or_else(|| format!("internal error: part not found: {}", instance.part_id))?;

        if !can_fit_any_stock(part, &input.stocks) {
            unplaced.push(Unplaced {
                instance_id: instance.instance_id.clone(),
                part_id: instance.part_id.clone(),
                reason: "PART_NEVER_FITS_STOCK".to_string(),
            });
            continue;
        }

        let mut placed = None;
        for (idx, (_stock_id, sw, sh)) in sheets.iter().enumerate() {
            if let Some(candidate) = try_place_on_sheet(instance, *sw, *sh, &mut per_sheet_cursor[idx], idx) {
                placed = Some(candidate);
                break;
            }
        }

        if let Some(p) = placed {
            placements.push(p);
        } else {
            unplaced.push(Unplaced {
                instance_id: instance.instance_id.clone(),
                part_id: instance.part_id.clone(),
                reason: "NO_CAPACITY".to_string(),
            });
        }
    }

    let status = if unplaced.is_empty() { "ok" } else { "partial" }.to_string();
    let sheet_count_used = placements
        .iter()
        .map(|p| p.sheet_index)
        .max()
        .map(|v| v + 1)
        .unwrap_or(0);

    let placed_count = placements.len();
    let unplaced_count = unplaced.len();

    let output = SolverOutput {
        contract_version: "v1".to_string(),
        status,
        placements,
        unplaced,
        metrics: Metrics {
            placed_count,
            unplaced_count,
            sheet_count_used,
            seed: input.seed,
            time_limit_s: input.time_limit_s,
            project_name: input.project_name,
        },
    };

    let output_json = serde_json::to_string_pretty(&output)
        .map_err(|e| format!("failed to serialize output json: {e}"))?;
    fs::write(output_path, format!("{output_json}\n"))
        .map_err(|e| format!("failed to write output json {output_path}: {e}"))?;

    Ok(())
}
