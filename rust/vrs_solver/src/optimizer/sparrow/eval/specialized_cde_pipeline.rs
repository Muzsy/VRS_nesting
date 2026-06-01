use super::*;

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

/// Local counterpart of upstream `SpecializedHazardCollector`.
///
/// The VRS CDE adapter exposes batch query results rather than jagua's
/// `HazardCollector` trait, so this collector owns the incremental loss cache
/// and receives hazards from `collect_poly_collisions_in_detector_custom`.
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

    fn add_container(&mut self, candidate: &CdePreparedShape, diag: &mut SparrowDiagnostics) {
        let raw = quantify_collision_poly_container_native(candidate, self.sheet_shape, diag)
            .max(QUANT_FLOOR);
        let weight = self.tracker.container_weight(self.target);
        self.container_hazard_count += 1;
        self.hazards
            .push(SpecializedHazard::Container { loss: raw, weight });
        self.add_loss(raw * weight);
    }

    fn add_pair(
        &mut self,
        candidate: &CdePreparedShape,
        layout_idx: usize,
        diag: &mut SparrowDiagnostics,
    ) {
        let Some(Some(fixed)) = self.fixed_shapes.get(layout_idx) else {
            self.add_unsupported();
            return;
        };
        let raw = quantify_collision_poly_poly_native(candidate, fixed, diag).max(QUANT_FLOOR);
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

pub(crate) fn collect_poly_collisions_in_detector_custom(
    session: &CdeCandidateSession,
    candidate: &CdePreparedShape,
    collector: &mut SpecializedCdeHazardCollector<'_>,
    diag: &mut SparrowDiagnostics,
) {
    let res = session.query(candidate);
    if res.unsupported {
        diag.unsupported_queries += 1;
        collector.add_unsupported();
        if collector.early_terminate() {
            return;
        }
    }
    if res.boundary_collision {
        collector.add_container(candidate, diag);
        if collector.early_terminate() {
            return;
        }
    }
    for layout_idx in res.colliding_layout_idxs {
        collector.add_pair(candidate, layout_idx, diag);
        if collector.early_terminate() {
            return;
        }
    }
}
