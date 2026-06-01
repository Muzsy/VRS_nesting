use super::*;

pub(crate) struct SeparationEvaluator<'a> {
    pub(crate) target: usize,
    pub(crate) inst: &'a SPInstance,
    pub(crate) sheet: &'a SheetShape,
    pub(crate) sheet_idx: usize,
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
    pub(crate) fn score_candidate(
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
        let res = self.session.query(&shape);
        if res.unsupported {
            diag.search_unsupported_samples += 1;
            return None;
        }
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

        if res.is_clear() {
            return Some(ScoredPlacement {
                score: clear_quality,
                collision_loss: 0.0,
                is_clear: true,
                placement,
            });
        }

        // A colliding candidate can never beat a clear incumbent: short-circuit on
        // the upper bound without paying for hazard ordering (Algorithm 7 prune).
        if matches!(upper_bound, Some(SampleEval::Clear { .. })) {
            return None;
        }
        let bound_loss = match upper_bound {
            Some(SampleEval::Collision { loss }) => loss,
            _ => f64::INFINITY,
        };

        // Collision ordering magnitude: CDE-confirmed hazard penetration scaled by
        // the TRACKER's GLS weights (pair_weight / container_weight). bbox extent is
        // only the broad-phase ordering hint; CDE owns the colliding SET, and the
        // authoritative loss magnitude remains the tracker's CDE-probe quantifier.
        let cand_bbox = (shape.min_x, shape.min_y, shape.max_x, shape.max_y);
        let mut loss = 0.0_f64;
        if res.boundary_collision {
            let over = (self.sheet.min_x - cand_bbox.0).max(0.0)
                + (self.sheet.min_y - cand_bbox.1).max(0.0)
                + (cand_bbox.2 - self.sheet.max_x).max(0.0)
                + (cand_bbox.3 - self.sheet.max_y).max(0.0);
            loss += over.max(QUANT_FLOOR) * self.tracker.container_weight(self.target);
            if loss >= bound_loss {
                return None;
            }
        }
        for &layout_j in &res.colliding_layout_idxs {
            if let Some(Some(fixed)) = self.fixed_shapes.get(layout_j) {
                let pen = hazard_extent_depth(cand_bbox, (fixed.min_x, fixed.min_y, fixed.max_x, fixed.max_y));
                let pair_weight = self.tracker.pair_weight(self.target, layout_j);
                loss += pen.max(QUANT_FLOOR) * pair_weight;
            } else {
                loss += BIG_UNSUPPORTED_LOSS;
            }
            if loss >= bound_loss {
                return None;
            }
        }
        let quantified_loss = loss.max(QUANT_FLOOR);
        Some(ScoredPlacement {
            score: 1_000_000.0 + quantified_loss + clear_quality,
            collision_loss: quantified_loss,
            is_clear: false,
            placement,
        })
    }
}

/// Axis-aligned penetration depth between two bboxes (0 if disjoint). Broad-phase
/// ordering hint only — never the authoritative collision truth or loss.
fn hazard_extent_depth(a: (f64, f64, f64, f64), b: (f64, f64, f64, f64)) -> f64 {
    let ox = (a.2.min(b.2) - a.0.max(b.0)).max(0.0);
    let oy = (a.3.min(b.3) - a.1.max(b.1)).max(0.0);
    ox.min(oy)
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
