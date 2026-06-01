use super::*;

// ---------------------------------------------------------------------------
// tracker (native, CDE-backed, quantified loss)
// ---------------------------------------------------------------------------

/// Native CDE-backed collision tracker. Owns quantified pair/boundary records +
/// GLS weights. Collision EXISTENCE is decided by the CDE adapter
/// (`CdeCandidateSession` / jagua `CDEngine`); the stored loss is a CDE-truth
/// quantified separation/resolution distance (never a binary count).
pub struct SparrowCollisionTracker {
    pub(crate) n: usize,
    /// Prepared CDE shapes per instance index (rebuilt lazily after a move).
    pub(crate) shapes: Vec<Option<Rc<CdePreparedShape>>>,
    /// Prepared sheet shapes per sheet index.
    pub(crate) sheet_shapes: Vec<Option<Rc<CdePreparedShape>>>,
    /// Quantified raw pair loss (resolution distance proxy), keyed i<j.
    pub(crate) pair_loss: HashMap<(usize, usize), f64>,
    /// GLS pair weights, i<j.
    pub(crate) pair_weight: HashMap<(usize, usize), f64>,
    /// Quantified raw boundary/container loss per item (clearance distance).
    pub(crate) boundary_loss: Vec<f64>,
    /// GLS boundary/container weights per item.
    pub(crate) boundary_weight: Vec<f64>,
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
    fn prepare_item(
        layout: &SparrowLayout,
        instances: &[SPInstance],
        idx: usize,
    ) -> Option<Rc<CdePreparedShape>> {
        let p = &layout.placements[idx];
        let inst = &instances[p.instance_idx];
        prepare_shape_native(&inst.part, p.x, p.y, p.rotation_deg)
            .ok()
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
        _instances: &[SPInstance],
        sheets: &[SheetShape],
        diag: &mut SparrowDiagnostics,
    ) {
        self.boundary_loss[i] = 0.0;
        let Some(shape_i) = self.shapes[i].clone() else {
            self.unsupported = true;
            diag.unsupported_queries += 1;
            return;
        };
        let pi = &layout.placements[i];
        let si = pi.sheet_index;

        // Boundary / container clearance (quantified).
        if let Some(sheet_shape) = self.sheet_shapes.get(si).and_then(|s| s.clone()) {
            let adapter = CdeAdapter::with_defaults();
            match adapter.query_boundary(&shape_i, &sheet_shape) {
                CdeQueryResult::NoCollision => {}
                CdeQueryResult::Collision => {
                    let dist = quantify_collision_poly_container_native(&shape_i, &sheet_shape, diag);
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
            if let Some(session) = CdeCandidateSession::build(others.clone(), &sheet_shape) {
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
        self.update_after_move(i, layout, instances, sheets, diag);
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
        self.pair_loss.retain(|&(a, b), _| a != i && b != i);
        self.recompute_boundary_for_item(i, layout, instances, sheets, diag);
        self.recompute_pairs_for_item(i, layout, diag);
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
            let Some(session) = CdeCandidateSession::build(vec![(i, shape_i.clone())], &sheet_shape)
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

    /// GLS Algorithm 8: decay clear entries and increase colliding entries
    /// proportionally to their current loss relative to the maximum loss.
    pub fn update_weights(&mut self) {
        let max_loss = self
            .pair_loss
            .values()
            .copied()
            .chain(self.boundary_loss.iter().copied())
            .fold(0.0_f64, f64::max)
            .max(1e-9);
        const DECAY: f64 = 0.995;
        const MIN_INC: f64 = 1.05;
        const MAX_INC: f64 = 1.30;
        for (k, &loss) in self.pair_loss.iter() {
            let ratio = (loss / max_loss).clamp(0.0, 1.0);
            let mult = MIN_INC + (MAX_INC - MIN_INC) * ratio;
            let w = self.pair_weight.entry(*k).or_insert(1.0);
            *w = (*w * mult).max(1.0).min(50.0);
        }
        for w in self.pair_weight.values_mut() {
            *w = (*w * DECAY).max(1.0);
        }
        for i in 0..self.n {
            if self.boundary_loss[i] > 0.0 {
                let ratio = (self.boundary_loss[i] / max_loss).clamp(0.0, 1.0);
                let mult = MIN_INC + (MAX_INC - MIN_INC) * ratio;
                self.boundary_weight[i] = (self.boundary_weight[i] * mult).max(1.0).min(50.0);
            } else {
                self.boundary_weight[i] = (self.boundary_weight[i] * DECAY).max(1.0);
            }
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

/// Minimum stored loss for any CDE-confirmed collision (so a confirmed positive
/// never rounds to a feasible 0 because of probe resolution).
pub(crate) const QUANT_FLOOR: f64 = 1e-3;
/// Loss assigned to an unsupported-geometry verdict (treated honestly as a hard,
/// large violation — never as no-collision).
pub(crate) const BIG_UNSUPPORTED_LOSS: f64 = 1.0e6;

thread_local! {
    /// Solve-scoped probe config so the tracker's `recompute_item` (which has no
    /// `cfg` parameter on the public API surface used by callers/tests) can reach
    /// the active probe budget. Set at the start of each `solve`.
    static QUANT_CFG: std::cell::RefCell<SparrowConfig> = std::cell::RefCell::new(
        SparrowConfig::from_solver_input(1.0, CollisionBackendKind::Cde, RotationResolveContext::legacy_default(), 0)
    );
}

pub(crate) fn set_quant_config(cfg: SparrowConfig) {
    QUANT_CFG.with(|c| *c.borrow_mut() = cfg);
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

fn shape_convex_area(s: &CdePreparedShape) -> f64 {
    bbox_area(s)
}

fn bbox_area(s: &CdePreparedShape) -> f64 {
    ((s.max_x - s.min_x).max(0.0) * (s.max_y - s.min_y).max(0.0)).max(1.0)
}

/// SGH-Q24R9 CDE-truth pair quantification (Sparrow tracker parity).
///
/// Existence of the collision is decided by the CDE (the caller only invokes this
/// for a CDE-confirmed colliding pair). The *magnitude* is the minimal translation
/// distance that separates `candidate` from `fixed` along their centroid axis,
/// found by a bracket-doubling + binary-refinement probe in which **every step is
/// resolved by the CDE** (`query_pair`). No bbox/AABB overlap area is used as the
/// loss magnitude; bbox is only a centroid/direction hint.
pub(crate) fn quantify_collision_poly_poly_native(
    candidate: &CdePreparedShape,
    fixed: &CdePreparedShape,
    diag: &mut SparrowDiagnostics,
) -> f64 {
    let (n_bracket, n_refine) = QUANT_CFG.with(|c| {
        let c = c.borrow();
        (c.probe_bracket_steps.max(1), c.probe_binary_refine_steps.max(1))
    });
    let adapter = CdeAdapter::with_defaults();
    let cx = (candidate.min_x + candidate.max_x) * 0.5;
    let cy = (candidate.min_y + candidate.max_y) * 0.5;
    let fx = (fixed.min_x + fixed.max_x) * 0.5;
    let fy = (fixed.min_y + fixed.max_y) * 0.5;
    let (dir_x, dir_y) = probe_unit(cx - fx, cy - fy);
    let span =
        (candidate.max_x - candidate.min_x).max(candidate.max_y - candidate.min_y).max(1.0);
    let base_step = (span * 0.08).max(1.0);
    let pair_collides_at = |t: f64, diag: &mut SparrowDiagnostics| -> bool {
        match translate_prepared(candidate, dir_x * t, dir_y * t) {
            Some(s) => {
                diag.quantified_pair_queries += 1;
                matches!(adapter.query_pair(&s, fixed), CdeQueryResult::Collision)
            }
            None => {
                diag.unsupported_queries += 1;
                true
            }
        }
    };
    let resolution_distance = probe_resolution(base_step, n_bracket, n_refine, diag, pair_collides_at);
    resolution_distance.max(QUANT_FLOOR)
}

/// SGH-Q24R9 CDE-truth container quantification (Sparrow tracker parity).
///
/// The CDE decides the boundary violation; the magnitude is the minimal
/// translation toward the container centroid that brings `candidate` inside,
/// found by the same CDE-resolved probe (`query_boundary`). No bbox-outside-area
/// proxy is used.
pub(crate) fn quantify_collision_poly_container_native(
    candidate: &CdePreparedShape,
    sheet_shape: &CdePreparedShape,
    diag: &mut SparrowDiagnostics,
) -> f64 {
    let (n_bracket, n_refine) = QUANT_CFG.with(|c| {
        let c = c.borrow();
        (c.probe_bracket_steps.max(1), c.probe_binary_refine_steps.max(1))
    });
    let adapter = CdeAdapter::with_defaults();
    let cx = (candidate.min_x + candidate.max_x) * 0.5;
    let cy = (candidate.min_y + candidate.max_y) * 0.5;
    let sx = (sheet_shape.min_x + sheet_shape.max_x) * 0.5;
    let sy = (sheet_shape.min_y + sheet_shape.max_y) * 0.5;
    let (dir_x, dir_y) = probe_unit(sx - cx, sy - cy);
    let span =
        (candidate.max_x - candidate.min_x).max(candidate.max_y - candidate.min_y).max(1.0);
    let base_step = (span * 0.10).max(1.0);
    let outside_at = |t: f64, diag: &mut SparrowDiagnostics| -> bool {
        match translate_prepared(candidate, dir_x * t, dir_y * t) {
            Some(s) => {
                diag.quantified_boundary_queries += 1;
                matches!(adapter.query_boundary(&s, sheet_shape), CdeQueryResult::Collision)
            }
            None => {
                diag.unsupported_queries += 1;
                true
            }
        }
    };
    let resolution_distance = probe_resolution(base_step, n_bracket, n_refine, diag, outside_at);
    (2.0 * resolution_distance).max(QUANT_FLOOR)
}

/// Unit direction with a deterministic +x fallback for a degenerate vector.
fn probe_unit(dx: f64, dy: f64) -> (f64, f64) {
    let n = (dx * dx + dy * dy).sqrt();
    if n < 1e-9 {
        (1.0, 0.0)
    } else {
        (dx / n, dy / n)
    }
}

/// Shared bracket-doubling + binary-refinement resolution probe. `collides_at`
/// must return whether the shape (translated by `t` along the probe direction)
/// still collides per the CDE. Returns the minimal clearing distance.
fn probe_resolution(
    base_step: f64,
    n_bracket: usize,
    n_refine: usize,
    diag: &mut SparrowDiagnostics,
    mut collides_at: impl FnMut(f64, &mut SparrowDiagnostics) -> bool,
) -> f64 {
    let step0 = base_step.max(1e-3);
    let mut lo = 0.0_f64;
    let mut hi = step0;
    let mut bracketed = false;
    for _ in 0..n_bracket {
        if collides_at(hi, diag) {
            lo = hi;
            hi *= 2.0;
        } else {
            bracketed = true;
            break;
        }
    }
    if !bracketed {
        return hi.max(step0);
    }
    for _ in 0..n_refine {
        let mid = 0.5 * (lo + hi);
        if collides_at(mid, diag) {
            lo = mid;
        } else {
            hi = mid;
        }
    }
    hi.max(step0 * 0.25)
}
