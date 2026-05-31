# Checklist — SGH-Q24R2 Native Sparrow core port implementation

## Code-first gates

- [ ] Meaningful Rust changes are in `rust/vrs_solver/src/optimizer/sparrow.rs` or new `optimizer/sparrow/*` modules.
- [ ] The task did not only modify `cde_adapter.rs`, `cde_observability.rs`, reports, or benchmark scripts.
- [ ] `.cache/sparrow` was inspected and mapped to VRS implementation files.
- [ ] Top-level VRS Sparrow optimizer orchestration exists: initial solution → exploration → compression → final validation.
- [ ] Separator has strike/no-improvement loop and incumbent rollback.
- [ ] GLS weights survive rollback correctly.
- [ ] `move_items_multi` uses worker-master snapshot semantics.
- [ ] Worker `move_items` processes all currently colliding items in worker-specific order.
- [ ] Worker commits only moves that improve weighted loss according to the evaluator.
- [ ] Search placement uses container-wide sampling.
- [ ] Search placement uses focused/local sampling.
- [ ] Search placement keeps BestSamples/top samples.
- [ ] Search placement performs pre-refinement coordinate descent.
- [ ] Search placement performs final/finer coordinate descent.
- [ ] Exploration phase maintains bounded infeasible pool.
- [ ] Exploration phase inserts local-best infeasible solutions into the pool.
- [ ] Exploration phase restores from the pool with bias toward lower loss.
- [ ] Exploration phase applies real large-item disruption.
- [ ] Compression phase saves incumbent, applies pressure, calls separator, accepts/rejects, and rolls back on failure.
- [ ] The old grid-spread restart is no longer the whole exploration phase.
- [ ] The old 1mm left/down nudge is no longer the whole compression phase.
- [ ] Tracker/layout save-restore consistency is implemented or debug-asserted.
- [ ] CDE/active-set work is supportive, not the main deliverable.
- [ ] Minimal compile/unit/smoke evidence is present.

## Automatic REVISE checks

- [ ] Report top line is `REVISE` if exploration pool is still partial/not done.
- [ ] Report top line is `REVISE` if compression rewrite is still partial/not done.
- [ ] Report top line is `REVISE` if worker move_items remains top-K only.
- [ ] Report top line is `REVISE` if the run mainly produced LV8 timeout benchmark rows without lifecycle code.
