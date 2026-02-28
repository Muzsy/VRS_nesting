use std::time::Instant;

use crate::feasibility::{
    aabb::aabb_from_polygon64,
    can_place, PlacedPart,
    narrow::PlacedIndex,
};
use crate::geometry::{
    scale::i64_to_mm,
    trig_lut::{normalize_deg, round_div_i128, COS_Q, SIN_Q, TRIG_SCALE_I128},
    types::{is_convex, Point64, Polygon64},
};
use nesting_engine::nfp::{
    cache::{NfpCache, NfpCacheKey, shape_id},
    cfr::compute_cfr,
    concave::compute_concave_nfp_default,
    convex::compute_convex_nfp,
    ifp::{IfpRect, compute_ifp_rect},
};
use nesting_engine::geometry::types::{Point64 as LibPoint64, Polygon64 as LibPolygon64};

use super::blf::InflatedPartSpec;
use super::PlacementResult;

const MAX_VERTICES_PER_COMPONENT: usize = 512;
const MAX_CANDIDATES_PER_PART: usize = 4096;
const NUDGE_STEPS: [i64; 3] = [1, 2, 4];
const NUDGE_DIRS: [(i64, i64); 8] = [
    (1, 0),
    (0, 1),
    (1, 1),
    (-1, 0),
    (0, -1),
    (-1, -1),
    (-1, 1),
    (1, -1),
];

#[derive(Debug, Clone)]
struct RotationContext {
    rotation_deg: i32,
    rotation_rank: usize,
    moving_polygon: Polygon64,
    ifp: IfpRect,
}

#[derive(Debug, Clone, Copy)]
struct Candidate {
    tx: i64,
    ty: i64,
    rotation_idx: usize,
    cfr_component_rank: usize,
    vertex_rank_within_component: usize,
    nudge_rank: usize,
}

pub fn nfp_place(
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
    _grid_step_mm: f64,
    time_limit_sec: u64,
    started_at: Instant,
    cache: &mut NfpCache,
) -> PlacementResult {
    let mut ordered = parts.to_vec();
    ordered.sort_by(|a, b| {
        b.nominal_bbox_area
            .cmp(&a.nominal_bbox_area)
            .then_with(|| a.id.cmp(&b.id))
    });

    let bin_aabb = aabb_from_polygon64(bin_polygon);
    let mut placed_state = PlacedIndex::new();
    let mut placed_for_nfp: Vec<PlacedPart> = Vec::new();
    let mut placed = Vec::new();
    let mut unplaced = Vec::new();

    for part in &ordered {
        for instance in 0..part.quantity {
            if started_at.elapsed().as_secs() >= time_limit_sec {
                unplaced.push(super::blf::UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: "TIME_LIMIT_EXCEEDED".to_string(),
                });
                continue;
            }

            let mut rotation_values = part.allowed_rotations_deg.clone();
            rotation_values.sort_unstable();
            rotation_values.dedup();
            if rotation_values.is_empty() {
                unplaced.push(super::blf::UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: "PART_NEVER_FITS_SHEET".to_string(),
                });
                continue;
            }

            let mut rotation_contexts: Vec<RotationContext> = Vec::new();
            let mut all_candidates: Vec<Candidate> = Vec::new();

            for (rotation_rank, rotation_deg) in rotation_values.iter().copied().enumerate() {
                let rotated = rotate_polygon(&part.inflated_polygon, rotation_deg);
                let moving = normalize_polygon_min_xy(&rotated);
                let moving_aabb = aabb_from_polygon64(&moving);
                let Some(ifp) = compute_ifp_rect(
                    bin_aabb.min_x,
                    bin_aabb.max_x,
                    bin_aabb.min_y,
                    bin_aabb.max_y,
                    moving_aabb.min_x,
                    moving_aabb.max_x,
                    moving_aabb.min_y,
                    moving_aabb.max_y,
                ) else {
                    continue;
                };

                let moving_shape_id = shape_id(&to_lib_polygon(&moving));
                let mut nfp_polys: Vec<LibPolygon64> = Vec::new();
                let mut nfp_failed = false;
                for placed_part in &placed_for_nfp {
                    let (placed_normalized, placed_anchor_x, placed_anchor_y) =
                        normalize_polygon_min_xy_with_offset(&placed_part.inflated_polygon);
                    let key = NfpCacheKey {
                        shape_id_a: shape_id(&to_lib_polygon(&placed_normalized)),
                        shape_id_b: moving_shape_id,
                        rotation_steps_b: normalize_deg(rotation_deg) as i16,
                    };
                    if let Some(cached_rel) = cache.get(&key) {
                        let cached_world = translate_polygon(
                            &from_lib_polygon(cached_rel),
                            placed_anchor_x,
                            placed_anchor_y,
                        );
                        nfp_polys.push(to_lib_polygon(&cached_world));
                        continue;
                    }

                    let computed = compute_nfp_lib(&placed_normalized, &moving);
                    match computed {
                        Some(poly_rel) => {
                            cache.insert(key, poly_rel.clone());
                            let world_poly = translate_polygon(
                                &from_lib_polygon(&poly_rel),
                                placed_anchor_x,
                                placed_anchor_y,
                            );
                            nfp_polys.push(to_lib_polygon(&world_poly));
                        }
                        None => {
                            nfp_failed = true;
                            break;
                        }
                    }
                }
                if nfp_failed {
                    continue;
                }

                let cfr_components: Vec<Polygon64> = compute_cfr(&ifp.polygon, &nfp_polys)
                    .iter()
                    .map(from_lib_polygon)
                    .collect();
                if cfr_components.is_empty() {
                    continue;
                }

                let rotation_idx = rotation_contexts.len();
                rotation_contexts.push(RotationContext {
                    rotation_deg,
                    rotation_rank,
                    moving_polygon: moving,
                    ifp,
                });
                let ctx = &rotation_contexts[rotation_idx];
                append_candidates(
                    &mut all_candidates,
                    rotation_idx,
                    &cfr_components,
                    ctx,
                );
            }

            if all_candidates.is_empty() {
                unplaced.push(super::blf::UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: if started_at.elapsed().as_secs() >= time_limit_sec {
                        "TIME_LIMIT_EXCEEDED".to_string()
                    } else {
                        "PART_NEVER_FITS_SHEET".to_string()
                    },
                });
                continue;
            }

            all_candidates.sort_by(|a, b| {
                let ra = rotation_contexts[a.rotation_idx].rotation_rank;
                let rb = rotation_contexts[b.rotation_idx].rotation_rank;
                a.ty
                    .cmp(&b.ty)
                    .then(a.tx.cmp(&b.tx))
                    .then(ra.cmp(&rb))
                    .then(a.cfr_component_rank.cmp(&b.cfr_component_rank))
                    .then(
                        a.vertex_rank_within_component
                            .cmp(&b.vertex_rank_within_component),
                    )
                    .then(a.nudge_rank.cmp(&b.nudge_rank))
            });

            let mut deduped: Vec<Candidate> = Vec::new();
            let mut seen = std::collections::BTreeSet::new();
            for candidate in all_candidates {
                if seen.insert((candidate.tx, candidate.ty)) {
                    deduped.push(candidate);
                    if deduped.len() >= MAX_CANDIDATES_PER_PART {
                        break;
                    }
                }
            }

            let mut placed_this_instance = false;
            for candidate in deduped {
                if started_at.elapsed().as_secs() >= time_limit_sec {
                    break;
                }
                let ctx = &rotation_contexts[candidate.rotation_idx];
                let candidate_poly = translate_polygon(&ctx.moving_polygon, candidate.tx, candidate.ty);
                if can_place(&candidate_poly, bin_polygon, &placed_state) {
                    let candidate_aabb = aabb_from_polygon64(&candidate_poly);
                    placed_state.insert(PlacedPart {
                        inflated_polygon: candidate_poly.clone(),
                        aabb: candidate_aabb,
                    });
                    placed_for_nfp.push(PlacedPart {
                        inflated_polygon: candidate_poly,
                        aabb: candidate_aabb,
                    });
                    placed.push(super::blf::PlacedItem {
                        part_id: part.id.clone(),
                        instance,
                        sheet: 0,
                        x_mm: i64_to_mm(candidate.tx),
                        y_mm: i64_to_mm(candidate.ty),
                        rotation_deg: ctx.rotation_deg,
                    });
                    placed_this_instance = true;
                    break;
                }
            }

            if !placed_this_instance {
                unplaced.push(super::blf::UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: if started_at.elapsed().as_secs() >= time_limit_sec {
                        "TIME_LIMIT_EXCEEDED".to_string()
                    } else {
                        "PART_NEVER_FITS_SHEET".to_string()
                    },
                });
            }
        }
    }

    PlacementResult { placed, unplaced }
}

fn compute_nfp_lib(placed_polygon: &Polygon64, moving_polygon: &Polygon64) -> Option<LibPolygon64> {
    let placed_lib = to_lib_polygon(placed_polygon);
    let moving_lib = to_lib_polygon(moving_polygon);
    if is_convex(&placed_polygon.outer) && is_convex(&moving_polygon.outer) {
        compute_convex_nfp(&placed_lib, &moving_lib).ok()
    } else {
        compute_concave_nfp_default(&placed_lib, &moving_lib).ok()
    }
}

fn append_candidates(
    out: &mut Vec<Candidate>,
    rotation_idx: usize,
    cfr_components: &[Polygon64],
    ctx: &RotationContext,
) {
    for (component_rank, component) in cfr_components.iter().enumerate() {
        for (vertex_rank, vertex) in component
            .outer
            .iter()
            .take(MAX_VERTICES_PER_COMPONENT)
            .enumerate()
        {
            if !inside_ifp(vertex.x, vertex.y, &ctx.ifp) {
                continue;
            }
            out.push(Candidate {
                tx: vertex.x,
                ty: vertex.y,
                rotation_idx,
                cfr_component_rank: component_rank,
                vertex_rank_within_component: vertex_rank,
                nudge_rank: 0,
            });

            let mut nudge_rank = 1_usize;
            for step in NUDGE_STEPS {
                for (dx, dy) in NUDGE_DIRS {
                    let tx = vertex.x.saturating_add(dx.saturating_mul(step));
                    let ty = vertex.y.saturating_add(dy.saturating_mul(step));
                    if !inside_ifp(tx, ty, &ctx.ifp) {
                        nudge_rank += 1;
                        continue;
                    }
                    out.push(Candidate {
                        tx,
                        ty,
                        rotation_idx,
                        cfr_component_rank: component_rank,
                        vertex_rank_within_component: vertex_rank,
                        nudge_rank,
                    });
                    nudge_rank += 1;
                }
            }
        }
    }
}

fn inside_ifp(tx: i64, ty: i64, ifp: &IfpRect) -> bool {
    tx >= ifp.tx.min && tx <= ifp.tx.max && ty >= ifp.ty.min && ty <= ifp.ty.max
}

fn normalize_polygon_min_xy(poly: &Polygon64) -> Polygon64 {
    normalize_polygon_min_xy_with_offset(poly).0
}

fn normalize_polygon_min_xy_with_offset(poly: &Polygon64) -> (Polygon64, i64, i64) {
    let mut min_x = i64::MAX;
    let mut min_y = i64::MAX;
    for point in &poly.outer {
        min_x = min_x.min(point.x);
        min_y = min_y.min(point.y);
    }
    if min_x == i64::MAX || min_y == i64::MAX {
        return (poly.clone(), 0, 0);
    }
    (translate_polygon(poly, -min_x, -min_y), min_x, min_y)
}

fn rotate_polygon(poly: &Polygon64, rotation_deg: i32) -> Polygon64 {
    Polygon64 {
        outer: poly
            .outer
            .iter()
            .map(|p| rotate_point(*p, rotation_deg))
            .collect(),
        holes: poly
            .holes
            .iter()
            .map(|hole| hole.iter().map(|p| rotate_point(*p, rotation_deg)).collect())
            .collect(),
    }
}

fn rotate_point(p: Point64, rotation_deg: i32) -> Point64 {
    let norm = normalize_deg(rotation_deg);
    match norm {
        0 => p,
        90 => Point64 { x: -p.y, y: p.x },
        180 => Point64 { x: -p.x, y: -p.y },
        270 => Point64 { x: p.y, y: -p.x },
        _ => {
            let c = COS_Q[norm] as i128;
            let s = SIN_Q[norm] as i128;
            let x = p.x as i128;
            let y = p.y as i128;
            Point64 {
                x: round_div_i128((x * c) - (y * s), TRIG_SCALE_I128),
                y: round_div_i128((x * s) + (y * c), TRIG_SCALE_I128),
            }
        }
    }
}

fn translate_polygon(poly: &Polygon64, tx: i64, ty: i64) -> Polygon64 {
    Polygon64 {
        outer: poly
            .outer
            .iter()
            .map(|p| Point64 {
                x: p.x + tx,
                y: p.y + ty,
            })
            .collect(),
        holes: poly
            .holes
            .iter()
            .map(|hole| {
                hole.iter()
                    .map(|p| Point64 {
                        x: p.x + tx,
                        y: p.y + ty,
                    })
                    .collect()
            })
            .collect(),
    }
}

fn to_lib_polygon(poly: &Polygon64) -> LibPolygon64 {
    LibPolygon64 {
        outer: poly
            .outer
            .iter()
            .map(|p| LibPoint64 { x: p.x, y: p.y })
            .collect(),
        holes: poly
            .holes
            .iter()
            .map(|hole| hole.iter().map(|p| LibPoint64 { x: p.x, y: p.y }).collect())
            .collect(),
    }
}

fn from_lib_polygon(poly: &LibPolygon64) -> Polygon64 {
    Polygon64 {
        outer: poly
            .outer
            .iter()
            .map(|p| Point64 { x: p.x, y: p.y })
            .collect(),
        holes: poly
            .holes
            .iter()
            .map(|hole| hole.iter().map(|p| Point64 { x: p.x, y: p.y }).collect())
            .collect(),
    }
}

#[cfg(test)]
mod tests {
    use std::time::Instant;

    use crate::placement::blf::bbox_area;
    use nesting_engine::nfp::cache::NfpCache;

    use super::{InflatedPartSpec, nfp_place};
    use crate::geometry::{
        scale::mm_to_i64,
        types::{Point64, Polygon64},
    };

    fn rect(w_mm: f64, h_mm: f64) -> Polygon64 {
        Polygon64 {
            outer: vec![
                Point64 {
                    x: mm_to_i64(0.0),
                    y: mm_to_i64(0.0),
                },
                Point64 {
                    x: mm_to_i64(w_mm),
                    y: mm_to_i64(0.0),
                },
                Point64 {
                    x: mm_to_i64(w_mm),
                    y: mm_to_i64(h_mm),
                },
                Point64 {
                    x: mm_to_i64(0.0),
                    y: mm_to_i64(h_mm),
                },
            ],
            holes: Vec::new(),
        }
    }

    fn part(id: &str, quantity: usize, w: f64, h: f64, rots: &[i32]) -> InflatedPartSpec {
        let poly = rect(w, h);
        InflatedPartSpec {
            id: id.to_string(),
            quantity,
            allowed_rotations_deg: rots.to_vec(),
            nominal_bbox_area: bbox_area(&poly.outer),
            inflated_polygon: poly,
        }
    }

    #[test]
    fn basic_places_at_least_one_part() {
        let bin = rect(80.0, 60.0);
        let parts = vec![
            part("a", 1, 35.0, 20.0, &[0]),
            part("b", 1, 30.0, 20.0, &[0]),
            part("c", 1, 20.0, 20.0, &[0]),
        ];
        let mut cache = NfpCache::new();
        let out = nfp_place(&parts, &bin, 1.0, 30, Instant::now(), &mut cache);
        assert!(!out.placed.is_empty());
    }

    #[test]
    fn wrapper_contract_case_keeps_going_after_unplaceable_first() {
        let bin = rect(60.0, 40.0);
        let parts = vec![part("big", 1, 120.0, 80.0, &[0]), part("small", 1, 20.0, 20.0, &[0])];
        let mut cache = NfpCache::new();
        let out = nfp_place(&parts, &bin, 1.0, 30, Instant::now(), &mut cache);
        assert!(
            out.placed.iter().any(|p| p.part_id == "small"),
            "later feasible part must still be placed"
        );
    }

    #[test]
    fn deterministic_for_same_input() {
        let bin = rect(100.0, 100.0);
        let parts = vec![
            part("p1", 2, 30.0, 20.0, &[0, 90]),
            part("p2", 2, 20.0, 10.0, &[0, 90]),
        ];
        let mut cache_a = NfpCache::new();
        let mut cache_b = NfpCache::new();
        let a = nfp_place(&parts, &bin, 1.0, 30, Instant::now(), &mut cache_a);
        let b = nfp_place(&parts, &bin, 1.0, 30, Instant::now(), &mut cache_b);
        assert_eq!(a.placed, b.placed);
        assert_eq!(a.unplaced, b.unplaced);
    }
}
