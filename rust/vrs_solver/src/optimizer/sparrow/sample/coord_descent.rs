use super::*;

// Coordinate Descent refinement module mapped from upstream sample/coord_descent.rs.
pub(crate) fn refine_coord_desc(
    init: ScoredPlacement,
    evaluator: &mut impl SampleEvaluator,
    cfg: &SparrowConfig,
    rng: &mut DeterministicRng,
    diag: &mut SparrowDiagnostics,
    final_stage: bool,
    wiggle: bool,
    rotation_wiggle_deg: f64,
) -> Option<ScoredPlacement> {
    let mut cur = init;
    let mut step = if final_stage { 0.05 } else { 0.15 } * evaluator_step_span(&cur).max(1.0);
    let limit = step * 0.10;
    // Nonzero rotation-wiggle step (degrees); shrinks alongside the translation step.
    let mut rotation_step = if wiggle { rotation_wiggle_deg.max(0.5) } else { 0.0 };
    let rotation_limit = 0.25_f64;
    let mut rounds = 0usize;
    while (step >= limit || (wiggle && rotation_step >= rotation_limit))
        && rounds < cfg.coord_descent_steps.max(1)
    {
        rounds += 1;
        // Translation axes (horizontal / vertical / diagonals) plus, for free
        // rotation, a ± rotation-wiggle axis with a genuinely nonzero delta.
        let mut axes: Vec<(f64, f64, f64)> = vec![
            (step, 0.0, 0.0),
            (-step, 0.0, 0.0),
            (0.0, step, 0.0),
            (0.0, -step, 0.0),
            (step, step, 0.0),
            (-step, step, 0.0),
        ];
        if wiggle && rotation_step >= rotation_limit {
            axes.push((0.0, 0.0, rotation_step));
            axes.push((0.0, 0.0, -rotation_step));
        }
        let mut improved = false;
        let mut rotation_improved = false;
        let start = (rng.next_u64() as usize) % axes.len();
        for k in 0..axes.len() {
            let (dx, dy, dr) = axes[(start + k) % axes.len()];
            diag.search_coord_descent_steps += 1;
            if dr != 0.0 {
                diag.search_rotation_wiggle += 1;
            }
            if let Some(c) = evaluator.evaluate_sample(
                cur.placement.x + dx,
                cur.placement.y + dy,
                cur.placement.rotation_deg + dr,
                Some(cur.eval()),
                diag,
            ) {
                if c.eval() <= cur.eval() {
                    let was_rotation = dr != 0.0;
                    cur = c;
                    diag.search_refined_samples += 1;
                    improved = true;
                    if was_rotation {
                        rotation_improved = true;
                    }
                }
            }
        }
        if !improved {
            step *= 0.5;
            rotation_step *= 0.5;
        } else if wiggle && !rotation_improved {
            // Translation improved but rotation did not: shrink the wiggle axis.
            rotation_step *= 0.75;
        }
    }
    Some(cur)
}

fn evaluator_step_span(c: &ScoredPlacement) -> f64 {
    (c.placement.x.abs() + c.placement.y.abs()).sqrt().max(10.0)
}

