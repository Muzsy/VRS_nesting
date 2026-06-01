use super::*;

/// Native LBFBuilder equivalent: place instances in descending
/// convex-hull-area/diameter order, using CDE-backed sample search against the
/// already placed fixed-sheet layout. If no clear candidate exists, the
/// least-infeasible candidate is placed honestly and separation resolves it.
pub fn build_native_constructive_seed(problem: &SparrowProblem) -> SparrowLayout {
    LBFBuilder::new(problem).construct()
}

pub struct LBFBuilder<'a> {
    problem: &'a SparrowProblem,
    rng: DeterministicRng,
    started: Instant,
    seed_budget_s: f64,
}

impl<'a> LBFBuilder<'a> {
    pub fn new(problem: &'a SparrowProblem) -> Self {
        Self {
            problem,
            rng: DeterministicRng::new(problem.config.seed ^ 0x4c42_4642),
            started: Instant::now(),
            seed_budget_s: if problem.instances.len() >= 100 {
                (problem.config.time_limit_s * 0.03).clamp(1.0, 3.0)
            } else {
                (problem.config.time_limit_s * 0.20).clamp(2.0, 20.0)
            },
        }
    }

    fn area_desc_order(&self) -> Vec<usize> {
        let mut order: Vec<usize> = (0..self.problem.instances.len()).collect();
        order.sort_by(|&a, &b| {
            let ia = &self.problem.instances[a];
            let ib = &self.problem.instances[b];
            let da = (ia.part.width * ia.part.width + ia.part.height * ia.part.height).sqrt();
            let db = (ib.part.width * ib.part.width + ib.part.height * ib.part.height).sqrt();
            let ka = ia.part.width * ia.part.height * da;
            let kb = ib.part.width * ib.part.height * db;
            kb.partial_cmp(&ka)
                .unwrap_or(Ordering::Equal)
                .then_with(|| ia.instance_id.cmp(&ib.instance_id))
        });
        order
    }

    pub fn construct(mut self) -> SparrowLayout {
        let order = self.area_desc_order();
        let mut layout = SparrowLayout {
            placements: Vec::with_capacity(self.problem.instances.len()),
        };
        for instance_idx in order {
            let placement = self.search_placement(&layout, instance_idx);
            if let Some(p) = placement {
                layout.placements.push(p);
            }
        }
        layout.placements.sort_by_key(|p| p.instance_idx);
        layout
    }

    fn search_placement(
        &mut self,
        layout: &SparrowLayout,
        instance_idx: usize,
    ) -> Option<SparrowPlacement> {
        let inst = &self.problem.instances[instance_idx];
        let sheets = &self.problem.container.sheets;
        let mut best = BestSamples::new(8, inst.part.width.min(inst.part.height).max(1.0) * 0.10);
        let rotations = if inst.allowed_rotations_deg.is_empty() {
            vec![fitting_rotation(inst, sheets)]
        } else {
            inst.allowed_rotations_deg.clone()
        };
        for sheet_idx in 0..sheets.len() {
            if self.started.elapsed().as_secs_f64() >= self.seed_budget_s {
                break;
            }
            let sheet = &sheets[sheet_idx];
            let Some(sheet_shape) = prepare_shape_from_sheet(sheet).ok().map(Rc::new) else {
                continue;
            };
            let others: Vec<(usize, Rc<CdePreparedShape>)> = layout
                .placements
                .iter()
                .enumerate()
                .filter(|(_, p)| p.sheet_index == sheet_idx)
                .filter_map(|(idx, p)| {
                    let other = &self.problem.instances[p.instance_idx];
                    prepare_shape_native(&other.part, p.x, p.y, p.rotation_deg)
                        .ok()
                        .map(Rc::new)
                        .map(|s| (idx, s))
                })
                .collect();
            let Some(session) = CdeCandidateSession::build(others, &sheet_shape) else {
                continue;
            };
            let evaluator = LBFEvaluator {
                inst,
                sheet,
                sheet_idx,
                session: &session,
            };
            let sampler = UniformBBoxSampler::new(sheet, inst);
            for &rot in &rotations {
                if self.started.elapsed().as_secs_f64() >= self.seed_budget_s {
                    break;
                }
                for (rmx, rmy) in sampler.samples_for(rot, 1, &mut self.rng) {
                    if self.started.elapsed().as_secs_f64() >= self.seed_budget_s {
                        break;
                    }
                    if let Some(scored) = evaluator.score_lbf_candidate(rmx, rmy, rot) {
                        best.report(scored);
                    }
                }
            }
        }
        best.best().map(|s| s.placement)
    }
}
