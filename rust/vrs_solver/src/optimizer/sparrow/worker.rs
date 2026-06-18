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

    let colliding = ordered_colliding_items_for_worker(&tracker, cfg, worker_idx, &mut rng);

    // Build one CDE session per pass for the primary sheet (the sheet of the first
    // colliding target). Each target is deregistered before search and reregistered
    // after accept/reject, so the session stays consistent across the whole pass.
    let primary_sheet_idx = colliding
        .first()
        .map(|&t| layout.placements[t].sheet_index)
        .unwrap_or(0);
    let all_on_primary: Vec<(usize, Rc<CdePreparedShape>)> = (0..layout.placements.len())
        .filter(|&j| layout.placements[j].sheet_index == primary_sheet_idx)
        .filter_map(|j| tracker.shapes[j].clone().map(|s| (j, s)))
        .collect();
    let initial_session_size = all_on_primary.len();
    // SGH-Q36: when spacing is active, the worker's live part-part session is built on
    // spacing-expanded item shapes WITHOUT the sheet Exterior (boundary stays on original
    // geometry via the bbox-fit gate). Expanded touching is allowed. Off ⇒ original path.
    let mut live_session: Option<CdeCandidateSession> = tracker
        .sheet_shapes
        .get(primary_sheet_idx)
        .and_then(|s| s.clone())
        .and_then(|ss| {
            if tracker.spacing_applied {
                CdeCandidateSession::build_pairs_only(
                    all_on_primary,
                    &ss,
                    crate::optimizer::sparrow::quantify::tracker::pair_touching_policy(true),
                )
            } else {
                CdeCandidateSession::build_all_items(
                    all_on_primary,
                    &ss,
                    crate::optimizer::cde_adapter::CdeTouchingPolicy::SparrowStrict,
                )
            }
        });

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
        // Pass the live session only when the target is on the primary sheet.
        let use_session =
            live_session.is_some() && layout.placements[target].sheet_index == primary_sheet_idx;
        let Some(newp) = native_search_placement(
            target,
            &layout,
            instances,
            &tracker,
            sheets,
            cfg,
            &mut rng,
            started,
            deadline,
            diag,
            if use_session {
                live_session.as_mut()
            } else {
                None
            },
        ) else {
            // No placement found; session was deregistered — restore it.
            if use_session {
                if let Some(ref mut s) = live_session {
                    if let Some(shape) = tracker.shapes[target].clone() {
                        s.reregister_item(target, shape);
                    }
                }
            }
            rejected += 1;
            continue;
        };
        evaluated += diag.search_position_calls - calls_before;
        let old_p = layout.placements[target].clone();
        let snap = tracker.snapshot();
        layout.placements[target] = newp;
        tracker.update_after_move(
            target,
            &layout,
            instances,
            sheets,
            diag,
            if use_session {
                live_session.as_mut()
            } else {
                None
            },
        );
        let new_w = tracker.weighted_loss_for_item(target);
        if new_w <= old_w + 1e-9 {
            // Accepted: tracker.shapes[target] now holds the new shape.
            if use_session {
                if let Some(ref mut s) = live_session {
                    if let Some(shape) = tracker.shapes[target].clone() {
                        s.reregister_item(target, shape);
                    }
                }
            }
            accepted += 1;
        } else {
            layout.placements[target] = old_p;
            tracker.restore_keep_weights(snap);
            // Rejected: restore_keep_weights reset shapes[target] to the old shape.
            if use_session {
                if let Some(ref mut s) = live_session {
                    if let Some(shape) = tracker.shapes[target].clone() {
                        s.reregister_item(target, shape);
                    }
                }
            }
            rejected += 1;
        }
    }

    debug_assert!(
        live_session
            .as_ref()
            .map_or(true, |s| s.hazard_count() == initial_session_size),
        "session hazard_count mismatch after pass: got {} expected {}",
        live_session.as_ref().map_or(0, |s| s.hazard_count()),
        initial_session_size,
    );

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

pub(super) fn ordered_colliding_items_for_worker(
    tracker: &SparrowCollisionTracker,
    cfg: &SparrowConfig,
    worker_idx: usize,
    rng: &mut DeterministicRng,
) -> Vec<usize> {
    let mut colliding = tracker.colliding_indices();
    match cfg.profile {
        SparrowProfile::SparrowStrictParity | SparrowProfile::SparrowDenseLargeScale => {
            rng.shuffle(&mut colliding);
        }
        _ => {
            if worker_idx.checked_rem(2) == Some(1) {
                rng.shuffle(&mut colliding);
            } else if worker_idx >= 2 {
                colliding = colliding.into_iter().rev().collect();
            }
        }
    }
    colliding
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
