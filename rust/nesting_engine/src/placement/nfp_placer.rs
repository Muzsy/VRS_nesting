use serde::Serialize;
use std::time::Instant;

use crate::feasibility::{aabb::aabb_from_polygon64, can_place, narrow::PlacedIndex, PlacedPart};
use crate::geometry::{
    scale::i64_to_mm,
    trig_lut::{normalize_deg, round_div_i128, COS_Q, SIN_Q, TRIG_SCALE_I128},
    types::{is_convex, Point64, Polygon64},
};
use crate::multi_bin::greedy::{PartOrderPolicy, StopPolicy};
use nesting_engine::geometry::types::{Point64 as LibPoint64, Polygon64 as LibPolygon64};
use nesting_engine::nfp::{
    cache::{shape_id, NfpCache, NfpCacheKey},
    cfr::{compute_cfr_with_stats, CfrStatsV1},
    ifp::{compute_ifp_rect, IfpRect},
    provider::{create_nfp_provider, NfpKernel, NfpProvider, NfpProviderConfig},
};

use super::blf::InflatedPartSpec;
use super::PlacementResult;

// T06e: NFP Runtime Diagnostic — global stats accumulated across all placements
#[derive(Debug, Clone, Default)]
pub struct NfpRuntimeDiagV1 {
    /// Total wall-clock time in nfp_place (ms)
    pub total_runtime_ms: u64,
    /// Total NFP requests (cache miss + compute)
    pub nfp_request_count: u64,
    /// Cache hits
    pub nfp_cache_hit_count: u64,
    /// Cache misses (triggers provider compute)
    pub nfp_cache_miss_count: u64,
    /// Provider compute invocations
    pub nfp_provider_compute_count: u64,
    /// Total time spent in provider compute (ms)
    pub nfp_provider_compute_ms_total: u64,
    /// Max single provider compute time (ms)
    pub nfp_provider_compute_ms_max: u64,
    /// CFR union time total (ms) — sum of all union_time_ms
    pub cfr_union_ms_total: f64,
    /// CFR diff time total (ms) — sum of all diff_time_ms
    pub cfr_diff_ms_total: f64,
    /// CFR calls count
    pub cfr_calls: u64,
    /// Total candidates generated (before dedup)
    pub candidate_generated_count: u64,
    /// Total candidates after dedup
    pub candidate_after_dedup_count: u64,
    /// Total can_place checks
    pub can_place_check_count: u64,
    /// Total time in can_place checks (ms)
    pub can_place_ms_total: u64,
    /// BLF fallback count (hybrid gating)
    pub blf_fallback_count: u64,
    /// Candidate-driven: CFR fallback count
    pub cfr_fallback_count: u64,
    /// Candidate-driven: fast path no candidate count
    pub cfr_fallback_no_candidate_count: u64,
    /// Candidate-driven: fast path no feasible count
    pub cfr_fallback_no_feasible_count: u64,
    /// Placed count
    pub placed_count: u64,
    /// Unplaced count
    pub unplaced_count: u64,
    /// Sheets used
    pub sheet_count: u64,
}

impl NfpRuntimeDiagV1 {
    pub fn emit_summary(&self) {
        eprintln!(
            "NFP_RUNTIME_DIAG_V1 \
             total_runtime_ms={} \
             nfp_requests={} \
             cache_hits={} cache_misses={} \
             provider_computes={} provider_ms_total={} provider_ms_max={} \
             cfr_calls={} cfr_union_ms_total={:.1} cfr_diff_ms_total={:.1} \
             candidates_gen={} candidates_dedup={} \
             can_place_checks={} can_place_ms_total={} \
             blf_fallback={} cfr_fallback={} \
             placed={} unplaced={} sheets={}",
            self.total_runtime_ms,
            self.nfp_request_count,
            self.nfp_cache_hit_count,
            self.nfp_cache_miss_count,
            self.nfp_provider_compute_count,
            self.nfp_provider_compute_ms_total,
            self.nfp_provider_compute_ms_max,
            self.cfr_calls,
            self.cfr_union_ms_total,
            self.cfr_diff_ms_total,
            self.candidate_generated_count,
            self.candidate_after_dedup_count,
            self.can_place_check_count,
            self.can_place_ms_total,
            self.blf_fallback_count,
            self.cfr_fallback_count,
            self.placed_count,
            self.unplaced_count,
            self.sheet_count,
        );
    }
}

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

// T06d: Candidate-driven fast-path limits
const MAX_NFP_VERTEX_CANDIDATES_PER_ROTATION: usize = 256;
const MAX_NFP_MIDPOINT_CANDIDATES_PER_ROTATION: usize = 128;
const MAX_PLACED_ANCHOR_CANDIDATES_PER_ROTATION: usize = 64;

/// Returns true when NESTING_ENGINE_CANDIDATE_DRIVEN=1
fn is_candidate_driven_enabled() -> bool {
    std::env::var("NESTING_ENGINE_CANDIDATE_DRIVEN").as_deref() == Ok("1")
}

/// Returns true when NESTING_ENGINE_CANDIDATE_ALLOW_CFR_FALLBACK=1
fn is_cfr_fallback_allowed() -> bool {
    std::env::var("NESTING_ENGINE_CANDIDATE_ALLOW_CFR_FALLBACK").as_deref() == Ok("1")
}

/// Returns true when NESTING_ENGINE_CANDIDATE_DIAG=1
fn is_candidate_diag_enabled() -> bool {
    std::env::var("NESTING_ENGINE_CANDIDATE_DIAG").as_deref() == Ok("1")
}

#[derive(Debug, Clone)]
struct RotationContext {
    rotation_deg: i32,
    rotation_rank: usize,
    moving_polygon: Polygon64,
    ifp: IfpRect,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub(crate) enum CandidateSource {
    /// IFP corners / BLF-like
    IfpCorner = 0,
    /// NFP polygon vertices
    NfpVertex = 1,
    /// NFP edge midpoints
    NfpMidpoint = 2,
    /// Placed part anchors / bbox corners
    PlacedAnchor = 3,
    /// Nudged variant of another candidate
    Nudge = 4,
}

#[derive(Debug, Clone, Copy)]
struct Candidate {
    tx: i64,
    ty: i64,
    rotation_idx: usize,
    cfr_component_rank: usize,
    vertex_rank_within_component: usize,
    nudge_rank: usize,
    source: CandidateSource,
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
    pub actual_nfp_kernel: String, // T05z: which NFP kernel was actually used
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
            actual_nfp_kernel: resolve_nfp_kernel_name(),
        }
    }
}

impl NfpPlacerStatsV1 {
    pub fn merge_from(&mut self, other: &Self) {
        self.nfp_cache_hits = self.nfp_cache_hits.saturating_add(other.nfp_cache_hits);
        self.nfp_cache_misses = self.nfp_cache_misses.saturating_add(other.nfp_cache_misses);
        self.nfp_compute_calls = self
            .nfp_compute_calls
            .saturating_add(other.nfp_compute_calls);
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
        self.cap_applied_count = self
            .cap_applied_count
            .saturating_add(other.cap_applied_count);

        if other.nfp_cache_entries_end > 0 {
            self.nfp_cache_entries_end = other.nfp_cache_entries_end;
        }
        if !other.effective_placer.is_empty() {
            self.effective_placer = other.effective_placer.clone();
        }
        if other.sheets_used > 0 {
            self.sheets_used = other.sheets_used;
        }
        if !other.actual_nfp_kernel.is_empty() {
            self.actual_nfp_kernel = other.actual_nfp_kernel.clone();
        }
    }

    pub fn add_assign(&mut self, other: &Self) {
        self.merge_from(other);
    }
}

// T06d: Candidate-driven fast-path diagnostics
#[derive(Debug, Clone, Default)]
pub struct CandidateDrivenStats {
    pub ifp_corner_candidates: u64,
    pub nfp_vertex_candidates: u64,
    pub nfp_edge_midpoint_candidates: u64,
    pub placed_anchor_candidates: u64,
    pub nudge_candidates: u64,
    pub total_generated: u64,
    pub total_after_dedup: u64,
    pub can_place_checks: u64,
    pub accepted: u64,
    pub rejected_by_can_place: u64,
    pub cfr_fallback_count: u64,
    pub fast_path_no_candidate_count: u64,
    pub fast_path_no_feasible_count: u64,
    pub runtime_candidate_gen_ms: u64,
    pub runtime_can_place_ms: u64,
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
    let runtime_diag_enabled = std::env::var("NESTING_ENGINE_NFP_RUNTIME_DIAG").as_deref() == Ok("1");
    let overall_start = if runtime_diag_enabled { Some(Instant::now()) } else { None };
    let mut runtime_diag = NfpRuntimeDiagV1::default();

    let ordered = order_parts_for_policy(parts, order_policy);
    // T05z: resolve kernel once so cache key matches the provider used in compute_nfp_lib.
    let nfp_kernel = resolve_nfp_kernel();

    let bin_aabb = aabb_from_polygon64(bin_polygon);
    let mut placed_state = PlacedIndex::new();
    let mut placed_for_nfp: Vec<PlacedPart> = Vec::new();
    let mut placed = Vec::new();
    let mut unplaced = Vec::new();

    // T06d: candidate-driven stats — only populated when feature flag is set
    let mut cd_stats = CandidateDrivenStats::default();
    let candidate_driven = is_candidate_driven_enabled();

    for (part_idx, part) in ordered.iter().enumerate() {
        for instance in 0..part.quantity {
            if stop.consume(1) {
                if !stop.is_timed_out() {
                    stop.mark_timed_out();
                }
                append_timeout_unplaced_for_remaining(&ordered, part_idx, instance, &mut unplaced);
                if candidate_driven && is_candidate_diag_enabled() {
                    eprintln!("[CANDIDATE_DIAG] {:?}", cd_stats);
                }
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

                // T06d: candidate-driven fast-path — generate candidates WITHOUT full CFR union
                if candidate_driven {
                    let rotation_idx = rotation_contexts.len();

                    let cd_gen_start = Instant::now();
                    let nfp_polys = collect_nfp_polys_for_rotation(
                        rotation_deg,
                        nfp_kernel,
                        cache,
                        stats,
                        &moving,
                        &moving_aabb,
                        &placed_for_nfp,
                    );

                    if nfp_polys.is_empty() && !placed_for_nfp.is_empty() {
                        // NFP failed but there are placed parts — can't proceed
                        continue;
                    }

                    // Push before candidate generation so context is available
                    rotation_contexts.push(RotationContext {
                        rotation_deg,
                        rotation_rank,
                        moving_polygon: moving,
                        ifp,
                    });

                    let candidates_from_sources = generate_candidate_driven_candidates(
                        rotation_idx,
                        &rotation_contexts[rotation_idx],
                        &placed_state,
                        &placed_for_nfp,
                        &nfp_polys,
                    );
                    cd_stats.ifp_corner_candidates += candidates_from_sources.ifp_corner;
                    cd_stats.nfp_vertex_candidates += candidates_from_sources.nfp_vertex;
                    cd_stats.nfp_edge_midpoint_candidates +=
                        candidates_from_sources.nfp_edge_midpoint;
                    cd_stats.placed_anchor_candidates += candidates_from_sources.placed_anchor;
                    cd_stats.nudge_candidates += candidates_from_sources.nudge;
                    cd_stats.total_generated += candidates_from_sources.total();

                    all_candidates.extend(candidates_from_sources.into_candidates());
                    cd_stats.runtime_candidate_gen_ms = cd_stats
                        .runtime_candidate_gen_ms
                        .saturating_add(cd_gen_start.elapsed().as_millis() as u64);
                    continue; // skip CFR in candidate-driven path
                }

                // === DEFAULT CFR PATH (unchanged when NESTING_ENGINE_CANDIDATE_DRIVEN != 1) ===
                // Push clone so original `moving` and `ifp` stay available for shape_id/eprintln below
                rotation_contexts.push(RotationContext {
                    rotation_deg,
                    rotation_rank,
                    moving_polygon: moving.clone(),
                    ifp: ifp.clone(),
                });
                let rotation_idx = rotation_contexts.len() - 1;

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
                        nfp_kernel,
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

                    eprintln!(
                        "[NFP DIAG] compute_nfp_lib START placed_pts={} placed_convex={} placed_holes={} moving_pts={} moving_convex={} moving_holes={} rotation_deg={}",
                        placed_normalized.outer.len(),
                        is_convex(&placed_normalized.outer),
                        placed_normalized.holes.len(),
                        moving.outer.len(),
                        is_convex(&moving.outer),
                        moving.holes.len(),
                        rotation_deg
                    );
                    let nfp_start = Instant::now();
                    let computed = compute_nfp_lib(&placed_normalized, &moving);
                    eprintln!(
                        "[NFP DIAG] compute_nfp_lib END elapsed_ms={:.2} result={}",
                        nfp_start.elapsed().as_secs_f64() * 1000.0,
                        if computed.is_some() {
                            format!(
                                "Some({}pts)",
                                computed.as_ref().map(|p| p.outer.len()).unwrap_or(0)
                            )
                        } else {
                            "None".to_string()
                        }
                    );
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
                    append_timeout_unplaced_for_remaining(
                        &ordered,
                        part_idx,
                        instance,
                        &mut unplaced,
                    );
                    if candidate_driven && is_candidate_diag_enabled() {
                        eprintln!("[CANDIDATE_DIAG] {:?}", cd_stats);
                    }
                    return PlacementResult { placed, unplaced };
                }

                stats.cfr_calls = stats.cfr_calls.saturating_add(1);
                let mut cfr_stats = CfrStatsV1::default();
                eprintln!(
                    "[CFR DIAG] START nfp_polys={} ifp_pts={} rotation_deg={}",
                    nfp_polys.len(),
                    ifp.polygon.outer.len(),
                    rotation_deg
                );
                let cfr_start = Instant::now();
                let cfr_components: Vec<Polygon64> =
                    compute_cfr_with_stats(&ifp.polygon, &nfp_polys, &mut cfr_stats)
                        .iter()
                        .map(from_lib_polygon)
                        .collect();
                eprintln!(
                    "[CFR DIAG] END elapsed_ms={:.2} components={} union_calls={} diff_calls={}",
                    cfr_start.elapsed().as_secs_f64() * 1000.0,
                    cfr_components.len(),
                    cfr_stats.cfr_union_calls,
                    cfr_stats.cfr_diff_calls
                );
                stats.cfr_union_calls = stats
                    .cfr_union_calls
                    .saturating_add(cfr_stats.cfr_union_calls);
                stats.cfr_diff_calls = stats
                    .cfr_diff_calls
                    .saturating_add(cfr_stats.cfr_diff_calls);
                if cfr_components.is_empty() {
                    continue;
                }

                let ctx = &rotation_contexts[rotation_idx];
                append_candidates(&mut all_candidates, rotation_idx, &cfr_components, ctx);
            }

            if all_candidates.is_empty() {
                // T06d: candidate-driven fast-path had no candidates
                if candidate_driven {
                    cd_stats.fast_path_no_candidate_count =
                        cd_stats.fast_path_no_candidate_count.saturating_add(1);
                }
                if stop.should_stop() {
                    if !stop.is_timed_out() {
                        stop.mark_timed_out();
                    }
                    append_timeout_unplaced_for_remaining(
                        &ordered,
                        part_idx,
                        instance,
                        &mut unplaced,
                    );
                    if candidate_driven && is_candidate_diag_enabled() {
                        eprintln!("[CANDIDATE_DIAG] {:?}", cd_stats);
                    }
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

            // T06d: separate dedup ordering for candidate-driven (includes source priority)
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

            // T06d: candidate-driven dedup stats
            let deduped_len = deduped.after_cap.len();
            if candidate_driven {
                cd_stats.total_after_dedup += deduped_len as u64;
            }

            let mut placed_this_instance = false;
            for candidate in deduped.after_cap {
                if stop.consume(1) {
                    if !stop.is_timed_out() {
                        stop.mark_timed_out();
                    }
                    append_timeout_unplaced_for_remaining(
                        &ordered,
                        part_idx,
                        instance,
                        &mut unplaced,
                    );
                    if candidate_driven && is_candidate_diag_enabled() {
                        eprintln!("[CANDIDATE_DIAG] {:?}", cd_stats);
                    }
                    return PlacementResult { placed, unplaced };
                }

                // T06d: candidate-driven diagnostics timing for can_place
                let cp_start = Instant::now();
                let ctx = &rotation_contexts[candidate.rotation_idx];
                let candidate_poly =
                    translate_polygon(&ctx.moving_polygon, candidate.tx, candidate.ty);
                if candidate_driven {
                    cd_stats.can_place_checks = cd_stats.can_place_checks.saturating_add(1);
                }
                if can_place(&candidate_poly, bin_polygon, &placed_state) {
                    if candidate_driven {
                        cd_stats.accepted = cd_stats.accepted.saturating_add(1);
                        cd_stats.runtime_can_place_ms = cd_stats
                            .runtime_can_place_ms
                            .saturating_add(cp_start.elapsed().as_millis() as u64);
                    }
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
                } else if candidate_driven {
                    cd_stats.rejected_by_can_place =
                        cd_stats.rejected_by_can_place.saturating_add(1);
                    cd_stats.runtime_can_place_ms = cd_stats
                        .runtime_can_place_ms
                        .saturating_add(cp_start.elapsed().as_millis() as u64);
                }
            }

            if !placed_this_instance {
                // T06d: candidate-driven fast-path found candidates but none was feasible
                if candidate_driven && deduped_len > 0 {
                    cd_stats.fast_path_no_feasible_count =
                        cd_stats.fast_path_no_feasible_count.saturating_add(1);
                }

                // T06d: CFR fallback — only if explicitly allowed and candidate-driven path failed
                if candidate_driven
                    && is_cfr_fallback_allowed()
                    && !placed_this_instance
                    && !rotation_contexts.is_empty()
                {
                    // CFR fallback path — regenerate with full CFR union
                    let fallback_candidates = compute_cfr_fallback_candidates(
                        &ordered,
                        part_idx,
                        instance,
                        rotation_contexts.len(),
                        nfp_kernel,
                        cache,
                        stats,
                        &placed_for_nfp,
                        &bin_aabb,
                        part,
                    );
                    cd_stats.cfr_fallback_count = cd_stats
                        .cfr_fallback_count
                        .saturating_add(fallback_candidates.0.len() as u64);
                    // Try fallback candidates
                    for candidate in fallback_candidates.0 {
                        if stop.consume(1) {
                            if !stop.is_timed_out() {
                                stop.mark_timed_out();
                            }
                            append_timeout_unplaced_for_remaining(
                                &ordered,
                                part_idx,
                                instance,
                                &mut unplaced,
                            );
                            if is_candidate_diag_enabled() {
                                eprintln!("[CANDIDATE_DIAG] {:?}", cd_stats);
                            }
                            return PlacementResult { placed, unplaced };
                        }
                        let ctx = &rotation_contexts[candidate.rotation_idx];
                        let candidate_poly =
                            translate_polygon(&ctx.moving_polygon, candidate.tx, candidate.ty);
                        cd_stats.can_place_checks = cd_stats.can_place_checks.saturating_add(1);
                        if can_place(&candidate_poly, bin_polygon, &placed_state) {
                            cd_stats.accepted = cd_stats.accepted.saturating_add(1);
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
                        } else {
                            cd_stats.rejected_by_can_place =
                                cd_stats.rejected_by_can_place.saturating_add(1);
                        }
                    }
                    if !placed_this_instance && is_candidate_diag_enabled() {
                        eprintln!(
                            "[CANDIDATE_DIAG] CFR fallback exhausted, part {} instance {} still unplaced",
                            part.id, instance
                        );
                    }
                }

                if !placed_this_instance {
                    if stop.should_stop() {
                        if !stop.is_timed_out() {
                            stop.mark_timed_out();
                        }
                        append_timeout_unplaced_for_remaining(
                            &ordered,
                            part_idx,
                            instance,
                            &mut unplaced,
                        );
                        if candidate_driven && is_candidate_diag_enabled() {
                            eprintln!("[CANDIDATE_DIAG] {:?}", cd_stats);
                        }
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
    }

    if candidate_driven && is_candidate_diag_enabled() {
        eprintln!("[CANDIDATE_DIAG] {:?}", cd_stats);
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
        a.ty.cmp(&b.ty)
            .then(a.tx.cmp(&b.tx))
            .then(ra.cmp(&rb))
            .then(a.source.cmp(&b.source))
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

/// Resolves NFP kernel from NESTING_ENGINE_NFP_KERNEL env variable.
/// Defaults to OldConcave if not set or invalid.
fn resolve_nfp_kernel() -> NfpKernel {
    match std::env::var("NESTING_ENGINE_NFP_KERNEL")
        .as_deref()
        .map(str::trim)
    {
        Ok("cgal_reference") => NfpKernel::CgalReference,
        Ok("old_concave") | Ok("") | Err(_) => NfpKernel::OldConcave,
        Ok(other) => {
            eprintln!(
                "[NFP PLACER] warning: unknown NESTING_ENGINE_NFP_KERNEL={}, using old_concave",
                other
            );
            NfpKernel::OldConcave
        }
    }
}

/// Human-readable kernel name from env.
fn resolve_nfp_kernel_name() -> String {
    match std::env::var("NESTING_ENGINE_NFP_KERNEL")
        .as_deref()
        .map(str::trim)
    {
        Ok("cgal_reference") => "cgal_reference".to_string(),
        Ok("old_concave") | Ok("") | Err(_) => "old_concave".to_string(),
        Ok(other) => {
            eprintln!(
                "[NFP PLACER] warning: unknown NESTING_ENGINE_NFP_KERNEL={}, using old_concave",
                other
            );
            "old_concave".to_string()
        }
    }
}

/// Default NFP computation — kernel selected by NESTING_ENGINE_NFP_KERNEL env.
/// Behavior is identical to the previous inline dispatch when env is unset.
/// T05z: kernel is now configurable for CGAL reference provider.
fn compute_nfp_lib(placed_polygon: &Polygon64, moving_polygon: &Polygon64) -> Option<LibPolygon64> {
    let placed_lib = to_lib_polygon(placed_polygon);
    let moving_lib = to_lib_polygon(moving_polygon);

    // T05z: resolve kernel from env; create provider dynamically.
    // This is the ONLY change from the original hardcoded OldConcaveProvider.
    let kernel = resolve_nfp_kernel();
    let config = NfpProviderConfig { kernel };
    let provider = match create_nfp_provider(&config) {
        Ok(p) => p,
        Err(e) => {
            eprintln!(
                "[NFP PLACER] failed to create provider for kernel {:?}: {}. \
                 Falling back to old_concave.",
                kernel, e
            );
            // Fall back to old_concave if requested kernel unavailable.
            let fallback_config = NfpProviderConfig {
                kernel: NfpKernel::OldConcave,
            };
            match create_nfp_provider(&fallback_config) {
                Ok(p) => p,
                Err(_) => return None,
            }
        }
    };

    let actual_kernel = provider.kernel();
    match provider.compute(&placed_lib, &moving_lib) {
        Ok(result) => {
            eprintln!(
                "[NFP DIAG] provider={} kernel={:?} elapsed_ms={} result_pts={}",
                provider.kernel_name(),
                actual_kernel,
                result.compute_time_ms,
                result.polygon.outer.len()
            );
            Some(LibPolygon64 {
                outer: result
                    .polygon
                    .outer
                    .iter()
                    .map(|p| LibPoint64 { x: p.x, y: p.y })
                    .collect(),
                holes: result
                    .polygon
                    .holes
                    .iter()
                    .map(|hole| hole.iter().map(|p| LibPoint64 { x: p.x, y: p.y }).collect())
                    .collect(),
            })
        }
        Err(_) => None,
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
                source: CandidateSource::NfpVertex,
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
                        source: CandidateSource::Nudge,
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

// T06d: Collect NFP polygons for a given rotation (used by both default and candidate-driven path)
fn collect_nfp_polys_for_rotation(
    rotation_deg: i32,
    nfp_kernel: NfpKernel,
    cache: &mut NfpCache,
    stats: &mut NfpPlacerStatsV1,
    moving: &Polygon64,
    moving_aabb: &crate::feasibility::aabb::Aabb,
    placed_for_nfp: &[PlacedPart],
) -> Vec<Polygon64> {
    let mut nfp_polys: Vec<Polygon64> = Vec::new();
    if placed_for_nfp.is_empty() {
        return nfp_polys;
    }

    let moving_shape_id = shape_id(&to_lib_polygon(moving));
    let mut nfp_failed = false;

    for placed_part in placed_for_nfp {
        let (placed_normalized, placed_anchor_x, placed_anchor_y) =
            normalize_polygon_min_xy_with_offset(&placed_part.inflated_polygon);
        let key = NfpCacheKey {
            shape_id_a: shape_id(&to_lib_polygon(&placed_normalized)),
            shape_id_b: moving_shape_id,
            rotation_steps_b: normalize_deg(rotation_deg) as i16,
            nfp_kernel,
        };
        if let Some(cached_rel) = cache.get(&key) {
            stats.nfp_cache_hits = stats.nfp_cache_hits.saturating_add(1);
            let cached_world = translate_polygon(
                &from_lib_polygon(cached_rel),
                placed_anchor_x,
                placed_anchor_y,
            );
            nfp_polys.push(cached_world);
            continue;
        }
        stats.nfp_cache_misses = stats.nfp_cache_misses.saturating_add(1);
        stats.nfp_compute_calls = stats.nfp_compute_calls.saturating_add(1);

        let computed = compute_nfp_lib(&placed_normalized, moving);
        match computed {
            Some(poly_rel) => {
                cache.insert(key, poly_rel.clone());
                let world_poly = translate_polygon(
                    &from_lib_polygon(&poly_rel),
                    placed_anchor_x,
                    placed_anchor_y,
                );
                nfp_polys.push(world_poly);
            }
            None => {
                nfp_failed = true;
                break;
            }
        }
    }

    if nfp_failed {
        return Vec::new();
    }
    nfp_polys
}

/// T06d: Candidate generation counts from multiple sources
#[derive(Default)]
struct CandidateSourceCounts {
    ifp_corner: u64,
    nfp_vertex: u64,
    nfp_edge_midpoint: u64,
    placed_anchor: u64,
    nudge: u64,
    candidates: Vec<Candidate>,
}

impl CandidateSourceCounts {
    fn total(&self) -> u64 {
        self.ifp_corner + self.nfp_vertex + self.nfp_edge_midpoint + self.placed_anchor + self.nudge
    }
    fn into_candidates(self) -> Vec<Candidate> {
        self.candidates
    }
}

/// T06d: Generate candidates without building full CFR union.
/// Uses IFP corners, NFP vertices, NFP edge midpoints, placed anchors, and nudge variants.
fn generate_candidate_driven_candidates(
    rotation_idx: usize,
    ctx: &RotationContext,
    placed_state: &PlacedIndex,
    placed_for_nfp: &[PlacedPart],
    nfp_polys: &[Polygon64],
) -> CandidateSourceCounts {
    let mut counts = CandidateSourceCounts::default();

    // A) IFP corners — 4 BLF-like candidates from IFP polygon vertices
    for vertex in ctx.ifp.polygon.outer.iter() {
        if inside_ifp(vertex.x, vertex.y, &ctx.ifp) {
            counts.candidates.push(Candidate {
                tx: vertex.x,
                ty: vertex.y,
                rotation_idx,
                cfr_component_rank: 0,
                vertex_rank_within_component: 0,
                nudge_rank: 0,
                source: CandidateSource::IfpCorner,
            });
            counts.ifp_corner += 1;
        }
    }

    // B) Pairwise NFP vertices (world-coordinate, limited)
    for (poly_rank, nfp_poly) in nfp_polys.iter().enumerate() {
        for (vtx_rank, vertex) in nfp_poly
            .outer
            .iter()
            .take(MAX_NFP_VERTEX_CANDIDATES_PER_ROTATION)
            .enumerate()
        {
            if inside_ifp(vertex.x, vertex.y, &ctx.ifp) {
                counts.candidates.push(Candidate {
                    tx: vertex.x,
                    ty: vertex.y,
                    rotation_idx,
                    cfr_component_rank: poly_rank,
                    vertex_rank_within_component: vtx_rank,
                    nudge_rank: 0,
                    source: CandidateSource::NfpVertex,
                });
                counts.nfp_vertex += 1;
            }
        }
    }

    // C) NFP edge midpoints (limited, prefer longer edges)
    for (poly_rank, nfp_poly) in nfp_polys.iter().enumerate() {
        let outer = &nfp_poly.outer;
        let n = outer.len();
        let mut edge_lengths: Vec<(i128, usize)> = Vec::new();
        for i in 0..n {
            let dx = outer[(i + 1) % n].x as i128 - outer[i].x as i128;
            let dy = outer[(i + 1) % n].y as i128 - outer[i].y as i128;
            let len2 = dx * dx + dy * dy;
            edge_lengths.push((len2, i));
        }
        // Sort by length descending, take top N
        edge_lengths.sort_by(|a, b| b.0.cmp(&a.0));
        let max_midpoints = MAX_NFP_MIDPOINT_CANDIDATES_PER_ROTATION.min(edge_lengths.len());
        for &(len2, edge_idx) in edge_lengths.iter().take(max_midpoints) {
            if len2 == 0 {
                continue;
            }
            let p0 = &outer[edge_idx];
            let p1 = &outer[(edge_idx + 1) % n];
            let mx = (p0.x + p1.x) / 2;
            let my = (p0.y + p1.y) / 2;
            if inside_ifp(mx, my, &ctx.ifp) {
                counts.candidates.push(Candidate {
                    tx: mx,
                    ty: my,
                    rotation_idx,
                    cfr_component_rank: poly_rank,
                    vertex_rank_within_component: edge_idx,
                    nudge_rank: 0,
                    source: CandidateSource::NfpMidpoint,
                });
                counts.nfp_edge_midpoint += 1;
            }
        }
    }

    // D) Placed anchor / bbox corners
    for (anchor_rank, placed_part) in placed_for_nfp.iter().enumerate() {
        for corner in placed_part.aabb.corners() {
            if counts.placed_anchor as usize >= MAX_PLACED_ANCHOR_CANDIDATES_PER_ROTATION {
                break;
            }
            if inside_ifp(corner.x, corner.y, &ctx.ifp) {
                counts.candidates.push(Candidate {
                    tx: corner.x,
                    ty: corner.y,
                    rotation_idx,
                    cfr_component_rank: anchor_rank,
                    vertex_rank_within_component: 0,
                    nudge_rank: 0,
                    source: CandidateSource::PlacedAnchor,
                });
                counts.placed_anchor += 1;
            }
        }
    }

    // E) Nudge variants of all generated candidates (limited)
    let base_count = counts.candidates.len();
    for i in 0..base_count {
        let base = counts.candidates[i];
        let mut nudge_rank = 1_usize;
        for step in NUDGE_STEPS {
            for (dx, dy) in NUDGE_DIRS {
                let tx = base.tx.saturating_add(dx.saturating_mul(step));
                let ty = base.ty.saturating_add(dy.saturating_mul(step));
                if !inside_ifp(tx, ty, &ctx.ifp) {
                    nudge_rank += 1;
                    continue;
                }
                counts.candidates.push(Candidate {
                    tx,
                    ty,
                    rotation_idx: base.rotation_idx,
                    cfr_component_rank: base.cfr_component_rank,
                    vertex_rank_within_component: base.vertex_rank_within_component,
                    nudge_rank,
                    source: CandidateSource::Nudge,
                });
                counts.nudge += 1;
                nudge_rank += 1;
            }
        }
    }

    counts
}

// T06d: Add corners() method to Aabb for anchor candidate generation
mod aabb_ext {
    use super::Aabb;
    use crate::geometry::types::Point64;

    impl Aabb {
        /// Returns the four corners of the AABB in order: (min_x,min_y), (max_x,min_y),
        /// (max_x,max_y), (min_x,max_y)
        pub fn corners(&self) -> [Point64; 4] {
            [
                Point64 {
                    x: self.min_x,
                    y: self.min_y,
                },
                Point64 {
                    x: self.max_x,
                    y: self.min_y,
                },
                Point64 {
                    x: self.max_x,
                    y: self.max_y,
                },
                Point64 {
                    x: self.min_x,
                    y: self.max_y,
                },
            ]
        }
    }
}

use crate::feasibility::aabb::Aabb;

/// T06d: CFR fallback — recomputes NFP and CFR for a specific part instance.
/// Returns (candidates, rotation_contexts) for the fallback attempt.
#[allow(clippy::too_many_arguments)]
fn compute_cfr_fallback_candidates(
    ordered: &[InflatedPartSpec],
    part_idx: usize,
    instance: usize,
    existing_rotation_count: usize,
    nfp_kernel: NfpKernel,
    cache: &mut NfpCache,
    stats: &mut NfpPlacerStatsV1,
    placed_for_nfp: &[PlacedPart],
    bin_aabb: &crate::feasibility::aabb::Aabb,
    part: &InflatedPartSpec,
) -> (Vec<Candidate>, Vec<RotationContext>) {
    // Rebuild rotation contexts for this part (limited to already-computed rotations)
    let mut rotation_contexts: Vec<RotationContext> = Vec::new();
    let mut all_candidates: Vec<Candidate> = Vec::new();

    let mut rotation_values = part.allowed_rotations_deg.clone();
    rotation_values.sort_unstable();
    rotation_values.dedup();

    for (rotation_rank, rotation_deg) in rotation_values.iter().copied().enumerate() {
        if rotation_rank >= existing_rotation_count {
            break;
        }
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

        let rotation_idx = rotation_contexts.len();
        rotation_contexts.push(RotationContext {
            rotation_deg,
            rotation_rank,
            moving_polygon: moving,
            ifp,
        });

        // Collect NFP polys
        let nfp_polys = collect_nfp_polys_for_rotation(
            rotation_deg,
            nfp_kernel,
            cache,
            stats,
            &rotation_contexts[rotation_idx].moving_polygon,
            &moving_aabb,
            placed_for_nfp,
        );

        if nfp_polys.is_empty() && !placed_for_nfp.is_empty() {
            continue;
        }

        // Compute full CFR
        if !nfp_polys.is_empty() {
            stats.cfr_calls = stats.cfr_calls.saturating_add(1);
            let lib_nfp_polys: Vec<LibPolygon64> =
                nfp_polys.iter().map(|p| to_lib_polygon(p)).collect();
            let cfr_components: Vec<Polygon64> = compute_cfr_with_stats(
                &rotation_contexts[rotation_idx].ifp.polygon,
                &lib_nfp_polys,
                &mut CfrStatsV1::default(),
            )
            .iter()
            .map(from_lib_polygon)
            .collect();

            if !cfr_components.is_empty() {
                let ctx = &rotation_contexts[rotation_idx];
                append_candidates(&mut all_candidates, rotation_idx, &cfr_components, ctx);
            }
        }
    }

    (all_candidates, rotation_contexts)
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
            .map(|hole| {
                hole.iter()
                    .map(|p| rotate_point(*p, rotation_deg))
                    .collect()
            })
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
    use super::CandidateSource;
    use crate::placement::blf::bbox_area;
    use nesting_engine::geometry::types::{Point64 as LibPoint64, Polygon64 as LibPolygon64};
    use nesting_engine::nfp::cache::NfpCache;
    use nesting_engine::nfp::ifp::{IfpRect, TranslationRange};

    use super::{
        nfp_place, order_parts_for_policy, sort_and_dedupe_candidates, Candidate, InflatedPartSpec,
        NfpPlacerStatsV1, RotationContext,
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
        let parts = vec![
            part("big", 1, 120.0, 80.0, &[0]),
            part("small", 1, 20.0, 20.0, &[0]),
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
                source: CandidateSource::NfpVertex,
            },
            Candidate {
                tx: 100,
                ty: 200,
                rotation_idx: 1,
                cfr_component_rank: 0,
                vertex_rank_within_component: 0,
                nudge_rank: 0,
                source: CandidateSource::NfpVertex,
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
