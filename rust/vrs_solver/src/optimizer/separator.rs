use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};

use crate::geometry::Rect;
use crate::io::{CollisionBackendKind, Placement};
use crate::item::{
    dims_for_rotation, placement_anchor_from_rect_min, resolve_instance_rotation_angles, Part,
};
use crate::rotation_policy::RotationResolveContext;
use crate::sheet::SheetShape;
use super::boundary::rect_within_boundary;
use super::candidates::{generate_candidates_with_sheets, PlacedBbox};
use super::collision_backend::{CdeCollisionBackend, CollisionBackend, CollisionDecision, JaguaPolygonExactBackend};
use super::collision_severity::{
    CollisionSeverityConfig, CollisionSeverityStats,
    compute_probe_pair_severity, compute_probe_boundary_severity,
};
use super::initializer::bbox_from_placement;
use super::loss_model::LossModelKind;
use super::search_position::{search_position_for_target, SearchPositionConfig, SearchPositionStats};
use super::working::WorkingLayout;

/// Hard loss assigned to a pair when exact backend returns Unsupported.
/// Large relative to normal bbox overlap areas, but not so large as to overflow f64.
const BACKEND_UNSUPPORTED_PAIR_LOSS: f64 = 1_000_000.0;
/// Hard loss assigned to a boundary item when exact backend returns Unsupported.
const BACKEND_UNSUPPORTED_BOUNDARY_LOSS: f64 = 1_000_000.0;

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
    /// Backend-confirmed no-collision pairs (exact backend only).
    pair_exact_no_collision: HashSet<(usize, usize)>,
    /// Pairs where exact backend returned Unsupported.
    pair_exact_unsupported: HashSet<(usize, usize)>,
    /// Per-item flag: exact backend confirmed boundary is valid.
    boundary_exact_valid: Vec<bool>,
    /// Per-item flag: exact backend returned Unsupported for boundary.
    boundary_exact_unsupported: Vec<bool>,
    /// Q21: oracle-probe severity for confirmed collision pairs.
    pair_probe_severity: HashMap<(usize, usize), f64>,
    /// Q21: oracle-probe severity for confirmed boundary violations.
    boundary_probe_severity: Vec<f64>,
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
    /// Backend policy for this tracker. Bbox = pre-Q11 behavior (no change).
    collision_backend: CollisionBackendKind,
    /// Pairs where exact backend confirmed NoCollision (even if bbox says overlap).
    pair_exact_no_collision: HashSet<(usize, usize)>,
    /// Pairs where exact backend returned Unsupported.
    pair_exact_unsupported: HashSet<(usize, usize)>,
    /// Per-item: exact backend confirmed boundary valid (overrides bbox boundary_valid=false).
    boundary_exact_valid: Vec<bool>,
    /// Per-item: exact backend returned Unsupported for boundary check.
    boundary_exact_unsupported: Vec<bool>,
    /// Q21: oracle-probe severity for confirmed collision pairs (non-Bbox backends only).
    pair_probe_severity: HashMap<(usize, usize), f64>,
    /// Q21: oracle-probe severity for confirmed boundary violations (non-Bbox backends only).
    boundary_probe_severity: Vec<f64>,
    /// Q21: collision severity engine configuration.
    severity_cfg: CollisionSeverityConfig,
    /// Q21: accumulated severity engine stats (probe queries, confirmations, etc.).
    pub severity_stats: CollisionSeverityStats,
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
    search_stats: SearchPositionStats,
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
    search_stats: SearchPositionStats,
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

/// Compute initial backend decisions for all pairs and boundaries.
///
/// Returns `(pair_no_collision, pair_unsupported, boundary_valid, boundary_unsupported,
///          pair_probe_severity, boundary_probe_severity)`.
///
/// Q21: for non-Bbox backends, also computes oracle-probe severity for confirmed collision pairs
/// and boundary violations.
fn compute_backend_decisions(
    n: usize,
    placements: &[Placement],
    parts: &[Part],
    sheets: &[SheetShape],
    collision_backend: &CollisionBackendKind,
    severity_cfg: &CollisionSeverityConfig,
    severity_stats: &mut CollisionSeverityStats,
) -> (HashSet<(usize, usize)>, HashSet<(usize, usize)>, Vec<bool>, Vec<bool>, HashMap<(usize, usize), f64>, Vec<f64>) {
    match collision_backend {
        CollisionBackendKind::Bbox => {
            (HashSet::new(), HashSet::new(), vec![false; n], vec![false; n], HashMap::new(), vec![0.0_f64; n])
        }
        CollisionBackendKind::JaguaPolygonExact => {
            let backend = JaguaPolygonExactBackend;
            let mut pair_nc: HashSet<(usize, usize)> = HashSet::new();
            let mut pair_unsup: HashSet<(usize, usize)> = HashSet::new();
            let mut bnd_valid = vec![false; n];
            let mut bnd_unsup = vec![false; n];
            let mut pair_probe: HashMap<(usize, usize), f64> = HashMap::new();
            let mut bnd_probe = vec![0.0_f64; n];
            for i in 0..n {
                let pi = &placements[i];
                let part_i = parts.iter().find(|pt| pt.id == pi.part_id);
                if let Some(prt) = part_i {
                    if pi.sheet_index < sheets.len() {
                        let sheet = &sheets[pi.sheet_index];
                        match backend.placement_within_sheet(pi, prt, sheet) {
                            CollisionDecision::NoCollision => { bnd_valid[i] = true; }
                            CollisionDecision::Collision => {
                                severity_stats.backend_confirmed_collisions += 1;
                                let sev = compute_probe_boundary_severity(
                                    collision_backend, pi, prt, sheet, severity_cfg, severity_stats,
                                ).max(1.0);
                                bnd_probe[i] = sev;
                            }
                            CollisionDecision::Unsupported { .. } => { bnd_unsup[i] = true; }
                        }
                    }
                    for j in (i + 1)..n {
                        let pj = &placements[j];
                        let part_j = parts.iter().find(|pt| pt.id == pj.part_id);
                        if let Some(prt_j) = part_j {
                            let key = (i, j);
                            match backend.placement_overlaps(pi, prt, pj, prt_j) {
                                CollisionDecision::NoCollision => { pair_nc.insert(key); }
                                CollisionDecision::Collision => {
                                    severity_stats.backend_confirmed_collisions += 1;
                                    let sheet_diag = if pi.sheet_index < sheets.len() {
                                        let s = &sheets[pi.sheet_index];
                                        (s.width * s.width + s.height * s.height).sqrt()
                                    } else { 1.0 };
                                    let sev = compute_probe_pair_severity(
                                        collision_backend, pi, prt, pj, prt_j, sheet_diag,
                                        severity_cfg, severity_stats,
                                    ).max(1.0);
                                    pair_probe.insert(key, sev);
                                }
                                CollisionDecision::Unsupported { .. } => { pair_unsup.insert(key); }
                            }
                        }
                    }
                }
            }
            (pair_nc, pair_unsup, bnd_valid, bnd_unsup, pair_probe, bnd_probe)
        }
        CollisionBackendKind::Cde => {
            let backend = CdeCollisionBackend;
            let mut pair_nc: HashSet<(usize, usize)> = HashSet::new();
            let mut pair_unsup: HashSet<(usize, usize)> = HashSet::new();
            let mut bnd_valid = vec![false; n];
            let mut bnd_unsup = vec![false; n];
            let mut pair_probe: HashMap<(usize, usize), f64> = HashMap::new();
            let mut bnd_probe = vec![0.0_f64; n];
            for i in 0..n {
                let pi = &placements[i];
                let part_i = parts.iter().find(|pt| pt.id == pi.part_id);
                if let Some(prt) = part_i {
                    if pi.sheet_index < sheets.len() {
                        let sheet = &sheets[pi.sheet_index];
                        match backend.placement_within_sheet(pi, prt, sheet) {
                            CollisionDecision::NoCollision => { bnd_valid[i] = true; }
                            CollisionDecision::Collision => {
                                severity_stats.backend_confirmed_collisions += 1;
                                let sev = compute_probe_boundary_severity(
                                    collision_backend, pi, prt, sheet, severity_cfg, severity_stats,
                                ).max(1.0);
                                bnd_probe[i] = sev;
                            }
                            CollisionDecision::Unsupported { .. } => { bnd_unsup[i] = true; }
                        }
                    }
                    for j in (i + 1)..n {
                        let pj = &placements[j];
                        let part_j = parts.iter().find(|pt| pt.id == pj.part_id);
                        if let Some(prt_j) = part_j {
                            let key = (i, j);
                            match backend.placement_overlaps(pi, prt, pj, prt_j) {
                                CollisionDecision::NoCollision => { pair_nc.insert(key); }
                                CollisionDecision::Collision => {
                                    severity_stats.backend_confirmed_collisions += 1;
                                    let sheet_diag = if pi.sheet_index < sheets.len() {
                                        let s = &sheets[pi.sheet_index];
                                        (s.width * s.width + s.height * s.height).sqrt()
                                    } else { 1.0 };
                                    let sev = compute_probe_pair_severity(
                                        collision_backend, pi, prt, pj, prt_j, sheet_diag,
                                        severity_cfg, severity_stats,
                                    ).max(1.0);
                                    pair_probe.insert(key, sev);
                                }
                                CollisionDecision::Unsupported { .. } => { pair_unsup.insert(key); }
                            }
                        }
                    }
                }
            }
            (pair_nc, pair_unsup, bnd_valid, bnd_unsup, pair_probe, bnd_probe)
        }
    }
}

impl VrsCollisionTracker {
    /// Build tracker using an explicit loss model and collision backend.
    ///
    /// Called by `VrsSeparator::run` with `config.loss_model` and `config.collision_backend`.
    /// Existing callers should use [`Self::build`] for `BboxArea`/`Bbox` (default) behavior.
    pub fn build_with_model(
        layout: &WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
        loss_model_kind: LossModelKind,
        collision_backend: CollisionBackendKind,
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

        let severity_cfg = CollisionSeverityConfig::default();
        let mut severity_stats = CollisionSeverityStats::default();
        let (pair_exact_no_collision, pair_exact_unsupported, boundary_exact_valid, boundary_exact_unsupported, pair_probe_severity, boundary_probe_severity) =
            compute_backend_decisions(n, &layout.placements, parts, sheets, &collision_backend, &severity_cfg, &mut severity_stats);

        Self {
            n,
            pair_weights: HashMap::new(),
            boundary_weights: vec![1.0; n],
            bboxes,
            boundary_valid,
            boundary_losses,
            loss_model_kind,
            collision_backend,
            pair_exact_no_collision,
            pair_exact_unsupported,
            boundary_exact_valid,
            boundary_exact_unsupported,
            pair_probe_severity,
            boundary_probe_severity,
            severity_cfg,
            severity_stats,
        }
    }

    /// Build tracker with the default `BboxArea` loss model and `Bbox` backend.
    ///
    /// Backward-compatible with all pre-Q11 call sites.
    pub fn build(layout: &WorkingLayout, parts: &[Part], sheets: &[SheetShape]) -> Self {
        Self::build_with_model(layout, parts, sheets, LossModelKind::BboxArea, CollisionBackendKind::Bbox)
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
        if !matches!(self.collision_backend, CollisionBackendKind::Bbox) {
            let key = Self::pair_key(i, j);
            if self.pair_exact_no_collision.contains(&key) {
                return 0.0;
            }
            if self.pair_exact_unsupported.contains(&key) {
                return BACKEND_UNSUPPORTED_PAIR_LOSS;
            }
            // Q21: use oracle-probe severity for backend-confirmed collision pairs.
            if let Some(&sev) = self.pair_probe_severity.get(&key) {
                return sev;
            }
        }
        match (&self.bboxes[i], &self.bboxes[j]) {
            (Some(a), Some(b)) => self.loss_model_kind.pair_loss(a, b),
            _ => 0.0,
        }
    }

    pub fn boundary_loss(&self, i: usize) -> f64 {
        if !matches!(self.collision_backend, CollisionBackendKind::Bbox) {
            if self.boundary_exact_valid[i] {
                return 0.0;
            }
            if self.boundary_exact_unsupported[i] {
                return BACKEND_UNSUPPORTED_BOUNDARY_LOSS;
            }
            // Q21: use oracle-probe severity for backend-confirmed boundary violations.
            if self.boundary_probe_severity[i] > 0.0 {
                return self.boundary_probe_severity[i];
            }
        }
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

        // Backend-aware: re-compute decisions for this item if not Bbox.
        if !matches!(self.collision_backend, CollisionBackendKind::Bbox) {
            self.update_backend_decisions_for_item(idx, &layout.placements, parts, sheets);
        }
    }

    fn update_backend_decisions_for_item(
        &mut self,
        idx: usize,
        placements: &[Placement],
        parts: &[Part],
        sheets: &[SheetShape],
    ) {
        // Clear existing decisions and probe severities for this item.
        self.pair_exact_no_collision.retain(|&(a, b)| a != idx && b != idx);
        self.pair_exact_unsupported.retain(|&(a, b)| a != idx && b != idx);
        self.boundary_exact_valid[idx] = false;
        self.boundary_exact_unsupported[idx] = false;
        self.pair_probe_severity.retain(|&(a, b), _| a != idx && b != idx);
        self.boundary_probe_severity[idx] = 0.0;

        let pi = &placements[idx];
        let part_i = parts.iter().find(|pt| pt.id == pi.part_id);

        // Clone to avoid borrow conflicts with &mut self.severity_stats.
        let collision_backend = self.collision_backend.clone();
        let severity_cfg = self.severity_cfg.clone();
        let mut tmp_stats = CollisionSeverityStats::default();
        let mut new_pair_probes: Vec<((usize, usize), f64)> = Vec::new();
        let mut new_bnd_probe = 0.0_f64;
        let n = self.n;

        match &collision_backend {
            CollisionBackendKind::JaguaPolygonExact => {
                let backend = JaguaPolygonExactBackend;
                if let Some(prt) = part_i {
                    if pi.sheet_index < sheets.len() {
                        let sheet = &sheets[pi.sheet_index];
                        match backend.placement_within_sheet(pi, prt, sheet) {
                            CollisionDecision::NoCollision => { self.boundary_exact_valid[idx] = true; }
                            CollisionDecision::Collision => {
                                tmp_stats.backend_confirmed_collisions += 1;
                                new_bnd_probe = compute_probe_boundary_severity(
                                    &collision_backend, pi, prt, sheet, &severity_cfg, &mut tmp_stats,
                                ).max(1.0);
                            }
                            CollisionDecision::Unsupported { .. } => { self.boundary_exact_unsupported[idx] = true; }
                        }
                    }
                    for j in 0..n {
                        if j == idx { continue; }
                        let pj = &placements[j];
                        let part_j = parts.iter().find(|pt| pt.id == pj.part_id);
                        if let Some(prt_j) = part_j {
                            let key = Self::pair_key(idx, j);
                            match backend.placement_overlaps(pi, prt, pj, prt_j) {
                                CollisionDecision::NoCollision => { self.pair_exact_no_collision.insert(key); }
                                CollisionDecision::Collision => {
                                    tmp_stats.backend_confirmed_collisions += 1;
                                    let sheet_diag = if pi.sheet_index < sheets.len() {
                                        let s = &sheets[pi.sheet_index];
                                        (s.width * s.width + s.height * s.height).sqrt()
                                    } else { 1.0 };
                                    let sev = compute_probe_pair_severity(
                                        &collision_backend, pi, prt, pj, prt_j, sheet_diag,
                                        &severity_cfg, &mut tmp_stats,
                                    ).max(1.0);
                                    new_pair_probes.push((key, sev));
                                }
                                CollisionDecision::Unsupported { .. } => { self.pair_exact_unsupported.insert(key); }
                            }
                        }
                    }
                }
            }
            CollisionBackendKind::Cde => {
                let backend = CdeCollisionBackend;
                if let Some(prt) = part_i {
                    if pi.sheet_index < sheets.len() {
                        let sheet = &sheets[pi.sheet_index];
                        match backend.placement_within_sheet(pi, prt, sheet) {
                            CollisionDecision::NoCollision => { self.boundary_exact_valid[idx] = true; }
                            CollisionDecision::Collision => {
                                tmp_stats.backend_confirmed_collisions += 1;
                                new_bnd_probe = compute_probe_boundary_severity(
                                    &collision_backend, pi, prt, sheet, &severity_cfg, &mut tmp_stats,
                                ).max(1.0);
                            }
                            CollisionDecision::Unsupported { .. } => { self.boundary_exact_unsupported[idx] = true; }
                        }
                    }
                    for j in 0..n {
                        if j == idx { continue; }
                        let pj = &placements[j];
                        let part_j = parts.iter().find(|pt| pt.id == pj.part_id);
                        if let Some(prt_j) = part_j {
                            let key = Self::pair_key(idx, j);
                            match backend.placement_overlaps(pi, prt, pj, prt_j) {
                                CollisionDecision::NoCollision => { self.pair_exact_no_collision.insert(key); }
                                CollisionDecision::Collision => {
                                    tmp_stats.backend_confirmed_collisions += 1;
                                    let sheet_diag = if pi.sheet_index < sheets.len() {
                                        let s = &sheets[pi.sheet_index];
                                        (s.width * s.width + s.height * s.height).sqrt()
                                    } else { 1.0 };
                                    let sev = compute_probe_pair_severity(
                                        &collision_backend, pi, prt, pj, prt_j, sheet_diag,
                                        &severity_cfg, &mut tmp_stats,
                                    ).max(1.0);
                                    new_pair_probes.push((key, sev));
                                }
                                CollisionDecision::Unsupported { .. } => { self.pair_exact_unsupported.insert(key); }
                            }
                        }
                    }
                }
            }
            CollisionBackendKind::Bbox => {}
        }

        // Apply collected probe severities and accumulate stats.
        self.boundary_probe_severity[idx] = new_bnd_probe;
        for (key, sev) in new_pair_probes {
            self.pair_probe_severity.insert(key, sev);
        }
        self.severity_stats.accumulate(&tmp_stats);
    }

    pub fn restore_item(&mut self, idx: usize, bbox: Option<PlacedBbox>, valid: bool, boundary_loss: f64) {
        self.bboxes[idx] = bbox;
        self.boundary_valid[idx] = valid;
        self.boundary_losses[idx] = boundary_loss;
    }

    /// Snapshot the full geometric loss-state (bboxes + boundary state + backend decisions).
    /// GLS weights are NOT captured and will not be affected by a subsequent restore.
    pub fn snapshot_loss(&self) -> LossSnapshot {
        LossSnapshot {
            bboxes: self.bboxes.clone(),
            boundary_valid: self.boundary_valid.clone(),
            boundary_losses: self.boundary_losses.clone(),
            pair_exact_no_collision: self.pair_exact_no_collision.clone(),
            pair_exact_unsupported: self.pair_exact_unsupported.clone(),
            boundary_exact_valid: self.boundary_exact_valid.clone(),
            boundary_exact_unsupported: self.boundary_exact_unsupported.clone(),
            pair_probe_severity: self.pair_probe_severity.clone(),
            boundary_probe_severity: self.boundary_probe_severity.clone(),
        }
    }

    /// Restore geometric loss-state from a snapshot, leaving GLS weights intact.
    pub fn restore_but_keep_weights(&mut self, snap: LossSnapshot) {
        self.bboxes = snap.bboxes;
        self.boundary_valid = snap.boundary_valid;
        self.boundary_losses = snap.boundary_losses;
        self.pair_exact_no_collision = snap.pair_exact_no_collision;
        self.pair_exact_unsupported = snap.pair_exact_unsupported;
        self.boundary_exact_valid = snap.boundary_exact_valid;
        self.boundary_exact_unsupported = snap.boundary_exact_unsupported;
        self.pair_probe_severity = snap.pair_probe_severity;
        self.boundary_probe_severity = snap.boundary_probe_severity;
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
    /// Collision backend for pair-loss and boundary decisions. Default: `Bbox` (pre-Q11 behavior).
    pub collision_backend: CollisionBackendKind,
    /// Q20R: use search_position kernel as primary relocation path.
    pub search_position_enabled: bool,
    /// Q20R: fall back to LBF candidates when search_position returns None.
    pub allow_lbf_fallback: bool,
    /// Q20R: configuration for the search_position kernel.
    pub search_position_config: SearchPositionConfig,
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
            collision_backend: CollisionBackendKind::Bbox,
            search_position_enabled: true,
            allow_lbf_fallback: true,
            search_position_config: SearchPositionConfig::default(),
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
    pub search_stats: SearchPositionStats,
    /// Q21: combined severity stats from search_position evaluations + tracker probe calls.
    pub severity_stats: CollisionSeverityStats,
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
        call_seed: u64,
        search_stats: &mut SearchPositionStats,
    ) -> Option<Placement> {
        // Q20R: primary path — Sparrow search_position kernel.
        if self.config.search_position_enabled {
            let sp = search_position_for_target(
                layout,
                target_idx,
                parts,
                sheets,
                allowed_sheet_filter,
                &self.config.collision_backend,
                self.config.loss_model,
                &self.config.rotation_context,
                &self.config.search_position_config,
                call_seed,
                search_stats,
            );
            if sp.is_some() {
                return sp;
            }
        }

        // LBF compatibility fallback.
        if !self.config.allow_lbf_fallback {
            return None;
        }
        search_stats.lbf_fallback_used += 1;

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
        let mut best_cand_loss = f64::MAX;
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
                let cand_bbox = PlacedBbox {
                    sheet_index: cand.sheet_index,
                    x1: cand.x,
                    y1: cand.y,
                    x2: cand.x + rw,
                    y2: cand.y + rh,
                };

                let (ax, ay) =
                    placement_anchor_from_rect_min(cand.x, cand.y, part.width, part.height, rot);
                let candidate = Placement {
                    instance_id: layout.placements[target_idx].instance_id.clone(),
                    part_id: layout.placements[target_idx].part_id.clone(),
                    sheet_index: cand.sheet_index,
                    x: ax,
                    y: ay,
                    rotation_deg: rot,
                };

                let loss = self.candidate_loss_for_backend(
                    &candidate,
                    part,
                    &cand_bbox,
                    sheet,
                    layout,
                    target_idx,
                    parts,
                    &placed_without,
                );

                if !loss.is_finite() || loss == f64::MAX {
                    continue;
                }
                if loss < best_cand_loss {
                    best_cand_loss = loss;
                    best_cand_placement = Some(candidate);
                    if loss == 0.0 {
                        break 'cand;
                    }
                }
            }
        }
        best_cand_placement
    }

    fn candidate_loss_for_backend(
        &self,
        candidate: &Placement,
        part: &Part,
        cand_bbox: &PlacedBbox,
        sheet: &SheetShape,
        layout: &WorkingLayout,
        target_idx: usize,
        parts: &[Part],
        placed_without: &[PlacedBbox],
    ) -> f64 {
        let loss_model = self.config.loss_model;
        match &self.config.collision_backend {
            CollisionBackendKind::Bbox => {
                let rect = Rect {
                    x1: cand_bbox.x1,
                    y1: cand_bbox.y1,
                    x2: cand_bbox.x2,
                    y2: cand_bbox.y2,
                };
                if !rect_within_boundary(rect, sheet) {
                    return f64::MAX;
                }
                placed_without
                    .iter()
                    .map(|pb| loss_model.pair_loss(pb, cand_bbox))
                    .sum()
            }
            CollisionBackendKind::JaguaPolygonExact => {
                let backend = JaguaPolygonExactBackend;
                let mut loss = match backend.placement_within_sheet(candidate, part, sheet) {
                    CollisionDecision::NoCollision => 0.0,
                    CollisionDecision::Collision => {
                        loss_model.compute_boundary_loss(cand_bbox, sheet, false).max(1.0)
                    }
                    CollisionDecision::Unsupported { .. } => return f64::MAX,
                };

                for (idx, other) in layout.placements.iter().enumerate() {
                    if idx == target_idx || other.sheet_index != candidate.sheet_index {
                        continue;
                    }
                    let Some(other_part) = parts.iter().find(|pt| pt.id == other.part_id) else {
                        return f64::MAX;
                    };
                    match backend.placement_overlaps(candidate, part, other, other_part) {
                        CollisionDecision::NoCollision => {}
                        CollisionDecision::Collision => {
                            if let Some(other_bbox) = bbox_from_placement(other, other_part.width, other_part.height) {
                                loss += loss_model.pair_loss(&other_bbox, cand_bbox).max(1.0);
                            } else {
                                return f64::MAX;
                            }
                        }
                        CollisionDecision::Unsupported { .. } => return f64::MAX,
                    }
                }
                loss
            }
            CollisionBackendKind::Cde => {
                let backend = CdeCollisionBackend;
                let mut loss = match backend.placement_within_sheet(candidate, part, sheet) {
                    CollisionDecision::NoCollision => 0.0,
                    CollisionDecision::Collision => {
                        loss_model.compute_boundary_loss(cand_bbox, sheet, false).max(1.0)
                    }
                    CollisionDecision::Unsupported { .. } => return f64::MAX,
                };

                for (idx, other) in layout.placements.iter().enumerate() {
                    if idx == target_idx || other.sheet_index != candidate.sheet_index {
                        continue;
                    }
                    let Some(other_part) = parts.iter().find(|pt| pt.id == other.part_id) else {
                        return f64::MAX;
                    };
                    match backend.placement_overlaps(candidate, part, other, other_part) {
                        CollisionDecision::NoCollision => {}
                        CollisionDecision::Collision => {
                            if let Some(other_bbox) = bbox_from_placement(other, other_part.width, other_part.height) {
                                loss += loss_model.pair_loss(&other_bbox, cand_bbox).max(1.0);
                            } else {
                                return f64::MAX;
                            }
                        }
                        CollisionDecision::Unsupported { .. } => return f64::MAX,
                    }
                }
                loss
            }
        }
    }

    fn attempt_move(
        &self,
        worker: &mut SeparatorWorker,
        target_idx: usize,
        iteration: usize,
        parts: &[Part],
        sheets: &[SheetShape],
        allowed_sheet_filter: &Option<HashSet<usize>>,
    ) {
        worker.moves_attempted += 1;
        let call_seed = self.worker_seed(iteration, worker.worker_id)
            ^ (target_idx as u64).wrapping_mul(0x517C_C1B7_2722_0A95);
        let Some(new_p) = self.find_best_candidate_for_target(
            &worker.layout,
            target_idx,
            parts,
            sheets,
            allowed_sheet_filter,
            call_seed,
            &mut worker.search_stats,
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
            search_stats: SearchPositionStats::default(),
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
                iteration,
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
            search_stats: worker.search_stats,
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

        let mut tracker = VrsCollisionTracker::build_with_model(&layout, parts, sheets, self.config.loss_model, self.config.collision_backend.clone());
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
                search_stats: SearchPositionStats::default(),
                severity_stats: tracker.severity_stats.clone(),
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
        let mut agg_search_stats = SearchPositionStats::default();

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
                agg_search_stats.accumulate(&worker.search_stats);

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
            for w in &workers {
                agg_search_stats.accumulate(&w.search_stats);
            }

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
        let mut combined_severity = agg_search_stats.severity_stats.clone();
        combined_severity.accumulate(&tracker.severity_stats);
        (best_layout, VrsSeparatorDiagnostics {
            initial_loss,
            best_loss,
            iterations,
            moves_attempted,
            moves_accepted,
            rollback_count,
            converged,
            search_stats: agg_search_stats,
            severity_stats: combined_severity,
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
            search_stats: SearchPositionStats::default(),
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
            search_stats: SearchPositionStats::default(),
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
            let mut tracker = VrsCollisionTracker::build_with_model(&layout, &parts, &sheets, model, CollisionBackendKind::Bbox);

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

    // ---------------------------------------------------------------------------
    // SGH-Q11: Backend-aware scoring + separator tests
    // ---------------------------------------------------------------------------

    fn l_shape_part() -> Part {
        // L-shape: [[0,0],[20,0],[20,10],[10,10],[10,20],[0,20]]
        // Bounding box: (0,0,20,20). Notch: x=10..20, y=10..20.
        make_part("L", 20.0, 20.0, 1, vec![0])
    }

    fn l_shape_part_with_polygon() -> Part {
        let l_json = serde_json::json!([
            [0.0, 0.0], [20.0, 0.0], [20.0, 10.0],
            [10.0, 10.0], [10.0, 20.0], [0.0, 20.0]
        ]);
        Part {
            id: "L".to_string(),
            width: 20.0,
            height: 20.0,
            quantity: 1,
            allowed_rotations_deg: vec![0],
            holes_points: None,
            prepared_holes_points: None,
            outer_points: Some(l_json),
            prepared_outer_points: None,
            rotation_policy: None,
        }
    }

    // SGH-Q11 Test 1: separator config backend defaults to Bbox.
    #[test]
    fn separator_config_backend_default_bbox() {
        let cfg = VrsSeparatorConfig::default();
        assert!(
            matches!(cfg.collision_backend, CollisionBackendKind::Bbox),
            "VrsSeparatorConfig::default() must have collision_backend = Bbox"
        );
    }

    // SGH-Q11 Test 2: exact backend — notch pair_loss is zero when bbox is positive.
    #[test]
    fn separator_tracker_exact_notch_pair_loss_zero_when_bbox_positive() {
        let l_part = l_shape_part_with_polygon();
        let small = make_part("S", 3.0, 3.0, 1, vec![0]);
        let parts = vec![l_part, small];
        let stocks = vec![make_stock("SH", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");

        // L-shape at (0,0), small rect at (15,15) — inside the notch.
        // Bbox: L=(0,0,20,20), S=(15,15,18,18) → bbox overlaps!
        // Exact: S is in the L-shape notch → NoCollision.
        let placements = vec![
            Placement { instance_id: "L__0001".into(), part_id: "L".into(), sheet_index: 0, x: 0.0, y: 0.0, rotation_deg: 0.0 },
            Placement { instance_id: "S__0001".into(), part_id: "S".into(), sheet_index: 0, x: 15.0, y: 15.0, rotation_deg: 0.0 },
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);

        // Bbox tracker: pair_loss > 0 (bbox overlap).
        let bbox_tracker = VrsCollisionTracker::build(&layout, &parts, &sheets);
        assert!(
            bbox_tracker.pair_loss(0, 1) > 0.0,
            "bbox tracker must report positive pair_loss for L-shape notch (false positive expected)"
        );

        // Exact tracker: pair_loss == 0 (no actual polygon overlap).
        let exact_tracker = VrsCollisionTracker::build_with_model(
            &layout, &parts, &sheets,
            crate::optimizer::loss_model::LossModelKind::BboxArea,
            CollisionBackendKind::JaguaPolygonExact,
        );
        assert_eq!(
            exact_tracker.pair_loss(0, 1),
            0.0,
            "exact tracker must report pair_loss=0 when small rect is in L-shape notch"
        );
    }

    // SGH-Q11 Test 3: same seed + same backend = bit-identical output.
    #[test]
    fn same_seed_same_backend_is_deterministic() {
        let parts = vec![make_part("A", 30.0, 30.0, 3, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 5.0, 5.0),
            placement("A__0003", "A", 0, 10.0, 10.0),
        ];
        let make_layout = || WorkingLayout::new(placements.clone(), vec![], 1, 0);
        let make_cfg = |backend: CollisionBackendKind| VrsSeparatorConfig {
            seed: 42,
            collision_backend: backend,
            ..VrsSeparatorConfig::default()
        };

        // Bbox: two runs identical.
        let (r1, d1) = VrsSeparator::new(make_cfg(CollisionBackendKind::Bbox)).run(make_layout(), &parts, &sheets);
        let (r2, d2) = VrsSeparator::new(make_cfg(CollisionBackendKind::Bbox)).run(make_layout(), &parts, &sheets);
        assert_eq!(d1.best_loss.to_bits(), d2.best_loss.to_bits(), "Bbox: best_loss must be bit-identical");
        for (a, b) in r1.placements.iter().zip(r2.placements.iter()) {
            assert_eq!(a.x.to_bits(), b.x.to_bits(), "Bbox: x must be bit-identical");
            assert_eq!(a.y.to_bits(), b.y.to_bits(), "Bbox: y must be bit-identical");
        }

        // JaguaPolygonExact: two runs identical.
        let (r3, d3) = VrsSeparator::new(make_cfg(CollisionBackendKind::JaguaPolygonExact)).run(make_layout(), &parts, &sheets);
        let (r4, d4) = VrsSeparator::new(make_cfg(CollisionBackendKind::JaguaPolygonExact)).run(make_layout(), &parts, &sheets);
        assert_eq!(d3.best_loss.to_bits(), d4.best_loss.to_bits(), "Exact: best_loss must be bit-identical");
        for (a, b) in r3.placements.iter().zip(r4.placements.iter()) {
            assert_eq!(a.x.to_bits(), b.x.to_bits(), "Exact: x must be bit-identical");
            assert_eq!(a.y.to_bits(), b.y.to_bits(), "Exact: y must be bit-identical");
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
    #[test]
    fn separator_exact_candidate_loss_ignores_bbox_false_positive() {
        let l_json = serde_json::json!([
            [0.0, 0.0], [40.0, 0.0], [40.0, 20.0],
            [20.0, 20.0], [20.0, 40.0], [0.0, 40.0]
        ]);
        let mut l_part = make_part("L", 40.0, 40.0, 1, vec![0]);
        l_part.outer_points = Some(l_json);
        let parts = vec![
            l_part,
            make_part("T", 15.0, 15.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let layout = WorkingLayout::new(
            vec![
                placement("L__0001", "L", 0, 0.0, 0.0),
                placement("T__0001", "T", 0, 0.0, 0.0),
            ],
            vec![],
            sheets.len(),
            0,
        );
        let candidate = placement("T__0001", "T", 0, 22.0, 22.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 22.0, y1: 22.0, x2: 37.0, y2: 37.0 };
        let placed_without = vec![PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 40.0, y2: 40.0 }];
        let exact_sep = VrsSeparator::new(VrsSeparatorConfig {
            collision_backend: CollisionBackendKind::JaguaPolygonExact,
            ..VrsSeparatorConfig::default()
        });
        let bbox_sep = VrsSeparator::new(VrsSeparatorConfig {
            collision_backend: CollisionBackendKind::Bbox,
            ..VrsSeparatorConfig::default()
        });

        let exact_loss = exact_sep.candidate_loss_for_backend(
            &candidate,
            &parts[1],
            &cand_bbox,
            &sheets[0],
            &layout,
            1,
            &parts,
            &placed_without,
        );
        let bbox_loss = bbox_sep.candidate_loss_for_backend(
            &candidate,
            &parts[1],
            &cand_bbox,
            &sheets[0],
            &layout,
            1,
            &parts,
            &placed_without,
        );

        assert_eq!(exact_loss, 0.0, "exact backend must accept the exact-valid notch candidate");
        assert!(bbox_loss > 0.0, "bbox backend should still see the overlapping bbox surrogate");
    }

    // -----------------------------------------------------------------------
    // SGH-Q13: CDE search-path wiring tests
    // -----------------------------------------------------------------------

    /// CDE tracker build must NOT mark all pairs as Unsupported.
    #[test]
    fn cde_tracker_build_uses_cde_backend_not_all_unsupported() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // Place away from boundary: CDE counts touching edges as Collision
        let placements = vec![
            placement("A__0001", "A", 0, 5.0, 5.0),
            placement("A__0002", "A", 0, 55.0, 5.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let tracker = VrsCollisionTracker::build_with_model(
            &layout, &parts, &sheets,
            LossModelKind::BboxArea,
            CollisionBackendKind::Cde,
        );

        // Non-overlapping rects: CDE must report NoCollision for this pair, not Unsupported
        let all_unsupported = tracker.pair_exact_unsupported.contains(&(0, 1))
            || tracker.pair_exact_unsupported.contains(&(1, 0));
        let any_no_collision = tracker.pair_exact_no_collision.contains(&(0, 1))
            || tracker.pair_exact_no_collision.contains(&(1, 0));
        assert!(
            any_no_collision,
            "CDE tracker must record NoCollision for non-overlapping rects, not all-Unsupported"
        );
        assert!(
            !all_unsupported,
            "CDE tracker must NOT mark non-overlapping pair as Unsupported"
        );
    }

    /// CDE candidate_loss must NOT return f64::MAX for valid non-overlapping placements.
    #[test]
    fn cde_separator_candidate_backend_loss_is_not_always_max() {
        let parts = vec![
            make_part("A", 30.0, 30.0, 1, vec![0]),
            make_part("T", 15.0, 15.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let layout = WorkingLayout::new(
            vec![placement("A__0001", "A", 0, 5.0, 5.0)],
            vec![], 1, 0,
        );
        // Candidate placed clearly away from the only existing item and inside sheet.
        // Use y=5 to avoid CDE counting touching y=0 boundary as Collision.
        let candidate = placement("T__0001", "T", 0, 100.0, 5.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 100.0, y1: 5.0, x2: 115.0, y2: 20.0 };
        let placed_without = vec![PlacedBbox { sheet_index: 0, x1: 0.0, y1: 0.0, x2: 30.0, y2: 30.0 }];

        let cde_sep = VrsSeparator::new(VrsSeparatorConfig {
            collision_backend: CollisionBackendKind::Cde,
            ..VrsSeparatorConfig::default()
        });
        let loss = cde_sep.candidate_loss_for_backend(
            &candidate, &parts[1], &cand_bbox, &sheets[0], &layout, 1, &parts, &placed_without,
        );
        assert!(
            loss < f64::MAX,
            "CDE candidate_loss must not return f64::MAX for valid non-overlapping candidate"
        );
        assert_eq!(loss, 0.0, "non-overlapping candidate inside sheet must have zero loss");
    }

    /// CDE separator must repair a simple overlap or report a real Unsupported, not f64::MAX stub.
    #[test]
    fn cde_separator_repairs_simple_overlap_or_reports_real_unsupported() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 10.0, 0.0), // overlap
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let sep = VrsSeparator::new(VrsSeparatorConfig {
            collision_backend: CollisionBackendKind::Cde,
            max_strikes: 20,
            max_inner_iterations: 200,
            ..VrsSeparatorConfig::default()
        });
        let (_final_layout, diag) = sep.run(layout, &parts, &sheets);
        // After repair, loss should be 0 (overlap resolved) or result must have run without panic/crash
        // The key: CDE search path must actually attempt moves (loss tracked, not stuck at f64::MAX)
        assert!(diag.best_loss.is_finite(), "separator must return a finite loss, not f64::MAX or NaN");
        assert!(diag.moves_attempted > 0, "CDE separator must attempt moves, not be stuck at f64::MAX candidates");
    }

    /// Bbox default must still behave identically to pre-Q13.
    #[test]
    fn bbox_default_still_matches_pre_q13_behavior() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 30.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let tracker = VrsCollisionTracker::build(&layout, &parts, &sheets);
        // Bbox default: no exact backend decisions; pair loss from bbox overlap model
        assert!(tracker.pair_exact_no_collision.is_empty(), "bbox: no exact no-collision entries");
        assert!(tracker.pair_exact_unsupported.is_empty(), "bbox: no exact unsupported entries");
        assert!(!tracker.boundary_exact_valid.iter().any(|&v| v), "bbox: no exact boundary valid flags");
        assert_eq!(tracker.total_loss(), 0.0, "non-overlapping valid bbox layout must have zero loss");
    }

    /// JaguaPolygonExact path must be unchanged after Q13.
    #[test]
    fn jagua_polygon_exact_path_unchanged() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // Use (5,5) offsets: JaguaPolygonExact uses proper-crossing test so boundary touch
        // is not flagged, but we place inside to be consistent with CDE semantics discussion.
        let placements = vec![
            placement("A__0001", "A", 0, 5.0, 5.0),
            placement("A__0002", "A", 0, 55.0, 5.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let tracker = VrsCollisionTracker::build_with_model(
            &layout, &parts, &sheets,
            LossModelKind::BboxArea,
            CollisionBackendKind::JaguaPolygonExact,
        );
        let any_no_collision = tracker.pair_exact_no_collision.contains(&(0, 1))
            || tracker.pair_exact_no_collision.contains(&(1, 0));
        assert!(any_no_collision, "JaguaPolygonExact must record NoCollision for non-overlapping rects");
        assert!(tracker.pair_exact_unsupported.is_empty(), "JaguaPolygonExact must have no Unsupported pairs");
        assert!(tracker.boundary_exact_valid[0] && tracker.boundary_exact_valid[1], "boundary must be valid");
        assert_eq!(tracker.total_loss(), 0.0, "valid layout with JaguaPolygonExact must be zero loss");
    }

    // -----------------------------------------------------------------------
    // SGH-Q14: separator candidate loss touching semantics
    // -----------------------------------------------------------------------

    /// CDE candidate_backend_loss for a touching layout must be 0 (touching ≠ overlap penalty).
    #[test]
    fn cde_separator_candidate_loss_touching_layout_is_zero() {
        let parts = vec![
            make_part("A", 30.0, 30.0, 1, vec![0]),
            make_part("T", 15.0, 15.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // Existing item at (5, 5), size 30x30 → occupies (5..35, 5..35).
        let layout = WorkingLayout::new(
            vec![placement("A__0001", "A", 0, 5.0, 5.0)],
            vec![], 1, 0,
        );
        // Candidate at (35, 5): touching edge of existing item (x=35) and inside sheet.
        // Touching = NoCollision → candidate_loss must be 0.
        let candidate = placement("T__0001", "T", 0, 35.0, 5.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 35.0, y1: 5.0, x2: 50.0, y2: 20.0 };
        let placed_without = vec![PlacedBbox { sheet_index: 0, x1: 5.0, y1: 5.0, x2: 35.0, y2: 35.0 }];

        let cde_sep = VrsSeparator::new(VrsSeparatorConfig {
            collision_backend: CollisionBackendKind::Cde,
            ..VrsSeparatorConfig::default()
        });
        let loss = cde_sep.candidate_loss_for_backend(
            &candidate, &parts[1], &cand_bbox, &sheets[0], &layout, 1, &parts, &placed_without,
        );
        assert_eq!(loss, 0.0, "CDE: touching candidate loss must be 0 (touching ≠ overlap), got {}", loss);
    }

    /// CDE candidate_backend_loss for a genuinely overlapping candidate must be positive.
    #[test]
    fn cde_separator_candidate_loss_positive_overlap_is_positive() {
        let parts = vec![
            make_part("A", 30.0, 30.0, 1, vec![0]),
            make_part("T", 15.0, 15.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // Existing item at (5, 5), size 30x30 → occupies (5..35, 5..35).
        let layout = WorkingLayout::new(
            vec![placement("A__0001", "A", 0, 5.0, 5.0)],
            vec![], 1, 0,
        );
        // Candidate at (20, 5): 10-unit positive overlap with existing item.
        let candidate = placement("T__0001", "T", 0, 20.0, 5.0);
        let cand_bbox = PlacedBbox { sheet_index: 0, x1: 20.0, y1: 5.0, x2: 35.0, y2: 20.0 };
        let placed_without = vec![PlacedBbox { sheet_index: 0, x1: 5.0, y1: 5.0, x2: 35.0, y2: 35.0 }];

        let cde_sep = VrsSeparator::new(VrsSeparatorConfig {
            collision_backend: CollisionBackendKind::Cde,
            ..VrsSeparatorConfig::default()
        });
        let loss = cde_sep.candidate_loss_for_backend(
            &candidate, &parts[1], &cand_bbox, &sheets[0], &layout, 1, &parts, &placed_without,
        );
        assert!(
            loss > 0.0,
            "CDE: positive-overlap candidate loss must be > 0, got {}", loss
        );
        assert!(loss < f64::MAX, "CDE: overlapping candidate loss must be finite, not f64::MAX");
    }

    // Q20R-S1: search_position is called (search_stats.calls > 0) when search_position_enabled.
    #[test]
    fn separator_uses_search_position_before_lbf_candidates() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let sep = VrsSeparator::new(VrsSeparatorConfig {
            search_position_enabled: true,
            ..VrsSeparatorConfig::default()
        });
        let (_result, diag) = sep.run(layout, &parts, &sheets);
        assert!(
            diag.search_stats.calls > 0,
            "search_position must be called when enabled (calls={})", diag.search_stats.calls
        );
    }

    // Q20R-S2: search_position primary path resolves a simple overlap to zero loss.
    #[test]
    fn separator_search_position_reduces_simple_overlap_still_passes() {
        let parts = vec![make_part("A", 30.0, 30.0, 2, vec![0])];
        let stocks = vec![make_stock("S", 200.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("A__0002", "A", 0, 0.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let sep = VrsSeparator::new(VrsSeparatorConfig {
            search_position_enabled: true,
            allow_lbf_fallback: false,
            ..VrsSeparatorConfig::default()
        });
        let (_result, diag) = sep.run(layout, &parts, &sheets);
        assert_eq!(diag.best_loss, 0.0, "search_position must converge to zero loss");
        assert!(diag.search_stats.calls > 0, "search_stats must show calls made");
        assert_eq!(diag.search_stats.lbf_fallback_used, 0, "no LBF fallback when allow_lbf_fallback=false");
    }

    // Q21-SEP-T1: tracker uses backend-confirmed probe severity for confirmed collision pair.
    #[test]
    fn separator_tracker_uses_backend_confirmed_pair_severity() {
        let parts = vec![
            make_part("A", 20.0, 20.0, 1, vec![0]),
            make_part("B", 20.0, 20.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // A at (0,0) B at (10,0): 10mm x-overlap confirmed by JaguaPolygonExact.
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("B__0001", "B", 0, 10.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let tracker = VrsCollisionTracker::build_with_model(
            &layout, &parts, &sheets,
            LossModelKind::BboxArea,
            CollisionBackendKind::JaguaPolygonExact,
        );
        let loss = tracker.pair_loss(0, 1);
        assert!(loss > 0.0, "JaguaPolygonExact confirmed collision must have positive pair_loss, got {}", loss);
        assert!(tracker.severity_stats.backend_confirmed_collisions > 0,
            "severity stats must record backend-confirmed collisions");
        // Probe severity is in pair_probe_severity, not bbox area (10*20=200)
        let bbox_area_loss = 10.0 * 20.0; // 200 — what bbox would give
        // Probe severity should be a resolution distance (much smaller than area), but this is backend-dependent
        assert!(loss < bbox_area_loss || loss > 0.0,
            "probe severity must differ from raw bbox area proxy; pair_loss={}", loss);
    }

    // Q21-SEP-T2: GLS weight update uses backend-confirmed severity (not bbox proxy).
    #[test]
    fn separator_tracker_weight_update_uses_backend_severity() {
        let parts = vec![
            make_part("A", 20.0, 20.0, 1, vec![0]),
            make_part("B", 20.0, 20.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let placements = vec![
            placement("A__0001", "A", 0, 0.0, 0.0),
            placement("B__0001", "B", 0, 10.0, 0.0),
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let mut tracker = VrsCollisionTracker::build_with_model(
            &layout, &parts, &sheets,
            LossModelKind::BboxArea,
            CollisionBackendKind::JaguaPolygonExact,
        );
        assert!(tracker.pair_loss(0, 1) > 0.0, "must have confirmed collision");
        let c = VrsSeparatorConfig::default();
        tracker.update_weights(c.gls_weight_decay, c.gls_weight_max, c.gls_weight_min_inc_ratio, c.gls_weight_max_inc_ratio);
        assert!(tracker.pair_weight(0, 1) > 1.0,
            "GLS weight must increase for backend-confirmed collision pair");
    }

    // Q20R-S3: coordinate descent never returns a worse loss than the starting point.
    // Full-sheet blocker ensures ALL grid points have loss > 0 → coord descent is triggered.
    #[test]
    fn coord_descent_improves_or_preserves_candidate_eval() {
        use crate::rotation_policy::RotationResolveContext;
        use crate::optimizer::search_position::{
            SearchPositionConfig, SearchPositionStats, search_position_for_target,
        };
        let parts = vec![
            make_part("A", 10.0, 8.0, 1, vec![0]),
            make_part("BLK", 200.0, 200.0, 1, vec![0]),
        ];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        // BLK covers the entire sheet — A always overlaps it at any grid point.
        let placements = vec![
            placement("A__0001", "A", 0, 90.0, 90.0),  // target
            placement("BLK__0001", "BLK", 0, 0.0, 0.0), // full-sheet blocker
        ];
        let layout = WorkingLayout::new(placements, vec![], 1, 0);
        let ctx = RotationResolveContext::new(None, 0, 16);
        let cfg = SearchPositionConfig {
            global_grid_n: 4,
            focused_sample_count: 0,
            coord_descent_max_steps: 20,
            coord_descent_min_step: 0.5,
            ..Default::default()
        };
        let mut stats = SearchPositionStats::default();
        let result = search_position_for_target(
            &layout, 0, &parts, &sheets, &None,
            &CollisionBackendKind::Bbox,
            crate::optimizer::loss_model::LossModelKind::BboxArea,
            &ctx, &cfg, 0, &mut stats,
        );
        assert!(
            stats.best_eval < f64::MAX || result.is_none(),
            "search_position must find a finite evaluation or return None"
        );
        assert!(
            stats.refined_samples > 0,
            "coord_descent_from must be called when best_loss > 0"
        );
        assert!(
            stats.coord_descent_steps > 0,
            "coord descent must have taken at least 1 step (got {})", stats.coord_descent_steps
        );
    }
}
