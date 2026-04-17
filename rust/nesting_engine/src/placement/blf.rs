use std::time::Instant;

use serde::Serialize;

use crate::feasibility::{
    aabb::{Aabb, aabb_from_polygon64},
    can_place, can_place_profiled, CanPlaceProfile, PlacedPart,
    narrow::PlacedIndex,
};
use crate::geometry::{
    scale::{i64_to_mm, mm_to_i64},
    trig_lut::{round_div_i128, normalize_deg, COS_Q, SIN_Q, TRIG_SCALE_I128},
    types::{Point64, Polygon64},
};
use crate::multi_bin::greedy::{PartInPartMode, PartOrderPolicy, StopPolicy};

const CAVITY_NUDGE_STEPS: [i64; 3] = [1, 2, 4];
const CAVITY_NUDGE_DIRS: [(i64, i64); 8] = [
    (1, 0),
    (0, 1),
    (1, 1),
    (-1, 0),
    (0, -1),
    (-1, -1),
    (-1, 1),
    (1, -1),
];

// ── BLF_PROFILE_V1 telemetry ──────────────────────────────────────────

fn blf_profile_enabled() -> bool {
    matches!(
        std::env::var("NESTING_ENGINE_BLF_PROFILE"),
        Ok(v) if v == "1"
    )
}

fn read_env_u64(key: &str, default: u64) -> u64 {
    std::env::var(key)
        .ok()
        .and_then(|raw| raw.trim().parse::<u64>().ok())
        .unwrap_or(default)
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct BlfProfileV1 {
    // top-level
    pub total_parts_requested: u64,
    pub total_parts_placed: u64,
    pub total_wall_ms: f64,
    pub total_rotation_checks: u64,
    pub total_candidates_considered: u64,
    pub total_candidates_translated: u64,
    pub total_candidates_rejected: u64,
    pub total_candidates_accepted: u64,
    pub total_cavity_candidates_generated: u64,
    pub total_cavity_candidates_tested: u64,
    pub total_grid_candidates_tested: u64,
    pub total_stop_budget_hits: u64,
    // timing
    pub wall_ms_in_cavity_generation: f64,
    pub wall_ms_in_grid_sweep: f64,
    pub wall_ms_in_translate_polygon: f64,
    pub wall_ms_in_can_place: f64,
    pub wall_ms_in_poly_within: f64,
    pub wall_ms_in_overlap_query: f64,
    pub wall_ms_in_narrow_phase: f64,
    // counters from can_place_profiled
    pub can_place_calls: u64,
    pub can_place_rejected_by_aabb: u64,
    pub can_place_rejected_by_within: u64,
    pub can_place_rejected_by_narrow: u64,
    pub poly_within_calls: u64,
    pub overlap_query_calls: u64,
    pub narrow_phase_calls: u64,
    pub segment_pair_checks: u64,
    pub placed_overlap_candidates_total: u64,
    // placement caps / early-outs (A4 telemetry; wiring pending)
    pub instance_cap_hits: u64,
    pub cavity_anchor_cap_applied: u64,
    pub cavity_hole_bbox_fit_skipped: u64,
    // stagnation
    pub last_successful_placement_index: i64,
    pub wall_ms_since_last_successful_placement: f64,
    pub candidates_tested_since_last_success: u64,
    pub progress_stalled: bool,
    // per-part instance
    pub per_instance: Vec<PartInstanceProfileV1>,
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct PartInstanceProfileV1 {
    pub part_id: String,
    pub instance: usize,
    pub rotation_count: u64,
    pub cavity_candidates_generated: u64,
    pub cavity_candidates_tested: u64,
    pub grid_candidates_tested: u64,
    pub accepted: bool,
    pub wall_ms_total: f64,
    pub wall_ms_can_place: f64,
    pub wall_ms_narrow_phase: f64,
    pub wall_ms_translate: f64,
    pub can_place_calls: u64,
    pub timed_out: bool,
}

#[derive(Debug, Clone)]
pub struct InflatedPartSpec {
    pub id: String,
    pub quantity: usize,
    pub allowed_rotations_deg: Vec<i32>,
    pub inflated_polygon: Polygon64,
    pub nominal_bbox_area: i128,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PlacedItem {
    pub part_id: String,
    pub instance: usize,
    pub sheet: usize,
    pub x_mm: f64,
    pub y_mm: f64,
    pub rotation_deg: i32,
}

#[derive(Debug, Clone, PartialEq)]
pub struct UnplacedItem {
    pub part_id: String,
    pub instance: usize,
    pub reason: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PlacementResult {
    pub placed: Vec<PlacedItem>,
    pub unplaced: Vec<UnplacedItem>,
}

pub fn blf_place(
    parts: &[InflatedPartSpec],
    bin_polygon: &Polygon64,
    grid_step_mm: f64,
    stop: &mut StopPolicy,
    order_policy: PartOrderPolicy,
    part_in_part_mode: PartInPartMode,
) -> PlacementResult {
    let profiling = blf_profile_enabled();
    let blf_start = Instant::now();
    let ordered = order_parts_for_policy(parts, order_policy);

    let instance_cap = read_env_u64("NESTING_ENGINE_BLF_INSTANCE_CANDIDATE_CAP", 0);
    let cavity_anchor_cap = read_env_u64("NESTING_ENGINE_BLF_CAVITY_ANCHOR_CAP", 0);

    let step = mm_to_i64(if grid_step_mm <= 0.0 { 1.0 } else { grid_step_mm }).max(1);
    let bin_aabb = aabb_from_polygon64(bin_polygon);
    let mut placed_state = PlacedIndex::new();
    let mut placed_polygons: Vec<Polygon64> = Vec::new();
    let mut placed: Vec<PlacedItem> = Vec::new();
    let mut unplaced: Vec<UnplacedItem> = Vec::new();

    // ── profile accumulators ───────────────────────────────────────
    let mut prof = BlfProfileV1::default();
    prof.last_successful_placement_index = -1;
    let mut last_success_time = blf_start;
    let mut global_candidate_counter: u64 = 0;
    let mut candidates_since_last_success: u64 = 0;
    for p in &ordered {
        prof.total_parts_requested += p.quantity as u64;
    }

    for part in &ordered {
        'instance_loop: for instance in 0..part.quantity {
            if stop.should_stop() {
                if profiling { prof.total_stop_budget_hits += 1; }
                unplaced.push(UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: "TIME_LIMIT_EXCEEDED".to_string(),
                });
                continue;
            }

            let inst_start = Instant::now();
            let mut inst_prof = PartInstanceProfileV1 {
                part_id: part.id.clone(),
                instance,
                ..Default::default()
            };

            let mut found = false;
            let mut instance_capped = false;
            let mut instance_candidates_tested: u64 = 0;
            let rotation_candidates: Vec<(i32, Polygon64, crate::feasibility::aabb::Aabb)> = part
                .allowed_rotations_deg
                .iter()
                .map(|&rotation| {
                    let rotated = rotate_polygon(&part.inflated_polygon, rotation);
                    let rotated_aabb = aabb_from_polygon64(&rotated);
                    (rotation, rotated, rotated_aabb)
                })
                .collect();
            if profiling {
                inst_prof.rotation_count = rotation_candidates.len() as u64;
                prof.total_rotation_checks += rotation_candidates.len() as u64;
            }
            if rotation_candidates.is_empty() {
                unplaced.push(UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: "PART_NEVER_FITS_SHEET".to_string(),
                });
                if profiling { prof.per_instance.push(inst_prof); }
                continue;
            }

            let mut global_tx_min = i64::MAX;
            let mut global_ty_min = i64::MAX;
            let mut global_tx_max = i64::MIN;
            let mut global_ty_max = i64::MIN;
            for (_, _, aabb) in &rotation_candidates {
                global_tx_min = global_tx_min.min(bin_aabb.min_x - aabb.min_x);
                global_ty_min = global_ty_min.min(bin_aabb.min_y - aabb.min_y);
                global_tx_max = global_tx_max.max(bin_aabb.max_x - aabb.max_x);
                global_ty_max = global_ty_max.max(bin_aabb.max_y - aabb.max_y);
            }

            let mut timed_out_current = false;
            if part_in_part_mode == PartInPartMode::Auto {
                let cav_gen_start = Instant::now();
                'cavity_rotation: for (rotation, rotated, rotated_aabb) in &rotation_candidates {
                    let tx_min = bin_aabb.min_x - rotated_aabb.min_x;
                    let ty_min = bin_aabb.min_y - rotated_aabb.min_y;
                    let tx_max = bin_aabb.max_x - rotated_aabb.max_x;
                    let ty_max = bin_aabb.max_y - rotated_aabb.max_y;

                    let cav_start = Instant::now();
                    let (cavity_candidates, bbox_fit_skipped) = collect_cavity_candidates(
                        &placed_polygons,
                        *rotated_aabb,
                        tx_min,
                        ty_min,
                        tx_max,
                        ty_max,
                        cavity_anchor_cap,
                    );
                    if profiling {
                        let cav_elapsed = cav_start.elapsed().as_secs_f64() * 1000.0;
                        prof.wall_ms_in_cavity_generation += cav_elapsed;
                        let n = cavity_candidates.len() as u64;
                        prof.total_cavity_candidates_generated += n;
                        inst_prof.cavity_candidates_generated += n;
                        prof.cavity_hole_bbox_fit_skipped += bbox_fit_skipped;
                        if cavity_anchor_cap > 0 && n >= cavity_anchor_cap {
                            prof.cavity_anchor_cap_applied += 1;
                        }
                    }

                    for (tx, ty) in cavity_candidates {
                        if stop.consume(1) {
                            timed_out_current = true;
                            if profiling { prof.total_stop_budget_hits += 1; }
                            break 'cavity_rotation;
                        }
                        instance_candidates_tested += 1;
                        if instance_cap > 0 && instance_candidates_tested >= instance_cap {
                            if profiling { prof.instance_cap_hits += 1; }
                            instance_capped = true;
                            break 'cavity_rotation;
                        }
                        if profiling {
                            prof.total_cavity_candidates_tested += 1;
                            inst_prof.cavity_candidates_tested += 1;
                            prof.total_candidates_considered += 1;
                            global_candidate_counter += 1;
                            candidates_since_last_success += 1;
                        }

                        let tr_start = Instant::now();
                        let candidate = translate_polygon(rotated, tx, ty);
                        if profiling {
                            let tr_ms = tr_start.elapsed().as_secs_f64() * 1000.0;
                            prof.wall_ms_in_translate_polygon += tr_ms;
                            prof.total_candidates_translated += 1;
                            inst_prof.wall_ms_translate += tr_ms;
                        }

                        let (feasible, cp) = if profiling {
                            let cp_start = Instant::now();
                            let (ok, cp) = can_place_profiled(&candidate, bin_polygon, &placed_state);
                            let cp_ms = cp_start.elapsed().as_secs_f64() * 1000.0;
                            prof.wall_ms_in_can_place += cp_ms;
                            inst_prof.wall_ms_can_place += cp_ms;
                            inst_prof.can_place_calls += 1;
                            prof.can_place_calls += 1;
                            prof.poly_within_calls += cp.poly_within_called as u64;
                            prof.wall_ms_in_poly_within += cp.poly_within_ns as f64 / 1_000_000.0;
                            prof.wall_ms_in_overlap_query += cp.overlap_query_ns as f64 / 1_000_000.0;
                            prof.overlap_query_calls += 1;
                            prof.placed_overlap_candidates_total += cp.overlap_candidates as u64;
                            prof.wall_ms_in_narrow_phase += cp.narrow_phase_ns as f64 / 1_000_000.0;
                            inst_prof.wall_ms_narrow_phase += cp.narrow_phase_ns as f64 / 1_000_000.0;
                            prof.narrow_phase_calls += cp.narrow_phase_pairs as u64;
                            prof.segment_pair_checks += cp.segment_pair_checks;
                            if cp.rejected_by_aabb { prof.can_place_rejected_by_aabb += 1; }
                            if cp.rejected_by_within { prof.can_place_rejected_by_within += 1; }
                            if cp.rejected_by_narrow { prof.can_place_rejected_by_narrow += 1; }
                            (ok, cp)
                        } else {
                            (can_place(&candidate, bin_polygon, &placed_state), CanPlaceProfile::default())
                        };
                        let _ = cp; // suppress unused warning when not profiling

                        if feasible {
                            let candidate_aabb = aabb_from_polygon64(&candidate);
                            placed_state.insert(PlacedPart {
                                inflated_polygon: candidate.clone(),
                                aabb: candidate_aabb,
                            });
                            placed_polygons.push(candidate);
                            placed.push(PlacedItem {
                                part_id: part.id.clone(),
                                instance,
                                sheet: 0,
                                x_mm: i64_to_mm(tx),
                                y_mm: i64_to_mm(ty),
                                rotation_deg: *rotation,
                            });
                            found = true;
                            if profiling {
                                prof.total_candidates_accepted += 1;
                                prof.total_parts_placed += 1;
                                prof.last_successful_placement_index = global_candidate_counter as i64;
                                last_success_time = Instant::now();
                                candidates_since_last_success = 0;
                            }
                            break 'cavity_rotation;
                        } else if profiling {
                            prof.total_candidates_rejected += 1;
                        }
                    }
                }
                if profiling && !found {
                    prof.wall_ms_in_cavity_generation += cav_gen_start.elapsed().as_secs_f64() * 1000.0
                        - prof.wall_ms_in_can_place; // avoid double-counting; approximate
                }
            }

            if found {
                if profiling {
                    inst_prof.accepted = true;
                    inst_prof.wall_ms_total = inst_start.elapsed().as_secs_f64() * 1000.0;
                    prof.per_instance.push(inst_prof);
                }
                continue;
            }

            let grid_sweep_start = Instant::now();
            let mut ty = global_ty_min;
            while ty <= global_ty_max && !found && !instance_capped {
                if stop.consume(1) {
                    timed_out_current = true;
                    if profiling { prof.total_stop_budget_hits += 1; }
                    break;
                }
                let mut tx = global_tx_min;
                while tx <= global_tx_max && !found && !instance_capped {
                    if stop.consume(1) {
                        timed_out_current = true;
                        if profiling { prof.total_stop_budget_hits += 1; }
                        break;
                    }
                    for (rotation, rotated, rotated_aabb) in &rotation_candidates {
                        if stop.consume(1) {
                            timed_out_current = true;
                            if profiling { prof.total_stop_budget_hits += 1; }
                            break;
                        }
                        let tx_min = bin_aabb.min_x - rotated_aabb.min_x;
                        let ty_min = bin_aabb.min_y - rotated_aabb.min_y;
                        let tx_max = bin_aabb.max_x - rotated_aabb.max_x;
                        let ty_max = bin_aabb.max_y - rotated_aabb.max_y;
                        if tx < tx_min || tx > tx_max || ty < ty_min || ty > ty_max {
                            continue;
                        }
                        instance_candidates_tested += 1;
                        if instance_cap > 0 && instance_candidates_tested >= instance_cap {
                            if profiling { prof.instance_cap_hits += 1; }
                            instance_capped = true;
                            break;
                        }
                        if profiling {
                            prof.total_grid_candidates_tested += 1;
                            inst_prof.grid_candidates_tested += 1;
                            prof.total_candidates_considered += 1;
                            global_candidate_counter += 1;
                            candidates_since_last_success += 1;
                        }

                        let tr_start = Instant::now();
                        let candidate = translate_polygon(rotated, tx, ty);
                        if profiling {
                            let tr_ms = tr_start.elapsed().as_secs_f64() * 1000.0;
                            prof.wall_ms_in_translate_polygon += tr_ms;
                            prof.total_candidates_translated += 1;
                            inst_prof.wall_ms_translate += tr_ms;
                        }

                        let (feasible, cp) = if profiling {
                            let cp_start = Instant::now();
                            let (ok, cp) = can_place_profiled(&candidate, bin_polygon, &placed_state);
                            let cp_ms = cp_start.elapsed().as_secs_f64() * 1000.0;
                            prof.wall_ms_in_can_place += cp_ms;
                            inst_prof.wall_ms_can_place += cp_ms;
                            inst_prof.can_place_calls += 1;
                            prof.can_place_calls += 1;
                            prof.poly_within_calls += cp.poly_within_called as u64;
                            prof.wall_ms_in_poly_within += cp.poly_within_ns as f64 / 1_000_000.0;
                            prof.wall_ms_in_overlap_query += cp.overlap_query_ns as f64 / 1_000_000.0;
                            prof.overlap_query_calls += 1;
                            prof.placed_overlap_candidates_total += cp.overlap_candidates as u64;
                            prof.wall_ms_in_narrow_phase += cp.narrow_phase_ns as f64 / 1_000_000.0;
                            inst_prof.wall_ms_narrow_phase += cp.narrow_phase_ns as f64 / 1_000_000.0;
                            prof.narrow_phase_calls += cp.narrow_phase_pairs as u64;
                            prof.segment_pair_checks += cp.segment_pair_checks;
                            if cp.rejected_by_aabb { prof.can_place_rejected_by_aabb += 1; }
                            if cp.rejected_by_within { prof.can_place_rejected_by_within += 1; }
                            if cp.rejected_by_narrow { prof.can_place_rejected_by_narrow += 1; }
                            (ok, cp)
                        } else {
                            (can_place(&candidate, bin_polygon, &placed_state), CanPlaceProfile::default())
                        };
                        let _ = cp;

                        if feasible {
                            let candidate_aabb = aabb_from_polygon64(&candidate);
                            placed_state.insert(PlacedPart {
                                inflated_polygon: candidate.clone(),
                                aabb: candidate_aabb,
                            });
                            placed_polygons.push(candidate);
                            placed.push(PlacedItem {
                                part_id: part.id.clone(),
                                instance,
                                sheet: 0,
                                x_mm: i64_to_mm(tx),
                                y_mm: i64_to_mm(ty),
                                rotation_deg: *rotation,
                            });
                            found = true;
                            if profiling {
                                prof.total_candidates_accepted += 1;
                                prof.total_parts_placed += 1;
                                prof.last_successful_placement_index = global_candidate_counter as i64;
                                last_success_time = Instant::now();
                                candidates_since_last_success = 0;
                            }
                            break;
                        } else if profiling {
                            prof.total_candidates_rejected += 1;
                        }
                    }
                    if timed_out_current || instance_capped {
                        break;
                    }
                    tx = tx.saturating_add(step);
                }
                if timed_out_current || instance_capped {
                    break;
                }
                ty = ty.saturating_add(step);
            }
            if profiling {
                prof.wall_ms_in_grid_sweep += grid_sweep_start.elapsed().as_secs_f64() * 1000.0;
            }

            if timed_out_current {
                if profiling { inst_prof.timed_out = true; }
                for remaining_instance in instance..part.quantity {
                    unplaced.push(UnplacedItem {
                        part_id: part.id.clone(),
                        instance: remaining_instance,
                        reason: "TIME_LIMIT_EXCEEDED".to_string(),
                    });
                }
                if profiling {
                    inst_prof.wall_ms_total = inst_start.elapsed().as_secs_f64() * 1000.0;
                    prof.per_instance.push(inst_prof);
                }
                break 'instance_loop;
            }

            if !found {
                unplaced.push(UnplacedItem {
                    part_id: part.id.clone(),
                    instance,
                    reason: if instance_capped {
                        "INSTANCE_CANDIDATE_CAP".to_string()
                    } else if stop.should_stop() {
                        "TIME_LIMIT_EXCEEDED".to_string()
                    } else {
                        "PART_NEVER_FITS_SHEET".to_string()
                    },
                });
            } else if profiling {
                inst_prof.accepted = true;
            }

            if profiling {
                inst_prof.wall_ms_total = inst_start.elapsed().as_secs_f64() * 1000.0;
                prof.per_instance.push(inst_prof);
            }
        }
    }

    // ── emit profile ───────────────────────────────────────────────
    if profiling {
        prof.total_wall_ms = blf_start.elapsed().as_secs_f64() * 1000.0;
        prof.wall_ms_since_last_successful_placement =
            last_success_time.elapsed().as_secs_f64() * 1000.0;
        prof.candidates_tested_since_last_success = candidates_since_last_success;
        prof.progress_stalled = prof.total_parts_placed < prof.total_parts_requested
            && candidates_since_last_success > 1000;
        if let Ok(json) = serde_json::to_string(&prof) {
            eprintln!("BLF_PROFILE_V1 {json}");
        }
    }

    PlacementResult { placed, unplaced }
}

fn collect_cavity_candidates(
    placed_polygons: &[Polygon64],
    rotated_aabb: Aabb,
    tx_min: i64,
    ty_min: i64,
    tx_max: i64,
    ty_max: i64,
    anchor_cap: u64,
) -> (Vec<(i64, i64)>, u64) {
    let mut out: Vec<(i64, i64)> = Vec::new();
    let mut seen: std::collections::BTreeSet<(i64, i64)> = std::collections::BTreeSet::new();
    let part_w = rotated_aabb.max_x - rotated_aabb.min_x;
    let part_h = rotated_aabb.max_y - rotated_aabb.min_y;
    let mut bbox_fit_skipped: u64 = 0;

    'outer: for placed in placed_polygons {
        let mut hole_meta: Vec<(usize, Aabb, i128)> = placed
            .holes
            .iter()
            .enumerate()
            .filter_map(|(idx, hole)| {
                if hole.is_empty() {
                    return None;
                }
                let bbox = ring_bbox(hole);
                let area = (bbox.max_x as i128 - bbox.min_x as i128)
                    * (bbox.max_y as i128 - bbox.min_y as i128);
                Some((idx, bbox, area))
            })
            .collect();

        hole_meta.sort_by(|a, b| {
            a.1.min_x
                .cmp(&b.1.min_x)
                .then(a.1.min_y.cmp(&b.1.min_y))
                .then(a.2.cmp(&b.2))
                .then(a.0.cmp(&b.0))
        });

        for (hole_idx, hole_bbox, _) in hole_meta {
            let hole_w = hole_bbox.max_x - hole_bbox.min_x;
            let hole_h = hole_bbox.max_y - hole_bbox.min_y;
            if hole_w < part_w || hole_h < part_h {
                bbox_fit_skipped += 1;
                continue;
            }
            let hole = &placed.holes[hole_idx];
            for anchor in hole_anchor_points(hole, hole_bbox) {
                let tx = anchor.x - rotated_aabb.min_x;
                let ty = anchor.y - rotated_aabb.min_y;

                if tx < tx_min || tx > tx_max || ty < ty_min || ty > ty_max {
                    continue;
                }
                if seen.insert((tx, ty)) {
                    out.push((tx, ty));
                    if anchor_cap > 0 && out.len() as u64 >= anchor_cap {
                        break 'outer;
                    }
                }
            }
        }
    }

    (out, bbox_fit_skipped)
}

fn hole_anchor_points(hole: &[Point64], hole_bbox: Aabb) -> Vec<Point64> {
    let mut out: Vec<Point64> = Vec::new();

    // Lower-left anchor with deterministic inward nudges.
    for step in CAVITY_NUDGE_STEPS {
        out.push(Point64 {
            x: hole_bbox.min_x.saturating_add(step),
            y: hole_bbox.min_y.saturating_add(step),
        });
    }

    // Center anchor plus deterministic nudge cloud.
    let center_x = hole_bbox.min_x + ((hole_bbox.max_x - hole_bbox.min_x) / 2);
    let center_y = hole_bbox.min_y + ((hole_bbox.max_y - hole_bbox.min_y) / 2);
    out.push(Point64 {
        x: center_x,
        y: center_y,
    });
    for step in CAVITY_NUDGE_STEPS {
        for (dx, dy) in CAVITY_NUDGE_DIRS {
            out.push(Point64 {
                x: center_x.saturating_add(dx.saturating_mul(step)),
                y: center_y.saturating_add(dy.saturating_mul(step)),
            });
        }
    }

    // Vertex anchors plus deterministic nudges to avoid touching-only placements.
    for vertex in hole {
        for step in CAVITY_NUDGE_STEPS {
            for (dx, dy) in CAVITY_NUDGE_DIRS {
                out.push(Point64 {
                    x: vertex.x.saturating_add(dx.saturating_mul(step)),
                    y: vertex.y.saturating_add(dy.saturating_mul(step)),
                });
            }
        }
    }

    out
}

fn ring_bbox(ring: &[Point64]) -> Aabb {
    let first = ring[0];
    let mut min_x = first.x;
    let mut min_y = first.y;
    let mut max_x = first.x;
    let mut max_y = first.y;

    for point in &ring[1..] {
        min_x = min_x.min(point.x);
        min_y = min_y.min(point.y);
        max_x = max_x.max(point.x);
        max_y = max_y.max(point.y);
    }

    Aabb {
        min_x,
        min_y,
        max_x,
        max_y,
    }
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

fn rotate_polygon(poly: &Polygon64, rotation_deg: i32) -> Polygon64 {
    Polygon64 {
        outer: poly.outer.iter().map(|p| rotate_point(*p, rotation_deg)).collect(),
        holes: poly
            .holes
            .iter()
            .map(|h| h.iter().map(|p| rotate_point(*p, rotation_deg)).collect())
            .collect(),
    }
}

pub(crate) fn rotated_inflated_aabb(inflated_polygon: &Polygon64, rotation_deg: i32) -> Aabb {
    let rotated = rotate_polygon(inflated_polygon, rotation_deg);
    aabb_from_polygon64(&rotated)
}

pub(crate) fn placed_extents_max_xy_i64(
    inflated_polygon: &Polygon64,
    rotation_deg: i32,
    tx: i64,
    ty: i64,
) -> (i64, i64) {
    let rotated_aabb = rotated_inflated_aabb(inflated_polygon, rotation_deg);
    (
        tx.saturating_add(rotated_aabb.max_x),
        ty.saturating_add(rotated_aabb.max_y),
    )
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

pub(crate) fn rotate_polygon_for_placement(poly: &Polygon64, rotation_deg: i32) -> Polygon64 {
    rotate_polygon(poly, rotation_deg)
}

fn translate_polygon(poly: &Polygon64, tx: i64, ty: i64) -> Polygon64 {
    Polygon64 {
        outer: poly.outer.iter().map(|p| Point64 { x: p.x + tx, y: p.y + ty }).collect(),
        holes: poly
            .holes
            .iter()
            .map(|h| h.iter().map(|p| Point64 { x: p.x + tx, y: p.y + ty }).collect())
            .collect(),
    }
}

pub(crate) fn translate_polygon_for_placement(poly: &Polygon64, tx: i64, ty: i64) -> Polygon64 {
    translate_polygon(poly, tx, ty)
}

pub(crate) fn placed_polygon_for_state(
    inflated_polygon: &Polygon64,
    rotation_deg: i32,
    tx: i64,
    ty: i64,
) -> Polygon64 {
    let rotated = rotate_polygon_for_placement(inflated_polygon, rotation_deg);
    translate_polygon_for_placement(&rotated, tx, ty)
}

pub fn bbox_area(pts: &[Point64]) -> i128 {
    let first = pts[0];
    let mut min_x = first.x;
    let mut min_y = first.y;
    let mut max_x = first.x;
    let mut max_y = first.y;
    for p in &pts[1..] {
        min_x = min_x.min(p.x);
        min_y = min_y.min(p.y);
        max_x = max_x.max(p.x);
        max_y = max_y.max(p.y);
    }
    (max_x as i128 - min_x as i128) * (max_y as i128 - min_y as i128)
}

#[cfg(test)]
pub fn rect_poly(w_mm: f64, h_mm: f64) -> Polygon64 {
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::multi_bin::{
        greedy::{CompactionMode, PartInPartMode, PartOrderPolicy, PlacerKind, StopPolicy},
        greedy_multi_sheet,
    };
    use std::time::Instant;

    fn rect_with_hole_poly(
        outer_w_mm: f64,
        outer_h_mm: f64,
        hole_min_x_mm: f64,
        hole_min_y_mm: f64,
        hole_max_x_mm: f64,
        hole_max_y_mm: f64,
    ) -> Polygon64 {
        Polygon64 {
            outer: vec![
                Point64 {
                    x: mm_to_i64(0.0),
                    y: mm_to_i64(0.0),
                },
                Point64 {
                    x: mm_to_i64(outer_w_mm),
                    y: mm_to_i64(0.0),
                },
                Point64 {
                    x: mm_to_i64(outer_w_mm),
                    y: mm_to_i64(outer_h_mm),
                },
                Point64 {
                    x: mm_to_i64(0.0),
                    y: mm_to_i64(outer_h_mm),
                },
            ],
            holes: vec![vec![
                Point64 {
                    x: mm_to_i64(hole_min_x_mm),
                    y: mm_to_i64(hole_min_y_mm),
                },
                Point64 {
                    x: mm_to_i64(hole_max_x_mm),
                    y: mm_to_i64(hole_min_y_mm),
                },
                Point64 {
                    x: mm_to_i64(hole_max_x_mm),
                    y: mm_to_i64(hole_max_y_mm),
                },
                Point64 {
                    x: mm_to_i64(hole_min_x_mm),
                    y: mm_to_i64(hole_max_y_mm),
                },
            ]],
        }
    }

    fn offgrid_fixture_parts() -> Vec<InflatedPartSpec> {
        let frame_poly = rect_with_hole_poly(100.0, 100.0, 20.3, 20.4, 30.8, 31.1);
        let small_poly = rect_poly(10.2, 10.2);
        vec![
            InflatedPartSpec {
                id: "frame".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                nominal_bbox_area: bbox_area(&frame_poly.outer),
                inflated_polygon: frame_poly,
            },
            InflatedPartSpec {
                id: "small".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                nominal_bbox_area: bbox_area(&small_poly.outer),
                inflated_polygon: small_poly,
            },
        ]
    }

    #[test]
    fn basic_placement() {
        let part = InflatedPartSpec {
            id: "p".to_string(),
            quantity: 2,
            allowed_rotations_deg: vec![0],
            inflated_polygon: rect_poly(10.0, 10.0),
            nominal_bbox_area: bbox_area(&rect_poly(10.0, 10.0).outer),
        };
        let bin = rect_poly(30.0, 30.0);
        let mut stop = StopPolicy::wall_clock_for_test(30, Instant::now());
        let res = blf_place(
            &[part],
            &bin,
            1.0,
            &mut stop,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        assert_eq!(res.placed.len(), 2);
    }

    #[test]
    fn determinism() {
        let part = InflatedPartSpec {
            id: "p".to_string(),
            quantity: 3,
            allowed_rotations_deg: vec![0, 90],
            inflated_polygon: rect_poly(10.0, 8.0),
            nominal_bbox_area: bbox_area(&rect_poly(10.0, 8.0).outer),
        };
        let bin = rect_poly(40.0, 40.0);
        let mut stop_a = StopPolicy::wall_clock_for_test(30, Instant::now());
        let a = blf_place(
            &[part.clone()],
            &bin,
            1.0,
            &mut stop_a,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        let mut stop_b = StopPolicy::wall_clock_for_test(30, Instant::now());
        let b = blf_place(
            &[part],
            &bin,
            1.0,
            &mut stop_b,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        assert_eq!(a.placed, b.placed);
        assert_eq!(a.unplaced, b.unplaced);
    }

    #[test]
    fn blf_budget_stop_is_deterministic() {
        let part = InflatedPartSpec {
            id: "p".to_string(),
            quantity: 120,
            allowed_rotations_deg: vec![0, 90],
            inflated_polygon: rect_poly(10.0, 8.0),
            nominal_bbox_area: bbox_area(&rect_poly(10.0, 8.0).outer),
        };
        let bin = rect_poly(40.0, 40.0);
        let mut stop_a = StopPolicy::work_budget_for_test(30, 2_500, 1_000, Instant::now());
        let out_a = blf_place(
            &[part.clone()],
            &bin,
            1.0,
            &mut stop_a,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );

        let mut stop_b = StopPolicy::work_budget_for_test(30, 2_500, 1_000, Instant::now());
        let out_b = blf_place(
            &[part],
            &bin,
            1.0,
            &mut stop_b,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );

        assert_eq!(out_a.placed, out_b.placed);
        assert_eq!(out_a.unplaced, out_b.unplaced);
        assert!(
            out_a
                .unplaced
                .iter()
                .any(|u| u.reason == "TIME_LIMIT_EXCEEDED"),
            "work-budget test expects cutoff to happen"
        );
    }

    #[test]
    fn rotate_point_non_orthogonal_is_fixed_point_deterministic() {
        let p = Point64 {
            x: 12_345_678,
            y: -9_876_543,
        };
        let out = rotate_point(p, 17);
        assert_eq!(
            out,
            Point64 {
                x: 14_693_852,
                y: -5_835_458,
            }
        );
    }

    #[test]
    fn order_policy_by_input_order_preserves_input_order() {
        let small_poly = rect_poly(8.0, 8.0);
        let large_poly = rect_poly(20.0, 20.0);
        let medium_poly = rect_poly(15.0, 10.0);
        let parts = vec![
            InflatedPartSpec {
                id: "small".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: small_poly.clone(),
                nominal_bbox_area: bbox_area(&small_poly.outer),
            },
            InflatedPartSpec {
                id: "large".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: large_poly.clone(),
                nominal_bbox_area: bbox_area(&large_poly.outer),
            },
            InflatedPartSpec {
                id: "medium".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: medium_poly.clone(),
                nominal_bbox_area: bbox_area(&medium_poly.outer),
            },
        ];

        let by_input = order_parts_for_policy(&parts, PartOrderPolicy::ByInputOrder);
        let by_area = order_parts_for_policy(&parts, PartOrderPolicy::ByArea);

        let by_input_ids: Vec<&str> = by_input.iter().map(|p| p.id.as_str()).collect();
        let by_area_ids: Vec<&str> = by_area.iter().map(|p| p.id.as_str()).collect();

        assert_eq!(by_input_ids, vec!["small", "large", "medium"]);
        assert_eq!(by_area_ids, vec!["large", "medium", "small"]);
    }

    #[test]
    fn blf_part_in_part_off_mode_preserves_baseline() {
        let parts = vec![
            InflatedPartSpec {
                id: "a".to_string(),
                quantity: 2,
                allowed_rotations_deg: vec![0],
                inflated_polygon: rect_poly(10.0, 10.0),
                nominal_bbox_area: bbox_area(&rect_poly(10.0, 10.0).outer),
            },
            InflatedPartSpec {
                id: "b".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                inflated_polygon: rect_poly(8.0, 8.0),
                nominal_bbox_area: bbox_area(&rect_poly(8.0, 8.0).outer),
            },
        ];
        let bin = rect_poly(40.0, 20.0);
        let mut off_stop = StopPolicy::wall_clock_for_test(30, Instant::now());
        let off_out = blf_place(
            &parts,
            &bin,
            1.0,
            &mut off_stop,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        let mut auto_stop = StopPolicy::wall_clock_for_test(30, Instant::now());
        let auto_out = blf_place(
            &parts,
            &bin,
            1.0,
            &mut auto_stop,
            PartOrderPolicy::ByArea,
            PartInPartMode::Auto,
        );

        assert_eq!(off_out, auto_out);
    }

    #[test]
    fn blf_part_in_part_offgrid_hole_improves_sheet_count() {
        let parts = offgrid_fixture_parts();
        let bin = rect_poly(102.0, 102.0);

        let (off_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
            CompactionMode::Off,
        );
        let (auto_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Auto,
            CompactionMode::Off,
        );

        assert_eq!(
            off_result.sheets_used, 2,
            "off mode should miss the off-grid cavity and spill to a second sheet"
        );
        assert_eq!(
            auto_result.sheets_used, 1,
            "auto mode should place the small part into the cavity on sheet 1"
        );
    }

    #[test]
    fn collect_cavity_candidates_skips_small_holes_via_bbox_fit() {
        // Frame: 100x100 outer with a 5x5 hole — too small for a 20x20 part.
        let frame = rect_with_hole_poly(100.0, 100.0, 40.0, 40.0, 45.0, 45.0);
        let placed_polygons = vec![frame];

        let part_aabb = Aabb {
            min_x: 0,
            min_y: 0,
            max_x: mm_to_i64(20.0),
            max_y: mm_to_i64(20.0),
        };

        let (candidates, bbox_skipped) = collect_cavity_candidates(
            &placed_polygons,
            part_aabb,
            i64::MIN / 2,
            i64::MIN / 2,
            i64::MAX / 2,
            i64::MAX / 2,
            0,
        );

        assert!(bbox_skipped > 0, "should skip the small 5x5 hole for 20x20 part");
        assert!(candidates.is_empty(), "no candidates from tiny hole");
    }

    #[test]
    fn collect_cavity_candidates_no_skip_when_hole_is_large_enough() {
        // Frame: 100x100 outer with a 50x50 hole — large enough for a 20x20 part.
        let frame = rect_with_hole_poly(100.0, 100.0, 25.0, 25.0, 75.0, 75.0);
        let placed_polygons = vec![frame];

        let part_aabb = Aabb {
            min_x: 0,
            min_y: 0,
            max_x: mm_to_i64(20.0),
            max_y: mm_to_i64(20.0),
        };

        let (candidates, bbox_skipped) = collect_cavity_candidates(
            &placed_polygons,
            part_aabb,
            i64::MIN / 2,
            i64::MIN / 2,
            i64::MAX / 2,
            i64::MAX / 2,
            0,
        );

        assert_eq!(bbox_skipped, 0, "hole is big enough, no skip");
        assert!(!candidates.is_empty(), "should generate candidates from 50x50 hole");
    }

    #[test]
    fn collect_cavity_candidates_respects_anchor_cap() {
        // Frame with large hole that generates many anchors.
        let frame = rect_with_hole_poly(100.0, 100.0, 10.0, 10.0, 90.0, 90.0);
        let placed_polygons = vec![frame];

        let part_aabb = Aabb {
            min_x: 0,
            min_y: 0,
            max_x: mm_to_i64(5.0),
            max_y: mm_to_i64(5.0),
        };

        let (uncapped, _) = collect_cavity_candidates(
            &placed_polygons,
            part_aabb,
            i64::MIN / 2,
            i64::MIN / 2,
            i64::MAX / 2,
            i64::MAX / 2,
            0,
        );

        let cap: u64 = 10;
        let (capped, _) = collect_cavity_candidates(
            &placed_polygons,
            part_aabb,
            i64::MIN / 2,
            i64::MIN / 2,
            i64::MAX / 2,
            i64::MAX / 2,
            cap,
        );

        assert!(
            uncapped.len() > cap as usize,
            "uncapped should have more than {cap} candidates, got {}",
            uncapped.len()
        );
        assert_eq!(
            capped.len(),
            cap as usize,
            "capped should have exactly {cap} candidates"
        );
    }

    #[test]
    fn blf_instance_candidate_cap_limits_placement_attempts() {
        // Many parts, tiny cap → most will be unplaced with INSTANCE_CANDIDATE_CAP reason.
        let part = InflatedPartSpec {
            id: "p".to_string(),
            quantity: 5,
            allowed_rotations_deg: vec![0, 90],
            inflated_polygon: rect_poly(10.0, 8.0),
            nominal_bbox_area: bbox_area(&rect_poly(10.0, 8.0).outer),
        };
        let bin = rect_poly(40.0, 40.0);

        // With cap=1, each instance gets only 1 candidate attempt.
        // First instance will succeed (first position is valid), rest likely won't
        // in just 1 attempt once space is scarce.
        std::env::set_var("NESTING_ENGINE_BLF_INSTANCE_CANDIDATE_CAP", "1");
        let mut stop = StopPolicy::wall_clock_for_test(30, Instant::now());
        let res = blf_place(
            &[part],
            &bin,
            1.0,
            &mut stop,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
        );
        std::env::remove_var("NESTING_ENGINE_BLF_INSTANCE_CANDIDATE_CAP");

        let cap_reasons: Vec<_> = res
            .unplaced
            .iter()
            .filter(|u| u.reason == "INSTANCE_CANDIDATE_CAP")
            .collect();
        // At least some instances should be capped (not all 5 can fit in 1 attempt each)
        assert!(
            !cap_reasons.is_empty(),
            "with cap=1, at least some instances should hit INSTANCE_CANDIDATE_CAP"
        );
    }

    #[test]
    fn blf_part_in_part_hole_collapsed_like_outer_only_source_is_ignored() {
        let frame_outer_only = rect_poly(100.0, 100.0);
        let small = rect_poly(10.2, 10.2);
        let parts = vec![
            InflatedPartSpec {
                id: "outer_only".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                nominal_bbox_area: bbox_area(&frame_outer_only.outer),
                inflated_polygon: frame_outer_only,
            },
            InflatedPartSpec {
                id: "small".to_string(),
                quantity: 1,
                allowed_rotations_deg: vec![0],
                nominal_bbox_area: bbox_area(&small.outer),
                inflated_polygon: small,
            },
        ];
        let bin = rect_poly(102.0, 102.0);

        let (off_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Off,
            CompactionMode::Off,
        );
        let (auto_result, _) = greedy_multi_sheet(
            &parts,
            &bin,
            1.0,
            30,
            PlacerKind::Blf,
            PartOrderPolicy::ByArea,
            PartInPartMode::Auto,
            CompactionMode::Off,
        );

        assert_eq!(off_result, auto_result);
        assert_eq!(
            auto_result.sheets_used, 2,
            "outer-only placed source (hole-collapsed-like) must not create cavity candidates"
        );
    }
}
