//! Sheet Elimination V1 — post-repair sheet count reduction pass.
//!
//! Strategy: snapshot → select weakest used sheet → remove its items → try to
//! reinsert them on the remaining sheets → exact/violation gate → commit or rollback.
//!
//! # Weakest sheet rule (V1, deterministic)
//! 1. Only used sheets (sheets that appear in `placements`) are candidates.
//! 2. Primary key: lowest total placed area on the sheet.
//! 3. Secondary key: lowest placed count.
//! 4. Tie-break: highest sheet_index — preferred under the max+1 `sheet_count_used`
//!    contract, because eliminating the highest-index used sheet always decreases
//!    `sheet_count_used` by exactly 1.
//!
//! # Rollback guarantee
//! Every elimination attempt either:
//! - Commits: all items reinserted, no violations, `sheet_count_used` decreased; or
//! - Rolls back: original `placements`/`unplaced` returned unchanged.
//!
//! Determinism: all decisions (sheet selection, reinsert order, candidate order)
//! are deterministic; no RNG.

use crate::geometry::Rect;
use crate::io::{Placement, Unplaced};
use crate::item::{dims_for_rotation, normalize_allowed_rotations, placement_anchor_from_rect_min, Part};
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::{generate_candidates_with_sheets, PlacedBbox};
use super::initializer::bbox_from_placement;
use super::multisheet::compute_sheet_count_used;
use super::repair::find_violations;
use super::stopping::StoppingPolicy;

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
    /// Number of elimination attempts made (0 or 1 in V1).
    pub attempts: usize,
    /// Number of successful eliminations (sheet_count_used decreased, layout valid).
    pub successful_eliminations: usize,
    /// Number of failed eliminations (triggered rollback).
    pub failed_eliminations: usize,
    /// Number of rollbacks executed.
    pub rollback_count: usize,
    /// Human-readable stop reason.
    pub stop_reason: String,
}

impl SheetEliminationDiagnostics {
    pub fn summary(&self) -> String {
        format!(
            "used_before={} used_after={} target={:?} attempts={} ok={} fail={} rollbacks={} reason={}",
            self.sheet_count_used_before,
            self.sheet_count_used_after,
            self.selected_sheet,
            self.attempts,
            self.successful_eliminations,
            self.failed_eliminations,
            self.rollback_count,
            self.stop_reason,
        )
    }
}

// ---------------------------------------------------------------------------
// SheetEliminationEngine
// ---------------------------------------------------------------------------

/// Sheet Elimination V1 engine.
///
/// Runs at most one elimination attempt per call: selects the weakest used sheet,
/// removes its items, tries to reinsert them on the remaining sheets, then commits
/// only when all three gates pass:
///   1. All removed items successfully reinserted.
///   2. No violations in the new layout (`find_violations` returns empty).
///   3. `sheet_count_used` strictly decreased.
/// On any failure, rolls back to the original snapshot.
pub struct SheetEliminationEngine<'a> {
    parts: &'a [Part],
    sheets: &'a [SheetShape],
}

impl<'a> SheetEliminationEngine<'a> {
    pub fn new(parts: &'a [Part], sheets: &'a [SheetShape]) -> Self {
        Self { parts, sheets }
    }

    /// Run one sheet elimination pass.
    ///
    /// Returns `(placements, unplaced, diagnostics)`. The placements are either
    /// improved (fewer sheets used) or byte-identical to the input (rollback).
    /// The `placed.len() + unplaced.len()` invariant is always preserved.
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

        // Clone for rollback snapshot; original `placements` is the rollback state.
        match self.try_eliminate(placements.clone(), target, policy) {
            Some(new_placements) => {
                let new_used = compute_sheet_count_used(&new_placements);
                let violations = find_violations(&new_placements, self.parts, self.sheets);
                if new_used < diag.sheet_count_used_before && violations.is_empty() {
                    // Commit gate passed.
                    diag.successful_eliminations += 1;
                    diag.sheet_count_used_after = new_used;
                    diag.stop_reason = "success".to_string();
                    (new_placements, unplaced, diag)
                } else {
                    // Commit gate failed — rollback to original snapshot.
                    diag.failed_eliminations += 1;
                    diag.rollback_count += 1;
                    diag.stop_reason = if !violations.is_empty() {
                        "invalid_layout_after_reinsert".to_string()
                    } else {
                        "sheet_count_not_reduced".to_string()
                    };
                    (placements, unplaced, diag)
                }
            }
            None => {
                diag.failed_eliminations += 1;
                diag.rollback_count += 1;
                diag.stop_reason = "reinsert_failed_or_stopped".to_string();
                (placements, unplaced, diag)
            }
        }
    }

    /// Select the weakest used sheet for elimination attempt.
    ///
    /// Only sheets that have at least one placement are considered.
    /// Sorted by: placed_area ASC → placed_count ASC → sheet_index DESC.
    pub(crate) fn select_target_sheet(&self, placements: &[Placement]) -> Option<usize> {
        let used = compute_sheet_count_used(placements);
        if used == 0 {
            return None;
        }

        // Build (sheet_index, total_area, placed_count) for each used slot.
        let mut candidates: Vec<(usize, f64, usize)> = Vec::new();
        for idx in 0..used {
            let count = placements.iter().filter(|p| p.sheet_index == idx).count();
            if count == 0 {
                continue;
            }
            let area: f64 = placements
                .iter()
                .filter(|p| p.sheet_index == idx)
                .filter_map(|p| {
                    self.parts
                        .iter()
                        .find(|pt| pt.id == p.part_id)
                        .and_then(|pt| bbox_from_placement(p, pt.width, pt.height))
                        .map(|bb| (bb.x2 - bb.x1) * (bb.y2 - bb.y1))
                })
                .sum();
            candidates.push((idx, area, count));
        }

        if candidates.is_empty() {
            return None;
        }

        // Sort: placed_area ASC → placed_count ASC → sheet_index DESC.
        candidates.sort_by(|a, b| {
            a.1.partial_cmp(&b.1)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.2.cmp(&b.2))
                .then_with(|| b.0.cmp(&a.0)) // highest index first on tie
        });

        Some(candidates[0].0)
    }

    /// Try to move all items from `target` sheet to other sheets.
    ///
    /// Returns `Some(new_placements)` if all items were reinserted to non-target
    /// sheets, `None` if any item could not be placed or the policy stopped.
    fn try_eliminate(
        &self,
        placements: Vec<Placement>,
        target: usize,
        policy: &mut StoppingPolicy,
    ) -> Option<Vec<Placement>> {
        // Split into base (stay) and queue (reinsert to non-target sheets).
        let mut base: Vec<Placement> = Vec::new();
        let mut queue: Vec<Placement> = Vec::new();
        for p in placements {
            if p.sheet_index == target {
                queue.push(p);
            } else {
                base.push(p);
            }
        }

        // Sort queue deterministically: area desc → instance_id asc.
        queue.sort_by(|a, b| {
            let area_of = |p: &Placement| {
                self.parts
                    .iter()
                    .find(|pt| pt.id == p.part_id)
                    .map(|pt| pt.width * pt.height)
                    .unwrap_or(0.0)
            };
            area_of(b)
                .partial_cmp(&area_of(a))
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| a.instance_id.cmp(&b.instance_id))
        });

        // Build bboxes from base placements as starting collision context.
        let mut placed_bboxes: Vec<PlacedBbox> = Vec::new();
        for p in &base {
            if let Some(pt) = self.parts.iter().find(|pt| pt.id == p.part_id) {
                if let Some(bbox) = bbox_from_placement(p, pt.width, pt.height) {
                    placed_bboxes.push(bbox);
                }
            }
        }

        // Try to reinsert each queued item on non-target sheets.
        for item_p in queue {
            if policy.should_stop() {
                return None;
            }
            policy.tick();

            let (w, h, rots) = self.resolve_dims(&item_p.part_id);
            if w <= 0.0 || h <= 0.0 || rots.is_empty() {
                return None;
            }

            // Generate candidates across all sheets, then exclude the target.
            let (all_candidates, _) = generate_candidates_with_sheets(self.sheets, &placed_bboxes);
            let candidates: Vec<_> = all_candidates
                .into_iter()
                .filter(|c| c.sheet_index != target)
                .collect();

            let mut placed_this = false;
            'cand: for candidate in &candidates {
                let sheet = &self.sheets[candidate.sheet_index];
                for &rot in &rots {
                    let Some((rw, rh)) = dims_for_rotation(w, h, rot) else {
                        continue;
                    };
                    let rect = Rect {
                        x1: candidate.x,
                        y1: candidate.y,
                        x2: candidate.x + rw,
                        y2: candidate.y + rh,
                    };
                    if !rect_within_boundary(rect, sheet) {
                        continue;
                    }
                    let candidate_bbox = PlacedBbox {
                        sheet_index: candidate.sheet_index,
                        x1: candidate.x,
                        y1: candidate.y,
                        x2: candidate.x + rw,
                        y2: candidate.y + rh,
                    };
                    if placed_bboxes.iter().any(|pb| pb.overlaps(&candidate_bbox)) {
                        continue;
                    }
                    let Some((anchor_x, anchor_y)) = placement_anchor_from_rect_min(
                        candidate.x,
                        candidate.y,
                        w,
                        h,
                        rot,
                    ) else {
                        continue;
                    };
                    placed_bboxes.push(candidate_bbox);
                    base.push(Placement {
                        instance_id: item_p.instance_id.clone(),
                        part_id: item_p.part_id.clone(),
                        sheet_index: candidate.sheet_index,
                        x: anchor_x,
                        y: anchor_y,
                        rotation_deg: rot,
                    });
                    placed_this = true;
                    break 'cand;
                }
            }

            if !placed_this {
                return None;
            }
        }

        Some(base)
    }

    fn resolve_dims(&self, part_id: &str) -> (f64, f64, Vec<i64>) {
        match self.parts.iter().find(|pt| pt.id == part_id) {
            Some(pt) => {
                let rots =
                    normalize_allowed_rotations(&pt.allowed_rotations_deg).unwrap_or_default();
                (pt.width, pt.height, rots)
            }
            None => (0.0, 0.0, vec![]),
        }
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
        }
    }

    fn make_placement(instance_id: &str, part_id: &str, sheet_index: usize) -> Placement {
        Placement {
            instance_id: instance_id.to_string(),
            part_id: part_id.to_string(),
            sheet_index,
            x: 0.0,
            y: 0.0,
            rotation_deg: 0,
        }
    }

    /// Build layout via construction+repair only (no elimination), then run elimination.
    /// This avoids double-elimination since MultiSheetManager now calls elimination internally.
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

    // -----------------------------------------------------------------------
    // Weakest sheet selection
    // -----------------------------------------------------------------------

    #[test]
    fn test_select_target_weakest_by_area() {
        // Sheet 0: 1 × 80×80 (area 6400); sheet 1: 1 × 30×30 (area 900).
        // Should select sheet 1 (lower area).
        let parts = vec![make_part("A", 80.0, 80.0, 1), make_part("B", 30.0, 30.0, 1)];
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
                rotation_deg: 0,
            },
            Placement {
                instance_id: "B__0001".into(),
                part_id: "B".into(),
                sheet_index: 1,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0,
            },
        ];
        assert_eq!(
            engine.select_target_sheet(&placements),
            Some(1),
            "should select sheet 1 (lower placed area)"
        );
    }

    #[test]
    fn test_select_target_tiebreak_highest_index() {
        // 3 sheets, each with 1 × 40×40 item (same area, same count).
        // Tie-break: highest sheet_index → sheet 2.
        let parts = vec![make_part("A", 40.0, 40.0, 3)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 3)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new(&parts, &sheets);

        let placements = vec![
            make_placement("A__0001", "A", 0),
            make_placement("A__0002", "A", 1),
            make_placement("A__0003", "A", 2),
        ];
        assert_eq!(
            engine.select_target_sheet(&placements),
            Some(2),
            "tie-break: prefer highest sheet_index"
        );
    }

    // -----------------------------------------------------------------------
    // Successful elimination
    // -----------------------------------------------------------------------

    #[test]
    fn test_successful_elimination_reduces_sheet_count() {
        // Directly construct a valid 2-sheet layout and verify the engine consolidates it.
        //
        // Layout: A__0001(sh0,0,0), A__0002(sh0,40,0), A__0003(sh1,0,0) — all 40×40 items.
        // sh0 free space at (0,40): 0+40=40≤100, 40+40=80≤100 → A__0003 can move there.
        // Expected: elimination selects sh1 (1 item, lower area), reinserts at (0,40), commits.
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
                rotation_deg: 0,
            },
            Placement {
                instance_id: "A__0002".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 40.0,
                y: 0.0,
                rotation_deg: 0,
            },
            Placement {
                instance_id: "A__0003".into(),
                part_id: "A".into(),
                sheet_index: 1,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0,
            },
        ];

        let mut policy = StoppingPolicy::new(512, 30.0);
        let (placed, _, diag) = engine.run(placements, vec![], &mut policy);

        assert_eq!(diag.sheet_count_used_before, 2);
        assert_eq!(diag.sheet_count_used_after, 1, "elimination must reduce sheet count to 1");
        assert_eq!(diag.successful_eliminations, 1);
        assert_eq!(diag.failed_eliminations, 0);
        assert!(
            placed.iter().all(|p| p.sheet_index == 0),
            "all items should be on sheet 0 after elimination"
        );
    }

    // -----------------------------------------------------------------------
    // Failed elimination and rollback
    // -----------------------------------------------------------------------

    #[test]
    fn test_failed_elimination_rollbacks() {
        // 2 stocks × 60×60, 2 items × 45×45.
        // 45+45=90 > 60 → only 1 item fits per sheet.
        // Elimination of sheet 1 fails: item can't fit on full sheet 0.
        let parts = vec![make_part("A", 45.0, 45.0, 2)];
        let stocks = vec![make_stock("S", 60.0, 60.0, 2)];
        let (placed, _unplaced, diag) = run_elimination_pass(&parts, &stocks);

        assert_eq!(diag.sheet_count_used_after, 2, "rollback: sheet count unchanged");
        assert_eq!(diag.successful_eliminations, 0);
        assert_eq!(diag.failed_eliminations, 1);
        assert_eq!(diag.rollback_count, 1);
        assert_eq!(placed.len(), 2, "placement count unchanged after rollback");
    }

    #[test]
    fn test_rollback_preserves_placements() {
        // Verify that after a failed elimination, placements are byte-identical to input.
        let parts = vec![make_part("A", 45.0, 45.0, 2)];
        let stocks = vec![make_stock("S", 60.0, 60.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");

        // Build pre-elimination state via construction+repair only.
        let (p, u, _) = build_initial_layout(&instances, &parts, &sheets);
        let mut policy_r = StoppingPolicy::new(512, 30.0);
        let (p_before, u_before, _) = run_repair(p, u, &parts, &sheets, &mut policy_r);

        // Run elimination (should fail and rollback).
        let engine = SheetEliminationEngine::new(&parts, &sheets);
        let mut policy_e = StoppingPolicy::new(512, 30.0);
        let (p_after, u_after, diag) = engine.run(p_before.clone(), u_before.clone(), &mut policy_e);

        assert_eq!(diag.rollback_count, 1, "rollback must have occurred");
        assert_eq!(p_before.len(), p_after.len(), "placed count preserved after rollback");
        assert_eq!(u_before.len(), u_after.len(), "unplaced count preserved after rollback");
        for (a, b) in p_before.iter().zip(p_after.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.sheet_index, b.sheet_index);
            assert_eq!(a.x.to_bits(), b.x.to_bits());
            assert_eq!(a.y.to_bits(), b.y.to_bits());
        }
    }

    // -----------------------------------------------------------------------
    // Edge cases and gates
    // -----------------------------------------------------------------------

    #[test]
    fn test_no_elimination_when_no_placements() {
        let parts = vec![make_part("A", 50.0, 50.0, 1)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new(&parts, &sheets);
        let mut policy = StoppingPolicy::new(512, 30.0);
        let (placed, _, diag) = engine.run(vec![], vec![], &mut policy);
        assert!(placed.is_empty());
        assert_eq!(diag.attempts, 0, "no attempt if no placements");
        assert_eq!(diag.selected_sheet, None);
        assert_eq!(diag.successful_eliminations, 0);
    }

    #[test]
    fn test_stopping_policy_stops_elimination() {
        // Build layout via construction+repair, then run elimination with stopped policy.
        let parts = vec![make_part("A", 50.0, 50.0, 3)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let instances = expand_instances(&parts).expect("instances");
        let sheets = expand_sheets(&stocks).expect("sheets");
        let (p, u, _) = build_initial_layout(&instances, &parts, &sheets);
        let mut policy_r = StoppingPolicy::new(512, 30.0);
        let (p, u, _) = run_repair(p, u, &parts, &sheets, &mut policy_r);

        // max_iterations=0 → should_stop() returns true immediately.
        let engine = SheetEliminationEngine::new(&parts, &sheets);
        let mut stopped_policy = StoppingPolicy::new(0, 30.0);
        let p_len = p.len();
        let (p_out, _, diag) = engine.run(p, u, &mut stopped_policy);
        assert_eq!(diag.attempts, 0, "no attempt if policy already stopped");
        assert_eq!(p_out.len(), p_len, "placements unchanged");
        assert_eq!(diag.successful_eliminations, 0);
    }

    #[test]
    fn test_invalid_layout_not_success() {
        // A single-sheet layout (sheet_count_used=1) cannot reduce further via elimination.
        // The engine attempts to eliminate sheet 0 but reinsert has no non-target sheets →
        // try_eliminate returns None → rollback → successful_eliminations=0.
        let parts = vec![make_part("A", 50.0, 50.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let engine = SheetEliminationEngine::new(&parts, &sheets);

        let placements = vec![
            Placement {
                instance_id: "A__0001".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 0.0,
                y: 0.0,
                rotation_deg: 0,
            },
            Placement {
                instance_id: "A__0002".into(),
                part_id: "A".into(),
                sheet_index: 0,
                x: 50.0,
                y: 0.0,
                rotation_deg: 0,
            },
        ];
        let mut policy = StoppingPolicy::new(512, 30.0);
        let (out, _, diag) = engine.run(placements.clone(), vec![], &mut policy);
        assert_eq!(diag.successful_eliminations, 0, "no valid reduction possible");
        assert_eq!(out.len(), placements.len(), "placements unchanged");
    }

    #[test]
    fn test_placed_plus_unplaced_invariant() {
        // Total item count must be preserved regardless of elimination outcome.
        let parts = vec![make_part("A", 50.0, 50.0, 4)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 3)];
        let (placed, unplaced, _) = run_elimination_pass(&parts, &stocks);
        assert_eq!(placed.len() + unplaced.len(), 4, "invariant: total == 4");
    }

    #[test]
    fn test_deterministic_two_runs() {
        let parts = vec![make_part("A", 50.0, 50.0, 3)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 2)];
        let (p1, u1, _) = run_elimination_pass(&parts, &stocks);
        let (p2, u2, _) = run_elimination_pass(&parts, &stocks);

        assert_eq!(p1.len(), p2.len(), "placed count deterministic");
        assert_eq!(u1.len(), u2.len(), "unplaced count deterministic");
        for (a, b) in p1.iter().zip(p2.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.sheet_index, b.sheet_index);
            assert_eq!(a.x.to_bits(), b.x.to_bits());
            assert_eq!(a.y.to_bits(), b.y.to_bits());
            assert_eq!(a.rotation_deg, b.rotation_deg);
        }
    }
}
