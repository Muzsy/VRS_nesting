use super::*;

/// Native LBFBuilder (upstream `optimizer/lbf.rs`) plus a clearly separated
/// fixed-sheet seeding adaptation.
///
/// `construct` is the upstream LBF parity path: it places items in descending
/// convex-hull-area/diameter order via `search_placement` + `LBFEvaluator`, and
/// accepts ONLY a collision-free (`Clear`) placement — exactly upstream
/// `find_placement`. Upstream, an item with no clear placement triggers a strip
/// expansion (`change_strip_width(* 1.2)`); in fixed-sheet multisheet the sheet
/// cannot grow, so such an item is recorded honestly as UNRESOLVED instead of
/// being installed as a colliding "best-bad" placement.
///
/// Items left unresolved by LBF are then handed to
/// [`seed_unresolved_on_fixed_sheets`] — a NAMED fixed-sheet adaptation (NOT LBF
/// parity) that gives each one an in-bounds starting position so the separator
/// (which only moves already-placed items) can resolve it. This keeps every
/// placeable instance in the layout without pretending the infeasible seed was a
/// constructive LBF success.
pub fn build_native_constructive_seed(problem: &SparrowProblem) -> SparrowLayout {
    let built = LBFBuilder::new(problem).construct();
    let mut layout = built.layout;
    if !built.unresolved.is_empty() {
        seed_unresolved_on_fixed_sheets(problem, &mut layout, &built.unresolved);
    }
    layout.placements.sort_by_key(|p| p.instance_idx);
    layout
}

/// Outcome of LBF construction: the clear placements plus the instances for which
/// no collision-free fixed-sheet position was found (honest unresolved set).
pub(crate) struct LBFResult {
    pub(crate) layout: SparrowLayout,
    pub(crate) unresolved: Vec<usize>,
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

    pub(crate) fn construct(mut self) -> LBFResult {
        let order = self.area_desc_order();
        let mut layout = SparrowLayout {
            placements: Vec::with_capacity(self.problem.instances.len()),
        };
        let mut unresolved = Vec::new();
        for instance_idx in order {
            match self.search_placement(&layout, instance_idx) {
                Some(p) => layout.placements.push(p),
                // No clear placement on any sheet (and the fixed sheet cannot be
                // expanded): record honestly as unresolved, do not install a
                // colliding placement as if it were LBF success.
                None => unresolved.push(instance_idx),
            }
        }
        LBFResult { layout, unresolved }
    }

    /// Upstream `find_placement`: search a position for `instance_idx` via the
    /// `LBFEvaluator` across every eligible sheet / rotation, and accept ONLY a
    /// collision-free (`Clear`) result. Returns `None` when no clear placement
    /// exists (the fixed-sheet equivalent of "would need a wider strip").
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
        // Accept ONLY a clear placement (upstream returns `Some` only for `Clear`).
        best.best().filter(|s| s.is_clear).map(|s| s.placement)
    }
}

/// Fixed-sheet seeding adaptation — NOT upstream LBF parity.
///
/// Upstream LBF guarantees every item a clear placement by widening the strip
/// when needed. On fixed sheets that lever does not exist, so the instances LBF
/// left unresolved get a deterministic in-bounds starting position here. These
/// seeds are deliberately allowed to be infeasible (overlapping); the separator
/// resolves them. This is an explicit fixed-sheet adaptation so the layout keeps
/// every placeable instance — it is documented as such and is never reported as
/// an LBF constructive success.
fn seed_unresolved_on_fixed_sheets(
    problem: &SparrowProblem,
    layout: &mut SparrowLayout,
    unresolved: &[usize],
) {
    let sheets = &problem.container.sheets;
    if sheets.is_empty() {
        return;
    }
    let mut rng = DeterministicRng::new(problem.config.seed ^ 0x5EED_F00D_1234_5678);
    for &instance_idx in unresolved {
        let inst = &problem.instances[instance_idx];
        let rot = fitting_rotation(inst, sheets);
        let (rw, rh) = dims_for_rotation(inst.part.width, inst.part.height, rot);
        // First sheet on which the part fits at its fitting rotation.
        let Some((sheet_idx, sheet)) = sheets
            .iter()
            .enumerate()
            .find(|(_, s)| rw <= s.width + 1e-9 && rh <= s.height + 1e-9)
        else {
            continue;
        };
        // Deterministic in-bounds anchor (separator will move it to feasibility).
        let max_rmx = (sheet.max_x - rw).max(sheet.min_x);
        let max_rmy = (sheet.max_y - rh).max(sheet.min_y);
        let rmx = sheet.min_x + rng.next_f64() * (max_rmx - sheet.min_x).max(0.0);
        let rmy = sheet.min_y + rng.next_f64() * (max_rmy - sheet.min_y).max(0.0);
        let (ax, ay) =
            placement_anchor_from_rect_min(rmx, rmy, inst.part.width, inst.part.height, rot);
        layout.placements.push(SparrowPlacement {
            instance_idx,
            sheet_index: sheet_idx,
            x: ax,
            y: ay,
            rotation_deg: rot,
        });
    }
}
