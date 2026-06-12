use super::*;

/// Native `LBFBuilder` — the upstream constructive builder
/// (`.cache/sparrow/src/optimizer/lbf.rs`), adapted to fixed sheets.
///
/// Items are placed in descending `convex_hull_area × diameter` order (upstream
/// ordering, computed from the actual shape surrogate — not a bbox
/// `width × height × diagonal` approximation). Each item is placed via the shared
/// `search_placement` + `LBFEvaluator`, and ONLY a collision-free (`Clear`)
/// placement is accepted. Upstream widens the strip when no clear placement
/// exists; on fixed sheets the sheet cannot grow, so such an item is recorded
/// honestly as unresolved. The builder never installs a colliding "best-bad"
/// placement and never carries a density-specific seed budget — the separator
/// bootstrap for unresolved items lives outside this builder (see
/// `fixed_sheet::build_native_constructive_seed`).
pub struct LBFBuilder<'a> {
    problem: &'a SparrowProblem,
    rng: DeterministicRng,
    started: Instant,
    deadline_s: f64,
}

/// Uniform fraction of the solve time budget allotted to the constructive seed
/// phase (same for every instance count — not a density-specific shortcut).
const SEED_PHASE_TIME_FRACTION: f64 = 0.4;

/// Outcome of LBF construction: the clear placements plus the instances for which
/// no collision-free fixed-sheet position was found (honest unresolved set).
pub(crate) struct LBFResult {
    pub(crate) layout: SparrowLayout,
    pub(crate) unresolved: Vec<usize>,
}

impl<'a> LBFBuilder<'a> {
    pub fn new(problem: &'a SparrowProblem) -> Self {
        Self {
            problem,
            rng: DeterministicRng::new(problem.config.seed ^ 0x4c42_4642),
            started: Instant::now(),
            // The constructive seed phase gets a bounded, UNIFORM share of the solve
            // budget (mirroring upstream's explore/compress phase split) so the
            // separator/exploration phases always run. This is not density-specific:
            // the same fraction applies for every instance count (no `len() >= 100`
            // branch). On fixed sheets some items may have no clear placement at all
            // (e.g. a perfectly tiling instance), so an unbounded clear-only search
            // could otherwise consume the whole budget fruitlessly.
            deadline_s: (problem.config.time_limit_s * SEED_PHASE_TIME_FRACTION).max(0.05),
        }
    }

    /// Upstream item ordering: descending `convex_hull_area × diameter`, both read
    /// from the shape surrogate (rotation-invariant), with a stable instance-id
    /// tie-break for determinism.
    fn order(&self) -> Vec<usize> {
        let mut keyed: Vec<(usize, f64)> = (0..self.problem.instances.len())
            .map(|i| (i, lbf_order_key(&self.problem.instances[i])))
            .collect();
        keyed.sort_by(|a, b| {
            b.1.partial_cmp(&a.1).unwrap_or(Ordering::Equal).then_with(|| {
                self.problem.instances[a.0]
                    .instance_id
                    .cmp(&self.problem.instances[b.0].instance_id)
            })
        });
        keyed.into_iter().map(|(i, _)| i).collect()
    }

    pub(crate) fn construct(mut self) -> LBFResult {
        let order = self.order();
        let mut layout = SparrowLayout {
            placements: Vec::with_capacity(self.problem.instances.len()),
        };
        let mut unresolved = Vec::new();
        for instance_idx in order {
            match self.find_clear_placement(&layout, instance_idx) {
                Some(p) => layout.placements.push(p),
                // No clear placement on any fixed sheet (cannot widen the strip):
                // record honestly as unresolved rather than install a collision.
                None => unresolved.push(instance_idx),
            }
        }
        LBFResult { layout, unresolved }
    }

    /// Place one item via the shared `search_placement` + `LBFEvaluator` on each
    /// eligible sheet, accepting only a collision-free (`Clear`) result (upstream
    /// `find_placement`). Returns `None` when no clear placement exists.
    fn find_clear_placement(
        &mut self,
        layout: &SparrowLayout,
        instance_idx: usize,
    ) -> Option<SparrowPlacement> {
        let inst = &self.problem.instances[instance_idx];
        let sheets = &self.problem.container.sheets;
        let sample_config = lbf_sample_config();
        let mut diag = SparrowDiagnostics::default();
        let mut best_clear: Option<ScoredPlacement> = None;
        // Q31: use cached base shape from instance — no prepare_base_shape_native call.
        // SGH-Q36: candidate part-part collision uses the spacing-expanded base shape
        // (same Rc as the original when spacing is off). Boundary is the bbox-fit gate
        // on the original dims inside LBFEvaluator.
        let spacing_applied = self.problem.config.spacing_mm > 0.0;
        let base = inst.spacing_collision_base_shape.clone();

        for sheet_idx in 0..sheets.len() {
            if self.started.elapsed().as_secs_f64() >= self.deadline_s {
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
                    // Q31: use cached base shape for already-placed items too.
                    // SGH-Q36: spacing-expanded for part-part collision (same Rc when off).
                    let other = &self.problem.instances[p.instance_idx];
                    transform_base_to_candidate(
                        &other.spacing_collision_base_shape,
                        p.x,
                        p.y,
                        p.rotation_deg,
                    )
                    .map(Rc::new)
                    .map(|s| (idx, s))
                })
                .collect();
            let session = if spacing_applied {
                // Pairs-only (no Exterior): boundary is the bbox-fit gate on original dims.
                CdeCandidateSession::build_pairs_only(
                    others,
                    &sheet_shape,
                    crate::optimizer::sparrow::quantify::tracker::pair_touching_policy(true),
                )
            } else {
                CdeCandidateSession::build_with_policy(
                    others,
                    &sheet_shape,
                    crate::optimizer::cde_adapter::CdeTouchingPolicy::SparrowStrict,
                )
            };
            let Some(session) = session else {
                continue;
            };
            let mut evaluator = LBFEvaluator {
                inst,
                sheet,
                sheet_idx,
                session: &session,
                base: &base,
                n_evals: 0,
            };
            if let Some(scored) = search_placement(
                &mut evaluator,
                inst,
                sheet,
                None,
                sample_config,
                &self.problem.config,
                &mut self.rng,
                &self.started,
                self.deadline_s,
                &mut diag,
            ) {
                // Accept only a clear placement (upstream returns Some only for Clear).
                if scored.is_clear {
                    best_clear = match best_clear {
                        None => Some(scored),
                        Some(b) if scored.eval() < b.eval() => Some(scored),
                        other => other,
                    };
                }
            }
        }
        best_clear.map(|s| s.placement)
    }
}

/// Upstream LBF sample budget: many container-wide samples, no focused sampler,
/// a small set of coordinate descents (mirrors `LBF_SAMPLE_CONFIG`).
fn lbf_sample_config() -> SampleConfig {
    SampleConfig {
        n_focused_samples: SPARROW_PARITY_LBF_FOCUSED_SAMPLES,
        n_container_samples: SPARROW_PARITY_LBF_CONTAINER_SAMPLES,
        n_coord_descents: SPARROW_PARITY_COORD_DESCENTS,
    }
}

/// Upstream ordering key: `convex_hull_area × diameter`, read from the item's
/// shape surrogate (both quantities are rotation-invariant, so a canonical
/// rotation-0 shape is used). Falls back to a bbox estimate only when the
/// canonical transform cannot be produced from the cached base shape.
fn lbf_order_key(inst: &SPInstance) -> f64 {
    // Q31: use cached base shape — no prepare_shape_native call.
    match transform_base_to_candidate(&inst.base_shape, 0.0, 0.0, 0.0) {
        Some(prepared) => {
            let (convex_hull_area, diameter) = convex_hull_area_and_diameter(&prepared);
            convex_hull_area * diameter
        }
        None => {
            let diameter = (inst.part.width.powi(2) + inst.part.height.powi(2)).sqrt();
            (inst.part.width * inst.part.height).max(1.0) * diameter
        }
    }
}
