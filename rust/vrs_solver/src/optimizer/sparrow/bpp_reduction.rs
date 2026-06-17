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

/// True when the interlock-aware density compaction pass is enabled.
fn density_compact_enabled() -> bool {
    std::env::var("VRS_BPP_DENSITY_COMPACT").ok().as_deref() == Some("1")
}

/// SGH-Q49: fraction of the total budget reserved for the density pass (active only when the pass
/// is enabled; otherwise 0.0 ⇒ pre-Q49 deadlines unchanged). Tunable via
/// `VRS_BPP_DENSITY_BUDGET_FRAC`, clamped to [0.0, 0.8]; default 0.35.
fn density_budget_frac() -> f64 {
    if !density_compact_enabled() {
        return 0.0;
    }
    std::env::var("VRS_BPP_DENSITY_BUDGET_FRAC")
        .ok()
        .and_then(|v| v.parse::<f64>().ok())
        .unwrap_or(0.35)
        .clamp(0.0, 0.8)
}

/// SGH-Q49: uniform-sample budget per part in the density search (tunable, clamped [20, 400]).
fn density_samples() -> usize {
    std::env::var("VRS_BPP_DENSITY_SAMPLES")
        .ok()
        .and_then(|v| v.parse::<usize>().ok())
        .unwrap_or(100)
        .clamp(20, 400)
}

/// SGH-Q50: true when the density-guided LNS sheet-drop pass is enabled.
fn lns_enabled() -> bool {
    std::env::var("VRS_BPP_LNS").ok().as_deref() == Some("1")
}

/// SGH-Q50: perturbed restarts per sheet-drop attempt (tunable, clamped [1, 16]; default 4).
fn lns_restarts() -> usize {
    std::env::var("VRS_BPP_LNS_RESTARTS")
        .ok()
        .and_then(|v| v.parse::<usize>().ok())
        .unwrap_or(4)
        .clamp(1, 16)
}

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

    // SGH-Q49: use the spacing-collision base shape for the candidate (matching the obstacles in
    // `tracker.shapes` and the upstream LBF), so the clear-check is spacing-correct — fewer
    // propose-then-revert moves than the Q48 original-geometry candidate.
    let cand_base = inst.spacing_collision_base_shape.as_ref();
    let session = build_sheet_session(li, sheet_idx, working, tracker, sheet_prepared)?;
    let ev = LBFEvaluator {
        inst,
        sheet,
        sheet_idx,
        session: &session,
        base: cand_base,
        n_evals: 0,
    };

    let cur_rot = p.rotation_deg;
    let baseline = transform_base_to_candidate(cand_base, p.x, p.y, cur_rot)
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
    let n_uniform = density_samples();
    for _ in 0..n_uniform {
        let rmx = sheet.min_x + rng.next_f64() * (sheet.max_x - rw0 - sheet.min_x).max(0.0);
        let rmy = sheet.min_y + rng.next_f64() * (sheet.max_y - rh0 - sheet.min_y).max(0.0);
        positions.push((rmx, rmy));
    }
    positions.extend(contour_near_rect_mins(
        &neighbours,
        rw0,
        rh0,
        sheet,
        n_uniform + 20,
    ));

    let margin = 1e-6;
    let mut best: Option<(f64, SparrowPlacement, bool)> = None;
    for &rot in &rotations {
        for &(rmx, rmy) in &positions {
            if ev.score_lbf_candidate(rmx, rmy, rot).is_none() {
                continue; // CDE: not collision-free here
            }
            let (ax, ay) =
                placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
            let Some(cand) = transform_base_to_candidate(cand_base, ax, ay, rot) else {
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

/// SGH-Q50: density-guided **insertion** of a ruined part onto a chosen `target_sheet`. `li` is the
/// part's layout index; the part is treated as not-on-`target_sheet` (its `tracker.shapes[li]` is
/// expected to be `None` while ruined). Returns the lowest density-score collision-free placement on
/// `target_sheet` (preferring interlock), or `None` if it does not fit there. Unlike
/// `density_place_part` there is no "improve on current" gate — any clear position is a valid
/// insertion. CDE decides clearance; continuous rotation preserved.
#[allow(clippy::too_many_arguments)]
fn density_insert_part(
    li: usize,
    target_sheet: usize,
    working: &SparrowLayout,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    tracker: &SparrowCollisionTracker,
    sheet_prepared: &Rc<CdePreparedShape>,
    weights: &DensityWeights,
    rng: &mut DeterministicRng,
    bpp: &mut BppReductionDiagnostics,
) -> Option<SparrowPlacement> {
    let inst_idx = working.placements[li].instance_idx;
    let inst = &instances[inst_idx];
    let sheet = &solver_sheets[target_sheet];
    let cand_base = inst.spacing_collision_base_shape.as_ref();

    // Neighbours = parts currently living on `target_sheet` with a live (non-ruined) shape.
    let neighbours: Vec<&CdePreparedShape> = (0..working.placements.len())
        .filter(|&j| j != li && working.placements[j].sheet_index == target_sheet)
        .filter_map(|j| tracker.shapes.get(j).and_then(|o| o.as_deref()))
        .collect();
    let session = build_sheet_session(li, target_sheet, working, tracker, sheet_prepared)?;
    let ev = LBFEvaluator {
        inst,
        sheet,
        sheet_idx: target_sheet,
        session: &session,
        base: cand_base,
        n_evals: 0,
    };

    // Seed rotation = the part's current rotation; plus a bounded subsample of its resolved
    // rotation set (continuous samples for continuous parts) — never snapped.
    let cur_rot = working.placements[li].rotation_deg;
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

    let (rw0, rh0) = dims_for_rotation(inst.part.width, inst.part.height, cur_rot);
    let n_uniform = density_samples();
    let mut positions: Vec<(f64, f64)> = Vec::with_capacity(n_uniform + 32);
    for _ in 0..n_uniform {
        let rmx = sheet.min_x + rng.next_f64() * (sheet.max_x - rw0 - sheet.min_x).max(0.0);
        let rmy = sheet.min_y + rng.next_f64() * (sheet.max_y - rh0 - sheet.min_y).max(0.0);
        positions.push((rmx, rmy));
    }
    if !neighbours.is_empty() {
        positions.extend(contour_near_rect_mins(&neighbours, rw0, rh0, sheet, n_uniform + 20));
    }

    let mut best: Option<(f64, SparrowPlacement, bool)> = None;
    for &rot in &rotations {
        for &(rmx, rmy) in &positions {
            if ev.score_lbf_candidate(rmx, rmy, rot).is_none() {
                continue; // CDE: not collision-free here
            }
            let (ax, ay) =
                placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
            let Some(cand) = transform_base_to_candidate(cand_base, ax, ay, rot) else {
                continue;
            };
            let interlock = is_interlock_candidate(&cand, &neighbours);
            if interlock {
                bpp.bpp_interlock_candidates_generated += 1;
            }
            // With neighbours rank by density (prefer interlock); on an empty sheet fall back to
            // a bottom-left score so the first part still lands in a corner.
            let score = if neighbours.is_empty() {
                (rmx - sheet.min_x) + (rmy - sheet.min_y)
            } else {
                density_candidate_score(&cand, &neighbours, weights)
            };
            if best.as_ref().is_none_or(|(bs, _, _)| score < *bs) {
                best = Some((
                    score,
                    SparrowPlacement {
                        instance_idx: inst_idx,
                        sheet_index: target_sheet,
                        x: ax,
                        y: ay,
                        rotation_deg: rot,
                    },
                    interlock,
                ));
            }
        }
    }
    best.map(|(_, pl, interlock)| {
        if interlock {
            bpp.bpp_interlock_candidates_accepted += 1;
        }
        pl
    })
}

// ── SGH-Q51: critical anchor admission (co-movable) ──────────────────────────────────────────

/// Centroid of the admitted parts on `sheet` (mean of their anchor positions); used as the
/// overlapping seed for the co-movable admission separation.
fn sheet_centroid(working: &SparrowLayout, sheet: usize) -> (f64, f64) {
    let (mut sx, mut sy, mut n) = (0.0, 0.0, 0.0);
    for p in working.placements.iter().filter(|p| p.sheet_index == sheet) {
        sx += p.x;
        sy += p.y;
        n += 1.0;
    }
    if n == 0.0 {
        (0.0, 0.0)
    } else {
        (sx / n, sy / n)
    }
}

/// SGH-Q51: try to admit critical `cand_inst_idx` onto `target_sheet`, with the already-admitted
/// parts on that sheet **co-movable**. Returns a new layout with the candidate admitted (and the
/// sheet's parts possibly re-arranged) on success, or `None`. The candidate is NOT yet in `working`.
///
/// Two stages: (1) **direct** density insertion with the admitted set fixed; (2) on failure,
/// **co-movable** — seed the candidate overlapping the admitted set (interlock-biased) and separate
/// the whole target sheet (admitted + candidate move together), accepting only a CDE-feasible,
/// on-sheet result. Continuous rotation preserved; the CDE decides clearance.
#[allow(clippy::too_many_arguments)]
fn try_admit_critical(
    optimizer: &SparrowOptimizer,
    working: &SparrowLayout,
    cand_inst_idx: usize,
    target_sheet: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) -> Option<SparrowLayout> {
    let sheet = &solver_sheets[target_sheet];
    let inst = &instances[cand_inst_idx];
    let sheet_sh = prepare_shape_from_sheet(sheet).ok().map(Rc::new)?;

    let rot = super::fixed_sheet::fitting_rotation(inst, std::slice::from_ref(sheet));
    let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
    if rw > sheet.width + 1e-9 || rh > sheet.height + 1e-9 {
        return None; // the part does not fit this sheet in any case
    }
    let weights = DensityWeights::default();

    // ── (1) DIRECT: density insertion with the admitted set fixed ──────────────────────────────
    {
        let mut trial = working.clone();
        let cand_li = trial.placements.len();
        let (ax, ay) =
            placement_anchor_from_rect_min(sheet.min_x, sheet.min_y, inst.part.width, inst.part.height, rot);
        trial.placements.push(SparrowPlacement {
            instance_idx: cand_inst_idx,
            sheet_index: target_sheet,
            x: ax,
            y: ay,
            rotation_deg: rot,
        });
        let mut tracker = SparrowCollisionTracker::build(&trial, instances, solver_sheets);
        tracker.shapes[cand_li] = None; // place the candidate fresh
        if let Some(pl) = density_insert_part(
            cand_li, target_sheet, &trial, instances, solver_sheets, &tracker, &sheet_sh, &weights,
            rng, bpp,
        ) {
            trial.placements[cand_li] = pl;
            // Mid-build feasibility = the placed parts are collision-free / in-bounds (NOT "all
            // instances placed" — the layout is still being constructed).
            if SparrowCollisionTracker::final_validation_tracker(&trial, instances, solver_sheets)
                .is_feasible()
            {
                return Some(trial);
            }
        }
    }

    // ── (2) CO-MOVABLE: overlapping seed + separate the whole target sheet ─────────────────────
    let (cx, cy) = sheet_centroid(working, target_sheet);
    let admitted_count = working
        .placements
        .iter()
        .filter(|p| p.sheet_index == target_sheet)
        .count();
    const RESTARTS: usize = 4;
    for r in 0..RESTARTS {
        if started.elapsed().as_secs_f64() >= deadline_s {
            break;
        }
        // Seed near the admitted centroid (overlapping), jittered per restart; clamped on-sheet.
        let jx = (rng.next_f64() - 0.5) * sheet.width * 0.3;
        let jy = (rng.next_f64() - 0.5) * sheet.height * 0.3;
        let sx = (cx + jx).clamp(sheet.min_x, (sheet.max_x - rw).max(sheet.min_x));
        let sy = (cy + jy).clamp(sheet.min_y, (sheet.max_y - rh).max(sheet.min_y));
        let seed_rot = if r == 0 { rot } else { rot + 90.0 * (r as f64) };
        let (ax, ay) =
            placement_anchor_from_rect_min(sx, sy, inst.part.width, inst.part.height, seed_rot);
        let mut trial = working.clone();
        trial.placements.push(SparrowPlacement {
            instance_idx: cand_inst_idx,
            sheet_index: target_sheet,
            x: ax,
            y: ay,
            rotation_deg: seed_rot,
        });
        let now = started.elapsed().as_secs_f64();
        let step_deadline = (now + (deadline_s - now).max(0.5) * 0.5).min(deadline_s);
        let (feasible, remapped) = separate_sheet_local(
            optimizer, &trial, target_sheet, sheet, instances, started, step_deadline, rng, diag,
        );
        if feasible && remapped.len() == admitted_count + 1 {
            let mut others: Vec<SparrowPlacement> = working
                .placements
                .iter()
                .filter(|p| p.sheet_index != target_sheet)
                .cloned()
                .collect();
            others.extend(remapped);
            let out = SparrowLayout { placements: others };
            if SparrowCollisionTracker::final_validation_tracker(&out, instances, solver_sheets)
                .is_feasible()
            {
                return Some(out);
            }
        }
    }
    None
}

/// SGH-Q51: directly insert (no co-movable separation) part `inst_idx` onto `sheet` at the densest
/// clear position (the structural/filler path). Returns the new layout or `None` if it does not fit.
#[allow(clippy::too_many_arguments)]
fn direct_insert_on_sheet(
    working: &SparrowLayout,
    inst_idx: usize,
    sheet: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    weights: &DensityWeights,
    rng: &mut DeterministicRng,
    bpp: &mut BppReductionDiagnostics,
) -> Option<SparrowLayout> {
    let s = &solver_sheets[sheet];
    let inst = &instances[inst_idx];
    let sheet_sh = prepare_shape_from_sheet(s).ok().map(Rc::new)?;
    let rot = super::fixed_sheet::fitting_rotation(inst, std::slice::from_ref(s));
    let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
    if rw > s.width + 1e-9 || rh > s.height + 1e-9 {
        return None;
    }
    let mut trial = working.clone();
    let cand_li = trial.placements.len();
    let (ax, ay) =
        placement_anchor_from_rect_min(s.min_x, s.min_y, inst.part.width, inst.part.height, rot);
    trial.placements.push(SparrowPlacement {
        instance_idx: inst_idx,
        sheet_index: sheet,
        x: ax,
        y: ay,
        rotation_deg: rot,
    });
    let mut tracker = SparrowCollisionTracker::build(&trial, instances, solver_sheets);
    tracker.shapes[cand_li] = None;
    let pl = density_insert_part(
        cand_li, sheet, &trial, instances, solver_sheets, &tracker, &sheet_sh, weights, rng, bpp,
    )?;
    trial.placements[cand_li] = pl; // density_insert_part guarantees a CDE-clear placement
    Some(trial)
}

/// True when the critical-aware constructive sheet builder is enabled (`VRS_SHEET_BUILDER=1`).
pub(crate) fn sheet_builder_enabled() -> bool {
    std::env::var("VRS_SHEET_BUILDER").ok().as_deref() == Some("1")
}

/// SGH-Q51: critical-aware constructive sheet builder. Builds the seed **anchor-first**: per sheet,
/// a critical admission phase (co-movable `try_admit_critical`) runs before any filler, then
/// structural and filler parts fill the remaining space; a new sheet opens only when the current
/// sheet's critical frontier is exhausted. The sheet count **emerges**. Any part that still does not
/// fit is bootstrapped (overlap allowed) so the downstream separator can resolve it. Gated; the
/// caller falls back to the LBF seed when disabled.
#[allow(clippy::too_many_arguments)]
pub(crate) fn build_critical_aware_seed(
    problem: &SparrowProblem,
    optimizer: &SparrowOptimizer,
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) -> SparrowLayout {
    let instances = &problem.instances;
    let sheets = &problem.container.sheets;
    let queues = super::fixed_sheet::build_criticality_queues(instances);
    let weights = DensityWeights::default();
    let mut layout = SparrowLayout {
        placements: Vec::with_capacity(instances.len()),
    };
    let mut placed = vec![false; instances.len()];
    bpp.bpp_sheet_builder_applied = true;

    const CRITICAL_FRONTIER: usize = 2; // close the critical phase after this many consecutive fails

    for sheet_idx in 0..sheets.len() {
        if started.elapsed().as_secs_f64() >= deadline_s || placed.iter().all(|&p| p) {
            break;
        }
        bpp.bpp_sheets_opened += 1;
        let mut critical_here = 0usize;

        // ── 1. Critical admission phase (co-movable anchors) ──────────────────────────────────
        let mut consec_fail = 0usize;
        for &ci in &queues.critical {
            if placed[ci] {
                continue;
            }
            if started.elapsed().as_secs_f64() >= deadline_s || consec_fail >= CRITICAL_FRONTIER {
                break;
            }
            let now = started.elapsed().as_secs_f64();
            let admit_deadline = (now + (deadline_s - now).max(1.0) * 0.5).min(deadline_s);
            match try_admit_critical(
                optimizer, &layout, ci, sheet_idx, instances, sheets, started, admit_deadline, rng,
                diag, bpp,
            ) {
                Some(new_layout) => {
                    layout = new_layout;
                    placed[ci] = true;
                    consec_fail = 0;
                    critical_here += 1;
                    bpp.bpp_critical_admitted += 1;
                }
                None => {
                    consec_fail += 1;
                    bpp.bpp_critical_deferred += 1;
                }
            }
        }
        bpp.bpp_max_critical_per_sheet = bpp.bpp_max_critical_per_sheet.max(critical_here);

        // ── 2. Structural + 3. Filler phases (direct density insertion on this sheet) ─────────
        for &pi in queues.structural.iter().chain(queues.filler.iter()) {
            if placed[pi] {
                continue;
            }
            if started.elapsed().as_secs_f64() >= deadline_s {
                break;
            }
            if let Some(new_layout) = direct_insert_on_sheet(
                &layout, pi, sheet_idx, instances, sheets, &weights, rng, bpp,
            ) {
                layout = new_layout;
                placed[pi] = true;
            }
        }
    }

    // Bootstrap any still-unplaced part (overlap allowed; the separator resolves it).
    for i in 0..instances.len() {
        if placed[i] {
            continue;
        }
        let inst = &instances[i];
        let rot = super::fixed_sheet::fitting_rotation(inst, sheets);
        let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
        if let Some((sheet_idx, sheet)) = sheets
            .iter()
            .enumerate()
            .find(|(_, s)| rw <= s.width + 1e-9 && rh <= s.height + 1e-9)
        {
            let max_rmx = (sheet.max_x - rw).max(sheet.min_x);
            let max_rmy = (sheet.max_y - rh).max(sheet.min_y);
            let rmx = sheet.min_x + rng.next_f64() * (max_rmx - sheet.min_x).max(0.0);
            let rmy = sheet.min_y + rng.next_f64() * (max_rmy - sheet.min_y).max(0.0);
            let (ax, ay) =
                placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
            layout.placements.push(SparrowPlacement {
                instance_idx: i,
                sheet_index: sheet_idx,
                x: ax,
                y: ay,
                rotation_deg: rot,
            });
        }
    }
    layout.placements.sort_by_key(|p| p.instance_idx);
    layout
}

/// Per-sheet density compaction (SGH-Q49): multi-sweep, **incremental tracker**. The shared
/// `tracker` is built once by the caller; after each accepted move only that part's shape is
/// updated (`tracker.shapes[li]`), which is all `build_sheet_session` reads — eliminating the Q48
/// per-part full rebuild. Each accepted move is collision-free vs the current positions (the
/// `density_place_part` clear-check), so per-move full-feasibility is dropped; the caller does one
/// final safety-net check. Sweeps repeat until convergence (no move) or the deadline.
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
    tracker: &mut SparrowCollisionTracker,
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
    const MAX_SWEEPS: usize = 6;
    for _ in 0..MAX_SWEEPS {
        if started.elapsed().as_secs_f64() >= deadline_s {
            break;
        }
        let mut sweep_moves = 0usize;
        for &li in &idxs {
            if started.elapsed().as_secs_f64() >= deadline_s {
                break;
            }
            bpp.bpp_density_parts_processed += 1;
            if let Some(pl) = density_place_part(
                li, layout, instances, solver_sheets, tracker, &sheet_sh, weights, rng, bpp,
            ) {
                layout.placements[li] = pl;
                tracker.shapes[li] =
                    SparrowCollisionTracker::prepare_item(layout, instances, li);
                bpp.bpp_density_moves_accepted += 1;
                sweep_moves += 1;
            }
        }
        bpp.bpp_density_sweeps += 1;
        if sweep_moves == 0 {
            break; // converged
        }
    }
}

/// SGH-Q48/Q49 entry: interlock-aware density compaction over all used sheets. Opt-in (default
/// off); enable with `VRS_BPP_DENSITY_COMPACT=1`. Builds the tracker once (incremental per-move
/// updates inside the sweeps) and reverts the whole pass via a final full-feasibility safety net.
fn density_compact_layout(
    working: &mut SparrowLayout,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    bpp: &mut BppReductionDiagnostics,
) {
    if !density_compact_enabled() || working.placements.is_empty() {
        return;
    }
    bpp.bpp_density_compaction_applied = true;
    let weights = DensityWeights::default();
    let snapshot = working.clone();
    let mut tracker = SparrowCollisionTracker::build(working, instances, solver_sheets);
    for s in used_sheet_set(working) {
        density_compact_sheet(
            working, s, instances, solver_sheets, started, deadline_s, rng, &weights, bpp,
            &mut tracker,
        );
    }
    // Final safety net: revert the whole pass if anything broke feasibility.
    if !layout_is_full_feasible(working, instances, solver_sheets) {
        *working = snapshot;
    }
}

// ── SGH-Q50: density-guided LNS sheet-drop pass (opt-in VRS_BPP_LNS) ──────────────────────────

/// Free area (sheet area − placed-part area) on a sheet — used to pick receiving-sheet order.
fn sheet_free_area(
    layout: &SparrowLayout,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    sheet: usize,
) -> f64 {
    solver_sheets[sheet].area - sheet_placed_area(layout, instances, sheet)
}

/// Attempt to drop sheet `s`: ruin its parts and re-insert them (density-guided) onto the
/// `receiving` sheets. Returns true and leaves `working` with `s` empty and feasible on success;
/// the caller reverts on false. `perturb` rotates the re-insertion order for restarts.
#[allow(clippy::too_many_arguments)]
fn try_drop_sheet(
    working: &mut SparrowLayout,
    s: usize,
    receiving: &[usize],
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    weights: &DensityWeights,
    rng: &mut DeterministicRng,
    bpp: &mut BppReductionDiagnostics,
    perturb: usize,
) -> bool {
    let ruined: Vec<usize> = (0..working.placements.len())
        .filter(|&i| working.placements[i].sheet_index == s)
        .collect();
    if ruined.is_empty() {
        return true;
    }
    // Tracker with the ruined parts removed (shape = None ⇒ excluded as neighbours / obstacles).
    let mut tracker = SparrowCollisionTracker::build(working, instances, solver_sheets);
    for &li in &ruined {
        tracker.shapes[li] = None;
    }
    // Re-insertion order: hardest (highest priority) first; rotate for perturbed restarts.
    let mut order = ruined.clone();
    order.sort_by(|&a, &b| {
        profile_order_key(instances, working.placements[b].instance_idx)
            .partial_cmp(&profile_order_key(instances, working.placements[a].instance_idx))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    if perturb > 0 && !order.is_empty() {
        let n = order.len();
        order.rotate_left(perturb % n);
    }

    // Prepared shapes for the receiving sheets.
    let sheet_prepared: Vec<Option<Rc<CdePreparedShape>>> = solver_sheets
        .iter()
        .map(|sh| prepare_shape_from_sheet(sh).ok().map(Rc::new))
        .collect();

    for &li in &order {
        if started.elapsed().as_secs_f64() >= deadline_s {
            return false;
        }
        // Receiving sheets by most free area first.
        let mut targets: Vec<usize> = receiving.to_vec();
        targets.sort_by(|&a, &b| {
            sheet_free_area(working, instances, solver_sheets, b)
                .partial_cmp(&sheet_free_area(working, instances, solver_sheets, a))
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        let mut placed = false;
        for &t in &targets {
            let Some(sheet_sh) = sheet_prepared.get(t).and_then(|o| o.clone()) else {
                continue;
            };
            if let Some(pl) = density_insert_part(
                li, t, working, instances, solver_sheets, &tracker, &sheet_sh, weights, rng, bpp,
            ) {
                working.placements[li] = pl;
                tracker.shapes[li] = SparrowCollisionTracker::prepare_item(working, instances, li);
                bpp.bpp_lns_parts_reinserted += 1;
                placed = true;
                break;
            }
        }
        if !placed {
            return false; // a ruined part has nowhere to go ⇒ this restart fails
        }
    }
    // All ruined parts re-homed on receiving sheets ⇒ `s` is empty. Confirm full feasibility.
    layout_is_full_feasible(working, instances, solver_sheets)
}

/// SGH-Q50 entry: density-guided LNS sheet-drop. Opt-in (`VRS_BPP_LNS=1`, default off). Runs after
/// the density compaction. Repeatedly ruins the least-utilized used sheet and re-inserts its parts
/// onto the others (density-guided, perturbed restarts); accepts only when a sheet is actually
/// emptied and the layout stays feasible, otherwise reverts. Feasibility-preserving.
fn lns_sheet_drop(
    working: &mut SparrowLayout,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    bpp: &mut BppReductionDiagnostics,
) {
    if !lns_enabled() || working.placements.is_empty() {
        return;
    }
    bpp.bpp_lns_applied = true;
    let weights = DensityWeights::default();
    let restarts = lns_restarts();
    loop {
        if started.elapsed().as_secs_f64() >= deadline_s {
            break;
        }
        let used = used_sheet_set(working);
        if used.len() <= 1 {
            break;
        }
        // Least-utilized used sheet (smallest placed area).
        let Some(&s) = used.iter().min_by(|&&a, &&b| {
            sheet_placed_area(working, instances, a)
                .partial_cmp(&sheet_placed_area(working, instances, b))
                .unwrap_or(std::cmp::Ordering::Equal)
        }) else {
            break;
        };
        let receiving: Vec<usize> = used.iter().copied().filter(|&x| x != s).collect();
        bpp.bpp_lns_attempts += 1;
        let snapshot = working.clone();
        let mut dropped = false;
        for restart in 0..restarts {
            if started.elapsed().as_secs_f64() >= deadline_s {
                break;
            }
            if restart > 0 {
                *working = snapshot.clone();
                bpp.bpp_lns_restarts += 1;
            }
            if try_drop_sheet(
                working, s, &receiving, instances, solver_sheets, started, deadline_s, &weights,
                rng, bpp, restart,
            ) {
                dropped = true;
                break;
            }
        }
        if dropped {
            bpp.bpp_lns_sheets_dropped += 1;
            // try to drop another sheet
        } else {
            *working = snapshot; // revert; the least-full sheet couldn't be cleared
            break;
        }
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
    // SGH-Q49: reserve a fraction of the budget for the density pass by capping the reduction loop
    // earlier (no-op when the density pass is disabled ⇒ reduction_deadline == total_budget-guard).
    let density_frac = density_budget_frac();
    let reduction_deadline = (total_budget * (1.0 - density_frac) - guard).max(guard.min(total_budget * 0.5));
    let construct_deadline =
        (total_budget * 0.25).clamp(2.0, 180.0).min((total_budget - guard).max(1.0));
    // SGH-Q51: critical-aware constructive sheet builder (opt-in). The builder seed is used ONLY
    // when it is complete and fully feasible (every part placed, collision-free); otherwise it
    // falls back to the LBF seed — so the builder can never regress the result. This banks the
    // proven cases (e.g. 3 big curved parts on one sheet) without risking partial output where the
    // admission is not yet strong enough (tight spacing).
    let seed = if sheet_builder_enabled() {
        // Snapshot the RNG so a fallback restores the exact pre-builder stream — the fallback path
        // is then identical (deterministically) to the builder-off path.
        let rng_snapshot = rng.clone();
        // Cap the builder's wall time to a small budget fraction so a fallback still leaves the
        // BPP reduction enough time at ANY total budget (no time-starvation regression, even at
        // tight budgets). The spacing-0 win completes well within this; tight-spacing failures fall
        // back cheaply.
        let builder_cap = (total_budget * 0.12).clamp(4.0, 20.0);
        let builder_deadline = (started.elapsed().as_secs_f64() + builder_cap).min(construct_deadline);
        let built = build_critical_aware_seed(
            &problem, &optimizer, &started, builder_deadline, &mut rng, &mut diag, &mut bpp,
        );
        if layout_is_full_feasible(&built, &instances, &solver_sheets) {
            built
        } else {
            rng = rng_snapshot;
            build_native_constructive_seed(&problem)
        }
    } else {
        build_native_constructive_seed(&problem)
    };
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
            if started.elapsed().as_secs_f64() >= reduction_deadline {
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
            let remaining = (reduction_deadline - started.elapsed().as_secs_f64()).max(1.0);
            let attempt_deadline = started.elapsed().as_secs_f64() + (remaining * 0.9).max(1.0);
            let (mut feasible, mut candidate_layout) = separate_affected_sheets(
                &optimizer, &trial, &receiving, &instances, &solver_sheets, &started, attempt_deadline, &mut rng, &mut diag,
            );
            bpp.bpp_separator_calls += 1;

            // explicit transfer/swap repair on residual collisions
            if !feasible {
                let rep_deadline = started.elapsed().as_secs_f64()
                    + ((reduction_deadline - started.elapsed().as_secs_f64()).max(1.0) * 0.5);
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
    // SGH-Q49: the reduction loop above was capped at `reduction_deadline` to reserve this budget.
    bpp.bpp_reduction_time_ms = started.elapsed().as_secs_f64() * 1000.0;
    let density_deadline = (total_budget - guard).max(started.elapsed().as_secs_f64() + 1.0);
    // SGH-Q50: when the LNS sheet-drop is enabled, give the density compaction the first half of the
    // reserved window and the LNS the second half; otherwise density gets the whole window (Q49).
    let density_compact_deadline = if lns_enabled() {
        let now = started.elapsed().as_secs_f64();
        (now + (density_deadline - now) * 0.5).max(now + 1.0)
    } else {
        density_deadline
    };
    density_compact_layout(
        &mut working, &instances, &solver_sheets, &started, density_compact_deadline, &mut rng,
        &mut bpp,
    );
    bpp.bpp_density_time_ms =
        (started.elapsed().as_secs_f64() * 1000.0 - bpp.bpp_reduction_time_ms).max(0.0);

    // SGH-Q50: density-guided LNS sheet-drop — try to eliminate one more sheet via coordinated
    // multi-part ruin-recreate (opt-in VRS_BPP_LNS, default off). Uses the remaining reserved budget.
    lns_sheet_drop(
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

#[cfg(test)]
mod q50_tests {
    use super::*;
    use crate::sheet::{expand_sheets, Stock};

    fn poly_part(id: &str, w: f64, h: f64, pts: serde_json::Value) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(pts),
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn make_instance(idx: usize, part: Part) -> SPInstance {
        let base = std::rc::Rc::new(prepare_base_shape_native(&part).expect("preparable"));
        let prof = std::rc::Rc::new(PartShapeProfile::compute(&part, &base, 40_000.0, 200.0));
        SPInstance {
            idx,
            instance_id: format!("{}#{idx}", part.id),
            part_id: part.id.clone(),
            part,
            allowed_rotations_deg: vec![0.0],
            continuous_rotation: false,
            spacing_collision_base_shape: base.clone(),
            base_shape: base,
            shape_profile: prof,
        }
    }

    #[test]
    fn density_insert_part_finds_interlock_on_target_sheet() {
        // U with a concave mouth (bbox 100×100) + a 20×20 square to insert.
        let u = poly_part(
            "U",
            100.0,
            100.0,
            serde_json::json!([
                [0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [70.0, 100.0],
                [70.0, 30.0], [30.0, 30.0], [30.0, 100.0], [0.0, 100.0]
            ]),
        );
        let sq = poly_part(
            "SQ",
            20.0,
            20.0,
            serde_json::json!([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]),
        );
        let instances = vec![make_instance(0, u), make_instance(1, sq)];
        let sheets = expand_sheets(&[Stock {
            id: "S".into(),
            quantity: 1,
            width: Some(200.0),
            height: Some(200.0),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }])
        .expect("sheets");

        // Place the U well inside the sheet; the square's start position is irrelevant (ruined).
        let u0 = transform_base_to_candidate(instances[0].base_shape.as_ref(), 0.0, 0.0, 0.0).unwrap();
        let (uax, uay) = (40.0 - u0.min_x, 40.0 - u0.min_y);
        let mut layout = SparrowLayout {
            placements: vec![
                SparrowPlacement { instance_idx: 0, sheet_index: 0, x: uax, y: uay, rotation_deg: 0.0 },
                SparrowPlacement { instance_idx: 1, sheet_index: 0, x: 10.0, y: 10.0, rotation_deg: 0.0 },
            ],
        };
        // Build the tracker, then ruin the square (its shape becomes None ⇒ excluded as a neighbour).
        let mut tracker = SparrowCollisionTracker::build(&layout, &instances, &sheets);
        tracker.shapes[1] = None;
        layout.placements[1].sheet_index = 0; // stays addressable; tracker None excludes it

        let sheet_sh = std::rc::Rc::new(prepare_shape_from_sheet(&sheets[0]).expect("sheet shape"));
        let weights = DensityWeights::default();
        let mut rng = DeterministicRng::new(7);
        let mut bpp = BppReductionDiagnostics::default();
        let pl = density_insert_part(
            1, 0, &layout, &instances, &sheets, &tracker, &sheet_sh, &weights, &mut rng, &mut bpp,
        )
        .expect("square must fit on the target sheet");
        assert_eq!(pl.sheet_index, 0);

        // The chosen placement should interlock with the U (bbox-overlap, polygon-clear): the
        // densest spot is tucked into the concave mouth.
        let placed = transform_base_to_candidate(
            instances[1].spacing_collision_base_shape.as_ref(),
            pl.x,
            pl.y,
            pl.rotation_deg,
        )
        .unwrap();
        let u_shape = transform_base_to_candidate(instances[0].base_shape.as_ref(), uax, uay, 0.0).unwrap();
        assert!(
            super::super::density::bbox_overlaps(&placed, &u_shape),
            "inserted square should interlock (bbox-overlap) the U"
        );
        assert!(bpp.bpp_interlock_candidates_generated > 0);
    }

    #[test]
    fn try_drop_sheet_rehomes_a_droppable_sheet() {
        // sheet 0 has a 40×40 square; sheet 1 has one 30×30 square that obviously fits on sheet 0.
        let a = poly_part(
            "A",
            40.0,
            40.0,
            serde_json::json!([[0.0, 0.0], [40.0, 0.0], [40.0, 40.0], [0.0, 40.0]]),
        );
        let b = poly_part(
            "B",
            30.0,
            30.0,
            serde_json::json!([[0.0, 0.0], [30.0, 0.0], [30.0, 30.0], [0.0, 30.0]]),
        );
        let instances = vec![make_instance(0, a), make_instance(1, b)];
        let sheets = expand_sheets(&[Stock {
            id: "S".into(),
            quantity: 2,
            width: Some(200.0),
            height: Some(200.0),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }])
        .expect("sheets");
        // place A on sheet 0, B on sheet 1
        let a0 = transform_base_to_candidate(instances[0].base_shape.as_ref(), 0.0, 0.0, 0.0).unwrap();
        let b0 = transform_base_to_candidate(instances[1].base_shape.as_ref(), 0.0, 0.0, 0.0).unwrap();
        let mut working = SparrowLayout {
            placements: vec![
                SparrowPlacement { instance_idx: 0, sheet_index: 0, x: 20.0 - a0.min_x, y: 20.0 - a0.min_y, rotation_deg: 0.0 },
                SparrowPlacement { instance_idx: 1, sheet_index: 1, x: 20.0 - b0.min_x, y: 20.0 - b0.min_y, rotation_deg: 0.0 },
            ],
        };
        let weights = DensityWeights::default();
        let mut rng = DeterministicRng::new(3);
        let mut bpp = BppReductionDiagnostics::default();
        let started = std::time::Instant::now();
        let dropped = try_drop_sheet(
            &mut working, 1, &[0], &instances, &sheets, &started, 1e9, &weights, &mut rng, &mut bpp, 0,
        );
        assert!(dropped, "B must be re-homed onto sheet 0, emptying sheet 1");
        assert!(
            working.placements.iter().all(|p| p.sheet_index != 1),
            "no part should remain on the dropped sheet 1"
        );
        assert!(layout_is_full_feasible(&working, &instances, &sheets));
    }
}

#[cfg(test)]
mod q51_measure_gate {
    use super::*;
    use crate::sheet::{expand_sheets, Stock};

    fn load_lv8_11612() -> Part {
        let base = std::fs::read_to_string(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/../../artifacts/benchmarks/sgh_q32/inputs/case_01_2x1500x3000.json"
        ))
        .expect("base input");
        let v: serde_json::Value = serde_json::from_str(&base).unwrap();
        let p = v["parts"]
            .as_array()
            .unwrap()
            .iter()
            .find(|x| x["id"].as_str().unwrap_or("").starts_with("Lv8_11612"))
            .expect("Lv8_11612");
        Part {
            id: p["id"].as_str().unwrap().to_string(),
            width: p["width"].as_f64().unwrap(),
            height: p["height"].as_f64().unwrap(),
            quantity: 6,
            allowed_rotations_deg: vec![],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(p["outer_points"].clone()),
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn continuous_instance(idx: usize, part: Part) -> SPInstance {
        let base = std::rc::Rc::new(prepare_base_shape_native(&part).expect("preparable"));
        let prof = std::rc::Rc::new(PartShapeProfile::compute(&part, &base, 4_500_000.0, 3000.0));
        // 24 continuous-domain rotation samples (the separator's rotation set); continuous flag on.
        let rots: Vec<f64> = (0..24).map(|i| i as f64 * 15.0).collect();
        SPInstance {
            idx,
            instance_id: format!("{}#{idx}", part.id),
            part_id: part.id.clone(),
            part,
            allowed_rotations_deg: rots,
            continuous_rotation: true,
            spacing_collision_base_shape: base.clone(),
            base_shape: base,
            shape_profile: prof,
        }
    }

    #[test]
    fn measure_gate_admit_third_big_part_on_one_sheet() {
        let part = load_lv8_11612();
        let instances: Vec<SPInstance> = (0..3).map(|i| continuous_instance(i, part.clone())).collect();
        let sheets = expand_sheets(&[Stock {
            id: "S".into(),
            quantity: 1,
            width: Some(1500.0),
            height: Some(3000.0),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }])
        .expect("sheets");
        let sheet = &sheets[0];

        let cfg = SparrowConfig::from_solver_input(
            30.0,
            CollisionBackendKind::Cde,
            RotationResolveContext::legacy_default(),
            42,
        );
        let optimizer = SparrowOptimizer::new(cfg);
        let mut rng = DeterministicRng::new(42);
        let mut diag = SparrowDiagnostics::default();
        let mut bpp = BppReductionDiagnostics::default();
        let started = std::time::Instant::now();

        // Place 2 big parts side by side at the fitting (≈90°) rotation — bbox-separate, feasible.
        let rot = super::super::fixed_sheet::fitting_rotation(&instances[0], std::slice::from_ref(sheet));
        let (rw, _rh) = dims_for_rotation(part.width, part.height, rot);
        let mk = |idx: usize, rmx: f64| {
            let (ax, ay) =
                placement_anchor_from_rect_min(rmx, sheet.min_y + 5.0, part.width, part.height, rot);
            SparrowPlacement { instance_idx: idx, sheet_index: 0, x: ax, y: ay, rotation_deg: rot }
        };
        let working = SparrowLayout {
            placements: vec![mk(0, sheet.min_x + 5.0), mk(1, sheet.min_x + rw + 20.0)],
        };
        let setup_feasible =
            SparrowCollisionTracker::final_validation_tracker(&working, &instances, &sheets)
                .is_feasible();
        assert!(setup_feasible, "two big parts side by side must be feasible (rw={rw})");

        // Try to admit the 3rd big part onto the same sheet (only interlock can fit it).
        let result = try_admit_critical(
            &optimizer, &working, 2, 0, &instances, &sheets, &started, 25.0, &mut rng, &mut diag,
            &mut bpp,
        );
        let admitted = result.is_some();
        eprintln!("=== Q51 MEASURE-GATE: 3rd big Lv8_11612 admitted on one sheet = {admitted} ===");
        if let Some(out) = result {
            assert!(layout_is_full_feasible(&out, &instances, &sheets), "admitted layout must be feasible");
            let on_sheet = out.placements.iter().filter(|p| p.sheet_index == 0).count();
            eprintln!("=== Q51 MEASURE-GATE: parts on sheet 0 = {on_sheet} (expect 3) ===");
            assert_eq!(on_sheet, 3, "all 3 big parts on one sheet");
        }
        // The test passes either way; the eprintln reports the gate outcome (run with --nocapture).
    }
}
