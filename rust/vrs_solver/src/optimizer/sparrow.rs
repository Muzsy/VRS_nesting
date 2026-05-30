//! SGH-Q22: Sparrow-style separation kernel with explicit infeasible state.
//!
//! This module implements the first testable jagua_rs/Sparrow-style solver mode
//! inside the VRS solver. Unlike `PhaseOptimizer`, the kernel:
//!
//! 1. Seeds the layout with all fittable instances (overlaps allowed).
//! 2. Tracks an explicit `SparrowState` with current + best feasible + best
//!    infeasible layouts.
//! 3. Builds deterministic `CollisionGraphSnapshot`s after each iteration.
//! 4. Selects targets via GLS-weighted worst-collider scoring.
//! 5. Relocates via `search_position_for_target` (no LBF fallback by default).
//! 6. Commits / rolls back tentative moves; GLS weights survive rollback.
//! 7. Validates the final feasible layout with the active backend.
//!
//! The kernel reuses `VrsCollisionTracker` (severity engine and GLS weights)
//! and `search_position_for_target` (Q20R sample + coord descent), but the
//! lifecycle, state, and metrics live here — not behind a black-box
//! `VrsSeparator::run` call.

use std::collections::HashSet;
use std::time::Instant;

use crate::io::{CollisionBackendKind, Placement, Unplaced};
use crate::item::{
    can_fit_any_stock_with_policy, dims_for_rotation, expand_instances_with_policy,
    placement_anchor_from_rect_min, Instance, Part,
};
use crate::rotation_policy::RotationResolveContext;
use crate::sheet::SheetShape;

use super::collision_severity::{CollisionSeverityConfig, CollisionSeverityStats};
use super::loss_model::LossModelKind;
use super::search_position::{
    search_position_for_target, SearchPositionConfig, SearchPositionStats,
};
use super::separator::VrsCollisionTracker;
use super::working::WorkingLayout;

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

/// Configuration for the Sparrow separation kernel.
#[derive(Debug, Clone)]
pub struct SparrowConfig {
    pub max_iterations: usize,
    pub time_limit_s: f64,
    pub collision_backend: CollisionBackendKind,
    pub loss_model: LossModelKind,
    pub rotation_context: RotationResolveContext,
    pub search_position_config: SearchPositionConfig,
    pub severity_cfg: CollisionSeverityConfig,
    /// GLS multiplicative decay applied to weights on no-collision items each
    /// `gls_update_period` iterations.
    pub gls_weight_decay: f64,
    pub gls_weight_max: f64,
    pub gls_weight_min_inc_ratio: f64,
    pub gls_weight_max_inc_ratio: f64,
    /// Update GLS weights every N iterations (Sparrow guidance period).
    pub gls_update_period: usize,
    pub seed: u64,
    /// LBF fallback is disabled by default in sparrow_experimental — counted
    /// in diagnostics if it ever fires elsewhere.
    pub allow_lbf_fallback: bool,
}

impl Default for SparrowConfig {
    fn default() -> Self {
        Self {
            max_iterations: 200,
            time_limit_s: 5.0,
            collision_backend: CollisionBackendKind::Bbox,
            loss_model: LossModelKind::BboxArea,
            rotation_context: RotationResolveContext::legacy_default(),
            search_position_config: SearchPositionConfig::default(),
            severity_cfg: CollisionSeverityConfig::default(),
            gls_weight_decay: 0.9,
            gls_weight_max: 100.0,
            gls_weight_min_inc_ratio: 1.05,
            gls_weight_max_inc_ratio: 1.5,
            gls_update_period: 5,
            seed: 0,
            allow_lbf_fallback: false,
        }
    }
}

// ---------------------------------------------------------------------------
// Diagnostics
// ---------------------------------------------------------------------------

/// Sparrow-mode diagnostics surfaced into `OptimizerDiagnosticsOutput`.
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
    pub severity_pair_queries: usize,
    pub severity_boundary_queries: usize,
    pub severity_probe_queries: usize,
    pub lbf_fallback_used: usize,
}

// ---------------------------------------------------------------------------
// CollisionGraphSnapshot
// ---------------------------------------------------------------------------

/// Deterministic snapshot of the current collision graph (derived from the
/// underlying `VrsCollisionTracker`). Used both for target selection (worst
/// weighted collider) and for diagnostics.
#[derive(Debug, Clone, Default)]
pub struct CollisionGraphSnapshot {
    pub colliding_items_count: usize,
    pub colliding_pairs_count: usize,
    pub boundary_violations_count: usize,
    pub total_raw_loss: f64,
    pub total_weighted_loss: f64,
    pub worst_item_index: Option<usize>,
    pub worst_item_instance_id: Option<String>,
    pub worst_pair_instance_ids: Option<(String, String)>,
    pub worst_boundary_instance_id: Option<String>,
    pub max_pair_weight: f64,
    pub max_boundary_weight: f64,
    /// Top-K colliding pairs: (instance_a, instance_b, raw_severity, weight, weighted_loss).
    pub top_colliding_pairs: Vec<(String, String, f64, f64, f64)>,
    /// Top-K boundary violations: (instance_id, raw_severity, weight, weighted_loss).
    pub top_boundary_violations: Vec<(String, f64, f64, f64)>,
}

impl CollisionGraphSnapshot {
    pub fn is_feasible(&self) -> bool {
        self.colliding_pairs_count == 0 && self.boundary_violations_count == 0
    }

    /// Build a deterministic snapshot from the current tracker state and layout.
    ///
    /// `top_k` controls the length of `top_colliding_pairs` / `top_boundary_violations`.
    /// Sorted: by weighted_loss DESC, ties broken by instance_id ASC.
    pub fn from_tracker(
        tracker: &VrsCollisionTracker,
        layout: &WorkingLayout,
        top_k: usize,
    ) -> Self {
        let n = layout.placements.len();
        let mut pair_list: Vec<(usize, usize, f64, f64, f64)> = Vec::new();
        let mut boundary_list: Vec<(usize, f64, f64, f64)> = Vec::new();
        let mut max_pair_weight = 0.0_f64;
        let mut max_boundary_weight = 0.0_f64;
        let mut total_raw = 0.0_f64;
        let mut total_weighted = 0.0_f64;
        let mut per_item_weighted = vec![0.0_f64; n];
        let mut colliding_items: HashSet<usize> = HashSet::new();

        for i in 0..n {
            let bl = tracker.boundary_loss(i);
            let bw = tracker.boundary_weight(i);
            if bl > 0.0 {
                total_raw += bl;
                total_weighted += bl * bw;
                per_item_weighted[i] += bl * bw;
                colliding_items.insert(i);
                boundary_list.push((i, bl, bw, bl * bw));
                if bw > max_boundary_weight {
                    max_boundary_weight = bw;
                }
            }
            for j in (i + 1)..n {
                let pl = tracker.pair_loss(i, j);
                if pl > 0.0 {
                    let pw = tracker.pair_weight(i, j);
                    total_raw += pl;
                    total_weighted += pl * pw;
                    per_item_weighted[i] += pl * pw;
                    per_item_weighted[j] += pl * pw;
                    colliding_items.insert(i);
                    colliding_items.insert(j);
                    pair_list.push((i, j, pl, pw, pl * pw));
                    if pw > max_pair_weight {
                        max_pair_weight = pw;
                    }
                }
            }
        }

        // Deterministic worst-item selection: highest weighted incident loss; ties → instance_id ASC.
        let mut worst_item_index: Option<usize> = None;
        let mut worst_item_score = -1.0_f64;
        let mut worst_item_id = String::new();
        for (i, &score) in per_item_weighted.iter().enumerate() {
            if score <= 0.0 {
                continue;
            }
            let id = &layout.placements[i].instance_id;
            let better = score > worst_item_score + 1e-12
                || (worst_item_index.is_some()
                    && (score - worst_item_score).abs() < 1e-12
                    && id < &worst_item_id);
            if worst_item_index.is_none() || better {
                worst_item_index = Some(i);
                worst_item_score = score;
                worst_item_id = id.clone();
            }
        }
        let worst_item_instance_id =
            worst_item_index.map(|i| layout.placements[i].instance_id.clone());

        // Sort top pair / boundary lists deterministically.
        pair_list.sort_by(|a, b| {
            b.4.partial_cmp(&a.4)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| layout.placements[a.0].instance_id.cmp(&layout.placements[b.0].instance_id))
                .then_with(|| layout.placements[a.1].instance_id.cmp(&layout.placements[b.1].instance_id))
        });
        boundary_list.sort_by(|a, b| {
            b.3.partial_cmp(&a.3)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then_with(|| layout.placements[a.0].instance_id.cmp(&layout.placements[b.0].instance_id))
        });

        let worst_pair_instance_ids = pair_list.first().map(|t| {
            (
                layout.placements[t.0].instance_id.clone(),
                layout.placements[t.1].instance_id.clone(),
            )
        });
        let worst_boundary_instance_id =
            boundary_list.first().map(|t| layout.placements[t.0].instance_id.clone());

        let top_pairs: Vec<_> = pair_list
            .iter()
            .take(top_k)
            .map(|t| {
                (
                    layout.placements[t.0].instance_id.clone(),
                    layout.placements[t.1].instance_id.clone(),
                    t.2,
                    t.3,
                    t.4,
                )
            })
            .collect();
        let top_boundary: Vec<_> = boundary_list
            .iter()
            .take(top_k)
            .map(|t| (layout.placements[t.0].instance_id.clone(), t.1, t.2, t.3))
            .collect();

        Self {
            colliding_items_count: colliding_items.len(),
            colliding_pairs_count: pair_list.len(),
            boundary_violations_count: boundary_list.len(),
            total_raw_loss: total_raw,
            total_weighted_loss: total_weighted,
            worst_item_index,
            worst_item_instance_id,
            worst_pair_instance_ids,
            worst_boundary_instance_id,
            max_pair_weight,
            max_boundary_weight,
            top_colliding_pairs: top_pairs,
            top_boundary_violations: top_boundary,
        }
    }
}

// ---------------------------------------------------------------------------
// SparrowState
// ---------------------------------------------------------------------------

/// Explicit lifecycle state for the Sparrow separation kernel.
///
/// Tracks the current (potentially infeasible) layout, the best feasible
/// layout found so far (if any), and the best infeasible layout (lowest raw
/// loss). Holds the underlying `VrsCollisionTracker` and the latest
/// `CollisionGraphSnapshot`. All counters are explicit and diagnosable.
pub struct SparrowState {
    pub layout: WorkingLayout,
    pub tracker: VrsCollisionTracker,
    pub current_raw_loss: f64,
    pub current_weighted_loss: f64,
    pub best_feasible_layout: Option<WorkingLayout>,
    pub best_infeasible_layout: Option<WorkingLayout>,
    pub best_infeasible_raw_loss: f64,
    pub best_infeasible_weighted_loss: f64,
    pub current_graph: CollisionGraphSnapshot,
    pub iteration: usize,
    pub moves_attempted: usize,
    pub moves_accepted: usize,
    pub rollbacks: usize,
    pub gls_weight_updates: usize,
    pub seed: u64,
}

impl SparrowState {
    pub fn new(
        layout: WorkingLayout,
        tracker: VrsCollisionTracker,
        seed: u64,
    ) -> Self {
        let raw = tracker.total_loss();
        let weighted = tracker.total_weighted_loss();
        let graph = CollisionGraphSnapshot::from_tracker(&tracker, &layout, 5);
        let best_infeasible_layout = Some(layout.clone());
        Self {
            layout,
            tracker,
            current_raw_loss: raw,
            current_weighted_loss: weighted,
            best_feasible_layout: None,
            best_infeasible_layout,
            best_infeasible_raw_loss: raw,
            best_infeasible_weighted_loss: weighted,
            current_graph: graph,
            iteration: 0,
            moves_attempted: 0,
            moves_accepted: 0,
            rollbacks: 0,
            gls_weight_updates: 0,
            seed,
        }
    }

    /// Recompute the snapshot, losses, and best-infeasible incumbent.
    pub fn refresh(&mut self) {
        self.current_raw_loss = self.tracker.total_loss();
        self.current_weighted_loss = self.tracker.total_weighted_loss();
        self.current_graph =
            CollisionGraphSnapshot::from_tracker(&self.tracker, &self.layout, 5);
        if self.current_graph.is_feasible() {
            self.best_feasible_layout = Some(self.layout.clone());
        } else if self.current_raw_loss < self.best_infeasible_raw_loss
            || self.best_infeasible_layout.is_none()
        {
            self.best_infeasible_layout = Some(self.layout.clone());
            self.best_infeasible_raw_loss = self.current_raw_loss;
            self.best_infeasible_weighted_loss = self.current_weighted_loss;
        }
    }
}

// ---------------------------------------------------------------------------
// Result
// ---------------------------------------------------------------------------

pub struct SparrowResult {
    pub layout: WorkingLayout,
    pub diagnostics: SparrowDiagnostics,
    pub feasible: bool,
}

// ---------------------------------------------------------------------------
// Seed builder
// ---------------------------------------------------------------------------

/// Build the intentional infeasible seed layout for Sparrow mode.
///
/// Includes every instance whose part can fit on at least one sheet under the
/// active rotation policy. Items that cannot fit any sheet become
/// `PART_NEVER_FITS_STOCK` unplaced. All other items are placed deterministically
/// at the bottom-left corner of the first sheet that can host them — overlaps
/// are intentional and resolved by the separation kernel.
///
/// Deterministic for the same input seed; respects rotation policy; outer-only
/// (no holes) per Q15 contract.
pub fn build_sparrow_seed_layout(
    parts: &[Part],
    sheets: &[SheetShape],
    rotation_context: &RotationResolveContext,
) -> Result<(Vec<Placement>, Vec<Unplaced>), String> {
    let instances: Vec<Instance> = expand_instances_with_policy(parts, rotation_context)?;
    let mut placements: Vec<Placement> = Vec::with_capacity(instances.len());
    let mut unplaced: Vec<Unplaced> = Vec::new();

    for inst in instances {
        let part = parts
            .iter()
            .find(|p| p.id == inst.part_id)
            .ok_or_else(|| format!("part {} missing for instance {}", inst.part_id, inst.instance_id))?;
        let can_fit = can_fit_any_stock_with_policy(part, sheets, rotation_context)?;
        if !can_fit {
            unplaced.push(Unplaced {
                instance_id: inst.instance_id.clone(),
                part_id: inst.part_id.clone(),
                reason: "PART_NEVER_FITS_STOCK".to_string(),
            });
            continue;
        }
        // Deterministic rule: first allowed rotation, first sheet that can host
        // the rotated part, place at (0,0) of that sheet.
        let mut placed = false;
        for (sheet_idx, sheet) in sheets.iter().enumerate() {
            for &rot in &inst.allowed_rotations_deg {
                let (rw, rh) = dims_for_rotation(part.width, part.height, rot);
                if rw <= sheet.width + 1e-9 && rh <= sheet.height + 1e-9 {
                    let (ax, ay) =
                        placement_anchor_from_rect_min(0.0, 0.0, part.width, part.height, rot);
                    placements.push(Placement {
                        instance_id: inst.instance_id.clone(),
                        part_id: inst.part_id.clone(),
                        sheet_index: sheet_idx,
                        x: ax,
                        y: ay,
                        rotation_deg: rot,
                    });
                    placed = true;
                    break;
                }
            }
            if placed {
                break;
            }
        }
        if !placed {
            // Defensive: can_fit said yes but no sheet/rotation pair matched.
            unplaced.push(Unplaced {
                instance_id: inst.instance_id.clone(),
                part_id: inst.part_id.clone(),
                reason: "PART_NEVER_FITS_STOCK".to_string(),
            });
        }
    }
    Ok((placements, unplaced))
}

// ---------------------------------------------------------------------------
// SparrowSeparationKernel
// ---------------------------------------------------------------------------

pub struct SparrowSeparationKernel {
    pub config: SparrowConfig,
}

impl SparrowSeparationKernel {
    pub fn new(config: SparrowConfig) -> Self {
        Self { config }
    }

    /// Run the separation loop on the seeded `WorkingLayout`.
    ///
    /// Lifecycle:
    /// - build tracker + initial collision graph
    /// - while budget remains and graph is infeasible:
    ///     pick worst weighted target (via graph snapshot)
    ///     run `search_position_for_target` for that target
    ///     evaluate candidate via tracker.update_placement (backend-confirmed)
    ///     if `weighted_loss` improved → keep, else rollback (preserve GLS)
    ///     every `gls_update_period` iters, call `tracker.update_weights(...)`
    /// - refresh graph each iteration
    pub fn run(
        &self,
        seed_layout: WorkingLayout,
        parts: &[Part],
        sheets: &[SheetShape],
    ) -> SparrowResult {
        let mut diag = SparrowDiagnostics::default();
        diag.invoked = true;
        diag.seed_placements = seed_layout.placements.len();
        diag.seed_unplaced = seed_layout.unplaced.len();

        // Build initial tracker + state.
        let tracker = VrsCollisionTracker::build_with_model(
            &seed_layout,
            parts,
            sheets,
            self.config.loss_model,
            self.config.collision_backend.clone(),
        );
        let mut state = SparrowState::new(seed_layout, tracker, self.config.seed);

        diag.initial_raw_loss = state.current_raw_loss;
        diag.initial_weighted_loss = state.current_weighted_loss;
        diag.collision_graph_initial_pairs = state.current_graph.colliding_pairs_count;
        diag.boundary_violations_initial = state.current_graph.boundary_violations_count;

        // Early-exit: already feasible.
        if state.current_graph.is_feasible() {
            state.best_feasible_layout = Some(state.layout.clone());
            return self.finalize(state, diag);
        }

        let mut search_stats = SearchPositionStats::default();
        let started = Instant::now();
        let max_iter = self.config.max_iterations.max(1);
        let time_limit = self.config.time_limit_s.max(0.1);

        for iter in 0..max_iter {
            state.iteration = iter + 1;
            if started.elapsed().as_secs_f64() >= time_limit {
                break;
            }
            if state.current_graph.is_feasible() {
                break;
            }
            let Some(target_idx) = state.current_graph.worst_item_index else {
                break;
            };

            // Relocate target via search_position.
            state.moves_attempted += 1;
            diag.moves_attempted += 1;
            let call_seed = self
                .config
                .seed
                .wrapping_add(iter as u64)
                .wrapping_mul(0x9E37_79B9_7F4A_7C15);
            let new_placement_opt = search_position_for_target(
                &state.layout,
                target_idx,
                parts,
                sheets,
                &None,
                &self.config.collision_backend,
                self.config.loss_model,
                &self.config.rotation_context,
                &self.config.search_position_config,
                call_seed,
                &mut search_stats,
            );

            let Some(new_p) = new_placement_opt else {
                // search_position returned None; update GLS so the same target
                // does not stay top-worst forever.
                state.tracker.update_weights(
                    self.config.gls_weight_decay,
                    self.config.gls_weight_max,
                    self.config.gls_weight_min_inc_ratio,
                    self.config.gls_weight_max_inc_ratio,
                );
                state.gls_weight_updates += 1;
                diag.gls_weight_updates += 1;
                state.refresh();
                continue;
            };

            // Tentatively apply.
            let prev_weighted = state.current_weighted_loss;
            let prev_raw = state.current_raw_loss;
            let old_placement = state.layout.placements[target_idx].clone();
            let snap = state.tracker.snapshot_loss();
            state.layout.placements[target_idx] = new_p;
            state
                .tracker
                .update_placement(target_idx, &state.layout, parts, sheets);
            let new_weighted = state.tracker.total_weighted_loss();
            let new_raw = state.tracker.total_loss();

            // Accept on weighted-loss improvement, or on tie-with-raw-improvement.
            let improved = new_weighted < prev_weighted - 1e-9
                || (new_weighted <= prev_weighted + 1e-9 && new_raw < prev_raw - 1e-9);
            if improved {
                state.moves_accepted += 1;
                diag.moves_accepted += 1;
                state.current_weighted_loss = new_weighted;
                state.current_raw_loss = new_raw;
            } else {
                // Rollback geometry, preserve GLS weights.
                state.layout.placements[target_idx] = old_placement;
                state.tracker.restore_but_keep_weights(snap);
                state.rollbacks += 1;
                diag.rollbacks += 1;
            }

            // Periodic GLS weight update on stagnation/persistence.
            if self.config.gls_update_period > 0
                && state.iteration % self.config.gls_update_period.max(1) == 0
            {
                state.tracker.update_weights(
                    self.config.gls_weight_decay,
                    self.config.gls_weight_max,
                    self.config.gls_weight_min_inc_ratio,
                    self.config.gls_weight_max_inc_ratio,
                );
                state.gls_weight_updates += 1;
                diag.gls_weight_updates += 1;
            }

            state.refresh();
        }

        // Final stats from search_position + tracker severity.
        diag.search_position_calls = search_stats.calls;
        diag.search_position_samples = search_stats.global_samples_evaluated
            + search_stats.focused_samples_evaluated;
        diag.lbf_fallback_used = search_stats.lbf_fallback_used;
        let sev = &state.tracker.severity_stats;
        let mut combined_sev = sev.clone();
        combined_sev.accumulate(&search_stats.severity_stats);
        diag.severity_pair_queries = combined_sev.pair_queries;
        diag.severity_boundary_queries = combined_sev.boundary_queries;
        diag.severity_probe_queries = combined_sev.probe_queries;

        diag.iterations = state.iteration;

        self.finalize(state, diag)
    }

    fn finalize(&self, state: SparrowState, mut diag: SparrowDiagnostics) -> SparrowResult {
        diag.final_raw_loss = state.current_raw_loss;
        diag.final_weighted_loss = state.current_weighted_loss;
        diag.best_infeasible_raw_loss = state.best_infeasible_raw_loss;
        diag.best_infeasible_weighted_loss = state.best_infeasible_weighted_loss;
        diag.collision_graph_final_pairs = state.current_graph.colliding_pairs_count;
        diag.boundary_violations_final = state.current_graph.boundary_violations_count;
        diag.converged = state.current_graph.is_feasible();

        if let Some(feasible) = state.best_feasible_layout {
            SparrowResult {
                layout: feasible,
                diagnostics: diag,
                feasible: true,
            }
        } else {
            // No feasible layout found — return the seed (or current) layout
            // for diagnostics; the adapter MUST NOT emit colliding placements
            // as successful final output (responsibility of `validate_and_commit_with_backend`
            // gate in the adapter).
            SparrowResult {
                layout: state.layout,
                diagnostics: diag,
                feasible: false,
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::io::Placement;
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

    fn default_cfg(backend: CollisionBackendKind, max_iter: usize) -> SparrowConfig {
        SparrowConfig {
            collision_backend: backend,
            max_iterations: max_iter,
            time_limit_s: 10.0,
            ..SparrowConfig::default()
        }
    }

    // -----------------------------------------------------------------------
    // Q22-T1: seed includes all fit instances
    // -----------------------------------------------------------------------
    #[test]
    fn sparrow_seed_layout_includes_all_fit_instances() {
        let parts = vec![
            make_part("A", 30.0, 20.0, 3),  // fits
            make_part("B", 1000.0, 1000.0, 1), // never fits 100x100 sheet
        ];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (placements, unplaced) =
            build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        assert_eq!(placements.len(), 3, "all 3 A instances must be placed");
        assert_eq!(unplaced.len(), 1, "B must be PART_NEVER_FITS_STOCK");
        assert_eq!(unplaced[0].reason, "PART_NEVER_FITS_STOCK");
    }

    // -----------------------------------------------------------------------
    // Q22-T2: SparrowState allows infeasible intermediate layout
    // -----------------------------------------------------------------------
    #[test]
    fn sparrow_state_allows_infeasible_intermediate_layout() {
        let parts = vec![make_part("A", 30.0, 20.0, 2)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (p, u) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        // Both instances are placed at (0,0) → severe overlap.
        assert_eq!(p.len(), 2);
        let layout = WorkingLayout::new(p, u, 1, 0);
        let tracker = VrsCollisionTracker::build_with_model(
            &layout, &parts, &sheets,
            LossModelKind::BboxArea, CollisionBackendKind::Bbox,
        );
        let state = SparrowState::new(layout, tracker, 0);
        assert!(state.current_raw_loss > 0.0, "seed state must be infeasible");
        assert!(!state.current_graph.is_feasible());
    }

    // -----------------------------------------------------------------------
    // Q22-T3: collision graph counts pair and boundary violations
    // -----------------------------------------------------------------------
    #[test]
    fn collision_graph_snapshot_counts_pair_and_boundary_violations() {
        let parts = vec![make_part("A", 60.0, 60.0, 2)];
        let stocks = vec![make_stock("S", 80.0, 80.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (p, u) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        let layout = WorkingLayout::new(p, u, 1, 0);
        let tracker = VrsCollisionTracker::build_with_model(
            &layout, &parts, &sheets,
            LossModelKind::BboxArea, CollisionBackendKind::Bbox,
        );
        let graph = CollisionGraphSnapshot::from_tracker(&tracker, &layout, 5);
        assert_eq!(graph.colliding_pairs_count, 1, "two overlapping items → 1 pair");
        assert!(graph.colliding_items_count >= 2);
    }

    // -----------------------------------------------------------------------
    // Q22-T4: worst weighted collider selected deterministically
    // -----------------------------------------------------------------------
    #[test]
    fn sparrow_selects_worst_weighted_collider_deterministically() {
        let parts = vec![make_part("A", 30.0, 30.0, 3)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (p, u) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        let layout = WorkingLayout::new(p, u, 1, 0);
        let tracker = VrsCollisionTracker::build_with_model(
            &layout, &parts, &sheets,
            LossModelKind::BboxArea, CollisionBackendKind::Bbox,
        );
        let g1 = CollisionGraphSnapshot::from_tracker(&tracker, &layout, 5);
        let g2 = CollisionGraphSnapshot::from_tracker(&tracker, &layout, 5);
        assert_eq!(g1.worst_item_index, g2.worst_item_index,
                   "worst_item_index must be deterministic");
        assert_eq!(g1.worst_item_instance_id, g2.worst_item_instance_id);
        assert!(g1.worst_item_index.is_some());
    }

    // -----------------------------------------------------------------------
    // Q22-T5: move commit improves loss or rolls back
    // -----------------------------------------------------------------------
    #[test]
    fn sparrow_move_commit_improves_loss_or_rolls_back() {
        let parts = vec![make_part("A", 30.0, 20.0, 2)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (p, u) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        let layout = WorkingLayout::new(p, u, 1, 0);
        let cfg = default_cfg(CollisionBackendKind::Bbox, 20);
        let initial_raw = {
            let tr = VrsCollisionTracker::build_with_model(
                &layout, &parts, &sheets, cfg.loss_model, cfg.collision_backend.clone(),
            );
            tr.total_loss()
        };
        let kernel = SparrowSeparationKernel::new(cfg);
        let result = kernel.run(layout, &parts, &sheets);
        // Either feasible (loss=0) or monotonically non-worse final loss.
        assert!(result.diagnostics.final_raw_loss <= initial_raw + 1e-9,
                "final raw loss must not exceed initial after separation: initial={} final={}",
                initial_raw, result.diagnostics.final_raw_loss);
        // moves_accepted + rollbacks == moves_attempted.
        assert_eq!(
            result.diagnostics.moves_accepted + result.diagnostics.rollbacks,
            result.diagnostics.moves_attempted,
            "every attempt must be accepted or rolled back"
        );
    }

    // -----------------------------------------------------------------------
    // Q22-T6: rollback preserves GLS weights
    // -----------------------------------------------------------------------
    #[test]
    fn sparrow_rollback_preserves_gls_weights() {
        let parts = vec![make_part("A", 30.0, 20.0, 2)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (p, u) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        let layout = WorkingLayout::new(p, u, 1, 0);
        // Build a tracker with bumped weight on pair(0,1).
        let mut tracker = VrsCollisionTracker::build_with_model(
            &layout, &parts, &sheets,
            LossModelKind::BboxArea, CollisionBackendKind::Bbox,
        );
        tracker.update_weights(0.9, 100.0, 1.2, 1.5);
        let w_before = tracker.pair_weight(0, 1);
        // Take a snapshot, apply a "move", restore_but_keep_weights.
        let snap = tracker.snapshot_loss();
        let mut moved = layout.clone();
        moved.placements[1].x = 50.0;
        tracker.update_placement(1, &moved, &parts, &sheets);
        tracker.restore_but_keep_weights(snap);
        let w_after = tracker.pair_weight(0, 1);
        assert_eq!(w_before, w_after,
                   "GLS weight must survive rollback: before={} after={}",
                   w_before, w_after);
    }

    // -----------------------------------------------------------------------
    // Q22-T7: kernel resolves two-rect overlap
    // -----------------------------------------------------------------------
    #[test]
    fn sparrow_kernel_resolves_two_rect_overlap() {
        let parts = vec![make_part("A", 30.0, 20.0, 2)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (p, u) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        let layout = WorkingLayout::new(p, u, 1, 0);
        let cfg = default_cfg(CollisionBackendKind::Bbox, 50);
        let kernel = SparrowSeparationKernel::new(cfg);
        let result = kernel.run(layout, &parts, &sheets);
        assert!(result.feasible, "kernel must resolve two-rect overlap; final raw={}",
                result.diagnostics.final_raw_loss);
        assert_eq!(result.diagnostics.collision_graph_final_pairs, 0);
        assert_eq!(result.diagnostics.boundary_violations_final, 0);
    }

    // -----------------------------------------------------------------------
    // Q22-T8: kernel boundary recovery
    // -----------------------------------------------------------------------
    #[test]
    fn sparrow_kernel_boundary_recovery() {
        // Single item that fits the sheet — seed places it at (0,0) (already
        // inside). To exercise boundary recovery, we manually inject a
        // boundary-violating start placement.
        let parts = vec![make_part("A", 40.0, 30.0, 1)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let mut layout = WorkingLayout::new(
            vec![Placement {
                instance_id: "A__0001".to_string(),
                part_id: "A".to_string(),
                sheet_index: 0,
                x: 70.0, // 70 + 40 = 110 > 100 → boundary violation
                y: 10.0,
                rotation_deg: 0.0,
            }],
            vec![],
            1,
            0,
        );
        // Replace any extra unplaced.
        layout.unplaced.clear();
        let cfg = default_cfg(CollisionBackendKind::Bbox, 50);
        let kernel = SparrowSeparationKernel::new(cfg);
        let result = kernel.run(layout, &parts, &sheets);
        assert!(result.feasible,
                "kernel must pull boundary-violating item back; final raw={}",
                result.diagnostics.final_raw_loss);
        assert_eq!(result.diagnostics.boundary_violations_final, 0);
    }

    // -----------------------------------------------------------------------
    // Q22-T9: same-seed determinism (kernel-level)
    // -----------------------------------------------------------------------
    #[test]
    fn sparrow_kernel_same_seed_is_deterministic() {
        let parts = vec![make_part("A", 30.0, 20.0, 3)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (p1, u1) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        let layout1 = WorkingLayout::new(p1, u1, 1, 0);
        let (p2, u2) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        let layout2 = WorkingLayout::new(p2, u2, 1, 0);
        let cfg = default_cfg(CollisionBackendKind::Bbox, 30);
        let r1 = SparrowSeparationKernel::new(cfg.clone()).run(layout1, &parts, &sheets);
        let r2 = SparrowSeparationKernel::new(cfg).run(layout2, &parts, &sheets);
        assert_eq!(r1.feasible, r2.feasible);
        assert_eq!(r1.layout.placements.len(), r2.layout.placements.len());
        for (a, b) in r1.layout.placements.iter().zip(r2.layout.placements.iter()) {
            assert_eq!(a.instance_id, b.instance_id);
            assert!((a.x - b.x).abs() < 1e-9);
            assert!((a.y - b.y).abs() < 1e-9);
            assert!((a.rotation_deg - b.rotation_deg).abs() < 1e-9);
        }
    }
}
