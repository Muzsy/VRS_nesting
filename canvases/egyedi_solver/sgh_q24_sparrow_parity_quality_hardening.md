# SGH-Q24 — Sparrow parity quality hardening

## Purpose

Q23R3 completed the first real production `sparrow_cde` cutover milestone. The solver now has infeasible state, CDE-backed evaluation, collision graph, GLS weights, multi-target workers, restart/disruption, compression, CDE final validation and Phase1 default routing.

But it is **not yet equivalent to the original jagua_rs/Sparrow solver** in search quality. Q24 must harden the missing parity pieces.

This task is not another cutover task. It is not a report-only task. It is not an LV8 benchmark-only task. It must implement the next missing Sparrow-quality features and prove them on stronger real fixtures.

## Current accepted baseline

From Q23R3:

- `sparrow_cde` is production Phase1 default when `optimizer_pipeline` is missing.
- Medium fixture passes `12/12`, final pairs `0`, final raw loss `0`.
- LV8 readiness smoke passes only a tiny `3/3` subset.
- Search lifecycle exists, but still simplified.

## Hard problem to fix

The remaining code-level differences versus original Sparrow are:

1. production `search_position` is still too weak;
2. exploration is not a true pool/restart/disruption lifecycle;
3. compression is only simple left/down step compaction;
4. production search loss still carries `BboxArea` / extent-proxy legacy;
5. real LV8 evidence is far too small.

Q24 must address all five. If any are only documented but not implemented, the task is `REVISE`.

## Non-negotiable principles

- The goal is Sparrow-quality behavior, not merely removing bbox.
- BBox may remain only as a safe broad-phase/prereject mechanism.
- CDE/exact geometry remains the source of collision truth.
- Production `sparrow_cde` must not silently fallback to bbox, LBF, legacy multisheet, or PhaseOptimizer.
- If stronger search makes runtime worse, optimize candidate budgets and CDE reuse; do not disable the search and call it PASS.
- Full LV8 276/276 on two sheets is not yet the hard gate in Q24, but Q24 must move materially beyond the Q23R3 3-item LV8 smoke.

## Required implementation

### 1. Production search-position strength uplift

Q23R3 still uses an overly weak production search budget. This must be changed.

Production `sparrow_cde` must use non-trivial deterministic search budgets, for example:

- `global_grid_n > 1`;
- `focused_sample_count > 0`;
- `coord_descent_max_steps > 0`;
- `coord_descent_top_k > 1`;
- rotation refinement enabled where the part rotation policy allows it.

Do not hard-code a huge budget blindly. Implement profile/config aware deterministic budgets:

- tiny/smoke budget;
- medium budget;
- LV8 subset budget;
- optional quality budget.

The production Phase1 default must not remain at the Q23R3 near-disabled settings.

Required diagnostics:

- `search_global_grid_n_effective`
- `search_focused_sample_count_effective`
- `search_coord_descent_steps_effective`
- `search_coord_descent_top_k_effective`
- `search_rotation_refinement_enabled`
- `search_candidates_generated`
- `search_candidates_evaluated`
- `search_coord_descent_attempts`
- `search_coord_descent_accepts`
- `search_focused_samples_used`

Hard gate: on the medium and LV8 subset runs, the diagnostics must prove non-trivial sampling/refinement is active. A PASS with all these effectively zero is invalid.

### 2. Real Sparrow-style exploration pool and disruption

Replace the minimal “one grid-spread restart” behavior with a stronger fixed-sheet adaptation of Sparrow exploration.

Implement:

- best feasible incumbent;
- best infeasible incumbent;
- infeasible solution pool with bounded size;
- deterministic selection from pool using weighted raw loss / collision count / compactness;
- deterministic disruption operators:
  - large-item swap / relocate;
  - sheet redistribution attempt;
  - clustered collision split;
- repeated restart attempts within a fixed deterministic budget;
- restore/retry accounting.

Required diagnostics:

- `sparrow_exploration_pool_size`
- `sparrow_exploration_pool_inserts`
- `sparrow_exploration_pool_restores`
- `sparrow_exploration_disruption_large_item_swaps`
- `sparrow_exploration_disruption_sheet_redistributions`
- `sparrow_exploration_disruption_cluster_splits`
- `sparrow_exploration_restore_attempts`
- `sparrow_exploration_restart_budget`
- `sparrow_exploration_restart_used`

Hard gate: medium and LV8 12-types-x1 must show either direct convergence or meaningful exploration diagnostics. Fake zero-valued fields do not pass.

### 3. Rewrite fixed-sheet compression lifecycle

The Q23R3 compression is too primitive. Replace or extend it with a real fixed-sheet compression loop.

Required lifecycle:

1. start from a feasible incumbent;
2. propose a compacted/shrunk target objective;
3. perturb/move one or more items toward compactness;
4. run separation to restore feasibility;
5. accept if CDE-valid and objective improves;
6. otherwise rollback to incumbent;
7. repeat with a deterministic budget.

Compression must not emit invalid placements.

At minimum, implement multiple deterministic compactness proposals:

- left/down compaction;
- right/top extent reduction;
- centroid/cluster compaction;
- occupied bounding extent shrink;
- optional sheet-local compaction.

Required diagnostics:

- `sparrow_compression_outer_iterations`
- `sparrow_compression_proposals`
- `sparrow_compression_separation_calls`
- `sparrow_compression_accepts`
- `sparrow_compression_rollbacks`
- `sparrow_compression_objective_before`
- `sparrow_compression_objective_after`
- `sparrow_compression_best_delta`
- `sparrow_compression_invalid_rejects`

Hard gate: compression must be active on at least one feasible production run and must preserve final CDE validity.

### 4. Shape-aware / CDE-aware production loss

Production `sparrow_cde` must stop treating `LossModelKind::BboxArea` as the primary search loss.

Implement a production loss model such as:

```text
LossModelKind::CdeSeparation
```

or:

```text
LossModelKind::ShapeAwareCde
```

Requirements:

- CDE collision truth remains mandatory.
- Pair loss must come from CDE/separation signal, not bbox area as the main value.
- Boundary loss must be geometry-aware and not just constant `1.0` where possible.
- BBox may only prereject or provide fallback diagnostics, not primary production loss.
- The selected production loss model must be visible in output diagnostics.

Required diagnostics:

- `loss_model_used`
- `loss_cde_separation_queries`
- `loss_bbox_proxy_queries`
- `loss_bbox_proxy_used_as_primary`
- `loss_shape_aware_pairs`
- `loss_boundary_shape_aware_queries`

Hard gate:

- for production `sparrow_cde`, `loss_bbox_proxy_used_as_primary` must be `false`;
- `loss_model_used` must not be `bbox_area` on production `sparrow_cde` runs;
- any unavoidable proxy path must be counted and explained.

### 5. LV8 benchmark ladder

Q23R3 only proved a 3-item LV8 subset. Q24 must introduce a real LV8 ladder based on:

```text
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

Create deterministic subset generators:

1. `lv8_12types_x1` — one instance from each of the 12 part types;
2. `lv8_24_instances` — deterministic quantity-aware subset with 24 instances;
3. `lv8_50_instances` — benchmark row, not hard PASS unless it already passes;
4. `lv8_100_instances` — benchmark row if runtime budget allows;
5. `lv8_full_276` — optional measured row, not a hard PASS in Q24.

Use consistent sheet assumptions:

- two 1500×3000 sheets where appropriate;
- CDE backend;
- no bbox/LBF/legacy fallback;
- deterministic seed(s);
- explicit gap/margin values in the generated input/report.

Hard PASS gates:

- medium fixture still `12/12 ok`;
- `lv8_12types_x1` must be `12/12 ok`;
- `lv8_24_instances` must be `24/24 ok`;
- all hard-gate rows must have final pairs `0`, boundary violations `0`, CDE backend, no fallback.

Benchmark-only rows:

- `lv8_50_instances`;
- `lv8_100_instances`;
- `lv8_full_276`.

These larger rows must be included in the denominator and reported honestly. They may be `partial`/`unsupported` in Q24, but hiding or skipping them without a clear runtime/config reason is a failure.

## Required scripts

Create/update:

```text
scripts/smoke_sgh_q24_sparrow_parity_quality_hardening.py
scripts/bench_sgh_q24_sparrow_parity_quality_hardening.py
```

Smoke must fail if any hard gate fails.

Benchmark must write:

```text
codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening_measurements.json
codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening_measurements.md
```

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening.md
codex/reports/egyedi_solver/sgh_q24_sparrow_parity_quality_hardening.verify.log
```

The report top line must be exactly one of:

```text
PASS
REVISE
```

A PASS is only allowed if every hard gate is satisfied.

## Required verification

Run at minimum:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24_sparrow_parity_quality_hardening.py
python3 scripts/bench_sgh_q24_sparrow_parity_quality_hardening.py --quick
./scripts/check.sh
```

If a command cannot run, document the exact reason. Do not claim PASS if a required hard gate was not executed.

## Explicit reject conditions

The task is REVISE if any of these happen:

- report-only implementation;
- production search budgets remain effectively disabled;
- medium gate regresses;
- LV8 12-types-x1 or 24-instance hard rows fail;
- production `sparrow_cde` still uses `bbox_area` as primary loss;
- compression remains only a single simple left/down step without separation restore loop;
- exploration remains only one grid-spread restart with no pool/restoration/disruption policy;
- any hidden fallback to LBF/legacy/bbox appears in production `sparrow_cde`;
- larger LV8 benchmark rows are silently omitted;
- PASS is claimed with unexecuted smoke/benchmark gates.
