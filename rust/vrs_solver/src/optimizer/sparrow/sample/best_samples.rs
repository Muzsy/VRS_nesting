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

    pub(crate) fn report(&mut self, cand: ScoredPlacement) -> bool {
        if cand.eval() >= self.upper_bound() {
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
            } else {
                return false;
            }
        }
        self.samples.push(cand);
        self.samples.sort_by(|a, b| a.eval().cmp(&b.eval()));
        if self.samples.len() > self.size {
            self.samples.pop();
        }
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
