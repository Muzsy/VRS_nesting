use jagua_rs::geometry::geo_traits::CollidesWith;
use jagua_rs::geometry::primitives::{Edge as JagEdge, Point as JagPoint, SPolygon};
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
    allowed_rotations_deg: Vec<i64>,
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
    min_x: f64,
    min_y: f64,
    max_x: f64,
    max_y: f64,
    width: f64,
    height: f64,
    _outer_poly: SPolygon,
    hole_polys: Vec<SPolygon>,
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
    allowed_rotations_deg: Vec<i64>,
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

fn to_jag_point(p: Point) -> JagPoint {
    JagPoint(p.x as f32, p.y as f32)
}

fn to_jag_polygon(points: &[Point], label: &str) -> Result<SPolygon, String> {
    let vertices: Vec<JagPoint> = points.iter().copied().map(to_jag_point).collect();
    SPolygon::new(vertices).map_err(|e| format!("{label}: {e}"))
}

fn stock_to_shape(stock: &Stock) -> Result<SheetShape, String> {
    let outer: Vec<Point> = if let Some(raw_outer) = &stock.outer_points {
        if raw_outer.len() < 3 {
            return Err(format!(
                "stock {} outer_points must have >=3 points",
                stock.id
            ));
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
                    return Err(format!(
                        "stock {} hole polygon must have >=3 points",
                        stock.id
                    ));
                }
                parsed.push(hole.iter().map(point_from_input).collect());
            }
            parsed
        }
    };

    let (min_x, min_y, max_x, max_y) =
        polygon_bbox(&outer).ok_or_else(|| format!("stock {} outer polygon is empty", stock.id))?;
    let bbox_w = max_x - min_x;
    let bbox_h = max_y - min_y;
    if bbox_w <= 0.0 || bbox_h <= 0.0 {
        return Err(format!("stock {} outer polygon has invalid bbox", stock.id));
    }

    let outer_poly = to_jag_polygon(&outer, &format!("stock {} outer_points", stock.id))?;
    let mut hole_polys = Vec::new();
    for (idx, hole) in holes.iter().enumerate() {
        hole_polys.push(to_jag_polygon(
            hole,
            &format!("stock {} holes_points[{idx}]", stock.id),
        )?);
    }

    Ok(SheetShape {
        min_x,
        min_y,
        max_x,
        max_y,
        width: bbox_w,
        height: bbox_h,
        _outer_poly: outer_poly,
        hole_polys,
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

fn normalize_allowed_rotations(raw: &[i64]) -> Result<Vec<i64>, String> {
    if raw.is_empty() {
        return Err("part.allowed_rotations_deg must be non-empty".to_string());
    }

    let mut out = Vec::new();
    for r in raw {
        let rot = r.rem_euclid(360);
        if !matches!(rot, 0 | 90 | 180 | 270) {
            return Err(format!(
                "unsupported rotation in allowed_rotations_deg: {r} (normalized: {rot})"
            ));
        }
        if !out.contains(&rot) {
            out.push(rot);
        }
    }
    Ok(out)
}

fn dims_for_rotation(width: f64, height: f64, rot: i64) -> Option<(f64, f64)> {
    match rot.rem_euclid(360) {
        0 | 180 => Some((width, height)),
        90 | 270 => Some((height, width)),
        _ => None,
    }
}

fn rotated_bbox_min_offset(width: f64, height: f64, rot: i64) -> Option<(f64, f64)> {
    match rot.rem_euclid(360) {
        0 => Some((0.0, 0.0)),
        90 => Some((-height, 0.0)),
        180 => Some((-width, -height)),
        270 => Some((0.0, -width)),
        _ => None,
    }
}

fn placement_anchor_from_rect_min(
    rect_min_x: f64,
    rect_min_y: f64,
    width: f64,
    height: f64,
    rot: i64,
) -> Option<(f64, f64)> {
    let (bbox_min_x, bbox_min_y) = rotated_bbox_min_offset(width, height, rot)?;
    Some((rect_min_x - bbox_min_x, rect_min_y - bbox_min_y))
}

fn can_fit_any_stock(part: &Part, sheets: &[SheetShape]) -> Result<bool, String> {
    let allowed_rotations = normalize_allowed_rotations(&part.allowed_rotations_deg)?;
    for sheet in sheets {
        for rot in &allowed_rotations {
            let Some((w, h)) = dims_for_rotation(part.width, part.height, *rot) else {
                continue;
            };
            if w <= sheet.width + EPS && h <= sheet.height + EPS {
                return Ok(true);
            }
        }
    }
    Ok(false)
}

fn expand_instances(parts: &[Part]) -> Result<Vec<Instance>, String> {
    let mut instances = Vec::new();
    for part in parts {
        let allowed_rotations = normalize_allowed_rotations(&part.allowed_rotations_deg)?;
        for idx in 0..part.quantity {
            instances.push(Instance {
                instance_id: format!("{}__{:04}", part.id, idx + 1),
                part_id: part.id.clone(),
                width: part.width,
                height: part.height,
                allowed_rotations_deg: allowed_rotations.clone(),
            });
        }
    }
    instances.sort_by(|a, b| a.instance_id.cmp(&b.instance_id));
    Ok(instances)
}

fn jag_edge_from_points(a: Point, b: Point) -> Option<JagEdge> {
    JagEdge::try_new(to_jag_point(a), to_jag_point(b)).ok()
}

fn rect_corners(rect: Rect) -> [Point; 4] {
    [
        Point {
            x: rect.x1,
            y: rect.y1,
        },
        Point {
            x: rect.x2,
            y: rect.y1,
        },
        Point {
            x: rect.x2,
            y: rect.y2,
        },
        Point {
            x: rect.x1,
            y: rect.y2,
        },
    ]
}

fn rect_edges(rect: Rect) -> [(Point, Point); 4] {
    let c = rect_corners(rect);
    [(c[0], c[1]), (c[1], c[2]), (c[2], c[3]), (c[3], c[0])]
}

fn rect_inside_sheet_shape(rect: Rect, sheet: &SheetShape) -> bool {
    // Axis-aligned in-bounds guard for the current v1 rectangular stock contract.
    if rect.x1 < sheet.min_x - EPS
        || rect.y1 < sheet.min_y - EPS
        || rect.x2 > sheet.max_x + EPS
        || rect.y2 > sheet.max_y + EPS
    {
        return false;
    }

    let corners = rect_corners(rect);
    let rect_edges_arr = rect_edges(rect);
    for hole in &sheet.hole_polys {
        for c in corners {
            if hole.collides_with(&to_jag_point(c)) {
                return false;
            }
        }

        for re in rect_edges_arr {
            let Some(rect_edge) = jag_edge_from_points(re.0, re.1) else {
                continue;
            };
            for hole_edge in hole.edge_iter() {
                if rect_edge.collides_with(&hole_edge) {
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
    for rot in &instance.allowed_rotations_deg {
        let Some((w, h)) = dims_for_rotation(instance.width, instance.height, *rot) else {
            continue;
        };
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

        // Output x/y must be the translation anchor used by the validator:
        // rotate shape around (0,0), then translate by (x,y).
        let Some((placement_x, placement_y)) =
            placement_anchor_from_rect_min(x, y, instance.width, instance.height, *rot)
        else {
            continue;
        };

        let placed = Placement {
            instance_id: instance.instance_id.clone(),
            part_id: instance.part_id.clone(),
            sheet_index,
            x: placement_x,
            y: placement_y,
            rotation_deg: *rot,
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
    let instances = expand_instances(&input.parts)?;
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

        if !can_fit_any_stock(part, &sheets)? {
            unplaced.push(Unplaced {
                instance_id: instance.instance_id.clone(),
                part_id: instance.part_id.clone(),
                reason: "PART_NEVER_FITS_STOCK".to_string(),
            });
            continue;
        }

        let mut placed = None;
        for (idx, sheet) in sheets.iter().enumerate() {
            if let Some(candidate) =
                try_place_on_sheet(instance, sheet, &mut per_sheet_cursor[idx], idx)
            {
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

#[cfg(test)]
mod tests {
    use super::{dims_for_rotation, placement_anchor_from_rect_min, rotated_bbox_min_offset};

    fn approx_eq(a: f64, b: f64) -> bool {
        (a - b).abs() <= 1e-9
    }

    #[test]
    fn rotated_bbox_min_offset_matches_expected_quadrants() {
        let width = 1000.0;
        let height = 2000.0;
        let expected = [
            (0, (0.0, 0.0)),
            (90, (-2000.0, 0.0)),
            (180, (-1000.0, -2000.0)),
            (270, (0.0, -1000.0)),
        ];

        for (rot, (exp_x, exp_y)) in expected {
            let (x, y) = rotated_bbox_min_offset(width, height, rot).expect("supported rotation");
            assert!(approx_eq(x, exp_x), "rot={rot} min_x={x} expected={exp_x}");
            assert!(approx_eq(y, exp_y), "rot={rot} min_y={y} expected={exp_y}");
        }
    }

    #[test]
    fn placement_anchor_from_rect_min_keeps_rotated_bbox_inside_target_rect() {
        let width = 1000.0;
        let height = 2000.0;
        let rect_min_x = 0.0;
        let rect_min_y = 480.0;

        for rot in [0, 90, 180, 270] {
            let (anchor_x, anchor_y) =
                placement_anchor_from_rect_min(rect_min_x, rect_min_y, width, height, rot)
                    .expect("supported rotation");
            let (min_off_x, min_off_y) =
                rotated_bbox_min_offset(width, height, rot).expect("supported rotation");
            let Some((rw, rh)) = dims_for_rotation(width, height, rot) else {
                panic!("unsupported rotation in test");
            };

            let placed_min_x = anchor_x + min_off_x;
            let placed_min_y = anchor_y + min_off_y;
            let placed_max_x = placed_min_x + rw;
            let placed_max_y = placed_min_y + rh;

            assert!(
                approx_eq(placed_min_x, rect_min_x),
                "rot={rot} placed_min_x={placed_min_x} rect_min_x={rect_min_x}"
            );
            assert!(
                approx_eq(placed_min_y, rect_min_y),
                "rot={rot} placed_min_y={placed_min_y} rect_min_y={rect_min_y}"
            );
            assert!(
                approx_eq(placed_max_x, rect_min_x + rw),
                "rot={rot} placed_max_x={placed_max_x} expected={}",
                rect_min_x + rw
            );
            assert!(
                approx_eq(placed_max_y, rect_min_y + rh),
                "rot={rot} placed_max_y={placed_max_y} expected={}",
                rect_min_y + rh
            );
        }
    }
}
