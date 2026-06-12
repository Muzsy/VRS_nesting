use super::*;

// ---------------------------------------------------------------------------
// tracker (native, CDE-backed, quantified loss)
// ---------------------------------------------------------------------------

/// Native CDE-backed collision tracker (upstream `CollisionTracker`). Owns the
/// quantified pair/boundary loss records + GLS weights. Collision EXISTENCE is
/// decided by the CDE adapter (`CdeCandidateSession` / jagua `CDEngine`); the
/// stored loss is the upstream overlap-proxy quantification (Algorithm 3/4:
/// `sqrt(overlap-proxy + epsilon²) × shape penalty` for pairs, outside-area for
/// the container), never a binary count.
pub struct SparrowCollisionTracker {
    pub(crate) n: usize,
    /// Prepared CDE shapes per instance index (rebuilt lazily after a move).
    pub(crate) shapes: Vec<Option<Rc<CdePreparedShape>>>,
    /// Prepared sheet shapes per sheet index.
    pub(crate) sheet_shapes: Vec<Option<Rc<CdePreparedShape>>>,
    /// Quantified raw pair loss (overlap-area proxy + shape penalty), keyed i<j.
    pub(crate) pair_loss: HashMap<(usize, usize), f64>,
    /// GLS pair weights, i<j.
    pub(crate) pair_weight: HashMap<(usize, usize), f64>,
    /// Quantified raw boundary/container loss per item (upstream outside-area proxy).
    pub(crate) boundary_loss: Vec<f64>,
    /// GLS boundary/container weights per item.
    pub(crate) boundary_weight: Vec<f64>,
    pub full_rebuilds: usize,
    pub incremental_updates: usize,
    pub unsupported: bool,
    /// SGH-Q36: true when part-part collision runs on spacing-expanded geometry.
    /// `shapes[i]` then holds the spacing-expanded shape (used for pairs + sessions);
    /// boundary is recomputed from the ORIGINAL base shape on the fly.
    pub(crate) spacing_applied: bool,
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
            spacing_applied: self.spacing_applied,
        }
    }
}

/// SGH-Q36: touching policy for the tracker/separator sessions — spacing-expanded
/// touching is allowed when spacing is active, otherwise strict (original semantics).
pub(crate) fn pair_touching_policy(
    spacing_applied: bool,
) -> crate::optimizer::cde_adapter::CdeTouchingPolicy {
    if spacing_applied {
        crate::optimizer::cde_adapter::CdeTouchingPolicy::SpacingExpandedTouchAllowed
    } else {
        crate::optimizer::cde_adapter::CdeTouchingPolicy::SparrowStrict
    }
}

impl SparrowCollisionTracker {
    fn prepare_item(
        layout: &SparrowLayout,
        instances: &[SPInstance],
        idx: usize,
    ) -> Option<Rc<CdePreparedShape>> {
        let p = &layout.placements[idx];
        let inst = &instances[p.instance_idx];
        // Q31: use cached base shape — no prepare_shape_native call.
        // SGH-Q36: use the spacing-expanded collision base shape for pairs/sessions.
        // When spacing is off this is the SAME Rc as the original base shape, so the
        // result is byte-identical to the pre-Q36 path.
        transform_base_to_candidate(&inst.spacing_collision_base_shape, p.x, p.y, p.rotation_deg)
            .map(Rc::new)
    }

    /// Full CDE rebuild of the collision state from the native layout.
    pub fn build(layout: &SparrowLayout, instances: &[SPInstance], sheets: &[SheetShape]) -> Self {
        Self::build_with_diag(
            layout,
            instances,
            sheets,
            &mut SparrowDiagnostics::default(),
        )
    }

    /// Full CDE rebuild, recording quantification queries into `diag`.
    pub fn build_with_diag(
        layout: &SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        diag: &mut SparrowDiagnostics,
    ) -> Self {
        let n = layout.placements.len();
        // SGH-Q36: spacing is active when any instance carries a distinct spacing-expanded
        // base shape (when spacing is off, the two base-shape Rc handles are identical).
        let spacing_applied = instances
            .iter()
            .any(|i| !Rc::ptr_eq(&i.base_shape, &i.spacing_collision_base_shape));
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
            spacing_applied,
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
            self.recompute_boundary_for_item(i, layout, instances, sheets, diag);
        }
        for i in 0..self.n {
            self.recompute_pairs_for_item(i, layout, diag);
        }
    }

    fn recompute_boundary_for_item(
        &mut self,
        i: usize,
        layout: &SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        diag: &mut SparrowDiagnostics,
    ) {
        self.boundary_loss[i] = 0.0;
        let pi = &layout.placements[i];
        // SGH-Q36: boundary/container uses ORIGINAL geometry. When spacing is active,
        // `self.shapes[i]` is the spacing-expanded shape (for pairs), so build the
        // original shape on the fly here; otherwise reuse the cached shape (identical).
        let shape_i = if self.spacing_applied {
            let inst = &instances[pi.instance_idx];
            match transform_base_to_candidate(&inst.base_shape, pi.x, pi.y, pi.rotation_deg) {
                Some(s) => Rc::new(s),
                None => {
                    self.unsupported = true;
                    diag.unsupported_queries += 1;
                    return;
                }
            }
        } else {
            let Some(shape_i) = self.shapes[i].clone() else {
                self.unsupported = true;
                diag.unsupported_queries += 1;
                return;
            };
            shape_i
        };
        let si = pi.sheet_index;

        // Boundary / container clearance (quantified).
        if let Some(sheet_shape) = self.sheet_shapes.get(si).and_then(|s| s.clone()) {
            let adapter = CdeAdapter::with_sparrow_strict();
            match adapter.query_boundary(&shape_i, &sheet_shape) {
                CdeQueryResult::NoCollision => {}
                CdeQueryResult::Collision => {
                    let dist =
                        quantify_collision_poly_container_native(&shape_i, &sheet_shape, diag);
                    self.boundary_loss[i] = dist.max(QUANT_FLOOR);
                }
                CdeQueryResult::Unsupported { .. } => {
                    self.unsupported = true;
                    diag.unsupported_queries += 1;
                    self.boundary_loss[i] = BIG_UNSUPPORTED_LOSS;
                }
            }
        }
    }

    fn recompute_pairs_for_item(
        &mut self,
        i: usize,
        layout: &SparrowLayout,
        diag: &mut SparrowDiagnostics,
    ) {
        let Some(shape_i) = self.shapes[i].clone() else {
            self.unsupported = true;
            diag.unsupported_queries += 1;
            return;
        };
        let si = layout.placements[i].sheet_index;
        let others: Vec<(usize, Rc<CdePreparedShape>)> = ((i + 1)..self.n)
            .filter(|&j| j != i && layout.placements[j].sheet_index == si)
            .filter_map(|j| self.shapes[j].clone().map(|s| (j, s)))
            .filter(|(_, s)| bbox_may_overlap(&shape_i, s))
            .collect();
        if let Some(sheet_shape) = self.sheet_shapes.get(si).and_then(|s| s.clone()) {
            if let Some(session) = CdeCandidateSession::build_with_policy(
                others.clone(),
                &sheet_shape,
                pair_touching_policy(self.spacing_applied),
            ) {
                let res = session.query(&shape_i);
                if res.unsupported {
                    self.unsupported = true;
                    diag.unsupported_queries += 1;
                }
                // Map session hole index back to the actual layout index.
                for &layout_j in &res.colliding_layout_idxs {
                    let key = if i < layout_j {
                        (i, layout_j)
                    } else {
                        (layout_j, i)
                    };
                    let fixed = match others.iter().find(|(jj, _)| *jj == layout_j) {
                        Some((_, s)) => s.clone(),
                        None => continue,
                    };
                    let dist = quantify_collision_poly_poly_native(&shape_i, &fixed, diag);
                    self.pair_loss.insert(key, dist.max(QUANT_FLOOR));
                    self.pair_weight.entry(key).or_insert(1.0);
                }
            }
        }
    }

    /// Upstream alias for `update_after_move` (register a single item's move).
    pub fn register_item_move(
        &mut self,
        i: usize,
        layout: &SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        diag: &mut SparrowDiagnostics,
    ) {
        self.update_after_move(i, layout, instances, sheets, diag, None);
    }

    /// Incremental update after item `i` moved (its placement/shape changed).
    ///
    /// `live_session`: when `Some`, the backward-pair recompute uses the live session
    /// (item `i` must NOT be in it — it was deregistered before search) instead of
    /// building per-pair mini-sessions. When `None`: original mini-session fallback.
    pub fn update_after_move(
        &mut self,
        i: usize,
        layout: &SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
        diag: &mut SparrowDiagnostics,
        live_session: Option<&mut CdeCandidateSession>,
    ) {
        self.shapes[i] = Self::prepare_item(layout, instances, i);
        self.incremental_updates += 1;
        diag.native_tracker_incremental_updates += 1;
        self.pair_loss.retain(|&(a, b), _| a != i && b != i);
        self.recompute_boundary_for_item(i, layout, instances, sheets, diag);
        self.recompute_pairs_for_item(i, layout, diag);
        if let Some(session) = live_session {
            // Fast path: query the live session once with i's new shape to get all
            // backward-pair collisions. Item i is NOT in the session (deregistered
            // before search); all j items are at their current positions.
            if let Some(shape_i) = self.shapes[i].clone() {
                let res = session.query(&shape_i);
                if res.unsupported {
                    self.unsupported = true;
                    diag.unsupported_queries += 1;
                } else {
                    for &j in &res.colliding_layout_idxs {
                        if j >= i { continue; }
                        if layout.placements[j].sheet_index != layout.placements[i].sheet_index {
                            continue;
                        }
                        let Some(shape_j) = self.shapes[j].clone() else { continue; };
                        let dist = quantify_collision_poly_poly_native(&shape_j, &shape_i, diag);
                        self.pair_loss.insert((j, i), dist.max(QUANT_FLOOR));
                        self.pair_weight.entry((j, i)).or_insert(1.0);
                    }
                }
            }
        } else {
            // Fallback: per-pair mini-session build (backward compat, exploration phase).
            for j in 0..i {
                if layout.placements[j].sheet_index != layout.placements[i].sheet_index {
                    continue;
                }
                let Some(shape_j) = self.shapes[j].clone() else {
                    continue;
                };
                let Some(shape_i) = self.shapes[i].clone() else {
                    continue;
                };
                if !bbox_may_overlap(&shape_i, &shape_j) {
                    continue;
                }
                let Some(sheet_shape) = self
                    .sheet_shapes
                    .get(layout.placements[i].sheet_index)
                    .and_then(|s| s.clone())
                else {
                    continue;
                };
                let Some(session) =
                    CdeCandidateSession::build_with_policy(
                        vec![(i, shape_i.clone())],
                        &sheet_shape,
                        pair_touching_policy(self.spacing_applied),
                    )
                else {
                    continue;
                };
                let res = session.query(&shape_j);
                if res.unsupported {
                    self.unsupported = true;
                    diag.unsupported_queries += 1;
                    continue;
                }
                if !res.colliding_layout_idxs.is_empty() {
                    let dist = quantify_collision_poly_poly_native(&shape_j, &shape_i, diag);
                    self.pair_loss.insert((j, i), dist.max(QUANT_FLOOR));
                    self.pair_weight.entry((j, i)).or_insert(1.0);
                }
            }
        }
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
        let bnd: f64 = (0..self.n)
            .map(|i| self.boundary_loss[i] * self.boundary_weight[i])
            .sum();
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
    // ── Upstream-style tracker authority accessors (SGH-Q24R9) ──────────────
    /// Quantified raw pair loss for the ordered pair (min,max). 0 if not colliding.
    pub fn pair_loss(&self, i: usize, j: usize) -> f64 {
        let key = if i < j { (i, j) } else { (j, i) };
        self.pair_loss.get(&key).copied().unwrap_or(0.0)
    }
    /// GLS pair weight for the pair (>= 1.0).
    pub fn pair_weight(&self, i: usize, j: usize) -> f64 {
        let key = if i < j { (i, j) } else { (j, i) };
        self.pair_weight.get(&key).copied().unwrap_or(1.0)
    }
    /// Quantified raw container/boundary loss for item `i`.
    pub fn container_loss(&self, i: usize) -> f64 {
        self.boundary_loss.get(i).copied().unwrap_or(0.0)
    }
    /// GLS container/boundary weight for item `i` (>= 1.0).
    pub fn container_weight(&self, i: usize) -> f64 {
        self.boundary_weight.get(i).copied().unwrap_or(1.0)
    }
    /// Upstream alias: raw loss of an item (sum of its quantified records).
    pub fn item_raw_loss(&self, i: usize) -> f64 {
        self.raw_loss_for_item(i)
    }
    /// Upstream alias: weighted loss of an item (raw × GLS weights).
    pub fn item_weighted_loss(&self, i: usize) -> f64 {
        self.weighted_loss_for_item(i)
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
            b.1.partial_cmp(&a.1)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(a.0.cmp(&b.0))
        });
        set.into_iter().map(|(i, _)| i).collect()
    }

    /// GLS Algorithm 8 (upstream `CollisionTracker::update_weights`): for every
    /// entry, EITHER decay its weight back toward 1.0 if it is currently clear,
    /// OR increase it in proportion to how bad its collision is relative to the
    /// worst collision — never both. Uses the upstream GLS constants.
    pub fn update_weights(&mut self) {
        let max_loss = self
            .pair_loss
            .values()
            .copied()
            .chain(self.boundary_loss.iter().copied())
            .fold(0.0_f64, f64::max)
            .max(1e-9);
        // Pair weights: iterate the union of currently-colliding pairs and any pair
        // that still carries a non-default weight (so resolved pairs decay back).
        let pair_keys: Vec<(usize, usize)> = self
            .pair_weight
            .keys()
            .copied()
            .chain(self.pair_loss.keys().copied())
            .collect();
        for k in pair_keys {
            let loss = self.pair_loss.get(&k).copied().unwrap_or(0.0);
            let mult = if loss == 0.0 {
                GLS_WEIGHT_DECAY
            } else {
                let ratio = (loss / max_loss).clamp(0.0, 1.0);
                GLS_WEIGHT_MIN_INC_RATIO + (GLS_WEIGHT_MAX_INC_RATIO - GLS_WEIGHT_MIN_INC_RATIO) * ratio
            };
            let w = self.pair_weight.entry(k).or_insert(1.0);
            *w = (*w * mult).max(1.0);
        }
        // Container / boundary weights.
        for i in 0..self.n {
            let mult = if self.boundary_loss[i] == 0.0 {
                GLS_WEIGHT_DECAY
            } else {
                let ratio = (self.boundary_loss[i] / max_loss).clamp(0.0, 1.0);
                GLS_WEIGHT_MIN_INC_RATIO + (GLS_WEIGHT_MAX_INC_RATIO - GLS_WEIGHT_MIN_INC_RATIO) * ratio
            };
            self.boundary_weight[i] = (self.boundary_weight[i] * mult).max(1.0);
        }
    }

    /// Upstream alias for `update_weights` (GLS Algorithm 8).
    pub fn update_weights_gls(&mut self) {
        self.update_weights();
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
    pub fn final_validation(
        layout: &SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
    ) -> bool {
        Self::final_validation_tracker(layout, instances, sheets).is_feasible()
    }

    pub fn final_validation_tracker(
        layout: &SparrowLayout,
        instances: &[SPInstance],
        sheets: &[SheetShape],
    ) -> Self {
        SparrowCollisionTracker::build(layout, instances, sheets)
    }
}

/// Minimum stored loss for any CDE-confirmed collision.
pub(crate) const QUANT_FLOOR: f64 = 1e-3;
/// Upstream GLS weight-update constants (`.cache/sparrow/src/consts.rs`).
const GLS_WEIGHT_MAX_INC_RATIO: f64 = 2.0;
const GLS_WEIGHT_MIN_INC_RATIO: f64 = 1.2;
const GLS_WEIGHT_DECAY: f64 = 0.95;
/// Loss assigned to an unsupported-geometry verdict (treated honestly as a hard,
/// large violation — never as no-collision).
pub(crate) const BIG_UNSUPPORTED_LOSS: f64 = 1.0e6;

pub(crate) fn set_quant_config(_cfg: SparrowConfig) {
    // The Q25-R1 production quantifier is the upstream overlap-proxy model and
    // no longer reads solve-scoped probe budgets. Keep this hook for the stable
    // optimizer call boundary.
}

#[derive(Clone)]
pub struct TrackerSnapshot {
    pub(crate) shapes: Vec<Option<Rc<CdePreparedShape>>>,
    pub(crate) pair_loss: HashMap<(usize, usize), f64>,
    pub(crate) boundary_loss: Vec<f64>,
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
    pub best_infeasible_pair_count: usize,
}

impl SparrowState {
    pub fn new(layout: SparrowLayout, instances: &[SPInstance], sheets: &[SheetShape]) -> Self {
        Self::new_with_diag(
            layout,
            instances,
            sheets,
            &mut SparrowDiagnostics::default(),
        )
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
            best_infeasible_pair_count: tracker.colliding_pairs(),
            layout,
            tracker,
        }
    }
    pub fn refresh_incumbents(&mut self) {
        if self.tracker.is_feasible() {
            self.best_feasible = Some(self.layout.clone());
        } else {
            let raw = self.tracker.total_raw_loss();
            let pairs = self.tracker.colliding_pairs();
            if raw < self.best_infeasible_raw_loss
                || pairs < self.best_infeasible_pair_count
                || self.best_infeasible.is_none()
            {
                self.best_infeasible = Some(self.layout.clone());
                self.best_infeasible_raw_loss = raw;
                self.best_infeasible_pair_count = pairs;
            }
        }
    }
}

pub(crate) fn bbox_may_overlap(a: &CdePreparedShape, b: &CdePreparedShape) -> bool {
    !(a.max_x < b.min_x || b.max_x < a.min_x || a.max_y < b.min_y || b.max_y < a.min_y)
}

/// Upstream pair quantification: overlap area proxy plus shape penalty.
/// Collision existence remains decided by the local CDE session/query.
pub(crate) fn quantify_collision_poly_poly_native(
    candidate: &CdePreparedShape,
    fixed: &CdePreparedShape,
    diag: &mut SparrowDiagnostics,
) -> f64 {
    quantify_collision_poly_poly(candidate, fixed, diag).max(QUANT_FLOOR)
}

/// Upstream container quantification adapted to a fixed VRS sheet shape.
/// Boundary violation existence remains decided by the local CDE query.
pub(crate) fn quantify_collision_poly_container_native(
    candidate: &CdePreparedShape,
    sheet_shape: &CdePreparedShape,
    diag: &mut SparrowDiagnostics,
) -> f64 {
    quantify_collision_poly_container(candidate, sheet_shape, diag).max(QUANT_FLOOR)
}
