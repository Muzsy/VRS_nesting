use super::*;

// ---------------------------------------------------------------------------
// worker competition (Alg 5/10 native port)
// ---------------------------------------------------------------------------

/// A single competing worker's result: its own layout + tracker after a move
/// batch, plus per-worker statistics. The best (lowest weighted loss) candidate
/// is loaded back into the master; the rest are discarded.
pub(super) struct SeparatorWorker {
    pub(super) layout: SparrowLayout,
    pub(super) tracker: SparrowCollisionTracker,
    pub(super) weighted_loss: f64,
    pub(super) raw_loss: f64,
    pub(super) colliding_pair_total: usize,
    pub(super) attempted: usize,
    pub(super) accepted: usize,
    pub(super) rejected: usize,
    pub(super) evaluated: usize,
    pub(super) worker_idx: usize,
}

/// Run one worker pass: clone the master state, move every colliding item once
/// (greedy accept on per-item weighted-loss improvement) using a worker-unique
/// deterministic ordering/seed. Returns the worker candidate state.
#[allow(clippy::too_many_arguments)]
pub(super) fn run_worker_pass(
    worker_idx: usize,
    master: &SparrowState,
    instances: &[SPInstance],
    sheets: &[SheetShape],
    cfg: &SparrowConfig,
    worker_seed: u64,
    started: &Instant,
    deadline: f64,
    diag: &mut SparrowDiagnostics,
) -> SeparatorWorker {
    let mut layout = master.layout.snapshot();
    let mut tracker = master.tracker.clone();
    let mut rng = DeterministicRng::new(worker_seed);

    let mut colliding = tracker.colliding_indices();
    // Worker-unique ordering bias: even workers worst-first (as-ranked), odd
    // workers shuffled — different exploration of the same master state.
    if worker_idx % 2 == 1 {
        rng.shuffle(&mut colliding);
    } else if worker_idx >= 2 {
        // higher even workers: reverse (least-loss first)
        colliding.reverse();
    }

    let mut attempted = 0usize;
    let mut accepted = 0usize;
    let mut rejected = 0usize;
    let mut evaluated = 0usize;

    for target in colliding {
        if started.elapsed().as_secs_f64() >= deadline {
            break;
        }
        if tracker.weighted_loss_for_item(target) <= 1e-12 {
            continue;
        }
        attempted += 1;
        let calls_before = diag.search_position_calls;
        // Upstream acceptance authority: the moved item's weighted collision loss
        // (tracker GLS weights) must not increase. No loose global new_total /
        // new_pairs fallback that could worsen the moved item's local damage.
        let old_w = tracker.weighted_loss_for_item(target);
        let Some(newp) = native_search_placement(
            target, &layout, instances, &tracker, sheets, cfg, &mut rng, diag,
        ) else {
            rejected += 1;
            continue;
        };
        evaluated += diag.search_position_calls - calls_before;
        let old_p = layout.placements[target].clone();
        let snap = tracker.snapshot();
        layout.placements[target] = newp;
        tracker.update_after_move(target, &layout, instances, sheets, diag);
        let new_w = tracker.weighted_loss_for_item(target);
        if new_w <= old_w + 1e-9 {
            accepted += 1;
        } else {
            layout.placements[target] = old_p;
            tracker.restore_keep_weights(snap);
            rejected += 1;
        }
    }

    let weighted_loss = tracker.total_weighted_loss();
    let raw_loss = tracker.total_raw_loss();
    let colliding_pair_total = tracker.colliding_pairs();
    SeparatorWorker {
        layout,
        tracker,
        weighted_loss,
        raw_loss,
        colliding_pair_total,
        attempted,
        accepted,
        rejected,
        evaluated: evaluated.max(1),
        worker_idx,
    }
}

/// Compare worker candidates by upstream weighted loss, then raw loss and pair
/// total only as deterministic tie-breakers.
pub(super) fn compare_worker_candidates<'a>(cands: &'a [SeparatorWorker]) -> &'a SeparatorWorker {
    cands
        .iter()
        .min_by(|a, b| {
            a.weighted_loss
                .partial_cmp(&b.weighted_loss)
                .unwrap_or(std::cmp::Ordering::Equal)
                .then(
                    a.raw_loss
                        .partial_cmp(&b.raw_loss)
                        .unwrap_or(std::cmp::Ordering::Equal),
                )
                .then(usize::cmp(&a.colliding_pair_total, &b.colliding_pair_total))
                .then(a.worker_idx.cmp(&b.worker_idx))
        })
        .expect("at least one worker")
}

/// Load the winning worker's state back into the master, discarding the rest
/// (Sparrow Alg 10 load-back step). The master adopts the best worker's layout
/// and CDE tracker (including its GLS-bumped weights and incremental records).
pub(super) fn load_best_worker(master: &mut SparrowState, best: SeparatorWorker) {
    master.layout = best.layout;
    master.tracker = best.tracker;
}
