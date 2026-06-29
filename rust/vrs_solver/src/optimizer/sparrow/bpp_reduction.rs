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

use super::density::{
    bbox_corner_fallback_rect_mins, contour_near_rect_mins, density_candidate_score,
    is_interlock_candidate, DensityWeights,
};
use super::multisheet::{
    compute_utilization, part_polygon_area, sanitize_partial, FiniteStockRunConfig,
    FiniteStockRunResult,
};
use super::*;
use crate::io::BppReductionDiagnostics;
use crate::optimizer::sparrow::sheet_skeleton::SkeletonRole;
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

fn unique_parts_from_instances(instances: &[SPInstance]) -> Vec<Part> {
    let mut seen: HashSet<String> = HashSet::new();
    let mut parts: Vec<Part> = Vec::new();
    for inst in instances {
        if seen.insert(inst.part_id.clone()) {
            parts.push(inst.part.clone());
        }
    }
    parts
}

fn build_live_sheet_feasibility_hints(
    problem: &SparrowProblem,
) -> Result<super::sheet_feasibility::SheetFeasibilityHints, String> {
    let Some(rep_sheet) = problem.container.sheets.iter().max_by(|a, b| {
        a.area
            .partial_cmp(&b.area)
            .unwrap_or(std::cmp::Ordering::Equal)
    }) else {
        return Err("no solver sheets available for sheet-feasibility hints".to_string());
    };
    let parts = unique_parts_from_instances(&problem.instances);
    // The production builder sees the already inset solver-sheet frame, so the live hint model is
    // built in that same coordinate frame (margin 0 here, spacing still explicit).
    super::sheet_feasibility::build_sheet_feasibility_hints(
        &parts,
        rep_sheet.width,
        rep_sheet.height,
        0.0,
        problem.config.spacing_mm,
    )
}

fn critical_incumbent_source(role: Option<SkeletonRole>) -> String {
    match role {
        Some(SkeletonRole::Anchor) => "anchor".to_string(),
        Some(SkeletonRole::Interlock) => "interlock".to_string(),
        Some(SkeletonRole::BandInsert) => "band_insert".to_string(),
        None => "generic".to_string(),
    }
}

fn layout_is_full_feasible(
    layout: &SparrowLayout,
    instances: &[SPInstance],
    sheets: &[SheetShape],
) -> bool {
    if layout.placements.len() != instances.len() {
        return false;
    }
    let mut seen = vec![false; instances.len()];
    for p in &layout.placements {
        if p.instance_idx >= instances.len() || seen[p.instance_idx] {
            return false;
        }
        seen[p.instance_idx] = true;
    }
    if seen.iter().any(|&v| !v) {
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

fn role_aware_path_should_skip_generic_direct(
    skeleton_on: bool,
    role: Option<super::sheet_skeleton::SkeletonRole>,
) -> bool {
    skeleton_on && role.is_some()
}

fn forced_latest_sheet_deadline(now_s: f64, deadline_s: f64, remaining_sheet_count: usize) -> f64 {
    if remaining_sheet_count <= 1 {
        return deadline_s;
    }
    let remaining_budget = (deadline_s - now_s).max(0.0);
    (now_s + remaining_budget / remaining_sheet_count as f64).min(deadline_s)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AnchorAuthorityWinner {
    None,
    Feature,
    Catalog,
}

fn choose_anchor_authority_winner(
    feature_score: Option<f64>,
    catalog_score: Option<f64>,
) -> AnchorAuthorityWinner {
    match (feature_score, catalog_score) {
        (None, None) => AnchorAuthorityWinner::None,
        (Some(_), None) => AnchorAuthorityWinner::Feature,
        (None, Some(_)) => AnchorAuthorityWinner::Catalog,
        (Some(feature), Some(catalog)) => {
            if catalog + 1e-9 >= feature {
                AnchorAuthorityWinner::Catalog
            } else {
                AnchorAuthorityWinner::Feature
            }
        }
    }
}

#[derive(Debug, Clone)]
struct AnchorCatalogChoice {
    score: f64,
    layout: SparrowLayout,
    source: &'static str,
    secondary: &'static str,
    target_edge: &'static str,
    seed_rotation_deg: f64,
}

fn anchor_secondary_is_center(secondary: &str) -> bool {
    secondary.contains("center")
}

#[derive(Debug, Clone, Copy)]
struct AnchorAlignmentMetrics {
    primary_gap_mm: f64,
    secondary_gap_mm: f64,
    min_edge_gap_mm: f64,
    rotation_drift_deg: f64,
}

const FORCED_LATEST_ANCHOR_PRIMARY_MAX_GAP_MM: f64 = 40.0;
const FORCED_LATEST_ANCHOR_CORNER_MAX_GAP_MM: f64 = 120.0;
const FORCED_LATEST_ANCHOR_ROTATION_DRIFT_MAX_DEG: f64 = 22.5;
const FORCED_LATEST_STRICT_ANCHOR_PRIMARY_MAX_GAP_MM: f64 = 15.0;
const FORCED_LATEST_STRICT_ANCHOR_CORNER_MAX_GAP_MM: f64 = 40.0;
const FORCED_LATEST_STRICT_ANCHOR_ROTATION_DRIFT_MAX_DEG: f64 = 12.0;

fn angular_drift_deg(a: f64, b: f64) -> f64 {
    let mut d = (a - b).rem_euclid(360.0).abs();
    if d > 180.0 {
        d = 360.0 - d;
    }
    d
}

fn forced_latest_strict_edge_lock(inst: &SPInstance) -> bool {
    inst.shape_profile.is_large_anchor
}

fn placed_bbox(layout: &SparrowLayout, ci: usize, instances: &[SPInstance]) -> Option<[f64; 4]> {
    let placement = layout.placements.iter().find(|p| p.instance_idx == ci)?;
    let inst = &instances[ci];
    let prepared = transform_base_to_candidate(
        inst.base_shape.as_ref(),
        placement.x,
        placement.y,
        placement.rotation_deg,
    )?;
    Some([
        prepared.min_x,
        prepared.min_y,
        prepared.max_x,
        prepared.max_y,
    ])
}

fn placed_rotation_deg(layout: &SparrowLayout, ci: usize) -> Option<f64> {
    layout
        .placements
        .iter()
        .find(|p| p.instance_idx == ci)
        .map(|p| p.rotation_deg)
}

fn edge_gap_mm(bbox: [f64; 4], sheet: &SheetShape, edge: &str) -> f64 {
    match edge {
        "left" => (bbox[0] - sheet.min_x).abs(),
        "right" => (sheet.max_x - bbox[2]).abs(),
        "bottom" => (bbox[1] - sheet.min_y).abs(),
        "top" => (sheet.max_y - bbox[3]).abs(),
        _ => f64::INFINITY,
    }
}

fn sheet_edge_alignment_kind_to_edge(kind: &str) -> Option<&'static str> {
    match kind {
        "sheet_edge_left" => Some("left"),
        "sheet_edge_right" => Some("right"),
        "sheet_edge_bottom" => Some("bottom"),
        "sheet_edge_top" => Some("top"),
        _ => None,
    }
}

fn anchor_secondary_target_edge(target_edge: &str, secondary: &str) -> Option<&'static str> {
    match (target_edge, secondary) {
        ("left" | "right", "corner_low") => Some("bottom"),
        ("left" | "right", "corner_high") => Some("top"),
        ("bottom" | "top", "corner_low") => Some("left"),
        ("bottom" | "top", "corner_high") => Some("right"),
        _ => None,
    }
}

fn secondary_gap_mm(bbox: [f64; 4], sheet: &SheetShape, target_edge: &str, secondary: &str) -> f64 {
    match (target_edge, secondary) {
        ("left" | "right", "corner_low") => (bbox[1] - sheet.min_y).abs(),
        ("left" | "right", "corner_high") => (sheet.max_y - bbox[3]).abs(),
        ("bottom" | "top", "corner_low") => (bbox[0] - sheet.min_x).abs(),
        ("bottom" | "top", "corner_high") => (sheet.max_x - bbox[2]).abs(),
        ("left" | "right", "center") => {
            let cy = (bbox[1] + bbox[3]) * 0.5;
            let sy = (sheet.min_y + sheet.max_y) * 0.5;
            (cy - sy).abs()
        }
        ("bottom" | "top", "center") => {
            let cx = (bbox[0] + bbox[2]) * 0.5;
            let sx = (sheet.min_x + sheet.max_x) * 0.5;
            (cx - sx).abs()
        }
        _ => 0.0,
    }
}

fn min_edge_gap_mm(bbox: [f64; 4], sheet: &SheetShape) -> f64 {
    [
        (bbox[0] - sheet.min_x).abs(),
        (sheet.max_x - bbox[2]).abs(),
        (bbox[1] - sheet.min_y).abs(),
        (sheet.max_y - bbox[3]).abs(),
    ]
    .into_iter()
    .fold(f64::INFINITY, f64::min)
}

fn anchor_alignment_metrics(
    layout: &SparrowLayout,
    cand_inst_idx: usize,
    instances: &[SPInstance],
    sheet: &SheetShape,
    target_edge: &str,
    secondary: &str,
    seed_rotation_deg: f64,
) -> Option<AnchorAlignmentMetrics> {
    let bbox = placed_bbox(layout, cand_inst_idx, instances)?;
    let final_rot = placed_rotation_deg(layout, cand_inst_idx)?;
    Some(AnchorAlignmentMetrics {
        primary_gap_mm: edge_gap_mm(bbox, sheet, target_edge),
        secondary_gap_mm: secondary_gap_mm(bbox, sheet, target_edge, secondary),
        min_edge_gap_mm: min_edge_gap_mm(bbox, sheet),
        rotation_drift_deg: angular_drift_deg(final_rot, seed_rotation_deg),
    })
}

fn record_anchor_alignment_diag(
    bpp: &mut BppReductionDiagnostics,
    metrics: AnchorAlignmentMetrics,
) {
    bpp.bpp_q71_anchor_final_primary_gap_mm = Some(metrics.primary_gap_mm);
    bpp.bpp_q71_anchor_final_secondary_gap_mm = Some(metrics.secondary_gap_mm);
    bpp.bpp_q71_anchor_final_min_edge_gap_mm = Some(metrics.min_edge_gap_mm);
    bpp.bpp_q71_anchor_final_rotation_drift_deg = Some(metrics.rotation_drift_deg);
}

fn record_anchor_min_edge_diag(
    bpp: &mut BppReductionDiagnostics,
    layout: &SparrowLayout,
    cand_inst_idx: usize,
    instances: &[SPInstance],
    sheet: &SheetShape,
) {
    if let Some(bbox) = placed_bbox(layout, cand_inst_idx, instances) {
        bpp.bpp_q71_anchor_final_min_edge_gap_mm = Some(min_edge_gap_mm(bbox, sheet));
    }
}

fn translated_candidate_layout(
    layout: &SparrowLayout,
    cand_inst_idx: usize,
    dx: f64,
    dy: f64,
) -> Option<SparrowLayout> {
    let mut moved = layout.clone();
    let placement = moved
        .placements
        .iter_mut()
        .find(|p| p.instance_idx == cand_inst_idx)?;
    placement.x += dx;
    placement.y += dy;
    Some(moved)
}

fn flush_delta_to_edge(
    layout: &SparrowLayout,
    cand_inst_idx: usize,
    instances: &[SPInstance],
    sheet: &SheetShape,
    edge: &str,
) -> Option<(f64, f64)> {
    let bbox = placed_bbox(layout, cand_inst_idx, instances)?;
    Some(match edge {
        "left" => (sheet.min_x - bbox[0], 0.0),
        "right" => (sheet.max_x - bbox[2], 0.0),
        "bottom" => (0.0, sheet.min_y - bbox[1]),
        "top" => (0.0, sheet.max_y - bbox[3]),
        _ => return None,
    })
}

fn push_candidate_toward_edge(
    layout: &SparrowLayout,
    cand_inst_idx: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    sheet: &SheetShape,
    edge: &str,
) -> SparrowLayout {
    let Some((dx, dy)) = flush_delta_to_edge(layout, cand_inst_idx, instances, sheet, edge) else {
        return layout.clone();
    };
    if dx.abs() <= 1e-6 && dy.abs() <= 1e-6 {
        return layout.clone();
    }

    let feasible_at = |t: f64| -> Option<SparrowLayout> {
        let moved = translated_candidate_layout(layout, cand_inst_idx, dx * t, dy * t)?;
        SparrowCollisionTracker::final_validation_tracker(&moved, instances, solver_sheets)
            .is_feasible()
            .then_some(moved)
    };

    if let Some(flush) = feasible_at(1.0) {
        return flush;
    }

    let mut lo = 0.0_f64;
    let mut hi = 1.0_f64;
    let mut best = layout.clone();
    for _ in 0..12 {
        let mid = (lo + hi) * 0.5;
        if let Some(moved) = feasible_at(mid) {
            lo = mid;
            best = moved;
        } else {
            hi = mid;
        }
    }
    best
}

fn nearest_edge_for_bbox(bbox: [f64; 4], sheet: &SheetShape) -> &'static str {
    let mut best = ("left", edge_gap_mm(bbox, sheet, "left"));
    for edge in ["right", "bottom", "top"] {
        let gap = edge_gap_mm(bbox, sheet, edge);
        if gap < best.1 {
            best = (edge, gap);
        }
    }
    best.0
}

fn repair_strict_edge_lock_placements_on_sheet(
    layout: &SparrowLayout,
    target_sheet: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    sheet: &SheetShape,
) -> SparrowLayout {
    let mut repaired = layout.clone();
    let mut locked: Vec<usize> = repaired
        .placements
        .iter()
        .filter(|p| {
            p.sheet_index == target_sheet
                && forced_latest_strict_edge_lock(&instances[p.instance_idx])
        })
        .map(|p| p.instance_idx)
        .collect();
    locked.sort_by(|a, b| {
        instances[*b]
            .shape_profile
            .sheet_area_ratio
            .partial_cmp(&instances[*a].shape_profile.sheet_area_ratio)
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    for cand_inst_idx in locked {
        let Some(bbox) = placed_bbox(&repaired, cand_inst_idx, instances) else {
            continue;
        };
        let edge = nearest_edge_for_bbox(bbox, sheet);
        repaired = push_candidate_toward_edge(
            &repaired,
            cand_inst_idx,
            instances,
            solver_sheets,
            sheet,
            edge,
        );
    }
    repaired
}

fn repair_anchor_flush_alignment(
    layout: &SparrowLayout,
    cand_inst_idx: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    sheet: &SheetShape,
    target_edge: &str,
    secondary: Option<&str>,
) -> SparrowLayout {
    let mut repaired = push_candidate_toward_edge(
        layout,
        cand_inst_idx,
        instances,
        solver_sheets,
        sheet,
        target_edge,
    );
    if let Some(secondary_edge) =
        secondary.and_then(|secondary| anchor_secondary_target_edge(target_edge, secondary))
    {
        repaired = push_candidate_toward_edge(
            &repaired,
            cand_inst_idx,
            instances,
            solver_sheets,
            sheet,
            secondary_edge,
        );
    }
    repaired
}

fn forced_latest_anchor_catalog_score(
    forced_latest: bool,
    strict_edge_lock: bool,
    layout: &SparrowLayout,
    cand_inst_idx: usize,
    target_sheet: usize,
    instances: &[SPInstance],
    sheet: &SheetShape,
    target_edge: &str,
    secondary: &str,
    seed_rotation_deg: f64,
) -> Option<(f64, AnchorAlignmentMetrics)> {
    let free = sheet_freespace_score(layout, target_sheet, instances, sheet);
    let metrics = anchor_alignment_metrics(
        layout,
        cand_inst_idx,
        instances,
        sheet,
        target_edge,
        secondary,
        seed_rotation_deg,
    )?;
    if !forced_latest {
        return Some((free, metrics));
    }
    let primary_limit = if strict_edge_lock {
        FORCED_LATEST_STRICT_ANCHOR_PRIMARY_MAX_GAP_MM
    } else {
        FORCED_LATEST_ANCHOR_PRIMARY_MAX_GAP_MM
    };
    let corner_limit = if strict_edge_lock {
        FORCED_LATEST_STRICT_ANCHOR_CORNER_MAX_GAP_MM
    } else {
        FORCED_LATEST_ANCHOR_CORNER_MAX_GAP_MM
    };
    let rotation_limit = if strict_edge_lock {
        FORCED_LATEST_STRICT_ANCHOR_ROTATION_DRIFT_MAX_DEG
    } else {
        FORCED_LATEST_ANCHOR_ROTATION_DRIFT_MAX_DEG
    };
    if strict_edge_lock && anchor_secondary_is_center(secondary) {
        return None;
    }
    let gross_primary_drift = metrics.primary_gap_mm > primary_limit;
    let gross_corner_drift =
        !anchor_secondary_is_center(secondary) && metrics.secondary_gap_mm > corner_limit;
    let gross_rotation_drift = metrics.rotation_drift_deg > rotation_limit;
    if gross_primary_drift || gross_corner_drift || gross_rotation_drift {
        return None;
    }
    let span = sheet.width.max(sheet.height);
    let primary_bonus = (primary_limit - metrics.primary_gap_mm).max(0.0) * span * 45.0;
    let secondary_bonus = if anchor_secondary_is_center(secondary) {
        0.0
    } else {
        (corner_limit - metrics.secondary_gap_mm).max(0.0) * span * 8.0
    };
    let rotation_penalty = metrics.rotation_drift_deg * sheet.area * 0.0008;
    Some((
        free + primary_bonus + secondary_bonus - rotation_penalty,
        metrics,
    ))
}

fn forced_latest_anchor_feature_score(
    forced_latest: bool,
    strict_edge_lock: bool,
    layout: &SparrowLayout,
    cand_inst_idx: usize,
    target_sheet: usize,
    instances: &[SPInstance],
    sheet: &SheetShape,
    target_edge: Option<&str>,
    seed_rotation_deg: f64,
) -> Option<f64> {
    let free = sheet_freespace_score(layout, target_sheet, instances, sheet);
    if !forced_latest {
        return Some(free);
    }
    let bbox = placed_bbox(layout, cand_inst_idx, instances)?;
    let edge_gap = target_edge.map_or_else(
        || min_edge_gap_mm(bbox, sheet),
        |target_edge| edge_gap_mm(bbox, sheet, target_edge),
    );
    let rotation_drift = placed_rotation_deg(layout, cand_inst_idx)
        .map(|rot| angular_drift_deg(rot, seed_rotation_deg))
        .unwrap_or(0.0);
    let primary_limit = if strict_edge_lock {
        FORCED_LATEST_STRICT_ANCHOR_PRIMARY_MAX_GAP_MM
    } else {
        FORCED_LATEST_ANCHOR_PRIMARY_MAX_GAP_MM
    };
    let rotation_limit = if strict_edge_lock {
        FORCED_LATEST_STRICT_ANCHOR_ROTATION_DRIFT_MAX_DEG
    } else {
        FORCED_LATEST_ANCHOR_ROTATION_DRIFT_MAX_DEG
    };
    if edge_gap > primary_limit || rotation_drift > rotation_limit {
        return None;
    }
    let span = sheet.width.max(sheet.height);
    let edge_bonus = (primary_limit - edge_gap).max(0.0) * span * 35.0;
    let rotation_penalty = rotation_drift * sheet.area * 0.0008;
    Some(free + edge_bonus - rotation_penalty)
}

fn forced_latest_center_material_gain(corner_score: f64, center_score: f64) -> bool {
    const ABS_GAIN_MM2: f64 = 250_000.0;
    const REL_GAIN: f64 = 0.10;
    center_score >= corner_score + ABS_GAIN_MM2 || center_score >= corner_score * (1.0 + REL_GAIN)
}

fn choose_anchor_catalog_candidate(
    forced_latest: bool,
    strict_edge_lock: bool,
    best_corner: Option<AnchorCatalogChoice>,
    best_center: Option<AnchorCatalogChoice>,
    bpp: &mut BppReductionDiagnostics,
) -> Option<AnchorCatalogChoice> {
    if let Some(score) = best_corner.as_ref().map(|c| c.score) {
        bpp.bpp_q70_anchor_best_corner_score = Some(
            bpp.bpp_q70_anchor_best_corner_score
                .map_or(score, |prev| prev.max(score)),
        );
    }
    if let Some(score) = best_center.as_ref().map(|c| c.score) {
        bpp.bpp_q70_anchor_best_center_score = Some(
            bpp.bpp_q70_anchor_best_center_score
                .map_or(score, |prev| prev.max(score)),
        );
    }

    match (best_corner, best_center) {
        (None, None) => None,
        (Some(corner), None) => Some(corner),
        (None, Some(center)) => {
            bpp.bpp_q70_anchor_center_only_path = true;
            if strict_edge_lock {
                bpp.bpp_q70_anchor_center_blocked_by_policy = true;
                None
            } else {
                Some(center)
            }
        }
        (Some(corner), Some(center)) => {
            if strict_edge_lock {
                bpp.bpp_q70_anchor_center_blocked_by_policy = true;
                Some(corner)
            } else if !forced_latest {
                if center.score + 1e-9 >= corner.score {
                    Some(center)
                } else {
                    Some(corner)
                }
            } else if forced_latest_center_material_gain(corner.score, center.score) {
                bpp.bpp_q70_anchor_center_override_used = true;
                Some(center)
            } else {
                bpp.bpp_q70_anchor_center_blocked_by_policy = true;
                Some(corner)
            }
        }
    }
}

fn sheet_physical_utilization_ratio(
    layout: &SparrowLayout,
    instances: &[SPInstance],
    sheet_idx: usize,
    sheet: &SheetShape,
) -> f64 {
    if sheet.area <= 1e-9 {
        return 0.0;
    }
    sheet_placed_area(layout, instances, sheet_idx) / sheet.area
}

fn forced_latest_recovery_deadline(
    now_s: f64,
    deadline_s: f64,
    remaining_sheet_count: usize,
) -> f64 {
    let remaining_budget = (deadline_s - now_s).max(0.0);
    if remaining_budget <= 0.0 {
        return now_s;
    }
    let extra_budget = if remaining_sheet_count == 0 {
        remaining_budget
    } else {
        (remaining_budget / (remaining_sheet_count as f64 + 1.0)).min(20.0)
    };
    (now_s + extra_budget).min(deadline_s)
}

fn completion_recovery_score(
    before: &SparrowLayout,
    after: &SparrowLayout,
    sheet_idx: usize,
    instances: &[SPInstance],
    sheet: &SheetShape,
) -> f64 {
    let before_free = sheet_freespace_score(before, sheet_idx, instances, sheet);
    let after_free = sheet_freespace_score(after, sheet_idx, instances, sheet);
    let before_util = sheet_physical_utilization_ratio(before, instances, sheet_idx, sheet);
    let after_util = sheet_physical_utilization_ratio(after, instances, sheet_idx, sheet);
    let free_reduction = (before_free - after_free).max(0.0);
    let util_gain = ((after_util - before_util).max(0.0)) * sheet.area;
    let underfill_bonus = ((0.60 - before_util).max(0.0)) * sheet.area * 0.35;
    free_reduction + util_gain + underfill_bonus
}

fn filler_first_completion_order(
    queues: &super::fixed_sheet::CriticalityQueues,
    instances: &[SPInstance],
) -> Vec<usize> {
    let by_small_first = |a: &usize, b: &usize| {
        instances[*a]
            .shape_profile
            .sheet_area_ratio
            .partial_cmp(&instances[*b].shape_profile.sheet_area_ratio)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| instances[*a].instance_id.cmp(&instances[*b].instance_id))
    };
    let mut filler = queues.filler.clone();
    filler.sort_by(by_small_first);
    let mut structural = queues.structural.clone();
    structural.sort_by(by_small_first);
    filler.extend(structural);
    filler
}

// ── ADAPTED bp_separator: sub-problem separation over an explicit sheet set ─────

/// Run the native exploration/separation over `local_sheets` only, seeded with
/// `seed_layout` (placements indexed into `local_sheets`). Returns
/// `(full_feasible, solved_local_layout)`.
#[allow(clippy::too_many_arguments)]
fn run_subsolve(
    optimizer: &SparrowOptimizer,
    seed_layout: SparrowLayout,
    instances: &[SPInstance],
    local_sheets: &[SheetShape],
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    locked: &HashSet<usize>,
) -> (bool, SparrowLayout) {
    let mut state = SparrowState::new_with_diag(seed_layout, instances, local_sheets, diag);
    state.locked_items = locked.clone();
    let _ = optimizer.exploration_phase(
        &mut state,
        instances,
        local_sheets,
        started,
        deadline_s,
        rng,
        diag,
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
    let local_sheets: Vec<SheetShape> = receiving
        .iter()
        .map(|&g| solver_sheets[g].clone())
        .collect();
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
        optimizer,
        local_layout,
        instances,
        &local_sheets,
        started,
        deadline_s,
        rng,
        diag,
        &HashSet::new(),
    );
    let remapped = SparrowLayout {
        placements: solved
            .placements
            .iter()
            .map(|p| SparrowPlacement {
                sheet_index: receiving
                    .get(p.sheet_index)
                    .cloned()
                    .unwrap_or(receiving[0]),
                ..p.clone()
            })
            .collect(),
    };
    // SGH-Q46 M3: when the direct fit fails, try the strip-compress fit (place loose on a
    // virtual-wide boundary, then compress to the real width — the only way to fit parts that
    // need interlocking). Opt-in (default off) while it matures.
    if !full && std::env::var("VRS_BPP_COMPRESS").ok().as_deref() == Some("1") {
        let (sc_full, sc_layout) = strip_compress_fit(
            optimizer,
            trial,
            receiving,
            instances,
            solver_sheets,
            started,
            deadline_s,
            rng,
            diag,
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

/// Rotation candidate set for a density placement / separation step. Honors continuous rotation:
/// a continuous part gets the current angle + **fine local refinement** (the wiggle that lands a
/// precise interlock orientation, e.g. ~91°/~281°) + a **coarse global sweep** (every 30°, to flip
/// 90↔270 or escape the seed basin) — never snapped to a discrete grid, and the coordinate descent
/// keeps refining across sweeps. A discrete part gets the current angle + a bounded subsample of its
/// allowed set. (`allowed_rotations_deg` is EMPTY for continuous parts — keying off it alone froze
/// continuous parts at their seed rotation; this helper is the fix and the single source of truth.)
fn density_rotation_candidates(inst: &SPInstance, cur_rot: f64) -> Vec<f64> {
    let mut rotations: Vec<f64> = vec![cur_rot];
    if inst.continuous_rotation {
        for d in [0.5_f64, 1.0, 2.0, 4.0, 8.0, 16.0] {
            rotations.push(cur_rot + d);
            rotations.push(cur_rot - d);
        }
        for k in 0..12 {
            rotations.push(k as f64 * 30.0);
        }
    } else {
        let allowed = &inst.allowed_rotations_deg;
        if !allowed.is_empty() {
            let stride = (allowed.len() / 8).max(1);
            for (i, &r) in allowed.iter().enumerate() {
                if i % stride == 0 {
                    rotations.push(r);
                }
            }
        }
    }
    rotations
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
                    sheet_index: receiving
                        .get(p.sheet_index)
                        .cloned()
                        .unwrap_or(receiving[0]),
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
            &mut state,
            instances,
            &local_sheets,
            started,
            sep_deadline,
            rng,
            diag,
        );
        state
            .best_feasible
            .clone()
            .unwrap_or_else(|| state.layout.clone())
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
        let pairs =
            SparrowCollisionTracker::final_validation_tracker(&cur, instances, &local_sheets)
                .colliding_pairs();
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
                optimizer,
                &cur,
                l,
                &trial_sheet,
                instances,
                started,
                step_deadline,
                rng,
                diag,
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
    let real_local: Vec<SheetShape> = receiving
        .iter()
        .map(|&g| solver_sheets[g].clone())
        .collect();
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
        .map(|p| SparrowPlacement {
            sheet_index: 0,
            ..p.clone()
        })
        .collect();
    let inst = &instances[target_instance];
    let rot = super::fixed_sheet::fitting_rotation(inst, &local_sheets);
    let s = &local_sheets[0];
    let (ax, ay) =
        placement_anchor_from_rect_min(s.min_x, s.min_y, inst.part.width, inst.part.height, rot);
    let target_idx = local.len();
    local.push(SparrowPlacement {
        instance_idx: target_instance,
        sheet_index: 0,
        x: ax,
        y: ay,
        rotation_deg: rot,
    });
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
    let global = SparrowPlacement {
        sheet_index: sheet,
        ..pl
    };
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
        let t = SparrowCollisionTracker::final_validation_tracker(
            &chk_layout,
            instances,
            solver_sheets,
        );
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
    SparrowPlacement {
        instance_idx: target_instance,
        sheet_index: sheet,
        x: ax,
        y: ay,
        rotation_deg: rot,
    }
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
                optimizer,
                target_instance,
                rs,
                trial,
                instances,
                solver_sheets,
                started,
                rng,
                diag,
                true,
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
            trial.placements[li] =
                bootstrap_on_sheet(target_instance, rs, instances, solver_sheets, rng);
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
        optimizer,
        inst,
        to_sheet,
        layout,
        instances,
        solver_sheets,
        started,
        rng,
        diag,
        false,
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
    layout.placements[a] = SparrowPlacement {
        sheet_index: pb.sheet_index,
        x: pb.x,
        y: pb.y,
        ..pa.clone()
    };
    layout.placements[b] = SparrowPlacement {
        sheet_index: pa.sheet_index,
        x: pa.x,
        y: pa.y,
        ..pb.clone()
    };
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
        let tracker =
            SparrowCollisionTracker::final_validation_tracker(layout, instances, solver_sheets);
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
                if try_transfer(
                    optimizer,
                    layout,
                    ci,
                    to,
                    instances,
                    solver_sheets,
                    started,
                    rng,
                    diag,
                    bpp,
                ) {
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
                let _ = try_swap(
                    layout,
                    colliding[0],
                    colliding[1],
                    instances,
                    solver_sheets,
                    bpp,
                );
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
            .partial_cmp(&profile_order_key(
                instances,
                layout.placements[a].instance_idx,
            ))
            .unwrap_or(std::cmp::Ordering::Equal)
    });
    let mut any = false;
    for li in idxs {
        let target_instance = layout.placements[li].instance_idx;
        let old = layout.placements[li].clone();
        // temporarily lift the item off the sheet so search ignores it as an obstacle
        layout.placements[li] = SparrowPlacement {
            sheet_index: usize::MAX,
            ..old.clone()
        };
        let candidate = search_placement_on_sheet(
            optimizer,
            target_instance,
            sheet,
            layout,
            instances,
            solver_sheets,
            started,
            rng,
            diag,
            true,
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
        .map(|p| SparrowPlacement {
            sheet_index: 0,
            ..p.clone()
        })
        .collect();
    if placements.is_empty() {
        return (true, vec![]);
    }
    let local_sheets = [local_sheet.clone()];
    let local_layout = SparrowLayout { placements };
    let mut state = SparrowState::new_with_diag(local_layout, instances, &local_sheets, diag);
    let _ = optimizer.exploration_phase(
        &mut state,
        instances,
        &local_sheets,
        started,
        deadline_s,
        rng,
        diag,
    );
    let layout = state
        .best_feasible
        .clone()
        .unwrap_or_else(|| state.layout.clone());
    let tracker =
        SparrowCollisionTracker::final_validation_tracker(&layout, instances, &local_sheets);
    let feasible = tracker.is_feasible();
    let remapped = layout
        .placements
        .iter()
        .map(|p| SparrowPlacement {
            sheet_index: sheet_idx,
            ..p.clone()
        })
        .collect();
    (feasible, remapped)
}

/// Used extent (max coordinate of any part) on one axis for a sheet's items.
fn sheet_used_max(
    layout: &SparrowLayout,
    instances: &[SPInstance],
    sheet_idx: usize,
    axis_x: bool,
) -> f64 {
    layout
        .placements
        .iter()
        .filter(|p| p.sheet_index == sheet_idx)
        .map(|p| {
            let inst = &instances[p.instance_idx];
            let (rmx, rmy) =
                rect_min_from_anchor(p.x, p.y, inst.part.width, inst.part.height, p.rotation_deg);
            let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, p.rotation_deg);
            if axis_x {
                rmx + rw
            } else {
                rmy + rh
            }
        })
        .fold(f64::MIN, f64::max)
}

/// Replace the placements on `sheet_idx` with `new`.
fn replace_sheet_placements(
    working: &mut SparrowLayout,
    sheet_idx: usize,
    new: Vec<SparrowPlacement>,
) {
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
            let mut accepted_max = sheet_used_max(working, instances, s, axis_x).min(if axis_x {
                sheet.max_x
            } else {
                sheet.max_y
            });
            let before_extent = accepted_max - sheet_min;
            // Fine-grained compression (upstream uses ~0.05% steps): take small steps and keep
            // going while they remain feasible; shrink the step on failure. A small step injects
            // a small overlap the separator can resolve by nudging parts into concavities, which
            // accumulates into deep nesting. Coarse steps inject un-nestable overlaps and fail.
            let mut step = 0.015;
            let mut stagnant = 0usize;
            while step >= MIN_SHRINK && stagnant < 5 && started.elapsed().as_secs_f64() < deadline_s
            {
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
                    optimizer,
                    working,
                    s,
                    &trial,
                    instances,
                    started,
                    step_deadline,
                    rng,
                    diag,
                );
                if feasible && !remapped.is_empty() {
                    replace_sheet_placements(working, s, remapped);
                    bpp.bpp_region_compression_accepts += 1;
                    let new_extent = (sheet_used_max(working, instances, s, axis_x).min(new_max)
                        - sheet_min)
                        .max(0.0);
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

/// SGH-Q53D: opt-in feature-first critical admission inside the sheet builder.
fn critical_feature_admission_enabled() -> bool {
    std::env::var("VRS_SHEET_BUILDER_FEATURE_CRITICAL")
        .ok()
        .as_deref()
        == Some("1")
}

fn feature_seed_rejection_summary(seeds: &[CandidateSeed]) -> Option<String> {
    let mut counts: std::collections::BTreeMap<String, usize> = std::collections::BTreeMap::new();
    for seed in seeds {
        if seed.refine_success {
            continue;
        }
        let reason = seed
            .refine_rejection_reason
            .clone()
            .unwrap_or_else(|| "unknown".to_string());
        *counts.entry(reason).or_insert(0) += 1;
    }
    if counts.is_empty() {
        return None;
    }
    Some(
        counts
            .into_iter()
            .map(|(reason, count)| format!("{reason}={count}"))
            .collect::<Vec<_>>()
            .join(","),
    )
}

fn record_feature_seed_metrics(
    seeds: &[CandidateSeed],
    bpp: &mut BppReductionDiagnostics,
    diag: &mut SparrowDiagnostics,
) {
    bpp.bpp_feature_candidates_generated += seeds.len();
    diag.feature_candidates_generated += seeds.len();

    let refine_successes = seeds.iter().filter(|seed| seed.refine_success).count();
    let refine_failures = seeds.len().saturating_sub(refine_successes);
    bpp.bpp_feature_refine_successes += refine_successes;
    bpp.bpp_feature_refine_failures += refine_failures;
    diag.feature_refine_successes += refine_successes;
    diag.feature_refine_failures += refine_failures;

    if bpp.bpp_feature_refine_rejection_reason.is_none() {
        bpp.bpp_feature_refine_rejection_reason = feature_seed_rejection_summary(seeds);
    }
    if diag.feature_refine_rejection_reason.is_none() {
        diag.feature_refine_rejection_reason = feature_seed_rejection_summary(seeds);
    }
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
    let cand_base = inst.base_shape.as_ref();
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

    // Rotation set: current + continuous refinement (continuous parts) or a bounded subsample of
    // the discrete set — never snapped. See `density_rotation_candidates`.
    let rotations = density_rotation_candidates(inst, cur_rot);

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
    allow_feature_seeds: bool,
    allow_bbox_fallback: bool,
    allow_uniform_positions: bool,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) -> Option<SparrowPlacement> {
    let inst_idx = working.placements[li].instance_idx;
    let inst = &instances[inst_idx];
    let sheet = &solver_sheets[target_sheet];
    let cand_base = inst.base_shape.as_ref();

    // Neighbours = parts currently living on `target_sheet` with a live (non-ruined) shape.
    let mut neighbours: Vec<&CdePreparedShape> = Vec::new();
    let mut feature_neighbours: Vec<PlacedFeatureNeighbour<'_>> = Vec::new();
    for j in 0..working.placements.len() {
        if j == li || working.placements[j].sheet_index != target_sheet {
            continue;
        }
        let Some(shape) = tracker.shapes.get(j).and_then(|o| o.as_deref()) else {
            continue;
        };
        neighbours.push(shape);
        feature_neighbours.push(PlacedFeatureNeighbour {
            placement: &working.placements[j],
            instance: &instances[working.placements[j].instance_idx],
        });
    }
    let session = build_sheet_session(li, target_sheet, working, tracker, sheet_prepared)?;
    let ev = LBFEvaluator {
        inst,
        sheet,
        sheet_idx: target_sheet,
        session: &session,
        base: cand_base,
        n_evals: 0,
    };

    // Seed rotation = the part's current rotation; plus continuous refinement (continuous parts) or
    // a bounded subsample of the discrete set — never snapped. See `density_rotation_candidates`.
    let cur_rot = working.placements[li].rotation_deg;
    let rotations = density_rotation_candidates(inst, cur_rot);

    let (rw0, rh0) = dims_for_rotation(inst.part.width, inst.part.height, cur_rot);
    let n_uniform = density_samples();
    let mut uniform_positions: Vec<(f64, f64)> = Vec::with_capacity(n_uniform);
    if allow_uniform_positions {
        for _ in 0..n_uniform {
            let rmx = sheet.min_x + rng.next_f64() * (sheet.max_x - rw0 - sheet.min_x).max(0.0);
            let rmy = sheet.min_y + rng.next_f64() * (sheet.max_y - rh0 - sheet.min_y).max(0.0);
            uniform_positions.push((rmx, rmy));
        }
    }
    let feature_seeds = if allow_feature_seeds
        && feature_candidate_generation_enabled()
        && inst.shape_profile.is_critical()
    {
        let seeds = generate_feature_candidate_seeds_for_sheet(
            inst,
            cur_rot,
            sheet,
            &feature_neighbours,
            n_uniform + 20,
        );
        record_feature_seed_metrics(&seeds, bpp, diag);
        seeds
    } else {
        Vec::new()
    };
    let bbox_positions = if allow_bbox_fallback && !neighbours.is_empty() {
        bbox_corner_fallback_rect_mins(&neighbours, rw0, rh0, sheet, n_uniform + 20)
    } else {
        Vec::new()
    };
    bpp.bpp_bbox_corner_candidates_generated += bbox_positions.len();
    diag.bbox_corner_candidates_generated += bbox_positions.len();

    let mut best: Option<(
        f64,
        SparrowPlacement,
        bool,
        Option<CandidateSeedSource>,
        Option<CandidateSeed>,
    )> = None;
    let mut consider = |rmx: f64,
                        rmy: f64,
                        rot: f64,
                        source: Option<CandidateSeedSource>,
                        feature_seed: Option<CandidateSeed>| {
        if ev.score_lbf_candidate(rmx, rmy, rot).is_none() {
            return;
        }
        let (ax, ay) =
            placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
        let Some(cand) = transform_base_to_candidate(cand_base, ax, ay, rot) else {
            return;
        };
        let interlock = is_interlock_candidate(&cand, &neighbours);
        if interlock {
            bpp.bpp_interlock_candidates_generated += 1;
        }
        let score = if neighbours.is_empty() {
            (rmx - sheet.min_x) + (rmy - sheet.min_y)
        } else {
            density_candidate_score(&cand, &neighbours, weights)
        };
        if best.as_ref().is_none_or(|(bs, _, _, _, _)| score < *bs) {
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
                source,
                feature_seed,
            ));
        }
    };

    for seed in &feature_seeds {
        consider(
            seed.x,
            seed.y,
            seed.rotation_seed_deg,
            Some(seed.source),
            Some(seed.clone()),
        );
    }
    for &(rmx, rmy) in &bbox_positions {
        for &rot in &rotations {
            consider(
                rmx,
                rmy,
                rot,
                Some(CandidateSeedSource::BboxCornerFallback),
                None,
            );
        }
    }
    for &(rmx, rmy) in &uniform_positions {
        for &rot in &rotations {
            consider(rmx, rmy, rot, None, None);
        }
    }
    best.map(|(_, pl, interlock, source, feature_seed)| {
        if interlock {
            bpp.bpp_interlock_candidates_accepted += 1;
        }
        match source {
            Some(CandidateSeedSource::ContourFeature) => {
                bpp.bpp_feature_candidates_accepted += 1;
                diag.feature_candidates_accepted += 1;
                if let Some(seed) = feature_seed {
                    bpp.bpp_accepted_feature_pair_type = Some(seed.pair_type());
                    diag.accepted_feature_pair_type = Some(seed.pair_type());
                    bpp.bpp_feature_refine_seed_rotation_deg = Some(seed.seed_rotation_deg);
                    bpp.bpp_feature_refine_refined_rotation_deg = Some(seed.rotation_seed_deg);
                    bpp.bpp_feature_refine_iterations = seed.refine_iterations;
                    bpp.bpp_feature_refine_rejection_reason = seed.refine_rejection_reason.clone();
                    diag.feature_refine_seed_rotation_deg = Some(seed.seed_rotation_deg);
                    diag.feature_refine_refined_rotation_deg = Some(seed.rotation_seed_deg);
                    diag.feature_refine_iterations = seed.refine_iterations;
                    diag.feature_refine_rejection_reason = seed.refine_rejection_reason;
                }
            }
            Some(CandidateSeedSource::BboxCornerFallback) => {
                bpp.bpp_bbox_corner_candidates_accepted += 1;
                diag.bbox_corner_candidates_accepted += 1;
            }
            None => {}
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

/// SGH-Q52: density-biased weight for the admission separation (`VRS_ADMISSION_DENSITY_BIAS`,
/// default 0.0 ⇒ pure overlap-minimising = Q51 behaviour). A positive value biases overlap
/// resolution toward interlock (tuck into concavities) instead of spreading.
fn admission_density_bias() -> f64 {
    std::env::var("VRS_ADMISSION_DENSITY_BIAS")
        .ok()
        .and_then(|v| v.parse::<f64>().ok())
        .unwrap_or(0.0)
        .max(0.0)
}

/// Feasibility of the parts on `sheet_idx` (collision-free + in-bounds), given the local placements.
fn sheet_local_feasible(
    local: &[SparrowPlacement],
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
) -> bool {
    let lay = SparrowLayout {
        placements: local.to_vec(),
    };
    SparrowCollisionTracker::final_validation_tracker(&lay, instances, solver_sheets).is_feasible()
}

/// SGH-Q52: density-biased separation over the parts on `sheet_idx`. Coordinate descent: each part
/// moves to the candidate (uniform + contour-near, continuous rotation) that minimises
/// `collision_proxy + w_density · density_proxy` — resolving overlap **toward interlock** (tuck into
/// concavities, gap-preserving via the spacing-collision shape) rather than spreading. Returns
/// `(feasible, remapped placements for the sheet)`. NFP-free; the CDE decides final feasibility.
#[allow(clippy::too_many_arguments)]
fn density_biased_separate(
    layout: &SparrowLayout,
    sheet_idx: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    w_density: f64,
    rng: &mut DeterministicRng,
    started: &Instant,
    deadline_s: f64,
) -> (bool, Vec<SparrowPlacement>) {
    let sheet = &solver_sheets[sheet_idx];
    let mut local: Vec<SparrowPlacement> = layout
        .placements
        .iter()
        .filter(|p| p.sheet_index == sheet_idx)
        .map(|p| SparrowPlacement {
            sheet_index: sheet_idx,
            ..p.clone()
        })
        .collect();
    if local.len() <= 1 {
        return (
            sheet_local_feasible(&local, instances, solver_sheets),
            local,
        );
    }
    let weights = DensityWeights::default();
    let n_uniform = density_samples();
    let Some(sheet_sh) = prepare_shape_from_sheet(sheet).ok().map(Rc::new) else {
        return (false, local);
    };
    const SWEEPS: usize = 12;
    const EPS: f64 = 1e-9;
    for _ in 0..SWEEPS {
        if started.elapsed().as_secs_f64() >= deadline_s {
            break;
        }
        for i in 0..local.len() {
            if started.elapsed().as_secs_f64() >= deadline_s {
                break;
            }
            let inst = &instances[local[i].instance_idx];
            let cand_base = inst.base_shape.as_ref();
            // Session + neighbour shapes over the OTHER parts on the sheet (current positions).
            let local_layout = SparrowLayout {
                placements: local.clone(),
            };
            let tracker = SparrowCollisionTracker::build(&local_layout, instances, solver_sheets);
            let Some(session) =
                build_sheet_session(i, sheet_idx, &local_layout, &tracker, &sheet_sh)
            else {
                continue;
            };
            let ev = LBFEvaluator {
                inst,
                sheet,
                sheet_idx,
                session: &session,
                base: cand_base,
                n_evals: 0,
            };
            let neigh: Vec<CdePreparedShape> = (0..local.len())
                .filter(|&j| j != i)
                .filter_map(|j| {
                    let p = &local[j];
                    let ji = &instances[p.instance_idx];
                    transform_base_to_candidate(
                        ji.base_shape.as_ref(),
                        p.x,
                        p.y,
                        p.rotation_deg,
                    )
                })
                .collect();
            let nref: Vec<&CdePreparedShape> = neigh.iter().collect();

            // SGH-Q52 fix: continuous parts must refine rotation CONTINUOUSLY (the interlock for the
            // curved parts needs precise angles + 90↔270 flips, not the frozen min-width seed).
            let cur_rot = local[i].rotation_deg;
            let rotations = density_rotation_candidates(inst, cur_rot);
            let (cur_rmx, cur_rmy) = rect_min_from_anchor(
                local[i].x,
                local[i].y,
                inst.part.width,
                inst.part.height,
                cur_rot,
            );
            let (rw0, rh0) = dims_for_rotation(inst.part.width, inst.part.height, cur_rot);
            let mut positions: Vec<(f64, f64)> = vec![(cur_rmx, cur_rmy)];
            for _ in 0..n_uniform {
                let rmx = sheet.min_x + rng.next_f64() * (sheet.max_x - rw0 - sheet.min_x).max(0.0);
                let rmy = sheet.min_y + rng.next_f64() * (sheet.max_y - rh0 - sheet.min_y).max(0.0);
                positions.push((rmx, rmy));
            }
            positions.extend(contour_near_rect_mins(
                &nref,
                rw0,
                rh0,
                sheet,
                n_uniform + 20,
            ));

            // Lexicographic objective: prefer CLEAR candidates ranked by density (interlock); only
            // if NONE is clear, take the lowest collision-proxy (progress toward feasible).
            let mut best_clear: Option<(f64, SparrowPlacement)> = None; // (density, placement)
            let mut best_coll: Option<(f64, SparrowPlacement)> = None; // (collision_proxy, placement)
            for &rot in &rotations {
                let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
                for &(rmx, rmy) in &positions {
                    if rmx < sheet.min_x - EPS
                        || rmy < sheet.min_y - EPS
                        || rmx + rw > sheet.max_x + EPS
                        || rmy + rh > sheet.max_y + EPS
                    {
                        continue;
                    }
                    let (ax, ay) = placement_anchor_from_rect_min(
                        rmx,
                        rmy,
                        inst.part.width,
                        inst.part.height,
                        rot,
                    );
                    let Some(cand) = transform_base_to_candidate(cand_base, ax, ay, rot) else {
                        continue;
                    };
                    let pl = SparrowPlacement {
                        instance_idx: local[i].instance_idx,
                        sheet_index: sheet_idx,
                        x: ax,
                        y: ay,
                        rotation_deg: rot,
                    };
                    if ev.score_lbf_candidate(rmx, rmy, rot).is_some() {
                        // clear ⇒ rank by density (lower = more interlocked), scaled by w_density
                        let dens = density_candidate_score(&cand, &nref, &weights) * w_density;
                        if best_clear.as_ref().is_none_or(|(bs, _)| dens < *bs) {
                            best_clear = Some((dens, pl));
                        }
                    } else {
                        let coll: f64 = nref
                            .iter()
                            .map(|n| quantify_collision_poly_poly_value(&cand, n))
                            .sum();
                        if best_coll.as_ref().is_none_or(|(bs, _)| coll < *bs) {
                            best_coll = Some((coll, pl));
                        }
                    }
                }
            }
            if let Some((_, pl)) = best_clear.or(best_coll) {
                local[i] = pl;
            }
        }
        if sheet_local_feasible(&local, instances, solver_sheets) {
            break;
        }
    }
    (
        sheet_local_feasible(&local, instances, solver_sheets),
        local,
    )
}

#[allow(clippy::too_many_arguments)]
fn try_seeded_critical_separation(
    optimizer: &SparrowOptimizer,
    working: &SparrowLayout,
    cand_inst_idx: usize,
    target_sheet: usize,
    seed_rmx: f64,
    seed_rmy: f64,
    seed_rot: f64,
    admitted_count: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    sheet: &SheetShape,
    started: &Instant,
    deadline_s: f64,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
) -> Option<SparrowLayout> {
    let inst = &instances[cand_inst_idx];
    let (ax, ay) = placement_anchor_from_rect_min(
        seed_rmx,
        seed_rmy,
        inst.part.width,
        inst.part.height,
        seed_rot,
    );
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
    // SGH-Q54C: on the skeleton path the overlap-tolerant density-biased separator (Q52,
    // rotation-correct) cleans an overlapping seed into interlock with continuous rotation; default
    // weight 2.0 so it is active even without VRS_ADMISSION_DENSITY_BIAS. Off the skeleton path the
    // explicit bias knob decides (0.0 ⇒ the legacy overlap-minimising separator).
    let w_density =
        admission_density_bias().max(if super::sheet_skeleton::skeleton_builder_enabled() {
            2.0
        } else {
            0.0
        });
    let (feasible, remapped) = if w_density > 0.0 {
        density_biased_separate(
            &trial,
            target_sheet,
            instances,
            solver_sheets,
            w_density,
            rng,
            started,
            step_deadline,
        )
    } else {
        separate_sheet_local(
            optimizer,
            &trial,
            target_sheet,
            sheet,
            instances,
            started,
            step_deadline,
            rng,
            diag,
        )
    };
    // SGH-Q55D'-2: if the sequential separator failed, try a SIMULTANEOUS simulated-annealing repack
    // of the whole sheet — the lever for the tight 3-way interlock the single-part descent (Q52)
    // cannot reach (it moves all critical parts at once into the deep-interlock configuration).
    //
    // SGH-Q64/Q61 follow-up: keep this available on the legacy builder path as well once we are
    // already admitting the 3rd-or-later critical on a sheet. Otherwise the builder-only reference
    // at spacing 0 silently loses the proven one-sheet 3-way interlock and spills the last part to a
    // new sheet even though the simultaneous repack is exactly the intended recovery lever.
    let allow_simultaneous_repack =
        super::sheet_skeleton::skeleton_builder_enabled() || admitted_count >= 2;
    let (feasible, remapped) = if !feasible && allow_simultaneous_repack {
        simultaneous_critical_repack(
            &trial,
            target_sheet,
            instances,
            solver_sheets,
            rng,
            started,
            step_deadline,
        )
    } else {
        (feasible, remapped)
    };
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
    None
}

#[allow(clippy::too_many_arguments)]
fn try_feature_first_direct(
    working: &SparrowLayout,
    cand_inst_idx: usize,
    target_sheet: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    sheet_sh: &Rc<CdePreparedShape>,
    sheet: &SheetShape,
    inst: &SPInstance,
    rot: f64,
    weights: &DensityWeights,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) -> Option<SparrowLayout> {
    bpp.bpp_critical_feature_admission_attempts += 1;
    let mut trial = working.clone();
    let cand_li = trial.placements.len();
    let (ax, ay) = placement_anchor_from_rect_min(
        sheet.min_x,
        sheet.min_y,
        inst.part.width,
        inst.part.height,
        rot,
    );
    trial.placements.push(SparrowPlacement {
        instance_idx: cand_inst_idx,
        sheet_index: target_sheet,
        x: ax,
        y: ay,
        rotation_deg: rot,
    });
    let mut tracker = SparrowCollisionTracker::build(&trial, instances, solver_sheets);
    tracker.shapes[cand_li] = None;
    if let Some(pl) = density_insert_part(
        cand_li,
        target_sheet,
        &trial,
        instances,
        solver_sheets,
        &tracker,
        sheet_sh,
        weights,
        rng,
        true,
        false,
        false,
        diag,
        bpp,
    ) {
        trial.placements[cand_li] = pl;
        if SparrowCollisionTracker::final_validation_tracker(&trial, instances, solver_sheets)
            .is_feasible()
        {
            bpp.bpp_critical_feature_admission_successes += 1;
            return Some(trial);
        }
    }
    bpp.bpp_critical_feature_admission_failures += 1;
    None
}

/// SGH-Q54D: largest edge-connected free-region area (mm²) on `sheet_idx` of `layout` — the
/// free-space-preserving ranking proxy for "does the next critical still have room?".
fn sheet_freespace_score(
    layout: &SparrowLayout,
    sheet_idx: usize,
    instances: &[SPInstance],
    sheet: &SheetShape,
) -> f64 {
    let bboxes: Vec<[f64; 4]> = layout
        .placements
        .iter()
        .filter(|p| p.sheet_index == sheet_idx)
        .map(|p| critical_world_bbox(layout, p.instance_idx, instances))
        .collect();
    super::sheet_skeleton::largest_edge_connected_free_area(
        &bboxes,
        sheet.min_x,
        sheet.min_y,
        sheet.max_x,
        sheet.max_y,
        super::sheet_skeleton::freespace_cell_mm(),
    )
}

/// SGH-Q55C: band-insert rect-min seeds — place the BandInsert big part INTO the free-space slot
/// bbox, edge-aligned to the slot corners, in the sheet-aware orientations (long/short edge + flip)
/// that fit the slot. The third reference big part goes into the preserved band, sheet-edge-aligned,
/// not interlocked to the anchor pair. Returns `(rect_min_x, rect_min_y, rotation_deg)`.
fn band_insert_seeds(
    inst: &SPInstance,
    sheet: &SheetShape,
    slot: [f64; 4],
) -> Vec<(f64, f64, f64)> {
    let (sx0, sy0, sx1, sy1) = (slot[0], slot[1], slot[2], slot[3]);
    let (slot_w, slot_h) = (sx1 - sx0, sy1 - sy0);
    let (long_dir, short_dir) = if sheet.width >= sheet.height {
        (0.0_f64, 90.0_f64)
    } else {
        (90.0_f64, 0.0_f64)
    };
    let mut out: Vec<(f64, f64, f64)> = Vec::new();
    for &rot in &[long_dir, short_dir, long_dir + 180.0, short_dir + 180.0] {
        let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
        if rw > slot_w + 1e-6 || rh > slot_h + 1e-6 {
            continue; // the part does not fit the slot in this orientation
        }
        // edge-aligned rect-min positions: the four slot corners (clamped on-sheet).
        for &(rmx, rmy) in &[
            (sx0, sy0),
            ((sx1 - rw).max(sx0), sy0),
            (sx0, (sy1 - rh).max(sy0)),
            ((sx1 - rw).max(sx0), (sy1 - rh).max(sy0)),
        ] {
            let rmx = rmx.clamp(sheet.min_x, (sheet.max_x - rw).max(sheet.min_x));
            let rmy = rmy.clamp(sheet.min_y, (sheet.max_y - rh).max(sheet.min_y));
            if !out.iter().any(|&(x, y, r)| {
                (x - rmx).abs() < 1.0 && (y - rmy).abs() < 1.0 && (r - rot).abs() < 1e-6
            }) {
                out.push((rmx, rmy, rot));
            }
        }
    }
    out
}

/// SGH-Q55D'-2: **simultaneous** multi-part repack of a sheet's critical parts via simulated
/// annealing. The sequential single-part coordinate descent (`density_biased_separate`, Q52) was
/// proven NOT to converge on the tight 3-way interlock; this perturbs ALL parts at once and accepts
/// via Metropolis, so the deep-interlock configuration (overlapping bboxes, nested contours — the
/// reference's actual layout) can be reached. Energy = pairwise spacing-collision overlap proxy +
/// boundary penalty; continuous rotation preserved; the CDE decides final feasibility.
fn simultaneous_critical_repack(
    layout: &SparrowLayout,
    sheet_idx: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    rng: &mut DeterministicRng,
    started: &Instant,
    deadline_s: f64,
) -> (bool, Vec<SparrowPlacement>) {
    let sheet = &solver_sheets[sheet_idx];
    let mut cur: Vec<SparrowPlacement> = layout
        .placements
        .iter()
        .filter(|p| p.sheet_index == sheet_idx)
        .map(|p| SparrowPlacement {
            sheet_index: sheet_idx,
            ..p.clone()
        })
        .collect();
    if cur.len() <= 1 {
        return (sheet_local_feasible(&cur, instances, solver_sheets), cur);
    }
    const BOUNDARY_W: f64 = 50.0;
    let energy = |poses: &[SparrowPlacement]| -> f64 {
        let shapes: Vec<Option<CdePreparedShape>> = poses
            .iter()
            .map(|p| {
                let inst = &instances[p.instance_idx];
                transform_base_to_candidate(
                    inst.base_shape.as_ref(),
                    p.x,
                    p.y,
                    p.rotation_deg,
                )
            })
            .collect();
        let mut e = 0.0;
        for i in 0..poses.len() {
            for j in (i + 1)..poses.len() {
                if let (Some(a), Some(b)) = (&shapes[i], &shapes[j]) {
                    e += quantify_collision_poly_poly_value(a, b);
                }
            }
        }
        for p in poses {
            let inst = &instances[p.instance_idx];
            let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, p.rotation_deg);
            let (rmx, rmy) =
                rect_min_from_anchor(p.x, p.y, inst.part.width, inst.part.height, p.rotation_deg);
            let over = (sheet.min_x - rmx).max(0.0)
                + (rmx + rw - sheet.max_x).max(0.0)
                + (sheet.min_y - rmy).max(0.0)
                + (rmy + rh - sheet.max_y).max(0.0);
            e += over * BOUNDARY_W;
        }
        e
    };
    let mut cur_e = energy(&cur);
    let mut best = cur.clone();
    let mut best_e = cur_e;
    let t0 = (cur_e / cur.len() as f64).max(1.0);
    const MAX_ITER: usize = 8000;
    for it in 0..MAX_ITER {
        if best_e <= 1e-6 || started.elapsed().as_secs_f64() >= deadline_s {
            break;
        }
        let frac = it as f64 / MAX_ITER as f64;
        let temp = t0 * (1.0 - frac).max(0.02);
        let tscale = sheet.width.min(sheet.height) * 0.15 * (1.0 - frac).max(0.04);
        let rscale = 25.0 * (1.0 - frac).max(0.04);
        let mut trial = cur.clone();
        for p in trial.iter_mut() {
            let inst = &instances[p.instance_idx];
            p.x += (rng.next_f64() - 0.5) * 2.0 * tscale;
            p.y += (rng.next_f64() - 0.5) * 2.0 * tscale;
            if inst.continuous_rotation {
                p.rotation_deg =
                    (p.rotation_deg + (rng.next_f64() - 0.5) * 2.0 * rscale).rem_euclid(360.0);
            }
            // clamp the anchor so the rotated bbox stays on-sheet.
            let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, p.rotation_deg);
            let (mut rmx, mut rmy) =
                rect_min_from_anchor(p.x, p.y, inst.part.width, inst.part.height, p.rotation_deg);
            rmx = rmx.clamp(sheet.min_x, (sheet.max_x - rw).max(sheet.min_x));
            rmy = rmy.clamp(sheet.min_y, (sheet.max_y - rh).max(sheet.min_y));
            let (ax, ay) = placement_anchor_from_rect_min(
                rmx,
                rmy,
                inst.part.width,
                inst.part.height,
                p.rotation_deg,
            );
            p.x = ax;
            p.y = ay;
        }
        let trial_e = energy(&trial);
        let de = trial_e - cur_e;
        if de < 0.0 || rng.next_f64() < (-de / temp).exp() {
            cur = trial;
            cur_e = trial_e;
            if cur_e < best_e {
                best_e = cur_e;
                best = cur.clone();
            }
        }
    }
    (sheet_local_feasible(&best, instances, solver_sheets), best)
}

/// SGH-Q54D: record the accepted-feature-admission metrics for `seed` onto the diagnostics.
fn commit_feature_admission(
    bpp: &mut BppReductionDiagnostics,
    diag: &mut SparrowDiagnostics,
    seed: &super::feature_candidate_generator::CandidateSeed,
) {
    bpp.bpp_critical_feature_admission_successes += 1;
    bpp.bpp_feature_candidates_accepted += 1;
    diag.feature_candidates_accepted += 1;
    bpp.bpp_accepted_feature_pair_type = Some(seed.pair_type());
    diag.accepted_feature_pair_type = Some(seed.pair_type());
    bpp.bpp_feature_refine_seed_rotation_deg = Some(seed.seed_rotation_deg);
    bpp.bpp_feature_refine_refined_rotation_deg = Some(seed.rotation_seed_deg);
    bpp.bpp_feature_refine_iterations = seed.refine_iterations;
    bpp.bpp_feature_refine_rejection_reason = seed.refine_rejection_reason.clone();
    diag.feature_refine_seed_rotation_deg = Some(seed.seed_rotation_deg);
    diag.feature_refine_refined_rotation_deg = Some(seed.rotation_seed_deg);
    diag.feature_refine_iterations = seed.refine_iterations;
    diag.feature_refine_rejection_reason = seed.refine_rejection_reason.clone();
}

fn try_simultaneous_same_part_group_authority(
    working: &SparrowLayout,
    cand_inst_idx: usize,
    target_sheet: usize,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    bpp: &mut BppReductionDiagnostics,
) -> Option<SparrowLayout> {
    let sheet = &solver_sheets[target_sheet];
    let cand_inst = &instances[cand_inst_idx];
    let sheet_placements: Vec<&SparrowPlacement> = working
        .placements
        .iter()
        .filter(|p| p.sheet_index == target_sheet)
        .collect();
    let same_part_placements: Vec<&SparrowPlacement> = sheet_placements
        .iter()
        .copied()
        .filter(|p| instances[p.instance_idx].part_id == cand_inst.part_id)
        .collect();
    if same_part_placements.is_empty() {
        return None;
    }
    let target_count = same_part_placements.len() + 1;
    if !(2..=3).contains(&target_count) {
        return None;
    }
    let observed_edge_inset = same_part_placements
        .iter()
        .map(|p| {
            let inst = &instances[p.instance_idx];
            let (rmx, rmy) =
                rect_min_from_anchor(p.x, p.y, inst.part.width, inst.part.height, p.rotation_deg);
            let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, p.rotation_deg);
            [
                rmx - sheet.min_x,
                rmy - sheet.min_y,
                sheet.max_x - (rmx + rw),
                sheet.max_y - (rmy + rh),
            ]
            .into_iter()
            .fold(f64::INFINITY, f64::min)
        })
        .fold(f64::INFINITY, f64::min)
        .clamp(0.0, f64::INFINITY);

    bpp.bpp_q61_simultaneous_critical_consulted = true;
    bpp.bpp_q61_simultaneous_group_attempts += 1;

    if target_count >= 3 && super::interlock_pair::interlock_pair_enabled() {
        bpp.bpp_q61_pair_index_consulted = true;
        if let Some(anchor_pl) = same_part_placements.first() {
            let anchor_inst = &instances[anchor_pl.instance_idx];
            let occupied_boxes: Vec<[f64; 4]> = working
                .placements
                .iter()
                .filter(|p| p.sheet_index == target_sheet)
                .map(|p| critical_world_bbox(working, p.instance_idx, instances))
                .collect();
            let sheet_bbox = [sheet.min_x, sheet.min_y, sheet.max_x, sheet.max_y];
            match super::interlock_pair::admit_interlock_pair_against_live_anchor(
                anchor_inst,
                anchor_pl,
                cand_inst,
                &occupied_boxes,
                sheet_bbox,
            ) {
                Ok(adm) => {
                    bpp.bpp_q61_pair_candidates_generated +=
                        adm.diagnostics.pair_candidates_generated;
                    bpp.bpp_q65_pair_candidates_valid += adm.diagnostics.pair_candidates_valid;
                    if adm.diagnostics.pair_candidates_generated == 0 {
                        bpp.bpp_q61_pair_rejection_summary = Some(
                            "same_part_group_authority: pair_index_generated_no_candidates"
                                .to_string(),
                        );
                    }
                }
                Err(err) => {
                    bpp.bpp_q61_pair_rejection_summary =
                        Some(format!("same_part_group_authority_pair_index_error: {err}"));
                }
            }
        }
    }

    if sheet_placements.len() != same_part_placements.len() {
        bpp.bpp_q67_simultaneous_rejection_summary = Some(format!(
            "mixed_sheet_group_not_supported: sheet={target_sheet} same_part_on_sheet={} total_on_sheet={}",
            same_part_placements.len(),
            sheet_placements.len()
        ));
        return None;
    }

    match super::critical_simultaneous::admit_live_same_part_group(
        cand_inst,
        target_count,
        sheet,
        observed_edge_inset,
    ) {
        Ok(adm) => {
            bpp.bpp_q67_simultaneous_candidates_generated += adm.arrangements.len();
            bpp.bpp_q67_simultaneous_best_partial_count = bpp
                .bpp_q67_simultaneous_best_partial_count
                .max(adm.best_partial_count);
            if adm.best_partial_source != "none" {
                bpp.bpp_q67_simultaneous_best_partial_source =
                    Some(adm.best_partial_source.clone());
            }
            if adm
                .arrangements
                .iter()
                .any(|a| a.any_part_moved_in_refinement)
            {
                bpp.bpp_q61_previous_group_parts_moved = true;
            }

            if adm.full_success {
                let preferred_source = adm.best_partial_source.clone();
                let mut full_arrangements: Vec<
                    &super::critical_simultaneous::GroupArrangementResult,
                > = adm
                    .arrangements
                    .iter()
                    .filter(|a| a.placed_count >= target_count)
                    .collect();
                full_arrangements.sort_by(|a, b| {
                    let a_pref = a.arrangement.as_str() == preferred_source;
                    let b_pref = b.arrangement.as_str() == preferred_source;
                    b_pref.cmp(&a_pref).then_with(|| {
                        b.score
                            .partial_cmp(&a.score)
                            .unwrap_or(std::cmp::Ordering::Equal)
                    })
                });
                let mut group_indices: Vec<usize> = same_part_placements
                    .iter()
                    .map(|p| p.instance_idx)
                    .collect();
                group_indices.push(cand_inst_idx);
                let mut best_failed_summary: Option<String> = None;
                for best in full_arrangements {
                    let mut out_placements: Vec<SparrowPlacement> = working
                        .placements
                        .iter()
                        .filter(|p| p.sheet_index != target_sheet)
                        .cloned()
                        .collect();
                    for (instance_idx, placed) in group_indices.iter().zip(best.placed.iter()) {
                        out_placements.push(SparrowPlacement {
                            instance_idx: *instance_idx,
                            sheet_index: target_sheet,
                            x: placed.x,
                            y: placed.y,
                            rotation_deg: placed.rotation_deg,
                        });
                    }
                    let out = SparrowLayout {
                        placements: out_placements,
                    };
                    let tracker = SparrowCollisionTracker::final_validation_tracker(
                        &out,
                        instances,
                        solver_sheets,
                    );
                    if tracker.is_feasible() {
                        bpp.bpp_q67_simultaneous_authority_used = true;
                        bpp.bpp_q67_simultaneous_full_successes += 1;
                        bpp.bpp_q67_simultaneous_accepted_group_source =
                            Some(best.arrangement.as_str().to_string());
                        return Some(out);
                    }
                    best_failed_summary = Some(format!(
                        "source={} colliding_pairs={} boundary_violations={} unsupported={}",
                        best.arrangement.as_str(),
                        tracker.colliding_pairs(),
                        tracker.boundary_violations(),
                        tracker.unsupported
                    ));
                }
                bpp.bpp_q67_simultaneous_rejection_summary = Some(format!(
                    "full_group_failed_final_validation: target_count={target_count} preferred_source={preferred_source} details={}",
                    best_failed_summary.unwrap_or_else(|| "none".to_string())
                ));
                return None;
            }

            if adm.best_partial_count > 0 {
                bpp.bpp_q67_simultaneous_partial_successes += 1;
            }
            bpp.bpp_q67_simultaneous_rejection_summary = Some(format!(
                "target_count={target_count} best_partial={} best_source={} -> fallback",
                adm.best_partial_count, adm.best_partial_source
            ));
            None
        }
        Err(err) => {
            bpp.bpp_q67_simultaneous_rejection_summary =
                Some(format!("simultaneous_group_error: {err}"));
            None
        }
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
    role: Option<super::sheet_skeleton::SkeletonRole>,
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
    let admitted_count = working
        .placements
        .iter()
        .filter(|p| p.sheet_index == target_sheet)
        .count();
    if super::critical_simultaneous::simultaneous_critical_enabled() && admitted_count >= 2 {
        if let Some(out) = try_simultaneous_same_part_group_authority(
            working,
            cand_inst_idx,
            target_sheet,
            instances,
            solver_sheets,
            bpp,
        ) {
            return Some(out);
        }
    }
    // SGH-Q54C: the skeleton path drives the same feature-first admission (clearance-aware seeds +
    // overlap-tolerant separation), so VRS_SHEET_BUILDER_SKELETON alone enables it (incl. feature
    // candidate generation). Off the skeleton path the Q53D gates decide.
    let skeleton_on = super::sheet_skeleton::skeleton_builder_enabled();
    // SGH-Q64 production cutover: the constructive sheet builder itself should exercise the newest
    // critical admission path instead of silently staying on the legacy direct-only branch unless a
    // second env flag is also set. The explicit envs still matter outside the builder path.
    let feature_first = sheet_builder_enabled()
        || ((critical_feature_admission_enabled() || skeleton_on)
            && (feature_candidate_generation_enabled() || skeleton_on));

    if skeleton_on && super::interlock_pair::interlock_pair_enabled() && admitted_count >= 1 {
        bpp.bpp_q61_pair_index_consulted = true;
        if role != Some(super::sheet_skeleton::SkeletonRole::Interlock)
            && bpp.bpp_q61_pair_rejection_summary.is_none()
        {
            let role_label = role
                .map(|r| r.as_str().to_string())
                .unwrap_or_else(|| "none".to_string());
            bpp.bpp_q61_pair_rejection_summary =
                Some(format!("pair_index_not_applicable_for_role={role_label}"));
        }
    }

    if feature_first {
        // ── SGH-Q61: Anchor role consults the Q56C SheetEdgePlacementCatalog (edge+corner) and feeds
        // its candidates into the SAME free-space ranking as the existing sheet-edge feature seeds —
        // NON-pre-empting: a catalog candidate only wins if its free-space score is at least as good as
        // the existing path's best, so the proven co-movable interlock seeding is never regressed. ──
        let forced_latest = sheet_builder_forced_latest_enabled();
        let strict_edge_lock = forced_latest && forced_latest_strict_edge_lock(inst);
        let anchor_like_role =
            role == Some(super::sheet_skeleton::SkeletonRole::Anchor) || strict_edge_lock;
        let mut best_anchor_corner: Option<AnchorCatalogChoice> = None;
        let mut best_anchor_center: Option<AnchorCatalogChoice> = None;
        if skeleton_on
            && anchor_like_role
            && super::sheet_edge_placement_catalog::anchor_catalog_enabled()
        {
            let cands =
                super::sheet_edge_placement_catalog::anchor_candidates_for_instance(inst, sheet);
            bpp.bpp_q61_anchor_catalog_consulted = true;
            bpp.bpp_q61_anchor_catalog_candidates_generated += cands.len();
            let mut cat_feasible = 0usize;
            let cat_feasible_limit = if strict_edge_lock { cands.len() } else { 6 };
            for c in &cands {
                if started.elapsed().as_secs_f64() >= deadline_s {
                    break;
                }
                bpp.bpp_role_anchor_generated += 1;
                if let Some(out) = try_seeded_critical_separation(
                    optimizer,
                    working,
                    cand_inst_idx,
                    target_sheet,
                    c.rect_min_x,
                    c.rect_min_y,
                    c.rotation_deg,
                    admitted_count,
                    instances,
                    solver_sheets,
                    sheet,
                    started,
                    deadline_s,
                    rng,
                    diag,
                ) {
                    let out = if forced_latest {
                        repair_anchor_flush_alignment(
                            &out,
                            cand_inst_idx,
                            instances,
                            solver_sheets,
                            sheet,
                            c.target_sheet_edge,
                            Some(c.secondary_axis_policy),
                        )
                    } else {
                        out
                    };
                    let Some((score, _metrics)) = forced_latest_anchor_catalog_score(
                        forced_latest,
                        strict_edge_lock,
                        &out,
                        cand_inst_idx,
                        target_sheet,
                        instances,
                        sheet,
                        c.target_sheet_edge,
                        c.secondary_axis_policy,
                        c.rotation_deg,
                    ) else {
                        continue;
                    };
                    let choice = AnchorCatalogChoice {
                        score,
                        layout: out,
                        source: c.source,
                        secondary: c.secondary_axis_policy,
                        target_edge: c.target_sheet_edge,
                        seed_rotation_deg: c.rotation_deg,
                    };
                    let slot = if anchor_secondary_is_center(c.secondary_axis_policy) {
                        &mut best_anchor_center
                    } else {
                        &mut best_anchor_corner
                    };
                    if slot.as_ref().is_none_or(|best| choice.score > best.score) {
                        *slot = Some(choice);
                    }
                    cat_feasible += 1;
                    if cat_feasible >= cat_feasible_limit {
                        break; // bounded: rank only a few feasible catalog candidates
                    }
                }
            }
        }
        let best_anchor_cat = choose_anchor_catalog_candidate(
            forced_latest,
            strict_edge_lock,
            best_anchor_corner,
            best_anchor_center,
            bpp,
        );
        // SGH-Q64 production authority cutover: once the skeleton role is known, the role-routed
        // production path gets first authority. The older generic direct insert remains a fallback,
        // but it must not short-circuit Anchor / Interlock / BandInsert before their own path runs.
        let skip_direct_for_role = role_aware_path_should_skip_generic_direct(skeleton_on, role);
        if !skip_direct_for_role {
            // ── (1) FEATURE-FIRST DIRECT: feature seeds only, admitted anchors fixed ───────────
            if let Some(out) = try_feature_first_direct(
                working,
                cand_inst_idx,
                target_sheet,
                instances,
                solver_sheets,
                &sheet_sh,
                sheet,
                inst,
                rot,
                &weights,
                rng,
                diag,
                bpp,
            ) {
                return Some(out);
            }
        } // end generic direct stage when no role-aware authority cutover applies

        // ── (2) FEATURE-FIRST CO-MOVABLE: seed from contour features, then separate together ──
        let feature_neighbours: Vec<PlacedFeatureNeighbour<'_>> = working
            .placements
            .iter()
            .filter(|p| p.sheet_index == target_sheet)
            .map(|placement| PlacedFeatureNeighbour {
                placement,
                instance: &instances[placement.instance_idx],
            })
            .collect();
        let feature_seeds = generate_feature_candidate_seeds_for_sheet(
            inst,
            rot,
            sheet,
            &feature_neighbours,
            density_samples() + 20,
        );
        record_feature_seed_metrics(&feature_seeds, bpp, diag);
        bpp.bpp_critical_candidate_rejection_summary =
            feature_seed_rejection_summary(&feature_seeds)
                .or_else(|| Some("no_feature_seed_rejections".to_string()));
        bpp.bpp_critical_feature_admission_attempts += 1;
        // SGH-Q54C: on the skeleton path, the overlap-tolerant separator cleans not-yet-clear seeds,
        // so do NOT pre-filter on refine_success (the Q53 behaviour that dropped every clearance-aware
        // seed → 0 accepted). Off the skeleton path, keep the Q53 refine-clear filter.
        let take_n = if skeleton_on { 24 } else { 16 };
        // SGH-Q54D: on the skeleton path, keep the feasible result that leaves the largest
        // edge-connected free band for the NEXT critical (free-space-preserving), not just the first
        // feasible. Off the skeleton path, commit the first feasible (Q53 behaviour).
        // SGH-Q55B: route candidate generation by skeleton role — Anchor → sheet-edge anchors,
        // Interlock → neighbour feature pairs, BandInsert → all (Q55C plugs the band generator here).
        use super::sheet_skeleton::SkeletonRole;
        let role_match = |seed: &super::feature_candidate_generator::CandidateSeed| -> bool {
            if anchor_like_role {
                seed.target_feature_type == "sheet_edge"
            } else {
                match role {
                    Some(SkeletonRole::Anchor) => seed.target_feature_type == "sheet_edge",
                    Some(SkeletonRole::Interlock) => seed.target_feature_type != "sheet_edge",
                    _ => true,
                }
            }
        };
        if skeleton_on {
            let gen = feature_seeds.iter().filter(|s| role_match(s)).count();
            match if anchor_like_role {
                Some(SkeletonRole::Anchor)
            } else {
                role
            } {
                Some(SkeletonRole::Anchor) => bpp.bpp_role_anchor_generated += gen,
                Some(SkeletonRole::Interlock) => bpp.bpp_role_interlock_generated += gen,
                Some(SkeletonRole::BandInsert) => bpp.bpp_role_band_insert_generated += gen,
                None => {}
            }
        }
        let role_accept = |bpp: &mut BppReductionDiagnostics| match role {
            Some(SkeletonRole::Anchor) => bpp.bpp_role_anchor_accepted += 1,
            Some(SkeletonRole::Interlock) => bpp.bpp_role_interlock_accepted += 1,
            Some(SkeletonRole::BandInsert) => bpp.bpp_role_band_insert_accepted += 1,
            None => {}
        };
        // SGH-Q55C: BandInsert role → place the third big part INTO the preserved free-space slot
        // (edge-aligned to the slot, sheet-edge-parallel), not interlocked to the anchor pair.
        if skeleton_on && role == Some(SkeletonRole::BandInsert) && !strict_edge_lock {
            let occ: Vec<[f64; 4]> = working
                .placements
                .iter()
                .filter(|p| p.sheet_index == target_sheet)
                .map(|p| critical_world_bbox(working, p.instance_idx, instances))
                .collect();
            if let Some(slot) = super::sheet_skeleton::largest_edge_connected_free_slot(
                &occ,
                sheet.min_x,
                sheet.min_y,
                sheet.max_x,
                sheet.max_y,
                super::sheet_skeleton::freespace_cell_mm(),
            ) {
                bpp.bpp_band_slot_found = true;
                // ── SGH-Q61: try the Q59 true-extreme slot-edge producer FIRST (gated), then the
                // existing bbox band_insert_seeds as fallback. ──
                if super::band_insert_slot_edge::band_insert_true_extreme_enabled() {
                    bpp.bpp_q61_band_insert_true_extreme_consulted = true;
                    let sheet_bbox = [sheet.min_x, sheet.min_y, sheet.max_x, sheet.max_y];
                    let seeds = super::band_insert_slot_edge::slot_edge_seeds_for_instance(
                        inst, slot, sheet_bbox,
                    );
                    bpp.bpp_q61_slot_edge_candidates_generated += seeds.len();
                    for s in &seeds {
                        if started.elapsed().as_secs_f64() >= deadline_s {
                            break;
                        }
                        bpp.bpp_role_band_insert_generated += 1;
                        if let Some(out) = try_seeded_critical_separation(
                            optimizer,
                            working,
                            cand_inst_idx,
                            target_sheet,
                            s.rect_min_x,
                            s.rect_min_y,
                            s.rotation_deg,
                            admitted_count,
                            instances,
                            solver_sheets,
                            sheet,
                            started,
                            deadline_s,
                            rng,
                            diag,
                        ) {
                            bpp.bpp_critical_feature_admission_successes += 1;
                            bpp.bpp_feature_candidates_accepted += 1;
                            bpp.bpp_role_band_insert_accepted += 1;
                            bpp.bpp_q61_slot_edge_candidates_accepted += 1;
                            return Some(out);
                        }
                    }
                    // No true-extreme slot-edge candidate accepted → fall back to bbox seeds.
                    bpp.bpp_q61_fallback_to_bbox_band_insert = true;
                }
                for (rmx, rmy, brot) in band_insert_seeds(inst, sheet, slot) {
                    if started.elapsed().as_secs_f64() >= deadline_s {
                        break;
                    }
                    bpp.bpp_role_band_insert_generated += 1;
                    if let Some(out) = try_seeded_critical_separation(
                        optimizer,
                        working,
                        cand_inst_idx,
                        target_sheet,
                        rmx,
                        rmy,
                        brot,
                        admitted_count,
                        instances,
                        solver_sheets,
                        sheet,
                        started,
                        deadline_s,
                        rng,
                        diag,
                    ) {
                        bpp.bpp_critical_feature_admission_successes += 1;
                        bpp.bpp_feature_candidates_accepted += 1;
                        bpp.bpp_role_band_insert_accepted += 1;
                        return Some(out);
                    }
                }
            }
        }
        // ── SGH-Q61: Interlock role consults the PairCompatibilityIndex (Q57A/B) BEFORE the generic
        // neighbour-feature candidates. Pair-derived seeds are placed relative to an already-placed
        // Anchor and resolved by the co-movable separation; the neighbour path remains the fallback. ──
        if skeleton_on
            && role == Some(SkeletonRole::Interlock)
            && !strict_edge_lock
            && super::interlock_pair::interlock_pair_enabled()
        {
            bpp.bpp_q61_pair_index_consulted = true;
            // Find a placed critical anchor on the target sheet (the deepest/first admitted).
            let anchor_placement = working
                .placements
                .iter()
                .find(|p| p.sheet_index == target_sheet);
            if let Some(anchor_pl) = anchor_placement {
                let anchor_inst = &instances[anchor_pl.instance_idx];
                let occupied_boxes: Vec<[f64; 4]> = working
                    .placements
                    .iter()
                    .filter(|p| p.sheet_index == target_sheet)
                    .map(|p| critical_world_bbox(working, p.instance_idx, instances))
                    .collect();
                let sheet_bbox = [sheet.min_x, sheet.min_y, sheet.max_x, sheet.max_y];
                match super::interlock_pair::admit_interlock_pair_against_live_anchor(
                    anchor_inst,
                    anchor_pl,
                    inst,
                    &occupied_boxes,
                    sheet_bbox,
                ) {
                    Ok(adm) => {
                        bpp.bpp_q61_pair_candidates_generated +=
                            adm.diagnostics.pair_candidates_generated;
                        bpp.bpp_q65_pair_candidates_valid += adm.diagnostics.pair_candidates_valid;
                        bpp.bpp_role_interlock_generated +=
                            adm.diagnostics.pair_candidates_generated;
                        let mut separation_rejects = 0usize;
                        for s in &adm.considered {
                            if started.elapsed().as_secs_f64() >= deadline_s {
                                break;
                            }
                            if let Some(out) = try_seeded_critical_separation(
                                optimizer,
                                working,
                                cand_inst_idx,
                                target_sheet,
                                s.accepted_x,
                                s.accepted_y,
                                s.accepted_rotation_deg,
                                admitted_count,
                                instances,
                                solver_sheets,
                                sheet,
                                started,
                                deadline_s,
                                rng,
                                diag,
                            ) {
                                bpp.bpp_critical_feature_admission_successes += 1;
                                bpp.bpp_feature_candidates_accepted += 1;
                                bpp.bpp_role_interlock_accepted += 1;
                                bpp.bpp_q61_pair_candidates_accepted += 1;
                                bpp.bpp_q65_accepted_pair_source =
                                    Some(s.accepted_candidate_source.clone());
                                bpp.bpp_q65_accepted_pair_score = Some(s.pair_score);
                                bpp.bpp_q65_accepted_pair_relative_transform = Some(format!(
                                    "dx={:.4}, dy={:.4}, delta_rot={:.4}",
                                    s.relative_dx, s.relative_dy, s.rotation_delta_deg
                                ));
                                return Some(out);
                            }
                            separation_rejects += 1;
                        }
                        bpp.bpp_q61_interlock_fallback_to_neighbour = true;
                        bpp.bpp_q61_pair_rejection_summary = Some(format!(
                            "pair_candidates_generated={} valid_pair_candidates={} rejected_boundary={} rejected_collision={} rejected_transform={} separation_failed={} pair_not_found={} -> neighbour fallback",
                            adm.diagnostics.pair_candidates_generated,
                            adm.diagnostics.pair_candidates_valid,
                            adm.diagnostics.rejection_boundary_violation,
                            adm.diagnostics.rejection_collision,
                            adm.diagnostics.rejection_transform_invalid,
                            separation_rejects,
                            adm.diagnostics.rejection_pair_not_found
                        ));
                    }
                    Err(err) => {
                        bpp.bpp_q61_interlock_fallback_to_neighbour = true;
                        bpp.bpp_q61_pair_rejection_summary = Some(format!(
                            "interlock_pair_error: {} -> neighbour fallback",
                            err
                        ));
                    }
                }
            } else {
                bpp.bpp_q61_interlock_fallback_to_neighbour = true;
                bpp.bpp_q61_pair_rejection_summary = Some(
                    "role_anchor_missing: no placed anchor on sheet -> neighbour fallback"
                        .to_string(),
                );
            }
        }
        let mut best_skeleton: Option<(
            f64,
            SparrowLayout,
            &super::feature_candidate_generator::CandidateSeed,
        )> = None;
        let mut feasible_seen = 0usize;
        for seed in feature_seeds
            .iter()
            .filter(|seed| role_match(seed) && (skeleton_on || seed.refine_success))
            .take(take_n)
        {
            if let Some(out) = try_seeded_critical_separation(
                optimizer,
                working,
                cand_inst_idx,
                target_sheet,
                seed.x,
                seed.y,
                seed.rotation_seed_deg,
                admitted_count,
                instances,
                solver_sheets,
                sheet,
                started,
                deadline_s,
                rng,
                diag,
            ) {
                if skeleton_on {
                    let target_edge = sheet_edge_alignment_kind_to_edge(seed.alignment_kind);
                    let out = if forced_latest && anchor_like_role {
                        target_edge.map_or(out.clone(), |edge| {
                            repair_anchor_flush_alignment(
                                &out,
                                cand_inst_idx,
                                instances,
                                solver_sheets,
                                sheet,
                                edge,
                                None,
                            )
                        })
                    } else {
                        out
                    };
                    let score = if anchor_like_role {
                        forced_latest_anchor_feature_score(
                            forced_latest,
                            strict_edge_lock,
                            &out,
                            cand_inst_idx,
                            target_sheet,
                            instances,
                            sheet,
                            target_edge,
                            seed.rotation_seed_deg,
                        )
                    } else {
                        Some(sheet_freespace_score(&out, target_sheet, instances, sheet))
                    };
                    if let Some(score) = score {
                        if best_skeleton.as_ref().is_none_or(|(s, _, _)| score > *s) {
                            best_skeleton = Some((score, out, seed));
                        }
                        feasible_seen += 1;
                        // SGH-Q54D: rank a BOUNDED number of feasible candidates by free-space (the
                        // separation budget is precious — don't separate all 24 seeds).
                        if feasible_seen >= 4 || started.elapsed().as_secs_f64() >= deadline_s {
                            break;
                        }
                    }
                } else {
                    commit_feature_admission(bpp, diag, seed);
                    return Some(out);
                }
            }
        }
        let feature_score = best_skeleton.as_ref().map(|(score, _, _)| *score);
        let catalog_score = best_anchor_cat.as_ref().map(|choice| choice.score);
        if skeleton_on && anchor_like_role && best_anchor_cat.is_some() {
            bpp.bpp_q68_anchor_competition_ran = true;
            bpp.bpp_q68_anchor_feature_score = feature_score;
            bpp.bpp_q68_anchor_catalog_score = catalog_score;
        }
        match choose_anchor_authority_winner(feature_score, catalog_score) {
            AnchorAuthorityWinner::Catalog => {
                if let Some(choice) = best_anchor_cat {
                    bpp.bpp_q68_anchor_selected_path = Some("catalog".to_string());
                    bpp.bpp_critical_feature_admission_successes += 1;
                    bpp.bpp_feature_candidates_accepted += 1;
                    if anchor_like_role {
                        bpp.bpp_role_anchor_accepted += 1;
                    }
                    bpp.bpp_q61_anchor_catalog_accepted += 1;
                    bpp.bpp_q61_accepted_anchor_source = Some(choice.source.to_string());
                    bpp.bpp_q61_accepted_anchor_secondary_policy =
                        Some(choice.secondary.to_string());
                    if let Some(metrics) = anchor_alignment_metrics(
                        &choice.layout,
                        cand_inst_idx,
                        instances,
                        sheet,
                        choice.target_edge,
                        choice.secondary,
                        choice.seed_rotation_deg,
                    ) {
                        record_anchor_alignment_diag(bpp, metrics);
                    }
                    return Some(choice.layout);
                }
            }
            AnchorAuthorityWinner::Feature => {
                if let Some((_, out, seed)) = best_skeleton {
                    if skeleton_on && anchor_like_role && best_anchor_cat.is_some() {
                        bpp.bpp_q68_anchor_selected_path = Some("feature".to_string());
                    }
                    commit_feature_admission(bpp, diag, seed);
                    role_accept(bpp); // SGH-Q55B: per-role accepted count
                    if anchor_like_role {
                        record_anchor_min_edge_diag(bpp, &out, cand_inst_idx, instances, sheet);
                    }
                    return Some(out);
                }
            }
            AnchorAuthorityWinner::None => {}
        }
        if skip_direct_for_role {
            if forced_latest && anchor_like_role {
                bpp.bpp_q71_anchor_direct_fallback_blocked = true;
            } else {
                // SGH-Q64: role-aware routing gets first shot, but the older direct path still remains a
                // second-line fallback inside the same admission attempt so proven spacing-0 wins are not
                // thrown away when the newer path cannot yet finish the job.
                if let Some(out) = try_feature_first_direct(
                    working,
                    cand_inst_idx,
                    target_sheet,
                    instances,
                    solver_sheets,
                    &sheet_sh,
                    sheet,
                    inst,
                    rot,
                    &weights,
                    rng,
                    diag,
                    bpp,
                ) {
                    return Some(out);
                }
            }
        }
        bpp.bpp_critical_feature_admission_failures += 1;
    }

    // ── (3) EXPLICIT FALLBACK: bbox/uniform direct insertion, then centroid-seeded co-movable ──
    if sheet_builder_forced_latest_enabled()
        && (role == Some(super::sheet_skeleton::SkeletonRole::Anchor)
            || forced_latest_strict_edge_lock(inst))
    {
        bpp.bpp_q71_anchor_direct_fallback_blocked = true;
        return None;
    }
    {
        let mut trial = working.clone();
        let cand_li = trial.placements.len();
        let (ax, ay) = placement_anchor_from_rect_min(
            sheet.min_x,
            sheet.min_y,
            inst.part.width,
            inst.part.height,
            rot,
        );
        trial.placements.push(SparrowPlacement {
            instance_idx: cand_inst_idx,
            sheet_index: target_sheet,
            x: ax,
            y: ay,
            rotation_deg: rot,
        });
        let mut tracker = SparrowCollisionTracker::build(&trial, instances, solver_sheets);
        tracker.shapes[cand_li] = None;
        if let Some(pl) = density_insert_part(
            cand_li,
            target_sheet,
            &trial,
            instances,
            solver_sheets,
            &tracker,
            &sheet_sh,
            &weights,
            rng,
            false,
            true,
            true,
            diag,
            bpp,
        ) {
            trial.placements[cand_li] = pl;
            if SparrowCollisionTracker::final_validation_tracker(&trial, instances, solver_sheets)
                .is_feasible()
            {
                return Some(trial);
            }
        }
    }

    let (cx, cy) = sheet_centroid(working, target_sheet);
    const RESTARTS: usize = 4;
    for r in 0..RESTARTS {
        if started.elapsed().as_secs_f64() >= deadline_s {
            break;
        }
        let jx = (rng.next_f64() - 0.5) * sheet.width * 0.3;
        let jy = (rng.next_f64() - 0.5) * sheet.height * 0.3;
        let sx = (cx + jx).clamp(sheet.min_x, (sheet.max_x - rw).max(sheet.min_x));
        let sy = (cy + jy).clamp(sheet.min_y, (sheet.max_y - rh).max(sheet.min_y));
        let seed_rot = if r == 0 { rot } else { rot + 90.0 * (r as f64) };
        if let Some(out) = try_seeded_critical_separation(
            optimizer,
            working,
            cand_inst_idx,
            target_sheet,
            sx,
            sy,
            seed_rot,
            admitted_count,
            instances,
            solver_sheets,
            sheet,
            started,
            deadline_s,
            rng,
            diag,
        ) {
            return Some(out);
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
    diag: &mut SparrowDiagnostics,
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
        cand_li,
        sheet,
        &trial,
        instances,
        solver_sheets,
        &tracker,
        &sheet_sh,
        weights,
        rng,
        true,
        true,
        true,
        diag,
        bpp,
    )?;
    trial.placements[cand_li] = pl; // density_insert_part guarantees a CDE-clear placement
    Some(trial)
}

/// True when the critical-aware constructive sheet builder is enabled (`VRS_SHEET_BUILDER=1`).
pub(crate) fn sheet_builder_enabled() -> bool {
    std::env::var("VRS_SHEET_BUILDER").ok().as_deref() == Some("1")
}

/// SGH-Q63: strict latest-behavior observation mode for the critical-aware sheet builder.
///
/// When enabled, the solver should show the newest role-aware builder path honestly instead of
/// silently dropping back to older seed/bootstrap behavior that masks it in the final layout.
pub(crate) fn sheet_builder_strict_latest_enabled() -> bool {
    std::env::var("VRS_SHEET_BUILDER_STRICT_LATEST")
        .ok()
        .as_deref()
        == Some("1")
}

/// SGH-Q69: forced latest-path solve mode.
pub(crate) fn sheet_builder_forced_latest_enabled() -> bool {
    std::env::var("VRS_SHEET_BUILDER_FORCE_LATEST")
        .ok()
        .as_deref()
        == Some("1")
}

fn sheet_builder_latest_lock_enabled() -> bool {
    sheet_builder_strict_latest_enabled() || sheet_builder_forced_latest_enabled()
}

/// SGH-Q73: opt-in big-part pitch-minimizing row seed. Default OFF: on the Full276 LV8 benchmark the
/// seed is valid and non-orthogonal at seed time (2 per sheet @ ~81.5°), but the unpinned exploration
/// SA resolves the overlaps with the surrounding fillers by moving the big parts back toward 90° and
/// ejecting one — regressing the total placed-count (252 vs the Q72 262). Kept as a tested building
/// block; turning it into a net win needs item-pinning / obstacle-aware filling (see report).
fn big_row_seed_enabled() -> bool {
    std::env::var("VRS_BIG_ROW_SEED").ok().as_deref() == Some("1")
}

#[allow(clippy::too_many_arguments)]
fn forced_latest_completion_sweep(
    layout: &mut SparrowLayout,
    placed: &mut [bool],
    order: impl Iterator<Item = usize>,
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    weights: &DensityWeights,
    rng: &mut DeterministicRng,
    started: &Instant,
    deadline_s: f64,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) {
    for inst_idx in order {
        if placed[inst_idx] || started.elapsed().as_secs_f64() >= deadline_s {
            continue;
        }
        let mut best: Option<(f64, SparrowLayout)> = None;
        for sheet_idx in 0..solver_sheets.len() {
            if let Some(candidate) = direct_insert_on_sheet(
                layout,
                inst_idx,
                sheet_idx,
                instances,
                solver_sheets,
                weights,
                rng,
                diag,
                bpp,
            ) {
                let score = completion_recovery_score(
                    layout,
                    &candidate,
                    sheet_idx,
                    instances,
                    &solver_sheets[sheet_idx],
                );
                if best
                    .as_ref()
                    .is_none_or(|(best_score, _)| score > *best_score)
                {
                    best = Some((score, candidate));
                }
            }
        }
        if let Some((_, candidate)) = best {
            *layout = candidate;
            placed[inst_idx] = true;
            bpp.bpp_q69_completion_sweep_inserted += 1;
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn forced_latest_sheet_fill_recovery(
    layout: &mut SparrowLayout,
    placed: &mut [bool],
    sheet_idx: usize,
    order: &[usize],
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
    weights: &DensityWeights,
    rng: &mut DeterministicRng,
    started: &Instant,
    deadline_s: f64,
    diag: &mut SparrowDiagnostics,
    bpp: &mut BppReductionDiagnostics,
) {
    if started.elapsed().as_secs_f64() >= deadline_s {
        return;
    }
    bpp.bpp_q70_completion_fill_first_applied = true;
    let mut sweeps = 0usize;
    while sweeps < 2 && started.elapsed().as_secs_f64() < deadline_s {
        let mut progress = false;
        for &inst_idx in order {
            if placed[inst_idx] || started.elapsed().as_secs_f64() >= deadline_s {
                continue;
            }
            if let Some(candidate) = direct_insert_on_sheet(
                layout,
                inst_idx,
                sheet_idx,
                instances,
                solver_sheets,
                weights,
                rng,
                diag,
                bpp,
            ) {
                *layout = candidate;
                placed[inst_idx] = true;
                progress = true;
                bpp.bpp_q70_sheet_fill_recovery_inserted += 1;
            }
        }
        if !progress {
            break;
        }
        sweeps += 1;
    }
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
    let latest_lock = sheet_builder_latest_lock_enabled();
    let forced_latest = sheet_builder_forced_latest_enabled();
    let mut layout = SparrowLayout {
        placements: Vec::with_capacity(instances.len()),
    };
    let mut placed = vec![false; instances.len()];
    bpp.bpp_sheet_builder_applied = true;
    bpp.bpp_q69_forced_latest_mode = forced_latest;

    // SGH-Q54A: skeleton role state (opt-in VRS_SHEET_BUILDER_SKELETON). When off, never built and
    // placement is byte-identical to Q51/Q52; when on, it only records role/geometry (Q54B+ act on it).
    let skeleton_on = super::sheet_skeleton::skeleton_builder_enabled();
    let mut skeleton = super::sheet_skeleton::SheetSkeletonState::new(sheets.len());

    let hints_gate_on = super::sheet_feasibility_bpp::sheet_feasibility_hints_enabled();
    let mut critical_queue = queues.critical.clone();
    let mut sheet_target_quotas: Vec<super::sheet_feasibility_bpp::SheetTargetQuota> = Vec::new();
    let mut hints_built = false;
    if hints_gate_on {
        match build_live_sheet_feasibility_hints(problem) {
            Ok(hints) => {
                let hint_diag = super::sheet_feasibility_bpp::build_hint_diagnostics(&hints, true);
                let hinted_ids = super::sheet_feasibility_bpp::hint_aware_critical_order(&hints);
                let rank: HashMap<String, usize> = hinted_ids
                    .iter()
                    .enumerate()
                    .map(|(i, id)| (id.clone(), i))
                    .collect();
                let legacy_rank: HashMap<usize, usize> = critical_queue
                    .iter()
                    .enumerate()
                    .map(|(i, &ci)| (ci, i))
                    .collect();
                let legacy_queue = critical_queue.clone();
                critical_queue.sort_by(|a, b| {
                    let ra = rank
                        .get(&instances[*a].part_id)
                        .copied()
                        .unwrap_or(usize::MAX);
                    let rb = rank
                        .get(&instances[*b].part_id)
                        .copied()
                        .unwrap_or(usize::MAX);
                    ra.cmp(&rb).then_with(|| {
                        legacy_rank
                            .get(a)
                            .copied()
                            .unwrap_or(usize::MAX)
                            .cmp(&legacy_rank.get(b).copied().unwrap_or(usize::MAX))
                    })
                });
                sheet_target_quotas = super::sheet_feasibility_bpp::sheet_target_quotas(&hints);
                bpp.bpp_sheet_feasibility_hints_used = true;
                bpp.bpp_q61_best_partial_tracker_enabled = true;
                bpp.bpp_target_critical_distribution = hint_diag.target_critical_distribution;
                bpp.bpp_sheet_target_quota = hint_diag.sheet_target_quota;
                bpp.bpp_hint_queue_reorder_applied = critical_queue != legacy_queue;
                bpp.bpp_hint_frontier_extension_applied = hint_diag.frontier_extension_applied;
                hints_built = true;
            }
            Err(err) => {
                bpp.bpp_hint_quota_abandoned_reason = Some(format!("hint_build_failed: {err}"));
            }
        }
    }
    if hints_built && critical_queue.is_empty() && !sheet_target_quotas.is_empty() {
        bpp.bpp_hint_quota_abandoned_reason =
            Some("no_critical_queue_entries_after_priority_filter".to_string());
    }

    // SGH-Q54D sheet-close guard: on the skeleton path keep the critical phase open longer (4 vs 2)
    // so a band-insert third big part still gets attempts after the tighter interlock pair's misses,
    // instead of closing the sheet early and spilling to a new one.
    let base_critical_frontier: usize = if skeleton_on { 4 } else { 2 };

    for sheet_idx in 0..sheets.len() {
        if started.elapsed().as_secs_f64() >= deadline_s || placed.iter().all(|&p| p) {
            break;
        }
        bpp.bpp_sheets_opened += 1;
        let sheet_deadline = if forced_latest {
            forced_latest_sheet_deadline(
                started.elapsed().as_secs_f64(),
                deadline_s,
                sheets.len().saturating_sub(sheet_idx),
            )
        } else {
            deadline_s
        };
        let mut critical_here = 0usize;
        let remaining_quotas: Vec<&super::sheet_feasibility_bpp::SheetTargetQuota> =
            sheet_target_quotas
                .iter()
                .filter(|q| {
                    critical_queue
                        .iter()
                        .any(|&ci| !placed[ci] && instances[ci].part_id == q.part_id)
                })
                .collect();
        let sheet_target_total = remaining_quotas
            .iter()
            .map(|q| q.target_per_sheet)
            .max()
            .unwrap_or(0);
        let sheet_target_min_useful = remaining_quotas
            .iter()
            .map(|q| q.fallback_min_useful)
            .max()
            .unwrap_or(0);
        let critical_frontier = if hints_built {
            super::sheet_feasibility_bpp::hint_aware_frontier(
                base_critical_frontier,
                sheet_target_total,
            )
        } else {
            base_critical_frontier
        };
        if hints_built && critical_frontier > base_critical_frontier {
            bpp.bpp_hint_frontier_extension_applied = true;
        }
        let mut best_partial_tracker = hints_built.then(|| {
            bpp.bpp_q61_best_partial_tracker_enabled = true;
            super::sheet_feasibility_bpp::BestPartialTracker::new()
        });

        // ── 1. Critical admission phase (co-movable anchors) ──────────────────────────────────
        let mut consec_fail = 0usize;
        for &ci in &critical_queue {
            if placed[ci] {
                continue;
            }
            if started.elapsed().as_secs_f64() >= sheet_deadline || consec_fail >= critical_frontier
            {
                break;
            }
            let now = started.elapsed().as_secs_f64();
            let admit_deadline = (now + (sheet_deadline - now).max(1.0) * 0.5).min(sheet_deadline);
            // SGH-Q54A: classify the candidate's skeleton role BEFORE admission (from the sheet's
            // current topology + the part's Q47 profile). Decision-support only in Q54A.
            let role = skeleton_on.then(|| {
                let inputs =
                    super::sheet_skeleton::RoleInputs::from_profile(&instances[ci].shape_profile);
                super::sheet_skeleton::assign_role(&inputs, &skeleton, sheet_idx)
            });
            if super::critical_simultaneous::simultaneous_critical_enabled() && critical_here >= 1 {
                // Admitting onto a sheet that already holds critical parts runs the co-movable
                // separation, which moves ALL admitted critical parts together — a genuine
                // simultaneous group refinement (earlier group parts can and do move).
                bpp.bpp_q61_simultaneous_critical_consulted = true;
                bpp.bpp_q61_simultaneous_group_attempts += 1;
                bpp.bpp_q61_previous_group_parts_moved = true;
            }
            match try_admit_critical(
                optimizer,
                &layout,
                ci,
                sheet_idx,
                instances,
                sheets,
                started,
                admit_deadline,
                rng,
                diag,
                bpp,
                role, // SGH-Q55B: route the candidate generation by skeleton role
            ) {
                Some(new_layout) => {
                    layout = new_layout;
                    placed[ci] = true;
                    consec_fail = 0;
                    critical_here += 1;
                    bpp.bpp_critical_admitted += 1;
                    bpp.bpp_q61_best_partial_max_critical_count = bpp
                        .bpp_q61_best_partial_max_critical_count
                        .max(critical_here);
                    if let Some(tracker) = best_partial_tracker.as_mut() {
                        let before_rejects = tracker.downgrades_rejected();
                        let target_met =
                            sheet_target_total > 0 && critical_here >= sheet_target_total;
                        let became_incumbent =
                            tracker.offer(super::sheet_feasibility_bpp::CriticalIncumbent {
                                critical_count: critical_here,
                                placed_area: sheet_placed_area(&layout, instances, sheet_idx),
                                free_space_score: sheet_freespace_score(
                                    &layout,
                                    sheet_idx,
                                    instances,
                                    &sheets[sheet_idx],
                                ),
                                hint_target_met: target_met,
                                source: critical_incumbent_source(role),
                            });
                        bpp.bpp_q61_best_partial_downgrades_rejected +=
                            tracker.downgrades_rejected() - before_rejects;
                        bpp.bpp_sheet_best_partial_critical_count = bpp
                            .bpp_sheet_best_partial_critical_count
                            .max(tracker.best_critical_count());
                        if became_incumbent {
                            bpp.bpp_sheet_best_partial_source =
                                tracker.best().map(|best| best.source.clone());
                        }
                        if target_met {
                            bpp.bpp_sheet_target_quota_met = true;
                        }
                    }
                    if let Some(role) = role {
                        let bbox = critical_world_bbox(&layout, ci, instances);
                        skeleton.record_admission(sheet_idx, ci, role, bbox);
                    }
                }
                None => {
                    consec_fail += 1;
                    bpp.bpp_critical_deferred += 1;
                    // SGH-Q61 best-partial preservation: a failed critical admission NEVER removes the
                    // already-admitted criticals on this sheet — a valid 2-group is preserved when a 3rd
                    // attempt fails (the 2/3 → 1/3 regression is impossible by construction here).
                    if critical_here >= 2 {
                        bpp.bpp_q61_best_partial_downgrades_rejected += 1;
                    }
                }
            }
        }
        bpp.bpp_critical_phase_close_reason =
            Some(if started.elapsed().as_secs_f64() >= sheet_deadline {
                "deadline".to_string()
            } else if consec_fail >= critical_frontier {
                "frontier_fail_limit".to_string()
            } else if critical_queue.iter().all(|&ci| placed[ci]) {
                "critical_exhausted".to_string()
            } else {
                "sheet_phase_exhausted".to_string()
            });
        if let Some(tracker) = best_partial_tracker.as_ref() {
            bpp.bpp_sheet_best_partial_critical_count = bpp
                .bpp_sheet_best_partial_critical_count
                .max(tracker.best_critical_count());
            if bpp.bpp_sheet_best_partial_source.is_none() {
                bpp.bpp_sheet_best_partial_source = tracker.best().map(|best| best.source.clone());
            }
            if hints_built
                && sheet_target_total > 0
                && tracker.best_critical_count() < sheet_target_total
                && bpp.bpp_hint_quota_abandoned_reason.is_none()
            {
                let useful_partial = tracker.best_critical_count() >= sheet_target_min_useful;
                bpp.bpp_hint_quota_abandoned_reason = Some(format!(
                    "sheet={sheet_idx} target_quota={sheet_target_total} best_partial={} useful_partial={} close_reason={}",
                    tracker.best_critical_count(),
                    useful_partial,
                    bpp.bpp_critical_phase_close_reason
                        .clone()
                        .unwrap_or_else(|| "unknown".to_string())
                ));
            }
        }
        bpp.bpp_max_critical_per_sheet = bpp.bpp_max_critical_per_sheet.max(critical_here);

        // ── 2. Structural + 3. Filler phases (direct density insertion on this sheet) ─────────
        for &pi in queues.structural.iter().chain(queues.filler.iter()) {
            if placed[pi] {
                continue;
            }
            if started.elapsed().as_secs_f64() >= sheet_deadline {
                break;
            }
            if let Some(new_layout) = direct_insert_on_sheet(
                &layout, pi, sheet_idx, instances, sheets, &weights, rng, diag, bpp,
            ) {
                layout = new_layout;
                placed[pi] = true;
            }
        }
        let sheet_util =
            sheet_physical_utilization_ratio(&layout, instances, sheet_idx, &sheets[sheet_idx]);
        if forced_latest && sheet_util < 0.55 {
            let recovery_deadline = forced_latest_recovery_deadline(
                started.elapsed().as_secs_f64().max(sheet_deadline),
                deadline_s,
                sheets.len().saturating_sub(sheet_idx + 1),
            );
            if recovery_deadline > started.elapsed().as_secs_f64() {
                bpp.bpp_q70_underfilled_sheet_recovery_used = true;
                let filler_first = filler_first_completion_order(&queues, instances);
                forced_latest_sheet_fill_recovery(
                    &mut layout,
                    &mut placed,
                    sheet_idx,
                    &filler_first,
                    instances,
                    sheets,
                    &weights,
                    rng,
                    started,
                    recovery_deadline,
                    diag,
                    bpp,
                );
            }
        }
        if forced_latest
            && started.elapsed().as_secs_f64() >= sheet_deadline
            && sheet_deadline < deadline_s
        {
            bpp.bpp_q69_builder_sheet_slice_hits += 1;
        }
    }

    if forced_latest {
        forced_latest_completion_sweep(
            &mut layout,
            &mut placed,
            filler_first_completion_order(&queues, instances).into_iter(),
            instances,
            sheets,
            &weights,
            rng,
            started,
            deadline_s,
            diag,
            bpp,
        );
    }

    // Bootstrap any still-unplaced part (overlap allowed; the separator resolves it).
    //
    // SGH-Q63 strict latest-behavior mode deliberately DISABLES this bootstrap: the random rescue
    // seeds visually mask what the latest builder actually achieved, which makes benchmark renders
    // misleading when the task is to observe the newest builder path honestly.
    if !latest_lock {
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
                let (ax, ay) = placement_anchor_from_rect_min(
                    rmx,
                    rmy,
                    inst.part.width,
                    inst.part.height,
                    rot,
                );
                layout.placements.push(SparrowPlacement {
                    instance_idx: i,
                    sheet_index: sheet_idx,
                    x: ax,
                    y: ay,
                    rotation_deg: rot,
                });
                bpp.bpp_q69_builder_random_bootstrap_used = true;
            }
        }
    }
    if skeleton_on {
        let (a, i, b) = skeleton.role_counts();
        bpp.bpp_skeleton_anchor_count = a;
        bpp.bpp_skeleton_interlock_count = i;
        bpp.bpp_skeleton_bandinsert_count = b;
    }
    layout.placements.sort_by_key(|p| p.instance_idx);
    layout
}

/// SGH-Q54A: world-space bbox `[min_x, min_y, max_x, max_y]` of instance `ci` as currently placed in
/// `layout` (decision-support geometry for the skeleton state). Uses the same rect-min/rotated-dims
/// convention as placement; no collision semantics.
fn critical_world_bbox(layout: &SparrowLayout, ci: usize, instances: &[SPInstance]) -> [f64; 4] {
    let inst = &instances[ci];
    match layout.placements.iter().find(|p| p.instance_idx == ci) {
        Some(p) => {
            let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, p.rotation_deg);
            let (rmx, rmy) =
                rect_min_from_anchor(p.x, p.y, inst.part.width, inst.part.height, p.rotation_deg);
            [rmx, rmy, rmx + rw, rmy + rh]
        }
        None => [0.0, 0.0, 0.0, 0.0],
    }
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
            .partial_cmp(&profile_order_key(
                instances,
                layout.placements[a].instance_idx,
            ))
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
                li,
                layout,
                instances,
                solver_sheets,
                tracker,
                &sheet_sh,
                weights,
                rng,
                bpp,
            ) {
                layout.placements[li] = pl;
                tracker.shapes[li] = SparrowCollisionTracker::prepare_item(layout, instances, li);
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
            working,
            s,
            instances,
            solver_sheets,
            started,
            deadline_s,
            rng,
            &weights,
            bpp,
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
    diag: &mut SparrowDiagnostics,
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
            .partial_cmp(&profile_order_key(
                instances,
                working.placements[a].instance_idx,
            ))
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
                li,
                t,
                working,
                instances,
                solver_sheets,
                &tracker,
                &sheet_sh,
                weights,
                rng,
                true,
                true,
                true,
                diag,
                bpp,
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
    diag: &mut SparrowDiagnostics,
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
                working,
                s,
                &receiving,
                instances,
                solver_sheets,
                started,
                deadline_s,
                &weights,
                rng,
                diag,
                bpp,
                restart,
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
    locked: &HashSet<usize>,
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
            // SGH-Q74: never gravity-slide a locked (edge-anchored interlock) part off its anchor.
            if locked.contains(&working.placements[li].instance_idx) {
                continue;
            }
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
                if let Some(sh) = transform_base_to_candidate(inst.base_shape.as_ref(), ax, ay, rot)
                {
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

/// SGH-Q72: complete a (possibly incomplete) latest-path builder seed to a *full-instance* seed so
/// no part is dropped before the optimizer runs. The builder's smart critical/anchor placements are
/// kept verbatim; every instance the builder did not place is re-inserted from the native LBF /
/// bootstrap seed (deliberately allowed to overlap — the exploration separator resolves it on the
/// fixed sheets, exactly like the native seed path that reaches the higher baseline placed-count).
/// Returns the merged layout, the builder's pre-completion placement count, and how many instances
/// were re-inserted.
fn complete_seed_to_full_instance(
    built: SparrowLayout,
    problem: &SparrowProblem,
    exclude: &HashSet<usize>,
) -> (SparrowLayout, usize, usize) {
    let n = problem.instances.len();
    let builder_placed = built.placements.len();
    let mut present = vec![false; n];
    for p in &built.placements {
        if p.instance_idx < n {
            present[p.instance_idx] = true;
        }
    }
    // SGH-Q74: instances the seeder deliberately left out (e.g. big copies that do not fit) are NOT
    // re-inserted overlapping — that only churns the pinned interlock and gets the seeded big parts
    // ejected at sanitize. They become honest unplaced parts instead.
    for &ix in exclude {
        if ix < n {
            present[ix] = true;
        }
    }
    if (0..n).all(|i| present[i]) {
        return (built, builder_placed, 0);
    }
    let native = build_native_constructive_seed(problem);
    let mut merged = built;
    let mut reinserted = 0usize;
    for p in native.placements {
        if p.instance_idx < n && !present[p.instance_idx] {
            present[p.instance_idx] = true;
            merged.placements.push(p);
            reinserted += 1;
        }
    }
    merged.placements.sort_by_key(|p| p.instance_idx);
    (merged, builder_placed, reinserted)
}

/// SGH-Q73: pitch-minimizing row seed for the dominant repeated BIG critical type.
struct BigRowSeed {
    part_id: String,
    rotation_deg: f64,
    pitch_mm: f64,
    copies_per_sheet: usize,
    placements: Vec<SparrowPlacement>,
}

/// SGH-Q73: choose the orientation that packs the dominant repeated BIG part type with the smallest
/// CDE-clear translational pitch (a row with the long axis along the sheet's longer side), then seed
/// as many copies per sheet as actually fit — filling each sheet before opening the next. The
/// orientation sweep is continuous, so a non-orthogonal interlock angle wins whenever it packs the
/// concave parts tighter than the min-bbox-width 90° the builder defaults to. `solver_sheets` are the
/// margin-shrunk sheets, and `sheet_local_feasible` is the CDE truth (boundary + spacing-expanded
/// clearance), so every seeded placement is a real, valid placement.
fn repeated_big_critical_row_seed(
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
) -> Option<BigRowSeed> {
    let sheet = solver_sheets.first()?;
    let max_sheet_area = solver_sheets.iter().map(|s| s.area).fold(0.0_f64, f64::max);
    if max_sheet_area <= 0.0 {
        return None;
    }
    // Dominant big repeated type: count >= 2, piece area >= 4% of the sheet, largest area.
    let mut groups: HashMap<String, Vec<usize>> = HashMap::new();
    for (i, inst) in instances.iter().enumerate() {
        groups.entry(inst.part_id.clone()).or_default().push(i);
    }
    let mut chosen: Option<(String, f64, Vec<usize>)> = None;
    for (pid, idxs) in &groups {
        if idxs.len() < 2 {
            continue;
        }
        let area = part_polygon_area(&instances[idxs[0]].part);
        if area < 0.04 * max_sheet_area {
            continue;
        }
        if chosen.as_ref().is_none_or(|(_, a, _)| area > *a) {
            chosen = Some((pid.clone(), area, idxs.clone()));
        }
    }
    let (part_id, _area, mut idxs) = chosen?;
    idxs.sort_unstable();
    let proto_part = instances[idxs[0]].part.clone();
    // Inset off the (margin-shrunk) corner so the CDE boundary check / spacing geometry clears.
    const INSET: f64 = 2.0;
    let sx = sheet.min_x + INSET;
    let sy = sheet.min_y + INSET;
    let usable_w = (sheet.max_x - INSET) - sx;
    let usable_h = (sheet.max_y - INSET) - sy;
    if usable_w <= 0.0 || usable_h <= 0.0 {
        return None;
    }
    // Exact transformed-polygon bbox per orientation. The part's local polygon is the
    // spacing-expanded contour and does NOT start at the origin, so the corner-origin anchor helper
    // would misplace it (and fail the boundary check). Probe the CDE shape at anchor (0,0): then the
    // anchor that lands the world-bbox min at a target rect-min `(tx,ty)` is `(tx - smin_x, ty - smin_y)`.
    let probe = |theta: f64| -> Option<(f64, f64, f64, f64)> {
        let s = crate::optimizer::cde_adapter::prepare_shape_native(&proto_part, 0.0, 0.0, theta)
            .ok()?;
        Some((s.min_x, s.min_y, s.max_x - s.min_x, s.max_y - s.min_y))
    };
    // CDE feasibility of `n` copies in a row at orientation `theta`, rect-min pitch `d`, starting at
    // the inset corner (`ox`/`oy` are the probed world-bbox min offsets for this orientation).
    let row_feasible = |theta: f64, ox: f64, oy: f64, d: f64, n: usize| -> bool {
        let local: Vec<SparrowPlacement> = (0..n)
            .map(|k| SparrowPlacement {
                instance_idx: idxs[k],
                sheet_index: 0,
                x: sx + (k as f64) * d - ox,
                y: sy - oy,
                rotation_deg: theta,
            })
            .collect();
        sheet_local_feasible(&local, instances, solver_sheets)
    };
    // Evaluate an orientation → (min clear pitch, how many copies fit in one row).
    let eval = |theta: f64| -> Option<(f64, usize)> {
        let (ox, oy, ew, eh) = probe(theta)?;
        if ew > usable_w + 1e-6 || eh > usable_h + 1e-6 {
            return None;
        }
        if !row_feasible(theta, ox, oy, 0.0, 1) {
            return None;
        }
        let max_d = usable_w - ew;
        if max_d <= 1.0 || !row_feasible(theta, ox, oy, max_d, 2) {
            return Some((ew.max(1.0), 1));
        }
        let (mut lo, mut hi) = (0.0_f64, max_d);
        for _ in 0..24 {
            let mid = 0.5 * (lo + hi);
            if row_feasible(theta, ox, oy, mid, 2) {
                hi = mid;
            } else {
                lo = mid;
            }
        }
        let pitch = hi.max(1.0);
        let count = (((usable_w - ew) / pitch).floor() as usize + 1).min(idxs.len());
        Some((pitch, count))
    };

    // Coarse sweep 0..180° (step 3°), then refine ±3° (step 0.5°). Prefer max count, then min pitch.
    let mut best: Option<(f64, f64, usize)> = None;
    let mut consider = |theta: f64, best: &mut Option<(f64, f64, usize)>| {
        if let Some((pitch, count)) = eval(theta) {
            let better = best
                .as_ref()
                .is_none_or(|(_, bp, bc)| count > *bc || (count == *bc && pitch < *bp - 1e-6));
            if better {
                *best = Some((theta, pitch, count));
            }
        }
    };
    let mut theta = 0.0_f64;
    while theta < 180.0 {
        consider(theta, &mut best);
        theta += 3.0;
    }
    let (bt0, _, _) = best?;
    let mut t = (bt0 - 3.0).max(0.0);
    let end = (bt0 + 3.0).min(179.9);
    while t <= end {
        consider(t, &mut best);
        t += 0.5;
    }
    let (bt, bp, bc) = best?;
    if bc == 0 {
        return None;
    }

    let (ox, oy, ew, _eh) = probe(bt)?;
    let mut placements: Vec<SparrowPlacement> = Vec::new();
    let mut next = 0usize;
    'outer: for (s, sh) in solver_sheets.iter().enumerate() {
        for k in 0..bc {
            if next >= idxs.len() {
                break 'outer;
            }
            let rmx = sh.min_x + INSET + (k as f64) * bp;
            if rmx + ew > sh.max_x - INSET + 1e-6 {
                break;
            }
            placements.push(SparrowPlacement {
                instance_idx: idxs[next],
                sheet_index: s,
                x: rmx - ox,
                y: sh.min_y + INSET - oy,
                rotation_deg: bt,
            });
            next += 1;
        }
    }
    if placements.is_empty() {
        return None;
    }
    Some(BigRowSeed {
        part_id,
        rotation_deg: bt,
        pitch_mm: bp,
        copies_per_sheet: bc,
        placements,
    })
}

/// SGH-Q74: opt-in edge-anchored, slide-nest interlock seed for the dominant repeated BIG critical
/// type — the reference (nestandcut) recipe. Unlike the Q73 fixed-pitch row (which forbids bbox
/// overlap and so caps at 2/sheet), this slides each next copy in until it is polygon-touching
/// (CDE-clear) against the already-placed chain, allowing bbox OVERLAP — exactly the deep crescent
/// interlock that fits 3/sheet. The seeded big parts are then PINNED (fixed obstacles) so the
/// exploration separator and gravity do not disturb them; the fillers pack around them.
fn edge_interlock_seed_enabled() -> bool {
    std::env::var("VRS_EDGE_INTERLOCK_SEED").ok().as_deref() == Some("1")
}

struct EdgeInterlockSeed {
    part_id: String,
    rotation_deg: f64,
    copies_per_sheet: usize,
    placements: Vec<SparrowPlacement>,
    locked: HashSet<usize>,
}

fn edge_anchored_interlock_big_seed(
    instances: &[SPInstance],
    solver_sheets: &[SheetShape],
) -> Option<EdgeInterlockSeed> {
    let sheet = solver_sheets.first()?;
    let max_sheet_area = solver_sheets.iter().map(|s| s.area).fold(0.0_f64, f64::max);
    if max_sheet_area <= 0.0 {
        return None;
    }
    // Dominant big repeated type: count >= 2, piece area >= 4% of the sheet, largest area.
    let mut groups: HashMap<String, Vec<usize>> = HashMap::new();
    for (i, inst) in instances.iter().enumerate() {
        groups.entry(inst.part_id.clone()).or_default().push(i);
    }
    let mut chosen: Option<(String, f64, Vec<usize>)> = None;
    for (pid, idxs) in &groups {
        if idxs.len() < 2 {
            continue;
        }
        let area = part_polygon_area(&instances[idxs[0]].part);
        if area < 0.04 * max_sheet_area {
            continue;
        }
        if chosen.as_ref().is_none_or(|(_, a, _)| area > *a) {
            chosen = Some((pid.clone(), area, idxs.clone()));
        }
    }
    let (part_id, _area, mut idxs) = chosen?;
    idxs.sort_unstable();
    let proto_part = instances[idxs[0]].part.clone();
    const INSET: f64 = 2.0;
    let sx = sheet.min_x + INSET;
    let sy = sheet.min_y + INSET;
    let usable_w = (sheet.max_x - INSET) - sx;
    let usable_h = (sheet.max_y - INSET) - sy;
    if usable_w <= 0.0 || usable_h <= 0.0 {
        return None;
    }
    // Exact transformed-polygon bbox-min offset + extent for an orientation (anchor at 0,0).
    let probe = |theta: f64| -> Option<(f64, f64, f64, f64)> {
        let s = crate::optimizer::cde_adapter::prepare_shape_native(&proto_part, 0.0, 0.0, theta)
            .ok()?;
        Some((s.min_x, s.min_y, s.max_x - s.min_x, s.max_y - s.min_y))
    };
    // Build the slide-nest chain for one sheet at base orientation `theta` (optionally alternating
    // a 180° flip). Each next copy is slid left until it is CDE-touching the chain (bbox overlap
    // allowed). Returns per-copy (rect_min_x, rotation_deg, off_x, off_y, extent_w).
    let build_chain = |theta: f64, flip: bool| -> Vec<(f64, f64, f64, f64, f64)> {
        let mut chain: Vec<(f64, f64, f64, f64, f64)> = Vec::new();
        let mut rightmost = sx;
        for k in 0..idxs.len() {
            let thetak = if flip && k % 2 == 1 {
                (theta + 180.0) % 360.0
            } else {
                theta
            };
            let Some((ox, oy, ew, eh)) = probe(thetak) else {
                break;
            };
            if eh > usable_h + 1e-6 || ew > usable_w + 1e-6 {
                break;
            }
            let start_x = if chain.is_empty() { sx } else { rightmost + 1.0 };
            if start_x + ew > sx + usable_w + 1e-6 {
                break;
            }
            let feas = |x: f64| -> bool {
                let mut locals: Vec<SparrowPlacement> = chain
                    .iter()
                    .enumerate()
                    .map(|(j, &(cx, ct, cox, coy, _))| SparrowPlacement {
                        instance_idx: idxs[j],
                        sheet_index: 0,
                        x: cx - cox,
                        y: sy - coy,
                        rotation_deg: ct,
                    })
                    .collect();
                locals.push(SparrowPlacement {
                    instance_idx: idxs[chain.len()],
                    sheet_index: 0,
                    x: x - ox,
                    y: sy - oy,
                    rotation_deg: thetak,
                });
                sheet_local_feasible(&locals, instances, solver_sheets)
            };
            if !feas(start_x) {
                break;
            }
            // Slide left to the deepest CDE-clear nest position.
            let (mut lo, mut hi) = (sx, start_x);
            if feas(lo) {
                hi = lo;
            } else {
                for _ in 0..18 {
                    let mid = 0.5 * (lo + hi);
                    if feas(mid) {
                        hi = mid;
                    } else {
                        lo = mid;
                    }
                }
            }
            let x = hi;
            if x + ew > sx + usable_w + 1e-6 {
                break;
            }
            chain.push((x, thetak, ox, oy, ew));
            rightmost = rightmost.max(x + ew);
        }
        chain
    };

    // Orientation sweep: max copies/sheet, then tightest span (smallest rightmost). Continuous, so a
    // non-orthogonal nest angle wins where it packs the crescents deepest.
    let span = |chain: &[(f64, f64, f64, f64, f64)]| -> f64 {
        chain
            .iter()
            .map(|&(x, _, _, _, ew)| x + ew)
            .fold(0.0_f64, f64::max)
    };
    let mut best: Option<Vec<(f64, f64, f64, f64, f64)>> = None;
    let mut consider = |chain: Vec<(f64, f64, f64, f64, f64)>,
                        best: &mut Option<Vec<(f64, f64, f64, f64, f64)>>| {
        if chain.is_empty() {
            return;
        }
        let better = match best {
            None => true,
            Some(b) => chain.len() > b.len() || (chain.len() == b.len() && span(&chain) < span(b) - 1e-6),
        };
        if better {
            *best = Some(chain);
        }
    };
    let mut theta = 0.0_f64;
    while theta < 180.0 {
        consider(build_chain(theta, false), &mut best);
        consider(build_chain(theta, true), &mut best);
        theta += 4.0;
    }
    // refine ±4° around the best base orientation
    if let Some(b) = best.clone() {
        let bt = b.first().map(|&(_, t, _, _, _)| t % 180.0).unwrap_or(0.0);
        let mut t = (bt - 4.0).max(0.0);
        let end = (bt + 4.0).min(179.9);
        while t <= end {
            consider(build_chain(t, false), &mut best);
            consider(build_chain(t, true), &mut best);
            t += 1.0;
        }
    }
    let chain = best?;
    // θ* = the orientation the slide-nest found best (where the crescents interlock deepest).
    let rotation_deg = chain.first().map(|&(_, t, _, _, _)| t).unwrap_or(0.0);

    // Unified per-sheet seats: (rect_min_x, rect_min_y, rotation, off_x, off_y).
    // Reference recipe: anchor the first two big parts to OPPOSITE edges (left-flush + right-flush) at
    // θ*, leaving a middle channel; Phase B then nests the 3rd into the middle. If the right-edge
    // anchor is not CDE-clear, fall back to the Phase-A left-nest chain (≥2 deep-nested at one side).
    let chain_seats: Vec<(f64, f64, f64, f64, f64)> = chain
        .iter()
        .map(|&(rmx, t, ox, oy, _ew)| (rmx, sy, t, ox, oy))
        .collect();
    let mut seats: Vec<(f64, f64, f64, f64, f64)> = Vec::new();
    if let Some((ox, oy, ew, _eh)) = probe(rotation_deg) {
        seats.push((sx, sy, rotation_deg, ox, oy)); // #1 left-flush
        for &t2 in &[rotation_deg, (rotation_deg + 180.0) % 360.0] {
            let Some((ox2, oy2, ew2, _)) = probe(t2) else {
                continue;
            };
            let rmx2 = sx + usable_w - ew2;
            if rmx2 - sx <= ew * 0.25 {
                continue; // not enough separation from #1 to leave a middle channel
            }
            let locals = vec![
                SparrowPlacement {
                    instance_idx: idxs[0],
                    sheet_index: 0,
                    x: sx - ox,
                    y: sy - oy,
                    rotation_deg,
                },
                SparrowPlacement {
                    instance_idx: idxs[1],
                    sheet_index: 0,
                    x: rmx2 - ox2,
                    y: sy - oy2,
                    rotation_deg: t2,
                },
            ];
            if sheet_local_feasible(&locals, instances, solver_sheets) {
                seats.push((rmx2, sy, t2, ox2, oy2)); // #2 right-flush
                break;
            }
        }
    }
    // Keep whichever Phase-A arrangement seats more big parts (edge-anchored pair vs left-nest chain).
    if seats.len() < chain_seats.len() {
        seats = chain_seats;
    }

    // SGH-Q74 Phase B: try to nest ADDITIONAL copies (the reference's 3rd crescent — anchored toward
    // the OPPOSITE edge / staggered in y) via a bounded 2D scan against the chosen seats. Allows bbox
    // overlap; the CDE decides. Runs once on the chosen orientation (cheap), not inside the θ sweep.
    {
        let base = rotation_deg;
        while seats.len() < idxs.len() {
            let mut placed_one = false;
            'scan: for &thetak in &[base, (base + 180.0) % 360.0] {
                let Some((ox, oy, ew, eh)) = probe(thetak) else {
                    continue;
                };
                if ew > usable_w + 1e-6 || eh > usable_h + 1e-6 {
                    continue;
                }
                let (nx, ny) = (28usize, 28usize);
                for iy in 0..=ny {
                    let rmy = sy + (usable_h - eh) * (iy as f64 / ny as f64);
                    for ix in 0..=nx {
                        // scan right→left so the new copy prefers the opposite (far) edge first
                        let rmx = sx + (usable_w - ew) * (1.0 - ix as f64 / nx as f64);
                        let mut locals: Vec<SparrowPlacement> = seats
                            .iter()
                            .enumerate()
                            .map(|(j, &(cx, cy, ct, cox, coy))| SparrowPlacement {
                                instance_idx: idxs[j],
                                sheet_index: 0,
                                x: cx - cox,
                                y: cy - coy,
                                rotation_deg: ct,
                            })
                            .collect();
                        locals.push(SparrowPlacement {
                            instance_idx: idxs[seats.len()],
                            sheet_index: 0,
                            x: rmx - ox,
                            y: rmy - oy,
                            rotation_deg: thetak,
                        });
                        if sheet_local_feasible(&locals, instances, solver_sheets) {
                            seats.push((rmx, rmy, thetak, ox, oy));
                            placed_one = true;
                            break 'scan;
                        }
                    }
                }
            }
            if !placed_one {
                break;
            }
        }
    }
    let copies_per_sheet = seats.len();

    // Distribute across sheets, filling each before opening the next (coords identical per stock).
    let mut placements: Vec<SparrowPlacement> = Vec::new();
    let mut locked: HashSet<usize> = HashSet::new();
    let mut next = 0usize;
    'outer: for (s, _sh) in solver_sheets.iter().enumerate() {
        for &(rmx, rmy, thetak, ox, oy) in &seats {
            if next >= idxs.len() {
                break 'outer;
            }
            let ix = idxs[next];
            placements.push(SparrowPlacement {
                instance_idx: ix,
                sheet_index: s,
                x: rmx - ox,
                y: rmy - oy,
                rotation_deg: thetak,
            });
            locked.insert(ix);
            next += 1;
        }
    }
    if placements.is_empty() {
        return None;
    }
    Some(EdgeInterlockSeed {
        part_id,
        rotation_deg,
        copies_per_sheet,
        placements,
        locked,
    })
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
        Err(e) => {
            return error_result(
                parts,
                extra_pre_unplaced,
                total_instances,
                &started,
                total_budget,
                format!("STOCK_BUILD_ERROR: {e}"),
            )
        }
    };
    let n = original_sheets.len();
    let solver_sheets: Vec<SheetShape> = match &config.solver_sheets_override {
        Some(ov) if ov.len() == n => ov.clone(),
        _ => original_sheets.clone(),
    };
    let all_sheets_with_orig: Vec<(SheetShape, usize)> = original_sheets
        .iter()
        .cloned()
        .enumerate()
        .map(|(i, s)| (s, i))
        .collect();

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
        Err(e) => {
            return error_result(
                parts,
                extra_pre_unplaced,
                total_instances,
                &started,
                total_budget,
                format!("PROBLEM_BUILD_ERROR: {e}"),
            )
        }
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
    let reduction_deadline =
        (total_budget * (1.0 - density_frac) - guard).max(guard.min(total_budget * 0.5));
    let construct_deadline = (total_budget * 0.25)
        .clamp(2.0, 180.0)
        .min((total_budget - guard).max(1.0));
    // SGH-Q51: critical-aware constructive sheet builder (opt-in). The builder seed is used ONLY
    // when it is complete and fully feasible (every part placed, collision-free); otherwise it
    // falls back to the LBF seed — so the builder can never regress the result. This banks the
    // proven cases (e.g. 3 big curved parts on one sheet) without risking partial output where the
    // admission is not yet strong enough (tight spacing).
    // SGH-Q74: instance indices of the edge-anchored interlock big criticals to pin (fixed obstacles)
    // through the exploration separator and the gravity compaction. Empty unless the Q74 seeder runs.
    let mut q74_locked: HashSet<usize> = HashSet::new();
    let seed = if sheet_builder_enabled() {
        let strict_latest = sheet_builder_strict_latest_enabled();
        let forced_latest = sheet_builder_forced_latest_enabled();
        let latest_lock = strict_latest || forced_latest;
        // Snapshot the RNG so a fallback restores the exact pre-builder stream — the fallback path
        // is then identical (deterministically) to the builder-off path.
        let rng_snapshot = rng.clone();
        // Cap the builder's wall time to a small budget fraction so a fallback still leaves the
        // BPP reduction enough time at ANY total budget (no time-starvation regression, even at
        // tight budgets). The spacing-0 win completes well within this; tight-spacing failures fall
        // back cheaply.
        let builder_deadline = if latest_lock {
            // SGH-Q63: in strict latest mode we want to observe the builder itself, not a tiny
            // builder sample that instantly hands control back to the older seed path.
            construct_deadline
        } else if super::sheet_skeleton::skeleton_builder_enabled() {
            // SGH-Q67/Q61 follow-up: once the role-aware skeleton path is enabled, the production
            // builder must get enough of the constructive window to actually reach the interlock /
            // simultaneous critical attempts before the older seed path takes over. Keep the
            // fallback semantics, but stop time-capping the newest admission path so aggressively
            // that its diagnostics and authority disappear in practice.
            construct_deadline
        } else {
            let builder_cap = (total_budget * 0.12).clamp(4.0, 20.0);
            (started.elapsed().as_secs_f64() + builder_cap).min(construct_deadline)
        };
        let built = build_critical_aware_seed(
            &problem,
            &optimizer,
            &started,
            builder_deadline,
            &mut rng,
            &mut diag,
            &mut bpp,
        );
        if latest_lock {
            bpp.bpp_q69_seed_source = Some(if forced_latest {
                "builder_forced_latest".to_string()
            } else {
                "builder_strict_latest".to_string()
            });
            // SGH-Q73: replace the dominant repeated BIG critical type's placements with a
            // pitch-minimizing row seed — distributed to FILL a sheet before opening the next, at the
            // tightest (often non-orthogonal) CDE-clear orientation — so the big parts no longer sit
            // one-per-sheet at the min-bbox-width 90° default. The remaining big copies (if more than
            // fit) and all other parts are restored by the Q72 no-drop completion below.
            let mut built = built;
            let mut q74_exclude: HashSet<usize> = HashSet::new();
            // SGH-Q74: edge-anchored slide-nest interlock seed (the reference recipe). Replaces the
            // dominant big type's placements with a deep-interlock chain (bbox overlap allowed), and
            // PINS those placements (q74_locked) so the exploration separator + gravity treat them as
            // fixed obstacles while the fillers pack around them. Preferred over the Q73 row seed.
            if edge_interlock_seed_enabled() {
                if let Some(es) = edge_anchored_interlock_big_seed(&instances, &solver_sheets) {
                    built
                        .placements
                        .retain(|p| instances[p.instance_idx].part_id != es.part_id);
                    built.placements.extend(es.placements.iter().cloned());
                    // Big copies that did not fit the interlock are left UNPLACED (not re-inserted
                    // overlapping) so they cannot churn / eject the pinned seed.
                    for (i, inst) in instances.iter().enumerate() {
                        if inst.part_id == es.part_id && !es.locked.contains(&i) {
                            q74_exclude.insert(i);
                        }
                    }
                    q74_locked = es.locked.clone();
                    bpp.bpp_q74_edge_interlock_seed_used = true;
                    bpp.bpp_q74_edge_interlock_part_id = Some(es.part_id.clone());
                    bpp.bpp_q74_edge_interlock_rotation_deg = Some(es.rotation_deg);
                    bpp.bpp_q74_edge_interlock_copies_per_sheet = es.copies_per_sheet;
                    bpp.bpp_q74_edge_interlock_seeded_count = es.placements.len();
                    bpp.bpp_q74_edge_interlock_locked_count = es.locked.len();
                }
            } else if big_row_seed_enabled() {
                if let Some(row) = repeated_big_critical_row_seed(&instances, &solver_sheets) {
                    built
                        .placements
                        .retain(|p| instances[p.instance_idx].part_id != row.part_id);
                    built.placements.extend(row.placements.iter().cloned());
                    bpp.bpp_q73_big_row_seed_used = true;
                    bpp.bpp_q73_big_row_part_id = Some(row.part_id.clone());
                    bpp.bpp_q73_big_row_rotation_deg = Some(row.rotation_deg);
                    bpp.bpp_q73_big_row_pitch_mm = Some(row.pitch_mm);
                    bpp.bpp_q73_big_row_copies_per_sheet = row.copies_per_sheet;
                    bpp.bpp_q73_big_row_seeded_count = row.placements.len();
                }
            }
            // SGH-Q72: no-drop completion. The builder's smart critical/anchor placements are kept,
            // but every instance it did not place is retained in the seed (native LBF/bootstrap)
            // so the real exploration SA + redistribute/reduction pipeline can pack ALL parts on the
            // fixed sheets — instead of the builder silently dropping parts before the optimizer.
            let (full_seed, builder_placed, reinserted) =
                complete_seed_to_full_instance(built, &problem, &q74_exclude);
            bpp.bpp_q72_no_drop_seed_used = true;
            bpp.bpp_q72_seed_builder_placed_before_completion = builder_placed;
            bpp.bpp_q72_global_repack_reinserted_count = reinserted;
            bpp.bpp_q72_seed_instance_count_before_pipeline = full_seed.placements.len();
            full_seed
        } else if layout_is_full_feasible(&built, &instances, &solver_sheets) {
            bpp.bpp_q69_seed_source = Some("builder_complete".to_string());
            built
        } else {
            rng = rng_snapshot;
            bpp.bpp_q69_native_seed_fallback_used = true;
            bpp.bpp_q69_seed_source = Some("native_constructive_fallback".to_string());
            build_native_constructive_seed(&problem)
        }
    } else {
        bpp.bpp_q69_seed_source = Some("native_constructive".to_string());
        build_native_constructive_seed(&problem)
    };
    let mut working = if layout_is_full_feasible(&seed, &instances, &solver_sheets) {
        seed
    } else {
        // SGH-Q72: in latest-lock mode the seed retains ALL instances (no-drop), so the exploration
        // separator must get a real budget to actually pack them on the fixed sheets — not just the
        // leftover construction window. Otherwise (with the construction-full reduction loop skipped
        // for a partial seed) most of the time budget goes unused and the overlapping re-inserted
        // parts get ejected for lack of separation time. Reserve the same window the reduction loop
        // would have used; compress/density/gravity still run on the remaining tail.
        let subsolve_deadline = if sheet_builder_latest_lock_enabled() {
            reduction_deadline.max(construct_deadline)
        } else {
            construct_deadline
        };
        let (_cf, solved) = run_subsolve(
            &optimizer,
            seed,
            &instances,
            &solver_sheets,
            &started,
            subsolve_deadline,
            &mut rng,
            &mut diag,
            &q74_locked,
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
            let candidate = match select_candidate_sheet(
                &working,
                &instances,
                &solver_sheets,
                &used,
                &failed,
            ) {
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
                    .partial_cmp(&profile_order_key(
                        &instances,
                        working.placements[a].instance_idx,
                    ))
                    .unwrap_or(std::cmp::Ordering::Equal)
            });
            bpp.bpp_displaced_items_total += displaced.len();

            let mut trial = working.clone();
            redistribute_displaced(
                &optimizer,
                &mut trial,
                &displaced,
                &receiving,
                &instances,
                &solver_sheets,
                &started,
                &mut rng,
                &mut diag,
                &mut bpp,
            );

            // affected-sheet-only separation
            let remaining = (reduction_deadline - started.elapsed().as_secs_f64()).max(1.0);
            let attempt_deadline = started.elapsed().as_secs_f64() + (remaining * 0.9).max(1.0);
            let (mut feasible, mut candidate_layout) = separate_affected_sheets(
                &optimizer,
                &trial,
                &receiving,
                &instances,
                &solver_sheets,
                &started,
                attempt_deadline,
                &mut rng,
                &mut diag,
            );
            bpp.bpp_separator_calls += 1;

            // explicit transfer/swap repair on residual collisions
            if !feasible {
                let rep_deadline = started.elapsed().as_secs_f64()
                    + ((reduction_deadline - started.elapsed().as_secs_f64()).max(1.0) * 0.5);
                feasible = resolve_by_transfers(
                    &optimizer,
                    &mut candidate_layout,
                    &receiving,
                    &instances,
                    &solver_sheets,
                    &started,
                    rep_deadline,
                    &mut rng,
                    &mut diag,
                    &mut bpp,
                );
            }

            if feasible && layout_is_full_feasible(&candidate_layout, &instances, &solver_sheets) {
                // compact the receiving sheets, accept incumbent
                for &s in &receiving {
                    compact_sheet(
                        &optimizer,
                        &mut candidate_layout,
                        s,
                        &instances,
                        &solver_sheets,
                        &started,
                        &mut rng,
                        &mut diag,
                        &mut bpp,
                    );
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
                perturb_swap_between_sheets(
                    &mut working,
                    &used,
                    &instances,
                    &solver_sheets,
                    &mut rng,
                    &mut bpp,
                );
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
        &optimizer,
        &mut working,
        &instances,
        &solver_sheets,
        &started,
        compress_deadline,
        &mut rng,
        &mut diag,
        &mut bpp,
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
        &mut working,
        &instances,
        &solver_sheets,
        &started,
        density_compact_deadline,
        &mut rng,
        &mut bpp,
    );
    bpp.bpp_density_time_ms =
        (started.elapsed().as_secs_f64() * 1000.0 - bpp.bpp_reduction_time_ms).max(0.0);

    // SGH-Q50: density-guided LNS sheet-drop — try to eliminate one more sheet via coordinated
    // multi-part ruin-recreate (opt-in VRS_BPP_LNS, default off). Uses the remaining reserved budget.
    lns_sheet_drop(
        &mut working,
        &instances,
        &solver_sheets,
        &started,
        density_deadline,
        &mut rng,
        &mut diag,
        &mut bpp,
    );

    // SGH-Q46 M2: gravity / bottom-left compaction post-pass (density + edge alignment).
    gravity_compact_layout(&mut working, &instances, &solver_sheets, &q74_locked, &mut bpp);

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
    let final_tracker =
        SparrowCollisionTracker::final_validation_tracker(&working, &instances, &solver_sheets);
    let (placements, unplaced, final_pairs, boundary_violations): (
        Vec<Placement>,
        Vec<Unplaced>,
        usize,
        usize,
    ) = if final_full {
        (project(&working, &instances), pre_unplaced.clone(), 0, 0)
    } else {
        // sanitize to a collision-free partial
        let raw = project(&working, &instances);
        let (kept, mut newly) = sanitize_partial(
            &working,
            &instances,
            &solver_sheets,
            &raw,
            REASON_BPP_STOCK_EXHAUSTED,
            &q74_locked,
        );
        let mut un = pre_unplaced.clone();
        un.append(&mut newly);
        let mut already_unplaced: HashSet<String> =
            un.iter().map(|u| u.instance_id.clone()).collect();
        for inst in &instances {
            let kept_present = kept.iter().any(|p| p.instance_id == inst.instance_id);
            if !kept_present && !already_unplaced.contains(&inst.instance_id) {
                already_unplaced.insert(inst.instance_id.clone());
                un.push(Unplaced {
                    instance_id: inst.instance_id.clone(),
                    part_id: inst.part_id.clone(),
                    reason: REASON_BPP_STOCK_EXHAUSTED.to_string(),
                });
            }
        }
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
    use crate::optimizer::sparrow::sheet_skeleton::SkeletonRole;
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
        let orient = std::rc::Rc::new(OrientationCatalog::placeholder(&part.id));
        let analysis = std::rc::Rc::new(PartAnalysis::placeholder(&part.id, &prof));
        SPInstance {
            idx,
            instance_id: format!("{}#{idx}", part.id),
            part_id: part.id.clone(),
            part,
            allowed_rotations_deg: vec![0.0],
            continuous_rotation: false,
            base_shape: base,
            shape_profile: prof,
            orientation_catalog: orient,
            part_analysis: analysis,
        }
    }

    #[test]
    fn density_rotation_candidates_refines_continuous_parts() {
        // Production-faithful: a continuous part carries `continuous_rotation=true` and an EMPTY
        // `allowed_rotations_deg`. The helper must still refine rotation (fine offsets + a global
        // sweep that includes the 90↔270 flip) — NOT degenerate to `[cur_rot]` (the old bug that
        // froze continuous parts at their seed orientation).
        let part = self::poly_part(
            "sq",
            20.0,
            20.0,
            serde_json::json!([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]),
        );
        let mut cont = make_instance(0, part.clone());
        cont.continuous_rotation = true;
        cont.allowed_rotations_deg = vec![]; // empty, as in production for continuous parts

        let cands = density_rotation_candidates(&cont, 90.0);
        assert!(
            cands.len() > 8,
            "continuous part must explore many rotations, got {}",
            cands.len()
        );
        assert!(
            cands.contains(&90.5),
            "fine local refinement around cur_rot is missing"
        );
        assert!(
            cands.contains(&89.5),
            "fine local refinement (negative offset) is missing"
        );
        assert!(
            cands.iter().any(|&r| (r - 270.0).abs() < 1e-9),
            "the 90↔270 flip must be reachable"
        );

        // A discrete part keeps the bounded allowed-set subsample (NO continuous offsets).
        let mut disc = make_instance(1, part);
        disc.continuous_rotation = false;
        disc.allowed_rotations_deg = vec![0.0, 90.0, 180.0, 270.0];
        let dcands = density_rotation_candidates(&disc, 0.0);
        assert!(
            !dcands.contains(&0.5),
            "discrete part must NOT get continuous offsets"
        );
        assert!(dcands.contains(&0.0));
    }

    #[test]
    fn density_insert_part_finds_interlock_on_target_sheet() {
        // U with a concave mouth (bbox 100×100) + a 20×20 square to insert.
        let u = poly_part(
            "U",
            100.0,
            100.0,
            serde_json::json!([
                [0.0, 0.0],
                [100.0, 0.0],
                [100.0, 100.0],
                [70.0, 100.0],
                [70.0, 30.0],
                [30.0, 30.0],
                [30.0, 100.0],
                [0.0, 100.0]
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
        let u0 =
            transform_base_to_candidate(instances[0].base_shape.as_ref(), 0.0, 0.0, 0.0).unwrap();
        let (uax, uay) = (40.0 - u0.min_x, 40.0 - u0.min_y);
        let mut layout = SparrowLayout {
            placements: vec![
                SparrowPlacement {
                    instance_idx: 0,
                    sheet_index: 0,
                    x: uax,
                    y: uay,
                    rotation_deg: 0.0,
                },
                SparrowPlacement {
                    instance_idx: 1,
                    sheet_index: 0,
                    x: 10.0,
                    y: 10.0,
                    rotation_deg: 0.0,
                },
            ],
        };
        // Build the tracker, then ruin the square (its shape becomes None ⇒ excluded as a neighbour).
        let mut tracker = SparrowCollisionTracker::build(&layout, &instances, &sheets);
        tracker.shapes[1] = None;
        layout.placements[1].sheet_index = 0; // stays addressable; tracker None excludes it

        let sheet_sh = std::rc::Rc::new(prepare_shape_from_sheet(&sheets[0]).expect("sheet shape"));
        let weights = DensityWeights::default();
        let mut rng = DeterministicRng::new(7);
        let mut diag = SparrowDiagnostics::default();
        let mut bpp = BppReductionDiagnostics::default();
        let pl = density_insert_part(
            1, 0, &layout, &instances, &sheets, &tracker, &sheet_sh, &weights, &mut rng, true,
            true, true, &mut diag, &mut bpp,
        )
        .expect("square must fit on the target sheet");
        assert_eq!(pl.sheet_index, 0);

        // The chosen placement should interlock with the U (bbox-overlap, polygon-clear): the
        // densest spot is tucked into the concave mouth.
        let placed = transform_base_to_candidate(
            instances[1].base_shape.as_ref(),
            pl.x,
            pl.y,
            pl.rotation_deg,
        )
        .unwrap();
        let u_shape =
            transform_base_to_candidate(instances[0].base_shape.as_ref(), uax, uay, 0.0).unwrap();
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
        let a0 =
            transform_base_to_candidate(instances[0].base_shape.as_ref(), 0.0, 0.0, 0.0).unwrap();
        let b0 =
            transform_base_to_candidate(instances[1].base_shape.as_ref(), 0.0, 0.0, 0.0).unwrap();
        let mut working = SparrowLayout {
            placements: vec![
                SparrowPlacement {
                    instance_idx: 0,
                    sheet_index: 0,
                    x: 20.0 - a0.min_x,
                    y: 20.0 - a0.min_y,
                    rotation_deg: 0.0,
                },
                SparrowPlacement {
                    instance_idx: 1,
                    sheet_index: 1,
                    x: 20.0 - b0.min_x,
                    y: 20.0 - b0.min_y,
                    rotation_deg: 0.0,
                },
            ],
        };
        let weights = DensityWeights::default();
        let mut rng = DeterministicRng::new(3);
        let mut diag = SparrowDiagnostics::default();
        let mut bpp = BppReductionDiagnostics::default();
        let started = std::time::Instant::now();
        let dropped = try_drop_sheet(
            &mut working,
            1,
            &[0],
            &instances,
            &sheets,
            &started,
            1e9,
            &weights,
            &mut rng,
            &mut diag,
            &mut bpp,
            0,
        );
        assert!(dropped, "B must be re-homed onto sheet 0, emptying sheet 1");
        assert!(
            working.placements.iter().all(|p| p.sheet_index != 1),
            "no part should remain on the dropped sheet 1"
        );
        assert!(layout_is_full_feasible(&working, &instances, &sheets));
    }

    #[test]
    fn density_biased_separate_resolves_overlap_into_interlock() {
        // SGH-Q52: a U with a concave mouth fills a tight sheet; a square seeded OVERLAPPING the
        // U's floor must be resolved by the density-biased separator into the U's mouth (the only
        // clear space) — i.e. feasible AND bbox-overlapping the U (interlock), not spread.
        let u = poly_part(
            "U",
            100.0,
            100.0,
            serde_json::json!([
                [0.0, 0.0],
                [100.0, 0.0],
                [100.0, 100.0],
                [70.0, 100.0],
                [70.0, 30.0],
                [30.0, 30.0],
                [30.0, 100.0],
                [0.0, 100.0]
            ]),
        );
        let sq = poly_part(
            "SQ",
            20.0,
            20.0,
            serde_json::json!([[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]),
        );
        let instances = vec![make_instance(0, u), make_instance(1, sq)];
        // Sheet 110×110 with the U placed at (5,5)-(105,105): the 5 mm margin around the U is too
        // narrow for the 20×20 square, so the only place it fits is the U's mouth ⇒ it can only be
        // admitted interlocked. (The U itself stays off the sheet boundary, so it is feasible.)
        let sheets = expand_sheets(&[Stock {
            id: "S".into(),
            quantity: 1,
            width: Some(110.0),
            height: Some(110.0),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }])
        .expect("sheets");
        let u0 =
            transform_base_to_candidate(instances[0].base_shape.as_ref(), 0.0, 0.0, 0.0).unwrap();
        let (uax, uay) = (5.0 - u0.min_x, 5.0 - u0.min_y);
        let sq0 =
            transform_base_to_candidate(instances[1].base_shape.as_ref(), 0.0, 0.0, 0.0).unwrap();
        let (sax, say) = (45.0 - sq0.min_x, 10.0 - sq0.min_y); // floor region ⇒ overlaps the U
        let layout = SparrowLayout {
            placements: vec![
                SparrowPlacement {
                    instance_idx: 0,
                    sheet_index: 0,
                    x: uax,
                    y: uay,
                    rotation_deg: 0.0,
                },
                SparrowPlacement {
                    instance_idx: 1,
                    sheet_index: 0,
                    x: sax,
                    y: say,
                    rotation_deg: 0.0,
                },
            ],
        };
        let mut rng = DeterministicRng::new(11);
        let started = std::time::Instant::now();
        let (feasible, remapped) = density_biased_separate(
            &layout, 0, &instances, &sheets, 3.0, &mut rng, &started, 10.0,
        );
        assert!(
            feasible,
            "the density-biased separator must resolve the overlap to feasible"
        );
        let sq_pl = remapped
            .iter()
            .find(|p| p.instance_idx == 1)
            .expect("square placement");
        let sq_shape = transform_base_to_candidate(
            instances[1].base_shape.as_ref(),
            sq_pl.x,
            sq_pl.y,
            sq_pl.rotation_deg,
        )
        .unwrap();
        let u_shape =
            transform_base_to_candidate(instances[0].base_shape.as_ref(), uax, uay, 0.0).unwrap();
        assert!(
            super::super::density::bbox_overlaps(&sq_shape, &u_shape),
            "the square should resolve INTO the U's mouth (interlock), not spread"
        );
    }

    #[test]
    fn role_aware_path_disables_generic_direct_for_known_roles() {
        assert!(role_aware_path_should_skip_generic_direct(
            true,
            Some(SkeletonRole::Anchor)
        ));
        assert!(role_aware_path_should_skip_generic_direct(
            true,
            Some(SkeletonRole::Interlock)
        ));
        assert!(role_aware_path_should_skip_generic_direct(
            true,
            Some(SkeletonRole::BandInsert)
        ));
        assert!(!role_aware_path_should_skip_generic_direct(true, None));
        assert!(!role_aware_path_should_skip_generic_direct(
            false,
            Some(SkeletonRole::Anchor)
        ));
    }

    #[test]
    fn anchor_catalog_wins_ties_and_better_scores() {
        assert_eq!(
            choose_anchor_authority_winner(Some(10.0), Some(10.0)),
            AnchorAuthorityWinner::Catalog
        );
        assert_eq!(
            choose_anchor_authority_winner(Some(10.0), Some(10.5)),
            AnchorAuthorityWinner::Catalog
        );
        assert_eq!(
            choose_anchor_authority_winner(None, Some(4.0)),
            AnchorAuthorityWinner::Catalog
        );
    }

    #[test]
    fn anchor_feature_kept_when_catalog_score_is_worse() {
        assert_eq!(
            choose_anchor_authority_winner(Some(10.0), Some(9.5)),
            AnchorAuthorityWinner::Feature
        );
        assert_eq!(
            choose_anchor_authority_winner(Some(10.0), None),
            AnchorAuthorityWinner::Feature
        );
        assert_eq!(
            choose_anchor_authority_winner(None, None),
            AnchorAuthorityWinner::None
        );
    }

    #[test]
    fn forced_latest_catalog_prefers_corner_without_material_center_gain() {
        let corner = AnchorCatalogChoice {
            score: 1_000_000.0,
            layout: SparrowLayout { placements: vec![] },
            source: "catalog",
            secondary: "left-top",
            target_edge: "left",
            seed_rotation_deg: 0.0,
        };
        let center = AnchorCatalogChoice {
            score: 1_050_000.0,
            layout: SparrowLayout { placements: vec![] },
            source: "catalog",
            secondary: "left-center",
            target_edge: "left",
            seed_rotation_deg: 0.0,
        };
        let mut bpp = BppReductionDiagnostics::default();
        let chosen =
            choose_anchor_catalog_candidate(true, false, Some(corner), Some(center), &mut bpp)
                .unwrap();
        assert_eq!(chosen.secondary, "left-top");
        assert!(bpp.bpp_q70_anchor_center_blocked_by_policy);
        assert!(!bpp.bpp_q70_anchor_center_override_used);
    }

    #[test]
    fn forced_latest_catalog_allows_center_when_materially_better() {
        let corner = AnchorCatalogChoice {
            score: 1_000_000.0,
            layout: SparrowLayout { placements: vec![] },
            source: "catalog",
            secondary: "left-top",
            target_edge: "left",
            seed_rotation_deg: 0.0,
        };
        let center = AnchorCatalogChoice {
            score: 1_300_000.0,
            layout: SparrowLayout { placements: vec![] },
            source: "catalog",
            secondary: "left-center",
            target_edge: "left",
            seed_rotation_deg: 0.0,
        };
        let mut bpp = BppReductionDiagnostics::default();
        let chosen =
            choose_anchor_catalog_candidate(true, false, Some(corner), Some(center), &mut bpp)
                .unwrap();
        assert_eq!(chosen.secondary, "left-center");
        assert!(bpp.bpp_q70_anchor_center_override_used);
        assert!(!bpp.bpp_q70_anchor_center_blocked_by_policy);
    }

    #[test]
    fn strict_edge_lock_blocks_center_even_without_corner_gain_check() {
        let corner = AnchorCatalogChoice {
            score: 1_000_000.0,
            layout: SparrowLayout { placements: vec![] },
            source: "catalog",
            secondary: "corner_high",
            target_edge: "left",
            seed_rotation_deg: 0.0,
        };
        let center = AnchorCatalogChoice {
            score: 5_000_000.0,
            layout: SparrowLayout { placements: vec![] },
            source: "catalog",
            secondary: "center",
            target_edge: "left",
            seed_rotation_deg: 0.0,
        };
        let mut bpp = BppReductionDiagnostics::default();
        let chosen =
            choose_anchor_catalog_candidate(true, true, Some(corner), Some(center), &mut bpp)
                .unwrap();
        assert_eq!(chosen.secondary, "corner_high");
        assert!(bpp.bpp_q70_anchor_center_blocked_by_policy);
        assert!(!bpp.bpp_q70_anchor_center_override_used);
    }

    #[test]
    fn strict_edge_lock_rejects_center_only_catalog_path() {
        let center = AnchorCatalogChoice {
            score: 5_000_000.0,
            layout: SparrowLayout { placements: vec![] },
            source: "catalog",
            secondary: "center",
            target_edge: "left",
            seed_rotation_deg: 0.0,
        };
        let mut bpp = BppReductionDiagnostics::default();
        let chosen = choose_anchor_catalog_candidate(true, true, None, Some(center), &mut bpp);
        assert!(chosen.is_none());
        assert!(bpp.bpp_q70_anchor_center_only_path);
        assert!(bpp.bpp_q70_anchor_center_blocked_by_policy);
    }

    #[test]
    fn forced_latest_sheet_deadline_reserves_budget_for_remaining_sheets() {
        let d = forced_latest_sheet_deadline(0.0, 120.0, 2);
        assert!((d - 60.0).abs() < 1e-9);
        let d = forced_latest_sheet_deadline(30.0, 120.0, 3);
        assert!((d - 60.0).abs() < 1e-9);
        let d = forced_latest_sheet_deadline(95.0, 120.0, 1);
        assert!((d - 120.0).abs() < 1e-9);
    }
}

#[cfg(test)]
mod q51_measure_gate {
    use super::*;
    use crate::optimizer::sparrow::sheet_skeleton::SkeletonRole;
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
        let orient = std::rc::Rc::new(OrientationCatalog::placeholder(&part.id));
        let analysis = std::rc::Rc::new(PartAnalysis::placeholder(&part.id, &prof));
        SPInstance {
            idx,
            instance_id: format!("{}#{idx}", part.id),
            part_id: part.id.clone(),
            part,
            allowed_rotations_deg: rots,
            continuous_rotation: true,
            base_shape: base,
            shape_profile: prof,
            orientation_catalog: orient,
            part_analysis: analysis,
        }
    }

    #[test]
    fn measure_gate_admit_third_big_part_on_one_sheet() {
        let part = load_lv8_11612();
        let instances: Vec<SPInstance> = (0..3)
            .map(|i| continuous_instance(i, part.clone()))
            .collect();
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
        let rot =
            super::super::fixed_sheet::fitting_rotation(&instances[0], std::slice::from_ref(sheet));
        let (rw, _rh) = dims_for_rotation(part.width, part.height, rot);
        let mk = |idx: usize, rmx: f64| {
            let (ax, ay) = placement_anchor_from_rect_min(
                rmx,
                sheet.min_y + 5.0,
                part.width,
                part.height,
                rot,
            );
            SparrowPlacement {
                instance_idx: idx,
                sheet_index: 0,
                x: ax,
                y: ay,
                rotation_deg: rot,
            }
        };
        let working = SparrowLayout {
            placements: vec![mk(0, sheet.min_x + 5.0), mk(1, sheet.min_x + rw + 20.0)],
        };
        let setup_feasible =
            SparrowCollisionTracker::final_validation_tracker(&working, &instances, &sheets)
                .is_feasible();
        assert!(
            setup_feasible,
            "two big parts side by side must be feasible (rw={rw})"
        );

        // Try to admit the 3rd big part onto the same sheet (only interlock can fit it).
        let result = try_admit_critical(
            &optimizer, &working, 2, 0, &instances, &sheets, &started, 25.0, &mut rng, &mut diag,
            &mut bpp, None,
        );
        let admitted = result.is_some();
        eprintln!("=== Q51 MEASURE-GATE: 3rd big Lv8_11612 admitted on one sheet = {admitted} ===");
        if let Some(out) = result {
            assert!(
                layout_is_full_feasible(&out, &instances, &sheets),
                "admitted layout must be feasible"
            );
            let on_sheet = out.placements.iter().filter(|p| p.sheet_index == 0).count();
            eprintln!("=== Q51 MEASURE-GATE: parts on sheet 0 = {on_sheet} (expect 3) ===");
            assert_eq!(on_sheet, 3, "all 3 big parts on one sheet");
        }
        // The test passes either way; the eprintln reports the gate outcome (run with --nocapture).
    }

    #[test]
    fn interlock_role_consults_live_pair_index_in_production_branch() {
        let part = load_lv8_11612();
        let instances: Vec<SPInstance> = (0..2)
            .map(|i| continuous_instance(i, part.clone()))
            .collect();
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
        let mut rng = DeterministicRng::new(7);
        let mut diag = SparrowDiagnostics::default();
        let mut bpp = BppReductionDiagnostics::default();
        let started = std::time::Instant::now();

        let rot =
            super::super::fixed_sheet::fitting_rotation(&instances[0], std::slice::from_ref(sheet));
        let (ax, ay) = placement_anchor_from_rect_min(
            sheet.min_x + 5.0,
            sheet.min_y + 5.0,
            part.width,
            part.height,
            rot,
        );
        let working = SparrowLayout {
            placements: vec![SparrowPlacement {
                instance_idx: 0,
                sheet_index: 0,
                x: ax,
                y: ay,
                rotation_deg: rot,
            }],
        };

        std::env::set_var("VRS_SHEET_BUILDER_SKELETON", "1");
        std::env::set_var("VRS_INTERLOCK_PAIR", "1");
        std::env::set_var("VRS_PAIR_INDEX", "1");
        let _ = try_admit_critical(
            &optimizer,
            &working,
            1,
            0,
            &instances,
            &sheets,
            &started,
            10.0,
            &mut rng,
            &mut diag,
            &mut bpp,
            Some(SkeletonRole::Interlock),
        );
        std::env::remove_var("VRS_SHEET_BUILDER_SKELETON");
        std::env::remove_var("VRS_INTERLOCK_PAIR");
        std::env::remove_var("VRS_PAIR_INDEX");

        assert!(
            bpp.bpp_q61_pair_index_consulted,
            "the production Interlock branch must consult the live pair index"
        );
        assert!(
            bpp.bpp_q61_pair_candidates_generated > 0
                || bpp.bpp_q61_pair_rejection_summary.is_some(),
            "pair consultation must yield candidates or an explicit rejection summary"
        );
        if bpp.bpp_q61_pair_candidates_accepted > 0 {
            assert!(bpp.bpp_q65_accepted_pair_source.is_some());
            assert!(bpp.bpp_q65_accepted_pair_score.is_some());
            assert!(bpp.bpp_q65_accepted_pair_relative_transform.is_some());
        } else {
            assert!(bpp.bpp_q61_interlock_fallback_to_neighbour);
            assert!(bpp.bpp_q61_pair_rejection_summary.is_some());
        }
    }
}

#[cfg(test)]
mod q67_tests {
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
        let orient = std::rc::Rc::new(OrientationCatalog::placeholder(&part.id));
        let analysis = std::rc::Rc::new(PartAnalysis::placeholder(&part.id, &prof));
        SPInstance {
            idx,
            instance_id: format!("{}#{idx}", part.id),
            part_id: part.id.clone(),
            part,
            allowed_rotations_deg: vec![0.0],
            continuous_rotation: false,
            base_shape: base,
            shape_profile: prof,
            orientation_catalog: orient,
            part_analysis: analysis,
        }
    }

    #[test]
    fn simultaneous_same_part_authority_commits_three_part_group_in_production_branch() {
        let part = poly_part(
            "q67_rect",
            300.0,
            200.0,
            serde_json::json!([[0.0, 0.0], [300.0, 0.0], [300.0, 200.0], [0.0, 200.0]]),
        );
        let instances = vec![
            make_instance(0, part.clone()),
            make_instance(1, part.clone()),
            make_instance(2, part),
        ];
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
        let mut rng = DeterministicRng::new(11);
        let mut diag = SparrowDiagnostics::default();
        let mut bpp = BppReductionDiagnostics::default();
        let started = std::time::Instant::now();

        let rot =
            super::super::fixed_sheet::fitting_rotation(&instances[0], std::slice::from_ref(sheet));
        let (ax, ay) = placement_anchor_from_rect_min(
            sheet.min_x + 5.0,
            sheet.min_y + 5.0,
            instances[0].part.width,
            instances[0].part.height,
            rot,
        );
        let (rw, _) = dims_for_rotation(instances[0].part.width, instances[0].part.height, rot);
        let mk = |idx: usize, rmx: f64| {
            let (px, py) = placement_anchor_from_rect_min(
                rmx,
                sheet.min_y + 5.0,
                instances[idx].part.width,
                instances[idx].part.height,
                rot,
            );
            SparrowPlacement {
                instance_idx: idx,
                sheet_index: 0,
                x: px,
                y: py,
                rotation_deg: rot,
            }
        };
        let working = SparrowLayout {
            placements: vec![mk(0, sheet.min_x + 5.0), mk(1, sheet.min_x + rw + 20.0)],
        };

        std::env::set_var("VRS_SIMULTANEOUS_CRITICAL", "1");
        let result = try_admit_critical(
            &optimizer, &working, 2, 0, &instances, &sheets, &started, 10.0, &mut rng, &mut diag,
            &mut bpp, None,
        );
        std::env::remove_var("VRS_SIMULTANEOUS_CRITICAL");

        assert!(
            result.is_some(),
            "the three-part same-part group should commit"
        );
        assert!(bpp.bpp_q61_simultaneous_critical_consulted);
        assert!(
            bpp.bpp_q67_simultaneous_authority_used,
            "authority_used=false full_successes={} partial_successes={} best_partial={} best_source={:?} rejection={:?}",
            bpp.bpp_q67_simultaneous_full_successes,
            bpp.bpp_q67_simultaneous_partial_successes,
            bpp.bpp_q67_simultaneous_best_partial_count,
            bpp.bpp_q67_simultaneous_best_partial_source,
            bpp.bpp_q67_simultaneous_rejection_summary
        );
        assert!(bpp.bpp_q67_simultaneous_full_successes > 0);
        assert!(bpp.bpp_q67_simultaneous_accepted_group_source.is_some());
    }

    #[test]
    fn simultaneous_same_part_authority_preserves_best_partial_on_three_part_fail() {
        let part = poly_part(
            "q67_big",
            700.0,
            2400.0,
            serde_json::json!([[0.0, 0.0], [700.0, 0.0], [700.0, 2400.0], [0.0, 2400.0]]),
        );
        let instances = vec![
            make_instance(0, part.clone()),
            make_instance(1, part.clone()),
            make_instance(2, part),
        ];
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
        let mut rng = DeterministicRng::new(17);
        let mut diag = SparrowDiagnostics::default();
        let mut bpp = BppReductionDiagnostics::default();
        let started = std::time::Instant::now();

        let rot =
            super::super::fixed_sheet::fitting_rotation(&instances[0], std::slice::from_ref(sheet));
        let (rw, _) = dims_for_rotation(instances[0].part.width, instances[0].part.height, rot);
        let mk = |idx: usize, rmx: f64| {
            let (ax, ay) = placement_anchor_from_rect_min(
                rmx,
                sheet.min_y + 5.0,
                instances[idx].part.width,
                instances[idx].part.height,
                rot,
            );
            SparrowPlacement {
                instance_idx: idx,
                sheet_index: 0,
                x: ax,
                y: ay,
                rotation_deg: rot,
            }
        };
        let working = SparrowLayout {
            placements: vec![mk(0, sheet.min_x + 5.0), mk(1, sheet.min_x + rw + 20.0)],
        };

        std::env::set_var("VRS_SIMULTANEOUS_CRITICAL", "1");
        let _ = try_admit_critical(
            &optimizer, &working, 2, 0, &instances, &sheets, &started, 10.0, &mut rng, &mut diag,
            &mut bpp, None,
        );
        std::env::remove_var("VRS_SIMULTANEOUS_CRITICAL");

        assert!(bpp.bpp_q61_simultaneous_critical_consulted);
        assert_eq!(bpp.bpp_q67_simultaneous_best_partial_count, 2);
        assert!(bpp.bpp_q67_simultaneous_rejection_summary.is_some());
    }
}
