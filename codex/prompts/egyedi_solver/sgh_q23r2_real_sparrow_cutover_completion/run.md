# SGH-Q23R2 — Real Sparrow cutover completion

You are working in the VRS_nesting repository.

This is a **REVISE-fix implementation task** after Q23R1. Do not perform another audit-only pass. Implement the remaining production cutover to a real jagua_rs/Sparrow-style fixed-sheet solver.

## Context you must read first

Read these files before coding:

1. `codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_implementation.md`
2. `codex/reports/egyedi_solver/sgh_q23r1_production_sparrow_cutover_measurements.md`
3. `docs/egyedi_solver/sgh_q23r1_sparrow_reference_delta.md`
4. `docs/egyedi_solver/sgh_q23_sparrow_reference_map.md`
5. `rust/vrs_solver/src/optimizer/sparrow.rs`
6. `rust/vrs_solver/src/optimizer/cde_adapter.rs`
7. `rust/vrs_solver/src/optimizer/collision_severity.rs`
8. `rust/vrs_solver/src/optimizer/search_position.rs`
9. `rust/vrs_solver/src/optimizer/separator.rs`
10. `rust/vrs_solver/src/adapter.rs`
11. `rust/vrs_solver/src/io.rs`

Also inspect the local Sparrow reference clone:

```text
.cache/sparrow
```

It is gitignored but present locally. Use it as a reference for CDE/tracker/separator lifecycle. Do not ignore it.

## Problem statement

Q23R1 implemented a solve-scoped CDE cache, but Q23R1 is still `REVISE`:

- production default remains legacy;
- medium `sparrow_cde` fixture is still `unsupported`, `0/12` placed;
- residual collision pairs remain (`66 -> 10`);
- final raw loss remains nonzero (`1320 -> 200`);
- CDE engine builds reduced only from 7650 to 4246, not the hard ≥80% target;
- collision graph is still O(n²) snapshot after each move;
- no true Sparrow `move_items_multi` / multi-target worker pass;
- no fixed-sheet exploration/compression lifecycle.

Your job is to implement the remaining cutover.

## Critical goal

The goal is not merely to remove bbox. The goal is to make the production fixed-sheet solver behave like a jagua_rs/Sparrow solver:

- infeasible layout state is allowed internally;
- collision graph and GLS weights drive the search;
- CDE/exact geometry is the truth source;
- multi-target / multi-worker movement is used;
- exploration and compression are separate lifecycle phases;
- final output is backend-valid;
- fixed sheet objective is part of the search.

BBox may be used only as a safe broad-phase NoCollision prereject. It may not be positive collision truth, search loss truth, final validity, or fallback.

## Implementation requirements

### A. Implement single-engine multi-hazard CDE candidate evaluation

The current hot path still effectively performs many pairwise CDE calls. Implement a CDE-specific candidate evaluator that builds one `CDEngine` per moving candidate with:

- the sheet boundary as `Exterior` hazard;
- all relevant fixed placements on the same sheet as `Hole` hazards;
- moving candidate queried once.

It must return which hazards collided and must apply VRS touching post-policy per collided hazard.

Expected result: candidate evaluation no longer needs N `CDEngine::new(...)` pairwise builds.

Add or update code around:

- `rust/vrs_solver/src/optimizer/cde_adapter.rs`
- `rust/vrs_solver/src/optimizer/collision_backend.rs`
- `rust/vrs_solver/src/optimizer/collision_severity.rs`
- `rust/vrs_solver/src/optimizer/search_position.rs`
- `rust/vrs_solver/src/optimizer/sparrow.rs`

Add diagnostics:

- `cde_batch_candidate_queries`
- `cde_batch_engine_builds`
- `cde_batch_hazards_registered`
- `cde_batch_collisions_returned`
- `cde_pairwise_fallback_queries`
- `cde_probe_batch_queries`
- `cde_probe_pairwise_queries`

### B. Reduce probe cost through the batch path

The severity probe path must not explode into pairwise engine builds. Reuse the batched CDE candidate session where possible.

If exact per-pair probes remain necessary, they must be bounded, counted, and absent from the ordinary medium fixture hot path unless justified.

### C. Replace normal O(n²) collision graph refresh with incremental updates

Implement maintained graph/tracker updates for a moved target:

- update target boundary loss;
- update target pair losses against relevant same-sheet items;
- update total raw/weighted loss;
- update top-K colliding pairs/items with deterministic tie-breaking.

Full rebuild may remain for initialization and debug consistency checks only.

Diagnostics required:

- `sparrow_graph_full_rebuilds`
- `sparrow_graph_incremental_updates`
- `sparrow_graph_edges_recomputed`
- `sparrow_graph_debug_rebuild_mismatches`

### D. Implement real multi-target / move_items_multi pass

The kernel must not just move one worst item per iteration.

Implement a Sparrow-style multi-target pass:

- select top-K colliding items and boundary offenders;
- run multiple deterministic workers/orders per iteration;
- each worker starts from master snapshot;
- each worker tries a sequence of moves;
- select best worker by weighted loss;
- commit best result or rollback;
- GLS weights survive rollback/commit according to Sparrow logic.

Diagnostics required:

- `sparrow_workers`
- `sparrow_worker_passes`
- `sparrow_worker_candidates_evaluated`
- `sparrow_worker_best_loss`
- `sparrow_multi_target_items_attempted`
- `sparrow_multi_target_items_accepted`

### E. Add fixed-sheet exploration/compression lifecycle

Implement fixed-sheet analogues of Sparrow exploration and compression.

Exploration:

- multiple deterministic restarts;
- disruption on stagnation;
- alternative initial distributions / sheet assignments;
- best feasible and best infeasible incumbents.

Compression:

- after feasibility, compact while preserving CDE validity;
- reduce spread/compactness objective on fixed sheets;
- never emit invalid output.

Diagnostics required:

- `sparrow_exploration_restarts`
- `sparrow_exploration_best_raw_loss`
- `sparrow_compression_passes`
- `sparrow_compression_accepts`
- `sparrow_fixed_sheet_objective_before`
- `sparrow_fixed_sheet_objective_after`

### F. Flip production default routing

For `solver_profile = jagua_optimizer_phase1_outer_only`, when `optimizer_pipeline` is absent, the solver must use `sparrow_cde`.

Legacy must be explicit opt-in only:

```json
"optimizer_pipeline": "legacy_multisheet"
```

or:

```json
"optimizer_pipeline": "phase_optimizer"
```

Update tests accordingly. Do not preserve legacy default because old tests expect it.

### G. Make medium fixture a hard PASS

Update the Q23R1 smoke/benchmark into Q23R2 scripts and make medium convergence a hard gate.

The existing medium fixture must pass:

- status `ok`
- placed/required `12/12`
- `sparrow_converged = true`
- final collision pairs `0`
- final boundary violations `0`
- final raw loss `0`
- `bbox_fallback_queries = 0`
- `lbf_fallback_used = 0`
- `backend_used = cde_adapter`
- no timeout
- CDE engine builds meet the Q23R1 hard target (`<=1530`) or a stronger batch metric proves equivalent structural progress.

Do not downgrade this to soft gate.

### H. Add LV8 readiness smoke if fixture exists

If present, use:

```text
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

Create a small deterministic subset smoke that proves production `sparrow_cde` can run on LV8-derived real geometry without legacy fallback and with complete diagnostics.

Full 276/276 LV8 acceptance is not required in Q23R2.

## Required scripts

Create/update:

```text
scripts/smoke_sgh_q23r2_real_sparrow_cutover_completion.py
scripts/bench_sgh_q23r2_real_sparrow_cutover_completion.py
```

Smoke must fail if medium does not converge.

Benchmark must output:

```text
codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_measurements.json
codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_measurements.md
```

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion.md
codex/reports/egyedi_solver/sgh_q23r2_real_sparrow_cutover_completion.verify.log
```

Report top line must be `PASS` or `REVISE`.

`PASS` is allowed only if:

1. medium fixture converges 12/12;
2. production default is `sparrow_cde` for Phase1 profile;
3. no bbox/LBF/legacy fallback in production;
4. batch CDE candidate path is actually wired;
5. incremental graph is active;
6. multi-target pass is active;
7. fixed-sheet exploration/compression is active;
8. tests and measurements are present.

## Verification commands

Run:

```bash
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q23r2_real_sparrow_cutover_completion.py
python3 scripts/bench_sgh_q23r2_real_sparrow_cutover_completion.py --quick
./scripts/check.sh
```

If any command cannot run, document exact reason, but still perform the implementation and run all feasible targeted checks.

## Output discipline

Do not claim PASS if any hard gate fails. Do not hide unsupported/timeout/error runs. Every production `sparrow_cde` run must count in the denominator.
