use crate::geometry::{
    scale::SCALE,
    types::{cross_product_i128, is_ccw, signed_area2_i128, Point64, Polygon64},
};

#[derive(Debug, Clone, PartialEq)]
pub struct SimplifyResult {
    pub polygon: Polygon64,
    pub vertex_count_before: usize,
    pub vertex_count_after: usize,
    pub reflex_vertex_count_before: usize,
    pub reflex_vertex_count_after: usize,
    pub area_delta_mm2: f64,
    pub bbox_delta_mm: f64,
    pub max_deviation_mm: f64,
    pub topology_changed: bool,
    pub simplification_ratio: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub enum SimplifyError {
    EpsilonTooLarge {
        epsilon_mm: f64,
        area_delta_mm2: f64,
    },
    TopologyChanged {
        reflex_before: usize,
        reflex_after: usize,
    },
    EmptyResult,
}

pub fn topology_preserving_rdp(
    poly: &Polygon64,
    epsilon_mm: f64,
) -> Result<SimplifyResult, SimplifyError> {
    if poly.outer.len() < 3 {
        return Err(SimplifyError::EmptyResult);
    }

    let eps = if epsilon_mm.is_finite() && epsilon_mm > 0.0 {
        epsilon_mm
    } else {
        0.0
    };

    let before_outer = poly.outer.clone();
    let before_holes = poly.holes.clone();
    let reflex_before = count_reflex_vertices(&before_outer);

    let simplified_outer = simplify_ring_conservative(&before_outer, eps)?;
    let mut simplified_holes = Vec::with_capacity(before_holes.len());
    for hole in &before_holes {
        simplified_holes.push(simplify_ring_conservative(hole, eps)?);
    }

    let simplified = Polygon64 {
        outer: simplified_outer,
        holes: simplified_holes,
    };

    if simplified.outer.len() < 3 {
        return Err(SimplifyError::EmptyResult);
    }

    let reflex_after = count_reflex_vertices(&simplified.outer);
    if reflex_after < reflex_before {
        return Err(SimplifyError::TopologyChanged {
            reflex_before,
            reflex_after,
        });
    }

    let area_before = polygon_area_mm2(poly);
    let area_after = polygon_area_mm2(&simplified);
    let area_delta_mm2 = (area_after - area_before).abs();

    let perimeter_before = ring_perimeter_mm(&before_outer);
    let max_area_delta = eps * perimeter_before;
    if eps > 0.0 && area_delta_mm2 > max_area_delta {
        return Err(SimplifyError::EpsilonTooLarge {
            epsilon_mm: eps,
            area_delta_mm2,
        });
    }

    let bbox_delta_mm = bbox_delta_mm(&before_outer, &simplified.outer);
    let max_deviation_mm = polygon_max_deviation_mm(poly, &simplified);

    let vertex_count_before = before_outer.len();
    let vertex_count_after = simplified.outer.len();

    Ok(SimplifyResult {
        polygon: simplified,
        vertex_count_before,
        vertex_count_after,
        reflex_vertex_count_before: reflex_before,
        reflex_vertex_count_after: reflex_after,
        area_delta_mm2,
        bbox_delta_mm,
        max_deviation_mm,
        topology_changed: false,
        simplification_ratio: if vertex_count_before == 0 {
            1.0
        } else {
            vertex_count_after as f64 / vertex_count_before as f64
        },
    })
}

pub fn count_reflex_vertices(ring: &[Point64]) -> usize {
    let n = ring.len();
    if n < 3 {
        return 0;
    }

    let ccw = is_ccw(ring);
    let mut count = 0usize;
    for i in 0..n {
        let prev = ring[(i + n - 1) % n];
        let curr = ring[i];
        let next = ring[(i + 1) % n];
        let cross = cross_product_i128(
            curr.x - prev.x,
            curr.y - prev.y,
            next.x - curr.x,
            next.y - curr.y,
        );
        if cross == 0 {
            continue;
        }
        let is_reflex = if ccw { cross < 0 } else { cross > 0 };
        if is_reflex {
            count += 1;
        }
    }
    count
}

fn simplify_ring_conservative(
    ring: &[Point64],
    epsilon_mm: f64,
) -> Result<Vec<Point64>, SimplifyError> {
    if ring.len() < 3 {
        return Err(SimplifyError::EmptyResult);
    }

    if epsilon_mm <= 0.0 {
        return Ok(ring.to_vec());
    }

    let mut out = ring.to_vec();
    loop {
        if out.len() < 4 {
            break;
        }

        let mut changed = false;
        let n = out.len();
        let mut keep = vec![true; n];

        for i in 0..n {
            let prev = out[(i + n - 1) % n];
            let curr = out[i];
            let next = out[(i + 1) % n];
            let cross = cross_product_i128(
                curr.x - prev.x,
                curr.y - prev.y,
                next.x - curr.x,
                next.y - curr.y,
            );
            if cross != 0 {
                continue;
            }
            let dist = point_to_segment_distance_mm(curr, prev, next);
            if dist <= epsilon_mm {
                keep[i] = false;
                changed = true;
            }
        }

        if !changed {
            break;
        }

        let mut filtered = Vec::with_capacity(out.len());
        for (idx, p) in out.iter().enumerate() {
            if keep[idx] {
                filtered.push(*p);
            }
        }
        if filtered.len() < 3 {
            return Err(SimplifyError::EmptyResult);
        }
        out = filtered;
    }

    Ok(out)
}

fn polygon_area_mm2(poly: &Polygon64) -> f64 {
    let outer = ring_area_mm2(&poly.outer).abs();
    let holes: f64 = poly.holes.iter().map(|h| ring_area_mm2(h).abs()).sum();
    outer - holes
}

fn ring_area_mm2(ring: &[Point64]) -> f64 {
    let area2 = signed_area2_i128(ring).abs() as f64;
    let scale2 = (SCALE as f64) * (SCALE as f64);
    area2 / (2.0 * scale2)
}

fn ring_perimeter_mm(ring: &[Point64]) -> f64 {
    if ring.len() < 2 {
        return 0.0;
    }
    let mut perimeter = 0.0;
    for i in 0..ring.len() {
        let a = ring[i];
        let b = ring[(i + 1) % ring.len()];
        let dx = (b.x - a.x) as f64 / SCALE as f64;
        let dy = (b.y - a.y) as f64 / SCALE as f64;
        perimeter += (dx * dx + dy * dy).sqrt();
    }
    perimeter
}

fn ring_bbox_mm(ring: &[Point64]) -> (f64, f64) {
    let mut min_x = i64::MAX;
    let mut min_y = i64::MAX;
    let mut max_x = i64::MIN;
    let mut max_y = i64::MIN;
    for p in ring {
        min_x = min_x.min(p.x);
        min_y = min_y.min(p.y);
        max_x = max_x.max(p.x);
        max_y = max_y.max(p.y);
    }
    let width = (max_x - min_x) as f64 / SCALE as f64;
    let height = (max_y - min_y) as f64 / SCALE as f64;
    (width, height)
}

fn bbox_delta_mm(before: &[Point64], after: &[Point64]) -> f64 {
    let (bw, bh) = ring_bbox_mm(before);
    let (aw, ah) = ring_bbox_mm(after);
    (bw - aw).abs().max((bh - ah).abs())
}

fn point_to_segment_distance_mm(p: Point64, a: Point64, b: Point64) -> f64 {
    let px = p.x as f64;
    let py = p.y as f64;
    let ax = a.x as f64;
    let ay = a.y as f64;
    let bx = b.x as f64;
    let by = b.y as f64;

    let abx = bx - ax;
    let aby = by - ay;
    let apx = px - ax;
    let apy = py - ay;

    let ab2 = abx * abx + aby * aby;
    if ab2 == 0.0 {
        let dx = px - ax;
        let dy = py - ay;
        return (dx * dx + dy * dy).sqrt() / SCALE as f64;
    }

    let t = ((apx * abx + apy * aby) / ab2).clamp(0.0, 1.0);
    let cx = ax + t * abx;
    let cy = ay + t * aby;
    let dx = px - cx;
    let dy = py - cy;
    (dx * dx + dy * dy).sqrt() / SCALE as f64
}

fn ring_max_deviation_mm(original: &[Point64], simplified: &[Point64]) -> f64 {
    if simplified.len() < 2 || original.is_empty() {
        return 0.0;
    }

    let mut max_d = 0.0;
    for point in original {
        let mut best = f64::INFINITY;
        for i in 0..simplified.len() {
            let a = simplified[i];
            let b = simplified[(i + 1) % simplified.len()];
            let d = point_to_segment_distance_mm(*point, a, b);
            if d < best {
                best = d;
            }
        }
        if best > max_d {
            max_d = best;
        }
    }
    max_d
}

fn polygon_max_deviation_mm(original: &Polygon64, simplified: &Polygon64) -> f64 {
    let mut max_d = ring_max_deviation_mm(&original.outer, &simplified.outer);
    let hole_count = original.holes.len().min(simplified.holes.len());
    for idx in 0..hole_count {
        max_d = max_d.max(ring_max_deviation_mm(
            &original.holes[idx],
            &simplified.holes[idx],
        ));
    }
    max_d
}

#[cfg(test)]
mod tests {
    use super::{count_reflex_vertices, topology_preserving_rdp};
    use crate::geometry::{
        scale::mm_to_i64,
        types::{Point64, Polygon64},
    };

    #[test]
    fn reflex_count_detects_concavity() {
        let ring = vec![
            Point64 { x: 0, y: 0 },
            Point64 { x: 10, y: 0 },
            Point64 { x: 6, y: 4 },
            Point64 { x: 10, y: 8 },
            Point64 { x: 0, y: 8 },
        ];
        assert!(count_reflex_vertices(&ring) >= 1);
    }

    #[test]
    fn simplify_keeps_topology_on_rectangle() {
        let poly = Polygon64 {
            outer: vec![
                Point64 {
                    x: mm_to_i64(0.0),
                    y: mm_to_i64(0.0),
                },
                Point64 {
                    x: mm_to_i64(10.0),
                    y: mm_to_i64(0.0),
                },
                Point64 {
                    x: mm_to_i64(10.0),
                    y: mm_to_i64(5.0),
                },
                Point64 {
                    x: mm_to_i64(0.0),
                    y: mm_to_i64(5.0),
                },
            ],
            holes: Vec::new(),
        };
        let out = topology_preserving_rdp(&poly, 0.1).expect("simplify must pass");
        assert!(!out.topology_changed);
        assert!(out.area_delta_mm2 <= 0.5);
    }
}
