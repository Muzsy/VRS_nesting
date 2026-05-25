use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};

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
use super::loss_model::LossModelKind;
use super::working::WorkingLayout;

// ---------------------------------------------------------------------------
// LossSnapshot
// ---------------------------------------------------------------------------

/// Snapshot of `VrsCollisionTracker` geometric loss-state (bboxes + boundary state).
///
/// Restoring via [`VrsCollisionTracker::restore_but_keep_weights`] resets geometric state
/// without touching GLS weights, preserving accumulated weight history.
#[derive(Clone)]
pub struct LossSnapshot {
    bboxes: Vec<Option<PlacedBbox>>,
    boundary_valid: Vec<bool>,
    boundary_losses: Vec<f64>,
}

// ---------------------------------------------------------------------------
// VrsCollisionTracker
// ---------------------------------------------------------------------------

#[derive(Clone)]
pub struct VrsCollisionTracker {
    n: usize,
    pair_weights: HashMap<(usize, usize), f64>,
    boundary_weights: Vec<f64>,
    bboxes: Vec<Option<PlacedBbox>>,
    boundary_valid: Vec<bool>,
    boundary_losses: Vec<f64>,
    loss_model_kind: LossModelKind,
}

#[derive(Clone)]
struct SeparatorWorker {
    worker_id: usize,
    layout: WorkingLayout,
    tracker: VrsCollisionTracker,
    raw_loss: f64,
    weighted_loss: f64,
    moves_attempted: usize,
    moves_accepted: usize,
    rollback_count: usize,
}

struct WorkerCandidate {
    worker_id: usize,
    layout: WorkingLayout,
    tracker: VrsCollisionTracker,
    raw_loss: f64,
    weighted_loss: f64,
    moves_attempted: usize,
    moves_accepted: usize,
    rollback_count: usize,
}

struct DeterministicRng {
    state: u64,
}

impl DeterministicRng {
    fn new(seed: u64) -> Self {
        // Avoid all-zero xorshift state.
        let state = if seed == 0 {
            0x9E37_79B9_7F4A_7C15
        } else {
            seed
        };
        Self { state }
    }

    fn next_u64(&mut self) -> u64 {
        let mut x = self.state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        self.state = x;
        x.wrapping_mul(0x2545_F491_4F6C_DD1D)
    }
}

impl VrsCollisionTracker {
    /// Build tracker using an explicit loss model.
    ///
    /// Called by `VrsSeparator::run` with `config.loss_model`.
    /// Existing callers should use [`Self::build`] for `BboxArea` (default) behavior.
    pub fn build_with_model(
        layout: &WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
        loss_model_kind: LossModelKind,
    ) -> Self {
        let n = layout.placements.len();
        let mut bboxes = Vec::with_capacity(n);
        let mut boundary_valid = Vec::with_capacity(n);
        let mut boundary_losses = Vec::with_capacity(n);

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
            let bl = if let Some(ref bb) = bbox {
                if p.sheet_index < sheets.len() {
                    loss_model_kind.compute_boundary_loss(bb, &sheets[p.sheet_index], valid)
                } else {
                    if valid { 0.0 } else { 1.0 }
                }
            } else {
                if valid { 0.0 } else { 1.0 }
            };
            bboxes.push(bbox);
            boundary_valid.push(valid);
            boundary_losses.push(bl);
        }

        Self {
            n,
            pair_weights: HashMap::new(),
            boundary_weights: vec![1.0; n],
            bboxes,
            boundary_valid,
            boundary_losses,
            loss_model_kind,
        }
    }

    /// Build tracker with the default `BboxArea` loss model.
    ///
    /// Backward-compatible with all pre-Q06 call sites. Existing tests and
    /// integrations that call `build` continue to use `dx*dy` overlap and binary
    /// boundary proxy without modification.
    pub fn build(layout: &WorkingLayout, parts: &[Part], sheets: &[SheetShape]) -> Self {
        Self::build_with_model(layout, parts, sheets, LossModelKind::BboxArea)
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
            (Some(a), Some(b)) => self.loss_model_kind.pair_loss(a, b),
            _ => 0.0,
        }
    }

    pub fn boundary_loss(&self, i: usize) -> f64 {
        self.boundary_losses[i]
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
        let bl = if let Some(ref bb) = bbox {
            if p.sheet_index < sheets.len() {
                self.loss_model_kind.compute_boundary_loss(bb, &sheets[p.sheet_index], valid)
            } else {
                if valid { 0.0 } else { 1.0 }
            }
        } else {
            if valid { 0.0 } else { 1.0 }
        };
        self.bboxes[idx] = bbox;
        self.boundary_valid[idx] = valid;
        self.boundary_losses[idx] = bl;
    }

    pub fn restore_item(&mut self, idx: usize, bbox: Option<PlacedBbox>, valid: bool, boundary_loss: f64) {
        self.bboxes[idx] = bbox;
        self.boundary_valid[idx] = valid;
        self.boundary_losses[idx] = boundary_loss;
    }

    /// Snapshot the full geometric loss-state (bboxes + boundary state).
    /// GLS weights are NOT captured and will not be affected by a subsequent restore.
    pub fn snapshot_loss(&self) -> LossSnapshot {
        LossSnapshot {
            bboxes: self.bboxes.clone(),
            boundary_valid: self.boundary_valid.clone(),
            boundary_losses: self.boundary_losses.clone(),
        }
    }

    /// Restore geometric loss-state from a snapshot, leaving GLS weights intact.
    pub fn restore_but_keep_weights(&mut self, snap: LossSnapshot) {
        self.bboxes = snap.bboxes;
        self.boundary_valid = snap.boundary_valid;
        self.boundary_losses = snap.boundary_losses;
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
    /// Number of separator workers. `0` is normalized to `1`.
    pub worker_count: usize,
    /// Base seed for deterministic worker-specific shuffles.
    pub seed: u64,
    /// Rotation resolution context for item re-candidate generation during separation.
    pub rotation_context: RotationResolveContext,
    /// Collision loss model. Default: `BboxArea` (backward-compatible dx*dy + binary boundary).
    pub loss_model: LossModelKind,
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
            worker_count: 1,
            seed: 0,
            rotation_context: RotationResolveContext::legacy_default(),
            loss_model: LossModelKind::BboxArea,
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

    fn compare_f64_asc(a: f64, b: f64) -> Ordering {
        a.partial_cmp(&b).unwrap_or(Ordering::Equal)
    }

    fn normalized_worker_count(&self) -> usize {
        self.config.worker_count.max(1)
    }

    fn worker_seed(&self, iteration: usize, worker_id: usize) -> u64 {
        self.config.seed
            ^ (iteration as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15)
            ^ ((worker_id as u64) + 1).wrapping_mul(0xD1B5_4A32_D192_ED03)
    }

    fn deterministic_shuffle(values: &[usize], seed: u64) -> Vec<usize> {
        let mut out = values.to_vec();
        if out.len() <= 1 {
            return out;
        }
        let mut rng = DeterministicRng::new(seed);
        for i in (1..out.len()).rev() {
            let j = (rng.next_u64() % ((i + 1) as u64)) as usize;
            out.swap(i, j);
        }
        out
    }

    fn select_worst_collider(tracker: &VrsCollisionTracker, colliders: &[usize]) -> usize {
        colliders
            .iter()
            .copied()
            .max_by(|&a, &b| {
                Self::compare_f64_asc(
                    tracker.weighted_loss_for_item(a),
                    tracker.weighted_loss_for_item(b),
                )
                .then(a.cmp(&b))
            })
            .unwrap()
    }

    fn find_best_candidate_for_target(
        &self,
        layout: &WorkingLayout,
        target_idx: usize,
        parts: &[Part],
        sheets: &[SheetShape],
        allowed_sheet_filter: &Option<HashSet<usize>>,
    ) -> Option<Placement> {
        let part = parts
            .iter()
            .find(|p| p.id == layout.placements[target_idx].part_id)?;
        let allowed_rotations = resolve_instance_rotation_angles(
            part,
            &layout.placements[target_idx].instance_id,
            &self.config.rotation_context,
        );

        let placed_without: Vec<PlacedBbox> = layout
            .placements
            .iter()
            .enumerate()
            .filter(|(i, _)| *i != target_idx)
            .filter_map(|(_, p)| {
                parts
                    .iter()
                    .find(|pt| pt.id == p.part_id)
                    .and_then(|pt| bbox_from_placement(p, pt.width, pt.height))
            })
            .collect();

        let (candidates, _) = generate_candidates_with_sheets(sheets, &placed_without);
        let mut best_cand_overlap = f64::MAX;
        let mut best_cand_placement: Option<Placement> = None;

        'cand: for cand in &candidates {
            if cand.sheet_index >= sheets.len() {
                continue;
            }
            if let Some(filter) = allowed_sheet_filter {
                if !filter.contains(&cand.sheet_index) {
                    continue;
                }
            }
            let sheet = &sheets[cand.sheet_index];
            for &rot in &allowed_rotations {
                let (rw, rh) = dims_for_rotation(part.width, part.height, rot);
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
                    sheet_index: cand.sheet_index,
                    x1: cand.x,
                    y1: cand.y,
                    x2: cand.x + rw,
                    y2: cand.y + rh,
                };
                let loss_model = self.config.loss_model;
                let overlap: f64 = placed_without
                    .iter()
                    .map(|pb| loss_model.pair_loss(pb, &cand_bbox))
                    .sum();
                if overlap < best_cand_overlap {
                    let (ax, ay) =
                        placement_anchor_from_rect_min(cand.x, cand.y, part.width, part.height, rot);
                    best_cand_overlap = overlap;
                    best_cand_placement = Some(Placement {
                        instance_id: layout.placements[target_idx].instance_id.clone(),
                        part_id: layout.placements[target_idx].part_id.clone(),
                        sheet_index: cand.sheet_index,
                        x: ax,
                        y: ay,
                        rotation_deg: rot,
                    });
                    if overlap == 0.0 {
                        break 'cand;
                    }
                }
            }
        }
        best_cand_placement
    }

    fn attempt_move(
        &self,
        worker: &mut SeparatorWorker,
        target_idx: usize,
        parts: &[Part],
        sheets: &[SheetShape],
        allowed_sheet_filter: &Option<HashSet<usize>>,
    ) {
        worker.moves_attempted += 1;
        let Some(new_p) = self.find_best_candidate_for_target(
            &worker.layout,
            target_idx,
            parts,
            sheets,
            allowed_sheet_filter,
        ) else {
            worker.tracker.update_weights(
                self.config.gls_weight_decay,
                self.config.gls_weight_max,
                self.config.gls_weight_min_inc_ratio,
                self.config.gls_weight_max_inc_ratio,
            );
            worker.weighted_loss = worker.tracker.total_weighted_loss();
            return;
        };

        let old_placement = worker.layout.placements[target_idx].clone();
        let loss_snap = worker.tracker.snapshot_loss();
        worker.layout.placements[target_idx] = new_p;
        worker
            .tracker
            .update_placement(target_idx, &worker.layout, parts, sheets);
        let new_loss = worker.tracker.total_loss();

        if new_loss < worker.raw_loss {
            worker.raw_loss = new_loss;
            worker.weighted_loss = worker.tracker.total_weighted_loss();
            worker.moves_accepted += 1;
        } else {
            worker.layout.placements[target_idx] = old_placement;
            worker.tracker.restore_but_keep_weights(loss_snap);
            worker.rollback_count += 1;
            worker.tracker.update_weights(
                self.config.gls_weight_decay,
                self.config.gls_weight_max,
                self.config.gls_weight_min_inc_ratio,
                self.config.gls_weight_max_inc_ratio,
            );
            worker.weighted_loss = worker.tracker.total_weighted_loss();
        }
    }

    fn run_worker_iteration(
        &self,
        current: &WorkingLayout,
        tracker: &VrsCollisionTracker,
        colliders: &[usize],
        iteration: usize,
        worker_id: usize,
        parts: &[Part],
        sheets: &[SheetShape],
        allowed_sheet_filter: &Option<HashSet<usize>>,
    ) -> WorkerCandidate {
        let mut worker = SeparatorWorker {
            worker_id,
            layout: current.snapshot(),
            tracker: tracker.clone(),
            raw_loss: tracker.total_loss(),
            weighted_loss: tracker.total_weighted_loss(),
            moves_attempted: 0,
            moves_accepted: 0,
            rollback_count: 0,
        };

        let targets = if worker_id == 0 {
            vec![Self::select_worst_collider(tracker, colliders)]
        } else {
            Self::deterministic_shuffle(colliders, self.worker_seed(iteration, worker_id))
        };

        for target_idx in targets {
            if worker.raw_loss == 0.0 {
                break;
            }
            self.attempt_move(
                &mut worker,
                target_idx,
                parts,
                sheets,
                allowed_sheet_filter,
            );
        }

        WorkerCandidate {
            worker_id: worker.worker_id,
            layout: worker.layout,
            tracker: worker.tracker,
            raw_loss: worker.raw_loss,
            weighted_loss: worker.weighted_loss,
            moves_attempted: worker.moves_attempted,
            moves_accepted: worker.moves_accepted,
            rollback_count: worker.rollback_count,
        }
    }

    fn compare_layout_order(a: &WorkingLayout, b: &WorkingLayout) -> Ordering {
        a.placements
            .iter()
            .zip(b.placements.iter())
            .find_map(|(pa, pb)| {
                let ord = pa
                    .sheet_index
                    .cmp(&pb.sheet_index)
                    .then(pa.rotation_deg.to_bits().cmp(&pb.rotation_deg.to_bits()))
                    .then(pa.x.to_bits().cmp(&pb.x.to_bits()))
                    .then(pa.y.to_bits().cmp(&pb.y.to_bits()))
                    .then(pa.instance_id.cmp(&pb.instance_id))
                    .then(pa.part_id.cmp(&pb.part_id));
                if ord == Ordering::Equal {
                    None
                } else {
                    Some(ord)
                }
            })
            .unwrap_or_else(|| a.placements.len().cmp(&b.placements.len()))
    }

    fn compare_worker_candidates(a: &WorkerCandidate, b: &WorkerCandidate) -> Ordering {
        Self::compare_f64_asc(a.raw_loss, b.raw_loss)
            .then(Self::compare_f64_asc(a.weighted_loss, b.weighted_loss))
            .then(b.moves_accepted.cmp(&a.moves_accepted))
            .then(a.worker_id.cmp(&b.worker_id))
            .then(Self::compare_layout_order(&a.layout, &b.layout))
    }

    fn is_better_than_master(
        master_raw_loss: f64,
        master_weighted_loss: f64,
        candidate: &WorkerCandidate,
    ) -> bool {
        candidate.raw_loss < master_raw_loss
            || (candidate.raw_loss.to_bits() == master_raw_loss.to_bits()
                && candidate.weighted_loss < master_weighted_loss)
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

        let mut tracker = VrsCollisionTracker::build_with_model(&layout, parts, sheets, self.config.loss_model);
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
        let worker_count = self.normalized_worker_count();

        while iterations < self.config.max_inner_iterations && strikes < self.config.max_strikes {
            iterations += 1;

            if current_loss == 0.0 {
                break;
            }

            let colliders = tracker.colliding_indices();
            if colliders.is_empty() {
                break;
            }

            if worker_count <= 1 {
                let worker = self.run_worker_iteration(
                    &current,
                    &tracker,
                    &colliders,
                    iterations,
                    0,
                    parts,
                    sheets,
                    &allowed_sheet_filter,
                );
                moves_attempted += worker.moves_attempted;
                moves_accepted += worker.moves_accepted;
                rollback_count += worker.rollback_count;

                if Self::is_better_than_master(current_loss, tracker.total_weighted_loss(), &worker) {
                    current = worker.layout;
                    tracker = worker.tracker;
                    current_loss = worker.raw_loss;
                    if current_loss < best_loss {
                        best_loss = current_loss;
                        best_layout = current.snapshot();
                        strikes = 0;
                    } else {
                        strikes += 1;
                    }
                } else {
                    strikes += 1;
                    if worker.moves_attempted == 0 {
                        tracker.update_weights(
                            self.config.gls_weight_decay,
                            self.config.gls_weight_max,
                            self.config.gls_weight_min_inc_ratio,
                            self.config.gls_weight_max_inc_ratio,
                        );
                    }
                }
                continue;
            }

            let master_weighted_loss = tracker.total_weighted_loss();
            let mut workers: Vec<WorkerCandidate> = Vec::with_capacity(worker_count);
            for worker_id in 0..worker_count {
                workers.push(self.run_worker_iteration(
                    &current,
                    &tracker,
                    &colliders,
                    iterations,
                    worker_id,
                    parts,
                    sheets,
                    &allowed_sheet_filter,
                ));
            }

            moves_attempted += workers.iter().map(|w| w.moves_attempted).sum::<usize>();
            moves_accepted += workers.iter().map(|w| w.moves_accepted).sum::<usize>();
            rollback_count += workers.iter().map(|w| w.rollback_count).sum::<usize>();

            workers.sort_by(Self::compare_worker_candidates);
            let best_worker = workers.into_iter().next().unwrap();

            if Self::is_better_than_master(current_loss, master_weighted_loss, &best_worker) {
                current = best_worker.layout;
                tracker = best_worker.tracker;
                current_loss = best_worker.raw_loss;
                if current_loss < best_loss {
                    best_loss = current_loss;
                    best_layout = current.snapshot();
                    strikes = 0;
                } else {
                    strikes += 1;
                }
            } else {
                strikes += 1;
                tracker.update_weights(
                    self.config.gls_weight_decay,
                    self.config.gls_weight_max,
                    self.config.gls_weight_min_inc_ratio,
                    self.config.gls_weight_max_inc_ratio,
                );
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

    fn placement(instance_id: &str, part_id: &str, sheet_index: usize, x: f64, y: f64) -> Placement {
        Placement {
            instance_id: instance_id.to_string(),
            part_id: part_id.to_string(),
            sheet_index,
            x,
            y,
            rotation_deg: 0.0,
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
            assert_eq!(a.rotation_deg.to_bits(), b.rotation_deg.to_bits());
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

    // SGH-Q03 Test 1: worker_count=1 backward compatibility.
    #[test]
    fn separator_worker_count_one_backward_compatible() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let sep = VrsSeparator::new(VrsSeparatorConfig {
            worker_count: 1,
            ..VrsSeparatorConfig::default()
        });
        let (result, diag) = sep.run(layout, &parts, &sheets);
        assert_eq!(diag.best_loss, 0.0, "worker_count=1 should keep single-worker behavior");
        assert!(find_violations(&result.placements, &parts, &sheets).is_empty());
    }

    // SGH-Q03 Test 2: worker_count=0 normalization.
    #[test]
    fn separator_worker_count_zero_normalized_to_one() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let sep = VrsSeparator::new(VrsSeparatorConfig {
            worker_count: 0,
            ..VrsSeparatorConfig::default()
        });
        let (_result, diag) = sep.run(layout, &parts, &sheets);
        assert_eq!(diag.best_loss, 0.0, "worker_count=0 should be treated as worker_count=1");
    }

    // SGH-Q03 Test 3: worker_count=3 same seed determinism.
    #[test]
    fn multi_worker_same_seed_is_deterministic() {
        let parts = vec![make_part("A", 30.0, 30.0, 3, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 5.0, 5.0),
            placement("A__0003", "A", 0, 10.0, 10.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let cfg = VrsSeparatorConfig {
            worker_count: 3,
            seed: 4242,
            ..VrsSeparatorConfig::default()
        };

        let (r1, d1) = VrsSeparator::new(cfg).run(layout.snapshot(), &parts, &sheets);
        let (r2, d2) = VrsSeparator::new(VrsSeparatorConfig { worker_count: 3, seed: 4242, ..VrsSeparatorConfig::default() })
            .run(layout, &parts, &sheets);

        assert_eq!(d1.best_loss.to_bits(), d2.best_loss.to_bits());
        assert_eq!(d1.iterations, d2.iterations);
        assert_eq!(d1.moves_attempted, d2.moves_attempted);
        assert_eq!(d1.moves_accepted, d2.moves_accepted);
        assert_eq!(d1.rollback_count, d2.rollback_count);
        assert_eq!(r1.placements.len(), r2.placements.len());
        for (a, b) in r1.placements.iter().zip(r2.placements.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert_eq!(a.sheet_index, b.sheet_index);
            assert_eq!(a.rotation_deg.to_bits(), b.rotation_deg.to_bits());
            assert_eq!(a.x.to_bits(), b.x.to_bits());
            assert_eq!(a.y.to_bits(), b.y.to_bits());
        }
    }

    // SGH-Q03 Test 4: deterministic shuffle differs for different worker seeds.
    #[test]
    fn worker_seed_shuffle_smoke_distinct_and_deterministic() {
        let base = vec![0usize, 1, 2, 3, 4, 5, 6, 7];
        let s1 = VrsSeparator::deterministic_shuffle(&base, 11);
        let s2 = VrsSeparator::deterministic_shuffle(&base, 12);
        let s1_repeat = VrsSeparator::deterministic_shuffle(&base, 11);
        assert_ne!(s1, s2, "different seeds should produce different order in this smoke fixture");
        assert_eq!(s1, s1_repeat, "same seed should produce deterministic order");
    }

    fn dense_fixture_21() -> (Vec<Part>, Vec<SheetShape>, WorkingLayout) {
        let parts = vec![make_part("D", 20.0, 20.0, 21, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let mut placements = Vec::new();
        for idx in 1..=21 {
            placements.push(placement(&format!("D__{idx:04}"), "D", 0, 0.0, 0.0));
        }
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        (parts, sheets, layout)
    }

    // SGH-Q03 Test 5: 3-worker dense fixture best_loss <= 1-worker best_loss.
    #[test]
    fn dense_fixture_three_worker_not_worse_than_single_worker() {
        let (parts, sheets, layout) = dense_fixture_21();
        let single_cfg = VrsSeparatorConfig {
            worker_count: 1,
            seed: 777,
            max_strikes: 80,
            max_inner_iterations: 600,
            ..VrsSeparatorConfig::default()
        };
        let multi_cfg = VrsSeparatorConfig {
            worker_count: 3,
            seed: 777,
            max_strikes: 80,
            max_inner_iterations: 600,
            ..VrsSeparatorConfig::default()
        };
        let (_single_layout, single_diag) = VrsSeparator::new(single_cfg).run(layout.snapshot(), &parts, &sheets);
        let (_multi_layout, multi_diag) = VrsSeparator::new(multi_cfg).run(layout, &parts, &sheets);
        println!(
            "dense_fixture_21 single: best_loss={} iterations={} moves_attempted={} moves_accepted={} rollback_count={}",
            single_diag.best_loss,
            single_diag.iterations,
            single_diag.moves_attempted,
            single_diag.moves_accepted,
            single_diag.rollback_count
        );
        println!(
            "dense_fixture_21 multi3: best_loss={} iterations={} moves_attempted={} moves_accepted={} rollback_count={}",
            multi_diag.best_loss,
            multi_diag.iterations,
            multi_diag.moves_attempted,
            multi_diag.moves_accepted,
            multi_diag.rollback_count
        );
        assert!(
            multi_diag.best_loss <= single_diag.best_loss,
            "3-worker must not be worse: single={} multi={}",
            single_diag.best_loss,
            multi_diag.best_loss
        );
    }

    // SGH-Q03 Test 6: no violations when dense fixture converges to zero.
    #[test]
    fn dense_fixture_three_worker_output_no_violations_if_zero_loss() {
        let (parts, sheets, layout) = dense_fixture_21();
        let cfg = VrsSeparatorConfig {
            worker_count: 3,
            seed: 777,
            max_strikes: 120,
            max_inner_iterations: 800,
            ..VrsSeparatorConfig::default()
        };
        let (result, diag) = VrsSeparator::new(cfg).run(layout, &parts, &sheets);
        if diag.best_loss == 0.0 {
            let violations = find_violations(&result.placements, &parts, &sheets);
            assert!(violations.is_empty(), "zero-loss output must have no violations");
        }
    }

    // SGH-Q03 Test 7: tie-break deterministic by worker_id on equal scores.
    #[test]
    fn worker_candidate_tiebreak_is_deterministic() {
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 5.0, 5.0),
        ];
        let layout_a = WorkingLayout::new(placements.clone(), vec![], 1, 0);
        let layout_b = WorkingLayout::new(placements, vec![], 1, 0);
        let parts = vec![make_part("A", 10.0, 10.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let tracker = VrsCollisionTracker::build(&layout_a, &parts, &sheets);

        let c0 = WorkerCandidate {
            worker_id: 0,
            layout: layout_a,
            tracker: tracker.clone(),
            raw_loss: 12.0,
            weighted_loss: 13.0,
            moves_attempted: 1,
            moves_accepted: 1,
            rollback_count: 0,
        };
        let c1 = WorkerCandidate {
            worker_id: 1,
            layout: layout_b,
            tracker,
            raw_loss: 12.0,
            weighted_loss: 13.0,
            moves_attempted: 1,
            moves_accepted: 1,
            rollback_count: 0,
        };
        assert_eq!(VrsSeparator::compare_worker_candidates(&c0, &c1), Ordering::Less);
    }

    // ---------------------------------------------------------------------------
    // SGH-Q06: LossModel separator integration tests
    // ---------------------------------------------------------------------------

    // SGH-Q06 separator test 1: default config uses BboxAreaLoss and preserves legacy behavior
    #[test]
    fn separator_default_loss_model_preserves_existing_behavior() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        // Default config uses BboxAreaLoss: initial_loss = 30*30 = 900 (same as pre-Q06)
        let sep = VrsSeparator::new(VrsSeparatorConfig::default());
        let (result, diag) = sep.run(layout, &parts, &sheets);

        assert_eq!(
            diag.initial_loss, 900.0,
            "default BboxAreaLoss initial_loss must match legacy 30*30=900"
        );
        assert_eq!(diag.best_loss, 0.0, "default config must fix overlap");
        assert!(diag.converged, "default config must converge");
        assert!(find_violations(&result.placements, &parts, &sheets).is_empty());
    }

    // SGH-Q06 separator test 2: PolePenetrationSmooth model runs, converges, and is violation-free
    #[test]
    fn separator_can_use_smooth_loss_model() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        let cfg = VrsSeparatorConfig {
            loss_model: LossModelKind::PolePenetrationSmooth,
            ..VrsSeparatorConfig::default()
        };
        let (result, diag) = VrsSeparator::new(cfg).run(layout, &parts, &sheets);

        assert!(
            diag.initial_loss > 0.0,
            "smooth model must detect non-zero initial loss for overlapping items"
        );
        assert_eq!(diag.best_loss, 0.0, "smooth model must achieve zero loss");
        assert!(diag.converged, "smooth model must converge for this fixture");
        assert!(find_violations(&result.placements, &parts, &sheets).is_empty());
    }

    // SGH-Q06 separator test 3: restore_but_keep_weights preserves GLS weights for any loss model
    #[test]
    fn restore_but_keep_weights_preserves_weights_with_loss_model() {
        for &model in &[LossModelKind::BboxArea, LossModelKind::PolePenetrationSmooth] {
            let parts = vec![make_part("A", 100.0, 100.0, 2, vec![0])];
            let stocks = vec![make_stock("S", 500.0, 200.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let placements = vec![
                placement("A__0001", "A", 0, 0.0, 0.0),
                placement("A__0002", "A", 0, 0.0, 0.0),
            ];
            let layout = WorkingLayout::new(placements, vec![], 1, 0);
            let mut tracker = VrsCollisionTracker::build_with_model(&layout, &parts, &sheets, model);

            let c = VrsSeparatorConfig::default();
            tracker.update_weights(
                c.gls_weight_decay,
                c.gls_weight_max,
                c.gls_weight_min_inc_ratio,
                c.gls_weight_max_inc_ratio,
            );
            let w_before = tracker.pair_weight(0, 1);
            assert!(w_before > 1.0, "weight must build up from collision ({model:?})");

            let snap = tracker.snapshot_loss();

            let layout_moved = WorkingLayout::new(
                vec![
                    placement("A__0001", "A", 0, 0.0, 0.0),
                    placement("A__0002", "A", 0, 300.0, 0.0),
                ],
                vec![],
                1,
                0,
            );
            tracker.update_placement(1, &layout_moved, &parts, &sheets);
            assert_eq!(
                tracker.total_loss(),
                0.0,
                "loss must be 0 after moving apart ({model:?})"
            );

            tracker.restore_but_keep_weights(snap);

            assert!(
                tracker.total_loss() > 0.0,
                "loss must return to overlapping state after restore ({model:?})"
            );
            assert_eq!(
                tracker.pair_weight(0, 1).to_bits(),
                w_before.to_bits(),
                "GLS weight must be bit-identical after restore_but_keep_weights ({model:?})"
            );
        }
    }

    // SGH-Q06 separator test 4: same seed + same loss model → bit-identical output
    #[test]
    fn same_seed_same_loss_model_determinism() {
        for &model in &[LossModelKind::BboxArea, LossModelKind::PolePenetrationSmooth] {
            let parts = vec![make_part("A", 30.0, 30.0, 3, vec![0])];
            let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
            let sheets = expand_sheets(&stocks).expect("sheets");
            let placements = vec![
                placement("A__0001", "A", 0, 0.0, 0.0),
                placement("A__0002", "A", 0, 5.0, 5.0),
                placement("A__0003", "A", 0, 10.0, 10.0),
            ];
            let make_layout = || WorkingLayout::new(placements.clone(), vec![], 1, 0);
            let make_cfg = || VrsSeparatorConfig {
                seed: 12345,
                loss_model: model,
                ..VrsSeparatorConfig::default()
            };

            let (r1, d1) = VrsSeparator::new(make_cfg()).run(make_layout(), &parts, &sheets);
            let (r2, d2) = VrsSeparator::new(make_cfg()).run(make_layout(), &parts, &sheets);

            assert_eq!(
                d1.best_loss.to_bits(),
                d2.best_loss.to_bits(),
                "best_loss must be bit-identical for same seed + loss model ({model:?})"
            );
            assert_eq!(
                d1.iterations, d2.iterations,
                "iterations must be identical ({model:?})"
            );
            for (a, b) in r1.placements.iter().zip(r2.placements.iter()) {
                assert_eq!(
                    a.x.to_bits(),
                    b.x.to_bits(),
                    "x must be bit-identical ({model:?})"
                );
                assert_eq!(
                    a.y.to_bits(),
                    b.y.to_bits(),
                    "y must be bit-identical ({model:?})"
                );
            }
        }
    }

    // SGH-Q06 smoke: BboxAreaLoss vs PolePenetrationSmoothLoss on dense fixture —
    // both must produce finite non-negative losses and detect overlaps.
    #[test]
    fn smoke_bbox_vs_smooth_loss_model_on_dense_fixture() {
        let (parts, sheets, layout) = dense_fixture_21();
        let cfg_bbox = VrsSeparatorConfig {
            seed: 42,
            max_strikes: 30,
            max_inner_iterations: 200,
            loss_model: LossModelKind::BboxArea,
            ..VrsSeparatorConfig::default()
        };
        let cfg_smooth = VrsSeparatorConfig {
            seed: 42,
            max_strikes: 30,
            max_inner_iterations: 200,
            loss_model: LossModelKind::PolePenetrationSmooth,
            ..VrsSeparatorConfig::default()
        };

        let (_, diag_bbox) = VrsSeparator::new(cfg_bbox).run(layout.snapshot(), &parts, &sheets);
        let (_, diag_smooth) = VrsSeparator::new(cfg_smooth).run(layout, &parts, &sheets);

        println!(
            "BboxAreaLoss:          initial_loss={:.3} best_loss={:.3} iters={}",
            diag_bbox.initial_loss, diag_bbox.best_loss, diag_bbox.iterations
        );
        println!(
            "PolePenetrationSmooth: initial_loss={:.3} best_loss={:.3} iters={}",
            diag_smooth.initial_loss, diag_smooth.best_loss, diag_smooth.iterations
        );

        assert!(
            diag_bbox.initial_loss >= 0.0 && diag_bbox.initial_loss.is_finite(),
            "BboxAreaLoss initial_loss must be finite non-negative"
        );
        assert!(
            diag_smooth.initial_loss >= 0.0 && diag_smooth.initial_loss.is_finite(),
            "smooth model initial_loss must be finite non-negative"
        );
        assert!(
            diag_bbox.best_loss >= 0.0 && diag_bbox.best_loss.is_finite(),
            "BboxAreaLoss best_loss must be finite non-negative"
        );
        assert!(
            diag_smooth.best_loss >= 0.0 && diag_smooth.best_loss.is_finite(),
            "smooth model best_loss must be finite non-negative"
        );
        assert!(
            diag_smooth.initial_loss > 0.0,
            "smooth model must detect overlaps in dense fixture (initial_loss > 0)"
        );
    }
}
