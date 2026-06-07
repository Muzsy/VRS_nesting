use super::*;

pub struct BestSamples {
    pub(crate) size: usize,
    pub(crate) unique_thresh: f64,
    pub(crate) samples: Vec<ScoredPlacement>,
}

impl BestSamples {
    pub fn new(size: usize, unique_thresh: f64) -> Self {
        Self {
            size: size.max(1),
            unique_thresh,
            samples: Vec::new(),
        }
    }

    /// Insert `cand` into the best-sample set.
    ///
    /// When `diag` is provided and Q30 profiling is enabled, tracks:
    /// - `best_samples_insert_attempts` (every call)
    /// - `best_samples_inserted` (accepted / replaced a dedup)
    /// - `best_samples_dedup_rejects` (position found but cand was worse)
    /// - `best_samples_insert_dedup_ms` (wall-time of the whole call)
    pub(crate) fn report(
        &mut self,
        cand: ScoredPlacement,
        diag: &mut SparrowDiagnostics,
    ) -> bool {
        let p = &mut diag.q30_profile;
        let scope_active = p.enabled && p.profiling_scope_active;
        let t = ProfileTimer::start_if(scope_active);
        if scope_active { p.best_samples_insert_attempts += 1; }

        if cand.eval() >= self.upper_bound() {
            t.add_to(&mut p.best_samples_insert_dedup_ms);
            return false;
        }
        if let Some(idx) = self.samples.iter().position(|s| {
            (s.rect_min_x - cand.rect_min_x).abs() < self.unique_thresh
                && (s.rect_min_y - cand.rect_min_y).abs() < self.unique_thresh
                && (s.placement.rotation_deg - cand.placement.rotation_deg).abs() < 1.0
                && s.placement.sheet_index == cand.placement.sheet_index
        }) {
            if cand.eval() < self.samples[idx].eval() {
                self.samples.remove(idx);
                // falls through to push below
            } else {
                if scope_active { p.best_samples_dedup_rejects += 1; }
                t.add_to(&mut p.best_samples_insert_dedup_ms);
                return false;
            }
        }
        self.samples.push(cand);
        self.samples.sort_by(|a, b| a.eval().cmp(&b.eval()));
        if self.samples.len() > self.size {
            self.samples.pop();
        }
        if scope_active { p.best_samples_inserted += 1; }
        t.add_to(&mut p.best_samples_insert_dedup_ms);
        true
    }

    pub(crate) fn best(&self) -> Option<ScoredPlacement> {
        self.samples.first().cloned()
    }

    pub(crate) fn upper_bound(&self) -> SampleEval {
        self.samples
            .get(self.size.saturating_sub(1))
            .map(|s| s.eval())
            .unwrap_or(SampleEval::Invalid)
    }
}
