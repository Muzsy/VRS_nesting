use super::*;

// Coordinate Descent refinement — faithful port of upstream
// `.cache/sparrow/src/sample/coord_descent.rs` (ask/tell state machine).

/// Coordinate-descent step multiplier on success (upstream `CD_STEP_SUCCESS`).
const CD_STEP_SUCCESS: f64 = 1.1;
/// Coordinate-descent step multiplier on failure (upstream `CD_STEP_FAIL`).
const CD_STEP_FAIL: f64 = 0.5;

/// Per-stage step configuration (upstream `CDConfig`).
#[derive(Clone, Copy)]
pub(crate) struct CDConfig {
    /// Initial translation step.
    pub t_step_init: f64,
    /// Translation step limit, below which no more candidates are generated.
    pub t_step_limit: f64,
    /// Initial rotation-wiggle step (degrees).
    pub r_step_init: f64,
    /// Rotation-wiggle step limit (degrees).
    pub r_step_limit: f64,
    /// Whether the rotation-wiggle axis is enabled (continuous rotation only).
    pub wiggle: bool,
}

impl CDConfig {
    /// Upstream `prerefine_cd_config` / `final_refine_cd_config`, parameterised by
    /// the item's minimum bbox dimension and the configured wiggle step.
    fn for_stage(item_min_dim: f64, final_stage: bool, wiggle: bool, rotation_wiggle_deg: f64) -> Self {
        let r_init = rotation_wiggle_deg.max(0.5);
        if final_stage {
            // Upstream SND_REFINE: (0.01, 0.001) of min dim; rotation (0.5°, 0.05°).
            CDConfig {
                t_step_init: item_min_dim * 0.01,
                t_step_limit: item_min_dim * 0.001,
                r_step_init: r_init * 0.1,
                r_step_limit: 0.05,
                wiggle,
            }
        } else {
            // Upstream PRE_REFINE: (0.25, 0.02) of min dim; rotation (5°, 1°).
            CDConfig {
                t_step_init: item_min_dim * 0.25,
                t_step_limit: item_min_dim * 0.02,
                r_step_init: r_init,
                r_step_limit: 1.0,
                wiggle,
            }
        }
    }
}

#[derive(Clone, Copy)]
enum CDAxis {
    Horizontal,
    Vertical,
    ForwardDiag,
    BackwardDiag,
    Wiggle,
}

impl CDAxis {
    fn random(rng: &mut DeterministicRng, rotate: bool) -> Self {
        let n = if rotate { 6 } else { 4 };
        match (rng.next_u64() as usize) % n {
            0 => CDAxis::Horizontal,
            1 => CDAxis::Vertical,
            2 => CDAxis::ForwardDiag,
            3 => CDAxis::BackwardDiag,
            _ => CDAxis::Wiggle,
        }
    }
}

/// Refine a starting sample into a local minimum via upstream-style coordinate
/// descent: ask for two candidates either side of the current position along the
/// active axis, accept the best if not worse, scale the active axis' step up on
/// success / down on failure, and reselect a random axis on any non-improvement.
/// Stops when both translation steps and the rotation step fall below their
/// limits. The translation/rotation deltas are passed to the evaluator in the
/// same (anchor + delta) convention the rest of the search uses.
#[allow(clippy::too_many_arguments)]
pub(crate) fn refine_coord_desc(
    init: ScoredPlacement,
    evaluator: &mut impl SampleEvaluator,
    item_min_dim: f64,
    cfg: &SparrowConfig,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    final_stage: bool,
    wiggle: bool,
    rotation_wiggle_deg: f64,
) -> Option<ScoredPlacement> {
    let cd_config = CDConfig::for_stage(item_min_dim.max(1.0), final_stage, wiggle, rotation_wiggle_deg);
    let mut cd = CoordinateDescent {
        cur: init,
        axis: CDAxis::random(rng, cd_config.wiggle),
        t_steps: (cd_config.t_step_init, cd_config.t_step_init),
        t_step_limit: cd_config.t_step_limit,
        r_step: cd_config.r_step_init,
        r_step_limit: cd_config.r_step_limit,
        wiggle: cd_config.wiggle,
    };

    // Safety cap mirroring upstream's <1000-eval guard; the natural stop is the
    // step-limit condition in `ask`. Scales gently with the configured budget.
    let max_rounds = (cfg.coord_descent_steps.max(1) * 20).clamp(40, 500);
    let mut rounds = 0usize;

    while let Some(cands) = cd.ask() {
        rounds += 1;
        if rounds > max_rounds {
            break;
        }
        // Evaluate the (up to) two candidates against the current eval as upper bound.
        let upper = Some(cd.cur.eval());
        let mut best: Option<ScoredPlacement> = None;
        for &(x, y, rot, is_wiggle) in &cands {
            diag.search_coord_descent_steps += 1;
            if is_wiggle {
                diag.search_rotation_wiggle += 1;
            }
            if let Some(c) = evaluator.evaluate_sample(x, y, rot, upper, diag) {
                best = match best {
                    None => Some(c),
                    Some(b) if c.eval() < b.eval() => Some(c),
                    other => other,
                };
            }
        }
        cd.tell(best, rng, diag);
    }
    Some(cd.cur)
}

struct CoordinateDescent {
    cur: ScoredPlacement,
    axis: CDAxis,
    t_steps: (f64, f64),
    t_step_limit: f64,
    r_step: f64,
    r_step_limit: f64,
    wiggle: bool,
}

impl CoordinateDescent {
    /// Generate the two candidates either side of the current position along the
    /// active axis, or `None` once all steps have reached their limits. Each
    /// candidate is `(x, y, rotation_deg, is_wiggle)`.
    fn ask(&self) -> Option<[(f64, f64, f64, bool); 2]> {
        let (sx, sy) = self.t_steps;
        let sr = self.r_step;
        if sx < self.t_step_limit && sy < self.t_step_limit && (sr < self.r_step_limit || !self.wiggle) {
            return None;
        }
        let tx = self.cur.placement.x;
        let ty = self.cur.placement.y;
        let r = self.cur.placement.rotation_deg;
        let c = match self.axis {
            CDAxis::Horizontal => [(tx + sx, ty, r, false), (tx - sx, ty, r, false)],
            CDAxis::Vertical => [(tx, ty + sy, r, false), (tx, ty - sy, r, false)],
            CDAxis::ForwardDiag => [(tx + sx, ty + sy, r, false), (tx - sx, ty - sy, r, false)],
            CDAxis::BackwardDiag => [(tx - sx, ty + sy, r, false), (tx + sx, ty - sy, r, false)],
            CDAxis::Wiggle => [(tx, ty, r + sr, true), (tx, ty, r - sr, true)],
        };
        Some(c)
    }

    /// Update state with the best candidate (upstream `tell`): accept if not
    /// worse; scale the active axis' step by `CD_STEP_SUCCESS` on improvement or
    /// `CD_STEP_FAIL` otherwise; reselect a random axis on any non-improvement.
    fn tell(
        &mut self,
        best: Option<ScoredPlacement>,
        rng: &mut DeterministicRng,
        _diag: &mut SparrowDiagnostics,
    ) {
        let (better, worse) = match &best {
            Some(c) => {
                let ord = c.eval().cmp(&self.cur.eval());
                (ord == Ordering::Less, ord == Ordering::Greater)
            }
            // No valid candidate (both out of bounds / dominated): treat as worse.
            None => (false, true),
        };

        if !worse {
            if let Some(c) = best {
                self.cur = c;
            }
        }

        let m = if better { CD_STEP_SUCCESS } else { CD_STEP_FAIL };
        match self.axis {
            CDAxis::Horizontal => self.t_steps.0 *= m,
            CDAxis::Vertical => self.t_steps.1 *= m,
            CDAxis::ForwardDiag | CDAxis::BackwardDiag => {
                self.t_steps.0 *= m.sqrt();
                self.t_steps.1 *= m.sqrt();
            }
            CDAxis::Wiggle => self.r_step *= m,
        }

        if !better {
            self.axis = CDAxis::random(rng, self.wiggle);
        }
    }
}
