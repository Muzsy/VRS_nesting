# SparrowGH → VRS jagua_optimizer migration plan

Plan date: 2026-05-24. Based on audit in `docs/egyedi_solver/sparrow_sparrowgh_code_audit.md`.

---

## Decision

```
Do not use SparrowGH as external benchmark backend.
Use Sparrow/SparrowGH as audited algorithmic source.
Port or reimplement selected algorithms inside VRS jagua_optimizer.
```

The VRS exact validator (`vrs_nesting/nesting/instances.py`, `validate_multi_sheet_output()`) is the only acceptance gate for any produced layout. Temporary infeasible/colliding working states are allowed inside the search loop, but no accepted output may reach the validator unless `find_violations()` returns empty and exact validation passes.

---

## Target architecture

The migrated VRS optimizer will extend the existing `rust/vrs_solver/src/optimizer/` module tree with a separator-driven search loop:

```
Initializer (FFD, largest-first)
  └─→ WorkingLayout (placed + infeasible/colliding items)
        └─→ Separator (GLS weighted loss, multi-pass, rollback)
              └─→ SheetElimination / BinReduction (select weakest sheet, redistribute, separate)
                    └─→ MoveOperators (transfer, swap, reinsert)
                          └─→ SolutionPool + Perturbation
                                └─→ ExactValidationGate (final accepted output only)
```

At every save/commit step, the layout must pass `find_violations() == []` before being emitted as solver output.

---

## VRS module mapping

| VRS module | Current state | Sparrow analog | Migration action |
|---|---|---|---|
| `optimizer/initializer.rs` | `build_initial_layout()` — FFD, bbox-based, largest-first | `BpLbfBuilder::construct()` Pass 1+3 | Add LBF scoring (SGH-03) |
| `optimizer/state.rs` | `LayoutState { placed, unplaced }` — valid only | `Layout` (jagua-rs, can be infeasible) | Extend with working infeasible state (SGH-01) |
| `optimizer/repair.rs` | `find_violations()` + reinsert — valid-placement repair only | Not a separator | Replace/augment with real GLS separator (SGH-02) |
| `optimizer/sheet_elimination.rs` | `SheetEliminationEngine` — select weakest sheet, reinsert, rollback | `bin_reduction_phase()` / `BpLbfBuilder` fallback | Integrate separator into elimination (SGH-04) |
| `optimizer/moves.rs` | `CandidateMove` enum — skeleton only | `try_transfer()`, `try_swap()`, `resolve_by_transfers()` | Implement move execution (SGH-05) |
| `optimizer/stopping.rs` | `StoppingPolicy { max_iterations, time_limit_s }` | Terminator trait | Extend with perturbation/SA awareness (SGH-06) |
| `optimizer/score.rs` | `ObjectiveBreakdown` — `score_layout()`, `sheet_cost_total`, `usable_area_utilization` | Not present (BPP uses bin count as objective) | Retain; integrate as search objective and acceptance criterion |
| `optimizer/candidates.rs` | `generate_candidates_with_sheets()` | LBF candidate generation | Extend for LBF scoring (SGH-03) |
| `optimizer/boundary.rs` | `rect_within_boundary()` | Container boundary check | Retain as-is |
| `optimizer/multisheet.rs` | `MultiSheetManager`, `compute_sheet_count_used()` | `BPProblem` layout management | Retain; integrate with working layout |

---

## State model changes

**Current:** `LayoutState { placed: Vec<PlacedItem>, unplaced: Vec<UnplacedItem> }` — only valid placements.

**Problem:** A GLS separator must temporarily move items to colliding positions to explore the search space. `repair.rs` avoids infeasible states entirely (reinsert only to valid candidate positions).

**Plan (SGH-01):**

Add a `WorkingLayout` concept (separate from `LayoutState`):
```rust
struct WorkingLayout {
    placed: Vec<PlacedItem>,     // may be colliding
    unplaced: Vec<UnplacedItem>,
    bboxes: Vec<PlacedBbox>,     // cached for collision queries
}
```

Or extend `LayoutState` with an `infeasible_zone: Vec<PlacedItem>` field, cleared before any save/commit.

**Invariant:** `LayoutState` (accepted snapshot) always satisfies `find_violations() == []`. `WorkingLayout` may violate this during search. The boundary between them is the commit gate.

---

## Separator migration plan

**Target (SGH-02):** A `VrsSeparator` that mirrors `BinSeparator` using VRS bbox geometry instead of jagua-rs NFP.

Key design decisions:
- **Loss quantification:** Use bbox overlap area (intersection area) as collision loss. Two bboxes on the same sheet with `PlacedBbox::overlaps()` → loss = intersection area. Container violation loss = area outside sheet boundary.
- **CollisionTracker equivalent:** `VrsCollisionTracker { pair_loss: Vec<Vec<f32>>, container_loss: Vec<f32>, weights: Vec<Vec<f32>> }` — O(n²) pair matrix. For Phase 1 item counts (≤300) this is acceptable.
- **GLS weight update:** Algorithm 8 from arXiv:2509.13329: for each pair, if no collision: weight *= `GLS_WEIGHT_DECAY`; if collision: weight *= proportional factor based on `loss / max_loss`.
- **Search:** For each colliding item: generate `generate_candidates_with_sheets()` candidates, score each by weighted collision loss at that position (moving item there virtually), pick best. Use existing `rect_within_boundary()`.
- **Multi-worker:** Phase 1: single-threaded (n ≤ 300 items, fast bbox ops). Parallel workers (rayon) may be added in SGH-06 if needed.
- **Rollback:** Snapshot = `WorkingLayout::clone()`. `restore_but_keep_weights()` pattern: restore positions, keep GLS weights.
- **Strike loop:** Same structure as `BinSeparator::separate()` — outer strike loop, inner no-improvement counter.

**Acceptance gate:** After separator returns, run `find_violations()`. Only accept (commit to `LayoutState`) if empty.

---

## Initial construction migration plan

**Current:** `build_initial_layout()` — FFD, largest-first, first valid candidate position. No LBF scoring.

**Target (SGH-03):** Add LBF (Lower-Left / Bottom-Left Fit) scoring to the initial placement pass:

- For each item in FFD order, score each candidate position by a lower-left heuristic (minimize `candidate.x + candidate.y` weighted by distance from origin, or use existing `generate_candidates_with_sheets()` order which already generates bottom-left-first candidates).
- Add separator fallback: if no collision-free position found in existing sheets, try placing in most-available sheet and run `VrsSeparator`. On separator success: commit. On fail: open new sheet.
- Keep Pass 3 (open new sheet) as final fallback.

**Migration path:** The current `generate_candidates_with_sheets()` already returns candidates in a useful order (sheet origins + placed bbox corners). SGH-03 adds: (1) LBF scoring among candidates, (2) separator fallback in most-available sheet.

---

## Sheet elimination migration plan

**Current:** `SheetEliminationEngine` — select weakest sheet (area → count → index), remove items, reinsert on non-target sheets using valid candidate positions, commit if violations empty + sheet_count reduced.

**Gap vs BPP bin reduction:** No LBF scoring in redistribution, no separator after redistribution, no multi-round attempts, no perturbation/pool.

**Target (SGH-04):** Integrate `VrsSeparator` into sheet elimination:

1. Select target sheet (current logic is adequate — keep it).
2. Remove items from target sheet. Sort displaced largest-first.
3. Redistribute: for each displaced item, try LBF placement on non-target sheets (like `try_lbf_into_any_bin`). Fallback: origin seed in most-available sheet.
4. **Run `VrsSeparator` on each sheet that received items.** Accept only if separator returns zero loss.
5. Commit gate: `find_violations() == []` + `sheet_count_used` decreased.
6. On fail: rollback to original snapshot.
7. Track failed sheets (QW-3 analog); after `MAX_FAILURES`: stop.

This brings VRS sheet elimination to parity with BPP bin reduction Phase 2, minus solution pool (added in SGH-06).

---

## Move operators migration plan

**Current:** `CandidateMove { Place, Move, Reinsert, Rotate }` — data skeleton, no execution.

**Target (SGH-05):** Implement execution for:

- **`try_transfer(from_sheet, to_sheet, item_idx)`:** Remove item from `from_sheet`, attempt LBF placement on `to_sheet`, run `VrsSeparator(to_sheet)`, check `find_violations()`. Return feasibility. Rollback on fail.
- **`try_swap(sheet_a, item_a, sheet_b, item_b)`:** Cross-place both items, separate both sheets. Return `feas_a && feas_b`. Rollback on fail.
- **`resolve_by_transfers(infeasible_sheets, all_sheets, budget)`:** Outer loop over infeasible sheets, inner over items, try transfer to each other sheet. Budget-limited. On success: check if source sheet is now feasible/empty.

All operators must leave `LayoutState` in an exact-valid state after commit, or restore to the pre-operator snapshot.

---

## Solution pool / perturbation plan

**Target (SGH-06):**

- **Pool:** After each successful sheet elimination, store `LayoutState` snapshot. Pool size: `POOL_MAX=5`. On new reduction: reset pool to `[incumbent]`.
- **Perturbation:** After `PERTURB_AFTER_FAILURES=1` consecutive failed reduction attempts, with probability `PERTURB_PROB=0.7`, restore from a random pool member and call `perturb_swap_between_sheets()` (two sheets, swap large items, separate both).
- **Last-resort:** If all candidate sheets have been tried (failed_sheets == all remaining), run up to `MAX_LAST_RESORT_PERTURBS=8` perturbations from pool before giving up.
- **Early exit:** After `MAX_CONSECUTIVE_FAILURES=15` consecutive failures: stop reduction loop.

**Stopping policy:** Extend `StoppingPolicy` with perturbation counters. The existing `time_limit_s` already handles time-budget termination.

---

## Scoring and exact validation integration

**Current:** `score.rs` → `ObjectiveBreakdown { sheet_cost_total, usable_area_utilization }` drives `MultiSheetManager` decisions (JG-19). `score_layout()` is called during construction and repair.

**Integration plan:**
- During separator search: use `sheet_cost_total` (or raw `sheet_count_used`) as primary objective for incumbent selection. `usable_area_utilization` as tiebreaker.
- At every commit gate: `find_violations(placements, parts, sheets) == []` required before updating `LayoutState`.
- Solver output: `validate_multi_sheet_output()` called by Python runner. VRS must emit only valid placements.
- No relaxation: the exact validator is the only correctness arbiter. If `find_violations()` is empty but exact validator fails (e.g., polygon containment issue), that is a geometry bridge bug and must be fixed, not bypassed.

---

## Irregular/remnant handling

Current VRS supports irregular sheet shapes (JG-18, `outer_points` in `Stock`) and remnant cost model (JG-19, `cost_per_use`). Phase 1 item shapes are rectangular (bbox-based collision).

**For separator/search loop:** Bbox-based collision detection is sufficient for rectangular items. Irregular sheet boundary check uses `rect_within_boundary()` (already jagua-rs backed for irregular sheets). No change needed for Phase 1.

**For Phase 2 irregular items:** When irregular item shapes are added, the collision quantification in `VrsCollisionTracker` must be upgraded from bbox-overlap to NFP/polygon overlap. This is planned but out of scope for SGH-01–SGH-07.

---

## Rotation policy handling

VRS Phase 1 supports 0/90/180/270° rotations (integer). `dims_for_rotation()` and `normalize_allowed_rotations()` handle these.

Sparrow supports continuous rotation — not adopted in this migration. `allowed_rotations_deg` policy is unchanged. SGH-08 may add continuous rotation support for irregular item shapes if needed.

---

## Test and benchmark strategy

Each SGH task must pass:

1. **Unit tests:** Add or extend tests in the relevant `*.rs` module. All existing `cargo test` (currently 97/97) must continue to pass.
2. **Smoke test:** For each new component, a Python smoke script (like `smoke_jagua_remnant_score_model_v1.py`) that exercises the new behavior and asserts `validation_status=pass`.
3. **Benchmark gate:** After SGH-04 (sheet elimination with separator), run `bench_jagua_optimizer_phase1_rectangular.py` and `bench_jagua_optimizer_phase2_irregular.py` as regression benchmarks. Sheet count must not increase; density must not decrease by >5% vs pre-SGH baseline.
4. **Exact validation:** Every benchmark case must produce `validation_status=pass`. Any validation fail is a blocker.

---

## Rollback strategy

All search operators follow snapshot/restore:

- Before any destructive operation (item removal, transfer, swap), call `LayoutState::clone()` to create a snapshot.
- On failure (violations detected, separator failed, all candidates exhausted), restore from snapshot.
- Never emit a `LayoutState` with violations to the Python runner.
- `SheetEliminationEngine::run()` already implements this pattern — reuse and extend it.

**Risk:** `WorkingLayout` (infeasible working state) must never be accidentally saved as `LayoutState`. Enforce via type system: make `WorkingLayout` and `LayoutState` distinct types with no implicit conversion; commitment requires passing through a `validate_and_commit()` function that calls `find_violations()`.

---

## Proposed SGH task chain

| Task | Goal | Input dependency | Primary output | Acceptance gate |
|---|---|---|---|---|
| SGH-01 | Working layout / infeasible search state scaffold | SGH-00 PASS | `WorkingLayout` type + tests | `cargo test` pass; type system enforces commit gate |
| SGH-02 | Per-sheet VRS separator V1 | SGH-01 PASS | `VrsSeparator` + `VrsCollisionTracker` | Separator reduces violations to 0 on test fixture; `find_violations() == []` on commit |
| SGH-03 | LBF + separator fallback construction | SGH-02 PASS | Extended `build_initial_layout()` with LBF + sep fallback | Phase 1 benchmark: sheet count ≤ baseline; all placements `validation_status=pass` |
| SGH-04 | Sheet elimination with separator integration | SGH-02 PASS | Extended `SheetEliminationEngine` calling `VrsSeparator` | Phase 1+2 benchmarks: sheet count ≤ pre-SGH; exact validator PASS |
| SGH-05 | Transfer/swap/reinsert move operators | SGH-02 PASS | `moves.rs` execution logic | Move operators reduce infeasibility or return false; `find_violations() == []` on commit |
| SGH-06 | Solution pool + perturbation + stagnation handling | SGH-04+05 PASS | Extended stopping + pool + `perturb_swap_between_sheets()` | Quality benchmark: sheet count improvements vs baseline; no regressions |
| SGH-07 | VRS quality benchmark suite + exact validator gate | SGH-06 PASS | Benchmark matrix + CI gate | All benchmark cases `validation_status=pass`; sheet count ≤ lower bound + buffer |
| SGH-08 | Irregular/remnant hardening on migrated search loop | SGH-07 PASS | Phase 2 irregular items in separator scope | Phase 2 benchmark: all cases `validation_status=pass`; no regressions vs JG-20 baseline |

---

## Acceptance gates

Final acceptance for each SGH task (non-negotiable):

1. `cargo test` — all tests pass (currently 97/97; count may grow).
2. `find_violations(placements, parts, sheets) == []` — zero violations for every committed layout.
3. `validate_multi_sheet_output()` — Python exact validator PASS for every benchmark case.
4. No regression: Phase 1 rectangular benchmark sheet counts and density not worse than JG-20 baseline.
5. No production code change beyond the task scope (scope safety per `NO_PRODUCTION_CODE_CHANGE`).
