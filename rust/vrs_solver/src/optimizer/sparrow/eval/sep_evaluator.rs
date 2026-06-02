use super::*;

pub(crate) struct SeparationEvaluator<'a> {
    pub(crate) target: usize,
    pub(crate) inst: &'a SPInstance,
    pub(crate) sheet: &'a SheetShape,
    pub(crate) sheet_idx: usize,
    pub(crate) sheet_shape: &'a CdePreparedShape,
    pub(crate) session: &'a CdeCandidateSession,
    pub(crate) fixed_shapes: &'a [Option<Rc<CdePreparedShape>>],
    /// Per-instance base shape (POI + surrogate precomputed once); each candidate
    /// is built from it by a cheap rigid transform.
    pub(crate) base: &'a CdeBaseShape,
    /// The native collision tracker is the loss/weight authority. The evaluator
    /// orders candidates by CDE-confirmed hazards scaled by the tracker's GLS
    /// pair/container weights — it does NOT invent local weights.
    pub(crate) tracker: &'a SparrowCollisionTracker,
    pub(crate) n_evals: usize,
}

impl<'a> SeparationEvaluator<'a> {
    /// Evaluate a candidate transform — upstream `SeparationEvaluator::evaluate_sample`
    /// (Algorithm 7). Steps:
    /// 1. prepare the candidate transform (bbox-in-sheet is a broad-phase *fit*
    ///    check only — never a ranking term);
    /// 2. reload the specialized collector with the loss bound derived from the
    ///    current upper bound;
    /// 3. collect hazards through the bounded visitor path;
    /// 4. early-terminate dominated samples (`Invalid`);
    /// 5. score solely from the collector's tracker-weighted loss:
    ///    `Clear { loss: 0.0 }` when no hazard, else `Collision { loss }`.
    fn score_candidate(
        &mut self,
        rmx: f64,
        rmy: f64,
        rot: f64,
        upper_bound: Option<SampleEval>,
        diag: &mut SparrowDiagnostics,
    ) -> Option<ScoredPlacement> {
        let (rw, rh) = dims_for_rotation(self.inst.part.width, self.inst.part.height, rot);
        // Broad-phase fit check: a candidate whose bbox cannot lie inside the sheet
        // is discarded before any CDE work. This is a fit gate, not separation loss.
        if rmx < self.sheet.min_x - 1e-9
            || rmy < self.sheet.min_y - 1e-9
            || rmx + rw > self.sheet.max_x + 1e-9
            || rmy + rh > self.sheet.max_y + 1e-9
        {
            return None;
        }
        let (ax, ay) = placement_anchor_from_rect_min(
            rmx,
            rmy,
            self.inst.part.width,
            self.inst.part.height,
            rot,
        );
        let shape = transform_base_to_candidate(self.base, ax, ay, rot)?;
        self.n_evals += 1;
        diag.search_position_samples += 1;
        let placement = SparrowPlacement {
            instance_idx: self.inst.idx,
            sheet_index: self.sheet_idx,
            x: ax,
            y: ay,
            rotation_deg: rot,
        };

        // Upper bound of quantification above which the sample is guaranteed to be
        // rejected (dominated by a previous one): Collision -> its loss, Clear -> 0,
        // none/Invalid -> +inf.
        let loss_bound = match upper_bound {
            Some(SampleEval::Collision { loss }) => loss,
            Some(SampleEval::Clear { .. }) => 0.0,
            _ => f64::INFINITY,
        };

        let mut collector = SpecializedCdeHazardCollector::new(
            self.target,
            self.tracker,
            self.fixed_shapes,
            self.sheet_shape,
        );
        collector.reload(loss_bound);
        collect_poly_collisions_in_detector_custom(self.session, &shape, &mut collector, diag);

        if collector.early_terminate() {
            // The quantification exceeded the upper bound and collection stopped
            // early. The sample will always be rejected, so report it as dominated.
            return None;
        }
        if collector.is_empty() {
            // No collisions detected -> clear. Upstream returns Clear { loss: 0.0 };
            // positional compaction is the (excluded) compression phase's job, not
            // the separator's.
            return Some(ScoredPlacement {
                score: 0.0,
                collision_loss: 0.0,
                is_clear: true,
                rect_min_x: rmx,
                rect_min_y: rmy,
                placement,
            });
        }
        // Some collisions, within the upper bound -> collision with total tracker-
        // weighted loss from the collector.
        let quantified_loss = collector.loss().max(QUANT_FLOOR);
        Some(ScoredPlacement {
            score: quantified_loss,
            collision_loss: quantified_loss,
            is_clear: false,
            rect_min_x: rmx,
            rect_min_y: rmy,
            placement,
        })
    }
}

impl<'a> SampleEvaluator for SeparationEvaluator<'a> {
    fn evaluate_sample(
        &mut self,
        x: f64,
        y: f64,
        rot: f64,
        upper_bound: Option<SampleEval>,
        diag: &mut SparrowDiagnostics,
    ) -> Option<ScoredPlacement> {
        self.score_candidate(x, y, rot, upper_bound, diag)
    }

    fn n_evals(&self) -> usize {
        self.n_evals
    }
}
