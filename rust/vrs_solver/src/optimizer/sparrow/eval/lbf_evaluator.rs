use super::*;

pub(crate) struct LBFEvaluator<'a> {
    pub(crate) inst: &'a SPInstance,
    pub(crate) sheet: &'a SheetShape,
    pub(crate) sheet_idx: usize,
    pub(crate) session: &'a CdeCandidateSession,
    /// Per-instance base shape (POI + surrogate precomputed once).
    pub(crate) base: &'a CdeBaseShape,
    pub(crate) n_evals: usize,
}

/// Upstream `LBFEvaluator` implements `SampleEvaluator` so the shared
/// `search_placement` (Algorithm 6) drives LBF construction with the same
/// sampler + two-stage coordinate descent the separator uses. The LBF ignores the
/// upper bound (it only distinguishes clear from collision) — exactly upstream.
impl<'a> SampleEvaluator for LBFEvaluator<'a> {
    fn evaluate_sample(
        &mut self,
        x: f64,
        y: f64,
        rot: f64,
        _upper_bound: Option<SampleEval>,
        _diag: &mut SparrowDiagnostics,
    ) -> Option<ScoredPlacement> {
        self.n_evals += 1;
        self.score_lbf_candidate(x, y, rot)
    }

    fn n_evals(&self) -> usize {
        self.n_evals
    }
}

impl<'a> LBFEvaluator<'a> {
    pub(crate) fn score_lbf_candidate(
        &self,
        rmx: f64,
        rmy: f64,
        rot: f64,
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
        let shape = transform_base_to_candidate(self.base, ax, ay, rot)?;
        let res = self.session.query(&shape);
        if res.unsupported {
            return None;
        }
        if !res.is_clear() {
            return None;
        }
        let placement = SparrowPlacement {
            instance_idx: self.inst.idx,
            sheet_index: self.sheet_idx,
            x: ax,
            y: ay,
            rotation_deg: rot,
        };
        let lbf_quality = (rmx - self.sheet.min_x).max(0.0) * 10.0
            + (rmy - self.sheet.min_y).max(0.0)
            + (self.sheet_idx as f64) * 1e-6;
        Some(ScoredPlacement {
            score: lbf_quality,
            collision_loss: 0.0,
            is_clear: true,
            rect_min_x: rmx,
            rect_min_y: rmy,
            placement,
        })
    }
}
