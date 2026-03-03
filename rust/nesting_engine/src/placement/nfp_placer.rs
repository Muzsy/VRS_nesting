use serde::Serialize;

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
use crate::multi_bin::greedy::{PartOrderPolicy, StopPolicy};
use nesting_engine::nfp::{
    cache::{NfpCache, NfpCacheKey, shape_id},
    cfr::{CfrStatsV1, compute_cfr_with_stats},
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

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct NfpPlacerStatsV1 {
    pub nfp_cache_hits: u64,
    pub nfp_cache_misses: u64,
    pub nfp_cache_entries_end: u64,
    pub nfp_compute_calls: u64,
    pub cfr_calls: u64,
    pub cfr_union_calls: u64,
    pub cfr_diff_calls: u64,
    pub candidates_before_dedupe_total: u64,
    pub candidates_after_dedupe_total: u64,
    pub candidates_after_cap_total: u64,
    pub cap_applied_count: u64,
    pub effective_placer: String,
    pub sheets_used: u64,
}

impl Default for NfpPlacerStatsV1 {
    fn default() -> Self {
        Self {
            nfp_cache_hits: 0,
            nfp_cache_misses: 0,
            nfp_cache_entries_end: 0,
            nfp_compute_calls: 0,
            cfr_calls: 0,
            cfr_union_calls: 0,
            cfr_diff_calls: 0,
            candidates_before_dedupe_total: 0,
            candidates_after_dedupe_total: 0,
            candidates_after_cap_total: 0,
            cap_applied_count: 0,
            effective_placer: String::new(),
            sheets_used: 0,
        }
    }
}

impl NfpPlacerStatsV1 {
    pub fn merge_from(&mut self, other: &Self) {
        self.nfp_cache_hits = self.nfp_cache_hits.saturating_add(other.nfp_cache_hits);
        self.nfp_cache_misses = self
            .nfp_cache_misses
            .saturating_add(other.nfp_cache_misses);
        self.nfp_compute_calls = self.nfp_compute_calls.saturating_add(other.nfp_compute_calls);
        self.cfr_calls = self.cfr_calls.saturating_add(other.cfr_calls);
        self.cfr_union_calls = self.cfr_union_calls.saturating_add(other.cfr_union_calls);
        self.cfr_diff_calls = self.cfr_diff_calls.saturating_add(other.cfr_diff_calls);
        self.candidates_before_dedupe_total = self
            .candidates_before_dedupe_total
            .saturating_add(other.candidates_before_dedupe_total);
        self.candidates_after_dedupe_total = self
            .candidates_after_dedupe_total
            .saturating_add(other.candidates_after_dedupe_total);
        self.candidates_after_cap_total = self
            .candidates_after_cap_total
            .saturating_add(other.candidates_after_cap_total);
        self.cap_applied_count = self.cap_applied_count.saturating_add(other.cap_applied_count);

        if other.nfp_cache_entries_end > 0 {
            self.nfp_cache_entries_end = other.nfp_cache_entries_end;
        }
        if !other.effective_placer.is_empty() {
            self.effective_placer = other.effective_placer.clone();
        }
        if other.sheets_used > 0 {
            self.sheets_used = other.sheets_used;
        }
    }

    pub fn add_assign(&mut self, other: &Self) {
        self.merge_from(other);
    }
}

#[derive(Debug)]
struct DedupedCandidates {
    after_cap: Vec<Candidate>,
    unique_count: usize,
    cap_applied: bool,
}

pub fn nfp_place(
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
    _grid_step_mm: f64,
    stop: &mut StopPolicy,
    cache: &mut NfpCache,
    stats: &mut NfpPlacerStatsV1,
    order_policy: PartOrderPolicy,
) -> PlacementResult {
    let ordered = order_parts_for_policy(parts, order_policy);

    let bin_aabb = aabb_from_polygon64(bin_polygon);
    let mut placed_state = PlacedIndex::new();
    let mut placed_for_nfp: Vec<PlacedPart> = Vec::new();
    let mut placed = Vec::new();
    let mut unplaced = Vec::new();

    for (part_idx, part) in ordered.iter().enumerate() {
        for instance in 0..part.quantity {
            if stop.consume(1) {
                if !stop.is_timed_out() {
                    stop.mark_timed_out();
                }
                append_timeout_unplaced_for_remaining(&ordered, part_idx, instance, &mut unplaced);
                return PlacementResult { placed, unplaced };
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
                        stats.nfp_cache_hits = stats.nfp_cache_hits.saturating_add(1);
                        let cached_world = translate_polygon(
                            &from_lib_polygon(cached_rel),
                            placed_anchor_x,
                            placed_anchor_y,
                        );
                        nfp_polys.push(to_lib_polygon(&cached_world));
                        continue;
                    }
                    stats.nfp_cache_misses = stats.nfp_cache_misses.saturating_add(1);
                    stats.nfp_compute_calls = stats.nfp_compute_calls.saturating_add(1);

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

                if stop.consume(1) {
                    if !stop.is_timed_out() {
                        stop.mark_timed_out();
                    }
                    append_timeout_unplaced_for_remaining(&ordered, part_idx, instance, &mut unplaced);
                    return PlacementResult { placed, unplaced };
                }

                stats.cfr_calls = stats.cfr_calls.saturating_add(1);
                let mut cfr_stats = CfrStatsV1::default();
                let cfr_components: Vec<Polygon64> = compute_cfr_with_stats(
                    &ifp.polygon,
                    &nfp_polys,
                    &mut cfr_stats,
                )
                    .iter()
                    .map(from_lib_polygon)
                    .collect();
                stats.cfr_union_calls = stats
                    .cfr_union_calls
                    .saturating_add(cfr_stats.cfr_union_calls);
                stats.cfr_diff_calls = stats.cfr_diff_calls.saturating_add(cfr_stats.cfr_diff_calls);
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
                if stop.should_stop() {
                    if !stop.is_timed_out() {
                        stop.mark_timed_out();
                    }
                    append_timeout_unplaced_for_remaining(&ordered, part_idx, instance, &mut unplaced);
                    return PlacementResult { placed, unplaced };
                }
                unplaced.push(super::blf::UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: "PART_NEVER_FITS_SHEET".to_string(),
                });
                continue;
            }

            stats.candidates_before_dedupe_total = stats
                .candidates_before_dedupe_total
                .saturating_add(all_candidates.len() as u64);
            let deduped = sort_and_dedupe_candidates(all_candidates, &rotation_contexts);
            stats.candidates_after_dedupe_total = stats
                .candidates_after_dedupe_total
                .saturating_add(deduped.unique_count as u64);
            stats.candidates_after_cap_total = stats
                .candidates_after_cap_total
                .saturating_add(deduped.after_cap.len() as u64);
            if deduped.cap_applied {
                stats.cap_applied_count = stats.cap_applied_count.saturating_add(1);
            }

            let mut placed_this_instance = false;
            for candidate in deduped.after_cap {
                if stop.consume(1) {
                    if !stop.is_timed_out() {
                        stop.mark_timed_out();
                    }
                    append_timeout_unplaced_for_remaining(&ordered, part_idx, instance, &mut unplaced);
                    return PlacementResult { placed, unplaced };
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
                if stop.should_stop() {
                    if !stop.is_timed_out() {
                        stop.mark_timed_out();
                    }
                    append_timeout_unplaced_for_remaining(&ordered, part_idx, instance, &mut unplaced);
                    return PlacementResult { placed, unplaced };
                }
                unplaced.push(super::blf::UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: "PART_NEVER_FITS_SHEET".to_string(),
                });
            }
        }
    }

    PlacementResult { placed, unplaced }
}

fn order_parts_for_policy(
    parts: &[InflatedPartSpec],
    order_policy: PartOrderPolicy,
) -> Vec<InflatedPartSpec> {
    let mut ordered = parts.to_vec();
    if order_policy == PartOrderPolicy::ByArea {
        ordered.sort_by(|a, b| {
            b.nominal_bbox_area
                .cmp(&a.nominal_bbox_area)
                .then_with(|| a.id.cmp(&b.id))
        });
    }
    ordered
}

fn append_timeout_unplaced_for_remaining(
    ordered: &[InflatedPartSpec],
    part_idx: usize,
    instance_idx: usize,
    out: &mut Vec<super::blf::UnplacedItem>,
) {
    for (idx, part) in ordered.iter().enumerate().skip(part_idx) {
        let start_instance = if idx == part_idx { instance_idx } else { 0 };
        for instance in start_instance..part.quantity {
            out.push(super::blf::UnplacedItem {
                part_id: part.id.clone(),
                instance,
                reason: "TIME_LIMIT_EXCEEDED".to_string(),
            });
        }
    }
}

fn sort_and_dedupe_candidates(
    mut all_candidates: Vec<Candidate>,
    rotation_contexts: &[RotationContext],
) -> DedupedCandidates {
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
    let mut unique_count = 0_usize;
    for candidate in all_candidates {
        if seen.insert((candidate.tx, candidate.ty, candidate.rotation_idx)) {
            unique_count += 1;
            if deduped.len() < MAX_CANDIDATES_PER_PART {
                deduped.push(candidate);
            }
        }
    }
    DedupedCandidates {
        after_cap: deduped,
        unique_count,
        cap_applied: unique_count > MAX_CANDIDATES_PER_PART,
    }
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

    use crate::multi_bin::greedy::{PartOrderPolicy, StopPolicy};
    use crate::placement::blf::bbox_area;
    use nesting_engine::nfp::cache::NfpCache;
    use nesting_engine::nfp::ifp::{IfpRect, TranslationRange};
    use nesting_engine::geometry::types::{Point64 as LibPoint64, Polygon64 as LibPolygon64};

    use super::{
        Candidate, InflatedPartSpec, NfpPlacerStatsV1, RotationContext, nfp_place,
        order_parts_for_policy,
        sort_and_dedupe_candidates,
    };
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

    fn lib_rect_i64(w: i64, h: i64) -> LibPolygon64 {
        LibPolygon64 {
            outer: vec![
                LibPoint64 { x: 0, y: 0 },
                LibPoint64 { x: w, y: 0 },
                LibPoint64 { x: w, y: h },
                LibPoint64 { x: 0, y: h },
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
        let mut stats = NfpPlacerStatsV1::default();
        let mut stop = StopPolicy::wall_clock_for_test(30, Instant::now());
        let out = nfp_place(
            &parts,
            &bin,
            1.0,
            &mut stop,
            &mut cache,
            &mut stats,
            PartOrderPolicy::ByArea,
        );
        assert!(!out.placed.is_empty());
    }

    #[test]
    fn wrapper_contract_case_keeps_going_after_unplaceable_first() {
        let bin = rect(60.0, 40.0);
        let parts = vec![part("big", 1, 120.0, 80.0, &[0]), part("small", 1, 20.0, 20.0, &[0])];
        let mut cache = NfpCache::new();
        let mut stats = NfpPlacerStatsV1::default();
        let mut stop = StopPolicy::wall_clock_for_test(30, Instant::now());
        let out = nfp_place(
            &parts,
            &bin,
            1.0,
            &mut stop,
            &mut cache,
            &mut stats,
            PartOrderPolicy::ByArea,
        );
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
        let mut stats_a = NfpPlacerStatsV1::default();
        let mut stats_b = NfpPlacerStatsV1::default();
        let mut stop_a = StopPolicy::wall_clock_for_test(30, Instant::now());
        let a = nfp_place(
            &parts,
            &bin,
            1.0,
            &mut stop_a,
            &mut cache_a,
            &mut stats_a,
            PartOrderPolicy::ByArea,
        );
        let mut stop_b = StopPolicy::wall_clock_for_test(30, Instant::now());
        let b = nfp_place(
            &parts,
            &bin,
            1.0,
            &mut stop_b,
            &mut cache_b,
            &mut stats_b,
            PartOrderPolicy::ByArea,
        );
        assert_eq!(a.placed, b.placed);
        assert_eq!(a.unplaced, b.unplaced);
    }

    #[test]
    fn nfp_budget_stop_is_deterministic() {
        let bin = rect(120.0, 100.0);
        let parts = vec![
            part("p1", 3, 40.0, 30.0, &[0, 90]),
            part("p2", 4, 20.0, 20.0, &[0, 90]),
            part("p3", 4, 18.0, 12.0, &[0, 90]),
        ];

        let mut cache_a = NfpCache::new();
        let mut cache_b = NfpCache::new();
        let mut stats_a = NfpPlacerStatsV1::default();
        let mut stats_b = NfpPlacerStatsV1::default();
        let mut stop_a = StopPolicy::work_budget_for_test(30, 16, 60, Instant::now());
        let mut stop_b = StopPolicy::work_budget_for_test(30, 16, 60, Instant::now());

        let a = nfp_place(
            &parts,
            &bin,
            1.0,
            &mut stop_a,
            &mut cache_a,
            &mut stats_a,
            PartOrderPolicy::ByArea,
        );
        let b = nfp_place(
            &parts,
            &bin,
            1.0,
            &mut stop_b,
            &mut cache_b,
            &mut stats_b,
            PartOrderPolicy::ByArea,
        );

        assert_eq!(a.placed, b.placed);
        assert_eq!(a.unplaced, b.unplaced);
        assert!(
            a.unplaced.iter().any(|u| u.reason == "TIME_LIMIT_EXCEEDED"),
            "test budget must trigger timeout"
        );
    }

    #[test]
    fn order_policy_by_input_order_preserves_input_order() {
        let parts = vec![
            part("small", 1, 8.0, 8.0, &[0]),
            part("large", 1, 20.0, 20.0, &[0]),
            part("medium", 1, 15.0, 10.0, &[0]),
        ];

        let by_input = order_parts_for_policy(&parts, PartOrderPolicy::ByInputOrder);
        let by_area = order_parts_for_policy(&parts, PartOrderPolicy::ByArea);

        let by_input_ids: Vec<&str> = by_input.iter().map(|p| p.id.as_str()).collect();
        let by_area_ids: Vec<&str> = by_area.iter().map(|p| p.id.as_str()).collect();

        assert_eq!(by_input_ids, vec!["small", "large", "medium"]);
        assert_eq!(by_area_ids, vec!["large", "medium", "small"]);
    }

    #[test]
    fn dedupe_keeps_same_xy_for_different_rotations() {
        let dummy_ifp = IfpRect {
            polygon: lib_rect_i64(10, 10),
            tx: TranslationRange { min: 0, max: 10 },
            ty: TranslationRange { min: 0, max: 10 },
        };
        let rotation_contexts = vec![
            RotationContext {
                rotation_deg: 0,
                rotation_rank: 0,
                moving_polygon: rect(2.0, 2.0),
                ifp: dummy_ifp.clone(),
            },
            RotationContext {
                rotation_deg: 90,
                rotation_rank: 1,
                moving_polygon: rect(2.0, 2.0),
                ifp: dummy_ifp,
            },
        ];
        let candidates = vec![
            Candidate {
                tx: 100,
                ty: 200,
                rotation_idx: 0,
                cfr_component_rank: 0,
                vertex_rank_within_component: 0,
                nudge_rank: 0,
            },
            Candidate {
                tx: 100,
                ty: 200,
                rotation_idx: 1,
                cfr_component_rank: 0,
                vertex_rank_within_component: 0,
                nudge_rank: 0,
            },
        ];

        let out = sort_and_dedupe_candidates(candidates, &rotation_contexts);
        assert_eq!(
            out.after_cap.len(),
            2,
            "different rotations at same tx/ty must survive dedupe"
        );
        assert_eq!(out.after_cap[0].rotation_idx, 0);
        assert_eq!(out.after_cap[1].rotation_idx, 1);
    }
}
