# Checklist - SGH-Q23R3 Real Sparrow search lifecycle completion

## Hard implementation gates

- [x] Report starts with exactly `PASS` or `REVISE`.
- [x] Task is not report-only; Rust code and scripts are changed.
- [x] Q23R2 CDE batch path remains active.
- [x] No regression to pairwise CDE engine builds in the ordinary candidate hot path.
- [x] `sparrow_cde` does not use bbox as positive collision truth.
- [x] `sparrow_cde` does not use bbox as search loss truth.
- [x] `sparrow_cde` does not use bbox as final validity.
- [x] `sparrow_cde` does not fallback to LBF.
- [x] `sparrow_cde` does not fallback to PhaseOptimizer or legacy multisheet.

## Multi-target pass gates

- [x] Production `sparrow_cde` selects top-K colliding/boundary targets, not only one worst item.
- [x] Multiple deterministic workers/orders are attempted per outer iteration.
- [x] Worker result selection is deterministic.
- [x] GLS weights survive rollback/commit according to the intended policy.
- [x] Diagnostics include worker counts, worker passes, candidates evaluated, commits, rollbacks, and accepted/rejected target counts.
- [x] Unit test proves more than one target is attempted on a multi-overlap fixture.

## Incremental graph gates

- [x] Hot path no longer rebuilds full collision graph after every move.
- [x] Incremental update handles moved item boundary and pair edges.
- [x] Incremental update maintains total raw/weighted loss.
- [x] Incremental update maintains deterministic top-K target selection.
- [x] Debug full rebuild consistency test exists.
- [x] Diagnostics include full rebuild count, incremental update count, recomputed edges, debug mismatches.

## Exploration/compression gates

- [x] At least two deterministic seed/restart strategies are implemented.
- [x] Stagnation detection is implemented.
- [x] Disruption is implemented.
- [x] Best feasible and best infeasible incumbents are tracked.
- [x] Compression pass runs after feasible layout.
- [x] Compression accepted moves preserve CDE validity.
- [x] Fixed-sheet objective before/after/delta is diagnosed.

## Medium hard gate

- [x] `medium_10_to_20_items / sparrow_cde / cde` returns `status=ok`.
- [x] Medium placed/required is `12/12`.
- [x] `sparrow_converged = true`.
- [x] Final collision pairs are `0`.
- [x] Final boundary violations are `0`.
- [x] Final raw loss is `0`.
- [x] `bbox_fallback_queries == 0`.
- [x] `lbf_fallback_used == 0`.
- [x] `backend_used == cde_adapter`.
- [x] No timeout.
- [x] Medium fixture was not weakened or replaced.

## Production default gates

- [x] Missing `optimizer_pipeline` with `solver_profile=jagua_optimizer_phase1_outer_only` routes to `sparrow_cde` after medium passes.
- [x] Explicit `legacy_multisheet` still routes to legacy.
- [x] Explicit `phase_optimizer` still routes to PhaseOptimizer.
- [x] `sparrow_cde` forces CDE even if input requests bbox.
- [x] Old tests preserving legacy default are updated, not used to block cutover.

## LV8 readiness gates

- [x] If `tests/fixtures/nesting_engine/ne2_input_lv8jav.json` exists, smoke loads it.
- [x] LV8 subset is deterministic and documented.
- [x] LV8 subset runs production `sparrow_cde`.
- [x] LV8 subset has full diagnostics.
- [x] No hidden skip if fixture exists.

## Required command gates

- [x] `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` executed or exact limitation documented.
- [x] `python3 scripts/smoke_sgh_q23r3_real_search_lifecycle_completion.py` executed.
- [x] `python3 scripts/bench_sgh_q23r3_real_search_lifecycle_completion.py --quick` executed.
- [x] `./scripts/check.sh` executed or exact limitation documented.
- [x] Measurement JSON and MD written.
- [x] Verify log written.

## Automatic REVISE conditions

- [x] Not triggered: medium convergence is not downgraded to soft gate.
- [x] Not triggered: default does not remain legacy after medium passes.
- [x] Not triggered: production path does not silently use legacy/PhaseOptimizer/LBF.
- [x] Not triggered: positive collision truth does not come from bbox.
- [x] Not triggered: invalid placements are not emitted as `ok`.
- [x] Not triggered: benchmark denominator counts all production runs, not only successes.
- [x] Not triggered: LV8 fixture exists and smoke runs it.
- [x] Not triggered: report says PASS only after hard gates passed.
