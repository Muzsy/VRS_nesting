use std::collections::{HashMap, HashSet};

use crate::geometry::Rect;
use crate::io::Placement;
use crate::item::{dims_for_rotation, normalize_allowed_rotations, placement_anchor_from_rect_min, Part};
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::{generate_candidates_with_sheets, PlacedBbox};
use super::initializer::bbox_from_placement;
use super::working::WorkingLayout;

// QUALITY_RISK: BinaryBoundaryLoss
// Exact for: never — always returns a constant (0 or 1), no gradient signal
// Proxy for: all cases; smooth boundary loss requires PolePenetrationSmoothLoss (Sparrow Algorithm 3)
// Parity: PROXY (F05, SGH-Q00)
const BOUNDARY_LOSS_PROXY: f64 = 1.0;

// QUALITY_RISK: BboxOnlyProxy
// Exact for: rectangular items at 0/90/180/270° (AABB overlap == true shape overlap)
// Proxy for: irregular shapes where axis-aligned bbox overapproximates true shape
// Parity: PROXY (F04, SGH-Q00)
fn bbox_overlap_area(a: &PlacedBbox, b: &PlacedBbox) -> f64 {
    if a.sheet_index != b.sheet_index {
        return 0.0;
    }
    let dx = (a.x2.min(b.x2) - a.x1.max(b.x1)).max(0.0);
    let dy = (a.y2.min(b.y2) - a.y1.max(b.y1)).max(0.0);
    dx * dy
}

// ---------------------------------------------------------------------------
// LossSnapshot
// ---------------------------------------------------------------------------

/// Snapshot of `VrsCollisionTracker` geometric loss-state (bboxes + boundary validity).
///
/// Restoring via [`VrsCollisionTracker::restore_but_keep_weights`] resets geometric state
/// without touching GLS weights, preserving accumulated weight history.
pub struct LossSnapshot {
    bboxes: Vec<Option<PlacedBbox>>,
    boundary_valid: Vec<bool>,
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

    pub fn pair_weight(&self, i: usize, j: usize) -> f64 {
        *self.pair_weights.get(&Self::pair_key(i, j)).unwrap_or(&1.0)
    }

    pub fn boundary_weight(&self, i: usize) -> f64 {
        self.boundary_weights[i]
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

    /// Multiplicative GLS weight update (Sparrow Algorithm 8 parity, SGH-Q02).
    ///
    /// - Colliding pairs/boundaries: weight *= multiplier proportional to loss / max_loss,
    ///   clamped to [1.0, weight_max].
    /// - Non-colliding pairs with existing weight entries: weight *= decay, floored at 1.0.
    /// - Non-colliding pairs with no entry: no entry created (no wasted memory).
    pub fn update_weights(
        &mut self,
        decay: f64,
        weight_max: f64,
        min_inc_ratio: f64,
        max_inc_ratio: f64,
    ) {
        // max_loss for normalization — computed once across all active collisions.
        let mut max_loss = 0.0_f64;
        for i in 0..self.n {
            max_loss = max_loss.max(self.boundary_loss(i));
            for j in (i + 1)..self.n {
                max_loss = max_loss.max(self.pair_loss(i, j));
            }
        }

        // Boundary weights.
        for i in 0..self.n {
            let loss = self.boundary_loss(i);
            let w = &mut self.boundary_weights[i];
            if loss == 0.0 {
                *w = (*w * decay).max(1.0);
            } else {
                let ratio = if max_loss > 0.0 { loss / max_loss } else { 1.0 };
                let mult = min_inc_ratio + (max_inc_ratio - min_inc_ratio) * ratio;
                *w = (*w * mult).min(weight_max);
            }
        }

        // Pair weights.
        for i in 0..self.n {
            for j in (i + 1)..self.n {
                let loss = self.pair_loss(i, j);
                let key = (i, j);
                if loss == 0.0 {
                    if let Some(w) = self.pair_weights.get_mut(&key) {
                        *w = (*w * decay).max(1.0);
                    }
                } else {
                    let ratio = if max_loss > 0.0 { loss / max_loss } else { 1.0 };
                    let mult = min_inc_ratio + (max_inc_ratio - min_inc_ratio) * ratio;
                    let w = self.pair_weights.entry(key).or_insert(1.0);
                    *w = (*w * mult).min(weight_max);
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

    /// Snapshot the full geometric loss-state (bboxes + boundary validity).
    /// GLS weights are NOT captured and will not be affected by a subsequent restore.
    pub fn snapshot_loss(&self) -> LossSnapshot {
        LossSnapshot {
            bboxes: self.bboxes.clone(),
            boundary_valid: self.boundary_valid.clone(),
        }
    }

    /// Restore geometric loss-state from a snapshot, leaving GLS weights intact.
    pub fn restore_but_keep_weights(&mut self, snap: LossSnapshot) {
        self.bboxes = snap.bboxes;
        self.boundary_valid = snap.boundary_valid;
    }
}

// ---------------------------------------------------------------------------
// VrsSeparatorConfig
// ---------------------------------------------------------------------------

pub struct VrsSeparatorConfig {
    pub max_strikes: usize,
    pub max_inner_iterations: usize,
    /// Multiplicative decay for non-colliding weight entries (0 < decay ≤ 1.0).
    /// Applied per iteration; weights never decay below 1.0.
    pub gls_weight_decay: f64,
    pub gls_weight_max: f64,
    /// Minimum weight multiplier for the lowest-loss colliding pair (≥ 1.0).
    pub gls_weight_min_inc_ratio: f64,
    /// Maximum weight multiplier for the highest-loss colliding pair (≥ min_inc_ratio).
    pub gls_weight_max_inc_ratio: f64,
    /// Optional relocation candidate filter. When set, separator can only place
    /// moved items onto these sheet indices.
    pub allowed_sheet_indices: Option<Vec<usize>>,
}

impl Default for VrsSeparatorConfig {
    fn default() -> Self {
        Self {
            max_strikes: 20,
            max_inner_iterations: 200,
            gls_weight_decay: 0.98,
            gls_weight_max: 100.0,
            gls_weight_min_inc_ratio: 1.01,
            gls_weight_max_inc_ratio: 1.05,
            allowed_sheet_indices: None,
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
        let allowed_sheet_filter: Option<HashSet<usize>> = self
            .config
            .allowed_sheet_indices
            .as_ref()
            .map(|v| v.iter().copied().collect());

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
                if let Some(filter) = &allowed_sheet_filter {
                    if !filter.contains(&cand.sheet_index) {
                        continue;
                    }
                }
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
                    tracker.update_weights(
                        self.config.gls_weight_decay,
                        self.config.gls_weight_max,
                        self.config.gls_weight_min_inc_ratio,
                        self.config.gls_weight_max_inc_ratio,
                    );
                }
                Some(new_p) => {
                    let old_placement = current.placements[target_idx].clone();
                    let loss_snap = tracker.snapshot_loss();

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
                        // Rollback move: restore layout + loss-state, keep GLS weights.
                        current.placements[target_idx] = old_placement;
                        tracker.restore_but_keep_weights(loss_snap);
                        rollback_count += 1;
                        strikes += 1;
                        tracker.update_weights(
                            self.config.gls_weight_decay,
                            self.config.gls_weight_max,
                            self.config.gls_weight_min_inc_ratio,
                            self.config.gls_weight_max_inc_ratio,
                        );
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
    use crate::item::Part;
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

    // Test 9: allowed sheet filter excludes disallowed relocation target sheets.
    #[test]
    fn separator_allowed_sheet_filter_excludes_disallowed_sheets() {
        let parts = vec![make_part("A", 60.0, 60.0, 2, vec![0])];
        let stocks = vec![
            make_stock("S0", 80.0, 60.0, 1),
            make_stock("S1", 80.0, 60.0, 1),
        ];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements.clone(), vec![], 2, 0);

        let sep_unfiltered = VrsSeparator::new(VrsSeparatorConfig::default());
        let (result_unfiltered, diag_unfiltered) = sep_unfiltered.run(layout.snapshot(), &parts, &sheets);
        assert!(
            diag_unfiltered.best_loss == 0.0 || diag_unfiltered.converged,
            "without filter separator should be able to use sheet 1 and resolve overlap"
        );
        assert!(
            result_unfiltered.placements.iter().any(|p| p.sheet_index == 1),
            "without filter at least one placement should move to sheet 1"
        );

        let sep_filtered = VrsSeparator::new(VrsSeparatorConfig {
            allowed_sheet_indices: Some(vec![0]),
            ..VrsSeparatorConfig::default()
        });
        let (result_filtered, diag_filtered) = sep_filtered.run(layout, &parts, &sheets);
        assert!(
            !diag_filtered.converged || diag_filtered.best_loss > 0.0,
            "with filter=only sheet 0, overlap should remain non-fixable"
        );
        assert!(
            result_filtered.placements.iter().all(|p| p.sheet_index == 0),
            "filtered run must not place items on disallowed sheet 1"
        );
    }

    // Test 10: default filter None keeps baseline behavior.
    #[test]
    fn separator_default_filter_none_is_backward_compatible() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let sep = VrsSeparator::new(VrsSeparatorConfig::default());
        let (result, diag) = sep.run(layout, &parts, &sheets);
        assert_eq!(diag.best_loss, 0.0, "default None filter should keep old behavior");
        let violations = find_violations(&result.placements, &parts, &sheets);
        assert!(violations.is_empty(), "default None filter result must remain valid");
    }

    // ---------------------------------------------------------------------------
    // SGH-Q02: Multiplicative GLS tests
    // ---------------------------------------------------------------------------

    fn cfg() -> VrsSeparatorConfig {
        VrsSeparatorConfig::default()
    }

    // Test 11: larger loss pair gets >= weight increment than smaller loss pair.
    #[test]
    fn multiplicative_gls_larger_loss_gets_larger_weight() {
        // Item 0: x=[0,100]; Item 1: x=[50,150] — 50×100=5000 overlap with 0.
        // Item 2: x=[90,190] — 10×100=1000 overlap with 0. Items 1 and 2 don't overlap.
        let parts = vec![make_part("A", 100.0, 100.0, 3, vec![0])];
        let stocks = vec![make_stock("S", 500.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 50.0, 0.0),
            placement("A__0003", "A", 0, 90.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let mut tracker = VrsCollisionTracker::build(&layout, &parts, &sheets);

        let loss_01 = tracker.pair_loss(0, 1);
        let loss_02 = tracker.pair_loss(0, 2);
        assert!(loss_01 > loss_02, "item 1 must overlap 0 more than item 2 does");

        let c = cfg();
        tracker.update_weights(c.gls_weight_decay, c.gls_weight_max, c.gls_weight_min_inc_ratio, c.gls_weight_max_inc_ratio);

        let w_01 = tracker.pair_weight(0, 1);
        let w_02 = tracker.pair_weight(0, 2);
        assert!(w_01 >= w_02, "larger loss pair must receive >= weight multiplier");
        assert!(w_01 > 1.0, "colliding pair weight must exceed 1.0 after update");
    }

    // Test 12: max-loss pair gets multiplier == max_inc_ratio (ratio = 1.0).
    #[test]
    fn multiplicative_gls_max_loss_pair_gets_max_ratio() {
        let parts = vec![make_part("A", 100.0, 100.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // Full overlap: loss = 100*100 = 10000 (max loss). ratio = 1.0 → mult = max_inc_ratio.
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let mut tracker = VrsCollisionTracker::build(&layout, &parts, &sheets);

        let c = cfg();
        tracker.update_weights(c.gls_weight_decay, c.gls_weight_max, c.gls_weight_min_inc_ratio, c.gls_weight_max_inc_ratio);

        let w = tracker.pair_weight(0, 1);
        let expected = 1.0 * c.gls_weight_max_inc_ratio;
        assert!((w - expected).abs() < 1e-12, "max-loss pair: weight={w} expected={expected}");
    }

    // Test 13: non-colliding existing weight decays toward 1.0 but never below.
    #[test]
    fn multiplicative_gls_no_collision_decay() {
        let parts = vec![make_part("A", 100.0, 100.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 500.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // First layout: overlapping → build up weight.
        let lp_overlap = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout_overlap = WorkingLayout::new(lp_overlap, vec![], 1, 0);
        let mut tracker = VrsCollisionTracker::build(&layout_overlap, &parts, &sheets);
        let c = cfg();
        tracker.update_weights(c.gls_weight_decay, c.gls_weight_max, c.gls_weight_min_inc_ratio, c.gls_weight_max_inc_ratio);
        let w_after_collision = tracker.pair_weight(0, 1);
        assert!(w_after_collision > 1.0, "weight must rise after collision");

        // Now move items apart — no collision.
        let lp_apart = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 200.0, 0.0),
        ];
        let layout_apart = WorkingLayout::new(lp_apart, vec![], 1, 0);
        // Rebuild with same pair_weights already in tracker would be ideal,
        // but for this test we build a fresh tracker and manually insert the weight.
        let mut tracker2 = VrsCollisionTracker::build(&layout_apart, &parts, &sheets);
        tracker2.pair_weights.insert((0, 1), w_after_collision);
        tracker2.update_weights(c.gls_weight_decay, c.gls_weight_max, c.gls_weight_min_inc_ratio, c.gls_weight_max_inc_ratio);

        let w_decayed = tracker2.pair_weight(0, 1);
        assert!(w_decayed < w_after_collision, "weight must decay when no collision");
        assert!(w_decayed >= 1.0, "weight must not decay below 1.0");
    }

    // Test 14: boundary weight uses same multiplicative principle.
    #[test]
    fn multiplicative_gls_boundary_weight_updates() {
        let parts = vec![make_part("A", 30.0, 30.0, 1, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![placement("A__0001", "A", 0, 999.0, 999.0)];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let mut tracker = VrsCollisionTracker::build(&layout, &parts, &sheets);

        assert!(tracker.boundary_loss(0) > 0.0, "out-of-bounds item must have boundary loss");
        let c = cfg();
        tracker.update_weights(c.gls_weight_decay, c.gls_weight_max, c.gls_weight_min_inc_ratio, c.gls_weight_max_inc_ratio);

        let bw = tracker.boundary_weight(0);
        assert!(bw > 1.0, "boundary weight must increase after boundary violation");
        let expected = 1.0 * c.gls_weight_max_inc_ratio; // only one loss entry → ratio = 1.0
        assert!((bw - expected).abs() < 1e-12, "boundary weight={bw} expected={expected}");
    }

    // Test 15: restore_but_keep_weights — loss-state restored, weights intact.
    #[test]
    fn restore_but_keep_weights_preserves_gls() {
        let parts = vec![make_part("A", 100.0, 100.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 500.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // Start with overlap to build up weights.
        let placements_overlap = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout_overlap = WorkingLayout::new(placements_overlap, vec![], 1, 0);
        let mut tracker = VrsCollisionTracker::build(&layout_overlap, &parts, &sheets);

        let c = cfg();
        tracker.update_weights(c.gls_weight_decay, c.gls_weight_max, c.gls_weight_min_inc_ratio, c.gls_weight_max_inc_ratio);
        let w_before = tracker.pair_weight(0, 1);
        assert!(w_before > 1.0, "weight must be > 1.0 before snapshot");

        // Snapshot the current (overlapping) loss-state.
        let snap = tracker.snapshot_loss();

        // Simulate a tentative move: move item 1 far away (no overlap).
        let layout_moved = WorkingLayout::new(vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 300.0, 0.0),
        ], vec![], 1, 0);
        tracker.update_placement(1, &layout_moved, &parts, &sheets);

        let loss_after_move = tracker.total_loss();
        assert_eq!(loss_after_move, 0.0, "loss must be 0 after moving apart");

        // Restore loss-state without touching weights.
        tracker.restore_but_keep_weights(snap);

        let w_after_restore = tracker.pair_weight(0, 1);
        let loss_after_restore = tracker.total_loss();

        assert!(loss_after_restore > 0.0, "loss must return to overlapping state after restore");
        assert_eq!(
            w_after_restore.to_bits(), w_before.to_bits(),
            "GLS weight must be bit-identical after restore_but_keep_weights"
        );
    }

    // Test 16: no weight entry created for zero-loss pairs.
    #[test]
    fn multiplicative_gls_no_spurious_entries_for_zero_loss() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // Items placed far apart — no collision.
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 100.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let mut tracker = VrsCollisionTracker::build(&layout, &parts, &sheets);

        let c = cfg();
        tracker.update_weights(c.gls_weight_decay, c.gls_weight_max, c.gls_weight_min_inc_ratio, c.gls_weight_max_inc_ratio);

        assert!(tracker.pair_weights.is_empty(), "no weight entries must be created for non-colliding pairs");
    }
}
