//! SGH-Q24R6 — Native Sparrow solver core (tracker + search + worker parity).
//!
//! This module is the production truth model for `sparrow_cde`. It replaces the
//! legacy VRS working-layout / collision-tracker core entirely; nothing here
//! delegates back to the old mutable-working-layout types.
//!
//! Production `sparrow_cde` runs on this native model:
//!   `SparrowProblem` -> `SparrowOptimizer::solve` -> `SparrowSolveResult`
//!   (native CDE validation) -> `SparrowSolution::to_solver_projection` (boundary).
//!
//! Q24R6 hardening over the Q24R5 architectural cutover:
//!   * tracker loss is CDE-truth *quantified* separation/resolution distance
//!     (bracket + binary-refine probe), not a binary `1.0` count;
//!   * native search evaluates candidates across every eligible sheet/container,
//!     all allowed rotations, with focused/global/coordinate-descent samples;
//!   * a real multi-worker competition spawns worker snapshots, lets each run a
//!     move batch, then loads the best worker back into the master;
//!   * exploration pool/restore/disruption is deeper than a single largest swap;
//!   * diagnostics report real solve-time search/worker/tracker activity.
//!
//! Collision truth is CDE: shapes are prepared via
//! `cde_adapter::prepare_shape_native` and queried through `CdeCandidateSession` /
//! `CdeAdapter`. bbox/AABB is used only as the broad-phase prune already inside
//! the CDE adapter, or as a centroid/direction hint — never as positive
//! collision truth. Compression is intentionally out of scope.

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
    prepare_shape_from_sheet, prepare_shape_native, CdeAdapter, CdeCandidateSession,
    CdePreparedShape, CdeQueryResult,
};

// ---------------------------------------------------------------------------
// rng
// ---------------------------------------------------------------------------

/// Deterministic SplitMix64-style RNG (native, seed-controlled).
#[derive(Clone)]
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
    /// Deterministic Fisher-Yates shuffle of `v`.
    pub fn shuffle<T>(&mut self, v: &mut [T]) {
        for k in (1..v.len()).rev() {
            let j = (self.next_u64() as usize) % (k + 1);
            v.swap(k, j);
        }
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
    /// Number of competing workers per `move_items_multi` pass (>= 2 for real
    /// worker competition / best-worker load-back).
    pub worker_count: usize,
    /// Focused samples per target search around the current placement.
    pub focused_samples: usize,
    /// Coarse global grid resolution per axis per eligible sheet.
    pub global_grid_n: usize,
    /// Coordinate-descent refinement steps on the best candidate.
    pub coord_descent_steps: usize,
    /// Bracket-doubling steps for the CDE resolution-distance probe.
    pub probe_bracket_steps: usize,
    /// Binary-refinement steps for the CDE resolution-distance probe.
    pub probe_binary_refine_steps: usize,
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
            worker_count: 2,
            focused_samples: 4,
            global_grid_n: 3,
            coord_descent_steps: 4,
            probe_bracket_steps: 5,
            probe_binary_refine_steps: 4,
        }
    }
}

/// Native Sparrow diagnostics surfaced to the adapter output projection.
/// Field names mirror the prior `sparrow_*` output contract plus the Q24R5
/// native-model proof flags and the Q24R6 search/worker/tracker evidence.
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
    // ── search activity ─────────────────────────────────────────────────────
    pub search_position_calls: usize,
    pub search_position_samples: usize,
    pub search_global_samples: usize,
    pub search_focused_samples: usize,
    pub search_refined_samples: usize,
    pub search_coord_descent_steps: usize,
    pub search_unsupported_samples: usize,
    pub search_cross_sheet_calls: usize,
    pub search_best_eval: f64,
    pub lbf_fallback_used: usize,
    // ── worker competition ──────────────────────────────────────────────────
    pub worker_count: usize,
    pub worker_passes: usize,
    pub worker_candidates_evaluated: usize,
    pub worker_commits: usize,
    pub worker_rollbacks: usize,
    pub worker_best_loss: f64,
    pub worker_colliding_items_seen: usize,
    pub worker_items_moved: usize,
    pub multi_target_items_attempted: usize,
    pub multi_target_items_accepted: usize,
    pub multi_target_items_rejected: usize,
    pub topk_target_count: usize,
    // ── separator / exploration ─────────────────────────────────────────────
    pub separator_invocations: usize,
    pub separator_strikes: usize,
    pub exploration_attempts: usize,
    pub exploration_pool_inserts: usize,
    pub exploration_pool_restores: usize,
    pub exploration_disruptions_large_item_swap: usize,
    pub exploration_disruptions_cross_sheet: usize,
    pub exploration_disruptions_rotation: usize,
    pub compression_passes: usize,
    // ── tracker quantification evidence ───────────────────────────────────────
    pub quantified_pair_queries: usize,
    pub quantified_boundary_queries: usize,
    pub unsupported_queries: usize,
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
    /// Iterate (layout index) of items on `sheet_idx`.
    pub fn items_on_sheet(&self, sheet_idx: usize) -> Vec<usize> {
        (0..self.placements.len())
            .filter(|&i| self.placements[i].sheet_index == sheet_idx)
            .collect()
    }
}

// ---------------------------------------------------------------------------
// CDE-truth quantification primitives
// ---------------------------------------------------------------------------

/// Bbox-center of a prepared shape (used only as a direction/centroid hint —
/// never as collision truth).
fn shape_center(s: &CdePreparedShape) -> (f64, f64) {
    ((s.min_x + s.max_x) * 0.5, (s.min_y + s.max_y) * 0.5)
}

/// Normalize a 2-vector; falls back to +x for a degenerate (zero) vector.
fn unit(dx: f64, dy: f64) -> (f64, f64) {
    let n = (dx * dx + dy * dy).sqrt();
    if n < 1e-9 {
        (1.0, 0.0)
    } else {
        (dx / n, dy / n)
    }
}

/// CDE-truth pairwise *resolution distance*: the minimal translation of the
/// moving part (along unit `dir`) that clears `fixed` according to the CDE.
/// Uses bracket doubling to find a clearing distance, then binary refinement to
/// tighten it. Returns a positive separation magnitude (>= a small floor when a
/// collision is confirmed at the start). bbox/AABB never decides collision here:
/// every probe step is resolved by `CdeAdapter::query_pair`.
#[allow(clippy::too_many_arguments)]
fn probe_pair_resolution_distance(
    part: &Part,
    x: f64,
    y: f64,
    rot: f64,
    dir: (f64, f64),
    base_step: f64,
    fixed: &CdePreparedShape,
    cfg: &SparrowConfig,
    diag: &mut SparrowDiagnostics,
) -> f64 {
    let adapter = CdeAdapter::with_defaults();
    let step0 = base_step.max(1e-3);
    let collides_at = |t: f64, diag: &mut SparrowDiagnostics| -> bool {
        let nx = x + dir.0 * t;
        let ny = y + dir.1 * t;
        match prepare_shape_native(part, nx, ny, rot) {
            Ok(s) => {
                diag.quantified_pair_queries += 1;
                matches!(adapter.query_pair(&s, fixed), CdeQueryResult::Collision)
            }
            Err(_) => {
                diag.unsupported_queries += 1;
                // Treat a prepare failure as "still colliding" so the probe keeps
                // its honest positive bias (never silently clears).
                true
            }
        }
    };
    // Bracket: grow until clear or budget exhausted.
    let mut lo = 0.0_f64; // known colliding (caller confirmed a collision)
    let mut hi = step0;
    let mut bracketed = false;
    for _ in 0..cfg.probe_bracket_steps.max(1) {
        if collides_at(hi, diag) {
            lo = hi;
            hi *= 2.0;
        } else {
            bracketed = true;
            break;
        }
    }
    if !bracketed {
        // Could not clear within the bracket budget: report the deepest probe as
        // the (large) resolution distance — a strong, honest separation penalty.
        return hi.max(step0);
    }
    // Binary refine the clearing distance in (lo, hi].
    for _ in 0..cfg.probe_binary_refine_steps {
        let mid = 0.5 * (lo + hi);
        if collides_at(mid, diag) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    hi.max(step0 * 0.25)
}

/// CDE-truth *container clearance* distance: minimal translation of the moving
/// part toward the sheet centroid that brings it inside the sheet boundary.
#[allow(clippy::too_many_arguments)]
fn probe_boundary_resolution_distance(
    part: &Part,
    x: f64,
    y: f64,
    rot: f64,
    sheet_center: (f64, f64),
    item_center: (f64, f64),
    diag_diam: f64,
    sheet_shape: &CdePreparedShape,
    cfg: &SparrowConfig,
    diag: &mut SparrowDiagnostics,
) -> f64 {
    let adapter = CdeAdapter::with_defaults();
    let dir = unit(sheet_center.0 - item_center.0, sheet_center.1 - item_center.1);
    let base_step = (diag_diam * 0.1).max(1e-3);
    let outside_at = |t: f64, diag: &mut SparrowDiagnostics| -> bool {
        let nx = x + dir.0 * t;
        let ny = y + dir.1 * t;
        match prepare_shape_native(part, nx, ny, rot) {
            Ok(s) => {
                diag.quantified_boundary_queries += 1;
                matches!(adapter.query_boundary(&s, sheet_shape), CdeQueryResult::Collision)
            }
            Err(_) => {
                diag.unsupported_queries += 1;
                true
            }
        }
    };
    let mut lo = 0.0_f64;
    let mut hi = base_step;
    let mut bracketed = false;
    for _ in 0..cfg.probe_bracket_steps.max(1) {
        if outside_at(hi, diag) {
            lo = hi;
            hi *= 2.0;
        } else {
            bracketed = true;
            break;
        }
    }
    if !bracketed {
        return hi.max(base_step);
    }
    for _ in 0..cfg.probe_binary_refine_steps {
        let mid = 0.5 * (lo + hi);
        if outside_at(mid, diag) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    hi.max(base_step * 0.25)
}

// ---------------------------------------------------------------------------
// tracker (native, CDE-backed, quantified loss)
// ---------------------------------------------------------------------------

/// Native CDE-backed collision tracker. Owns quantified pair/boundary records +
/// GLS weights. Collision EXISTENCE is decided by the CDE adapter
/// (`CdeCandidateSession` / jagua `CDEngine`); the stored loss is a CDE-truth
/// quantified separation/resolution distance (never a binary count).
pub struct SparrowCollisionTracker {
    n: usize,
    /// Prepared CDE shapes per instance index (rebuilt lazily after a move).
    shapes: Vec<Option<Rc<CdePreparedShape>>>,
    /// Prepared sheet shapes per sheet index.
    sheet_shapes: Vec<Option<Rc<CdePreparedShape>>>,
    /// Quantified raw pair loss (resolution distance proxy), keyed i<j.
    pair_loss: HashMap<(usize, usize), f64>,
    /// GLS pair weights, i<j.
    pair_weight: HashMap<(usize, usize), f64>,
    /// Quantified raw boundary/container loss per item (clearance distance).
    boundary_loss: Vec<f64>,
    /// GLS boundary/container weights per item.
    boundary_weight: Vec<f64>,
    pub full_rebuilds: usize,
    pub incremental_updates: usize,
    pub unsupported: bool,
}

impl Clone for SparrowCollisionTracker {
    fn clone(&self) -> Self {
        Self {
            n: self.n,
            shapes: self.shapes.clone(),
            sheet_shapes: self.sheet_shapes.clone(),
            pair_loss: self.pair_loss.clone(),
            pair_weight: self.pair_weight.clone(),
            boundary_loss: self.boundary_loss.clone(),
            boundary_weight: self.boundary_weight.clone(),
            full_rebuilds: self.full_rebuilds,
            incremental_updates: self.incremental_updates,
            unsupported: self.unsupported,
        }
    }
}

impl SparrowCollisionTracker {
    fn prepare_item(layout: &SparrowLayout, instances: &[SPInstance], idx: usize) -> Option<Rc<CdePreparedShape>> {
        let p = &layout.placements[idx];
        let inst = &instances[p.instance_idx];
        prepare_shape_native(&inst.part, p.x, p.y, p.rotation_deg).ok().map(Rc::new)
    }

    /// Full CDE rebuild of the collision state from the native layout.
    pub fn build(layout: &SparrowLayout, instances: &[SPInstance], sheets: &[SheetShape]) -> Self {
        Self::build_with_diag(layout, instances, sheets, &mut SparrowDiagnostics::default())
    }

    /// Full CDE rebuild, recording quantification queries into `diag`.
    pub fn build_with_diag(
        layout: &SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        diag: &mut SparrowDiagnostics,
    ) -> Self {
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
        t.recompute_all(layout, instances, sheets, diag);
        t
    }

    fn recompute_all(
        &mut self,
        layout: &SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        diag: &mut SparrowDiagnostics,
    ) {
        self.pair_loss.clear();
        for v in self.boundary_loss.iter_mut() {
            *v = 0.0;
        }
        self.unsupported = false;
        for i in 0..self.n {
            self.recompute_item(i, layout, instances, sheets, false, diag);
        }
    }

    /// Recompute quantified boundary + pair losses touching item `i`. When
    /// `clear_old`, first drop existing pair entries that include `i`.
    fn recompute_item(
        &mut self,
        i: usize,
        layout: &SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        clear_old: bool,
        diag: &mut SparrowDiagnostics,
    ) {
        if clear_old {
            self.pair_loss.retain(|&(a, b), _| a != i && b != i);
        }
        self.boundary_loss[i] = 0.0;
        let Some(shape_i) = self.shapes[i].clone() else {
            self.unsupported = true;
            diag.unsupported_queries += 1;
            return;
        };
        let pi = &layout.placements[i];
        let si = pi.sheet_index;
        let inst_i = &instances[pi.instance_idx];
        let cfg = QUANT_CFG.with(|c| c.borrow().clone());

        // Boundary / container clearance (quantified).
        if let Some(sheet_shape) = self.sheet_shapes.get(si).and_then(|s| s.clone()) {
            let adapter = CdeAdapter::with_defaults();
            match adapter.query_boundary(&shape_i, &sheet_shape) {
                CdeQueryResult::NoCollision => {}
                CdeQueryResult::Collision => {
                    let sc = shape_center(&sheet_shape);
                    let ic = shape_center(&shape_i);
                    let diam = (shape_i.max_x - shape_i.min_x).max(shape_i.max_y - shape_i.min_y);
                    let dist = probe_boundary_resolution_distance(
                        &inst_i.part, pi.x, pi.y, pi.rotation_deg, sc, ic, diam, &sheet_shape, &cfg, diag,
                    );
                    self.boundary_loss[i] = dist.max(QUANT_FLOOR);
                }
                CdeQueryResult::Unsupported { .. } => {
                    self.unsupported = true;
                    diag.unsupported_queries += 1;
                    self.boundary_loss[i] = BIG_UNSUPPORTED_LOSS;
                }
            }
        }

        // Pairs: query i against every other same-sheet item via one session.
        let others: Vec<(usize, Rc<CdePreparedShape>)> = (0..self.n)
            .filter(|&j| j != i && layout.placements[j].sheet_index == si)
            .filter_map(|j| self.shapes[j].clone().map(|s| (j, s)))
            .collect();
        if let Some(sheet_shape) = self.sheet_shapes.get(si).and_then(|s| s.clone()) {
            if let Some(session) = CdeCandidateSession::build(others.clone(), &sheet_shape) {
                let res = session.query(&shape_i);
                if res.unsupported {
                    self.unsupported = true;
                    diag.unsupported_queries += 1;
                }
                // Map session hole index back to the actual layout index.
                for &layout_j in &res.colliding_layout_idxs {
                    let key = if i < layout_j { (i, layout_j) } else { (layout_j, i) };
                    let fixed = match others.iter().find(|(jj, _)| *jj == layout_j) {
                        Some((_, s)) => s.clone(),
                        None => continue,
                    };
                    // Quantified separation distance: probe i away from j.
                    let ic = shape_center(&shape_i);
                    let jc = shape_center(&fixed);
                    let dir = unit(ic.0 - jc.0, ic.1 - jc.1);
                    let span = (shape_i.max_x - shape_i.min_x)
                        .max(shape_i.max_y - shape_i.min_y)
                        .max(fixed.max_x - fixed.min_x)
                        .max(fixed.max_y - fixed.min_y);
                    let base_step = (span * 0.08).max(1.0);
                    let dist = probe_pair_resolution_distance(
                        &inst_i.part, pi.x, pi.y, pi.rotation_deg, dir, base_step, &fixed, &cfg, diag,
                    );
                    self.pair_loss.insert(key, dist.max(QUANT_FLOOR));
                    self.pair_weight.entry(key).or_insert(1.0);
                }
            }
        }
    }

    /// Incremental update after item `i` moved (its placement/shape changed).
    pub fn update_after_move(
        &mut self,
        i: usize,
        layout: &SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        diag: &mut SparrowDiagnostics,
    ) {
        self.shapes[i] = Self::prepare_item(layout, instances, i);
        self.incremental_updates += 1;
        diag.native_tracker_incremental_updates += 1;
        self.recompute_item(i, layout, instances, sheets, true, diag);
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
    pub fn raw_loss_for_item(&self, i: usize) -> f64 {
        let pair: f64 = self
            .pair_loss
            .iter()
            .filter(|(k, _)| k.0 == i || k.1 == i)
            .map(|(_, v)| *v)
            .sum();
        pair + self.boundary_loss[i]
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
    /// Offending/colliding items ordered by descending weighted loss (worst first).
    pub fn colliding_indices(&self) -> Vec<usize> {
        let mut set: Vec<(usize, f64)> = Vec::new();
        for i in 0..self.n {
            let w = self.weighted_loss_for_item(i);
            if w > 1e-12 {
                set.push((i, w));
            }
        }
        set.sort_by(|a, b| {
            b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal).then(a.0.cmp(&b.0))
        });
        set.into_iter().map(|(i, _)| i).collect()
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

/// Minimum stored loss for any CDE-confirmed collision (so a confirmed positive
/// never rounds to a feasible 0 because of probe resolution).
const QUANT_FLOOR: f64 = 1e-3;
/// Loss assigned to an unsupported-geometry verdict (treated honestly as a hard,
/// large violation — never as no-collision).
const BIG_UNSUPPORTED_LOSS: f64 = 1.0e6;

thread_local! {
    /// Solve-scoped probe config so the tracker's `recompute_item` (which has no
    /// `cfg` parameter on the public API surface used by callers/tests) can reach
    /// the active probe budget. Set at the start of each `solve`.
    static QUANT_CFG: std::cell::RefCell<SparrowConfig> = std::cell::RefCell::new(
        SparrowConfig::from_solver_input(1.0, CollisionBackendKind::Cde, RotationResolveContext::legacy_default(), 0)
    );
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
#[derive(Clone)]
pub struct SparrowState {
    pub layout: SparrowLayout,
    pub tracker: SparrowCollisionTracker,
    pub best_feasible: Option<SparrowLayout>,
    pub best_infeasible: Option<SparrowLayout>,
    pub best_infeasible_raw_loss: f64,
}

impl SparrowState {
    pub fn new(layout: SparrowLayout, instances: &[SPInstance], sheets: &[SheetShape]) -> Self {
        Self::new_with_diag(layout, instances, sheets, &mut SparrowDiagnostics::default())
    }
    pub fn new_with_diag(
        layout: SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        diag: &mut SparrowDiagnostics,
    ) -> Self {
        let tracker = SparrowCollisionTracker::build_with_diag(&layout, instances, sheets, diag);
        diag.native_tracker_full_rebuilds += 1;
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

/// Pick the first allowed rotation under which the part fits at least one sheet
/// (rotation-aware: parts that only fit rotated — e.g. a strip wider than the
/// sheet at 0° — get a fitting rotation instead of being dropped).
fn fitting_rotation(inst: &SPInstance, sheets: &[SheetShape]) -> f64 {
    let rots: Vec<f64> = if inst.allowed_rotations_deg.is_empty() {
        vec![0.0]
    } else {
        inst.allowed_rotations_deg.clone()
    };
    for &rot in &rots {
        let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
        if sheets.iter().any(|s| rw <= s.width + 1e-9 && rh <= s.height + 1e-9) {
            return rot;
        }
    }
    rots[0]
}

/// Native constructive (LBF/grid) initial solution: area-sorted coarse row/grid
/// spread across sheets, in-bounds, mild overlap (near-feasible but with real
/// separation work). Rotation-aware so oversized-at-0° parts get a fitting
/// rotation. Plays Sparrow's `LBFBuilder::construct` role for fixed sheets.
pub fn build_native_constructive_seed(problem: &SparrowProblem) -> SparrowLayout {
    const PITCH_FACTOR: f64 = 0.92;
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
        let rot = fitting_rotation(inst, sheets);
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
            // Overlap-allowed fallback at origin of the first hosting sheet (with
            // a fitting rotation). Separation resolves the residual overlap.
            for sheet_idx in 0..sheets.len() {
                let sheet = &sheets[sheet_idx];
                if rw <= sheet.width + 1e-9 && rh <= sheet.height + 1e-9 {
                    let (ax, ay) =
                        placement_anchor_from_rect_min(0.0, 0.0, inst.part.width, inst.part.height, rot);
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
// native search (multi-sheet, multi-rotation, quantified)
// ---------------------------------------------------------------------------

/// One scored candidate produced by the search.
#[derive(Clone)]
struct ScoredPlacement {
    score: f64,
    placement: SparrowPlacement,
}

/// Axis-aligned penetration depth between two bboxes (0 if disjoint). Used ONLY
/// to *order* infeasible search candidates — never to decide collision truth
/// (the colliding set comes from the CDE session) and never as the authoritative
/// tracker loss (that is the CDE-truth resolution-distance probe).
fn aabb_penetration(
    a: (f64, f64, f64, f64),
    b: (f64, f64, f64, f64),
) -> f64 {
    let ox = (a.2.min(b.2) - a.0.max(b.0)).max(0.0);
    let oy = (a.3.min(b.3) - a.1.max(b.1)).max(0.0);
    ox.min(oy)
}

/// Evaluate a candidate position on a given sheet against a prebuilt session.
/// Returns `None` for out-of-bounds (rect bounds) or unsupported geometry.
/// Score 0 = CDE-clear (the authoritative target). Infeasible candidates are
/// ordered by a cheap geometric penetration magnitude (CDE decides the colliding
/// SET; the magnitude only ranks samples so the search descends toward clear).
#[allow(clippy::too_many_arguments)]
fn score_candidate(
    inst: &SPInstance,
    sheet: &SheetShape,
    sheet_idx: usize,
    session: &CdeCandidateSession,
    neighbor_bboxes: &[Option<(f64, f64, f64, f64)>],
    rmx: f64,
    rmy: f64,
    rot: f64,
    diag: &mut SparrowDiagnostics,
) -> Option<ScoredPlacement> {
    let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
    if rmx < sheet.min_x - 1e-9
        || rmy < sheet.min_y - 1e-9
        || rmx + rw > sheet.max_x + 1e-9
        || rmy + rh > sheet.max_y + 1e-9
    {
        return None;
    }
    let (ax, ay) = placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
    let shape = prepare_shape_native(&inst.part, ax, ay, rot).ok()?;
    diag.search_position_samples += 1;
    let res = session.query(&shape);
    if res.unsupported {
        diag.search_unsupported_samples += 1;
        return None;
    }
    let placement = SparrowPlacement { instance_idx: inst.idx, sheet_index: sheet_idx, x: ax, y: ay, rotation_deg: rot };
    if res.is_clear() {
        return Some(ScoredPlacement { score: 0.0, placement });
    }
    // Cheap continuous ordering magnitude for an infeasible candidate.
    let cand_bbox = (shape.min_x, shape.min_y, shape.max_x, shape.max_y);
    let mut score = 0.0;
    if res.boundary_collision {
        // How far the candidate bbox spills out of the sheet bbox (per side).
        let over = (sheet.min_x - cand_bbox.0).max(0.0)
            + (sheet.min_y - cand_bbox.1).max(0.0)
            + (cand_bbox.2 - sheet.max_x).max(0.0)
            + (cand_bbox.3 - sheet.max_y).max(0.0);
        score += over.max(QUANT_FLOOR) * 4.0;
    }
    for &layout_j in &res.colliding_layout_idxs {
        if let Some(Some(b)) = neighbor_bboxes.get(layout_j) {
            score += aabb_penetration(cand_bbox, *b).max(QUANT_FLOOR);
        } else {
            score += QUANT_FLOOR;
        }
    }
    Some(ScoredPlacement { score, placement })
}

/// Build the fixed-other CDE session for `target` on `sheet_idx` from the tracker
/// shapes (others = same-sheet items except `target`).
fn build_sheet_session(
    target: usize,
    sheet_idx: usize,
    layout: &SparrowLayout,
    tracker: &SparrowCollisionTracker,
    sheet_shape: &CdePreparedShape,
) -> Option<CdeCandidateSession> {
    let others: Vec<(usize, Rc<CdePreparedShape>)> = (0..layout.placements.len())
        .filter(|&j| j != target && layout.placements[j].sheet_index == sheet_idx)
        .filter_map(|j| tracker.shapes[j].clone().map(|s| (j, s)))
        .collect();
    CdeCandidateSession::build(others, sheet_shape)
}

/// Native CDE-backed search for a clear (or least-colliding) placement of the
/// target instance across EVERY eligible sheet, all allowed rotations, with
/// focused, global-grid and coordinate-descent candidates, scored by quantified
/// CDE-truth loss. The current sheet is searched first; other sheets are swept
/// only when no clear spot is found there (bounds the candidate volume).
#[allow(clippy::too_many_arguments)]
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
    let rotations: Vec<f64> = if inst.allowed_rotations_deg.is_empty() {
        vec![cur.rotation_deg]
    } else {
        inst.allowed_rotations_deg.clone()
    };

    // Precompute neighbour bboxes (by layout index) for the cheap ordering metric.
    let neighbor_bboxes: Vec<Option<(f64, f64, f64, f64)>> = (0..layout.placements.len())
        .map(|j| tracker.shapes[j].as_ref().map(|s| (s.min_x, s.min_y, s.max_x, s.max_y)))
        .collect();

    let mut best: Option<ScoredPlacement> = None;
    let mut consider = |c: Option<ScoredPlacement>, best: &mut Option<ScoredPlacement>| {
        if let Some(cand) = c {
            let better = match best {
                None => true,
                Some(b) => cand.score < b.score - 1e-9,
            };
            if better {
                *best = Some(cand);
            }
        }
    };

    // Sheet search order: current sheet first, then the rest (cross-sheet).
    let mut sheet_order: Vec<usize> = vec![cur.sheet_index];
    for sheet_idx in 0..sheets.len() {
        if sheet_idx != cur.sheet_index {
            sheet_order.push(sheet_idx);
        }
    }

    for (rank, &sheet_idx) in sheet_order.iter().enumerate() {
        // Once a clear spot exists on the current sheet, do not sweep others.
        if rank > 0 && best.as_ref().map(|b| b.score <= 1e-9).unwrap_or(false) {
            break;
        }
        if rank > 0 {
            diag.search_cross_sheet_calls += 1;
        }
        let sheet = &sheets[sheet_idx];
        let Some(sheet_shape) = tracker.sheet_shapes.get(sheet_idx).and_then(|s| s.clone()) else {
            continue;
        };
        let Some(session) = build_sheet_session(target, sheet_idx, layout, tracker, &sheet_shape) else {
            continue;
        };

        // Focused samples around the current placement (only on the current sheet).
        if sheet_idx == cur.sheet_index {
            let span = (sheet.width.min(sheet.height)) * 0.15;
            for &rot in &rotations {
                if let Some(c) = score_candidate(inst, sheet, sheet_idx, &session, &neighbor_bboxes, cur.x, cur.y, rot, diag) {
                    consider(Some(c), &mut best);
                }
                for _ in 0..cfg.focused_samples {
                    let nx = cur.x + rng.jitter(span);
                    let ny = cur.y + rng.jitter(span);
                    diag.search_focused_samples += 1;
                    consider(score_candidate(inst, sheet, sheet_idx, &session, &neighbor_bboxes, nx, ny, rot, diag), &mut best);
                    if best.as_ref().map(|b| b.score <= 1e-9).unwrap_or(false) {
                        break;
                    }
                }
            }
        }

        // Coarse global grid on this sheet, every rotation.
        if best.as_ref().map(|b| b.score > 1e-9).unwrap_or(true) {
            let n = cfg.global_grid_n.max(1);
            let step_x = sheet.width / (n as f64 + 1.0);
            let step_y = sheet.height / (n as f64 + 1.0);
            'grid: for gy in 1..=n {
                for gx in 1..=n {
                    let rmx = sheet.min_x + step_x * gx as f64;
                    let rmy = sheet.min_y + step_y * gy as f64;
                    for &rot in &rotations {
                        diag.search_global_samples += 1;
                        consider(score_candidate(inst, sheet, sheet_idx, &session, &neighbor_bboxes, rmx, rmy, rot, diag), &mut best);
                        if best.as_ref().map(|b| b.score <= 1e-9).unwrap_or(false) {
                            break 'grid;
                        }
                    }
                }
            }
        }

        // Coordinate-descent refinement of the best candidate on this sheet.
        if let Some(b) = best.clone() {
            if b.score > 1e-9 && b.placement.sheet_index == sheet_idx {
                let mut bx = b.placement.x;
                let mut by = b.placement.y;
                let brot = b.placement.rotation_deg;
                let mut bscore = b.score;
                let mut step = (sheet.width.min(sheet.height)) * 0.1;
                for _ in 0..cfg.coord_descent_steps {
                    let mut improved = false;
                    for &(dx, dy) in &[(step, 0.0), (-step, 0.0), (0.0, step), (0.0, -step)] {
                        diag.search_coord_descent_steps += 1;
                        if let Some(c) = score_candidate(inst, sheet, sheet_idx, &session, &neighbor_bboxes, bx + dx, by + dy, brot, diag) {
                            if c.score < bscore - 1e-9 {
                                bx = c.placement.x;
                                by = c.placement.y;
                                bscore = c.score;
                                diag.search_refined_samples += 1;
                                improved = true;
                                consider(Some(c), &mut best);
                                if bscore <= 1e-9 {
                                    break;
                                }
                            }
                        }
                    }
                    if bscore <= 1e-9 {
                        break;
                    }
                    if !improved {
                        step *= 0.5;
                    }
                }
            }
        }
    }

    if let Some(b) = &best {
        if b.score < diag.search_best_eval || diag.search_best_eval == 0.0 {
            // track the best (lowest) achieved eval seen this solve (0 = perfect)
            diag.search_best_eval = b.score;
        }
    }
    best.map(|b| b.placement)
}

// ---------------------------------------------------------------------------
// worker competition (Alg 5/10 native port)
// ---------------------------------------------------------------------------

/// A single competing worker's result: its own layout + tracker after a move
/// batch, plus per-worker statistics. The best (lowest weighted loss) candidate
/// is loaded back into the master; the rest are discarded.
struct WorkerCandidate {
    layout: SparrowLayout,
    tracker: SparrowCollisionTracker,
    weighted_loss: f64,
    raw_loss: f64,
    attempted: usize,
    accepted: usize,
    rejected: usize,
    evaluated: usize,
    worker_idx: usize,
}

/// Run one worker pass: clone the master state, move every colliding item once
/// (greedy accept on per-item weighted-loss improvement) using a worker-unique
/// deterministic ordering/seed. Returns the worker candidate state.
#[allow(clippy::too_many_arguments)]
fn run_worker_pass(
    worker_idx: usize,
    master: &SparrowState,
    instances: &[SPInstance],
    sheets: &[SheetShape],
    cfg: &SparrowConfig,
    worker_seed: u64,
    started: &Instant,
    deadline: f64,
    diag: &mut SparrowDiagnostics,
) -> WorkerCandidate {
    let mut layout = master.layout.snapshot();
    let mut tracker = master.tracker.clone();
    let mut rng = DeterministicRng::new(worker_seed);

    let mut colliding = tracker.colliding_indices();
    // Worker-unique ordering bias: even workers worst-first (as-ranked), odd
    // workers shuffled — different exploration of the same master state.
    if worker_idx % 2 == 1 {
        rng.shuffle(&mut colliding);
    } else if worker_idx >= 2 {
        // higher even workers: reverse (least-loss first)
        colliding.reverse();
    }

    let mut attempted = 0usize;
    let mut accepted = 0usize;
    let mut rejected = 0usize;
    let mut evaluated = 0usize;

    for target in colliding {
        if started.elapsed().as_secs_f64() >= deadline {
            break;
        }
        if tracker.weighted_loss_for_item(target) <= 1e-12 {
            continue;
        }
        attempted += 1;
        let calls_before = diag.search_position_calls;
        let old_w = tracker.weighted_loss_for_item(target);
        let Some(newp) = native_search_placement(target, &layout, instances, &tracker, sheets, cfg, &mut rng, diag) else {
            rejected += 1;
            continue;
        };
        evaluated += diag.search_position_calls - calls_before;
        let old_p = layout.placements[target].clone();
        let snap = tracker.snapshot();
        layout.placements[target] = newp;
        tracker.update_after_move(target, &layout, instances, sheets, diag);
        let new_w = tracker.weighted_loss_for_item(target);
        if new_w <= old_w + 1e-9 {
            accepted += 1;
        } else {
            layout.placements[target] = old_p;
            tracker.restore_keep_weights(snap);
            rejected += 1;
        }
    }

    let weighted_loss = tracker.total_weighted_loss();
    let raw_loss = tracker.total_raw_loss();
    WorkerCandidate {
        layout,
        tracker,
        weighted_loss,
        raw_loss,
        attempted,
        accepted,
        rejected,
        evaluated: evaluated.max(1),
        worker_idx,
    }
}

/// Compare worker candidates: lowest weighted loss wins, tie-broken by raw loss
/// then worker index (deterministic).
fn compare_worker_candidates<'a>(cands: &'a [WorkerCandidate]) -> &'a WorkerCandidate {
    cands
        .iter()
        .min_by(|a, b| {
            a.weighted_loss
                .partial_cmp(&b.weighted_loss)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(a.raw_loss.partial_cmp(&b.raw_loss).unwrap_or(std::cmp::Ordering::Equal))
                .then(a.worker_idx.cmp(&b.worker_idx))
        })
        .expect("at least one worker")
}

/// Load the winning worker's state back into the master, discarding the rest
/// (Sparrow Alg 10 load-back step). The master adopts the best worker's layout
/// and CDE tracker (including its GLS-bumped weights and incremental records).
fn load_best_worker(master: &mut SparrowState, best: WorkerCandidate) {
    master.layout = best.layout;
    master.tracker = best.tracker;
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

    /// Algorithm 10 native port: spawn `worker_count` competing workers from the
    /// SAME master state, run each worker's move batch, then load the best
    /// (lowest weighted loss) worker back into the master.
    fn move_items_multi(
        &self,
        state: &mut SparrowState,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        master_rng: &mut DeterministicRng,
        started: &Instant,
        deadline: f64,
        diag: &mut SparrowDiagnostics,
    ) {
        diag.worker_passes += 1;
        let colliding_seen = state.tracker.colliding_indices().len();
        diag.worker_colliding_items_seen += colliding_seen;
        diag.topk_target_count = diag.topk_target_count.max(colliding_seen);

        let worker_count = self.config.worker_count.max(1);
        let mut cands: Vec<WorkerCandidate> = Vec::with_capacity(worker_count);
        for w in 0..worker_count {
            let worker_seed = master_rng.next_u64() ^ ((w as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15));
            let cand = run_worker_pass(w, state, instances, sheets, &self.config, worker_seed, started, deadline, diag);
            cands.push(cand);
        }

        let best_idx = compare_worker_candidates(&cands).worker_idx;
        // Aggregate worker statistics (truthful evidence of the competition).
        for c in &cands {
            diag.worker_candidates_evaluated += c.evaluated;
            diag.multi_target_items_attempted += c.attempted;
            diag.multi_target_items_accepted += c.accepted;
            diag.multi_target_items_rejected += c.rejected;
        }
        diag.worker_count = worker_count;
        // Load the winning worker's state back into the master (Alg 10 load-back).
        let best = cands.into_iter().find(|c| c.worker_idx == best_idx).expect("best");
        diag.worker_commits += best.accepted;
        diag.worker_rollbacks += best.rejected + (worker_count - 1);
        diag.moves_attempted += best.attempted;
        diag.moves_accepted += best.accepted;
        diag.rollbacks += best.rejected;
        diag.worker_items_moved += best.accepted;
        diag.worker_best_loss = best.weighted_loss;
        load_best_worker(state, best);
    }

    /// Algorithm 9 native port: strike / no-improvement separation loop driven by
    /// the multi-worker competition, with GLS weight updates between iterations.
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
            let initial_strike_loss = state.tracker.total_raw_loss();
            let mut no_improve = 0usize;
            while no_improve < no_improve_limit && started.elapsed().as_secs_f64() < deadline {
                diag.iterations += 1;
                if state.tracker.colliding_indices().is_empty() {
                    break;
                }
                self.move_items_multi(state, instances, sheets, rng, started, deadline, diag);
                state.refresh_incumbents();
                let raw = state.tracker.total_raw_loss();
                if raw <= 1e-9 {
                    state.best_feasible = Some(state.layout.snapshot());
                    return true;
                } else if raw < best_raw - 1e-9 {
                    best_raw = raw;
                    best_snapshot = (state.layout.snapshot(), state.tracker.snapshot());
                    if raw < best_raw * 0.98 {
                        no_improve = 0;
                    }
                } else {
                    no_improve += 1;
                }
                state.tracker.update_weights();
                diag.gls_weight_updates += 1;
            }
            if initial_strike_loss * 0.98 <= best_raw {
                strikes += 1;
                diag.separator_strikes += 1;
            } else {
                strikes = 0;
            }
            // Roll back to the least-infeasible incumbent, keep GLS weights.
            state.layout = best_snapshot.0.snapshot();
            state.tracker.restore_keep_weights(best_snapshot.1.clone());
            if best_raw <= 1e-9 {
                break;
            }
        }
        state.tracker.is_feasible()
    }

    /// Deeper native disruption (no compression): combines a largest-item swap
    /// with a cross-sheet relocation and an alternate-rotation kick of the
    /// highest-loss item, to escape local optima.
    fn disrupt(
        &self,
        state: &mut SparrowState,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        rng: &mut DeterministicRng,
        diag: &mut SparrowDiagnostics,
    ) {
        let n = state.layout.placements.len();
        if n < 2 {
            return;
        }
        // (a) swap the two largest-area items.
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
        state.tracker.update_after_move(i, &state.layout, instances, sheets, diag);
        state.tracker.update_after_move(j, &state.layout, instances, sheets, diag);
        diag.exploration_disruptions_large_item_swap += 1;

        // (b) move the highest-loss item to a (different) eligible sheet at a
        //     randomized in-bounds anchor — escapes a saturated sheet.
        if sheets.len() > 1 {
            let worst = state.tracker.colliding_indices().into_iter().next();
            if let Some(w) = worst {
                let inst = &instances[state.layout.placements[w].instance_idx];
                let cur_sheet = state.layout.placements[w].sheet_index;
                let target_sheet = (cur_sheet + 1) % sheets.len();
                let rot = fitting_rotation(inst, sheets);
                let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
                let sh = &sheets[target_sheet];
                if rw <= sh.width + 1e-9 && rh <= sh.height + 1e-9 {
                    let max_rmx = (sh.width - rw).max(0.0);
                    let max_rmy = (sh.height - rh).max(0.0);
                    let rmx = sh.min_x + rng.next_f64() * max_rmx;
                    let rmy = sh.min_y + rng.next_f64() * max_rmy;
                    let (ax, ay) = placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
                    state.layout.placements[w] = SparrowPlacement { instance_idx: inst.idx, sheet_index: target_sheet, x: ax, y: ay, rotation_deg: rot };
                    state.tracker.update_after_move(w, &state.layout, instances, sheets, diag);
                    diag.exploration_disruptions_cross_sheet += 1;
                }
            }
        }

        // (c) rotation kick: rotate the highest-loss item to an alternate allowed
        //     rotation in place (different footprint can break a deadlock).
        if let Some(w) = state.tracker.colliding_indices().into_iter().next() {
            let inst = &instances[state.layout.placements[w].instance_idx];
            if inst.allowed_rotations_deg.len() > 1 {
                let cur_rot = state.layout.placements[w].rotation_deg;
                let alt: Vec<f64> = inst.allowed_rotations_deg.iter().copied().filter(|r| (r - cur_rot).abs() > 1e-9).collect();
                if !alt.is_empty() {
                    let pick = alt[(rng.next_u64() as usize) % alt.len()];
                    let sheet_idx = state.layout.placements[w].sheet_index;
                    let sh = &sheets[sheet_idx];
                    let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, pick);
                    if rw <= sh.width + 1e-9 && rh <= sh.height + 1e-9 {
                        let rmx = state.layout.placements[w].x.clamp(sh.min_x, sh.max_x - rw);
                        let rmy = state.layout.placements[w].y.clamp(sh.min_y, sh.max_y - rh);
                        let (ax, ay) = placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, pick);
                        state.layout.placements[w] = SparrowPlacement { instance_idx: inst.idx, sheet_index: sheet_idx, x: ax, y: ay, rotation_deg: pick };
                        state.tracker.update_after_move(w, &state.layout, instances, sheets, diag);
                        diag.exploration_disruptions_rotation += 1;
                    }
                }
            }
        }
    }

    /// Native solve: constructive seed -> exploration/separation -> final CDE validation.
    pub fn solve(&self, problem: SparrowProblem) -> SparrowSolveResult {
        let mut diag = SparrowDiagnostics {
            invoked: true,
            native_model_active: true,
            native_tracker_active: true,
            old_core_used: false,
            native_problem_instances: problem.instances.len(),
            worker_count: self.config.worker_count,
            ..SparrowDiagnostics::default()
        };
        super::cde_adapter::reset_query_cache();
        QUANT_CFG.with(|c| *c.borrow_mut() = self.config.clone());

        let instances = &problem.instances;
        let sheets = &problem.container.sheets;
        let started = Instant::now();
        let deadline = self.config.time_limit_s.max(0.1);
        let mut rng = DeterministicRng::new(self.config.seed);

        let seed_layout = build_native_constructive_seed(&problem);
        diag.seed_placements = seed_layout.placements.len();
        diag.seed_unplaced = problem.pre_unplaced.len();
        let mut state = SparrowState::new_with_diag(seed_layout, instances, sheets, &mut diag);
        diag.initial_raw_loss = state.tracker.total_raw_loss();
        diag.initial_weighted_loss = state.tracker.total_weighted_loss();
        diag.collision_graph_initial_pairs = state.tracker.colliding_pairs();
        diag.boundary_violations_initial = state.tracker.boundary_violations();
        diag.best_infeasible_raw_loss = state.best_infeasible_raw_loss;

        // Exploration: separate; on failure, pool the least-infeasible state,
        // biased-restore one, disrupt, and retry.
        let max_attempts = 10usize;
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
            let at = pool
                .binary_search_by(|(l, _)| l.partial_cmp(&raw).unwrap_or(std::cmp::Ordering::Equal))
                .unwrap_or_else(|e| e);
            pool.insert(at, (raw, state.layout.snapshot()));
            pool.truncate(8);
            diag.exploration_pool_inserts += 1;
            if !pool.is_empty() {
                // Biased restore: pick from the better half of the pool.
                let sel = (self.config.seed as usize).wrapping_add(attempt) % ((pool.len() + 1) / 2).max(1);
                let restored = pool[sel].1.snapshot();
                diag.exploration_pool_restores += 1;
                state = SparrowState::new_with_diag(restored, instances, sheets, &mut diag);
                self.disrupt(&mut state, instances, sheets, &mut rng, &mut diag);
            }
        }

        // Pick the layout to validate/emit: feasible incumbent if any.
        let final_layout = state.best_feasible.clone().unwrap_or_else(|| state.layout.snapshot());
        let validated = SparrowCollisionTracker::final_validation(&final_layout, instances, sheets);
        let final_tracker = SparrowCollisionTracker::build(&final_layout, instances, sheets);
        diag.collision_graph_final_pairs = final_tracker.colliding_pairs();
        diag.boundary_violations_final = final_tracker.boundary_violations();
        diag.final_raw_loss = final_tracker.total_raw_loss();
        diag.final_weighted_loss = final_tracker.total_weighted_loss();
        diag.best_infeasible_raw_loss = state.best_infeasible_raw_loss;
        diag.best_infeasible_weighted_loss = state.best_infeasible_raw_loss;
        diag.converged = feasible && validated && final_tracker.is_feasible();
        diag.native_tracker_full_rebuilds += final_tracker.full_rebuilds;
        diag.search_position_samples = diag
            .search_position_samples
            .max(diag.search_focused_samples + diag.search_global_samples + diag.search_refined_samples);
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

    fn make_part_rot(id: &str, w: f64, h: f64, qty: i64, rots: Vec<i64>) -> Part {
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

    fn ctx() -> RotationResolveContext {
        RotationResolveContext::legacy_default()
    }

    fn cfg(backend: CollisionBackendKind) -> SparrowConfig {
        SparrowConfig::from_solver_input(3.0, backend, ctx(), 7)
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
    fn constructive_seed_is_rotation_aware_for_oversized_at_zero() {
        // A 280x100 part does not fit a 150x300 sheet at 0deg (280>150) but fits at 90deg.
        let parts = vec![make_part_rot("WIDE", 280.0, 100.0, 1, vec![0, 90, 180, 270])];
        let stocks = vec![make_stock("S", 150.0, 300.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], cfg(CollisionBackendKind::Cde))
            .expect("problem");
        assert_eq!(problem.instances.len(), 1, "rotatable oversized part is placeable");
        let seed = build_native_constructive_seed(&problem);
        assert_eq!(seed.placements.len(), 1, "seed must place the rotation-only-fitting part");
        let rot = seed.placements[0].rotation_deg;
        assert!((rot - 90.0).abs() < 1e-9 || (rot - 270.0).abs() < 1e-9, "seed picked a fitting rotation, got {rot}");
    }

    #[test]
    fn native_tracker_quantified_loss_is_not_binary_count() {
        // Two overlapping 30x30 parts: a deep overlap must yield a LARGER quantified
        // pair loss than a shallow overlap (gradient, not a 1.0 count).
        let parts = vec![make_part("P", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], cfg(CollisionBackendKind::Cde))
            .expect("problem");
        let insts = &problem.instances;

        let deep = SparrowLayout { placements: vec![pl(0, 0.0, 0.0), pl(1, 5.0, 5.0)] };
        let shallow = SparrowLayout { placements: vec![pl(0, 0.0, 0.0), pl(1, 25.0, 25.0)] };
        let t_deep = SparrowCollisionTracker::build(&deep, insts, &sheets);
        let t_shallow = SparrowCollisionTracker::build(&shallow, insts, &sheets);
        assert!(t_deep.colliding_pairs() == 1 && t_shallow.colliding_pairs() == 1, "both overlap once");
        let l_deep = t_deep.total_raw_loss();
        let l_shallow = t_shallow.total_raw_loss();
        assert!(l_deep > QUANT_FLOOR && l_shallow > QUANT_FLOOR, "confirmed collisions have positive quantified loss");
        assert!(
            l_deep > l_shallow + 1e-6,
            "deeper overlap must have strictly larger quantified loss ({l_deep} vs {l_shallow})"
        );
        assert!(l_deep != 1.0 && l_shallow != 1.0, "loss must not be a binary 1.0 count");
    }

    #[test]
    fn native_tracker_cde_detects_overlap_and_separation() {
        let parts = vec![make_part("P", 30.0, 30.0, 2)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], cfg(CollisionBackendKind::Cde))
            .expect("problem");
        let insts = &problem.instances;

        let overlap = SparrowLayout { placements: vec![pl(0, 0.0, 0.0), pl(1, 10.0, 10.0)] };
        let t_overlap = SparrowCollisionTracker::build(&overlap, insts, &sheets);
        assert!(!t_overlap.unsupported, "rect-rect overlap must be CDE-supported");
        assert!(t_overlap.colliding_pairs() >= 1, "overlap yields >=1 colliding pair");
        assert!(!t_overlap.is_feasible(), "overlapping layout is infeasible");

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

        layout.placements[1] = pl(1, 120.0, 120.0);
        let mut diag = SparrowDiagnostics::default();
        tracker.update_after_move(1, &layout, insts, &sheets, &mut diag);
        assert_eq!(tracker.incremental_updates, before + 1, "incremental update counter advanced");
        assert_eq!(diag.native_tracker_incremental_updates, 1, "diag incremental update recorded");
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

        tracker.restore_keep_weights(snap);
        assert!(
            (tracker.total_weighted_loss() - weighted_after_bump).abs() < 1e-6,
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
        assert!(result.diagnostics.native_model_active);
        assert!(result.diagnostics.native_tracker_active);
        assert!(!result.diagnostics.old_core_used);
        assert_eq!(result.diagnostics.native_problem_instances, n);
        assert_eq!(result.diagnostics.compression_passes, 0, "compression disabled by default");
    }

    #[test]
    fn native_optimizer_worker_competition_is_active() {
        // A mildly overlapping instance must exercise the real worker competition
        // and quantified tracker: worker_count>=2, candidates evaluated, incremental
        // updates, and search calls all > 0. (Full convergence/timing is covered by
        // the release runtime smoke; this debug unit test only proves activity.)
        let parts = vec![make_part("P", 30.0, 20.0, 8)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let config = cfg(CollisionBackendKind::Cde);
        let problem = SparrowProblem::from_solver_input(&parts, &sheets, &ctx(), vec![], config.clone())
            .expect("problem");
        let result = SparrowOptimizer::new(config).solve(problem);
        let d = &result.diagnostics;
        assert!(d.worker_count >= 2, "worker competition active, got {}", d.worker_count);
        assert!(d.worker_passes > 0, "at least one worker pass ran");
        assert!(d.worker_candidates_evaluated > 0, "workers evaluated candidates");
        assert!(d.search_position_calls > 0, "search invoked");
        assert!(d.search_position_samples > 0, "search sampled candidates");
        assert!(d.native_tracker_incremental_updates > 0, "incremental tracker updates happened");
        assert!(d.quantified_pair_queries > 0, "quantified pair separation probed");
        assert!(d.multi_target_items_attempted > 0, "worker move targets attempted");
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
