use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;

const EPS: f64 = 1e-9;

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
    quantity: i64,
    width: Option<f64>,
    height: Option<f64>,
    outer_points: Option<Vec<PointInput>>,
    holes_points: Option<Vec<Vec<PointInput>>>,
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

#[derive(Debug, Deserialize, Clone)]
#[serde(untagged)]
enum PointInput {
    Pair([f64; 2]),
    Obj { x: f64, y: f64 },
}

#[derive(Debug, Clone, Copy)]
struct Point {
    x: f64,
    y: f64,
}

#[derive(Debug, Clone)]
struct SheetShape {
    width: f64,
    height: f64,
    outer: Vec<Point>,
    holes: Vec<Vec<Point>>,
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

#[derive(Debug, Clone, Copy)]
struct Rect {
    x1: f64,
    y1: f64,
    x2: f64,
    y2: f64,
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

fn point_from_input(raw: &PointInput) -> Point {
    match raw {
        PointInput::Pair([x, y]) => Point { x: *x, y: *y },
        PointInput::Obj { x, y } => Point { x: *x, y: *y },
    }
}

fn polygon_bbox(points: &[Point]) -> Option<(f64, f64, f64, f64)> {
    if points.is_empty() {
        return None;
    }
    let mut min_x = points[0].x;
    let mut max_x = points[0].x;
    let mut min_y = points[0].y;
    let mut max_y = points[0].y;
    for p in points.iter().skip(1) {
        if p.x < min_x {
            min_x = p.x;
        }
        if p.x > max_x {
            max_x = p.x;
        }
        if p.y < min_y {
            min_y = p.y;
        }
        if p.y > max_y {
            max_y = p.y;
        }
    }
    Some((min_x, min_y, max_x, max_y))
}

fn stock_to_shape(stock: &Stock) -> Result<SheetShape, String> {
    let outer: Vec<Point> = if let Some(raw_outer) = &stock.outer_points {
        if raw_outer.len() < 3 {
            return Err(format!("stock {} outer_points must have >=3 points", stock.id));
        }
        raw_outer.iter().map(point_from_input).collect()
    } else {
        let w = stock
            .width
            .ok_or_else(|| format!("stock {} missing width", stock.id))?;
        let h = stock
            .height
            .ok_or_else(|| format!("stock {} missing height", stock.id))?;
        if w <= 0.0 || h <= 0.0 {
            return Err(format!("stock {} width/height must be > 0", stock.id));
        }
        vec![
            Point { x: 0.0, y: 0.0 },
            Point { x: w, y: 0.0 },
            Point { x: w, y: h },
            Point { x: 0.0, y: h },
        ]
    };

    let holes: Vec<Vec<Point>> = match &stock.holes_points {
        None => Vec::new(),
        Some(raw_holes) => {
            let mut parsed = Vec::new();
            for hole in raw_holes {
                if hole.len() < 3 {
                    return Err(format!("stock {} hole polygon must have >=3 points", stock.id));
                }
                parsed.push(hole.iter().map(point_from_input).collect());
            }
            parsed
        }
    };

    let (min_x, min_y, max_x, max_y) = polygon_bbox(&outer)
        .ok_or_else(|| format!("stock {} outer polygon is empty", stock.id))?;
    let bbox_w = max_x - min_x;
    let bbox_h = max_y - min_y;
    if bbox_w <= 0.0 || bbox_h <= 0.0 {
        return Err(format!("stock {} outer polygon has invalid bbox", stock.id));
    }

    Ok(SheetShape {
        width: bbox_w,
        height: bbox_h,
        outer,
        holes,
    })
}

fn expand_sheets(stocks: &[Stock]) -> Result<Vec<SheetShape>, String> {
    let mut out = Vec::new();
    for stock in stocks {
        if stock.quantity <= 0 {
            continue;
        }
        let shape = stock_to_shape(stock)?;
        for _ in 0..stock.quantity {
            out.push(shape.clone());
        }
    }
    Ok(out)
}

fn can_fit_any_stock(part: &Part, sheets: &[SheetShape]) -> bool {
    for sheet in sheets {
        if part.width <= sheet.width + EPS && part.height <= sheet.height + EPS {
            return true;
        }
        if part.allow_rotation && part.height <= sheet.width + EPS && part.width <= sheet.height + EPS {
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

fn point_on_segment(p: Point, a: Point, b: Point) -> bool {
    let cross = (p.y - a.y) * (b.x - a.x) - (p.x - a.x) * (b.y - a.y);
    if cross.abs() > EPS {
        return false;
    }
    let dot = (p.x - a.x) * (p.x - b.x) + (p.y - a.y) * (p.y - b.y);
    dot <= EPS
}

fn point_in_polygon(p: Point, poly: &[Point]) -> bool {
    let mut inside = false;
    for i in 0..poly.len() {
        let a = poly[i];
        let b = poly[(i + 1) % poly.len()];
        if point_on_segment(p, a, b) {
            return true;
        }
        let intersects = ((a.y > p.y) != (b.y > p.y))
            && (p.x < (b.x - a.x) * (p.y - a.y) / ((b.y - a.y) + EPS) + a.x);
        if intersects {
            inside = !inside;
        }
    }
    inside
}

fn orientation(a: Point, b: Point, c: Point) -> f64 {
    (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x)
}

fn segments_intersect(a1: Point, a2: Point, b1: Point, b2: Point) -> bool {
    let o1 = orientation(a1, a2, b1);
    let o2 = orientation(a1, a2, b2);
    let o3 = orientation(b1, b2, a1);
    let o4 = orientation(b1, b2, a2);

    if ((o1 > EPS && o2 < -EPS) || (o1 < -EPS && o2 > EPS))
        && ((o3 > EPS && o4 < -EPS) || (o3 < -EPS && o4 > EPS))
    {
        return true;
    }

    if o1.abs() <= EPS && point_on_segment(b1, a1, a2) {
        return true;
    }
    if o2.abs() <= EPS && point_on_segment(b2, a1, a2) {
        return true;
    }
    if o3.abs() <= EPS && point_on_segment(a1, b1, b2) {
        return true;
    }
    if o4.abs() <= EPS && point_on_segment(a2, b1, b2) {
        return true;
    }

    false
}

fn polygon_edges(poly: &[Point]) -> Vec<(Point, Point)> {
    let mut out = Vec::new();
    for i in 0..poly.len() {
        out.push((poly[i], poly[(i + 1) % poly.len()]));
    }
    out
}

fn rect_corners(rect: Rect) -> [Point; 4] {
    [
        Point { x: rect.x1, y: rect.y1 },
        Point { x: rect.x2, y: rect.y1 },
        Point { x: rect.x2, y: rect.y2 },
        Point { x: rect.x1, y: rect.y2 },
    ]
}

fn rect_edges(rect: Rect) -> [(Point, Point); 4] {
    let c = rect_corners(rect);
    [(c[0], c[1]), (c[1], c[2]), (c[2], c[3]), (c[3], c[0])]
}

fn rect_inside_sheet_shape(rect: Rect, sheet: &SheetShape) -> bool {
    let corners = rect_corners(rect);
    for c in corners {
        if !point_in_polygon(c, &sheet.outer) {
            return false;
        }
    }

    let rect_edges_arr = rect_edges(rect);
    for hole in &sheet.holes {
        for c in corners {
            if point_in_polygon(c, hole) {
                return false;
            }
        }
        let hole_edges = polygon_edges(hole);
        for re in rect_edges_arr {
            for he in &hole_edges {
                if segments_intersect(re.0, re.1, he.0, he.1) {
                    return false;
                }
            }
        }
    }

    true
}

fn try_place_on_sheet(
    instance: &Instance,
    sheet: &SheetShape,
    cursor: &mut SheetCursor,
    sheet_index: usize,
) -> Option<Placement> {
    let mut variants = vec![(instance.width, instance.height, 0i64)];
    if instance.allow_rotation && (instance.width - instance.height).abs() > EPS {
        variants.push((instance.height, instance.width, 90));
    }

    for (w, h, rot) in variants {
        let mut x = cursor.x;
        let mut y = cursor.y;
        let mut row_h = cursor.row_h;

        if x + w > sheet.width + EPS {
            x = 0.0;
            y += row_h;
            row_h = 0.0;
        }

        if y + h > sheet.height + EPS {
            continue;
        }

        let rect = Rect {
            x1: x,
            y1: y,
            x2: x + w,
            y2: y + h,
        };

        if !rect_inside_sheet_shape(rect, sheet) {
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

    let sheets = expand_sheets(&input.stocks)?;
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

        if !can_fit_any_stock(part, &sheets) {
            unplaced.push(Unplaced {
                instance_id: instance.instance_id.clone(),
                part_id: instance.part_id.clone(),
                reason: "PART_NEVER_FITS_STOCK".to_string(),
            });
            continue;
        }

        let mut placed = None;
        for (idx, sheet) in sheets.iter().enumerate() {
            if let Some(candidate) = try_place_on_sheet(instance, sheet, &mut per_sheet_cursor[idx], idx) {
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
