use super::*;

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum SampleEval {
    Clear { loss: f64 },
    Collision { loss: f64 },
    Invalid,
}

impl Eq for SampleEval {}

impl Ord for SampleEval {
    fn cmp(&self, other: &Self) -> Ordering {
        use SampleEval::{Clear, Collision, Invalid};
        match (*self, *other) {
            (Invalid, Invalid) => Ordering::Equal,
            (Invalid, _) => Ordering::Greater,
            (_, Invalid) => Ordering::Less,
            (Collision { .. }, Clear { .. }) => Ordering::Greater,
            (Clear { .. }, Collision { .. }) => Ordering::Less,
            (Collision { loss: a }, Collision { loss: b })
            | (Clear { loss: a }, Clear { loss: b }) => {
                a.partial_cmp(&b).unwrap_or(Ordering::Equal)
            }
        }
    }
}

impl PartialOrd for SampleEval {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

pub(crate) trait SampleEvaluator {
    /// Evaluate a sample-space candidate. `x` and `y` are rect-min coordinates;
    /// output placements remain anchor coordinates at the VRS boundary.
    fn evaluate_sample(
        &mut self,
        x: f64,
        y: f64,
        rot: f64,
        upper_bound: Option<SampleEval>,
        diag: &mut SparrowDiagnostics,
    ) -> Option<ScoredPlacement>;

    fn n_evals(&self) -> usize;
}

/// One scored candidate produced by the search.
#[derive(Clone)]
pub(crate) struct ScoredPlacement {
    pub(crate) score: f64,
    pub(crate) collision_loss: f64,
    pub(crate) is_clear: bool,
    pub(crate) rect_min_x: f64,
    pub(crate) rect_min_y: f64,
    pub(crate) placement: SparrowPlacement,
}

impl ScoredPlacement {
    pub(crate) fn eval(&self) -> SampleEval {
        if self.is_clear {
            SampleEval::Clear { loss: self.score }
        } else {
            SampleEval::Collision {
                loss: self.collision_loss,
            }
        }
    }
}
