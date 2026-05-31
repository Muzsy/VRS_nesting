//! SGH-Q24R5 — Native Sparrow solver core.
//!
//! This module is the production truth model for `sparrow_cde`. It replaces the
//! legacy VRS working-layout / collision-tracker core entirely; nothing here
//! delegates back to the old mutable-working-layout types.
//!
//! Production `sparrow_cde` runs on this native model:
//!   `SparrowProblem` -> `SparrowOptimizer::solve` -> `SparrowSolveResult`
//!   (native CDE validation) -> `SparrowSolution::to_solver_projection` (boundary).
//!
//! Collision truth is CDE: the native `SparrowCollisionTracker` builds shapes via
//! `cde_adapter::prepare_shape_native` and queries `CdeCandidateSession` /
//! `CdeAdapter` directly. bbox/AABB is used only as the broad-phase prune already
//! inside the CDE adapter.
//!
//! Compression is intentionally out of scope (Q24R3/R4/R5): the default lifecycle
//! is constructive seed -> separation/exploration/search -> final CDE validation.

use std::collections::HashMap;
use std::rc::Rc;
use std::time::Instant;

use crate::io::{CollisionBackendKind, Placement, Unplaced};
use crate::item::{
    can_fit_any_stock_with_policy, dims_for_rotation, expand_instances_with_policy,
    placement_anchor_from_rect_min, Instance, Part,
};
use crate::rotation_policy::RotationResolveContext;
use crate::sheet::SheetShape;

use super::cde_adapter::{
    prepare_shape_native, prepare_shape_from_sheet, CdeCandidateSession, CdePreparedShape,
};

// ---------------------------------------------------------------------------
// rng
// ---------------------------------------------------------------------------

/// Deterministic SplitMix64-style RNG (native, seed-controlled).
pub struct DeterministicRng {
    state: u64,
}

impl DeterministicRng {
    pub fn new(seed: u64) -> Self {
        Self { state: seed ^ 0x9E37_79B9_7F4A_7C15 }
    }
    pub fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E37_79B9_7F4A_7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58_476D_1CE4_E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D0_49BB_1331_11EB);
        z ^ (z >> 31)
    }
    pub fn next_f64(&mut self) -> f64 {
        (self.next_u64() >> 11) as f64 / (1u64 << 53) as f64
    }
    pub fn jitter(&mut self, span: f64) -> f64 {
        (self.next_f64() * 2.0 - 1.0) * span
    }
}

// ---------------------------------------------------------------------------
// Config + Diagnostics
// ---------------------------------------------------------------------------

/// Native Sparrow solver configuration.
#[derive(Debug, Clone)]
pub struct SparrowConfig {
    pub time_limit_s: f64,
    pub collision_backend: CollisionBackendKind,
    pub rotation_context: RotationResolveContext,
    pub seed: u64,
    /// Compression is gated OUT of the default lifecycle (Q24R3+). When false the
    /// compression phase is skipped entirely.
    pub enable_compression: bool,
    /// Focused samples per target search around the current placement.
    pub focused_samples: usize,
    /// Coarse global grid resolution per axis per target search.
    pub global_grid_n: usize,
    /// Coordinate-descent refinement steps on the best candidate.
    pub coord_descent_steps: usize,
}

impl SparrowConfig {
    pub fn from_solver_input(
        time_limit_s: f64,
        backend: CollisionBackendKind,
        rotation_context: RotationResolveContext,
        seed: u64,
    ) -> Self {
        Self {
            time_limit_s: time_limit_s.max(0.1),
            collision_backend: backend,
            rotation_context,
            seed,
            enable_compression: false,
            focused_samples: 6,
            global_grid_n: 4,
            coord_descent_steps: 6,
        }
    }
}

/// Native Sparrow diagnostics surfaced to the adapter output projection.
/// Field names mirror the prior `sparrow_*` output contract plus the Q24R5
/// native-model proof flags.
#[derive(Debug, Clone, Default)]
pub struct SparrowDiagnostics {
    pub invoked: bool,
    pub seed_placements: usize,
    pub seed_unplaced: usize,
    pub initial_raw_loss: f64,
    pub initial_weighted_loss: f64,
    pub final_raw_loss: f64,
    pub final_weighted_loss: f64,
    pub best_infeasible_raw_loss: f64,
    pub best_infeasible_weighted_loss: f64,
    pub iterations: usize,
    pub moves_attempted: usize,
    pub moves_accepted: usize,
    pub rollbacks: usize,
    pub gls_weight_updates: usize,
    pub converged: bool,
    pub collision_graph_initial_pairs: usize,
    pub collision_graph_final_pairs: usize,
    pub boundary_violations_initial: usize,
    pub boundary_violations_final: usize,
    pub search_position_calls: usize,
    pub search_position_samples: usize,
    pub lbf_fallback_used: usize,
    pub worker_passes: usize,
    pub worker_colliding_items_seen: usize,
    pub worker_items_moved: usize,
    pub separator_invocations: usize,
    pub separator_strikes: usize,
    pub exploration_attempts: usize,
    pub exploration_pool_inserts: usize,
    pub exploration_pool_restores: usize,
    pub exploration_disruptions_large_item_swap: usize,
    pub compression_passes: usize,
    // ── Q24R5 native-model proof flags ──────────────────────────────────────
    pub native_model_active: bool,
    pub native_tracker_active: bool,
    pub old_core_used: bool,
    pub native_problem_instances: usize,
    pub native_tracker_full_rebuilds: usize,
    pub native_tracker_incremental_updates: usize,
}

// ---------------------------------------------------------------------------
// instance + problem
// ---------------------------------------------------------------------------

/// A native expanded item instance (replaces lookups through `crate::io::Placement`).
#[derive(Debug, Clone)]
pub struct SPInstance {
    pub idx: usize,
    pub instance_id: String,
    pub part_id: String,
    pub part: Part,
    pub allowed_rotations_deg: Vec<f64>,
}

/// Native fixed-sheet container set.
#[derive(Debug, Clone)]
pub struct SparrowContainer {
    pub sheets: Vec<SheetShape>,
}

/// Native rotation domain (resolved per instance).
#[derive(Debug, Clone)]
pub struct SparrowRotationDomain {
    pub allowed_rotations_deg: Vec<f64>,
}

/// Native Sparrow problem — the single conversion from VRS input structures.
pub struct SparrowProblem {
    pub instances: Vec<SPInstance>,
    pub container: SparrowContainer,
    pub config: SparrowConfig,
    /// Never-fit instances retained for output projection (no silent drops).
    pub pre_unplaced: Vec<Unplaced>,
}

impl SparrowProblem {
    /// One-way I/O conversion: VRS parts/sheets/policy -> native problem.
    pub fn from_solver_input(
        parts: &[Part],
        sheets: &[SheetShape],
        rotation_context: &RotationResolveContext,
        extra_unplaced: Vec<Unplaced>,
        config: SparrowConfig,
    ) -> Result<Self, String> {
        let expanded: Vec<Instance> = expand_instances_with_policy(parts, rotation_context)?;
        let mut instances: Vec<SPInstance> = Vec::new();
        let mut pre_unplaced: Vec<Unplaced> = extra_unplaced;
        for inst in expanded {
            let part = parts
                .iter()
                .find(|p| p.id == inst.part_id)
                .ok_or_else(|| format!("part {} missing for instance {}", inst.part_id, inst.instance_id))?;
            if !can_fit_any_stock_with_policy(part, sheets, rotation_context)? {
                pre_unplaced.push(Unplaced {
                    instance_id: inst.instance_id.clone(),
                    part_id: inst.part_id.clone(),
                    reason: "PART_NEVER_FITS_STOCK".to_string(),
                });
                continue;
            }
            let idx = instances.len();
            instances.push(SPInstance {
                idx,
                instance_id: inst.instance_id,
                part_id: inst.part_id,
                part: part.clone(),
                allowed_rotations_deg: inst.allowed_rotations_deg,
            });
        }
        Ok(Self {
            instances,
            container: SparrowContainer { sheets: sheets.to_vec() },
            config,
            pre_unplaced,
        })
    }

    pub fn rotation_domain(&self, idx: usize) -> SparrowRotationDomain {
        SparrowRotationDomain {
            allowed_rotations_deg: self.instances[idx].allowed_rotations_deg.clone(),
        }
    }
}

// ---------------------------------------------------------------------------
// layout
// ---------------------------------------------------------------------------

/// Native placement record (NOT `crate::io::Placement`). Indexed by `SPInstance`.
#[derive(Debug, Clone)]
pub struct SparrowPlacement {
    pub instance_idx: usize,
    pub sheet_index: usize,
    /// Anchor coordinates (consistent with `placement_anchor_from_rect_min`).
    pub x: f64,
    pub y: f64,
    pub rotation_deg: f64,
}

/// Native layout: one placement per (placed) instance, keyed by instance index.
#[derive(Debug, Clone)]
pub struct SparrowLayout {
    pub placements: Vec<SparrowPlacement>,
}

impl SparrowLayout {
    pub fn snapshot(&self) -> SparrowLayout {
        self.clone()
    }
    pub fn len(&self) -> usize {
        self.placements.len()
    }
    pub fn is_empty(&self) -> bool {
        self.placements.is_empty()
    }
}

// ---------------------------------------------------------------------------
// tracker (native, CDE-backed)
// ---------------------------------------------------------------------------

/// Native CDE-backed collision tracker. Owns pair/boundary records + GLS weights.
/// Collision EXISTENCE is decided by the CDE adapter (`CdeCandidateSession` /
/// jagua `CDEngine`), never bbox area.
pub struct SparrowCollisionTracker {
    n: usize,
    /// Prepared CDE shapes per instance index (rebuilt lazily after a move).
    shapes: Vec<Option<Rc<CdePreparedShape>>>,
    /// Prepared sheet shapes per sheet index.
    sheet_shapes: Vec<Option<Rc<CdePreparedShape>>>,
    /// Raw pair loss (count proxy: 1.0 per CDE-confirmed colliding pair), i<j.
    pair_loss: HashMap<(usize, usize), f64>,
    /// GLS pair weights, i<j.
    pair_weight: HashMap<(usize, usize), f64>,
    /// Raw boundary loss per item (1.0 if CDE-confirmed out of sheet).
    boundary_loss: Vec<f64>,
    /// GLS boundary weights per item.
    boundary_weight: Vec<f64>,
    pub full_rebuilds: usize,
    pub incremental_updates: usize,
    pub unsupported: bool,
}

impl SparrowCollisionTracker {
    fn prepare_item(layout: &SparrowLayout, instances: &[SPInstance], idx: usize) -> Option<Rc<CdePreparedShape>> {
        let p = &layout.placements[idx];
        let inst = &instances[p.instance_idx];
        prepare_shape_native(&inst.part, p.x, p.y, p.rotation_deg).ok().map(Rc::new)
    }

    /// Full CDE rebuild of the collision state from the native layout.
    pub fn build(layout: &SparrowLayout, instances: &[SPInstance], sheets: &[SheetShape]) -> Self {
        let n = layout.placements.len();
        let mut t = Self {
            n,
            shapes: vec![None; n],
            sheet_shapes: (0..sheets.len())
                .map(|s| prepare_shape_from_sheet(&sheets[s]).ok().map(Rc::new))
                .collect(),
            pair_loss: HashMap::new(),
            pair_weight: HashMap::new(),
            boundary_loss: vec![0.0; n],
            boundary_weight: vec![1.0; n],
            full_rebuilds: 0,
            incremental_updates: 0,
            unsupported: false,
        };
        for i in 0..n {
            t.shapes[i] = Self::prepare_item(layout, instances, i);
        }
        t.full_rebuilds += 1;
        t.recompute_all(layout, sheets);
        t
    }

    fn recompute_all(&mut self, layout: &SparrowLayout, sheets: &[SheetShape]) {
        self.pair_loss.clear();
        for v in self.boundary_loss.iter_mut() {
            *v = 0.0;
        }
        for i in 0..self.n {
            self.recompute_item(i, layout, sheets, false);
        }
    }

    /// Recompute boundary + pair losses touching item `i`. When `clear_old`, first
    /// drop existing pair entries that include `i` (incremental move update).
    fn recompute_item(&mut self, i: usize, layout: &SparrowLayout, sheets: &[SheetShape], clear_old: bool) {
        if clear_old {
            self.pair_loss.retain(|&(a, b), _| a != i && b != i);
        }
        self.boundary_loss[i] = 0.0;
        let Some(shape_i) = self.shapes[i].clone() else {
            self.unsupported = true;
            return;
        };
        let si = layout.placements[i].sheet_index;
        // Boundary: query item i against its sheet.
        if let Some(sheet_shape) = self.sheet_shapes.get(si).and_then(|s| s.clone()) {
            let adapter = super::cde_adapter::CdeAdapter::with_defaults();
            match adapter.query_boundary(&shape_i, &sheet_shape) {
                super::cde_adapter::CdeQueryResult::Collision => self.boundary_loss[i] = 1.0,
                super::cde_adapter::CdeQueryResult::NoCollision => {}
                super::cde_adapter::CdeQueryResult::Unsupported { .. } => {
                    self.unsupported = true;
                    self.boundary_loss[i] = 1.0;
                }
            }
        }
        // Pairs: query i against every other same-sheet item via one session.
        let others: Vec<(usize, Rc<CdePreparedShape>)> = (0..self.n)
            .filter(|&j| j != i && layout.placements[j].sheet_index == si)
            .filter_map(|j| self.shapes[j].clone().map(|s| (j, s)))
            .collect();
        if let Some(sheet_shape) = self.sheet_shapes.get(si).and_then(|s| s.clone()) {
            if let Some(session) = CdeCandidateSession::build(others, &sheet_shape) {
                let res = session.query(&shape_i);
                if res.unsupported {
                    self.unsupported = true;
                }
                for j in res.colliding_layout_idxs {
                    let key = if i < j { (i, j) } else { (j, i) };
                    self.pair_loss.insert(key, 1.0);
                    self.pair_weight.entry(key).or_insert(1.0);
                }
            }
        }
    }

    /// Incremental update after item `i` moved (its placement/shape changed).
    pub fn update_after_move(&mut self, i: usize, layout: &SparrowLayout, instances: &[SPInstance], sheets: &[SheetShape]) {
        self.shapes[i] = Self::prepare_item(layout, instances, i);
        self.incremental_updates += 1;
        self.recompute_item(i, layout, sheets, true);
    }

    pub fn total_raw_loss(&self) -> f64 {
        self.pair_loss.values().sum::<f64>() + self.boundary_loss.iter().sum::<f64>()
    }
    pub fn total_weighted_loss(&self) -> f64 {
        let pair: f64 = self
            .pair_loss
            .iter()
            .map(|(k, v)| v * self.pair_weight.get(k).copied().unwrap_or(1.0))
            .sum();
        let bnd: f64 = (0..self.n).map(|i| self.boundary_loss[i] * self.boundary_weight[i]).sum();
        pair + bnd
    }
    pub fn weighted_loss_for_item(&self, i: usize) -> f64 {
        let pair: f64 = self
            .pair_loss
            .iter()
            .filter(|(k, _)| k.0 == i || k.1 == i)
            .map(|(k, v)| v * self.pair_weight.get(k).copied().unwrap_or(1.0))
            .sum();
        pair + self.boundary_loss[i] * self.boundary_weight[i]
    }
    pub fn colliding_pairs(&self) -> usize {
        self.pair_loss.len()
    }
    pub fn boundary_violations(&self) -> usize {
        self.boundary_loss.iter().filter(|&&v| v > 0.0).count()
    }
    pub fn is_feasible(&self) -> bool {
        !self.unsupported && self.pair_loss.is_empty() && self.boundary_violations() == 0
    }
    pub fn colliding_indices(&self) -> Vec<usize> {
        let mut set: Vec<usize> = Vec::new();
        for i in 0..self.n {
            if self.weighted_loss_for_item(i) > 1e-12 {
                set.push(i);
            }
        }
        set
    }

    /// GLS: bump weights on currently-colliding edges/items; floor at 1.0.
    pub fn update_weights(&mut self) {
        for (k, &loss) in self.pair_loss.iter() {
            if loss > 0.0 {
                let w = self.pair_weight.entry(*k).or_insert(1.0);
                *w = (*w + 0.3).min(50.0);
            }
        }
        for i in 0..self.n {
            if self.boundary_loss[i] > 0.0 {
                self.boundary_weight[i] = (self.boundary_weight[i] + 0.3).min(50.0);
            }
        }
    }

    /// Snapshot of transient loss state (weights are preserved across restore, like Sparrow GLS).
    pub fn snapshot(&self) -> TrackerSnapshot {
        TrackerSnapshot {
            shapes: self.shapes.clone(),
            pair_loss: self.pair_loss.clone(),
            boundary_loss: self.boundary_loss.clone(),
            unsupported: self.unsupported,
        }
    }
    pub fn restore_keep_weights(&mut self, snap: TrackerSnapshot) {
        self.shapes = snap.shapes;
        self.pair_loss = snap.pair_loss;
        self.boundary_loss = snap.boundary_loss;
        self.unsupported = snap.unsupported;
    }

    /// Final full CDE validation: rebuild from scratch and confirm 0 collisions /
    /// 0 boundary violations / no unsupported queries.
    pub fn final_validation(layout: &SparrowLayout, instances: &[SPInstance], sheets: &[SheetShape]) -> bool {
        let t = SparrowCollisionTracker::build(layout, instances, sheets);
        t.is_feasible()
    }
}

#[derive(Clone)]
pub struct TrackerSnapshot {
    shapes: Vec<Option<Rc<CdePreparedShape>>>,
    pair_loss: HashMap<(usize, usize), f64>,
    boundary_loss: Vec<f64>,
    unsupported: bool,
}

// ---------------------------------------------------------------------------
// state
// ---------------------------------------------------------------------------

/// Native solver state owning layout + tracker + incumbents.
pub struct SparrowState {
    pub layout: SparrowLayout,
    pub tracker: SparrowCollisionTracker,
    pub best_feasible: Option<SparrowLayout>,
    pub best_infeasible: Option<SparrowLayout>,
    pub best_infeasible_raw_loss: f64,
}

impl SparrowState {
    pub fn new(layout: SparrowLayout, instances: &[SPInstance], sheets: &[SheetShape]) -> Self {
        let tracker = SparrowCollisionTracker::build(&layout, instances, sheets);
        let raw = tracker.total_raw_loss();
        let feasible = tracker.is_feasible();
        Self {
            best_feasible: if feasible { Some(layout.clone()) } else { None },
            best_infeasible: Some(layout.clone()),
            best_infeasible_raw_loss: raw,
            layout,
            tracker,
        }
    }
    pub fn refresh_incumbents(&mut self) {
        if self.tracker.is_feasible() {
            self.best_feasible = Some(self.layout.clone());
        } else {
            let raw = self.tracker.total_raw_loss();
            if raw < self.best_infeasible_raw_loss || self.best_infeasible.is_none() {
                self.best_infeasible = Some(self.layout.clone());
                self.best_infeasible_raw_loss = raw;
            }
        }
    }
}

// ---------------------------------------------------------------------------
// constructive seed
// ---------------------------------------------------------------------------

/// Native constructive (LBF/grid) initial solution: area-sorted coarse row/grid
/// spread across sheets, in-bounds, mild ~10% overlap (near-feasible but with real
/// separation work). Plays Sparrow's `LBFBuilder::construct` role for fixed sheets.
pub fn build_native_constructive_seed(problem: &SparrowProblem) -> SparrowLayout {
    const PITCH_FACTOR: f64 = 0.9;
    let sheets = &problem.container.sheets;
    let mut order: Vec<usize> = (0..problem.instances.len()).collect();
    order.sort_by(|&a, &b| {
        let aa = problem.instances[a].part.width * problem.instances[a].part.height;
        let ab = problem.instances[b].part.width * problem.instances[b].part.height;
        ab.partial_cmp(&aa)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| problem.instances[a].instance_id.cmp(&problem.instances[b].instance_id))
    });

    let mut cur_x = vec![0.0_f64; sheets.len()];
    let mut cur_y = vec![0.0_f64; sheets.len()];
    let mut row_h = vec![0.0_f64; sheets.len()];
    let mut placements: Vec<SparrowPlacement> = Vec::with_capacity(problem.instances.len());

    for &oi in &order {
        let inst = &problem.instances[oi];
        let rot = inst.allowed_rotations_deg.first().copied().unwrap_or(0.0);
        let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
        let mut placed = false;
        for sheet_idx in 0..sheets.len() {
            let sheet = &sheets[sheet_idx];
            if rw > sheet.width + 1e-9 || rh > sheet.height + 1e-9 {
                continue;
            }
            if cur_x[sheet_idx] + rw > sheet.width + 1e-9 {
                cur_x[sheet_idx] = 0.0;
                cur_y[sheet_idx] += row_h[sheet_idx].max(rh) * PITCH_FACTOR;
                row_h[sheet_idx] = 0.0;
            }
            if cur_y[sheet_idx] + rh > sheet.height + 1e-9 {
                continue;
            }
            let (ax, ay) = placement_anchor_from_rect_min(
                cur_x[sheet_idx],
                cur_y[sheet_idx],
                inst.part.width,
                inst.part.height,
                rot,
            );
            placements.push(SparrowPlacement {
                instance_idx: oi,
                sheet_index: sheet_idx,
                x: ax,
                y: ay,
                rotation_deg: rot,
            });
            cur_x[sheet_idx] += rw * PITCH_FACTOR;
            row_h[sheet_idx] = row_h[sheet_idx].max(rh);
            placed = true;
            break;
        }
        if !placed {
            // Overlap-allowed fallback at origin of the first hosting sheet.
            for (sheet_idx, sheet) in sheets.iter().enumerate() {
                if rw <= sheet.width + 1e-9 && rh <= sheet.height + 1e-9 {
                    let (ax, ay) = placement_anchor_from_rect_min(
                        0.0, 0.0, inst.part.width, inst.part.height, rot,
                    );
                    placements.push(SparrowPlacement {
                        instance_idx: oi,
                        sheet_index: sheet_idx,
                        x: ax,
                        y: ay,
                        rotation_deg: rot,
                    });
                    break;
                }
            }
        }
    }
    // Keep placements ordered by instance index for stable tracker indexing.
    placements.sort_by_key(|p| p.instance_idx);
    SparrowLayout { placements }
}

// ---------------------------------------------------------------------------
// native search
// ---------------------------------------------------------------------------

/// Native CDE-backed search for a clear (or least-colliding) placement of the
/// target instance, given the other items fixed. Reuses `CdeCandidateSession`.
fn native_search_placement(
    target: usize,
    layout: &SparrowLayout,
    instances: &[SPInstance],
    tracker: &SparrowCollisionTracker,
    sheets: &[SheetShape],
    cfg: &SparrowConfig,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
) -> Option<SparrowPlacement> {
    diag.search_position_calls += 1;
    let cur = &layout.placements[target];
    let inst = &instances[cur.instance_idx];
    let si = cur.sheet_index;
    let sheet = &sheets[si];
    let sheet_shape = Rc::new(prepare_shape_from_sheet(sheet).ok()?);
    // Build the fixed-other session once for this target search.
    let others: Vec<(usize, Rc<CdePreparedShape>)> = (0..layout.placements.len())
        .filter(|&j| j != target && layout.placements[j].sheet_index == si)
        .filter_map(|j| tracker.shapes[j].clone().map(|s| (j, s)))
        .collect();
    let session = CdeCandidateSession::build(others, &sheet_shape)?;

    let rotations = if inst.allowed_rotations_deg.is_empty() {
        vec![cur.rotation_deg]
    } else {
        inst.allowed_rotations_deg.clone()
    };

    // Score a candidate (rect_min_x, rect_min_y, rot): lower is better; 0 = clear.
    let mut score_at = |rmx: f64, rmy: f64, rot: f64| -> Option<(f64, SparrowPlacement)> {
        let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
        // Keep fully in-bounds (rectangular sheet bounds; CDE confirms exact boundary).
        if rmx < sheet.min_x - 1e-9
            || rmy < sheet.min_y - 1e-9
            || rmx + rw > sheet.max_x + 1e-9
            || rmy + rh > sheet.max_y + 1e-9
        {
            return None;
        }
        let (ax, ay) =
            placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
        let shape = prepare_shape_native(&inst.part, ax, ay, rot).ok()?;
        diag.search_position_samples += 1;
        let res = session.query(&shape);
        if res.unsupported {
            return None;
        }
        let score = res.colliding_layout_idxs.len() as f64
            + if res.boundary_collision { 1.0 } else { 0.0 };
        Some((
            score,
            SparrowPlacement { instance_idx: cur.instance_idx, sheet_index: si, x: ax, y: ay, rotation_deg: rot },
        ))
    };

    let mut best: Option<(f64, SparrowPlacement)> = None;
    let mut consider = |cand: Option<(f64, SparrowPlacement)>, best: &mut Option<(f64, SparrowPlacement)>| {
        if let Some((s, p)) = cand {
            let better = match best {
                None => true,
                Some((bs, _)) => s < *bs - 1e-9,
            };
            if better {
                *best = Some((s, p));
            }
        }
    };

    // Current rect-min as the reference for focused sampling.
    let (cw, ch) = dims_for_rotation(inst.part.width, inst.part.height, cur.rotation_deg);
    let cur_rmx = cur.x.min(cur.x); // anchor==rect_min for 0/90/... in this model
    let _ = (cw, ch, cur_rmx);
    // Recover rect-min from anchor: for the orthogonal/rect case anchor==rect_min.
    // Use the placement's stored anchor directly as rect-min reference.
    let ref_x = cur.x;
    let ref_y = cur.y;

    // Focused samples around the current placement.
    let span = (sheet.width.min(sheet.height)) * 0.15;
    for rot in &rotations {
        consider(score_at(ref_x, ref_y, *rot), &mut best);
        for _ in 0..cfg.focused_samples {
            let nx = ref_x + rng.jitter(span);
            let ny = ref_y + rng.jitter(span);
            consider(score_at(nx, ny, *rot), &mut best);
            if best.as_ref().map(|(s, _)| *s == 0.0).unwrap_or(false) {
                break;
            }
        }
    }
    // Coarse global grid.
    if best.as_ref().map(|(s, _)| *s > 0.0).unwrap_or(true) {
        let n = cfg.global_grid_n.max(1);
        let step_x = sheet.width / (n as f64 + 1.0);
        let step_y = sheet.height / (n as f64 + 1.0);
        'grid: for gy in 1..=n {
            for gx in 1..=n {
                let rmx = sheet.min_x + step_x * gx as f64;
                let rmy = sheet.min_y + step_y * gy as f64;
                for rot in &rotations {
                    consider(score_at(rmx, rmy, *rot), &mut best);
                    if best.as_ref().map(|(s, _)| *s == 0.0).unwrap_or(false) {
                        break 'grid;
                    }
                }
            }
        }
    }
    // Coordinate descent refinement on the best candidate (shrinking step).
    if let Some((bs, bp)) = best.clone() {
        if bs > 0.0 {
            let mut bx = bp.x;
            let mut by = bp.y;
            let mut brot = bp.rotation_deg;
            let mut bscore = bs;
            let mut step = (sheet.width.min(sheet.height)) * 0.1;
            for _ in 0..cfg.coord_descent_steps {
                let mut improved = false;
                for &(dx, dy) in &[(step, 0.0), (-step, 0.0), (0.0, step), (0.0, -step)] {
                    if let Some((s, p)) = score_at(bx + dx, by + dy, brot) {
                        if s < bscore - 1e-9 {
                            bx = p.x;
                            by = p.y;
                            brot = p.rotation_deg;
                            bscore = s;
                            improved = true;
                            if bscore == 0.0 {
                                break;
                            }
                        }
                    }
                }
                if bscore == 0.0 {
                    best = Some((0.0, SparrowPlacement { instance_idx: cur.instance_idx, sheet_index: si, x: bx, y: by, rotation_deg: brot }));
                    break;
                }
                if !improved {
                    step *= 0.5;
                }
            }
            if bscore < bs - 1e-9 {
                best = Some((bscore, SparrowPlacement { instance_idx: cur.instance_idx, sheet_index: si, x: bx, y: by, rotation_deg: brot }));
            }
        }
    }
    best.map(|(_, p)| p)
}

// ---------------------------------------------------------------------------
// optimizer (separate / worker / explore / solve)
// ---------------------------------------------------------------------------

pub struct SparrowSolution {
    pub layout: SparrowLayout,
    pub feasible: bool,
}

impl SparrowSolution {
    /// Project the native solution to VRS output placements (output boundary only).
    pub fn to_solver_projection(&self, instances: &[SPInstance]) -> Vec<Placement> {
        self.layout
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
}

pub struct SparrowSolveResult {
    pub solution: SparrowSolution,
    /// Projected output placements (VRS boundary).
    pub placements: Vec<Placement>,
    pub unplaced: Vec<Unplaced>,
    pub feasible: bool,
    pub diagnostics: SparrowDiagnostics,
}

pub struct SparrowOptimizer {
    pub config: SparrowConfig,
}

impl SparrowOptimizer {
    pub fn new(config: SparrowConfig) -> Self {
        Self { config }
    }

    /// Native separation pass over all currently colliding items (worker-style).
    fn separate(
        &self,
        state: &mut SparrowState,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        started: &Instant,
        deadline: f64,
        rng: &mut DeterministicRng,
        diag: &mut SparrowDiagnostics,
    ) -> bool {
        diag.separator_invocations += 1;
        let strike_limit = 4usize;
        let no_improve_limit = 6usize;
        let mut strikes = 0usize;
        let mut best_raw = state.tracker.total_raw_loss();
        let mut best_snapshot = (state.layout.snapshot(), state.tracker.snapshot());

        while strikes < strike_limit && started.elapsed().as_secs_f64() < deadline {
            let mut no_improve = 0usize;
            while no_improve < no_improve_limit && started.elapsed().as_secs_f64() < deadline {
                diag.iterations += 1;
                diag.worker_passes += 1;
                let colliding = state.tracker.colliding_indices();
                diag.worker_colliding_items_seen += colliding.len();
                if colliding.is_empty() {
                    break;
                }
                // Worker order: deterministic shuffle by rng.
                let mut order = colliding.clone();
                for k in (1..order.len()).rev() {
                    let j = (rng.next_u64() as usize) % (k + 1);
                    order.swap(k, j);
                }
                for target in order {
                    if started.elapsed().as_secs_f64() >= deadline {
                        break;
                    }
                    if state.tracker.weighted_loss_for_item(target) <= 1e-12 {
                        continue;
                    }
                    diag.moves_attempted += 1;
                    let old_w = state.tracker.weighted_loss_for_item(target);
                    let Some(newp) = native_search_placement(
                        target, &state.layout, instances, &state.tracker, sheets, &self.config, rng, diag,
                    ) else {
                        diag.rollbacks += 1;
                        continue;
                    };
                    let old_p = state.layout.placements[target].clone();
                    let snap = state.tracker.snapshot();
                    state.layout.placements[target] = newp;
                    state.tracker.update_after_move(target, &state.layout, instances, sheets);
                    let new_w = state.tracker.weighted_loss_for_item(target);
                    if new_w <= old_w + 1e-9 {
                        diag.moves_accepted += 1;
                        diag.worker_items_moved += 1;
                    } else {
                        state.layout.placements[target] = old_p;
                        state.tracker.restore_keep_weights(snap);
                        diag.rollbacks += 1;
                    }
                }
                state.refresh_incumbents();
                let raw = state.tracker.total_raw_loss();
                if raw == 0.0 {
                    state.best_feasible = Some(state.layout.snapshot());
                    return true;
                } else if raw < best_raw - 1e-9 {
                    best_raw = raw;
                    best_snapshot = (state.layout.snapshot(), state.tracker.snapshot());
                    no_improve = 0;
                } else {
                    no_improve += 1;
                }
                state.tracker.update_weights();
                diag.gls_weight_updates += 1;
            }
            if best_raw > 0.0 {
                strikes += 1;
                diag.separator_strikes += 1;
                // Roll back to the least-infeasible incumbent, keep GLS weights.
                state.layout = best_snapshot.0.snapshot();
                state.tracker.restore_keep_weights(best_snapshot.1.clone());
            } else {
                break;
            }
        }
        state.tracker.is_feasible()
    }

    /// Disruption: swap positions of the two largest-area items (escape local optimum).
    fn disrupt(&self, state: &mut SparrowState, instances: &[SPInstance], sheets: &[SheetShape], diag: &mut SparrowDiagnostics) {
        let n = state.layout.placements.len();
        if n < 2 {
            return;
        }
        let mut by_area: Vec<(usize, f64)> = (0..n)
            .map(|i| {
                let inst = &instances[state.layout.placements[i].instance_idx];
                (i, inst.part.width * inst.part.height)
            })
            .collect();
        by_area.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal).then(a.0.cmp(&b.0)));
        let (i, j) = (by_area[0].0, by_area[1].0);
        let pi = state.layout.placements[i].clone();
        let pj = state.layout.placements[j].clone();
        state.layout.placements[i].x = pj.x;
        state.layout.placements[i].y = pj.y;
        state.layout.placements[i].sheet_index = pj.sheet_index;
        state.layout.placements[j].x = pi.x;
        state.layout.placements[j].y = pi.y;
        state.layout.placements[j].sheet_index = pi.sheet_index;
        state.tracker.update_after_move(i, &state.layout, instances, sheets);
        state.tracker.update_after_move(j, &state.layout, instances, sheets);
        diag.exploration_disruptions_large_item_swap += 1;
    }

    /// Native solve: constructive seed -> exploration/separation -> final CDE validation.
    pub fn solve(&self, problem: SparrowProblem) -> SparrowSolveResult {
        let mut diag = SparrowDiagnostics {
            invoked: true,
            native_model_active: true,
            native_tracker_active: true,
            old_core_used: false,
            native_problem_instances: problem.instances.len(),
            ..SparrowDiagnostics::default()
        };
        super::cde_adapter::reset_query_cache();

        let instances = &problem.instances;
        let sheets = &problem.container.sheets;
        let started = Instant::now();
        let deadline = self.config.time_limit_s.max(0.1);
        let mut rng = DeterministicRng::new(self.config.seed);

        let seed_layout = build_native_constructive_seed(&problem);
        diag.seed_placements = seed_layout.placements.len();
        diag.seed_unplaced = problem.pre_unplaced.len();
        let mut state = SparrowState::new(seed_layout, instances, sheets);
        diag.initial_raw_loss = state.tracker.total_raw_loss();
        diag.initial_weighted_loss = state.tracker.total_weighted_loss();
        diag.collision_graph_initial_pairs = state.tracker.colliding_pairs();
        diag.boundary_violations_initial = state.tracker.boundary_violations();
        diag.best_infeasible_raw_loss = state.best_infeasible_raw_loss;

        // Exploration: separate; on failure, restore least-infeasible + disrupt; retry.
        let max_attempts = 8usize;
        let mut feasible = false;
        let mut pool: Vec<(f64, SparrowLayout)> = Vec::new();
        for attempt in 0..max_attempts {
            if started.elapsed().as_secs_f64() >= deadline {
                break;
            }
            diag.exploration_attempts += 1;
            if self.separate(&mut state, instances, sheets, &started, deadline, &mut rng, &mut diag) {
                feasible = true;
                break;
            }
            // Pool insert (least-infeasible), biased restore, disrupt.
            let raw = state.tracker.total_raw_loss();
            let at = pool.binary_search_by(|(l, _)| l.partial_cmp(&raw).unwrap_or(std::cmp::Ordering::Equal)).unwrap_or_else(|e| e);
            pool.insert(at, (raw, state.layout.snapshot()));
            pool.truncate(8);
            diag.exploration_pool_inserts += 1;
            if !pool.is_empty() {
                let sel = (self.config.seed as usize).wrapping_add(attempt) % ((pool.len() + 1) / 2).max(1);
                let restored = pool[sel].1.snapshot();
                diag.exploration_pool_restores += 1;
                state = SparrowState::new(restored, instances, sheets);
                self.disrupt(&mut state, instances, sheets, &mut diag);
            }
        }

        // Pick the layout to validate/emit: feasible incumbent if any.
        let final_layout = state.best_feasible.clone().unwrap_or_else(|| state.layout.snapshot());
        // Native final full CDE validation.
        let validated = SparrowCollisionTracker::final_validation(&final_layout, instances, sheets);
        let final_tracker = SparrowCollisionTracker::build(&final_layout, instances, sheets);
        diag.collision_graph_final_pairs = final_tracker.colliding_pairs();
        diag.boundary_violations_final = final_tracker.boundary_violations();
        diag.final_raw_loss = final_tracker.total_raw_loss();
        diag.final_weighted_loss = final_tracker.total_weighted_loss();
        diag.best_infeasible_raw_loss = state.best_infeasible_raw_loss;
        diag.best_infeasible_weighted_loss = state.best_infeasible_raw_loss;
        diag.converged = feasible && validated && final_tracker.is_feasible();
        diag.native_tracker_full_rebuilds = final_tracker.full_rebuilds;
        diag.iterations = diag.iterations.max(1);

        let feasible_final = diag.converged;
        let solution = SparrowSolution { layout: final_layout, feasible: feasible_final };
        let placements = solution.to_solver_projection(instances);
        SparrowSolveResult {
            placements,
            unplaced: problem.pre_unplaced,
            feasible: feasible_final,
            solution,
            diagnostics: diag,
        }
    }
}

// ---------------------------------------------------------------------------
// tests (native production types)
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
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

    fn ctx() -> RotationResolveContext {
        RotationResolveContext::legacy_default()
    }

    fn cfg(backend: CollisionBackendKind) -> SparrowConfig {
        SparrowConfig::from_solver_input(2.0, backend, ctx(), 7)
    }

    fn pl(idx: usize, x: f64, y: f64) -> SparrowPlacement {
        SparrowPlacement { instance_idx: idx, sheet_index: 0, x, y, rotation_deg: 0.0 }
    }

    #[test]
    fn from_solver_input_expands_instances_with_stable_indices() {
        let parts = vec![make_part("P", 30.0, 20.0, 3)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], cfg(CollisionBackendKind::Cde))
            .expect("problem");
        assert_eq!(problem.instances.len(), 3, "3 instances expanded from quantity 3");
        for (i, inst) in problem.instances.iter().enumerate() {
            assert_eq!(inst.idx, i, "native index is stable + dense");
            assert_eq!(inst.part_id, "P");
            assert!(!inst.instance_id.is_empty(), "external instance_id retained");
        }
        assert!(problem.pre_unplaced.is_empty());
    }

    #[test]
    fn from_solver_input_projects_never_fits_to_pre_unplaced() {
        // A 500x500 part can never fit a 200x200 sheet.
        let parts = vec![make_part("BIG", 500.0, 500.0, 1)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], cfg(CollisionBackendKind::Cde))
            .expect("problem");
        assert!(problem.instances.is_empty(), "never-fit part is not a placeable instance");
        assert_eq!(problem.pre_unplaced.len(), 1, "never-fit retained, not silently dropped");
        assert_eq!(problem.pre_unplaced[0].reason, "PART_NEVER_FITS_STOCK");
    }

    #[test]
    fn native_tracker_cde_detects_overlap_and_separation() {
        let parts = vec![make_part("P", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], cfg(CollisionBackendKind::Cde))
            .expect("problem");
        let insts = &problem.instances;

        // Overlapping placement => CDE-confirmed colliding pair, not feasible.
        let overlap = SparrowLayout { placements: vec![pl(0, 0.0, 0.0), pl(1, 10.0, 10.0)] };
        let t_overlap = SparrowCollisionTracker::build(&overlap, insts, &sheets);
        assert!(!t_overlap.unsupported, "rect-rect overlap must be CDE-supported");
        assert!(t_overlap.colliding_pairs() >= 1, "overlap yields >=1 colliding pair");
        assert!(!t_overlap.is_feasible(), "overlapping layout is infeasible");

        // Separated placement => zero pairs, feasible.
        let apart = SparrowLayout { placements: vec![pl(0, 0.0, 0.0), pl(1, 100.0, 100.0)] };
        let t_apart = SparrowCollisionTracker::build(&apart, insts, &sheets);
        assert_eq!(t_apart.colliding_pairs(), 0, "separated layout has no colliding pairs");
        assert_eq!(t_apart.boundary_violations(), 0, "separated layout inside sheet");
        assert!(t_apart.is_feasible(), "separated layout is feasible");
    }

    #[test]
    fn native_tracker_update_after_move_resolves_collision_incrementally() {
        let parts = vec![make_part("P", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], cfg(CollisionBackendKind::Cde))
            .expect("problem");
        let insts = &problem.instances;

        let mut layout = SparrowLayout { placements: vec![pl(0, 0.0, 0.0), pl(1, 10.0, 10.0)] };
        let mut tracker = SparrowCollisionTracker::build(&layout, insts, &sheets);
        assert!(!tracker.is_feasible(), "starts overlapping");
        let before = tracker.incremental_updates;

        // Move item 1 fully clear of item 0 and re-evaluate incrementally.
        layout.placements[1] = pl(1, 120.0, 120.0);
        tracker.update_after_move(1, &layout, insts, &sheets);
        assert_eq!(tracker.incremental_updates, before + 1, "incremental update counter advanced");
        assert_eq!(tracker.colliding_pairs(), 0, "collision resolved after move");
        assert!(tracker.is_feasible(), "feasible after separating move");
    }

    #[test]
    fn native_tracker_snapshot_restore_preserves_gls_weights() {
        let parts = vec![make_part("P", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], cfg(CollisionBackendKind::Cde))
            .expect("problem");
        let insts = &problem.instances;

        let layout = SparrowLayout { placements: vec![pl(0, 0.0, 0.0), pl(1, 10.0, 10.0)] };
        let mut tracker = SparrowCollisionTracker::build(&layout, insts, &sheets);
        let snap = tracker.snapshot();
        tracker.update_weights();
        let weighted_after_bump = tracker.total_weighted_loss();
        let raw = tracker.total_raw_loss();
        assert!(weighted_after_bump > raw, "GLS weight bump raises weighted loss above raw");

        // Restoring transient loss keeps the bumped weights (Sparrow GLS semantics).
        tracker.restore_keep_weights(snap);
        assert!(
            (tracker.total_weighted_loss() - weighted_after_bump).abs() < 1e-9,
            "weights survive snapshot/restore"
        );
    }

    #[test]
    fn native_optimizer_solve_feasible_projects_all_placements() {
        let parts = vec![make_part("P", 30.0, 20.0, 4)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let config = cfg(CollisionBackendKind::Cde);
        let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], config.clone())
            .expect("problem");
        let n = problem.instances.len();
        let result = SparrowOptimizer::new(config).solve(problem);

        assert!(result.feasible, "tiny problem converges natively");
        assert!(result.diagnostics.converged, "diagnostics report convergence");
        assert_eq!(result.placements.len(), n, "every instance projected to a Placement");
        assert_eq!(result.diagnostics.collision_graph_final_pairs, 0, "no residual collisions");
        assert_eq!(result.diagnostics.boundary_violations_final, 0, "no residual boundary violations");
        // Native-model proof flags.
        assert!(result.diagnostics.native_model_active);
        assert!(result.diagnostics.native_tracker_active);
        assert!(!result.diagnostics.old_core_used);
        assert_eq!(result.diagnostics.native_problem_instances, n);
        // Compression stays out of scope.
        assert_eq!(result.diagnostics.compression_passes, 0, "compression disabled by default");
    }

    #[test]
    fn native_optimizer_solve_is_deterministic_for_same_seed() {
        let parts = vec![make_part("P", 25.0, 25.0, 5)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let run = || {
            let config = cfg(CollisionBackendKind::Cde);
            let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], config.clone())
                .expect("problem");
            SparrowOptimizer::new(config).solve(problem).placements
        };
        let a = run();
        let b = run();
        assert_eq!(a.len(), b.len(), "same placed count");
        for (pa, pb) in a.iter().zip(b.iter()) {
            assert_eq!(pa.instance_id, pb.instance_id);
            assert!((pa.x - pb.x).abs() < 1e-9 && (pa.y - pb.y).abs() < 1e-9, "deterministic coords");
            assert!((pa.rotation_deg - pb.rotation_deg).abs() < 1e-9, "deterministic rotation");
        }
    }
}
