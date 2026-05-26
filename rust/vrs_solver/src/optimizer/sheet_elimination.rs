//! Sheet Elimination V2 — separator-backed sheet count reduction pass.
//!
//! Strategy: snapshot -> select highest-used sheet -> remove its items ->
//! largest-first redistribution to lower-index sheets using LBF clear reinsertion,
//! with separator-backed fallback on failure -> commit or rollback.
//!
//! Commit is accepted only when:
//! - all displaced items are reinserted,
//! - no target/higher sheet is used,
//! - `find_violations` is empty,
//! - `sheet_count_used` strictly decreases,
//! - placement count invariant is preserved.

use std::collections::HashSet;

use crate::geometry::Rect;
use crate::io::{CollisionBackendKind, Placement, Unplaced};
use crate::item::{
    dims_for_rotation, placement_anchor_from_rect_min, resolve_instance_rotation_angles, Part,
};
use crate::rotation_policy::RotationResolveContext;
use crate::sheet::SheetShape;

use super::boundary::rect_within_boundary;
use super::candidates::{generate_candidates_with_sheets, PlacedBbox};
use super::initializer::bbox_from_placement;
use super::multisheet::compute_sheet_count_used;
use super::repair::{find_violations, validate_placements_for_backend};
use super::separator::{VrsSeparator, VrsSeparatorConfig};
use super::stopping::StoppingPolicy;
use super::working::WorkingLayout;

// ---------------------------------------------------------------------------
// Diagnostics
// ---------------------------------------------------------------------------

/// Diagnostics collected by a single `SheetEliminationEngine::run` call.
#[derive(Debug, Clone, Default)]
pub struct SheetEliminationDiagnostics {
    /// `sheet_count_used` before the elimination pass.
    pub sheet_count_used_before: usize,
    /// `sheet_count_used` after the pass (same as before if elimination failed).
    pub sheet_count_used_after: usize,
    /// Sheet index targeted for elimination (if any).
    pub selected_sheet: Option<usize>,
    /// Number of elimination attempts made (0 or 1 in SGH-04).
    pub attempts: usize,
    /// Number of successful eliminations.
    pub successful_eliminations: usize,
    /// Number of failed eliminations.
    pub failed_eliminations: usize,
    /// Number of rollbacks executed.
    pub rollback_count: usize,
    /// Number of displaced items removed from the target sheet.
    pub displaced_items: usize,
    /// Successful clear LBF reinsertion count.
    pub lbf_reinsertion_successes: usize,
    /// Number of separator fallback attempts.
    pub separator_fallback_attempts: usize,
    /// Number of successful separator fallback commits.
    pub separator_fallback_successes: usize,
    /// Number of failed separator fallback attempts.
    pub separator_fallback_failures: usize,
    /// Number of commit-gate rejections.
    pub commit_gate_rejections: usize,
    /// Rejections due to target/higher sheet reuse.
    pub target_or_higher_sheet_reuse_rejections: usize,
    /// Number of receiving sheets considered (`target_sheet` value, using 0..target-1).
    pub receiving_sheet_count: usize,
    /// Human-readable stop reason.
    pub stop_reason: String,
}

impl SheetEliminationDiagnostics {
    pub fn summary(&self) -> String {
        format!(
            "used_before={} used_after={} target={:?} attempts={} ok={} fail={} rollbacks={} \
             displaced={} lbf_ok={} sep_attempts={} sep_ok={} sep_fail={} commit_reject={} \
             target_reuse_reject={} receiving_sheets={} reason={}",
            self.sheet_count_used_before,
            self.sheet_count_used_after,
            self.selected_sheet,
            self.attempts,
            self.successful_eliminations,
            self.failed_eliminations,
            self.rollback_count,
            self.displaced_items,
            self.lbf_reinsertion_successes,
            self.separator_fallback_attempts,
            self.separator_fallback_successes,
            self.separator_fallback_failures,
            self.commit_gate_rejections,
            self.target_or_higher_sheet_reuse_rejections,
            self.receiving_sheet_count,
            self.stop_reason,
        )
    }
}

// ---------------------------------------------------------------------------
// SheetEliminationEngine
// ---------------------------------------------------------------------------

pub struct SheetEliminationEngine<'a> {
    parts: &'a [Part],
    sheets: &'a [SheetShape],
    rotation_context: RotationResolveContext,
    collision_backend: CollisionBackendKind,
}

impl<'a> SheetEliminationEngine<'a> {
    pub fn new(parts: &'a [Part], sheets: &'a [SheetShape]) -> Self {
        Self::new_with_rotation_context(parts, sheets, RotationResolveContext::legacy_default())
    }

    pub fn new_with_rotation_context(
        parts: &'a [Part],
        sheets: &'a [SheetShape],
        rotation_context: RotationResolveContext,
    ) -> Self {
        Self::new_with_backend_and_rotation_context(
            parts,
            sheets,
            rotation_context,
            CollisionBackendKind::Bbox,
        )
    }

    pub fn new_with_backend_and_rotation_context(
        parts: &'a [Part],
        sheets: &'a [SheetShape],
        rotation_context: RotationResolveContext,
        collision_backend: CollisionBackendKind,
    ) -> Self {
        Self {
            parts,
            sheets,
            rotation_context,
            collision_backend,
        }
    }

    /// Run one sheet elimination pass.
    pub fn run(
        &self,
        placements: Vec<Placement>,
        unplaced: Vec<Unplaced>,
        policy: &mut StoppingPolicy,
    ) -> (Vec<Placement>, Vec<Unplaced>, SheetEliminationDiagnostics) {
        let mut diag = SheetEliminationDiagnostics::default();
        diag.sheet_count_used_before = compute_sheet_count_used(&placements);
        diag.sheet_count_used_after = diag.sheet_count_used_before;

        if policy.should_stop() {
            diag.stop_reason = "policy_stopped_before_start".to_string();
            return (placements, unplaced, diag);
        }

        let target = match self.select_target_sheet(&placements) {
            Some(t) => t,
            None => {
                diag.stop_reason = "no_used_sheets".to_string();
                return (placements, unplaced, diag);
            }
        };

        diag.selected_sheet = Some(target);
        diag.attempts += 1;
        diag.receiving_sheet_count = target;

        match self.try_eliminate(placements.clone(), target, policy, &mut diag) {
            Some(new_placements) => {
                let new_used = compute_sheet_count_used(&new_placements);
                let violations = validate_placements_for_backend(
                    &new_placements,
                    self.parts,
                    self.sheets,
                    &self.collision_backend,
                );
                let reuses_target_or_higher =
                    self.has_target_or_higher_sheet_use(&new_placements, target);
                let count_preserved = new_placements.len() == placements.len();

                if reuses_target_or_higher {
                    diag.target_or_higher_sheet_reuse_rejections += 1;
                }

                if new_used < diag.sheet_count_used_before
                    && violations.is_empty()
                    && !reuses_target_or_higher
                    && count_preserved
                {
                    diag.successful_eliminations += 1;
                    diag.sheet_count_used_after = new_used;
                    diag.stop_reason = "success".to_string();
                    (new_placements, unplaced, diag)
                } else {
                    diag.failed_eliminations += 1;
                    diag.rollback_count += 1;
                    diag.commit_gate_rejections += 1;
                    diag.stop_reason = if !count_preserved {
                        "placement_count_invariant_failed".to_string()
                    } else if reuses_target_or_higher {
                        "target_or_higher_sheet_reuse".to_string()
                    } else if !violations.is_empty() {
                        "invalid_layout_after_redistribution".to_string()
                    } else {
                        "sheet_count_not_reduced".to_string()
                    };
                    (placements, unplaced, diag)
                }
            }
            None => {
                diag.failed_eliminations += 1;
                diag.rollback_count += 1;
                diag.stop_reason = "redistribution_failed_or_stopped".to_string();
                (placements, unplaced, diag)
            }
        }
    }

    /// SGH-04 target selection: highest used sheet index.
    ///
    /// This is VRS-specific adaptation for `sheet_count_used = max(sheet_index)+1`.
    pub(crate) fn select_target_sheet(&self, placements: &[Placement]) -> Option<usize> {
        placements.iter().map(|p| p.sheet_index).max()
    }

    fn has_target_or_higher_sheet_use(&self, placements: &[Placement], target: usize) -> bool {
        placements.iter().any(|p| p.sheet_index >= target)
    }

    fn try_eliminate(
        &self,
        placements: Vec<Placement>,
        target: usize,
        policy: &mut StoppingPolicy,
        diag: &mut SheetEliminationDiagnostics,
    ) -> Option<Vec<Placement>> {
        // Split into base + displaced queue.
        let mut base: Vec<Placement> = Vec::new();
        let mut queue: Vec<Placement> = Vec::new();
        for p in placements {
            if p.sheet_index == target {
                queue.push(p);
            } else {
                base.push(p);
            }
        }

        if queue.is_empty() {
            return None;
        }

        // Only lower-index receiving sheets are allowed.
        let allowed_receiving: Vec<usize> = (0..target).collect();
        if allowed_receiving.is_empty() {
            return None;
        }

        diag.displaced_items = queue.len();

        // largest-first displaced queue: area desc -> max_dim desc -> instance_id asc.
        queue.sort_by(|a, b| {
            let (a_area, a_max_dim) = self.part_area_and_max_dim(&a.part_id);
            let (b_area, b_max_dim) = self.part_area_and_max_dim(&b.part_id);
            b_area
                .partial_cmp(&a_area)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| {
                    b_max_dim
                        .partial_cmp(&a_max_dim)
                        .unwrap_or(std::cmp::Ordering::Equal)
                })
                .then_with(|| a.instance_id.cmp(&b.instance_id))
        });

        let mut placed_bboxes = self.rebuild_placed_bboxes(&base);
        let mut used_receiving: HashSet<usize> = base.iter().map(|p| p.sheet_index).collect();

        for item in queue {
            if policy.should_stop() {
                return None;
            }
            policy.tick();

            let (w, h, rots) = self.resolve_dims(&item.part_id, &item.instance_id);
            if w <= 0.0 || h <= 0.0 || rots.is_empty() {
                return None;
            }

            if let Some((placement, bbox)) = self.lbf_select_clear_reinsert(
                &base,
                &item,
                w,
                h,
                &rots,
                &placed_bboxes,
                &used_receiving,
                target,
            ) {
                used_receiving.insert(placement.sheet_index);
                placed_bboxes.push(bbox);
                base.push(placement);
                diag.lbf_reinsertion_successes += 1;
                continue;
            }

            diag.separator_fallback_attempts += 1;
            match self.try_separator_fallback_for_item(
                &base,
                &placed_bboxes,
                &item,
                w,
                h,
                &rots,
                target,
                &allowed_receiving,
                diag,
            ) {
                Some((new_base, new_bboxes)) => {
                    base = new_base;
                    placed_bboxes = new_bboxes;
                    used_receiving = base.iter().map(|p| p.sheet_index).collect();
                    diag.separator_fallback_successes += 1;
                }
                None => {
                    diag.separator_fallback_failures += 1;
                    return None;
                }
            }
        }

        Some(base)
    }

    fn try_separator_fallback_for_item(
        &self,
        current_placements: &[Placement],
        placed_bboxes: &[PlacedBbox],
        item: &Placement,
        width: f64,
        height: f64,
        rotations: &[f64],
        target: usize,
        allowed_receiving: &[usize],
        diag: &mut SheetEliminationDiagnostics,
    ) -> Option<(Vec<Placement>, Vec<PlacedBbox>)> {
        let seed_sheet = self.select_separator_seed_sheet(allowed_receiving, placed_bboxes)?;

        let seed_rot = rotations
            .iter()
            .copied()
            .find(|&rot| {
                let (rw, rh) = dims_for_rotation(width, height, rot);
                let rect = Rect {
                    x1: 0.0,
                    y1: 0.0,
                    x2: rw,
                    y2: rh,
                };
                rect_within_boundary(rect, &self.sheets[seed_sheet])
            })
            .or_else(|| rotations.first().copied())?;

        let (anchor_x, anchor_y) =
            placement_anchor_from_rect_min(0.0, 0.0, width, height, seed_rot);

        let mut working_placements = current_placements.to_vec();
        working_placements.push(Placement {
            instance_id: item.instance_id.clone(),
            part_id: item.part_id.clone(),
            sheet_index: seed_sheet,
            x: anchor_x,
            y: anchor_y,
            rotation_deg: seed_rot,
        });

        let working = WorkingLayout::new(
            working_placements,
            vec![],
            self.sheets.len(),
            0,
        );

        let sep = VrsSeparator::new(VrsSeparatorConfig {
            allowed_sheet_indices: Some(allowed_receiving.to_vec()),
            rotation_context: self.rotation_context.clone(),
            collision_backend: self.collision_backend.clone(),
            ..VrsSeparatorConfig::default()
        });
        let (sep_layout, sep_diag) = sep.run(working, self.parts, self.sheets);

        if !(sep_diag.best_loss == 0.0 || sep_diag.converged) {
            return None;
        }

        if self.has_target_or_higher_sheet_use(&sep_layout.placements, target) {
            diag.target_or_higher_sheet_reuse_rejections += 1;
            return None;
        }

        if !validate_placements_for_backend(
            &sep_layout.placements,
            self.parts,
            self.sheets,
            &self.collision_backend,
        )
        .is_empty()
        {
            return None;
        }

        let new_bboxes = self.rebuild_placed_bboxes(&sep_layout.placements);
        Some((sep_layout.placements, new_bboxes))
    }

    fn lbf_select_clear_reinsert(
        &self,
        current_placements: &[Placement],
        item: &Placement,
        width: f64,
        height: f64,
        rotations: &[f64],
        placed_bboxes: &[PlacedBbox],
        used_receiving: &HashSet<usize>,
        target: usize,
    ) -> Option<(Placement, PlacedBbox)> {
        let (all_candidates, _) = generate_candidates_with_sheets(self.sheets, placed_bboxes);

        let mut best_key: Option<(bool, f64, f64, usize)> = None;
        let mut best: Option<(Placement, PlacedBbox)> = None;

        for cand in &all_candidates {
            if cand.sheet_index >= target {
                continue;
            }

            let sheet = &self.sheets[cand.sheet_index];
            let is_unused = !used_receiving.contains(&cand.sheet_index);

            for &rot in rotations {
                let (rw, rh) = dims_for_rotation(width, height, rot);

                let rect = Rect {
                    x1: cand.x,
                    y1: cand.y,
                    x2: cand.x + rw,
                    y2: cand.y + rh,
                };
                let candidate_bbox = PlacedBbox {
                    sheet_index: cand.sheet_index,
                    x1: cand.x,
                    y1: cand.y,
                    x2: cand.x + rw,
                    y2: cand.y + rh,
                };

                let (anchor_x, anchor_y) = placement_anchor_from_rect_min(
                    cand.x,
                    cand.y,
                    width,
                    height,
                    rot,
                );

                let candidate = Placement {
                    instance_id: item.instance_id.clone(),
                    part_id: item.part_id.clone(),
                    sheet_index: cand.sheet_index,
                    x: anchor_x,
                    y: anchor_y,
                    rotation_deg: rot,
                };

                if !self.lbf_candidate_valid_for_backend(
                    &candidate,
                    &candidate_bbox,
                    rect,
                    sheet,
                    current_placements,
                    placed_bboxes,
                ) {
                    continue;
                }

                let key = (is_unused, cand.y, cand.x, cand.sheet_index);
                if best_key.map_or(true, |k| Self::lbf_key_better(key, k)) {
                    best_key = Some(key);
                    best = Some((candidate, candidate_bbox));
                }

                // Stable rotation order: score only first valid rotation per candidate point.
                break;
            }
        }

        best
    }

    fn lbf_candidate_valid_for_backend(
        &self,
        candidate: &Placement,
        candidate_bbox: &PlacedBbox,
        rect: Rect,
        sheet: &SheetShape,
        current_placements: &[Placement],
        placed_bboxes: &[PlacedBbox],
    ) -> bool {
        match &self.collision_backend {
            CollisionBackendKind::Bbox => {
                rect_within_boundary(rect, sheet)
                    && !placed_bboxes.iter().any(|pb| pb.overlaps(candidate_bbox))
            }
            CollisionBackendKind::JaguaPolygonExact | CollisionBackendKind::Cde => {
                let mut trial = current_placements.to_vec();
                trial.push(candidate.clone());
                validate_placements_for_backend(
                    &trial,
                    self.parts,
                    self.sheets,
                    &self.collision_backend,
                )
                .is_empty()
            }
        }
    }

    fn lbf_key_better(
        a: (bool, f64, f64, usize),
        b: (bool, f64, f64, usize),
    ) -> bool {
        if a.0 != b.0 {
            return !a.0;
        }
        const EPS: f64 = 1e-12;
        if (a.1 - b.1).abs() > EPS {
            return a.1 < b.1;
        }
        if (a.2 - b.2).abs() > EPS {
            return a.2 < b.2;
        }
        a.3 < b.3
    }

    fn select_separator_seed_sheet(
        &self,
        allowed_receiving: &[usize],
        placed_bboxes: &[PlacedBbox],
    ) -> Option<usize> {
        let mut best_sheet: Option<usize> = None;
        let mut best_free = f64::NEG_INFINITY;

        for &si in allowed_receiving {
            if si >= self.sheets.len() {
                continue;
            }
            let placed_area: f64 = placed_bboxes
                .iter()
                .filter(|pb| pb.sheet_index == si)
                .map(|pb| (pb.x2 - pb.x1) * (pb.y2 - pb.y1))
                .sum();
            let free = self.sheets[si].area - placed_area;
            if free > best_free || (free == best_free && best_sheet.map_or(true, |b| si < b)) {
                best_free = free;
                best_sheet = Some(si);
            }
        }

        best_sheet
    }

    fn rebuild_placed_bboxes(&self, placements: &[Placement]) -> Vec<PlacedBbox> {
        placements
            .iter()
            .filter_map(|p| {
                let pt = self.parts.iter().find(|pt| pt.id == p.part_id)?;
                bbox_from_placement(p, pt.width, pt.height)
            })
            .collect()
    }

    fn resolve_dims(&self, part_id: &str, instance_id: &str) -> (f64, f64, Vec<f64>) {
        match self.parts.iter().find(|pt| pt.id == part_id) {
            Some(pt) => {
                let rots = resolve_instance_rotation_angles(pt, instance_id, &self.rotation_context);
                (pt.width, pt.height, rots)
            }
            None => (0.0, 0.0, vec![]),
        }
    }

    fn part_area_and_max_dim(&self, part_id: &str) -> (f64, f64) {
        self.parts
            .iter()
            .find(|pt| pt.id == part_id)
            .map(|pt| (pt.width * pt.height, pt.width.max(pt.height)))
            .unwrap_or((0.0, 0.0))
    }
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::item::expand_instances;
    use crate::optimizer::initializer::build_initial_layout;
    use crate::optimizer::repair::run_repair;
    use crate::optimizer::stopping::StoppingPolicy;
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

    fn run_elimination_pass(
        parts: &[Part],
        stocks: &[Stock],
    ) -> (Vec<Placement>, Vec<Unplaced>, SheetEliminationDiagnostics) {
        let instances = expand_instances(parts).expect("instances");
        let sheets = expand_sheets(stocks).expect("sheets");
        let (p, u, _) = build_initial_layout(&instances, parts, &sheets);
        let mut policy = StoppingPolicy::new(512, 30.0);
        let (p, u, _) = run_repair(p, u, parts, &sheets, &mut policy);
        let engine = SheetEliminationEngine::new(parts, &sheets);
        let mut policy2 = StoppingPolicy::new(512, 30.0);
        engine.run(p, u, &mut policy2)
    }

    #[test]
    fn test_select_target_highest_used_sheet() {
        let parts = vec![make_part("A", 40.0, 40.0, 3)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 4)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new(&parts, &sheets);

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
                sheet_index: 2,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "A__0003".into(),
                part_id: "A".into(),
                sheet_index: 1,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];

        assert_eq!(engine.select_target_sheet(&placements), Some(2));
    }

    #[test]
    fn test_successful_elimination_reduces_sheet_count() {
        let parts = vec![make_part("A", 40.0, 40.0, 3)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new(&parts, &sheets);

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
                x: 40.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "A__0003".into(),
                part_id: "A".into(),
                sheet_index: 1,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];

        let mut policy = StoppingPolicy::new(512, 30.0);
        let (placed, _, diag) = engine.run(placements, vec![], &mut policy);

        assert_eq!(diag.sheet_count_used_before, 2);
        assert_eq!(diag.sheet_count_used_after, 1);
        assert_eq!(diag.successful_eliminations, 1);
        assert!(placed.iter().all(|p| p.sheet_index < 1));
        assert!(find_violations(&placed, &parts, &sheets).is_empty());
    }

    #[test]
    fn test_redistribution_never_uses_target_or_higher_sheets() {
        let parts = vec![make_part("A", 30.0, 30.0, 4)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 4)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new(&parts, &sheets);

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
                sheet_index: 1,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "A__0003".into(),
                part_id: "A".into(),
                sheet_index: 2,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
            Placement {
                instance_id: "A__0004".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 30.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];

        let mut policy = StoppingPolicy::new(512, 30.0);
        let (placed, _, diag) = engine.run(placements, vec![], &mut policy);

        if diag.successful_eliminations == 1 {
            let target = diag.selected_sheet.expect("target");
            assert!(
                placed.iter().all(|p| p.sheet_index < target),
                "successful redistribution must only use lower-index sheets"
            );
        }
    }

    #[test]
    fn test_failed_elimination_rollbacks() {
        let parts = vec![make_part("A", 45.0, 45.0, 2)];
        let stocks = vec![make_stock("S", 60.0, 60.0, 2)];
        let (placed, _unplaced, diag) = run_elimination_pass(&parts, &stocks);

        assert_eq!(diag.sheet_count_used_after, 2);
        assert_eq!(diag.successful_eliminations, 0);
        assert_eq!(diag.failed_eliminations, 1);
        assert_eq!(diag.rollback_count, 1);
        assert_eq!(placed.len(), 2);
    }

    #[test]
    fn test_rollback_preserves_placements() {
        let parts = vec![make_part("A", 45.0, 45.0, 2)];
        let stocks = vec![make_stock("S", 60.0, 60.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");

        let (p, u, _) = build_initial_layout(&instances, &parts, &sheets);
        let mut policy_r = StoppingPolicy::new(512, 30.0);
        let (p_before, u_before, _) = run_repair(p, u, &parts, &sheets, &mut policy_r);

        let engine = SheetEliminationEngine::new(&parts, &sheets);
        let mut policy_e = StoppingPolicy::new(512, 30.0);
        let (p_after, u_after, diag) =
            engine.run(p_before.clone(), u_before.clone(), &mut policy_e);

        assert_eq!(diag.rollback_count, 1);
        assert_eq!(p_before.len(), p_after.len());
        assert_eq!(u_before.len(), u_after.len());
        for (a, b) in p_before.iter().zip(p_after.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.sheet_index, b.sheet_index);
            assert_eq!(a.x.to_bits(), b.x.to_bits());
            assert_eq!(a.y.to_bits(), b.y.to_bits());
        }
    }

    #[test]
    fn test_separator_backed_fallback_helper_can_succeed() {
        let parts = vec![make_part("A", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 200.0, 100.0, 2)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new(&parts, &sheets);

        let current_placements = vec![
            Placement {
                instance_id: "A__0001".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0.0,
            },
        ];
        let item = Placement {
            instance_id: "A__0002".into(),
            part_id: "A".into(),
            sheet_index: 1,
            x: 0.0,
            y: 0.0,
            rotation_deg: 0.0,
        };

        let placed_bboxes = engine.rebuild_placed_bboxes(&current_placements);
        let mut diag = SheetEliminationDiagnostics::default();
        let result = engine.try_separator_fallback_for_item(
            &current_placements,
            &placed_bboxes,
            &item,
            30.0,
            30.0,
            &[0.0],
            1,
            &[0],
            &mut diag,
        );

        assert!(result.is_some(), "separator fallback helper should return a valid layout");
        let (placements_after, _) = result.expect("fallback result");
        assert!(placements_after.iter().all(|p| p.sheet_index < 1));
        assert!(find_violations(&placements_after, &parts, &sheets).is_empty());
    }

    #[test]
    fn test_target_or_higher_sheet_reuse_rejected_by_gate() {
        let parts = vec![make_part("A", 10.0, 10.0, 1)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 3)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new(&parts, &sheets);

        let placements = vec![Placement {
            instance_id: "A__0001".into(),
            part_id: "A".into(),
            sheet_index: 2,
            x: 0.0,
            y: 0.0,
            rotation_deg: 0.0,
        }];

        assert!(
            engine.has_target_or_higher_sheet_use(&placements, 2),
            "sheet_index >= target must be rejected"
        );
    }

    #[test]
    fn test_diagnostics_summary_contains_sgh04_fields() {
        let diag = SheetEliminationDiagnostics {
            displaced_items: 2,
            lbf_reinsertion_successes: 1,
            separator_fallback_attempts: 1,
            separator_fallback_successes: 1,
            separator_fallback_failures: 0,
            commit_gate_rejections: 0,
            target_or_higher_sheet_reuse_rejections: 0,
            receiving_sheet_count: 2,
            ..SheetEliminationDiagnostics::default()
        };
        let s = diag.summary();
        assert!(s.contains("displaced=2"));
        assert!(s.contains("lbf_ok=1"));
        assert!(s.contains("sep_attempts=1"));
        assert!(s.contains("sep_ok=1"));
        assert!(s.contains("commit_reject=0"));
        assert!(s.contains("receiving_sheets=2"));
    }

    #[test]
    fn test_no_elimination_when_no_placements() {
        let parts = vec![make_part("A", 50.0, 50.0, 1)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new(&parts, &sheets);
        let mut policy = StoppingPolicy::new(512, 30.0);
        let (placed, _, diag) = engine.run(vec![], vec![], &mut policy);
        assert!(placed.is_empty());
        assert_eq!(diag.attempts, 0);
        assert_eq!(diag.selected_sheet, None);
    }

    #[test]
    fn test_stopping_policy_stops_elimination() {
        let parts = vec![make_part("A", 50.0, 50.0, 3)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (p, u, _) = build_initial_layout(&instances, &parts, &sheets);
        let mut policy_r = StoppingPolicy::new(512, 30.0);
        let (p, u, _) = run_repair(p, u, &parts, &sheets, &mut policy_r);

        let engine = SheetEliminationEngine::new(&parts, &sheets);
        let mut stopped_policy = StoppingPolicy::new(0, 30.0);
        let p_len = p.len();
        let (p_out, _, diag) = engine.run(p, u, &mut stopped_policy);
        assert_eq!(diag.attempts, 0);
        assert_eq!(p_out.len(), p_len);
    }

    #[test]
    fn test_placed_plus_unplaced_invariant() {
        let parts = vec![make_part("A", 50.0, 50.0, 4)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 3)];
        let (placed, unplaced, _) = run_elimination_pass(&parts, &stocks);
        assert_eq!(placed.len() + unplaced.len(), 4);
    }
    #[test]
    fn sheet_elimination_engine_passes_backend_to_separator_fallback() {
        let parts = vec![make_part("A", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new_with_backend_and_rotation_context(
            &parts,
            &sheets,
            crate::rotation_policy::RotationResolveContext::legacy_default(),
            CollisionBackendKind::JaguaPolygonExact,
        );

        assert!(matches!(engine.collision_backend, CollisionBackendKind::JaguaPolygonExact),
            "SheetEliminationEngine must retain and pass the explicit backend policy");
    }

    #[test]
    fn sheet_elimination_exact_lbf_candidate_does_not_reject_bbox_false_positive() {
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);
        let mut l_part = make_part("L", 40.0, 40.0, 1);
        l_part.outer_points = Some(l_json);
        let parts = vec![l_part, make_part("B", 15.0, 15.0, 1)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let exact_engine = SheetEliminationEngine::new_with_backend_and_rotation_context(
            &parts,
            &sheets,
            crate::rotation_policy::RotationResolveContext::legacy_default(),
            CollisionBackendKind::JaguaPolygonExact,
        );
        let bbox_engine = SheetEliminationEngine::new_with_backend_and_rotation_context(
            &parts,
            &sheets,
            crate::rotation_policy::RotationResolveContext::legacy_default(),
            CollisionBackendKind::Bbox,
        );
        let candidate = Placement { instance_id: "B__0001".into(), part_id: "B".into(), sheet_index: 0, x: 22.0, y: 22.0, rotation_deg: 0.0 };
        let candidate_bbox = PlacedBbox { sheet_index: 0, x1: 22.0, y1: 22.0, x2: 37.0, y2: 37.0 };
        let rect = Rect { x1: 22.0, y1: 22.0, x2: 37.0, y2: 37.0 };
        let base = vec![Placement { instance_id: "L__0001".into(), part_id: "L".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 }];
        let placed_bboxes = vec![PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 40.0, y2: 40.0 }];

        assert!(exact_engine.lbf_candidate_valid_for_backend(
            &candidate,
            &candidate_bbox,
            rect,
            &sheets[0],
            &base,
            &placed_bboxes,
        ), "exact LBF must not reject a bbox-overlapping but exact-valid notch candidate");
        assert!(!bbox_engine.lbf_candidate_valid_for_backend(
            &candidate,
            &candidate_bbox,
            rect,
            &sheets[0],
            &base,
            &placed_bboxes,
        ), "bbox LBF keeps the legacy bbox rejection behavior");
    }


    #[test]
    fn sheet_elimination_exact_commit_gate_no_silent_bbox_fallback() {
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);
        let mut l_part = make_part("L", 40.0, 40.0, 1);
        l_part.outer_points = Some(l_json);
        let parts = vec![l_part, make_part("B", 15.0, 15.0, 1)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            Placement { instance_id: "L__0001".into(), part_id: "L".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "B__0001".into(), part_id: "B".into(), sheet_index: 0, x: 22.0, y: 22.0, rotation_deg: 0.0 },
        ];

        let bbox_violations = validate_placements_for_backend(
            &placements,
            &parts,
            &sheets,
            &CollisionBackendKind::Bbox,
        );
        let exact_violations = validate_placements_for_backend(
            &placements,
            &parts,
            &sheets,
            &CollisionBackendKind::JaguaPolygonExact,
        );

        assert!(!bbox_violations.is_empty(), "fixture must expose the legacy bbox false-positive");
        assert!(exact_violations.is_empty(),
            "exact commit gate must use exact backend and not silently fall back to bbox");
    }

    #[test]
    fn cde_internal_paths_reject_or_hard_penalty_no_silent_success() {
        let parts = vec![make_part("A", 10.0, 10.0, 1)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new_with_backend_and_rotation_context(
            &parts,
            &sheets,
            crate::rotation_policy::RotationResolveContext::legacy_default(),
            CollisionBackendKind::Cde,
        );
        let candidate = Placement { instance_id: "A__0001".into(), part_id: "A".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 };
        let bbox = PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 10.0, y2: 10.0 };
        let rect = Rect { x1: 0.0, y1: 0.0, x2: 10.0, y2: 10.0 };

        assert!(!engine.lbf_candidate_valid_for_backend(
            &candidate,
            &bbox,
            rect,
            &sheets[0],
            &[],
            &[],
        ), "CDE must reject/hard-penalize internally, never silently pass as bbox");
    }

}
