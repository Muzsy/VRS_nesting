use super::*;
use std::f64::consts::PI;

#[derive(Clone, Debug)]
pub(crate) enum SpecializedHazard {
    Pair {
        layout_idx: usize,
        loss: f64,
        weight: f64,
    },
    Container {
        loss: f64,
        weight: f64,
    },
    Unsupported,
}

/// Local counterpart of upstream `SpecializedHazardCollector`
/// (`.cache/sparrow/src/eval/specialized_jaguars_pipeline.rs`).
///
/// It computes the tracker-weighted loss incrementally *on the fly* as the CDE
/// reports hazards (via the [`SpecializedHazardSink`] trait), caches the running
/// total, and supports loss-bound early termination — so a sample that is already
/// dominated by a previously found one can abort before all of its collisions are
/// detected/quantified. This is the upstream behaviour, not a post-`query`
/// batch accumulation.
pub(crate) struct SpecializedCdeHazardCollector<'a> {
    pub(crate) target: usize,
    pub(crate) tracker: &'a SparrowCollisionTracker,
    pub(crate) fixed_shapes: &'a [Option<Rc<CdePreparedShape>>],
    pub(crate) sheet_shape: &'a CdePreparedShape,
    pub(crate) hazards: Vec<SpecializedHazard>,
    accumulated_loss: f64,
    loss_bound: f64,
    early_terminated: bool,
    pub(crate) pair_hazard_count: usize,
    pub(crate) container_hazard_count: usize,
    pub(crate) unsupported_hazard_count: usize,
}

impl<'a> SpecializedCdeHazardCollector<'a> {
    pub(crate) fn new(
        target: usize,
        tracker: &'a SparrowCollisionTracker,
        fixed_shapes: &'a [Option<Rc<CdePreparedShape>>],
        sheet_shape: &'a CdePreparedShape,
    ) -> Self {
        Self {
            target,
            tracker,
            fixed_shapes,
            sheet_shape,
            hazards: Vec::new(),
            accumulated_loss: 0.0,
            loss_bound: f64::INFINITY,
            early_terminated: false,
            pair_hazard_count: 0,
            container_hazard_count: 0,
            unsupported_hazard_count: 0,
        }
    }

    /// Reload for a new query against the given `loss_bound` (upstream `reload`).
    pub(crate) fn reload(&mut self, loss_bound: f64) {
        self.hazards.clear();
        self.accumulated_loss = 0.0;
        self.loss_bound = loss_bound;
        self.early_terminated = false;
        self.pair_hazard_count = 0;
        self.container_hazard_count = 0;
        self.unsupported_hazard_count = 0;
    }

    pub(crate) fn is_empty(&self) -> bool {
        self.hazards.is_empty()
    }

    pub(crate) fn loss(&self) -> f64 {
        self.accumulated_loss
    }

    pub(crate) fn early_terminate(&self) -> bool {
        self.early_terminated
    }

    fn add_loss(&mut self, loss: f64) {
        self.accumulated_loss += loss;
        if self.accumulated_loss > self.loss_bound {
            self.early_terminated = true;
        }
    }

    fn add_container(&mut self, candidate: &CdePreparedShape) {
        let raw = quantify_collision_poly_container_value(candidate, self.sheet_shape).max(QUANT_FLOOR);
        let weight = self.tracker.container_weight(self.target);
        self.container_hazard_count += 1;
        self.hazards
            .push(SpecializedHazard::Container { loss: raw, weight });
        self.add_loss(raw * weight);
    }

    fn add_pair(&mut self, candidate: &CdePreparedShape, layout_idx: usize) {
        let Some(Some(fixed)) = self.fixed_shapes.get(layout_idx) else {
            self.add_unsupported();
            return;
        };
        let raw = quantify_collision_poly_poly_value(candidate, fixed).max(QUANT_FLOOR);
        let weight = self.tracker.pair_weight(self.target, layout_idx);
        self.pair_hazard_count += 1;
        self.hazards.push(SpecializedHazard::Pair {
            layout_idx,
            loss: raw,
            weight,
        });
        self.add_loss(raw * weight);
    }

    fn add_unsupported(&mut self) {
        self.unsupported_hazard_count += 1;
        self.hazards.push(SpecializedHazard::Unsupported);
        self.add_loss(BIG_UNSUPPORTED_LOSS);
    }
}

/// The collector receives hazards from the CDE traversal as they are found and
/// accumulates tracker-weighted loss, terminating early once the loss bound is
/// exceeded. This is the upstream `SpecializedHazardCollector` contract.
impl<'a> SpecializedHazardSink for SpecializedCdeHazardCollector<'a> {
    fn accept_pair(&mut self, candidate: &CdePreparedShape, layout_idx: usize) {
        self.add_pair(candidate, layout_idx);
    }

    fn accept_container(&mut self, candidate: &CdePreparedShape) {
        self.add_container(candidate);
    }

    fn accept_unsupported(&mut self) {
        self.add_unsupported();
    }

    fn should_terminate(&self) -> bool {
        self.early_terminated
    }
}

/// Upstream `collect_poly_collisions_in_detector_custom`
/// (`.cache/sparrow/src/eval/specialized_jaguars_pipeline.rs`).
///
/// Runs the bounded / visitor CDE collection so the collector accumulates
/// tracker-weighted loss *during* hazard detection (with loss-bound early
/// termination), not from a completed batch `query` result. Three phases, exactly
/// upstream order:
///
/// 1. **Pole pre-pass** — query the candidate's surrogate poles to surface obvious
///    collisions fast and raise the loss early, stopping once the checked poles
///    cover more than 50% of the shape area (`shape.area * 0.5 / PI`), with
///    loss-bound early termination after each pole.
/// 2. **Bit-reversed edge traversal** — query each candidate edge against the
///    virtual quadtree root in bit-reversed order (surfaces new hazards early),
///    with early termination after each edge.
/// 3. **Containment pass** — hazards that contain / are contained by the candidate
///    without an edge intersection, again with early termination.
///
/// Quantification counts gathered by the collector are merged into the run
/// diagnostics afterwards.
pub(crate) fn collect_poly_collisions_in_detector_custom(
    session: &CdeCandidateSession,
    candidate: &CdePreparedShape,
    collector: &mut SpecializedCdeHazardCollector<'_>,
    diag: &mut SparrowDiagnostics,
) {
    let cde_t0 = if diag.profiling_enabled { Some(std::time::Instant::now()) } else { None };
    let mut ctx = session.begin_specialized_collection(candidate);

    // Phase 1: pole pre-pass. Check poles until their cumulative area exceeds the
    // upstream threshold (`shape.area * 0.5 / PI`), failing fast on early hazards.
    let (poles, shape_area) = session.candidate_poles_and_area(candidate);
    let area_threshold = shape_area * 0.5 / PI;
    let mut area_sum = 0.0;
    for pole in &poles {
        session.collect_pole_hazards(&mut ctx, pole, candidate, collector);
        if collector.early_terminate() {
            diag.profile_early_termination_count += 1;
            merge_quant_counts(collector, diag);
            if let Some(t) = cde_t0 { diag.profile_cde_query_collect_ms += t.elapsed().as_secs_f64() * 1000.0; }
            return;
        }
        area_sum += pole.radius * pole.radius;
        if area_sum > area_threshold {
            break;
        }
    }

    // Phase 2: bit-reversed edge traversal.
    let n_edges = session.n_candidate_edges(candidate);
    for edge_index in bit_reversal_order(n_edges) {
        session.collect_edge_hazards(&mut ctx, candidate, edge_index, collector);
        if collector.early_terminate() {
            diag.profile_early_termination_count += 1;
            merge_quant_counts(collector, diag);
            if let Some(t) = cde_t0 { diag.profile_cde_query_collect_ms += t.elapsed().as_secs_f64() * 1000.0; }
            return;
        }
    }

    // Phase 3: containment pass (early termination handled inside).
    session.collect_containment_hazards(&mut ctx, candidate, collector);
    merge_quant_counts(collector, diag);
    if let Some(t) = cde_t0 { diag.profile_cde_query_collect_ms += t.elapsed().as_secs_f64() * 1000.0; }
}

fn merge_quant_counts(collector: &SpecializedCdeHazardCollector<'_>, diag: &mut SparrowDiagnostics) {
    diag.quantified_pair_queries += collector.pair_hazard_count;
    diag.quantified_boundary_queries += collector.container_hazard_count;
    diag.unsupported_queries += collector.unsupported_hazard_count;
}

/// Visit `0..n` in bit-reversed order (upstream `BitReversalIterator`): spreads
/// successive indices across the range so new hazards are surfaced early, which
/// makes loss-bound early termination kick in sooner.
fn bit_reversal_order(n: usize) -> Vec<usize> {
    if n <= 2 {
        return (0..n).collect();
    }
    let bits = (usize::BITS - (n - 1).leading_zeros()) as usize;
    let mut out = Vec::with_capacity(n);
    let mut placed = vec![false; n];
    for i in 0..(1usize << bits) {
        // Reverse the low `bits` bits of i.
        let mut r = 0usize;
        for b in 0..bits {
            if i & (1 << b) != 0 {
                r |= 1 << (bits - 1 - b);
            }
        }
        if r < n && !placed[r] {
            placed[r] = true;
            out.push(r);
        }
    }
    out
}
