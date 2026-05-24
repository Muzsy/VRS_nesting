use std::collections::{HashMap, HashSet};

use crate::geometry::Rect;
use crate::io::Placement;
use crate::item::{dims_for_rotation, normalize_allowed_rotations, placement_anchor_from_rect_min, Part};
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::{generate_candidates_with_sheets, PlacedBbox};
use super::initializer::bbox_from_placement;
use super::working::WorkingLayout;

const BOUNDARY_LOSS_PROXY: f64 = 1.0;

fn bbox_overlap_area(a: &PlacedBbox, b: &PlacedBbox) -> f64 {
    if a.sheet_index != b.sheet_index {
        return 0.0;
    }
    let dx = (a.x2.min(b.x2) - a.x1.max(b.x1)).max(0.0);
    let dy = (a.y2.min(b.y2) - a.y1.max(b.y1)).max(0.0);
    dx * dy
}

// ---------------------------------------------------------------------------
// VrsCollisionTracker
// ---------------------------------------------------------------------------

pub struct VrsCollisionTracker {
    n: usize,
    pair_weights: HashMap<(usize, usize), f64>,
    boundary_weights: Vec<f64>,
    bboxes: Vec<Option<PlacedBbox>>,
    boundary_valid: Vec<bool>,
}

impl VrsCollisionTracker {
    pub fn build(layout: &WorkingLayout, parts: &[Part], sheets: &[SheetShape]) -> Self {
        let n = layout.placements.len();
        let mut bboxes = Vec::with_capacity(n);
        let mut boundary_valid = Vec::with_capacity(n);

        for p in &layout.placements {
            let part = parts.iter().find(|pt| pt.id == p.part_id);
            let bbox = part.and_then(|pt| bbox_from_placement(p, pt.width, pt.height));
            let valid = if let Some(ref bb) = bbox {
                if p.sheet_index < sheets.len() {
                    let rect = Rect { x1: bb.x1, y1: bb.y1, x2: bb.x2, y2: bb.y2 };
                    rect_within_boundary(rect, &sheets[p.sheet_index])
                } else {
                    false
                }
            } else {
                false
            };
            bboxes.push(bbox);
            boundary_valid.push(valid);
        }

        Self {
            n,
            pair_weights: HashMap::new(),
            boundary_weights: vec![1.0; n],
            bboxes,
            boundary_valid,
        }
    }

    fn pair_key(i: usize, j: usize) -> (usize, usize) {
        if i < j { (i, j) } else { (j, i) }
    }

    fn pair_weight(&self, i: usize, j: usize) -> f64 {
        *self.pair_weights.get(&Self::pair_key(i, j)).unwrap_or(&1.0)
    }

    pub fn pair_loss(&self, i: usize, j: usize) -> f64 {
        match (&self.bboxes[i], &self.bboxes[j]) {
            (Some(a), Some(b)) => bbox_overlap_area(a, b),
            _ => 0.0,
        }
    }

    pub fn boundary_loss(&self, i: usize) -> f64 {
        if self.boundary_valid[i] { 0.0 } else { BOUNDARY_LOSS_PROXY }
    }

    pub fn total_loss(&self) -> f64 {
        let mut loss = 0.0;
        for i in 0..self.n {
            loss += self.boundary_loss(i);
            for j in (i + 1)..self.n {
                loss += self.pair_loss(i, j);
            }
        }
        loss
    }

    pub fn total_weighted_loss(&self) -> f64 {
        let mut loss = 0.0;
        for i in 0..self.n {
            loss += self.boundary_weights[i] * self.boundary_loss(i);
            for j in (i + 1)..self.n {
                loss += self.pair_weight(i, j) * self.pair_loss(i, j);
            }
        }
        loss
    }

    pub fn colliding_indices(&self) -> Vec<usize> {
        let mut set: HashSet<usize> = HashSet::new();
        for i in 0..self.n {
            if self.boundary_loss(i) > 0.0 {
                set.insert(i);
            }
            for j in (i + 1)..self.n {
                if self.pair_loss(i, j) > 0.0 {
                    set.insert(i);
                    set.insert(j);
                }
            }
        }
        let mut result: Vec<usize> = set.into_iter().collect();
        result.sort_unstable();
        result
    }

    pub fn weighted_loss_for_item(&self, idx: usize) -> f64 {
        let mut loss = self.boundary_weights[idx] * self.boundary_loss(idx);
        for j in 0..self.n {
            if j == idx { continue; }
            let (i, k) = if idx < j { (idx, j) } else { (j, idx) };
            loss += self.pair_weight(i, k) * self.pair_loss(i, k);
        }
        loss
    }

    pub fn update_weights(&mut self, decay: f64, weight_max: f64) {
        for i in 0..self.n {
            if self.boundary_loss(i) > 0.0 {
                let w = &mut self.boundary_weights[i];
                *w = (*w + 1.0 / (1.0 + *w * decay)).min(weight_max);
            }
            for j in (i + 1)..self.n {
                if self.pair_loss(i, j) > 0.0 {
                    let key = (i, j);
                    let w = self.pair_weights.entry(key).or_insert(1.0);
                    *w = (*w + 1.0 / (1.0 + *w * decay)).min(weight_max);
                }
            }
        }
    }

    pub fn update_placement(&mut self, idx: usize, layout: &WorkingLayout, parts: &[Part], sheets: &[SheetShape]) {
        let p = &layout.placements[idx];
        let part = parts.iter().find(|pt| pt.id == p.part_id);
        let bbox = part.and_then(|pt| bbox_from_placement(p, pt.width, pt.height));
        let valid = if let Some(ref bb) = bbox {
            if p.sheet_index < sheets.len() {
                let rect = Rect { x1: bb.x1, y1: bb.y1, x2: bb.x2, y2: bb.y2 };
                rect_within_boundary(rect, &sheets[p.sheet_index])
            } else {
                false
            }
        } else {
            false
        };
        self.bboxes[idx] = bbox;
        self.boundary_valid[idx] = valid;
    }

    pub fn restore_item(&mut self, idx: usize, bbox: Option<PlacedBbox>, valid: bool) {
        self.bboxes[idx] = bbox;
        self.boundary_valid[idx] = valid;
    }
}

// ---------------------------------------------------------------------------
// VrsSeparatorConfig
// ---------------------------------------------------------------------------

pub struct VrsSeparatorConfig {
    pub max_strikes: usize,
    pub max_inner_iterations: usize,
    pub gls_weight_decay: f64,
    pub gls_weight_max: f64,
}

impl Default for VrsSeparatorConfig {
    fn default() -> Self {
        Self {
            max_strikes: 20,
            max_inner_iterations: 200,
            gls_weight_decay: 0.01,
            gls_weight_max: 100.0,
        }
    }
}

// ---------------------------------------------------------------------------
// VrsSeparatorDiagnostics
// ---------------------------------------------------------------------------

pub struct VrsSeparatorDiagnostics {
    pub initial_loss: f64,
    pub best_loss: f64,
    pub iterations: usize,
    pub moves_attempted: usize,
    pub moves_accepted: usize,
    pub rollback_count: usize,
    pub converged: bool,
}

// ---------------------------------------------------------------------------
// VrsSeparator
// ---------------------------------------------------------------------------

pub struct VrsSeparator {
    pub config: VrsSeparatorConfig,
}

impl VrsSeparator {
    pub fn new(config: VrsSeparatorConfig) -> Self {
        Self { config }
    }

    pub fn run(
        &self,
        layout: WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> (WorkingLayout, VrsSeparatorDiagnostics) {
        let mut tracker = VrsCollisionTracker::build(&layout, parts, sheets);
        let initial_loss = tracker.total_loss();

        if initial_loss == 0.0 {
            return (layout, VrsSeparatorDiagnostics {
                initial_loss,
                best_loss: 0.0,
                iterations: 0,
                moves_attempted: 0,
                moves_accepted: 0,
                rollback_count: 0,
                converged: true,
            });
        }

        let mut current = layout;
        let mut best_layout = current.snapshot();
        let mut best_loss = initial_loss;
        let mut current_loss = initial_loss;

        let mut iterations = 0usize;
        let mut moves_attempted = 0usize;
        let mut moves_accepted = 0usize;
        let mut rollback_count = 0usize;
        let mut strikes = 0usize;

        while iterations < self.config.max_inner_iterations && strikes < self.config.max_strikes {
            iterations += 1;

            if current_loss == 0.0 { break; }

            let colliders = tracker.colliding_indices();
            if colliders.is_empty() { break; }

            // Select worst collider by weighted loss (deterministic: max by weighted loss, ties broken by index).
            let target_idx = colliders.iter().copied()
                .max_by(|&a, &b| {
                    tracker.weighted_loss_for_item(a)
                        .partial_cmp(&tracker.weighted_loss_for_item(b))
                        .unwrap_or(std::cmp::Ordering::Equal)
                        .then(a.cmp(&b))
                })
                .unwrap();

            let part = match parts.iter().find(|p| p.id == current.placements[target_idx].part_id) {
                Some(p) => p,
                None => {
                    strikes += 1;
                    continue;
                }
            };
            let allowed_rotations = match normalize_allowed_rotations(&part.allowed_rotations_deg) {
                Ok(r) => r,
                Err(_) => {
                    strikes += 1;
                    continue;
                }
            };

            // Build placed bboxes for all items except the target.
            let placed_without: Vec<PlacedBbox> = current.placements.iter().enumerate()
                .filter(|(i, _)| *i != target_idx)
                .filter_map(|(_, p)| {
                    parts.iter().find(|pt| pt.id == p.part_id)
                        .and_then(|pt| bbox_from_placement(p, pt.width, pt.height))
                })
                .collect();

            let (candidates, _) = generate_candidates_with_sheets(sheets, &placed_without);

            // Find candidate with minimum overlap area against all other placed items.
            let mut best_cand_overlap = f64::MAX;
            let mut best_cand_placement: Option<Placement> = None;

            'cand: for cand in &candidates {
                if cand.sheet_index >= sheets.len() { continue; }
                let sheet = &sheets[cand.sheet_index];
                for &rot in &allowed_rotations {
                    let Some((rw, rh)) = dims_for_rotation(part.width, part.height, rot) else { continue; };
                    let rect = Rect {
                        x1: cand.x,
                        y1: cand.y,
                        x2: cand.x + rw,
                        y2: cand.y + rh,
                    };
                    if !rect_within_boundary(rect, sheet) { continue; }
                    let cand_bbox = PlacedBbox {
                        sheet_index: cand.sheet_index,
                        x1: cand.x,
                        y1: cand.y,
                        x2: cand.x + rw,
                        y2: cand.y + rh,
                    };
                    let overlap: f64 = placed_without.iter()
                        .map(|pb| bbox_overlap_area(pb, &cand_bbox))
                        .sum();
                    if overlap < best_cand_overlap {
                        let Some((ax, ay)) = placement_anchor_from_rect_min(
                            cand.x, cand.y, part.width, part.height, rot,
                        ) else { continue; };
                        best_cand_overlap = overlap;
                        best_cand_placement = Some(Placement {
                            instance_id: current.placements[target_idx].instance_id.clone(),
                            part_id: current.placements[target_idx].part_id.clone(),
                            sheet_index: cand.sheet_index,
                            x: ax,
                            y: ay,
                            rotation_deg: rot,
                        });
                        if overlap == 0.0 { break 'cand; }
                    }
                }
            }

            moves_attempted += 1;

            match best_cand_placement {
                None => {
                    strikes += 1;
                    tracker.update_weights(self.config.gls_weight_decay, self.config.gls_weight_max);
                }
                Some(new_p) => {
                    let old_placement = current.placements[target_idx].clone();
                    let old_bbox = tracker.bboxes[target_idx].clone();
                    let old_valid = tracker.boundary_valid[target_idx];

                    current.placements[target_idx] = new_p;
                    tracker.update_placement(target_idx, &current, parts, sheets);
                    let new_loss = tracker.total_loss();

                    if new_loss < current_loss {
                        current_loss = new_loss;
                        moves_accepted += 1;
                        if new_loss < best_loss {
                            best_loss = new_loss;
                            best_layout = current.snapshot();
                            strikes = 0;
                        } else {
                            strikes += 1;
                        }
                    } else {
                        // Rollback move.
                        current.placements[target_idx] = old_placement;
                        tracker.restore_item(target_idx, old_bbox, old_valid);
                        rollback_count += 1;
                        strikes += 1;
                        tracker.update_weights(self.config.gls_weight_decay, self.config.gls_weight_max);
                    }
                }
            }
        }

        let converged = best_loss == 0.0;
        (best_layout, VrsSeparatorDiagnostics {
            initial_loss,
            best_loss,
            iterations,
            moves_attempted,
            moves_accepted,
            rollback_count,
            converged,
        })
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::{Placement, Unplaced};
    use crate::item::{expand_instances, Part};
    use crate::optimizer::repair::find_violations;
    use crate::optimizer::working::WorkingLayout;
    use crate::sheet::{expand_sheets, Stock};

    fn make_part(id: &str, w: f64, h: f64, qty: i64, rots: Vec<i64>) -> Part {
        Part {
            id: id.to_string(),
            width: w,
            height: h,
            quantity: qty,
            allowed_rotations_deg: rots,
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
            cost_per_use: None,
        }
    }

    fn placement(instance_id: &str, part_id: &str, sheet_index: usize, x: f64, y: f64) -> Placement {
        Placement {
            instance_id: instance_id.to_string(),
            part_id: part_id.to_string(),
            sheet_index,
            x,
            y,
            rotation_deg: 0,
        }
    }

    // Test 1: valid layout → total_loss == 0
    #[test]
    fn tracker_valid_layout_total_loss_zero() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 30.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let tracker = VrsCollisionTracker::build(&layout, &parts, &sheets);
        assert_eq!(tracker.total_loss(), 0.0, "valid layout must have zero total loss");
    }

    // Test 2: overlapping layout → pair loss > 0
    #[test]
    fn tracker_overlap_gives_positive_pair_loss() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // Both items at (0,0) → 30×30 overlap
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let tracker = VrsCollisionTracker::build(&layout, &parts, &sheets);
        assert!(tracker.pair_loss(0, 1) > 0.0, "overlapping items must have positive pair loss");
        assert!(tracker.total_loss() > 0.0, "total loss must be positive for overlapping layout");
    }

    // Test 3: boundary/sheet violation → boundary loss > 0
    #[test]
    fn tracker_boundary_violation_gives_positive_boundary_loss() {
        let parts = vec![make_part("A", 30.0, 30.0, 1, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // Item placed far outside sheet boundary
        let placements = vec![placement("A__0001", "A", 0, 999.0, 999.0)];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let tracker = VrsCollisionTracker::build(&layout, &parts, &sheets);
        assert!(tracker.boundary_loss(0) > 0.0, "out-of-boundary item must have positive boundary loss");
        assert!(tracker.total_loss() > 0.0, "total loss must be positive for boundary violation");
    }

    // Test 4: simple two-element overlap → separator produces valid layout
    #[test]
    fn separator_fixes_simple_overlap() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // Both items at (0,0) → overlap
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let sep = VrsSeparator::new(VrsSeparatorConfig::default());
        let (result, diag) = sep.run(layout, &parts, &sheets);

        assert_eq!(diag.initial_loss, 900.0, "initial overlap area 30*30=900");
        assert_eq!(diag.best_loss, 0.0, "separator must achieve zero loss");
        assert!(diag.converged, "must report converged");

        let violations = find_violations(&result.placements, &parts, &sheets);
        assert!(violations.is_empty(), "result layout must have no violations: {:?}", violations);
    }

    // Test 5: after fixing → WorkingLayout.validate_for_commit returns Ok
    #[test]
    fn separator_fixed_layout_passes_commit_gate() {
        let parts = vec![make_part("B", 40.0, 40.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("B__0001", "B", 0, 0.0, 0.0),
            placement("B__0002", "B", 0, 10.0, 10.0), // overlap with first
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let sep = VrsSeparator::new(VrsSeparatorConfig::default());
        let (result, diag) = sep.run(layout, &parts, &sheets);

        assert!(diag.best_loss == 0.0, "separator must fix overlap");
        let commit_result = result.validate_for_commit(&parts, &sheets);
        assert!(commit_result.is_ok(), "fixed layout must pass commit gate: {:?}", commit_result);
    }

    // Test 6: item count invariant maintained
    #[test]
    fn separator_preserves_item_count() {
        let parts = vec![make_part("A", 30.0, 30.0, 3, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
            placement("A__0003", "A", 0, 0.0, 0.0),
        ];
        let unplaced = vec![Unplaced { instance_id: "X__0001".to_string(), part_id: "X".to_string(), reason: "NO_CANDIDATE".to_string() }];
        let initial_count = placements.len() + unplaced.len();
        let layout = WorkingLayout::new(placements, unplaced, 1, 0);

        let sep = VrsSeparator::new(VrsSeparatorConfig::default());
        let (result, _diag) = sep.run(layout, &parts, &sheets);

        assert_eq!(result.total_item_count(), initial_count, "item count must be preserved");
    }

    // Test 7: deterministic — two identical runs give same output
    #[test]
    fn separator_is_deterministic() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 5.0, 5.0),
        ];

        let make_layout = || WorkingLayout::new(placements.clone(), vec![], 1, 0);
        let config1 = VrsSeparatorConfig::default();
        let config2 = VrsSeparatorConfig::default();

        let (r1, d1) = VrsSeparator::new(config1).run(make_layout(), &parts, &sheets);
        let (r2, d2) = VrsSeparator::new(config2).run(make_layout(), &parts, &sheets);

        assert_eq!(d1.best_loss.to_bits(), d2.best_loss.to_bits(), "best_loss must be identical");
        assert_eq!(r1.placements.len(), r2.placements.len());
        for (a, b) in r1.placements.iter().zip(r2.placements.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.sheet_index, b.sheet_index);
            assert_eq!(a.x.to_bits(), b.x.to_bits());
            assert_eq!(a.y.to_bits(), b.y.to_bits());
            assert_eq!(a.rotation_deg, b.rotation_deg);
        }
    }

    // Test 8: non-fixable fixture does not panic; diagnostics show non-convergence or best_loss > 0
    #[test]
    fn separator_non_fixable_does_not_panic() {
        // Two 60×60 items on 80×60 sheet — only one fits; cannot place both without overlap.
        let parts = vec![make_part("B", 60.0, 60.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 80.0, 60.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("B__0001", "B", 0, 0.0, 0.0),
            placement("B__0002", "B", 0, 0.0, 0.0), // forced overlap
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let sep = VrsSeparator::new(VrsSeparatorConfig {
            max_strikes: 5,
            max_inner_iterations: 20,
            ..VrsSeparatorConfig::default()
        });
        let (_result, diag) = sep.run(layout, &parts, &sheets);

        // Must not panic, and must indicate non-convergence or residual loss.
        assert!(!diag.converged || diag.best_loss > 0.0,
            "non-fixable fixture: converged={} best_loss={}", diag.converged, diag.best_loss);
    }
}
