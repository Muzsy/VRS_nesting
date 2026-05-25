use serde::{Deserialize, Serialize};
use std::collections::HashSet;

use crate::geometry::Rect;
use crate::io::Placement;
use crate::item::{
    dims_for_rotation, placement_anchor_from_rect_min, resolve_instance_rotation_angles, Part,
};
use crate::rotation_policy::RotationResolveContext;
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::{generate_candidates_with_sheets, PlacedBbox};
use super::initializer::bbox_from_placement;
use super::repair::find_violations;
use super::separator::{VrsSeparator, VrsSeparatorConfig};
use super::state::PlacementTransform;
use super::working::WorkingLayout;

// ---------------------------------------------------------------------------
// CandidateMove (skeleton, retained from pre-SGH-05)
// ---------------------------------------------------------------------------

/// Optimizer move skeleton. Place/Move/Reinsert/Rotate variants cover the
/// four canonical search operations.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CandidateMove {
    /// Place an unplaced instance at the given sheet and transform.
    Place {
        instance_id: String,
        sheet_index: usize,
        transform: PlacementTransform,
    },
    /// Move an already-placed instance to a different sheet and/or transform.
    Move {
        instance_id: String,
        to_sheet_index: usize,
        to_transform: PlacementTransform,
    },
    /// Reinsert an instance (may be placed or unplaced) at a new location.
    Reinsert {
        instance_id: String,
        sheet_index: usize,
        transform: PlacementTransform,
    },
    /// Rotate a placed or candidate instance to a new rotation.
    Rotate {
        instance_id: String,
        new_rotation_deg: f64,
    },
}

// ---------------------------------------------------------------------------
// MoveFailureReason
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum MoveFailureReason {
    UnknownInstanceId,
    InvalidSheetIndex,
    UnsupportedRotation,
    NoValidSeedPlacement,
    SeparatorDidNotConverge,
    CommitGateRejected,
    PlacementCountMismatch,
    InstanceSetMismatch,
}

impl std::fmt::Display for MoveFailureReason {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let s = match self {
            Self::UnknownInstanceId => "unknown_instance_id",
            Self::InvalidSheetIndex => "invalid_sheet_index",
            Self::UnsupportedRotation => "unsupported_rotation",
            Self::NoValidSeedPlacement => "no_valid_seed_placement",
            Self::SeparatorDidNotConverge => "separator_did_not_converge",
            Self::CommitGateRejected => "commit_gate_rejected",
            Self::PlacementCountMismatch => "placement_count_mismatch",
            Self::InstanceSetMismatch => "instance_set_mismatch",
        };
        write!(f, "{}", s)
    }
}

// ---------------------------------------------------------------------------
// MoveDiagnostics
// ---------------------------------------------------------------------------

#[derive(Debug, Clone, Default)]
pub struct MoveDiagnostics {
    pub attempted: usize,
    pub committed: usize,
    pub rolled_back: usize,
    pub separator_attempts: usize,
    pub separator_successes: usize,
    pub commit_gate_rejections: usize,
    pub last_reason: String,
}

impl MoveDiagnostics {
    pub fn summary(&self) -> String {
        format!(
            "attempted={} committed={} rolled_back={} sep_attempts={} sep_ok={} \
             commit_reject={} last_reason={}",
            self.attempted,
            self.committed,
            self.rolled_back,
            self.separator_attempts,
            self.separator_successes,
            self.commit_gate_rejections,
            self.last_reason,
        )
    }

    fn record_failure(&mut self, reason: MoveFailureReason) {
        self.rolled_back += 1;
        self.last_reason = reason.to_string();
    }

    fn record_success(&mut self) {
        self.committed += 1;
        self.last_reason = "committed".to_string();
    }
}

// ---------------------------------------------------------------------------
// MoveExecutor
// ---------------------------------------------------------------------------

pub struct MoveExecutor<'a> {
    parts: &'a [Part],
    sheets: &'a [SheetShape],
    rotation_context: RotationResolveContext,
}

impl<'a> MoveExecutor<'a> {
    pub fn new(parts: &'a [Part], sheets: &'a [SheetShape]) -> Self {
        Self::new_with_rotation_context(parts, sheets, RotationResolveContext::legacy_default())
    }

    pub fn new_with_rotation_context(
        parts: &'a [Part],
        sheets: &'a [SheetShape],
        rotation_context: RotationResolveContext,
    ) -> Self {
        Self {
            parts,
            sheets,
            rotation_context,
        }
    }

    // ── Private helpers ──────────────────────────────────────────────────────

    fn rebuild_bboxes(&self, placements: &[Placement]) -> Vec<PlacedBbox> {
        placements
            .iter()
            .filter_map(|p| {
                let pt = self.parts.iter().find(|pt| pt.id == p.part_id)?;
                bbox_from_placement(p, pt.width, pt.height)
            })
            .collect()
    }

    fn instance_id_set(placements: &[Placement]) -> HashSet<String> {
        placements.iter().map(|p| p.instance_id.clone()).collect()
    }

    /// Full commit gate: count, instance set, sheet bounds, find_violations.
    fn commit_gate_ok(
        &self,
        new_placements: &[Placement],
        original_count: usize,
        original_ids: &HashSet<String>,
    ) -> bool {
        if new_placements.len() != original_count {
            return false;
        }
        let new_ids: HashSet<String> =
            new_placements.iter().map(|p| p.instance_id.clone()).collect();
        if new_ids != *original_ids {
            return false;
        }
        if new_placements.iter().any(|p| p.sheet_index >= self.sheets.len()) {
            return false;
        }
        find_violations(new_placements, self.parts, self.sheets).is_empty()
    }

    /// Build WorkingLayout → VrsSeparator → validate; returns committed placements or None.
    fn run_separator_fix(
        &self,
        placements: Vec<Placement>,
        allowed_sheet_indices: Option<Vec<usize>>,
        diag: &mut MoveDiagnostics,
    ) -> Option<Vec<Placement>> {
        diag.separator_attempts += 1;
        let working = WorkingLayout::new(placements, vec![], self.sheets.len(), 0);
        let sep = VrsSeparator::new(VrsSeparatorConfig {
            allowed_sheet_indices,
            rotation_context: self.rotation_context.clone(),
            ..VrsSeparatorConfig::default()
        });
        let (sep_layout, sep_diag) = sep.run(working, self.parts, self.sheets);
        if !(sep_diag.best_loss == 0.0 || sep_diag.converged) {
            return None;
        }
        if sep_layout.validate_for_commit(self.parts, self.sheets).is_err() {
            return None;
        }
        diag.separator_successes += 1;
        Some(sep_layout.placements)
    }

    /// Compute seed Placement at origin of `sheet_index`.
    ///
    /// If `rotation_override` is given it must be in `rots`; otherwise finds first
    /// rotation whose bbox fits at origin, or falls back to first supported rotation.
    fn seed_at_origin(
        &self,
        instance_id: &str,
        part_id: &str,
        width: f64,
        height: f64,
        rots: &[f64],
        sheet_index: usize,
        rotation_override: Option<f64>,
    ) -> Option<Placement> {
        if sheet_index >= self.sheets.len() {
            return None;
        }
        let sheet = &self.sheets[sheet_index];

        let rot = if let Some(r) = rotation_override {
            let r_norm = r.rem_euclid(360.0);
            if !rots.iter().any(|&x| (x - r_norm).abs() < 1e-6) {
                return None;
            }
            r_norm
        } else {
            rots.iter()
                .copied()
                .find(|&r| {
                    let (rw, rh) = dims_for_rotation(width, height, r);
                    rect_within_boundary(
                        Rect { x1: 0.0, y1: 0.0, x2: rw, y2: rh },
                        sheet,
                    )
                })
                .or_else(|| rots.first().copied())?
        };

        let (anchor_x, anchor_y) =
            placement_anchor_from_rect_min(0.0, 0.0, width, height, rot);
        Some(Placement {
            instance_id: instance_id.to_string(),
            part_id: part_id.to_string(),
            sheet_index,
            x: anchor_x,
            y: anchor_y,
            rotation_deg: rot,
        })
    }

    /// Find the best LBF-scored collision-free candidate on `target_sheet`.
    ///
    /// `placed_bboxes` must exclude the item being placed.
    /// Returns None if no clear (collision-free, boundary-valid) candidate exists.
    fn lbf_clear_on_sheet(
        &self,
        instance_id: &str,
        part_id: &str,
        width: f64,
        height: f64,
        rots: &[f64],
        target_sheet: usize,
        placed_bboxes: &[PlacedBbox],
    ) -> Option<Placement> {
        if target_sheet >= self.sheets.len() {
            return None;
        }
        let sheet = &self.sheets[target_sheet];
        let (all_candidates, _) = generate_candidates_with_sheets(self.sheets, placed_bboxes);

        let mut best_key: Option<(f64, f64)> = None; // (y, x) — lower is better
        let mut best: Option<Placement> = None;

        for cand in all_candidates.iter().filter(|c| c.sheet_index == target_sheet) {
            for &rot in rots {
                let (rw, rh) = dims_for_rotation(width, height, rot);
                let rect = Rect {
                    x1: cand.x,
                    y1: cand.y,
                    x2: cand.x + rw,
                    y2: cand.y + rh,
                };
                if !rect_within_boundary(rect, sheet) {
                    continue;
                }
                let cand_bbox = PlacedBbox {
                    sheet_index: target_sheet,
                    x1: cand.x,
                    y1: cand.y,
                    x2: cand.x + rw,
                    y2: cand.y + rh,
                };
                if placed_bboxes.iter().any(|pb| pb.overlaps(&cand_bbox)) {
                    continue;
                }
                let (anchor_x, anchor_y) =
                    placement_anchor_from_rect_min(cand.x, cand.y, width, height, rot);
                let key = (cand.y, cand.x);
                let better = best_key.map_or(true, |(ky, kx)| {
                    const EPS: f64 = 1e-12;
                    if (key.0 - ky).abs() > EPS {
                        return key.0 < ky;
                    }
                    key.1 < kx - EPS
                });
                if better {
                    best_key = Some(key);
                    best = Some(Placement {
                        instance_id: instance_id.to_string(),
                        part_id: part_id.to_string(),
                        sheet_index: target_sheet,
                        x: anchor_x,
                        y: anchor_y,
                        rotation_deg: rot,
                    });
                }
                // First valid rotation per candidate point (stable rotation order).
                break;
            }
        }

        best
    }

    fn resolve_part_dims(&self, part_id: &str, instance_id: &str) -> Option<(f64, f64, Vec<f64>)> {
        let pt = self.parts.iter().find(|pt| pt.id == part_id)?;
        let rots = resolve_instance_rotation_angles(pt, instance_id, &self.rotation_context);
        if rots.is_empty() { return None; }
        Some((pt.width, pt.height, rots))
    }

    // ── Public operators ─────────────────────────────────────────────────────

    /// Reinsert `instance_id` on `to_sheet` with `rotation_deg`, seeded at origin.
    ///
    /// Seeds the item at the bbox-min origin of `to_sheet`, then runs the separator
    /// scoped to `to_sheet` to resolve any collisions.  Commits only if the global
    /// layout passes find_violations.  On failure returns None (caller's slice
    /// is unchanged — rollback-safe by design).
    pub fn try_reinsert(
        &self,
        placements: &[Placement],
        instance_id: &str,
        to_sheet: usize,
        rotation_deg: f64,
        diag: &mut MoveDiagnostics,
    ) -> Option<Vec<Placement>> {
        diag.attempted += 1;

        if to_sheet >= self.sheets.len() {
            diag.record_failure(MoveFailureReason::InvalidSheetIndex);
            return None;
        }

        let idx = match placements.iter().position(|p| p.instance_id == instance_id) {
            Some(i) => i,
            None => {
                diag.record_failure(MoveFailureReason::UnknownInstanceId);
                return None;
            }
        };

        let part_id = placements[idx].part_id.clone();
        let (width, height, rots) = match self.resolve_part_dims(&part_id, instance_id) {
            Some(d) => d,
            None => {
                diag.record_failure(MoveFailureReason::UnknownInstanceId);
                return None;
            }
        };

        let rot_norm = rotation_deg.rem_euclid(360.0);
        if !rots.iter().any(|&r| (r - rot_norm).abs() < 1e-6) {
            diag.record_failure(MoveFailureReason::UnsupportedRotation);
            return None;
        }

        let seed =
            match self.seed_at_origin(instance_id, &part_id, width, height, &rots, to_sheet, Some(rot_norm)) {
                Some(s) => s,
                None => {
                    diag.record_failure(MoveFailureReason::NoValidSeedPlacement);
                    return None;
                }
            };

        let original_count = placements.len();
        let original_ids = Self::instance_id_set(placements);

        let mut new_placements: Vec<Placement> = placements
            .iter()
            .enumerate()
            .filter(|(i, _)| *i != idx)
            .map(|(_, p)| p.clone())
            .collect();
        new_placements.push(seed);

        let result = match self.run_separator_fix(new_placements, Some(vec![to_sheet]), diag) {
            Some(r) => r,
            None => {
                diag.record_failure(MoveFailureReason::SeparatorDidNotConverge);
                return None;
            }
        };

        if !self.commit_gate_ok(&result, original_count, &original_ids) {
            diag.commit_gate_rejections += 1;
            diag.record_failure(MoveFailureReason::CommitGateRejected);
            return None;
        }

        diag.record_success();
        Some(result)
    }

    /// Move `instance_id` from its current sheet to `to_sheet`.
    ///
    /// Priority: (1) explicit rotation placement + separator; (2) LBF clear candidate;
    /// (3) origin seed + separator.  All paths commit only if find_violations is empty.
    pub fn try_transfer(
        &self,
        placements: &[Placement],
        instance_id: &str,
        to_sheet: usize,
        explicit_rotation: Option<f64>,
        diag: &mut MoveDiagnostics,
    ) -> Option<Vec<Placement>> {
        diag.attempted += 1;

        if to_sheet >= self.sheets.len() {
            diag.record_failure(MoveFailureReason::InvalidSheetIndex);
            return None;
        }

        let idx = match placements.iter().position(|p| p.instance_id == instance_id) {
            Some(i) => i,
            None => {
                diag.record_failure(MoveFailureReason::UnknownInstanceId);
                return None;
            }
        };

        let part_id = placements[idx].part_id.clone();
        let (width, height, rots) = match self.resolve_part_dims(&part_id, instance_id) {
            Some(d) => d,
            None => {
                diag.record_failure(MoveFailureReason::UnknownInstanceId);
                return None;
            }
        };

        if let Some(rot) = explicit_rotation {
            if !rots.iter().any(|&r| (r - rot.rem_euclid(360.0)).abs() < 1e-6) {
                diag.record_failure(MoveFailureReason::UnsupportedRotation);
                return None;
            }
        }

        let original_count = placements.len();
        let original_ids = Self::instance_id_set(placements);

        // Placements without the item being transferred.
        let without: Vec<Placement> = placements
            .iter()
            .enumerate()
            .filter(|(i, _)| *i != idx)
            .map(|(_, p)| p.clone())
            .collect();
        let placed_bboxes = self.rebuild_bboxes(&without);

        // Path 1: explicit rotation provided — seed at origin with that rotation, run separator.
        if let Some(rot) = explicit_rotation {
            let rot_norm = rot.rem_euclid(360.0);
            if let Some(seed) = self.seed_at_origin(
                &placements[idx].instance_id,
                &part_id,
                width,
                height,
                &rots,
                to_sheet,
                Some(rot_norm),
            ) {
                let mut candidate = without.clone();
                candidate.push(seed);
                if let Some(result) =
                    self.run_separator_fix(candidate, Some(vec![to_sheet]), diag)
                {
                    if self.commit_gate_ok(&result, original_count, &original_ids) {
                        diag.record_success();
                        return Some(result);
                    }
                    diag.commit_gate_rejections += 1;
                }
            }
        }

        // Path 2: LBF clear placement on to_sheet (no separator needed).
        if let Some(placement) = self.lbf_clear_on_sheet(
            &placements[idx].instance_id,
            &part_id,
            width,
            height,
            &rots,
            to_sheet,
            &placed_bboxes,
        ) {
            let mut candidate = without.clone();
            candidate.push(placement);
            if self.commit_gate_ok(&candidate, original_count, &original_ids) {
                diag.record_success();
                return Some(candidate);
            }
            diag.commit_gate_rejections += 1;
        }

        // Path 3: seed at origin and run separator.
        let seed = match self.seed_at_origin(
            &placements[idx].instance_id,
            &part_id,
            width,
            height,
            &rots,
            to_sheet,
            None,
        ) {
            Some(s) => s,
            None => {
                diag.record_failure(MoveFailureReason::NoValidSeedPlacement);
                return None;
            }
        };
        let mut candidate = without;
        candidate.push(seed);

        let result = match self.run_separator_fix(candidate, Some(vec![to_sheet]), diag) {
            Some(r) => r,
            None => {
                diag.record_failure(MoveFailureReason::SeparatorDidNotConverge);
                return None;
            }
        };

        if !self.commit_gate_ok(&result, original_count, &original_ids) {
            diag.commit_gate_rejections += 1;
            diag.record_failure(MoveFailureReason::CommitGateRejected);
            return None;
        }

        diag.record_success();
        Some(result)
    }

    /// Swap `instance_id_a` and `instance_id_b` between their sheets.
    ///
    /// Same-sheet swap: deterministic no-op (returns placements unchanged, counts as committed).
    /// Cross-sheet swap: seeds each item at the other item's old sheet at origin, then runs
    /// separator scoped to both affected sheets.
    pub fn try_swap(
        &self,
        placements: &[Placement],
        instance_id_a: &str,
        instance_id_b: &str,
        diag: &mut MoveDiagnostics,
    ) -> Option<Vec<Placement>> {
        diag.attempted += 1;

        let idx_a = match placements.iter().position(|p| p.instance_id == instance_id_a) {
            Some(i) => i,
            None => {
                diag.record_failure(MoveFailureReason::UnknownInstanceId);
                return None;
            }
        };
        let idx_b = match placements.iter().position(|p| p.instance_id == instance_id_b) {
            Some(i) => i,
            None => {
                diag.record_failure(MoveFailureReason::UnknownInstanceId);
                return None;
            }
        };

        let sheet_a = placements[idx_a].sheet_index;
        let sheet_b = placements[idx_b].sheet_index;

        // Same-sheet swap: no-op success (documented, deterministic).
        if sheet_a == sheet_b {
            diag.committed += 1;
            diag.last_reason = "same_sheet_swap_noop_success".to_string();
            return Some(placements.to_vec());
        }

        let (w_a, h_a, rots_a) =
            match self.resolve_part_dims(&placements[idx_a].part_id, &placements[idx_a].instance_id) {
            Some(d) => d,
            None => {
                diag.record_failure(MoveFailureReason::UnknownInstanceId);
                return None;
            }
        };
        let (w_b, h_b, rots_b) =
            match self.resolve_part_dims(&placements[idx_b].part_id, &placements[idx_b].instance_id) {
            Some(d) => d,
            None => {
                diag.record_failure(MoveFailureReason::UnknownInstanceId);
                return None;
            }
        };

        let original_count = placements.len();
        let original_ids = Self::instance_id_set(placements);

        // Try B's old rotation for A (if supported), otherwise A's first rotation.
        let rot_for_a = {
            let r = placements[idx_b].rotation_deg.rem_euclid(360.0);
            if rots_a.iter().any(|&x| (x - r).abs() < 1e-6) { r } else { *rots_a.first().unwrap() }
        };
        // Try A's old rotation for B (if supported), otherwise B's first rotation.
        let rot_for_b = {
            let r = placements[idx_a].rotation_deg.rem_euclid(360.0);
            if rots_b.iter().any(|&x| (x - r).abs() < 1e-6) { r } else { *rots_b.first().unwrap() }
        };

        let seed_a = match self.seed_at_origin(
            instance_id_a, &placements[idx_a].part_id, w_a, h_a, &rots_a, sheet_b, Some(rot_for_a),
        ) {
            Some(s) => s,
            None => {
                diag.record_failure(MoveFailureReason::NoValidSeedPlacement);
                return None;
            }
        };
        let seed_b = match self.seed_at_origin(
            instance_id_b, &placements[idx_b].part_id, w_b, h_b, &rots_b, sheet_a, Some(rot_for_b),
        ) {
            Some(s) => s,
            None => {
                diag.record_failure(MoveFailureReason::NoValidSeedPlacement);
                return None;
            }
        };

        let mut new_placements: Vec<Placement> = placements
            .iter()
            .enumerate()
            .filter(|(i, _)| *i != idx_a && *i != idx_b)
            .map(|(_, p)| p.clone())
            .collect();
        new_placements.push(seed_a);
        new_placements.push(seed_b);

        let result = match self.run_separator_fix(
            new_placements,
            Some(vec![sheet_a, sheet_b]),
            diag,
        ) {
            Some(r) => r,
            None => {
                diag.record_failure(MoveFailureReason::SeparatorDidNotConverge);
                return None;
            }
        };

        if !self.commit_gate_ok(&result, original_count, &original_ids) {
            diag.commit_gate_rejections += 1;
            diag.record_failure(MoveFailureReason::CommitGateRejected);
            return None;
        }

        diag.record_success();
        Some(result)
    }

    /// Budget-aware transfer helper.
    ///
    /// Iterates source sheets ascending, items on each sheet in area-desc/instance_id-asc order,
    /// destination sheets ascending.  Each failed attempt is rollback-safe (caller's placements
    /// are unmodified on failure).  Budget decremented per attempt regardless of outcome.
    /// Returns updated placements (may be unchanged if all attempts fail or budget exhausted).
    pub fn resolve_by_transfers(
        &self,
        mut placements: Vec<Placement>,
        source_sheets: &[usize],
        dest_sheets: &[usize],
        budget: usize,
        diag: &mut MoveDiagnostics,
    ) -> Vec<Placement> {
        let mut remaining = budget;

        let mut sorted_sources = source_sheets.to_vec();
        sorted_sources.sort_unstable();

        let mut sorted_dests = dest_sheets.to_vec();
        sorted_dests.sort_unstable();

        'outer: for &src in &sorted_sources {
            if remaining == 0 {
                break;
            }

            // Snapshot items on this source sheet (largest-first, then instance_id asc).
            let mut items_on_src: Vec<Placement> = placements
                .iter()
                .filter(|p| p.sheet_index == src)
                .cloned()
                .collect();
            items_on_src.sort_by(|a, b| {
                let area_a = self
                    .parts
                    .iter()
                    .find(|pt| pt.id == a.part_id)
                    .map(|pt| pt.width * pt.height)
                    .unwrap_or(0.0);
                let area_b = self
                    .parts
                    .iter()
                    .find(|pt| pt.id == b.part_id)
                    .map(|pt| pt.width * pt.height)
                    .unwrap_or(0.0);
                area_b
                    .partial_cmp(&area_a)
                    .unwrap_or(std::cmp::Ordering::Equal)
                    .then_with(|| a.instance_id.cmp(&b.instance_id))
            });

            for item in &items_on_src {
                if remaining == 0 {
                    break 'outer;
                }
                // Skip if already moved by a prior successful transfer in this pass.
                if !placements
                    .iter()
                    .any(|p| p.instance_id == item.instance_id && p.sheet_index == src)
                {
                    continue;
                }

                for &dst in &sorted_dests {
                    if dst == src {
                        continue;
                    }
                    if remaining == 0 {
                        break;
                    }
                    remaining -= 1;

                    if let Some(new_placements) =
                        self.try_transfer(&placements, &item.instance_id, dst, None, diag)
                    {
                        placements = new_placements;
                        break; // Item transferred; move to next item.
                    }
                }
            }
        }

        placements
    }
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::item::{expand_instances, Part};
    use crate::optimizer::initializer::build_initial_layout;
    use crate::optimizer::repair::find_violations;
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(id: &str, w: f64, h: f64, qty: i64) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: None,
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    fn make_stock(id: &str, w: f64, h: f64, qty: i64) -> Stock {
        Stock {
            id: id.to_string(),
            quantity: qty,
            width: Some(w),
            height: Some(h),
            outer_points: None,
            holes_points: None,
            cost_per_use: None,
        }
    }

    fn t(x: f64, y: f64, rot: i64) -> PlacementTransform {
        PlacementTransform { x, y, rotation_deg: rot }
    }

    // ── Existing serialization tests (unchanged) ─────────────────────────────

    #[test]
    fn candidate_move_place_creates() {
        let mv = CandidateMove::Place {
            instance_id: "A__0001".to_string(),
            sheet_index: 0,
            transform: t(0.0, 0.0, 0),
        };
        let json = serde_json::to_string(&mv).expect("serialize");
        assert!(json.contains("Place"));
        assert!(json.contains("A__0001"));
    }

    #[test]
    fn candidate_move_all_variants_create() {
        let variants: Vec<CandidateMove> = vec![
            CandidateMove::Place {
                instance_id: "A".to_string(),
                sheet_index: 0,
                transform: t(0.0, 0.0, 0),
            },
            CandidateMove::Move {
                instance_id: "B".to_string(),
                to_sheet_index: 1,
                to_transform: t(10.0, 0.0, 90),
            },
            CandidateMove::Reinsert {
                instance_id: "C".to_string(),
                sheet_index: 0,
                transform: t(20.0, 0.0, 180),
            },
            CandidateMove::Rotate {
                instance_id: "D".to_string(),
                new_rotation_deg: 270.0,
            },
        ];
        assert_eq!(variants.len(), 4);
        for mv in &variants {
            let json = serde_json::to_string(mv).expect("serialize");
            assert!(!json.is_empty());
        }
    }

    #[test]
    fn candidate_move_json_stable() {
        let mv =
            CandidateMove::Rotate { instance_id: "X__0001".to_string(), new_rotation_deg: 90.0 };
        let j1 = serde_json::to_string(&mv).expect("s1");
        let j2 = serde_json::to_string(&mv).expect("s2");
        assert_eq!(j1, j2);
    }

    // ── SGH-05 tests ─────────────────────────────────────────────────────────

    fn two_item_layout() -> (Vec<Placement>, Vec<Part>, Vec<crate::sheet::SheetShape>) {
        let parts = vec![make_part("A", 20.0, 20.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placed, _, _) = build_initial_layout(&instances, &parts, &sheets);
        (placed, parts, sheets)
    }

    #[test]
    fn try_reinsert_valid_commits() {
        let (placements, parts, sheets) = two_item_layout();
        assert!(!placements.is_empty());
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let iid = placements[0].instance_id.clone();
        let rot = placements[0].rotation_deg;
        let result = exec.try_reinsert(&placements, &iid, 0, rot, &mut diag);
        assert!(result.is_some(), "reinsert on same sheet must commit");
        let new = result.unwrap();
        assert!(find_violations(&new, &parts, &sheets).is_empty());
        assert_eq!(diag.committed, 1);
    }

    #[test]
    fn try_reinsert_unknown_instance_id_fails() {
        let (placements, parts, sheets) = two_item_layout();
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let result = exec.try_reinsert(&placements, "nonexistent__9999", 0, 0.0, &mut diag);
        assert!(result.is_none());
        assert_eq!(diag.rolled_back, 1);
        assert_eq!(diag.committed, 0);
    }

    #[test]
    fn try_reinsert_invalid_sheet_index_fails() {
        let (placements, parts, sheets) = two_item_layout();
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let iid = placements[0].instance_id.clone();
        let result = exec.try_reinsert(&placements, &iid, 9999, 0.0, &mut diag);
        assert!(result.is_none());
        assert_eq!(diag.rolled_back, 1);
    }

    #[test]
    fn try_transfer_success() {
        // Two items on sheet 0, transfer one to sheet 1 (both 100×100).
        let parts = vec![make_part("A", 20.0, 20.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placements, _, _) = build_initial_layout(&instances, &parts, &sheets);
        // Both items should be on sheet 0 (LBF used-sheet-first).
        assert!(!placements.is_empty());
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let iid = placements[0].instance_id.clone();
        let result = exec.try_transfer(&placements, &iid, 1, None, &mut diag);
        assert!(result.is_some(), "transfer to empty sheet 1 must succeed");
        let new = result.unwrap();
        assert!(find_violations(&new, &parts, &sheets).is_empty());
        assert_eq!(new.len(), placements.len());
        // The transferred item must now be on sheet 1.
        let moved = new.iter().find(|p| p.instance_id == iid).expect("item must exist");
        assert_eq!(moved.sheet_index, 1);
    }

    #[test]
    fn try_transfer_invalid_destination_fails() {
        let (placements, parts, sheets) = two_item_layout();
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let iid = placements[0].instance_id.clone();
        let result = exec.try_transfer(&placements, &iid, 999, None, &mut diag);
        assert!(result.is_none());
        assert_eq!(diag.rolled_back, 1);
    }

    #[test]
    fn try_transfer_unsupported_rotation_fails() {
        let (placements, parts, sheets) = two_item_layout();
        // Part only allows rot=0; passing 45 must fail.
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let iid = placements[0].instance_id.clone();
        let result = exec.try_transfer(&placements, &iid, 1, Some(45.0), &mut diag);
        assert!(result.is_none());
    }

    #[test]
    fn try_swap_cross_sheet_success() {
        // A on sheet 0, B on sheet 1; both 30×30 on 100×100 sheets.
        let parts = vec![make_part("A", 30.0, 30.0, 1), make_part("B", 30.0, 30.0, 1)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            Placement {
                instance_id: "A__0001".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "B__0001".into(),
                part_id: "B".into(),
                sheet_index: 1,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let result = exec.try_swap(&placements, "A__0001", "B__0001", &mut diag);
        assert!(result.is_some(), "cross-sheet swap of two fitting items must succeed");
        let new = result.unwrap();
        assert!(find_violations(&new, &parts, &sheets).is_empty());
        assert_eq!(new.len(), 2);
        assert_eq!(diag.committed, 1);
    }

    #[test]
    fn try_swap_same_sheet_is_noop_success() {
        // Both items on sheet 0: same-sheet swap returns original placements, counts as committed.
        let parts = vec![make_part("A", 20.0, 20.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            Placement {
                instance_id: "A__0001".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "A__0002".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 30.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let result = exec.try_swap(&placements, "A__0001", "A__0002", &mut diag);
        assert!(result.is_some(), "same-sheet swap must be noop success");
        assert_eq!(diag.committed, 1);
        let new = result.unwrap();
        assert!(find_violations(&new, &parts, &sheets).is_empty());
    }

    #[test]
    fn try_swap_unknown_instance_fails() {
        let (placements, parts, sheets) = two_item_layout();
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let result = exec.try_swap(&placements, "nonexistent__0001", "A__0001", &mut diag);
        assert!(result.is_none());
        assert_eq!(diag.rolled_back, 1);
    }

    #[test]
    fn resolve_by_transfers_budget_zero_no_changes() {
        let (placements, parts, sheets) = two_item_layout();
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let orig_len = placements.len();
        let result = exec.resolve_by_transfers(placements, &[0], &[1], 0, &mut diag);
        assert_eq!(result.len(), orig_len);
        // Budget=0 → no transfer attempts at all.
        assert_eq!(diag.attempted, 0);
    }

    #[test]
    fn resolve_by_transfers_no_partial_invalid_output() {
        // Source sheet 0, destination is an invalid sheet (9999) → all transfers fail.
        // Result must still be violation-free.
        let (placements, parts, sheets) = two_item_layout();
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let result = exec.resolve_by_transfers(placements.clone(), &[0], &[9999], 10, &mut diag);
        assert!(
            find_violations(&result, &parts, &sheets).is_empty(),
            "failed transfers must leave layout violation-free"
        );
        assert_eq!(result.len(), placements.len());
    }

    #[test]
    fn diagnostics_summary_contains_expected_fields() {
        let (placements, parts, sheets) = two_item_layout();
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let iid = placements[0].instance_id.clone();
        let _ = exec.try_transfer(&placements, &iid, 1, None, &mut diag);
        let summary = diag.summary();
        assert!(summary.contains("attempted="), "summary: {}", summary);
        assert!(summary.contains("committed="), "summary: {}", summary);
        assert!(summary.contains("rolled_back="), "summary: {}", summary);
        assert!(summary.contains("sep_attempts="), "summary: {}", summary);
        assert!(summary.contains("sep_ok="), "summary: {}", summary);
        assert!(summary.contains("commit_reject="), "summary: {}", summary);
        assert!(summary.contains("last_reason="), "summary: {}", summary);
    }

    #[test]
    fn placement_count_and_instance_set_invariant() {
        let (placements, parts, sheets) = two_item_layout();
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let iid = placements[0].instance_id.clone();
        let orig_ids: HashSet<String> =
            placements.iter().map(|p| p.instance_id.clone()).collect();
        let result = exec
            .try_transfer(&placements, &iid, 1, None, &mut diag)
            .expect("transfer must succeed");
        assert_eq!(result.len(), placements.len(), "placement count invariant");
        let new_ids: HashSet<String> = result.iter().map(|p| p.instance_id.clone()).collect();
        assert_eq!(new_ids, orig_ids, "instance set invariant");
    }

    #[test]
    fn deterministic_smoke() {
        let (placements, parts, sheets) = two_item_layout();
        let exec = MoveExecutor::new(&parts, &sheets);
        let iid = placements[0].instance_id.clone();

        let mut diag1 = MoveDiagnostics::default();
        let r1 = exec.try_transfer(&placements, &iid, 1, None, &mut diag1);

        let mut diag2 = MoveDiagnostics::default();
        let r2 = exec.try_transfer(&placements, &iid, 1, None, &mut diag2);

        match (r1, r2) {
            (Some(a), Some(b)) => {
                assert_eq!(a.len(), b.len(), "deterministic: same length");
                for (pa, pb) in a.iter().zip(b.iter()) {
                    assert_eq!(pa.instance_id, pb.instance_id);
                    assert_eq!(pa.sheet_index, pb.sheet_index);
                    assert_eq!(pa.rotation_deg.to_bits(), pb.rotation_deg.to_bits());
                    assert_eq!(pa.x.to_bits(), pb.x.to_bits());
                    assert_eq!(pa.y.to_bits(), pb.y.to_bits());
                }
            }
            (None, None) => {}
            _ => panic!("determinism failed: one run succeeded, the other did not"),
        }
    }

    #[test]
    fn committed_output_find_violations_valid() {
        let (placements, parts, sheets) = two_item_layout();
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let iid = placements[0].instance_id.clone();
        let result = exec
            .try_transfer(&placements, &iid, 1, None, &mut diag)
            .expect("transfer must succeed");
        assert!(
            find_violations(&result, &parts, &sheets).is_empty(),
            "committed output must be violation-free"
        );
    }

    #[test]
    fn resolve_by_transfers_transfers_item_to_dest() {
        // Verify that resolve_by_transfers actually moves an item from sheet 0 to sheet 1.
        let parts = vec![make_part("A", 20.0, 20.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (placements, _, _) = build_initial_layout(&instances, &parts, &sheets);
        let all_on_sheet0 = placements.iter().all(|p| p.sheet_index == 0);
        if !all_on_sheet0 {
            // Layout already split; skip test.
            return;
        }
        let exec = MoveExecutor::new(&parts, &sheets);
        let mut diag = MoveDiagnostics::default();
        let result =
            exec.resolve_by_transfers(placements.clone(), &[0], &[1], 10, &mut diag);
        assert!(find_violations(&result, &parts, &sheets).is_empty());
        assert_eq!(result.len(), placements.len());
        // At least one item should now be on sheet 1.
        assert!(
            result.iter().any(|p| p.sheet_index == 1),
            "resolve_by_transfers must transfer at least one item"
        );
    }
}
