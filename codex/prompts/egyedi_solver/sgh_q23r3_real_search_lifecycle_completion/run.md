# SGH-Q23R3 — Real Sparrow search lifecycle completion

You are working in the VRS_nesting repository.

This is a **hard REVISE-fix implementation task** after Q23R2. Do not perform another audit-only pass. Do not create a benchmark-only task. Do not write a report that explains why the current state is insufficient and then stop.

Your job is to finish the missing production cutover pieces so the fixed-sheet production solver can actually behave like a jagua_rs/Sparrow-style solver in CDE mode.

## Read first

Read these files before coding:

1. `codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion.md`
2. `codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_measurements.md`
3. `codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md`
4. `docs/egyedi_solver/sgh_q23r1_sparrow_reference_delta.md`
5. `docs/egyedi_solver/sgh_q23_sparrow_reference_map.md`
6. `rust/vrs_solver/src/optimizer/sparrow.rs`
7. `rust/vrs_solver/src/optimizer/separator.rs`
8. `rust/vrs_solver/src/optimizer/cde_adapter.rs`
9. `rust/vrs_solver/src/optimizer/collision_severity.rs`
10. `rust/vrs_solver/src/optimizer/search_position.rs`
11. `rust/vrs_solver/src/optimizer/cde_observability.rs`
12. `rust/vrs_solver/src/adapter.rs`
13. `rust/vrs_solver/src/io.rs`
14. `scripts/smoke_sgh_q23r2_real_sparrow_cutover_completion.py`
15. `scripts/bench_sgh_q23r2_real_sparrow_cutover_completion.py`

Also inspect the local Sparrow reference clone:

```text
.cache/sparrow
```

It is gitignored but present locally. Use it as a concrete reference for CDE/tracker/separation/exploration/compression lifecycle. Do not ignore it and do not rely only on previous VRS code names.

## Current known state from Q23R2

Q23R2 is **REVISE**, not PASS.

What Q23R2 did well:

- `CdeCandidateSession` is active.
- single-engine multi-hazard CDE candidate query is implemented.
- CDE engine builds on the medium fixture dropped roughly `7650 -> 198`.
- `cde_pairwise_fallback_queries = 0` on the measured path.
- bbox fallback and LBF fallback are zero in `sparrow_cde` measurements.

Do **not** spend this task re-implementing Q23R2's CDE batch path unless you find a correctness bug.

What still fails and must be fixed in Q23R3:

- medium `medium_10_to_20_items / sparrow_cde / cde` still returns `unsupported`, `0/12`, `sparrow_converged=false`;
- collision pairs only improve `66 -> 15`, not to zero;
- raw loss only improves `1320 -> 300`, not to zero;
- production default remains legacy;
- `SparrowSeparationKernel` still effectively moves one worst target per iteration;
- `SparrowState::refresh()` still rebuilds a full `CollisionGraphSnapshot` from tracker as the normal loop path;
- no production `move_items_multi` / multi-target worker pass is wired into `sparrow_cde`;
- no fixed-sheet exploration / restart / stagnation disruption lifecycle is active;
- no fixed-sheet compression/compaction pass after feasibility;
- LV8 readiness smoke is not done.

## Non-negotiable target

The goal is **not** merely to remove bbox. The goal is to make the production fixed-sheet solver operate according to the jagua_rs/Sparrow method, adapted to fixed rectangular sheets.

Hard interpretation:

- internal infeasible layouts are allowed and expected;
- CDE/exact geometry is the truth source;
- collision graph + GLS weights must drive search;
- search must move multiple colliding/offending items, not only one worst item forever;
- exploration and compression are separate lifecycle phases;
- fixed-sheet objective is part of the search;
- final `ok` output must be backend-valid;
- legacy/PhaseOptimizer/LBF cannot be hidden production fallback in `sparrow_cde`.

BBox may remain only as a safe broad-phase/prereject mechanism where it can prove `NoCollision` or reduce candidate sets. BBox must not be positive collision truth, search loss truth, final validity, or fallback validity.

## Implementation priority order

You must implement in this order unless code reality proves a different dependency order. If you deviate, explain precisely in the report.

1. Wire a real multi-target Sparrow pass into production `sparrow_cde`.
2. Replace the normal per-move full collision graph rebuild with maintained/incremental graph updates.
3. Add fixed-sheet exploration/restart/stagnation-disruption lifecycle.
4. Add fixed-sheet compression/compaction after feasible layouts are found.
5. Make the medium fixture converge `12/12` under `sparrow_cde` without timeout and without fallback.
6. Flip production Phase1 default to `sparrow_cde` only after the medium hard gate passes.
7. Add LV8-derived readiness smoke.

Do not flip the default while the medium fixture is still unsupported. If medium cannot be made to pass in this task, the status must be `REVISE`, and the default must not be falsely flipped to a failing production path. But you still must implement as much of the real lifecycle as possible before reporting REVISE.

## A. Production multi-target / move_items_multi in `sparrow_cde`

The current `sparrow.rs` loop is not enough:

```rust
let Some(target_idx) = state.current_graph.worst_item_index else { ... };
search_position_for_target(... target_idx ...)
```

Replace or substantially extend this with a production multi-target pass.

Requirements:

- derive a deterministic top-K target set from the collision graph:
  - top colliding items by weighted incident loss;
  - top boundary offenders;
  - endpoints from top colliding pairs;
- run multiple deterministic workers / target orders per outer iteration;
- each worker starts from the same master snapshot;
- each worker attempts a sequence of moves, not just one item;
- each accepted worker move must be CDE-confirmed through the active backend/session path;
- choose the best worker by weighted loss, then raw loss, then deterministic tie-breaker;
- commit the best worker only if it improves the master or reaches feasibility;
- rollback must not destroy GLS lifecycle incorrectly;
- GLS weights must survive according to Sparrow-style guided local search logic;
- no LBF fallback in production `sparrow_cde`.

You may reuse/port the existing `VrsSeparator` worker machinery, but do not simply call old separator as a black-box if it preserves legacy behavior, LBF fallback, bbox loss, or non-production defaults. The production `sparrow_cde` kernel must expose its own diagnostics and must stay CDE-first.

Required diagnostics:

- `sparrow_workers`
- `sparrow_worker_passes`
- `sparrow_worker_candidates_evaluated`
- `sparrow_worker_commits`
- `sparrow_worker_rollbacks`
- `sparrow_worker_best_loss`
- `sparrow_multi_target_items_attempted`
- `sparrow_multi_target_items_accepted`
- `sparrow_multi_target_items_rejected`
- `sparrow_topk_target_count`

Required tests:

- multi-target pass attempts more than one target on a synthetic multi-overlap case;
- worker tie-breaking is deterministic for same seed;
- GLS weights survive rollback/commit according to expected policy;
- production `sparrow_cde` does not use LBF fallback.

## B. Maintained / incremental collision graph

The normal loop must stop rebuilding the full graph after every move.

Current pattern to eliminate from the hot path:

```rust
CollisionGraphSnapshot::from_tracker(&self.tracker, &self.layout, 5)
```

Full rebuild is allowed only for:

- initialization;
- explicit debug consistency verification;
- optional periodic assertion, bounded and counted.

Implement maintained graph state that supports moved-target updates:

- update moved item boundary loss;
- update moved item pair losses against relevant same-sheet items;
- remove stale edges involving moved item;
- update total raw loss and weighted loss;
- update per-item weighted incident loss;
- update top-K pairs/items/boundary offenders deterministically;
- preserve pair/edge weights consistently with GLS.

If the existing `VrsCollisionTracker` cannot support this cleanly, extend it or add a `SparrowCollisionGraph` wrapper next to `sparrow.rs`. Do not leave the production loop dependent on full O(n²) graph refresh.

Required diagnostics:

- `sparrow_graph_full_rebuilds`
- `sparrow_graph_incremental_updates`
- `sparrow_graph_edges_recomputed`
- `sparrow_graph_edges_pruned_by_broadphase`
- `sparrow_graph_debug_rebuilds`
- `sparrow_graph_debug_rebuild_mismatches`

Required tests:

- incremental update produces the same loss/top-K graph as a debug full rebuild after a move;
- full rebuild count does not increase on every production iteration;
- edge recomputation count is proportional to affected item neighborhood, not global full rebuild count;
- deterministic top-K ordering under ties.

## C. Fixed-sheet exploration lifecycle

Implement a fixed-sheet analogue of Sparrow exploration. This is not optional and must not be a report-only placeholder.

Exploration must include:

- multiple deterministic restarts;
- alternative initial distributions / sheet assignments;
- at least one non-trivial seed strategy beyond “place everything at sheet 0 bottom-left”;
- stagnation detection;
- disruption when stagnation persists;
- best feasible incumbent;
- best infeasible incumbent;
- denominator accounting for all attempts, including unsupported/timeout.

Seed strategies should be simple but real. Examples:

- distributed grid/jitter seed across available sheets;
- deterministic part-order variation;
- sheet assignment variation;
- collision-cluster spreading seed;
- large-first / small-first alternatives.

Do not hide bad attempts. Every production `sparrow_cde` run must count in the benchmark denominator.

Required diagnostics:

- `sparrow_exploration_restarts`
- `sparrow_exploration_seed_strategies`
- `sparrow_exploration_disruptions`
- `sparrow_exploration_stagnation_events`
- `sparrow_exploration_best_raw_loss`
- `sparrow_exploration_best_weighted_loss`
- `sparrow_exploration_best_feasible_found`
- `sparrow_best_infeasible_raw_loss`

Required tests:

- at least two deterministic seed strategies are actually used under configured restarts;
- stagnation triggers disruption on a fixture that plateaus under single-target movement;
- best infeasible incumbent improves or is preserved correctly;
- same seed/config yields same result ordering and diagnostics.

## D. Fixed-sheet compression / compaction lifecycle

After a feasible layout is found, run a compression/compaction phase adapted to fixed sheets.

Do not treat compression as a cosmetic post-score. It must attempt valid moves while preserving CDE validity.

Compression objective may include:

- reduce right/top spread per sheet;
- reduce used bounding extent;
- improve compactness around lower-left or target region;
- reduce sheet usage where possible later, but Q23R3 may keep sheet count fixed if medium fixture is single/multi-sheet limited.

Hard rules:

- compression may never emit invalid placements as `ok`;
- every accepted compression move must preserve CDE validity;
- if compression finds no improvement, diagnostics must still show it ran;
- compression must not call legacy placement fallback.

Required diagnostics:

- `sparrow_compression_passes`
- `sparrow_compression_candidates_evaluated`
- `sparrow_compression_accepts`
- `sparrow_compression_rejects`
- `sparrow_fixed_sheet_objective_before`
- `sparrow_fixed_sheet_objective_after`
- `sparrow_fixed_sheet_objective_delta`

Required tests:

- compression preserves zero collision pairs and zero boundary violations;
- compression improves or preserves fixed-sheet objective;
- invalid compression candidate is rejected;
- diagnostics are emitted even when no compression improvement is possible.

## E. Medium fixture hard gate

The existing medium gate is the main immediate acceptance target.

The production `sparrow_cde / cde` medium fixture must satisfy all of these:

- status: `ok`
- placed/required: `12/12`
- `sparrow_converged = true`
- final collision pairs: `0`
- final boundary violations: `0`
- final raw loss: `0`
- final weighted loss: `0` or a documented zero-equivalent under weight normalization
- `bbox_fallback_queries = 0`
- `lbf_fallback_used = 0`
- `backend_used = cde_adapter`
- `final_commit_backend_used = cde_adapter` where this field exists
- `cde_pairwise_fallback_queries = 0` on the ordinary hot path
- no timeout
- CDE engine builds remain structurally improved versus Q23 baseline; Q23R2's ~198 total builds is a useful reference, but convergence may increase query count. Do not regress to per-pair engine build behavior.

You may adjust time budget moderately if needed for a real production-quality search lifecycle, but do not hide non-convergence by timeout games. If the medium test only passes under an unrealistic huge time budget, status is `REVISE` and explain the limit.

Reject conditions:

- changing the medium fixture into an easier fixture;
- counting a partial/unsupported medium result as success;
- using PhaseOptimizer/legacy result to satisfy `sparrow_cde` medium acceptance;
- using bbox validity to emit `ok`;
- suppressing diagnostics on failure.

## F. Production default cutover

Only after the medium gate passes, flip the Phase1 production default.

For:

```json
"solver_profile": "jagua_optimizer_phase1_outer_only"
```

missing `optimizer_pipeline` must route to:

```json
"optimizer_pipeline": "sparrow_cde"
```

Legacy remains explicit opt-in only:

```json
"optimizer_pipeline": "legacy_multisheet"
```

or:

```json
"optimizer_pipeline": "phase_optimizer"
```

Update old tests that preserve legacy default. Do not keep `LegacyMultisheet` default only because old assertions expect it.

Required tests:

- missing optimizer_pipeline + Phase1 profile routes to `sparrow_cde`;
- explicit legacy still routes to legacy;
- explicit phase_optimizer still routes to PhaseOptimizer;
- `sparrow_cde` forces CDE backend even if the input requests bbox;
- production default emits full Sparrow diagnostics.

## G. LV8 readiness smoke

If this fixture exists:

```text
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

add a deterministic LV8-derived smoke. This is **not** the full final 276/276 two-sheet acceptance yet.

Requirements:

- load the normalized LV8 fixture;
- build a small deterministic subset, for example:
  - all 12 part types × quantity 1, or
  - 10-20 mixed instances with at least one difficult/large part if present;
- run production `sparrow_cde`;
- no legacy/LBF fallback;
- diagnostics complete;
- result must be honest: `ok`, `partial`, or `unsupported` all count, but no hidden skip if fixture exists;
- if unsupported, include exact blocker and metrics.

This smoke is readiness evidence, not full Q19/LV8 acceptance.

## Required scripts

Create/update:

```text
scripts/smoke_sgh_q23r3_real_search_lifecycle_completion.py
scripts/bench_sgh_q23r3_real_search_lifecycle_completion.py
```

The smoke must exit non-zero if the medium hard gate fails.

The benchmark must write:

```text
codex/reports/egyedi_solver/sgh_q23r3_real_search_lifecycle_measurements.json
codex/reports/egyedi_solver/sgh_q23r3_real_search_lifecycle_measurements.md
```

Benchmark must include at least:

- tiny fixture;
- two_rect_overlap fixture;
- boundary fixture;
- medium_10_to_20_items fixture;
- LV8 subset if fixture exists;
- production `sparrow_cde` as acceptance path;
- optional legacy/phase_optimizer comparison rows clearly marked comparison-only.

Every production `sparrow_cde` row counts in the denominator. Do not count only successes.

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q23r3_real_search_lifecycle_completion.md
codex/reports/egyedi_solver/sgh_q23r3_real_search_lifecycle_completion.verify.log
```

Report top line must be exactly one of:

```text
PASS
```

or

```text
REVISE
```

`PASS` is allowed only if **all** hard gates below are met:

1. medium fixture converges `12/12` under production `sparrow_cde`;
2. final medium collision pairs = 0;
3. final medium boundary violations = 0;
4. final medium raw loss = 0;
5. production Phase1 missing pipeline routes to `sparrow_cde`;
6. no bbox/LBF/legacy fallback in production `sparrow_cde`;
7. CDE batch candidate path remains active and no pairwise hot-path regression occurs;
8. incremental collision graph is active in production loop;
9. multi-target/worker pass is active in production loop;
10. fixed-sheet exploration/restart/disruption is active;
11. fixed-sheet compression pass is active;
12. full diagnostics are emitted on success and failure;
13. smoke and benchmark outputs are written;
14. cargo tests and repo check run, or any environment limitation is documented exactly.

If any gate fails, the report top line must be `REVISE`. Do not call partial progress PASS.

## Verification commands

Run all feasible commands:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q23r3_real_search_lifecycle_completion.py
python3 scripts/bench_sgh_q23r3_real_search_lifecycle_completion.py --quick
./scripts/check.sh
```

If a command cannot run, document exact reason and still run all other targeted checks.

## Output discipline

No false PASS.

No report-only completion.

No default flip while medium still fails.

No benchmark denominator manipulation.

No fixture weakening.

No hidden fallback.

No bbox-as-truth.

No “Q24 should handle it” deferral for the listed hard gates. Q23R3 is the lifecycle cutover task.
