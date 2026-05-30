# SGH-Q23R2 — Real Sparrow cutover completion

## Purpose

Complete the production cutover from the legacy/PhaseOptimizer solver to a real jagua_rs/Sparrow-style fixed-sheet solver.

Q23R1 is **not PASS**. It implemented a solve-scoped CDE cache, but the remaining hard blockers are still open:

1. medium CDE fixture does not converge;
2. engine-build reduction is only ~45%, not ≥80%;
3. production default still routes to legacy;
4. collision graph is still rebuilt as an O(n²) snapshot;
5. candidate evaluation still relies on backend-agnostic pairwise CDE calls;
6. no real multi-target/move_items_multi Sparrow loop;
7. no fixed-sheet exploration/compression lifecycle.

This task must implement those blockers, not just document them.

## Non-negotiable direction

The target is not “remove bbox”. The target is a fully functional fixed-sheet adaptation of jagua_rs/Sparrow.

BBox may remain only as broad-phase/prereject where it can prove NoCollision. It must not be the source of positive collision truth, search loss, final validity, or production fallback.

## Required implementation

### 1. CDE single-engine multi-hazard candidate query

Implement a CDE-specific batched query path for evaluating one moving candidate against all fixed hazards on the same sheet.

For each candidate placement:

- build one `CDEngine` with:
  - sheet exterior hazard;
  - all relevant fixed placements on that sheet as `Hole` hazards;
- query the moving item once;
- collect colliding hazard identities;
- apply VRS touching post-policy per returned hazard;
- return:
  - boundary violation status;
  - colliding fixed item ids/indices;
  - pair/boundary loss inputs;
  - unsupported reason if conversion fails.

This must bypass the current N pairwise `CdeCollisionBackend.placement_overlaps()` loop on hot candidate evaluation.

Expected files likely include:

- `rust/vrs_solver/src/optimizer/cde_adapter.rs`
- `rust/vrs_solver/src/optimizer/collision_severity.rs`
- `rust/vrs_solver/src/optimizer/search_position.rs`
- `rust/vrs_solver/src/optimizer/sparrow.rs`

Use `.cache/sparrow` as the reference for how live `CDEngine` + tracker lifecycle is supposed to be used.

### 2. Probe-cost reduction

The collision severity probe path must not repeatedly build a CDE engine per pair/boundary probe when evaluating a candidate.

Route CDE severity probing through the same batched candidate session where possible. If exact per-pair probes are still needed, they must be bounded and measured separately.

Add diagnostics:

- `cde_batch_candidate_queries`
- `cde_batch_engine_builds`
- `cde_batch_hazards_registered`
- `cde_batch_collisions_returned`
- `cde_pairwise_fallback_queries`
- `cde_probe_batch_queries`
- `cde_probe_pairwise_queries`

The acceptance target is not “some cache hits”; it is a structural reduction of engine builds.

### 3. Incremental collision graph

Replace `CollisionGraphSnapshot::from_tracker(...)` as the normal per-move refresh mechanism.

Implement a maintained collision graph / tracker state that updates only affected edges when one placement changes:

- dirty item boundary edge;
- dirty item pair edges against same-sheet neighbors;
- total raw/weighted loss;
- top colliding items/pairs;
- deterministic tie-breaking.

Full O(n²) rebuild may remain only as:

- initialization;
- debug assertion mode;
- periodic optional consistency check.

Add diagnostics:

- `sparrow_graph_full_rebuilds`
- `sparrow_graph_incremental_updates`
- `sparrow_graph_edges_recomputed`
- `sparrow_graph_debug_rebuild_mismatches`

### 4. Real Sparrow multi-target / move_items_multi pass

The current Q22/Q23 kernel effectively moves one worst item per iteration. That is not enough.

Implement a Sparrow-style multi-target pass:

- take top-K colliding items / boundary offenders;
- run multiple deterministic workers/orders per iteration;
- each worker attempts a sequence of moves from a shared snapshot;
- choose best worker result by weighted loss;
- preserve GLS weights correctly across rollback/commit;
- no LBF fallback.

This should mirror the intent of Sparrow Algorithm 5/10, adapted to VRS fixed-sheet state.

Add diagnostics:

- `sparrow_workers`
- `sparrow_worker_passes`
- `sparrow_worker_candidates_evaluated`
- `sparrow_worker_best_loss`
- `sparrow_multi_target_items_attempted`
- `sparrow_multi_target_items_accepted`

### 5. Fixed-sheet exploration/compression lifecycle

Implement an actual fixed-sheet analogue of Sparrow exploration/compression.

Exploration:

- multiple deterministic restarts/seeds;
- disruption when stagnating;
- try alternative initial distributions / sheet assignments;
- keep best feasible and best infeasible incumbents.

Compression:

- once feasible, reduce spread/compactness while preserving feasibility;
- fixed-sheet objective must be part of the search, not a post-hoc score only;
- do not emit invalid placements.

Add diagnostics:

- `sparrow_exploration_restarts`
- `sparrow_exploration_best_raw_loss`
- `sparrow_compression_passes`
- `sparrow_compression_accepts`
- `sparrow_fixed_sheet_objective_before`
- `sparrow_fixed_sheet_objective_after`

### 6. Production default routing

For `solver_profile = jagua_optimizer_phase1_outer_only`, missing `optimizer_pipeline` must route to `sparrow_cde` after this task.

Legacy routes may remain only as explicit opt-in:

```json
"optimizer_pipeline": "legacy_multisheet"
```

or

```json
"optimizer_pipeline": "phase_optimizer"
```

Update tests that currently assert legacy default. Do not keep legacy default only to satisfy old tests.

### 7. Medium fixture must become hard PASS

The existing `medium_10_to_20_items` fixture must converge in production `sparrow_cde`:

- status: `ok`
- placed/required: `12/12`
- `sparrow_converged = true`
- final collision pairs: `0`
- final boundary violations: `0`
- final raw loss: `0`
- `bbox_fallback_queries = 0`
- `lbf_fallback_used = 0`
- `backend_used = cde_adapter`
- no timeout
- `cde_engine_builds <= 1530` or justified stricter/better metric via batch diagnostics

Do not make medium convergence a soft gate.

### 8. LV8 readiness smoke

Do not require full LV8 276/276 in this task, but add a small LV8-derived smoke if the normalized fixture exists:

`tests/fixtures/nesting_engine/ne2_input_lv8jav.json`

Acceptance for this smoke:

- parser loads the fixture;
- a small deterministic subset is built;
- production `sparrow_cde` runs;
- no legacy fallback;
- diagnostics complete;
- result either `ok` or honest `unsupported` with full diagnostics.

Full LV8 2-sheet target remains later.

## Verification commands

Run at minimum:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q23r2_real_sparrow_cutover_completion.py
python3 scripts/bench_sgh_q23r2_real_sparrow_cutover_completion.py --quick
./scripts/check.sh
```

If cargo/check.sh are too slow, still run targeted tests plus both Q23R2 scripts and document the limitation.

## Required report

Write:

- `codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion.md`
- `codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_measurements.json`
- `codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_measurements.md`
- verify log

The top of the report must be one of:

- `PASS`
- `REVISE`

A `PASS` is only allowed if the medium fixture converges and the default route is switched to production `sparrow_cde`.
