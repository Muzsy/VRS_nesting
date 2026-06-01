use super::*;

pub(crate) struct SeparationEvaluator<'a> {
    pub(crate) target: usize,
    pub(crate) inst: &'a SPInstance,
    pub(crate) sheet: &'a SheetShape,
    pub(crate) sheet_idx: usize,
    pub(crate) sheet_shape: &'a CdePreparedShape,
    pub(crate) session: &'a CdeCandidateSession,
    pub(crate) fixed_shapes: &'a [Option<Rc<CdePreparedShape>>],
    /// The native collision tracker is the loss/weight authority. The evaluator
    /// orders candidates by CDE-confirmed hazards scaled by the tracker's GLS
    /// pair/container weights — it does NOT invent local weights.
    pub(crate) tracker: &'a SparrowCollisionTracker,
    pub(crate) n_evals: usize,
}

impl<'a> SeparationEvaluator<'a> {
    /// Evaluate a candidate transform. CDE decides clear/collision (`session`);
    /// the tracker supplies the GLS weights; `upper_bound` enables early rejection
    /// of dominated samples (Sparrow Algorithm 7 semantics).
    fn score_candidate(
        &mut self,
        rmx: f64,
        rmy: f64,
        rot: f64,
        upper_bound: Option<SampleEval>,
        diag: &mut SparrowDiagnostics,
    ) -> Option<ScoredPlacement> {
        let (rw, rh) = dims_for_rotation(self.inst.part.width, self.inst.part.height, rot);
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
        let shape = prepare_shape_native(&self.inst.part, ax, ay, rot).ok()?;
        self.n_evals += 1;
        diag.search_position_samples += 1;
        let placement = SparrowPlacement {
            instance_idx: self.inst.idx,
            sheet_index: self.sheet_idx,
            x: ax,
            y: ay,
            rotation_deg: rot,
        };
        let clear_quality = ((rmy - self.sheet.min_y).max(0.0) / self.sheet.height.max(1.0))
            + ((rmx - self.sheet.min_x).max(0.0) / self.sheet.width.max(1.0)) * 0.1
            + (self.sheet_idx as f64) * 1e-6;

        let bound_loss = match upper_bound {
            Some(SampleEval::Collision { loss }) => loss,
            Some(SampleEval::Clear { .. }) => 0.0,
            _ => f64::INFINITY,
        };
        let _pair_weight_authority = self.tracker.pair_weight(self.target, self.target);

        let mut collector = SpecializedCdeHazardCollector::new(
            self.target,
            self.tracker,
            self.fixed_shapes,
            self.sheet_shape,
        );
        collector.reload(bound_loss);
        collect_poly_collisions_in_detector_custom(self.session, &shape, &mut collector, diag);
        if collector.early_terminate() {
            return None;
        }
        if collector.is_empty() {
            return Some(ScoredPlacement {
                score: clear_quality,
                collision_loss: 0.0,
                is_clear: true,
                placement,
            });
        }
        let loss = collector.loss();
        let quantified_loss = loss.max(QUANT_FLOOR);
        Some(ScoredPlacement {
            score: 1_000_000.0 + quantified_loss + clear_quality,
            collision_loss: quantified_loss,
            is_clear: false,
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
