# SGH-Q04R — Phase Orchestration Correction Notes

## Purpose

Corrective implementation notes for the SGH-Q04R task. The original SGH-Q04 report claimed PASS but the phase/explore/compress modules had six code-level defects (B1–B6) that prevented the contract from being satisfied. This document records the before/after for each blocker.

---

## B1 — PhaseOptimizer stub wiring

**Before:** `PhaseOptimizer::run_exploration()` and `run_compression()` were score-only stubs. They computed `initial_score`, set `best_score = initial_score`, and returned without ever calling `ExplorationPhase` or `CompressionPhase`. `iterations_run` was always 0.

**After:** `run_exploration()` instantiates `ExplorationPhase::new(self.config.clone())` and calls `.run(layout, parts, sheets)`. `run_compression()` does the same for `CompressionPhase`. Both now return `(WorkingLayout, PhaseDiagnostics)` with real iteration counts and pool state.

**Files changed:** `phase.rs` — imports added, signatures changed, bodies replaced.

---

## B2 — InfeasibleSolutionPool best() ordering

**Before:** `best()` called `self.candidates.peek()` on a `BinaryHeap` with ascending `Ord` (lower loss = "less"). Since `BinaryHeap` is a max-heap, `peek()` returned the highest raw_loss candidate — the opposite of the contract. The existing test `infeasible_pool_loss_ordering` also asserted `raw_loss == 5.0` (highest), documenting the bug rather than catching it.

**After:** `best()` iterates the heap and calls `.min_by(|a, b| a.cmp(b))` to find the lowest-loss entry. The ascending `Ord` is retained (it is correct for eviction in `push()`), only `best()` is fixed. The test now asserts `raw_loss == 1.0`.

**Eviction correctness (retained):** `push()` calls `BinaryHeap::pop()` which removes the highest-loss entry (max-heap + ascending Ord = highest loss at top), then keeps it only if the new candidate has lower loss. This correctly retains the N lowest-loss candidates.

**Files changed:** `explore.rs` — `best()` body, test renamed + assertion corrected.

---

## B3 — Fake time budget

**Before:** Both `ExplorationPhase::run()` and `CompressionPhase::run()` computed elapsed time as `(iteration as f64) * 0.01`. This is a fake linear proxy, not real wall-clock time. A `time_limit_s = 60.0` budget would be "exhausted" after 6000 iterations regardless of actual elapsed time.

**After:** Both phases now call `std::time::Instant::now()` before the loop and use `start_time.elapsed().as_secs_f64()` inside the loop check.

**Files changed:** `explore.rs`, `compress.rs`.

---

## B4 — Disruption max_attempts not used

**Before:** `LargeItemSwapDisruption::try_disrupt()` tried exactly one pair (from `deterministic_pair(iteration, &top_items)`) and returned `None` on failure. The `max_attempts` field was unused. The success check `diag.committed > 0` did not verify violation-freedom of the result.

**After:** `try_disrupt()` loops `0..self.max_attempts`. Each attempt uses `iteration.wrapping_add(attempt)` to select a different deterministic pair. A result is accepted only if `find_violations(...).is_empty()`. If no attempt succeeds, returns `None`.

**Files changed:** `explore.rs` — `try_disrupt()` body.

---

## B5 — Compression commit score mismatch

**Before:** `CompressionPhase::run()` computed `new_score` by scoring a manually-rotated clone of `layout.placements`. It then called `try_reinsert()` (which runs the separator and may place the item at a different position). The commit decision and `incumbent_score` update used `new_score.total_cost` (from the clone), not from the actual committed `try_result`.

**After:** The manual clone + pre-scoring step is removed. The code calls `try_reinsert()` first, then checks violations on `try_result`, then scores `try_result` directly. The commit decision compares `try_score.total_cost < incumbent_score`. `diag.best_score` is set to `try_score.total_cost`.

**Files changed:** `compress.rs` — inner loop body.

---

## B6 — Hardcoded rotation list in compression

**Before:** `compress.rs` used `let rotations_to_try = [0i64, 90, 180, 270];` regardless of the part's `allowed_rotations_deg`. This ignores the part's declared rotation support.

**After:** Rotations are looked up per placement: `parts.iter().find(|pt| pt.id == part_id).map(|pt| pt.allowed_rotations_deg.clone()).unwrap_or_default()`. `try_reinsert()` already validates the rotation against `normalize_allowed_rotations`, so this fix ensures the compression loop never proposes a rotation that the part doesn't support.

**Files changed:** `compress.rs` — per-placement rotation lookup.

---

## No-downgrade evidence

- `find_violations` is called on every accepted output in exploration (incumbent update), compression (try_result check), and disruption (new_placements check).
- The incumbent is always initialized from the input layout and only replaced on improvement (score < incumbent_score).
- `compression_scores_actual_try_result_before_commit` test verifies `diag.best_score` matches scoring the actual committed layout.

---

## Determinism

- `PhaseConfig::deterministic_default()` provides a fixed seed.
- `ExplorationPhase` seeds `VrsSeparatorConfig` with `self.config.seed`.
- `LargeItemSwapDisruption` uses `seed + iteration + attempt` for pair selection.
- `same_seed_phase_optimizer_determinism` test verifies bit-identical output for same seed + input.
