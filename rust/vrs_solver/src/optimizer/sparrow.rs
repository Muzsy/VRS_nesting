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

use std::cmp::Ordering;
use std::collections::{HashMap, HashSet};
use std::time::Instant;

use crate::io::{CollisionBackendKind, Placement, Unplaced};
use crate::item::{
    can_fit_any_stock_with_policy, dims_for_rotation, expand_instances_with_policy,
    placement_anchor_from_rect_min, Instance, Part,
};
use crate::rotation_policy::RotationResolveContext;
use crate::sheet::SheetShape;

use super::collision_severity::CollisionSeverityConfig;
use super::initializer::bbox_from_placement;
use super::loss_model::LossModelKind;
use super::search_position::{
    search_position_for_target, SearchPositionConfig, SearchPositionStats,
};
use super::separator::VrsCollisionTracker;
use super::working::WorkingLayout;

struct DeterministicRng {
    state: u64,
}

impl DeterministicRng {
    fn new(seed: u64) -> Self {
        let state = if seed == 0 { 0x9E37_79B9_7F4A_7C15 } else { seed };
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
    pub workers: usize,
    pub worker_passes: usize,
    pub worker_candidates_evaluated: usize,
    pub worker_commits: usize,
    pub worker_rollbacks: usize,
    pub worker_best_loss: f64,
    pub multi_target_items_attempted: usize,
    pub multi_target_items_accepted: usize,
    pub multi_target_items_rejected: usize,
    pub topk_target_count: usize,
    pub graph_full_rebuilds: usize,
    pub graph_incremental_updates: usize,
    pub graph_edges_recomputed: usize,
    pub graph_edges_pruned_by_broadphase: usize,
    pub graph_debug_rebuilds: usize,
    pub graph_debug_rebuild_mismatches: usize,
    pub exploration_restarts: usize,
    pub exploration_seed_strategies: usize,
    pub exploration_disruptions: usize,
    pub exploration_stagnation_events: usize,
    pub exploration_best_raw_loss: f64,
    pub exploration_best_weighted_loss: f64,
    pub exploration_best_feasible_found: bool,
    pub compression_passes: usize,
    pub compression_candidates_evaluated: usize,
    pub compression_accepts: usize,
    pub compression_rejects: usize,
    pub fixed_sheet_objective_before: f64,
    pub fixed_sheet_objective_after: f64,
    pub fixed_sheet_objective_delta: f64,
    // ── SGH-Q24R2 native Sparrow lifecycle diagnostics ──────────────────────
    /// Separator (Alg 9) strike/no-improvement loop accounting.
    pub separator_invocations: usize,
    pub separator_strikes: usize,
    pub separator_no_improvement_iters: usize,
    /// Worker `move_items` (Alg 5) over ALL currently colliding items.
    pub worker_colliding_items_seen: usize,
    pub worker_items_moved: usize,
    pub worker_items_skipped_clear: usize,
    pub worker_master_loads: usize,
    /// Exploration (Alg 12) pool + biased restore + large-item disruption.
    pub exploration_pool_inserts: usize,
    pub exploration_pool_size_max: usize,
    pub exploration_pool_restores: usize,
    pub exploration_disruptions_large_item_swap: usize,
    pub exploration_attempts: usize,
    pub exploration_failed_attempts: usize,
    /// Compression (Alg 13) restore→pressure→separate→accept lifecycle.
    pub compression_restore_attempts: usize,
    pub compression_pressure_proposals: usize,
    pub compression_separation_calls: usize,
    pub compression_step_decay_events: usize,
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

#[derive(Debug, Clone, Copy, Default)]
struct GraphEntry {
    raw_loss: f64,
    weight: f64,
}

impl GraphEntry {
    fn weighted_loss(&self) -> f64 {
        self.raw_loss * self.weight
    }
}

/// Maintained collision graph for the Sparrow hot loop.
///
/// The expensive backend work lives in `VrsCollisionTracker::update_placement`,
/// which recomputes only the moved item's backend decisions. This graph mirrors
/// the tracker's scalar losses and weights so target selection can be refreshed
/// from moved-item edges instead of rebuilding a tracker-derived snapshot after
/// every tentative move.
#[derive(Debug, Clone)]
struct SparrowCollisionGraph {
    pair_edges: Vec<Vec<GraphEntry>>,
    boundary_edges: Vec<GraphEntry>,
    snapshot: CollisionGraphSnapshot,
    full_rebuilds: usize,
    incremental_updates: usize,
    edges_recomputed: usize,
    edges_pruned_by_broadphase: usize,
    debug_rebuilds: usize,
    debug_rebuild_mismatches: usize,
}

impl SparrowCollisionGraph {
    fn build_from_tracker(
        tracker: &VrsCollisionTracker,
        layout: &WorkingLayout,
        top_k: usize,
    ) -> Self {
        let n = layout.placements.len();
        let mut pair_edges = vec![vec![GraphEntry::default(); n]; n];
        let mut boundary_edges = vec![GraphEntry::default(); n];
        for i in 0..n {
            boundary_edges[i] = GraphEntry {
                raw_loss: tracker.boundary_loss(i),
                weight: tracker.boundary_weight(i),
            };
            for j in (i + 1)..n {
                let entry = GraphEntry {
                    raw_loss: tracker.pair_loss(i, j),
                    weight: tracker.pair_weight(i, j),
                };
                pair_edges[i][j] = entry;
                pair_edges[j][i] = entry;
            }
        }
        let snapshot = Self::snapshot_from_edges(&pair_edges, &boundary_edges, layout, top_k);
        Self {
            pair_edges,
            boundary_edges,
            snapshot,
            full_rebuilds: 1,
            incremental_updates: 0,
            edges_recomputed: 0,
            edges_pruned_by_broadphase: 0,
            debug_rebuilds: 0,
            debug_rebuild_mismatches: 0,
        }
    }

    fn snapshot(&self) -> CollisionGraphSnapshot {
        self.snapshot.clone()
    }

    fn update_moved_item(
        &mut self,
        moved_idx: usize,
        tracker: &VrsCollisionTracker,
        layout: &WorkingLayout,
        top_k: usize,
    ) {
        let n = layout.placements.len();
        if moved_idx >= n {
            return;
        }
        self.boundary_edges[moved_idx] = GraphEntry {
            raw_loss: tracker.boundary_loss(moved_idx),
            weight: tracker.boundary_weight(moved_idx),
        };
        self.edges_recomputed += 1;
        for j in 0..n {
            if j == moved_idx {
                continue;
            }
            let entry = GraphEntry {
                raw_loss: tracker.pair_loss(moved_idx, j),
                weight: tracker.pair_weight(moved_idx, j),
            };
            if entry.raw_loss == 0.0 {
                self.edges_pruned_by_broadphase += 1;
            }
            self.pair_edges[moved_idx][j] = entry;
            self.pair_edges[j][moved_idx] = entry;
            self.edges_recomputed += 1;
        }
        self.incremental_updates += 1;
        self.snapshot = Self::snapshot_from_edges(&self.pair_edges, &self.boundary_edges, layout, top_k);
    }

    fn refresh_weights(
        &mut self,
        tracker: &VrsCollisionTracker,
        layout: &WorkingLayout,
        top_k: usize,
    ) {
        let n = layout.placements.len();
        for i in 0..n {
            self.boundary_edges[i].weight = tracker.boundary_weight(i);
            for j in (i + 1)..n {
                let weight = tracker.pair_weight(i, j);
                self.pair_edges[i][j].weight = weight;
                self.pair_edges[j][i].weight = weight;
            }
        }
        self.snapshot = Self::snapshot_from_edges(&self.pair_edges, &self.boundary_edges, layout, top_k);
    }

    fn debug_compare_full_rebuild(
        &mut self,
        tracker: &VrsCollisionTracker,
        layout: &WorkingLayout,
        top_k: usize,
    ) {
        self.debug_rebuilds += 1;
        let full = CollisionGraphSnapshot::from_tracker(tracker, layout, top_k);
        let s = &self.snapshot;
        let mismatch = s.colliding_pairs_count != full.colliding_pairs_count
            || s.boundary_violations_count != full.boundary_violations_count
            || (s.total_raw_loss - full.total_raw_loss).abs() > 1e-9
            || (s.total_weighted_loss - full.total_weighted_loss).abs() > 1e-9
            || s.worst_item_index != full.worst_item_index;
        if mismatch {
            self.debug_rebuild_mismatches += 1;
        }
    }

    fn snapshot_from_edges(
        pair_edges: &[Vec<GraphEntry>],
        boundary_edges: &[GraphEntry],
        layout: &WorkingLayout,
        top_k: usize,
    ) -> CollisionGraphSnapshot {
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
            let be = boundary_edges[i];
            if be.raw_loss > 0.0 {
                total_raw += be.raw_loss;
                total_weighted += be.weighted_loss();
                per_item_weighted[i] += be.weighted_loss();
                colliding_items.insert(i);
                boundary_list.push((i, be.raw_loss, be.weight, be.weighted_loss()));
                max_boundary_weight = max_boundary_weight.max(be.weight);
            }
            for j in (i + 1)..n {
                let pe = pair_edges[i][j];
                if pe.raw_loss > 0.0 {
                    total_raw += pe.raw_loss;
                    total_weighted += pe.weighted_loss();
                    per_item_weighted[i] += pe.weighted_loss();
                    per_item_weighted[j] += pe.weighted_loss();
                    colliding_items.insert(i);
                    colliding_items.insert(j);
                    pair_list.push((i, j, pe.raw_loss, pe.weight, pe.weighted_loss()));
                    max_pair_weight = max_pair_weight.max(pe.weight);
                }
            }
        }

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

        pair_list.sort_by(|a, b| {
            b.4.partial_cmp(&a.4)
                .unwrap_or(Ordering::Equal)
                .then_with(|| layout.placements[a.0].instance_id.cmp(&layout.placements[b.0].instance_id))
                .then_with(|| layout.placements[a.1].instance_id.cmp(&layout.placements[b.1].instance_id))
        });
        boundary_list.sort_by(|a, b| {
            b.3.partial_cmp(&a.3)
                .unwrap_or(Ordering::Equal)
                .then_with(|| layout.placements[a.0].instance_id.cmp(&layout.placements[b.0].instance_id))
        });

        CollisionGraphSnapshot {
            colliding_items_count: colliding_items.len(),
            colliding_pairs_count: pair_list.len(),
            boundary_violations_count: boundary_list.len(),
            total_raw_loss: total_raw,
            total_weighted_loss: total_weighted,
            worst_item_index,
            worst_item_instance_id: worst_item_index.map(|i| layout.placements[i].instance_id.clone()),
            worst_pair_instance_ids: pair_list.first().map(|t| {
                (
                    layout.placements[t.0].instance_id.clone(),
                    layout.placements[t.1].instance_id.clone(),
                )
            }),
            worst_boundary_instance_id: boundary_list.first().map(|t| layout.placements[t.0].instance_id.clone()),
            max_pair_weight,
            max_boundary_weight,
            top_colliding_pairs: pair_list
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
                .collect(),
            top_boundary_violations: boundary_list
                .iter()
                .take(top_k)
                .map(|t| (layout.placements[t.0].instance_id.clone(), t.1, t.2, t.3))
                .collect(),
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
    graph: SparrowCollisionGraph,
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
        let graph = SparrowCollisionGraph::build_from_tracker(&tracker, &layout, 5);
        let current_graph = graph.snapshot();
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
            current_graph,
            graph,
            iteration: 0,
            moves_attempted: 0,
            moves_accepted: 0,
            rollbacks: 0,
            gls_weight_updates: 0,
            seed,
        }
    }

    fn refresh_from_graph(&mut self) {
        self.current_graph = self.graph.snapshot();
        self.current_raw_loss = self.current_graph.total_raw_loss;
        self.current_weighted_loss = self.current_graph.total_weighted_loss;
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

    pub fn refresh_after_move(&mut self, moved_idx: usize) {
        self.graph.update_moved_item(moved_idx, &self.tracker, &self.layout, 5);
        self.refresh_from_graph();
    }

    pub fn refresh_after_weight_update(&mut self) {
        self.graph.refresh_weights(&self.tracker, &self.layout, 5);
        self.refresh_from_graph();
    }

    pub fn debug_verify_graph(&mut self) {
        self.graph.debug_compare_full_rebuild(&self.tracker, &self.layout, 5);
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

#[derive(Clone)]
struct SparrowWorkerCandidate {
    worker_id: usize,
    layout: WorkingLayout,
    tracker: VrsCollisionTracker,
    graph: SparrowCollisionGraph,
    raw_loss: f64,
    weighted_loss: f64,
    moves_attempted: usize,
    moves_accepted: usize,
    moves_rejected: usize,
    search_stats: SearchPositionStats,
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

fn fixed_sheet_objective(layout: &WorkingLayout, parts: &[Part]) -> f64 {
    let mut per_sheet: HashMap<usize, (f64, f64)> = HashMap::new();
    for p in &layout.placements {
        let Some(part) = parts.iter().find(|pt| pt.id == p.part_id) else {
            continue;
        };
        if let Some(bb) = bbox_from_placement(p, part.width, part.height) {
            let entry = per_sheet.entry(p.sheet_index).or_insert((0.0, 0.0));
            entry.0 = entry.0.max(bb.x2);
            entry.1 = entry.1.max(bb.y2);
        }
    }
    per_sheet.values().map(|(x, y)| x + y).sum()
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

    fn worker_count(&self) -> usize {
        // Multiple deterministic workers (Sparrow move_items_multi). Kept modest
        // so a single pass over all colliding items stays within the phase budget
        // under the per-candidate CDE search cost.
        2
    }

    fn compare_f64_asc(a: f64, b: f64) -> Ordering {
        a.partial_cmp(&b).unwrap_or(Ordering::Equal)
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
                if ord == Ordering::Equal { None } else { Some(ord) }
            })
            .unwrap_or_else(|| a.placements.len().cmp(&b.placements.len()))
    }

    fn compare_worker_candidates(a: &SparrowWorkerCandidate, b: &SparrowWorkerCandidate) -> Ordering {
        Self::compare_f64_asc(a.weighted_loss, b.weighted_loss)
            .then(Self::compare_f64_asc(a.raw_loss, b.raw_loss))
            .then(b.moves_accepted.cmp(&a.moves_accepted))
            .then(a.worker_id.cmp(&b.worker_id))
            .then(Self::compare_layout_order(&a.layout, &b.layout))
    }

    // -----------------------------------------------------------------------
    // SGH-Q24R2 native Sparrow lifecycle (Algorithms 5/9/10/12/13)
    // -----------------------------------------------------------------------

    /// Algorithm 5 — worker `move_items`: load the master snapshot, then give
    /// EVERY currently colliding item a move opportunity in a worker-specific
    /// deterministic order. A move is accepted only if the moved item's weighted
    /// loss does not increase (Sparrow worker acceptance); rejected moves roll the
    /// item back while preserving GLS weights.
    #[allow(clippy::too_many_arguments)]
    fn worker_move_items(
        &self,
        master: &SparrowState,
        iteration: usize,
        worker_id: usize,
        parts: &[Part],
        sheets: &[SheetShape],
        started: &Instant,
        time_limit: f64,
        diag: &mut SparrowDiagnostics,
    ) -> SparrowWorkerCandidate {
        // Worker loads master layout + tracker snapshot.
        let mut layout = master.layout.snapshot();
        let mut tracker = master.tracker.clone();
        let mut graph = master.graph.clone();
        diag.worker_master_loads += 1;

        // Collect ALL currently colliding items, ordered per worker.
        let colliding = tracker.colliding_indices();
        diag.worker_colliding_items_seen += colliding.len();
        let ordered = if worker_id == 0 {
            colliding.clone()
        } else {
            Self::deterministic_shuffle(&colliding, self.worker_seed(iteration, worker_id))
        };

        let mut moves_attempted = 0usize;
        let mut moves_accepted = 0usize;
        let mut moves_rejected = 0usize;
        let mut search_stats = SearchPositionStats::default();

        for target_idx in ordered {
            // Deadline guard: a single worker pass over all colliding items must
            // not overshoot the phase budget (CDE search is expensive per item).
            if started.elapsed().as_secs_f64() >= time_limit {
                break;
            }
            if target_idx >= layout.placements.len() {
                continue;
            }
            // Re-check: only move items that are STILL colliding (the set changes
            // as earlier items in this pass move).
            if tracker.weighted_loss_for_item(target_idx) <= 1e-12 {
                diag.worker_items_skipped_clear += 1;
                continue;
            }
            moves_attempted += 1;
            let call_seed = self.worker_seed(iteration, worker_id)
                ^ (target_idx as u64).wrapping_mul(0x517C_C1B7_2722_0A95);
            let Some(new_p) = search_position_for_target(
                &layout, target_idx, parts, sheets, &None,
                &self.config.collision_backend, self.config.loss_model,
                &self.config.rotation_context, &self.config.search_position_config,
                call_seed, &mut search_stats,
            ) else {
                moves_rejected += 1;
                continue;
            };

            let old_weighted = tracker.weighted_loss_for_item(target_idx);
            let old_placement = layout.placements[target_idx].clone();
            let loss_snap = tracker.snapshot_loss();
            layout.placements[target_idx] = new_p;
            tracker.update_placement(target_idx, &layout, parts, sheets);
            // Worker acceptance: the moved item's weighted loss must not increase.
            let new_weighted = tracker.weighted_loss_for_item(target_idx);
            if new_weighted <= old_weighted + 1e-9 {
                graph.update_moved_item(target_idx, &tracker, &layout, 5);
                moves_accepted += 1;
                diag.worker_items_moved += 1;
            } else {
                layout.placements[target_idx] = old_placement;
                tracker.restore_but_keep_weights(loss_snap);
                moves_rejected += 1;
            }
        }

        // Rebuild the worker's graph snapshot from its final tracker state.
        graph = SparrowCollisionGraph::build_from_tracker(&tracker, &layout, 5);
        let snap = graph.snapshot();
        SparrowWorkerCandidate {
            worker_id,
            layout,
            tracker,
            graph,
            raw_loss: snap.total_raw_loss,
            weighted_loss: snap.total_weighted_loss,
            moves_attempted,
            moves_accepted,
            moves_rejected,
            search_stats,
        }
    }

    /// Algorithm 10 — `move_items_multi`: run all workers from the shared master
    /// snapshot, then load the worker with the lowest weighted loss back into the
    /// master. Returns the accumulated search stats.
    #[allow(clippy::too_many_arguments)]
    fn move_items_multi(
        &self,
        state: &mut SparrowState,
        iteration: usize,
        parts: &[Part],
        sheets: &[SheetShape],
        started: &Instant,
        time_limit: f64,
        diag: &mut SparrowDiagnostics,
    ) -> SearchPositionStats {
        let worker_count = self.worker_count();
        let mut workers: Vec<SparrowWorkerCandidate> = Vec::with_capacity(worker_count);
        for worker_id in 0..worker_count {
            workers.push(self.worker_move_items(state, iteration, worker_id, parts, sheets, started, time_limit, diag));
        }
        let mut search_stats = SearchPositionStats::default();
        for w in &workers {
            diag.worker_candidates_evaluated += w.moves_attempted;
            diag.multi_target_items_attempted += w.moves_attempted;
            diag.multi_target_items_accepted += w.moves_accepted;
            diag.multi_target_items_rejected += w.moves_rejected;
            diag.moves_attempted += w.moves_attempted;
            diag.moves_accepted += w.moves_accepted;
            diag.rollbacks += w.moves_rejected;
            search_stats.accumulate(&w.search_stats);
        }
        diag.worker_passes += 1;
        workers.sort_by(Self::compare_worker_candidates);
        let best = workers.into_iter().next().unwrap();
        diag.worker_best_loss = best.weighted_loss;
        // Master loads the best worker (Sparrow keeps the lowest weighted loss).
        state.layout = best.layout;
        state.tracker = best.tracker;
        state.graph = best.graph;
        state.refresh_from_graph();
        search_stats
    }

    /// Algorithm 9 — `separate`: strike / no-improvement loop. Repeatedly runs
    /// `move_items_multi`; tracks the least-infeasible incumbent; updates GLS
    /// weights every iteration; rolls back to the incumbent at the end of each
    /// strike while preserving GLS weights. Returns true if feasibility reached.
    #[allow(clippy::too_many_arguments)]
    fn separate(
        &self,
        state: &mut SparrowState,
        parts: &[Part],
        sheets: &[SheetShape],
        started: &Instant,
        time_limit: f64,
        search_stats: &mut SearchPositionStats,
        diag: &mut SparrowDiagnostics,
    ) -> bool {
        diag.separator_invocations += 1;
        let strike_limit = 3usize;
        let iter_no_improvement_limit = 8usize;

        let mut min_loss_layout = state.layout.snapshot();
        let mut min_loss_snap = state.tracker.snapshot_loss();
        let mut min_loss = state.current_raw_loss;

        let mut n_strikes = 0usize;
        while n_strikes < strike_limit && started.elapsed().as_secs_f64() < time_limit {
            let initial_strike_loss = state.current_raw_loss;
            let mut n_no_improvement = 0usize;
            while n_no_improvement < iter_no_improvement_limit
                && started.elapsed().as_secs_f64() < time_limit
            {
                state.iteration += 1;
                diag.iterations += 1;
                let stats = self.move_items_multi(state, state.iteration, parts, sheets, started, time_limit, diag);
                search_stats.accumulate(&stats);
                let loss = state.current_raw_loss;
                if loss == 0.0 {
                    min_loss_layout = state.layout.snapshot();
                    min_loss_snap = state.tracker.snapshot_loss();
                    // Restore the feasible incumbent and return.
                    state.best_feasible_layout = Some(state.layout.clone());
                    return true;
                } else if loss < min_loss {
                    if loss < min_loss * 0.98 {
                        n_no_improvement = 0;
                    }
                    min_loss_layout = state.layout.snapshot();
                    min_loss_snap = state.tracker.snapshot_loss();
                    min_loss = loss;
                } else {
                    n_no_improvement += 1;
                    diag.separator_no_improvement_iters += 1;
                }
                // GLS weight update every iteration (Sparrow Algorithm 8).
                state.tracker.update_weights(
                    self.config.gls_weight_decay, self.config.gls_weight_max,
                    self.config.gls_weight_min_inc_ratio, self.config.gls_weight_max_inc_ratio,
                );
                state.gls_weight_updates += 1;
                diag.gls_weight_updates += 1;
                state.refresh_after_weight_update();
            }
            if initial_strike_loss * 0.98 <= min_loss {
                n_strikes += 1;
                diag.separator_strikes += 1;
            } else {
                n_strikes = 0;
            }
            // Rollback to least-infeasible incumbent, PRESERVING GLS weights.
            state.layout = min_loss_layout.snapshot();
            state.tracker.restore_but_keep_weights(min_loss_snap.clone());
            state.graph = SparrowCollisionGraph::build_from_tracker(&state.tracker, &state.layout, 5);
            state.refresh_from_graph();
        }
        state.current_graph.is_feasible()
    }

    /// Real large-item disruption (Algorithm 12 kick): swap the positions of the
    /// two largest-area placements on the same sheet (deterministic given the
    /// seed). This genuinely changes the layout to escape a local optimum.
    fn disrupt_large_items(
        &self,
        state: &mut SparrowState,
        parts: &[Part],
        sheets: &[SheetShape],
        seed: u64,
        diag: &mut SparrowDiagnostics,
    ) {
        let n = state.layout.placements.len();
        if n < 2 {
            return;
        }
        // Rank placements by part area (largest first), deterministic tie-break by index.
        let mut by_area: Vec<(usize, f64)> = (0..n)
            .filter_map(|i| {
                let p = &state.layout.placements[i];
                parts.iter().find(|pt| pt.id == p.part_id).map(|pt| (i, pt.width * pt.height))
            })
            .collect();
        by_area.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal).then(a.0.cmp(&b.0)));
        if by_area.len() < 2 {
            return;
        }
        // Pick the largest item and another large item (seed-selected among the top).
        let i = by_area[0].0;
        let top_k = by_area.len().min(6);
        let j_pick = 1 + (seed as usize % (top_k - 1));
        let j = by_area[j_pick].0;
        if i == j {
            return;
        }
        // Swap their (x, y, sheet) — keep each item's own rotation (feasible).
        let pi = state.layout.placements[i].clone();
        let pj = state.layout.placements[j].clone();
        state.layout.placements[i].x = pj.x;
        state.layout.placements[i].y = pj.y;
        state.layout.placements[i].sheet_index = pj.sheet_index;
        state.layout.placements[j].x = pi.x;
        state.layout.placements[j].y = pi.y;
        state.layout.placements[j].sheet_index = pi.sheet_index;
        state.tracker.update_placement(i, &state.layout, parts, sheets);
        state.tracker.update_placement(j, &state.layout, parts, sheets);
        state.graph = SparrowCollisionGraph::build_from_tracker(&state.tracker, &state.layout, 5);
        state.refresh_from_graph();
        diag.exploration_disruptions_large_item_swap += 1;
        diag.exploration_disruptions += 1;
    }

    /// Algorithm 12 — exploration phase: bounded infeasible pool + biased restore
    /// + large-item disruption + repeated separate attempts under budget.
    #[allow(clippy::too_many_arguments)]
    fn exploration_phase(
        &self,
        state: &mut SparrowState,
        parts: &[Part],
        sheets: &[SheetShape],
        started: &Instant,
        time_limit: f64,
        search_stats: &mut SearchPositionStats,
        diag: &mut SparrowDiagnostics,
    ) -> bool {
        const POOL_CAP: usize = 8;
        // (raw_loss, layout) sorted ascending by raw_loss.
        let mut pool: Vec<(f64, WorkingLayout)> = Vec::new();
        let max_attempts = 12usize;

        for attempt in 0..max_attempts {
            if started.elapsed().as_secs_f64() >= time_limit {
                break;
            }
            diag.exploration_attempts += 1;
            let feasible = self.separate(state, parts, sheets, started, time_limit, search_stats, diag);
            if feasible {
                diag.exploration_best_feasible_found = true;
                diag.exploration_best_raw_loss = 0.0;
                return true;
            }
            diag.exploration_failed_attempts += 1;
            // Insert the least-infeasible local solution into the pool.
            let loss = state.current_raw_loss;
            diag.exploration_best_raw_loss = diag.exploration_best_raw_loss.min(loss);
            let insert_at = pool
                .binary_search_by(|(l, _)| l.partial_cmp(&loss).unwrap_or(Ordering::Equal))
                .unwrap_or_else(|e| e);
            pool.insert(insert_at, (loss, state.layout.snapshot()));
            if pool.len() > POOL_CAP {
                pool.truncate(POOL_CAP);
            }
            diag.exploration_pool_inserts += 1;
            diag.exploration_pool_size_max = diag.exploration_pool_size_max.max(pool.len());

            if pool.is_empty() {
                break;
            }
            // Biased restore: favor low-loss entries (front of the pool).
            let bias_seed = self.config.seed ^ (attempt as u64).wrapping_mul(0x9E37_79B9_7F4A_7C15);
            let span = ((pool.len() + 1) / 2).max(1); // top half
            let sel = (bias_seed as usize) % span;
            let restored = pool[sel].1.snapshot();
            diag.exploration_pool_restores += 1;
            diag.exploration_restarts += 1;
            let tracker = VrsCollisionTracker::build_with_model(
                &restored, parts, sheets, self.config.loss_model, self.config.collision_backend.clone(),
            );
            let preserved_seed = state.seed;
            *state = SparrowState::new(restored, tracker, preserved_seed);
            // Disrupt before retrying separation.
            self.disrupt_large_items(state, parts, sheets, bias_seed, diag);
            diag.exploration_stagnation_events += 1;
        }
        state.current_graph.is_feasible()
    }

    /// Algorithm 13 — compression phase: restore the feasible incumbent, apply a
    /// compaction pressure proposal, run the separator to restore feasibility,
    /// accept if feasible AND the fixed-sheet objective improved, else rollback
    /// and decay the pressure step.
    #[allow(clippy::too_many_arguments)]
    fn compression_phase(
        &self,
        state: &mut SparrowState,
        parts: &[Part],
        sheets: &[SheetShape],
        started: &Instant,
        time_limit: f64,
        search_stats: &mut SearchPositionStats,
        diag: &mut SparrowDiagnostics,
    ) {
        let Some(incumbent) = state.best_feasible_layout.clone() else {
            return;
        };
        diag.compression_passes += 1;
        let before = fixed_sheet_objective(&incumbent, parts);
        diag.fixed_sheet_objective_before = before;
        let mut best = incumbent;
        let mut best_obj = before;
        let mut step = 0.10_f64; // fraction of the toward-origin distance
        let min_step = 0.01_f64;
        let max_passes = 4usize;

        for _pass in 0..max_passes {
            if step < min_step || started.elapsed().as_secs_f64() >= time_limit {
                break;
            }
            diag.compression_restore_attempts += 1;
            // Restore incumbent into a fresh state.
            let tracker = VrsCollisionTracker::build_with_model(
                &best, parts, sheets, self.config.loss_model, self.config.collision_backend.clone(),
            );
            let mut trial = SparrowState::new(best.snapshot(), tracker, state.seed);
            // Pressure proposal: compact every item toward its sheet origin by `step`.
            diag.compression_pressure_proposals += 1;
            for idx in 0..trial.layout.placements.len() {
                let p = &mut trial.layout.placements[idx];
                let sheet = &sheets[p.sheet_index.min(sheets.len() - 1)];
                p.x = sheet.min_x + (p.x - sheet.min_x) * (1.0 - step);
                p.y = sheet.min_y + (p.y - sheet.min_y) * (1.0 - step);
            }
            // Rebuild tracker after the bulk pressure move (temporary collisions allowed).
            trial.tracker = VrsCollisionTracker::build_with_model(
                &trial.layout, parts, sheets, self.config.loss_model, self.config.collision_backend.clone(),
            );
            trial.graph = SparrowCollisionGraph::build_from_tracker(&trial.tracker, &trial.layout, 5);
            trial.refresh_from_graph();
            // Run the separator to restore feasibility.
            diag.compression_separation_calls += 1;
            let feasible = self.separate(&mut trial, parts, sheets, started, time_limit, search_stats, diag);
            let obj = fixed_sheet_objective(&trial.layout, parts);
            if feasible && obj <= best_obj - 1e-9 {
                best = trial.layout.snapshot();
                best_obj = obj;
                diag.compression_accepts += 1;
            } else {
                diag.compression_rejects += 1;
                step *= 0.5;
                diag.compression_step_decay_events += 1;
            }
        }
        diag.fixed_sheet_objective_after = best_obj;
        diag.fixed_sheet_objective_delta = before - best_obj;
        // Commit the best feasible compressed incumbent.
        let tracker = VrsCollisionTracker::build_with_model(
            &best, parts, sheets, self.config.loss_model, self.config.collision_backend.clone(),
        );
        *state = SparrowState::new(best.snapshot(), tracker, state.seed);
        if state.current_graph.is_feasible() {
            state.best_feasible_layout = Some(best);
        }
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
        let time_limit = self.config.time_limit_s.max(0.1);
        // Reserve part of the budget for the compression phase (Algorithm 13).
        let exploration_deadline = time_limit * 0.8;
        diag.workers = self.worker_count();
        diag.worker_best_loss = state.current_weighted_loss;
        diag.exploration_seed_strategies = 1;
        diag.exploration_best_raw_loss = state.current_raw_loss;
        diag.exploration_best_weighted_loss = state.current_weighted_loss;

        // ── Algorithm 11 orchestration: exploration → compression → validate ──
        // Exploration phase (Alg 12): runs the separator (Alg 9 strike loop, which
        // drives Alg 10 move_items_multi → Alg 5 worker move_items over all
        // colliding items), then pool/biased-restore/disrupt under budget.
        let feasible = self.exploration_phase(
            &mut state, parts, sheets, &started, exploration_deadline,
            &mut search_stats, &mut diag,
        );

        // Compression phase (Alg 13): restore feasible incumbent → pressure →
        // separate → accept/reject, under the remaining budget.
        if feasible || state.best_feasible_layout.is_some() {
            diag.exploration_best_feasible_found = true;
            self.compression_phase(
                &mut state, parts, sheets, &started, time_limit,
                &mut search_stats, &mut diag,
            );
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

        // diag.iterations is accumulated inside `separate()` across all attempts.
        diag.graph_full_rebuilds += state.graph.full_rebuilds;
        diag.graph_incremental_updates += state.graph.incremental_updates;
        diag.graph_edges_recomputed += state.graph.edges_recomputed;
        diag.graph_edges_pruned_by_broadphase += state.graph.edges_pruned_by_broadphase;
        diag.graph_debug_rebuilds += state.graph.debug_rebuilds;
        diag.graph_debug_rebuild_mismatches += state.graph.debug_rebuild_mismatches;

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

    #[test]
    fn sparrow_q23r3_multi_target_and_incremental_graph_are_diagnosed() {
        let parts = vec![make_part("A", 30.0, 20.0, 4)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (p, u) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        let layout = WorkingLayout::new(p, u, 1, 0);
        let cfg = default_cfg(CollisionBackendKind::Bbox, 8);
        let result = SparrowSeparationKernel::new(cfg).run(layout, &parts, &sheets);
        let d = result.diagnostics;
        // SGH-Q24R2 native lifecycle: worker-master move_items_multi over ALL
        // currently colliding items (Alg 5/10), not top-K.
        assert!(d.workers > 1, "production pass must use multiple deterministic workers");
        assert!(d.worker_master_loads > 1, "each worker must load the master snapshot (move_items_multi)");
        assert!(d.worker_colliding_items_seen > 1,
            "worker move_items must see more than one currently-colliding item");
        assert!(d.multi_target_items_attempted > 1, "worker pass must attempt multiple items");
        assert!(d.separator_invocations >= 1, "separator (Alg 9) must be invoked");
        assert!(d.worker_passes >= 1, "move_items_multi pass must run");
    }

    #[test]
    fn sparrow_q24r2_exploration_and_compression_lifecycle_are_diagnosed() {
        // Medium fixture that converges: exercises separator + compression lifecycle.
        let parts = vec![make_part("A", 30.0, 20.0, 12)];
        let stocks = vec![make_stock("S", 200.0, 200.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (p, u) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        let layout = WorkingLayout::new(p, u, 1, 0);
        let cfg = default_cfg(CollisionBackendKind::Bbox, 64);
        let result = SparrowSeparationKernel::new(cfg).run(layout, &parts, &sheets);
        let d = result.diagnostics;
        assert!(result.feasible, "native lifecycle should produce a feasible fixed-sheet layout");
        assert!(d.exploration_attempts >= 1, "exploration phase must run at least one attempt");
        assert!(d.separator_invocations >= 1, "separator (Alg 9) must be invoked");
        assert!(d.compression_passes >= 1, "feasible incumbent must run compression (Alg 13)");
        assert!(d.compression_separation_calls >= 1,
            "compression must call the separator (restore→pressure→separate→accept)");
        assert!(d.fixed_sheet_objective_after <= d.fixed_sheet_objective_before + 1e-9,
            "compression must not worsen the fixed-sheet objective");
    }

    #[test]
    fn sparrow_q24r2_exploration_pool_and_disruption_fire_on_infeasible() {
        // Impossible fixture (5×50×50 on a single 100×100 sheet → only 4 fit):
        // separation never reaches feasibility, so the exploration pool must
        // insert, biased-restore, and disrupt (large-item swap).
        let parts = vec![make_part("A", 50.0, 50.0, 5)];
        let stocks = vec![make_stock("S", 100.0, 100.0, 1)];
        let sheets = expand_sheets(&stocks).expect("sheets");
        let ctx = RotationResolveContext::legacy_default();
        let (p, u) = build_sparrow_seed_layout(&parts, &sheets, &ctx).expect("seed");
        let layout = WorkingLayout::new(p, u, 1, 0);
        let cfg = SparrowConfig {
            time_limit_s: 5.0,
            ..default_cfg(CollisionBackendKind::Bbox, 32)
        };
        let result = SparrowSeparationKernel::new(cfg).run(layout, &parts, &sheets);
        let d = result.diagnostics;
        assert!(!result.feasible, "impossible fixture must not converge");
        assert!(d.separator_strikes >= 1, "separator strike loop must register strikes");
        assert!(d.exploration_pool_inserts >= 1, "exploration pool must receive inserts");
        assert!(d.exploration_pool_restores >= 1, "exploration must biased-restore from the pool");
        assert!(d.exploration_disruptions_large_item_swap >= 1,
            "exploration must perform a large-item disruption swap");
    }
}
