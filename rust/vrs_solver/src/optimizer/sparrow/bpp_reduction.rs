//! SGH-Q45: coroush/sparrow-style BPP sheet-reduction multisheet solver (VRS-adapted).
//!
//! This module is an ADAPTED port of the bin-packing (BPP) sheet-reduction layer of
//! `coroush/sparrow` (https://github.com/coroush/sparrow, commit 5df9ce15, MIT,
//! © 2025 Jeroen Gardeyn / KU Leuven — see THIRD_PARTY_NOTICES.md). The coroush BPP
//! algorithm (`src/bp_optimizer/{bp_lbf,bp_explore,bp_moves,bp_separator}.rs`) is mapped
//! onto VRS's flat multi-sheet `SparrowLayout` (a "bin" = a `sheet_index`) and reuses the
//! existing native CDE separator / collision tracker. No jagua-rs source is modified.
//!
//! Flow (coroush semantics, VRS types):
//!   construct_initial_layout (ADAPTED bp_lbf: FFD+LBF seed + exploration over the pool)
//!   → area lower bound
//!   → sheet-reduction loop (ADAPTED bp_explore::bin_reduction_phase):
//!       select lowest-utilization candidate sheet
//!       → redistribute its items into the remaining sheets (ADAPTED try_lbf_into_any_bin)
//!       → separate the affected sheets only (ADAPTED bp_separator on a sub-problem)
//!       → on residual collisions: resolve_by_transfers (ADAPTED bp_moves try_transfer/try_swap)
//!       → on success: compact affected sheets (ADAPTED compact_bin), accept incumbent
//!       → on failure: mark candidate failed, restore incumbent, maybe perturb
//!   → final validation; status "ok" only when all placed && pairs=0 && boundary=0.

use super::*;
use super::density::{
    contour_near_rect_mins, density_candidate_score, is_interlock_candidate, DensityWeights,
};
use super::multisheet::{
    compute_utilization, part_polygon_area, sanitize_partial, FiniteStockRunConfig,
    FiniteStockRunResult,
};
use crate::io::BppReductionDiagnostics;
use crate::sheet::{expand_sheets, Stock};
use std::collections::{BTreeSet, HashMap, HashSet};
use std::time::Instant;

/// Wall-time reserved (seconds) at the end of the budget for the post-solve margin/spacing
/// validators, final validation and output serialisation, plus the one-iteration GLS
/// deadline overrun. Calibrated at ~90 s for the LV8-dense full run; computed adaptively
/// (8 % of budget, capped at 90 s) so short test/CI runs are not starved.
fn final_guard_s(total_budget: f64) -> f64 {
    (total_budget * 0.08).clamp(3.0, 90.0)
}
const MAX_CONSEC_FAILURES: usize = 15;
const PERTURB_AFTER_FAILURES: usize = 5;
const TRANSFER_BUDGET: usize = 64;

const REASON_BPP_STOCK_EXHAUSTED: &str = "STOCK_EXHAUSTED_PARTIAL";

// ── small geometry/layout helpers ─────────────────────────────────────────────

/// Global sheet indices that currently hold ≥1 placement, ascending.
fn used_sheet_set(layout: &SparrowLayout) -> Vec<usize> {
    let s: BTreeSet<usize> = layout.placements.iter().map(|p| p.sheet_index).collect();
    s.into_iter().collect()
}

fn instance_area(instances: &[SPInstance], instance_idx: usize) -> f64 {
    part_polygon_area(&instances[instance_idx].part)
}

/// SGH-Q47 ordering key for redistribution/compaction: heavier shape-`priority_score` first, then
/// larger polygon area. Tuples compare lexicographically. With the profile layer disabled the
/// priority term is 0.0 for every instance ⇒ pure largest-area ordering (the pre-Q47 behaviour).
fn profile_order_key(instances: &[SPInstance], instance_idx: usize) -> (f64, f64) {
    let prio = if super::shape_profile::shape_profile_enabled() {
        instances[instance_idx].shape_profile.priority_score
    } else {
        0.0
    };
    (prio, instance_area(instances, instance_idx))
}

/// Sum of placed part areas on a given sheet (for utilization ranking).
fn sheet_placed_area(layout: &SparrowLayout, instances: &[SPInstance], sheet: usize) -> f64 {
    layout
        .placements
        .iter()
        .filter(|p| p.sheet_index == sheet)
        .map(|p| instance_area(instances, p.instance_idx))
        .sum()
}

fn layout_is_full_feasible(
    layout: &SparrowLayout,
    instances: &[SPInstance],
    sheets: &[SheetShape],
) -> bool {
    if layout.placements.len() != instances.len() {
        return false;
    }
    let t = SparrowCollisionTracker::final_validation_tracker(layout, instances, sheets);
    t.is_feasible()
}

fn layout_conflict_count(
    layout: &SparrowLayout,
    instances: &[SPInstance],
    sheets: &[SheetShape],
) -> usize {
    let t = SparrowCollisionTracker::final_validation_tracker(layout, instances, sheets);
    t.colliding_pairs() + t.boundary_violations()
}

// ── ADAPTED bp_separator: sub-problem separation over an explicit sheet set ─────

/// Run the native exploration/separation over `local_sheets` only, seeded with
/// `seed_layout` (placements indexed into `local_sheets`). Returns
/// `(full_feasible, solved_local_layout)`.
fn run_subsolve(
    optimizer: &SparrowOptimizer,
    seed_layout: SparrowLayout,
    instances: &[SPInstance],
    local_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
) -> (bool, SparrowLayout) {
    let mut state = SparrowState::new_with_diag(seed_layout, instances, local_sheets, diag);
    let _ = optimizer.exploration_phase(
        &mut state, instances, local_sheets, started, deadline_s, rng, diag,
    );
    let layout = state
        .best_feasible
        .clone()
        .unwrap_or_else(|| state.layout.clone());
    let full = layout_is_full_feasible(&layout, instances, local_sheets);
    // If the best_feasible was empty but the live layout happens to validate, prefer it.
    if full {
        (true, layout)
    } else {
        // Pick whichever of best_feasible / live layout has fewer conflicts.
        let live = state.layout.clone();
        let live_full = layout_is_full_feasible(&live, instances, local_sheets);
        if live_full {
            (true, live)
        } else if layout_conflict_count(&live, instances, local_sheets)
            < layout_conflict_count(&layout, instances, local_sheets)
        {
            (false, live)
        } else {
            (false, layout)
        }
    }
}

/// Separate the receiving sheets only (mandatory affected-sheet-only separation §D):
/// build a sub-`SparrowProblem` view over `receiving`, run the native separator, remap
/// `sheet_index` back to global. `trial` must already have every placement on a
/// `receiving` sheet.
fn separate_affected_sheets(
    optimizer: &SparrowOptimizer,
    trial: &SparrowLayout,
    receiving: &[usize],
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
) -> (bool, SparrowLayout) {
    let local_sheets: Vec<SheetShape> = receiving.iter().map(|&g| solver_sheets[g].clone()).collect();
    let g2l: HashMap<usize, usize> = receiving.iter().enumerate().map(|(l, &g)| (g, l)).collect();
    let local_layout = SparrowLayout {
        placements: trial
            .placements
            .iter()
            .map(|p| SparrowPlacement {
                sheet_index: *g2l.get(&p.sheet_index).unwrap_or(&0),
                ..p.clone()
            })
            .collect(),
    };
    let (full, solved) = run_subsolve(
        optimizer, local_layout, instances, &local_sheets, started, deadline_s, rng, diag,
    );
    let remapped = SparrowLayout {
        placements: solved
            .placements
            .iter()
            .map(|p| SparrowPlacement {
                sheet_index: receiving.get(p.sheet_index).cloned().unwrap_or(receiving[0]),
                ..p.clone()
            })
            .collect(),
    };
    // SGH-Q46 M3: when the direct fit fails, try the strip-compress fit (place loose on a
    // virtual-wide boundary, then compress to the real width — the only way to fit parts that
    // need interlocking). Opt-in (default off) while it matures.
    if !full && std::env::var("VRS_BPP_COMPRESS").ok().as_deref() == Some("1") {
        let (sc_full, sc_layout) = strip_compress_fit(
            optimizer, trial, receiving, instances, solver_sheets, started, deadline_s, rng, diag,
        );
        if sc_full {
            return (true, sc_layout);
        }
    }
    (full, remapped)
}

/// Rotation (deg) minimizing the part's bounding-box width — the narrow orientation along the
/// compression axis. Scans continuous angles or the allowed discrete set.
fn min_width_rotation(inst: &SPInstance) -> f64 {
    let candidates: Vec<f64> = if inst.continuous_rotation {
        (0..36).map(|i| i as f64 * 5.0).collect()
    } else if !inst.allowed_rotations_deg.is_empty() {
        inst.allowed_rotations_deg.clone()
    } else {
        vec![0.0]
    };
    candidates
        .into_iter()
        .min_by(|&a, &b| {
            let (wa, _) = dims_for_rotation(inst.part.width, inst.part.height, a);
            let (wb, _) = dims_for_rotation(inst.part.width, inst.part.height, b);
            wa.partial_cmp(&wb).unwrap_or(std::cmp::Ordering::Equal)
        })
        .unwrap_or(0.0)
}

/// SGH-Q46 M3: strip-compression fit. Place the items on a virtual-WIDE boundary (so they fit
/// feasibly, spread out), then incrementally compress each sheet's width back to the real
/// dimension, re-separating each step — forcing the separator to interlock the parts to fit.
/// Returns `(reached_real_feasibly, global_layout)`.
fn strip_compress_fit(
    optimizer: &SparrowOptimizer,
    trial: &SparrowLayout,
    receiving: &[usize],
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
) -> (bool, SparrowLayout) {
    let k = receiving.len();
    if k == 0 {
        return (false, trial.clone());
    }
    const WIDEN: f64 = 1.7;
    const MIN_SHRINK: f64 = 0.02;
    let n_items = trial.placements.len();
    let g2l: HashMap<usize, usize> = receiving.iter().enumerate().map(|(l, &g)| (g, l)).collect();
    let remap_to_global = |layout: &SparrowLayout| -> SparrowLayout {
        SparrowLayout {
            placements: layout
                .placements
                .iter()
                .map(|p| SparrowPlacement {
                    sheet_index: receiving.get(p.sheet_index).cloned().unwrap_or(receiving[0]),
                    ..p.clone()
                })
                .collect(),
        }
    };

    // virtual-wide local sheets
    let mut local_sheets: Vec<SheetShape> = receiving
        .iter()
        .map(|&g| {
            let s = &solver_sheets[g];
            shrunk_sheet(s, s.min_x + s.width * WIDEN, s.max_y)
        })
        .collect();
    // Seed each part in its MINIMUM-WIDTH orientation so the wide separation can fit them
    // side by side along the (to-be-compressed) width — the separator's small rotation-wiggle
    // cannot flip a part 90°, so the starting orientation is decisive.
    let local_layout = SparrowLayout {
        placements: trial
            .placements
            .iter()
            .map(|p| {
                let inst = &instances[p.instance_idx];
                SparrowPlacement {
                    sheet_index: *g2l.get(&p.sheet_index).unwrap_or(&0),
                    rotation_deg: min_width_rotation(inst),
                    ..p.clone()
                }
            })
            .collect(),
    };

    // 1. separate loose on the wide sheets (must place all items feasibly)
    let now = started.elapsed().as_secs_f64();
    let sep_deadline = (now + (deadline_s - now).max(1.0) * 0.35).min(deadline_s);
    let mut cur = {
        let mut state = SparrowState::new_with_diag(local_layout, instances, &local_sheets, diag);
        let _ = optimizer.exploration_phase(
            &mut state, instances, &local_sheets, started, sep_deadline, rng, diag,
        );
        state.best_feasible.clone().unwrap_or_else(|| state.layout.clone())
    };
    let wide_ok = SparrowCollisionTracker::final_validation_tracker(&cur, instances, &local_sheets)
        .is_feasible()
        && cur.placements.len() == n_items;
    let dbg = std::env::var("VRS_BPP_COMPRESS_DEBUG").ok().as_deref() == Some("1");
    if dbg {
        let mut per: std::collections::BTreeMap<usize, usize> = std::collections::BTreeMap::new();
        for p in &cur.placements {
            *per.entry(p.sheet_index).or_insert(0) += 1;
        }
        let pairs = SparrowCollisionTracker::final_validation_tracker(&cur, instances, &local_sheets).colliding_pairs();
        eprintln!(
            "[STRIP] receiving={:?} n_items={} wide_factor={} wide_ok={} placed={} per_local_sheet={:?} residual_pairs={}",
            receiving, n_items, WIDEN, wide_ok, cur.placements.len(), per, pairs
        );
    }
    if !wide_ok {
        return (false, remap_to_global(&cur));
    }

    // 2. compress each sheet's width toward the real dimension
    for l in 0..k {
        let g = receiving[l];
        let smin_x = solver_sheets[g].min_x;
        let target_max = smin_x + solver_sheets[g].width;
        let mut cur_max = local_sheets[l].max_x;
        let mut shrink = 0.10;
        while shrink >= MIN_SHRINK
            && cur_max > target_max + 1.0
            && started.elapsed().as_secs_f64() < deadline_s
        {
            let new_max = (cur_max - (cur_max - smin_x) * shrink).max(target_max);
            let trial_sheet = shrunk_sheet(&solver_sheets[g], new_max, local_sheets[l].max_y);
            let now = started.elapsed().as_secs_f64();
            let step_deadline = (now + (deadline_s - now).max(0.5) * 0.25).min(deadline_s);
            let (feas, remapped) = separate_sheet_local(
                optimizer, &cur, l, &trial_sheet, instances, started, step_deadline, rng, diag,
            );
            if feas {
                replace_sheet_placements(&mut cur, l, remapped);
                local_sheets[l] = trial_sheet;
                cur_max = new_max;
            } else {
                shrink *= 0.6;
            }
        }
        if dbg {
            eprintln!(
                "[STRIP]   sheet l={} target_w={:.0} reached_w={:.0} (gap {:.0})",
                l,
                target_max - smin_x,
                cur_max - smin_x,
                cur_max - target_max
            );
        }
    }

    // 3. validate against the REAL sheets
    let real_local: Vec<SheetShape> = receiving.iter().map(|&g| solver_sheets[g].clone()).collect();
    let feasible = SparrowCollisionTracker::final_validation_tracker(&cur, instances, &real_local)
        .is_feasible()
        && cur.placements.len() == n_items;
    if dbg {
        eprintln!("[STRIP] final feasible_at_real={}", feasible);
    }
    (feasible, remap_to_global(&cur))
}

// ── ADAPTED bp_lbf: clear placement search on a single global sheet ────────────

/// Try to find a low-loss placement for instance `target_instance` on global sheet
/// `sheet` given the items currently on it. Returns a global-sheet `SparrowPlacement`.
/// `prefer_clear` returns `None` if the best found placement still collides.
fn search_placement_on_sheet(
    optimizer: &SparrowOptimizer,
    target_instance: usize,
    sheet: usize,
    layout: &SparrowLayout,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    prefer_clear: bool,
) -> Option<SparrowPlacement> {
    let local_sheets = [solver_sheets[sheet].clone()];
    // local layout = items already on `sheet`, remapped to local sheet 0, plus the
    // target appended at a deterministic in-bounds bootstrap position.
    let mut local: Vec<SparrowPlacement> = layout
        .placements
        .iter()
        .filter(|p| p.sheet_index == sheet)
        .map(|p| SparrowPlacement { sheet_index: 0, ..p.clone() })
        .collect();
    let inst = &instances[target_instance];
    let rot = super::fixed_sheet::fitting_rotation(inst, &local_sheets);
    let s = &local_sheets[0];
    let (ax, ay) = placement_anchor_from_rect_min(s.min_x, s.min_y, inst.part.width, inst.part.height, rot);
    let target_idx = local.len();
    local.push(SparrowPlacement { instance_idx: target_instance, sheet_index: 0, x: ax, y: ay, rotation_deg: rot });
    let layout_local = SparrowLayout { placements: local };
    let tracker = SparrowCollisionTracker::build(&layout_local, instances, &local_sheets);
    // SGH-Q47 T4: scale the per-placement micro-budget by the target's shape budget multiplier
    // (large concave anchors get more search time, tiny fillers less). Base 2.0 s; multiplier is
    // clamped [0.4, 3.0] ⇒ deadline ∈ [0.8 s, 6.0 s]. `VRS_SHAPE_PROFILE=0` ⇒ flat 2.0 s.
    let budget_mult = if super::shape_profile::shape_profile_enabled() {
        inst.shape_profile.search_budget_multiplier
    } else {
        1.0
    };
    let found = native_search_placement(
        target_idx,
        &layout_local,
        instances,
        &tracker,
        &local_sheets,
        &optimizer.config,
        rng,
        started,
        started.elapsed().as_secs_f64() + 2.0 * budget_mult,
        diag,
        None,
    );
    let pl = found?;
    // Remap to global sheet.
    let global = SparrowPlacement { sheet_index: sheet, ..pl };
    if prefer_clear {
        // Verify the candidate is collision-free against the sheet's existing items.
        let mut check: Vec<SparrowPlacement> = layout
            .placements
            .iter()
            .filter(|p| p.sheet_index == sheet)
            .cloned()
            .collect();
        check.push(global.clone());
        let chk_layout = SparrowLayout { placements: check };
        let t = SparrowCollisionTracker::final_validation_tracker(&chk_layout, instances, solver_sheets);
        if !t.is_feasible() {
            return None;
        }
    }
    Some(global)
}

/// Deterministic in-bounds bootstrap placement of `target_instance` on `sheet`.
fn bootstrap_on_sheet(
    target_instance: usize,
    sheet: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    rng: &mut DeterministicRng,
) -> SparrowPlacement {
    let inst = &instances[target_instance];
    let s = &solver_sheets[sheet];
    let rot = super::fixed_sheet::fitting_rotation(inst, std::slice::from_ref(s));
    let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
    let max_rmx = (s.max_x - rw).max(s.min_x);
    let max_rmy = (s.max_y - rh).max(s.min_y);
    let rmx = s.min_x + rng.next_f64() * (max_rmx - s.min_x).max(0.0);
    let rmy = s.min_y + rng.next_f64() * (max_rmy - s.min_y).max(0.0);
    let (ax, ay) = placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
    SparrowPlacement { instance_idx: target_instance, sheet_index: sheet, x: ax, y: ay, rotation_deg: rot }
}

/// ADAPTED `try_lbf_into_any_bin`: move every displaced item from `candidate` into a
/// `receiving` sheet — clear LBF placement first, bootstrap fallback otherwise.
fn redistribute_displaced(
    optimizer: &SparrowOptimizer,
    trial: &mut SparrowLayout,
    displaced_layout_idxs: &[usize],
    receiving: &[usize],
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) {
    for &li in displaced_layout_idxs {
        let target_instance = trial.placements[li].instance_idx;
        // try a clear placement into each receiving sheet (most-available first by free area)
        let mut order: Vec<usize> = receiving.to_vec();
        order.sort_by(|&a, &b| {
            let fa = solver_sheets[a].area - sheet_placed_area(trial, instances, a);
            let fb = solver_sheets[b].area - sheet_placed_area(trial, instances, b);
            fb.partial_cmp(&fa).unwrap_or(std::cmp::Ordering::Equal)
        });
        let mut placed = false;
        for &rs in &order {
            if let Some(pl) = search_placement_on_sheet(
                optimizer, target_instance, rs, trial, instances, solver_sheets, started, rng, diag, true,
            ) {
                trial.placements[li] = pl;
                bpp.bpp_displaced_lbf_clear_count += 1;
                placed = true;
                break;
            }
        }
        if !placed {
            // bootstrap into the most-available receiving sheet (overlaps allowed; the
            // affected-sheet separator resolves them).
            let rs = order[0];
            trial.placements[li] = bootstrap_on_sheet(target_instance, rs, instances, solver_sheets, rng);
            bpp.bpp_displaced_fallback_count += 1;
        }
    }
}

// ── ADAPTED bp_moves: try_transfer / try_swap / resolve_by_transfers ───────────

/// ADAPTED `try_transfer`: move one item to `to_sheet`; accept only if the global
/// conflict count strictly decreases.
fn try_transfer(
    optimizer: &SparrowOptimizer,
    layout: &mut SparrowLayout,
    item_layout_idx: usize,
    to_sheet: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) -> bool {
    bpp.bpp_transfer_attempts += 1;
    let before = layout_conflict_count(layout, instances, solver_sheets);
    let old = layout.placements[item_layout_idx].clone();
    let inst = old.instance_idx;
    let new_pl = search_placement_on_sheet(
        optimizer, inst, to_sheet, layout, instances, solver_sheets, started, rng, diag, false,
    )
    .unwrap_or_else(|| bootstrap_on_sheet(inst, to_sheet, instances, solver_sheets, rng));
    layout.placements[item_layout_idx] = new_pl;
    let after = layout_conflict_count(layout, instances, solver_sheets);
    if after < before {
        bpp.bpp_transfer_successes += 1;
        true
    } else {
        layout.placements[item_layout_idx] = old;
        false
    }
}

/// ADAPTED `try_swap`: swap two items between their sheets; accept only on strict
/// conflict decrease.
fn try_swap(
    layout: &mut SparrowLayout,
    a: usize,
    b: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    bpp: &mut BppReductionDiagnostics,
) -> bool {
    bpp.bpp_swap_attempts += 1;
    let before = layout_conflict_count(layout, instances, solver_sheets);
    let pa = layout.placements[a].clone();
    let pb = layout.placements[b].clone();
    // swap sheet assignment + anchor (keep each item's own rotation)
    layout.placements[a] = SparrowPlacement { sheet_index: pb.sheet_index, x: pb.x, y: pb.y, ..pa.clone() };
    layout.placements[b] = SparrowPlacement { sheet_index: pa.sheet_index, x: pa.x, y: pa.y, ..pb.clone() };
    let after = layout_conflict_count(layout, instances, solver_sheets);
    if after < before {
        bpp.bpp_swap_successes += 1;
        true
    } else {
        layout.placements[a] = pa;
        layout.placements[b] = pb;
        false
    }
}

/// ADAPTED `resolve_by_transfers`: budget-limited inter-sheet transfer/swap repair on the
/// receiving sheets. Returns the repaired layout + whether it became full-feasible.
fn resolve_by_transfers(
    optimizer: &SparrowOptimizer,
    layout: &mut SparrowLayout,
    receiving: &[usize],
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) -> bool {
    let mut budget = TRANSFER_BUDGET;
    while budget > 0 && started.elapsed().as_secs_f64() < deadline_s {
        let tracker = SparrowCollisionTracker::final_validation_tracker(layout, instances, solver_sheets);
        if tracker.is_feasible() {
            return true;
        }
        let colliding = tracker.colliding_indices();
        if colliding.is_empty() {
            return tracker.is_feasible();
        }
        let mut improved = false;
        for &ci in colliding.iter().take(8) {
            let from = layout.placements[ci].sheet_index;
            for &to in receiving {
                if to == from {
                    continue;
                }
                budget = budget.saturating_sub(1);
                if try_transfer(optimizer, layout, ci, to, instances, solver_sheets, started, rng, diag, bpp) {
                    improved = true;
                    break;
                }
                if budget == 0 {
                    break;
                }
            }
            if improved || budget == 0 {
                break;
            }
        }
        if !improved {
            // one swap attempt between the two most-colliding items
            if colliding.len() >= 2 {
                let _ = try_swap(layout, colliding[0], colliding[1], instances, solver_sheets, bpp);
            }
            break;
        }
    }
    layout_is_full_feasible(layout, instances, solver_sheets)
}

// ── ADAPTED compact_bin ────────────────────────────────────────────────────────

/// ADAPTED `compact_bin`: shape-priority-then-area LBF reinsertion on one sheet (Q47);
/// restore-on-fail.
/// Never reduces placement count and never makes the sheet infeasible.
fn compact_sheet(
    optimizer: &SparrowOptimizer,
    layout: &mut SparrowLayout,
    sheet: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) {
    bpp.bpp_compaction_calls += 1;
    let mut idxs: Vec<usize> = (0..layout.placements.len())
        .filter(|&i| layout.placements[i].sheet_index == sheet)
        .collect();
    idxs.sort_by(|&a, &b| {
        profile_order_key(instances, layout.placements[b].instance_idx)
            .partial_cmp(&profile_order_key(instances, layout.placements[a].instance_idx))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    let mut any = false;
    for li in idxs {
        let target_instance = layout.placements[li].instance_idx;
        let old = layout.placements[li].clone();
        // temporarily lift the item off the sheet so search ignores it as an obstacle
        layout.placements[li] = SparrowPlacement { sheet_index: usize::MAX, ..old.clone() };
        let candidate = search_placement_on_sheet(
            optimizer, target_instance, sheet, layout, instances, solver_sheets, started, rng, diag, true,
        );
        match candidate {
            Some(pl) if pl.y + 1e-9 < old.y => {
                layout.placements[li] = pl;
                any = true;
            }
            _ => {
                layout.placements[li] = old;
            }
        }
    }
    if any && layout_is_full_feasible(layout, instances, solver_sheets) {
        bpp.bpp_compaction_successes += 1;
    }
}

// ── ADAPTED perturb_swap_between_bins ──────────────────────────────────────────

fn perturb_swap_between_sheets(
    layout: &mut SparrowLayout,
    used: &[usize],
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    rng: &mut DeterministicRng,
    bpp: &mut BppReductionDiagnostics,
) {
    bpp.bpp_perturbation_attempts += 1;
    if used.len() < 2 {
        return;
    }
    let s1 = used[(rng.next_u64() as usize) % used.len()];
    let mut s2 = used[(rng.next_u64() as usize) % used.len()];
    if s1 == s2 {
        s2 = used[(s1 + 1) % used.len()];
    }
    let pick_large = |sheet: usize| -> Option<usize> {
        layout
            .placements
            .iter()
            .enumerate()
            .filter(|(_, p)| p.sheet_index == sheet)
            .max_by(|(_, a), (_, b)| {
                profile_order_key(instances, a.instance_idx)
                    .partial_cmp(&profile_order_key(instances, b.instance_idx))
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .map(|(i, _)| i)
    };
    if let (Some(a), Some(b)) = (pick_large(s1), pick_large(s2)) {
        if try_swap(layout, a, b, instances, solver_sheets, bpp) {
            bpp.bpp_perturbation_successes += 1;
        }
    }
}

/// ADAPTED `select_candidate_bin`: lowest-utilization used sheet not in `failed`.
fn select_candidate_sheet(
    layout: &SparrowLayout,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    used: &[usize],
    failed: &HashSet<usize>,
) -> Option<usize> {
    used.iter()
        .filter(|s| !failed.contains(s))
        .cloned()
        .min_by(|&a, &b| {
            let ua = sheet_placed_area(layout, instances, a) / solver_sheets[a].area.max(1.0);
            let ub = sheet_placed_area(layout, instances, b) / solver_sheets[b].area.max(1.0);
            ua.partial_cmp(&ub).unwrap_or(std::cmp::Ordering::Equal)
        })
}

// ── projection / result assembly ───────────────────────────────────────────────

fn project(layout: &SparrowLayout, instances: &[SPInstance]) -> Vec<Placement> {
    layout
        .placements
        .iter()
        .map(|p| {
            let inst = &instances[p.instance_idx];
            Placement {
                instance_id: inst.instance_id.clone(),
                part_id: inst.part_id.clone(),
                sheet_index: p.sheet_index,
                x: p.x,
                y: p.y,
                rotation_deg: p.rotation_deg,
            }
        })
        .collect()
}

// ── SGH-Q46 M3: fixed-sheet region compression (upstream Sparrow Algorithm 13) ─

/// A rectangular sheet with a reduced usable extent. `prepare_shape_from_sheet` rebuilds
/// the boundary from min/max for rectangular sheets, so reducing `max_x`/`max_y` is enough.
fn shrunk_sheet(sheet: &SheetShape, new_max_x: f64, new_max_y: f64) -> SheetShape {
    let mut s = sheet.clone();
    s.max_x = new_max_x;
    s.max_y = new_max_y;
    s.width = (new_max_x - s.min_x).max(0.0);
    s.height = (new_max_y - s.min_y).max(0.0);
    s.area = s.width * s.height;
    s
}

/// Re-separate only the items on `sheet_idx` inside `local_sheet` (a possibly-shrunk
/// boundary). Returns `(feasible, remapped placements)`. Feasibility is "this sheet's items
/// are collision-free and inside the boundary" — independent of the global instance count.
fn separate_sheet_local(
    optimizer: &SparrowOptimizer,
    working: &SparrowLayout,
    sheet_idx: usize,
    local_sheet: &SheetShape,
    instances: &[SPInstance],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
) -> (bool, Vec<SparrowPlacement>) {
    let placements: Vec<SparrowPlacement> = working
        .placements
        .iter()
        .filter(|p| p.sheet_index == sheet_idx)
        .map(|p| SparrowPlacement { sheet_index: 0, ..p.clone() })
        .collect();
    if placements.is_empty() {
        return (true, vec![]);
    }
    let local_sheets = [local_sheet.clone()];
    let local_layout = SparrowLayout { placements };
    let mut state = SparrowState::new_with_diag(local_layout, instances, &local_sheets, diag);
    let _ = optimizer.exploration_phase(
        &mut state, instances, &local_sheets, started, deadline_s, rng, diag,
    );
    let layout = state
        .best_feasible
        .clone()
        .unwrap_or_else(|| state.layout.clone());
    let tracker = SparrowCollisionTracker::final_validation_tracker(&layout, instances, &local_sheets);
    let feasible = tracker.is_feasible();
    let remapped = layout
        .placements
        .iter()
        .map(|p| SparrowPlacement { sheet_index: sheet_idx, ..p.clone() })
        .collect();
    (feasible, remapped)
}

/// Used extent (max coordinate of any part) on one axis for a sheet's items.
fn sheet_used_max(layout: &SparrowLayout, instances: &[SPInstance], sheet_idx: usize, axis_x: bool) -> f64 {
    layout
        .placements
        .iter()
        .filter(|p| p.sheet_index == sheet_idx)
        .map(|p| {
            let inst = &instances[p.instance_idx];
            let (rmx, rmy) =
                rect_min_from_anchor(p.x, p.y, inst.part.width, inst.part.height, p.rotation_deg);
            let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, p.rotation_deg);
            if axis_x { rmx + rw } else { rmy + rh }
        })
        .fold(f64::MIN, f64::max)
}

/// Replace the placements on `sheet_idx` with `new`.
fn replace_sheet_placements(working: &mut SparrowLayout, sheet_idx: usize, new: Vec<SparrowPlacement>) {
    let mut others: Vec<SparrowPlacement> = working
        .placements
        .iter()
        .filter(|p| p.sheet_index != sheet_idx)
        .cloned()
        .collect();
    others.extend(new);
    others.sort_by_key(|p| p.instance_idx);
    working.placements = others;
}

/// ADAPTED upstream `compression_phase` (Algorithm 13) for fixed sheets. Per sheet, per axis,
/// incrementally shrink the usable extent toward the corner and re-separate; accept a shrink
/// only when the items still fit feasibly inside the smaller region (so the separator tucks
/// them tighter — this is the genuine Sparrow density driver, reusing the CDE separator, no
/// NFP). Disable with `VRS_BPP_COMPRESS=0`.
fn compress_layout(
    optimizer: &SparrowOptimizer,
    working: &mut SparrowLayout,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) {
    // SGH-Q46 M3 is opt-in while it matures (default off keeps production fast/correct).
    if std::env::var("VRS_BPP_COMPRESS").ok().as_deref() != Some("1") {
        return;
    }
    if working.placements.is_empty() {
        return;
    }
    const MIN_SHRINK: f64 = 0.01;
    const SHRINK_DECAY: f64 = 0.6;
    let used = used_sheet_set(working);
    let mut freed = 0.0;
    for &s in &used {
        let sheet = solver_sheets[s].clone();
        // shrink width then height (axis_x = true then false)
        for &axis_x in &[true, false] {
            let (sheet_min, _full_max) = if axis_x {
                (sheet.min_x, sheet.max_x)
            } else {
                (sheet.min_y, sheet.max_y)
            };
            let mut accepted_max = sheet_used_max(working, instances, s, axis_x).min(if axis_x { sheet.max_x } else { sheet.max_y });
            let before_extent = accepted_max - sheet_min;
            // Fine-grained compression (upstream uses ~0.05% steps): take small steps and keep
            // going while they remain feasible; shrink the step on failure. A small step injects
            // a small overlap the separator can resolve by nudging parts into concavities, which
            // accumulates into deep nesting. Coarse steps inject un-nestable overlaps and fail.
            let mut step = 0.015;
            let mut stagnant = 0usize;
            while step >= MIN_SHRINK && stagnant < 5 && started.elapsed().as_secs_f64() < deadline_s {
                let extent = (accepted_max - sheet_min).max(0.0);
                let new_max = sheet_min + extent * (1.0 - step);
                let trial = if axis_x {
                    shrunk_sheet(&sheet, new_max, sheet.max_y)
                } else {
                    shrunk_sheet(&sheet, sheet.max_x, new_max)
                };
                bpp.bpp_region_compression_attempts += 1;
                let now = started.elapsed().as_secs_f64();
                // Tight per-step deadline: a small overlap separates quickly.
                let step_deadline = (now + 2.5).min(deadline_s);
                let (feasible, remapped) = separate_sheet_local(
                    optimizer, working, s, &trial, instances, started, step_deadline, rng, diag,
                );
                if feasible && !remapped.is_empty() {
                    replace_sheet_placements(working, s, remapped);
                    bpp.bpp_region_compression_accepts += 1;
                    let new_extent = (sheet_used_max(working, instances, s, axis_x).min(new_max) - sheet_min).max(0.0);
                    if (extent - new_extent) < 1.0 {
                        stagnant += 1;
                    } else {
                        stagnant = 0;
                    }
                    accepted_max = sheet_min + new_extent;
                } else {
                    step *= SHRINK_DECAY;
                }
            }
            let after_extent = (accepted_max - sheet_min).max(0.0);
            let span = if axis_x { sheet.height } else { sheet.width };
            freed += (before_extent - after_extent).max(0.0) * span;
        }
    }
    bpp.bpp_region_compression_applied = true;
    bpp.bpp_region_compression_freed_area_mm2 = freed;
}

// ── SGH-Q46 M2: gravity / bottom-left compaction post-pass ─────────────────────

/// Slide `cur` toward `min_bound` (with the orthogonal coordinate fixed) until the part
/// would collide, then binary-refine the contact. Monotone descent — never jumps past an
/// obstacle. `is_clear(x, y)` tests the part's rect-min at (x, y); `is_x` selects which axis
/// `cur` is.
fn slide_axis<F: Fn(f64, f64) -> bool>(
    fixed: f64,
    cur: f64,
    min_bound: f64,
    is_clear: &F,
    is_x: bool,
) -> f64 {
    let test = |c: f64| -> bool {
        if is_x {
            is_clear(c, fixed)
        } else {
            is_clear(fixed, c)
        }
    };
    if cur <= min_bound + 1e-9 {
        return cur;
    }
    let mut last_clear = cur;
    let mut pos = cur;
    let step = ((cur - min_bound) / 16.0).clamp(2.0, 40.0);
    loop {
        let np = (pos - step).max(min_bound);
        if (np - pos).abs() < 1e-9 {
            break;
        }
        if test(np) {
            last_clear = np;
            pos = np;
            if np <= min_bound + 1e-9 {
                break;
            }
        } else {
            let (mut lo, mut hi) = (np, last_clear);
            for _ in 0..8 {
                let mid = 0.5 * (lo + hi);
                if test(mid) {
                    hi = mid;
                } else {
                    lo = mid;
                }
            }
            last_clear = hi;
            break;
        }
    }
    last_clear
}

/// ADAPTED density post-pass (coroush `compact_bin` generalised to a translational
/// gravity sweep): pull every part toward the bottom-left corner of its sheet along
/// collision-free directions, iterating until convergence. Pure translation (no rotation
/// change), monotone, and feasibility-preserving (only ever moves a part to a clear spot).
/// Disable with `VRS_BPP_GRAVITY=0` for A/B comparison.
// ── SGH-Q48: interlock-aware density compaction (opt-in VRS_BPP_DENSITY_COMPACT) ─────────────

/// Density placement search for one part on its sheet. Among collision-free candidates (current
/// position + uniform random + contour-near, across the part's rotation set), returns the lowest
/// density-score placement that strictly improves on the current one — or `None`. The CDE decides
/// clearance (LBFEvaluator); the density score only ranks the clear candidates. Counts interlock
/// (bbox-overlapping, polygon-clear) candidates into `bpp`. Continuous parts keep continuous
/// rotation (the candidate rotation set is the instance's resolved continuous samples).
#[allow(clippy::too_many_arguments)]
fn density_place_part(
    li: usize,
    working: &SparrowLayout,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    tracker: &SparrowCollisionTracker,
    sheet_prepared: &Rc<CdePreparedShape>,
    weights: &DensityWeights,
    rng: &mut DeterministicRng,
    bpp: &mut BppReductionDiagnostics,
) -> Option<SparrowPlacement> {
    let p = working.placements[li].clone();
    let sheet_idx = p.sheet_index;
    let inst = &instances[p.instance_idx];
    let sheet = &solver_sheets[sheet_idx];

    let neighbours: Vec<&CdePreparedShape> = (0..working.placements.len())
        .filter(|&j| j != li && working.placements[j].sheet_index == sheet_idx)
        .filter_map(|j| tracker.shapes.get(j).and_then(|o| o.as_deref()))
        .collect();
    if neighbours.is_empty() {
        return None; // first/only part on the sheet: density-neutral
    }

    let session = build_sheet_session(li, sheet_idx, working, tracker, sheet_prepared)?;
    let ev = LBFEvaluator {
        inst,
        sheet,
        sheet_idx,
        session: &session,
        base: inst.base_shape.as_ref(),
        n_evals: 0,
    };

    let cur_rot = p.rotation_deg;
    let baseline = transform_base_to_candidate(inst.base_shape.as_ref(), p.x, p.y, cur_rot)
        .map(|s| density_candidate_score(&s, &neighbours, weights))
        .unwrap_or(f64::MAX);

    // Rotation set: current + a bounded subsample of the instance's resolved rotations (these are
    // the continuous samples for continuous parts, or the discrete set otherwise) — never snapped.
    let mut rotations: Vec<f64> = vec![cur_rot];
    let allowed = &inst.allowed_rotations_deg;
    if !allowed.is_empty() {
        let stride = (allowed.len() / 8).max(1);
        for (i, &r) in allowed.iter().enumerate() {
            if i % stride == 0 {
                rotations.push(r);
            }
        }
    }

    // Position candidates: current rect-min + uniform random + contour-near (T3).
    let (cur_rmx, cur_rmy) =
        rect_min_from_anchor(p.x, p.y, inst.part.width, inst.part.height, cur_rot);
    let mut positions: Vec<(f64, f64)> = vec![(cur_rmx, cur_rmy)];
    let (rw0, rh0) = dims_for_rotation(inst.part.width, inst.part.height, cur_rot);
    for _ in 0..100 {
        let rmx = sheet.min_x + rng.next_f64() * (sheet.max_x - rw0 - sheet.min_x).max(0.0);
        let rmy = sheet.min_y + rng.next_f64() * (sheet.max_y - rh0 - sheet.min_y).max(0.0);
        positions.push((rmx, rmy));
    }
    positions.extend(contour_near_rect_mins(&neighbours, rw0, rh0, sheet, 120));

    let margin = 1e-6;
    let mut best: Option<(f64, SparrowPlacement, bool)> = None;
    for &rot in &rotations {
        for &(rmx, rmy) in &positions {
            if ev.score_lbf_candidate(rmx, rmy, rot).is_none() {
                continue; // CDE: not collision-free here
            }
            let (ax, ay) =
                placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
            let Some(cand) = transform_base_to_candidate(inst.base_shape.as_ref(), ax, ay, rot)
            else {
                continue;
            };
            let interlock = is_interlock_candidate(&cand, &neighbours);
            if interlock {
                bpp.bpp_interlock_candidates_generated += 1;
            }
            let score = density_candidate_score(&cand, &neighbours, weights);
            if best.as_ref().is_none_or(|(bs, _, _)| score < *bs - margin) {
                best = Some((
                    score,
                    SparrowPlacement {
                        instance_idx: p.instance_idx,
                        sheet_index: sheet_idx,
                        x: ax,
                        y: ay,
                        rotation_deg: rot,
                    },
                    interlock,
                ));
            }
        }
    }

    match best {
        Some((score, pl, interlock)) if score < baseline - margin => {
            if interlock {
                bpp.bpp_interlock_candidates_accepted += 1;
            }
            Some(pl)
        }
        _ => None,
    }
}

/// Per-sheet density compaction: re-place each part (priority order) to the densest collision-free
/// position. Rebuilds the tracker before each part so prior moves are seen; reverts any move that
/// fails the full-feasibility safety net.
#[allow(clippy::too_many_arguments)]
fn density_compact_sheet(
    layout: &mut SparrowLayout,
    sheet: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    weights: &DensityWeights,
    bpp: &mut BppReductionDiagnostics,
) {
    let Some(sheet_sh) = prepare_shape_from_sheet(&solver_sheets[sheet])
        .ok()
        .map(Rc::new)
    else {
        return;
    };
    let mut idxs: Vec<usize> = (0..layout.placements.len())
        .filter(|&i| layout.placements[i].sheet_index == sheet)
        .collect();
    idxs.sort_by(|&a, &b| {
        profile_order_key(instances, layout.placements[b].instance_idx)
            .partial_cmp(&profile_order_key(instances, layout.placements[a].instance_idx))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    for li in idxs {
        if started.elapsed().as_secs_f64() >= deadline_s {
            break;
        }
        let tracker = SparrowCollisionTracker::build(layout, instances, solver_sheets);
        if let Some(pl) = density_place_part(
            li, layout, instances, solver_sheets, &tracker, &sheet_sh, weights, rng, bpp,
        ) {
            let old = layout.placements[li].clone();
            layout.placements[li] = pl;
            if layout_is_full_feasible(layout, instances, solver_sheets) {
                bpp.bpp_density_moves_accepted += 1;
            } else {
                layout.placements[li] = old; // safety net
            }
        }
    }
}

/// SGH-Q48 entry: interlock-aware density compaction over all used sheets. Opt-in (default off);
/// enable with `VRS_BPP_DENSITY_COMPACT=1`. Feasibility-preserving by construction.
fn density_compact_layout(
    working: &mut SparrowLayout,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    bpp: &mut BppReductionDiagnostics,
) {
    if std::env::var("VRS_BPP_DENSITY_COMPACT").ok().as_deref() != Some("1") {
        return;
    }
    if working.placements.is_empty() {
        return;
    }
    bpp.bpp_density_compaction_applied = true;
    let weights = DensityWeights::default();
    for s in used_sheet_set(working) {
        density_compact_sheet(
            working, s, instances, solver_sheets, started, deadline_s, rng, &weights, bpp,
        );
    }
}

fn gravity_compact_layout(
    working: &mut SparrowLayout,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    bpp: &mut BppReductionDiagnostics,
) {
    if working.placements.is_empty() {
        return;
    }
    if std::env::var("VRS_BPP_GRAVITY").ok().as_deref() == Some("0") {
        return;
    }
    let mut tracker = SparrowCollisionTracker::build(working, instances, solver_sheets);
    let sheet_prepared: Vec<Option<Rc<CdePreparedShape>>> = solver_sheets
        .iter()
        .map(|s| prepare_shape_from_sheet(s).ok().map(Rc::new))
        .collect();

    const MAX_SWEEPS: usize = 4;
    const COMPACT_ITERS: usize = 3;
    let mut total_moved = 0.0;
    let mut sweeps = 0usize;
    for _ in 0..MAX_SWEEPS {
        sweeps += 1;
        // settle corner-most parts first
        let mut order: Vec<usize> = (0..working.placements.len()).collect();
        order.sort_by(|&a, &b| {
            let pa = &working.placements[a];
            let pb = &working.placements[b];
            (pa.y + pa.x)
                .partial_cmp(&(pb.y + pb.x))
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        let mut sweep_moved = 0.0;
        for li in order {
            let p = working.placements[li].clone();
            let sheet_idx = p.sheet_index;
            let Some(sheet_sh) = sheet_prepared.get(sheet_idx).and_then(|o| o.clone()) else {
                continue;
            };
            let inst = &instances[p.instance_idx];
            let sheet = &solver_sheets[sheet_idx];
            let rot = p.rotation_deg;
            let (mut rmx, mut rmy) =
                rect_min_from_anchor(p.x, p.y, inst.part.width, inst.part.height, rot);
            let Some(session) = build_sheet_session(li, sheet_idx, working, &tracker, &sheet_sh)
            else {
                continue;
            };
            let ev = LBFEvaluator {
                inst,
                sheet,
                sheet_idx,
                session: &session,
                base: inst.base_shape.as_ref(),
                n_evals: 0,
            };
            let clear = |x: f64, y: f64| ev.score_lbf_candidate(x, y, rot).is_some();
            if !clear(rmx, rmy) {
                continue; // colliding part (partial layout) — leave it to the safety net
            }
            for _ in 0..COMPACT_ITERS {
                rmy = slide_axis(rmx, rmy, sheet.min_y, &clear, false);
                rmx = slide_axis(rmy, rmx, sheet.min_x, &clear, true);
            }
            let (ax, ay) =
                placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
            let d = (ax - p.x).abs() + (ay - p.y).abs();
            if d > 1e-6 {
                working.placements[li].x = ax;
                working.placements[li].y = ay;
                if let Some(sh) = transform_base_to_candidate(inst.base_shape.as_ref(), ax, ay, rot) {
                    tracker.shapes[li] = Some(Rc::new(sh));
                }
                sweep_moved += d;
            }
        }
        total_moved += sweep_moved;
        if sweep_moved < 1.0 {
            break;
        }
    }
    bpp.bpp_gravity_compaction_applied = true;
    bpp.bpp_gravity_compaction_sweeps = sweeps;
    bpp.bpp_gravity_moved_total_mm = total_moved;
}

/// Relabel the used sheets to the lowest available slot of matching dimensions
/// (existing-sheet-first appearance). Valid because identical sheets are interchangeable
/// slots; a used sheet only ever maps to an unused slot with the same width/height, so the
/// physical area reported per placement is unchanged.
fn compact_sheet_indices(layout: &mut SparrowLayout, solver_sheets: &[SheetShape]) {
    let used = used_sheet_set(layout);
    let mut taken: HashSet<usize> = HashSet::new();
    let mut assign: HashMap<usize, usize> = HashMap::new();
    for &u in &used {
        let (uw, uh) = (solver_sheets[u].width, solver_sheets[u].height);
        let target = (0..solver_sheets.len())
            .find(|&j| {
                !taken.contains(&j)
                    && (solver_sheets[j].width - uw).abs() < 1e-9
                    && (solver_sheets[j].height - uh).abs() < 1e-9
            })
            .unwrap_or(u);
        taken.insert(target);
        assign.insert(u, target);
    }
    for p in &mut layout.placements {
        if let Some(&t) = assign.get(&p.sheet_index) {
            p.sheet_index = t;
        }
    }
}

// ── main entry point ───────────────────────────────────────────────────────────

/// SGH-Q45: coroush-style BPP sheet-reduction multisheet solve. Returns the same
/// `FiniteStockRunResult` contract as the legacy subset-attempt manager so the adapter
/// / output path is unchanged.
pub(crate) fn run_bpp_sheet_reduction_multisheet(
    parts: &[crate::item::Part],
    stocks: &[Stock],
    rotation_context: &RotationResolveContext,
    extra_pre_unplaced: Vec<Unplaced>,
    config: FiniteStockRunConfig,
) -> FiniteStockRunResult {
    let started = Instant::now();
    let total_budget = config.time_limit_s.max(1.0);
    let total_instances: usize = parts.iter().map(|p| p.quantity as usize).sum();

    let original_sheets = match expand_sheets(stocks) {
        Ok(s) => s,
        Err(e) => return error_result(parts, extra_pre_unplaced, total_instances, &started, total_budget, format!("STOCK_BUILD_ERROR: {e}")),
    };
    let n = original_sheets.len();
    let solver_sheets: Vec<SheetShape> = match &config.solver_sheets_override {
        Some(ov) if ov.len() == n => ov.clone(),
        _ => original_sheets.clone(),
    };
    let all_sheets_with_orig: Vec<(SheetShape, usize)> =
        original_sheets.iter().cloned().enumerate().map(|(i, s)| (s, i)).collect();

    let core_config = SparrowConfig::from_solver_input(
        total_budget,
        config.backend.clone(),
        rotation_context.clone(),
        config.seed,
    )
    .with_spacing_mm(config.spacing_mm);
    let optimizer = SparrowOptimizer::new(core_config.clone());

    let problem = match SparrowProblem::from_solver_input(
        parts,
        &solver_sheets,
        rotation_context,
        extra_pre_unplaced.clone(),
        core_config.clone(),
    ) {
        Ok(p) => p,
        Err(e) => return error_result(parts, extra_pre_unplaced, total_instances, &started, total_budget, format!("PROBLEM_BUILD_ERROR: {e}")),
    };

    let instances: Vec<SPInstance> = problem.instances.clone();
    let pre_unplaced: Vec<Unplaced> = problem.pre_unplaced.clone();
    let mut diag = SparrowDiagnostics {
        invoked: true,
        native_model_active: true,
        native_tracker_active: true,
        native_problem_instances: instances.len(),
        ..SparrowDiagnostics::default()
    };
    let mut rng = DeterministicRng::new(config.seed);
    let mut bpp = BppReductionDiagnostics {
        bpp_reduction_active: true,
        ..Default::default()
    };

    crate::optimizer::cde_adapter::reset_query_cache();

    // area lower bound (on the geometry actually packed = solver sheets / offset parts)
    let max_sheet_area = solver_sheets.iter().map(|s| s.area).fold(0.0_f64, f64::max);
    let total_part_area: f64 = instances.iter().map(|i| part_polygon_area(&i.part)).sum();
    let area_lb = if max_sheet_area > 0.0 {
        ((total_part_area / max_sheet_area).ceil() as usize).max(1)
    } else {
        1
    };
    bpp.bpp_area_lower_bound = area_lb;

    // ── construction (ADAPTED bp_lbf): FFD+LBF seed + exploration over the pool ───
    // `build_native_constructive_seed` is the upstream LBF builder (geometry-correct,
    // bottom-left clear placements). It may spread items across the empty pool; the
    // reduction loop and the final sheet-index compaction restore a tight, low-index used
    // set. The exploration/separation pass resolves any residual collisions from the seed.
    let guard = final_guard_s(total_budget);
    let construct_deadline =
        (total_budget * 0.25).clamp(2.0, 180.0).min((total_budget - guard).max(1.0));
    let seed = build_native_constructive_seed(&problem);
    let mut working = if layout_is_full_feasible(&seed, &instances, &solver_sheets) {
        seed
    } else {
        let (_cf, solved) = run_subsolve(
            &optimizer, seed, &instances, &solver_sheets, &started, construct_deadline, &mut rng, &mut diag,
        );
        bpp.bpp_separator_calls += 1;
        solved
    };
    bpp.bpp_initial_sheet_count = used_sheet_set(&working).len();

    let construction_full = layout_is_full_feasible(&working, &instances, &solver_sheets);

    // ── sheet-reduction loop (ADAPTED bp_explore::bin_reduction_phase) ────────────
    if construction_full {
        let mut failed: HashSet<usize> = HashSet::new();
        let mut tried: HashSet<usize> = HashSet::new();
        let mut consec_failures = 0usize;
        loop {
            let used = used_sheet_set(&working);
            if used.len() <= area_lb {
                break;
            }
            if started.elapsed().as_secs_f64() >= total_budget - guard {
                break;
            }
            if consec_failures >= MAX_CONSEC_FAILURES {
                break;
            }
            let candidate = match select_candidate_sheet(&working, &instances, &solver_sheets, &used, &failed) {
                Some(c) => c,
                None => break,
            };
            bpp.bpp_elimination_attempts += 1;
            tried.insert(candidate);
            bpp.bpp_candidate_sheets_tried = tried.len();

            let receiving: Vec<usize> = used.iter().cloned().filter(|&s| s != candidate).collect();
            bpp.bpp_receiving_sheet_count_total += receiving.len();

            // displaced layout indices on the candidate, by shape-priority then area (Q47)
            let mut displaced: Vec<usize> = (0..working.placements.len())
                .filter(|&i| working.placements[i].sheet_index == candidate)
                .collect();
            displaced.sort_by(|&a, &b| {
                profile_order_key(&instances, working.placements[b].instance_idx)
                    .partial_cmp(&profile_order_key(&instances, working.placements[a].instance_idx))
                    .unwrap_or(std::cmp::Ordering::Equal)
            });
            bpp.bpp_displaced_items_total += displaced.len();

            let mut trial = working.clone();
            redistribute_displaced(
                &optimizer, &mut trial, &displaced, &receiving, &instances, &solver_sheets, &started, &mut rng, &mut diag, &mut bpp,
            );

            // affected-sheet-only separation
            let remaining = (total_budget - guard - started.elapsed().as_secs_f64()).max(1.0);
            let attempt_deadline = started.elapsed().as_secs_f64() + (remaining * 0.9).max(1.0);
            let (mut feasible, mut candidate_layout) = separate_affected_sheets(
                &optimizer, &trial, &receiving, &instances, &solver_sheets, &started, attempt_deadline, &mut rng, &mut diag,
            );
            bpp.bpp_separator_calls += 1;

            // explicit transfer/swap repair on residual collisions
            if !feasible {
                let rep_deadline = started.elapsed().as_secs_f64()
                    + ((total_budget - guard - started.elapsed().as_secs_f64()).max(1.0) * 0.5);
                feasible = resolve_by_transfers(
                    &optimizer, &mut candidate_layout, &receiving, &instances, &solver_sheets, &started, rep_deadline, &mut rng, &mut diag, &mut bpp,
                );
            }

            if feasible && layout_is_full_feasible(&candidate_layout, &instances, &solver_sheets) {
                // compact the receiving sheets, accept incumbent
                for &s in &receiving {
                    compact_sheet(&optimizer, &mut candidate_layout, s, &instances, &solver_sheets, &started, &mut rng, &mut diag, &mut bpp);
                }
                if layout_is_full_feasible(&candidate_layout, &instances, &solver_sheets) {
                    working = candidate_layout;
                    bpp.bpp_elimination_successes += 1;
                    bpp.bpp_incumbent_updates += 1;
                    failed.clear();
                    consec_failures = 0;
                    continue;
                }
            }
            // failure: keep incumbent, mark candidate failed
            bpp.bpp_elimination_failures += 1;
            failed.insert(candidate);
            bpp.bpp_failed_candidate_sheets = failed.len();
            consec_failures += 1;
            bpp.bpp_restore_count += 1;
            if consec_failures % PERTURB_AFTER_FAILURES == 0 {
                perturb_swap_between_sheets(&mut working, &used, &instances, &solver_sheets, &mut rng, &mut bpp);
                // re-validate after perturbation; if it broke feasibility, undo by re-running
                // a quick affected separation over all used sheets is unnecessary — try_swap
                // only accepts strict improvements so feasibility is preserved.
            }
        }
    }

    // SGH-Q46 M3: fixed-sheet region compression (Sparrow Alg.13 adaptation) — the density
    // driver. Incrementally shrink each sheet's usable region and re-separate, tucking parts
    // tighter (interlocking concave parts). Runs before gravity; uses the remaining budget.
    let compress_deadline = (total_budget - guard).max(started.elapsed().as_secs_f64() + 1.0);
    compress_layout(
        &optimizer, &mut working, &instances, &solver_sheets, &started, compress_deadline, &mut rng, &mut diag, &mut bpp,
    );

    // SGH-Q48: interlock-aware density compaction (opt-in VRS_BPP_DENSITY_COMPACT) — the real
    // density driver: re-place parts to the densest collision-free position (tucking into
    // concavities / interlocking), CDE-validated, before the gravity tidy. Default off.
    let density_deadline = (total_budget - guard).max(started.elapsed().as_secs_f64() + 1.0);
    density_compact_layout(
        &mut working, &instances, &solver_sheets, &started, density_deadline, &mut rng, &mut bpp,
    );

    // SGH-Q46 M2: gravity / bottom-left compaction post-pass (density + edge alignment).
    gravity_compact_layout(&mut working, &instances, &solver_sheets, &mut bpp);

    // Relabel surviving sheets to the lowest matching slots (existing-sheet-first output).
    compact_sheet_indices(&mut working, &solver_sheets);

    let final_full = layout_is_full_feasible(&working, &instances, &solver_sheets);
    bpp.bpp_final_sheet_count = used_sheet_set(&working).len();
    bpp.bpp_runtime_ms = started.elapsed().as_secs_f64() * 1000.0;
    let gap = bpp.bpp_final_sheet_count.saturating_sub(area_lb);
    bpp.bpp_gap_to_area_lower_bound = gap;
    bpp.bpp_minimality_status = if !final_full {
        "PARTIAL".to_string()
    } else if gap == 0 {
        "AREA_LOWER_BOUND_MATCHED".to_string()
    } else {
        "BEST_FOUND_NOT_PROVEN_MINIMAL".to_string()
    };

    // ── assemble FiniteStockRunResult ────────────────────────────────────────────
    let final_tracker = SparrowCollisionTracker::final_validation_tracker(&working, &instances, &solver_sheets);
    let (placements, unplaced, final_pairs, boundary_violations): (Vec<Placement>, Vec<Unplaced>, usize, usize) =
        if final_full {
            (project(&working, &instances), pre_unplaced.clone(), 0, 0)
        } else {
            // sanitize to a collision-free partial
            let raw = project(&working, &instances);
            let (kept, mut newly) = sanitize_partial(&working, &instances, &solver_sheets, &raw, REASON_BPP_STOCK_EXHAUSTED);
            let mut un = pre_unplaced.clone();
            un.append(&mut newly);
            (kept, un, 0, 0)
        };

    let (used_indices, used_area, placed_area, util_pct) =
        compute_utilization(&placements, parts, &all_sheets_with_orig);
    // SGH-Q47: per-part-type decision diagnostics (built before `placements` is moved).
    let shape_profile_diags =
        super::shape_profile::build_shape_profile_diagnostics(&instances, &placements);
    let placed_instances = placements.len();
    let unplaced_instances = unplaced.len();
    let feasible = final_full && unplaced.is_empty();
    let status = if feasible { "ok" } else { "partial" }.to_string();
    diag.collision_graph_final_pairs = final_tracker.colliding_pairs();
    diag.boundary_violations_final = final_tracker.boundary_violations();
    let runtime_ms = started.elapsed().as_secs_f64() * 1000.0;
    let deadline_hit = started.elapsed().as_secs_f64() >= total_budget;

    FiniteStockRunResult {
        placements,
        unplaced,
        status,
        stock_exhausted: !feasible,
        used_sheet_indices: used_indices,
        used_sheet_area: used_area,
        placed_part_area: placed_area,
        utilization_pct: util_pct,
        total_instances,
        placed_instances,
        unplaced_instances,
        attempts: bpp.bpp_elimination_attempts + 1,
        candidate_subsets: 0,
        best_full_solution_found: feasible,
        runtime_ms,
        time_limit_s: config.time_limit_s,
        deadline_hit,
        best_score: bpp.bpp_final_sheet_count as f64,
        best_core_diag: Some(diag),
        available_sheet_count: n,
        final_pairs,
        boundary_violations,
        attempt_diagnostics: vec![],
        bpp_diagnostics: Some(bpp),
        shape_profile_diagnostics: Some(shape_profile_diags),
    }
}

fn error_result(
    parts: &[crate::item::Part],
    extra_pre_unplaced: Vec<Unplaced>,
    total_instances: usize,
    started: &Instant,
    total_budget: f64,
    reason: String,
) -> FiniteStockRunResult {
    let unplaced: Vec<Unplaced> = parts
        .iter()
        .flat_map(|p| {
            let reason = reason.clone();
            (0..p.quantity as usize).map(move |i| Unplaced {
                instance_id: format!("{}#{i}", p.id),
                part_id: p.id.clone(),
                reason: reason.clone(),
            })
        })
        .chain(extra_pre_unplaced)
        .collect();
    let unplaced_instances = unplaced.len();
    FiniteStockRunResult {
        placements: vec![],
        unplaced,
        status: "partial".to_string(),
        stock_exhausted: true,
        used_sheet_indices: vec![],
        used_sheet_area: 0.0,
        placed_part_area: 0.0,
        utilization_pct: 0.0,
        total_instances,
        placed_instances: 0,
        unplaced_instances,
        attempts: 0,
        candidate_subsets: 0,
        best_full_solution_found: false,
        runtime_ms: started.elapsed().as_secs_f64() * 1000.0,
        time_limit_s: total_budget,
        deadline_hit: false,
        best_score: f64::MAX,
        best_core_diag: None,
        available_sheet_count: 0,
        final_pairs: 0,
        boundary_violations: 0,
        attempt_diagnostics: vec![],
        bpp_diagnostics: Some(BppReductionDiagnostics {
            bpp_reduction_active: true,
            bpp_minimality_status: "PARTIAL".to_string(),
            ..Default::default()
        }),
        shape_profile_diagnostics: None,
    }
}
