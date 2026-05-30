# SGH-Q24 — Sparrow parity quality hardening

You are working in the VRS_nesting repository.

This is the next implementation task after Q23R3. Q23R3 is accepted as the first real production `sparrow_cde` cutover milestone, but the solver is not yet code-level equivalent to original jagua_rs/Sparrow in search quality.

Your job is to harden the remaining parity gaps.

Do not perform an audit-only pass. Do not create a benchmark-only task. Do not produce a report explaining future work and stop. Implement the code changes, tests, smoke/benchmark scripts, and reports.

## Read first

Read these VRS files before coding:

1. `codex/reports/egyedi_solver/sgh_q23r3_real_search_lifecycle_completion.md`
2. `codex/reports/egyedi_solver/sgh_q23r3_real_search_lifecycle_measurements.md`
3. `docs/egyedi_solver/sgh_q23r1_sparrow_reference_delta.md`
4. `docs/egyedi_solver/sgh_q23_sparrow_reference_map.md`
5. `rust/vrs_solver/src/optimizer/sparrow.rs`
6. `rust/vrs_solver/src/optimizer/search_position.rs`
7. `rust/vrs_solver/src/optimizer/collision_severity.rs`
8. `rust/vrs_solver/src/optimizer/loss_model.rs`
9. `rust/vrs_solver/src/optimizer/separator.rs`
10. `rust/vrs_solver/src/optimizer/cde_adapter.rs`
11. `rust/vrs_solver/src/adapter.rs`
12. `rust/vrs_solver/src/io.rs`
13. `scripts/smoke_sgh_q23r3_real_search_lifecycle_completion.py`
14. `scripts/bench_sgh_q23r3_real_search_lifecycle_completion.py`
15. `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`

Also inspect the local original Sparrow reference clone:

```text
.cache/sparrow
```

It is gitignored but present locally. Do not ignore it. Specifically compare against:

- optimizer lifecycle;
- separator / move_items_multi;
- sample/search;
- quantify/tracker;
- exploration/compression phases.

## Current state from Q23R3

Accepted Q23R3 baseline:

- `sparrow_cde` is Phase1 default when `optimizer_pipeline` is missing.
- `sparrow_cde` forces CDE backend.
- Medium fixture passes `12/12`, pairs `66 -> 0`, raw loss `1320 -> 0`.
- LV8 subset readiness passes only a tiny `3/3` subset.
- Multi-target worker pass exists.
- Incremental graph exists.
- Minimal exploration/restart/disruption exists.
- Minimal compression exists.
- BBox/LBF/legacy fallback is zero in measured production rows.

Known remaining gaps versus original Sparrow:

1. production `search_position` is too weak;
2. exploration is not a true pool/restart/disruption lifecycle;
3. compression is still primitive local compaction;
4. production loss still carries `BboxArea` / extent-proxy legacy;
5. real LV8 evidence is far too small.

## Non-negotiable objective

This task must move the solver from “Sparrow-style MVP” toward “Sparrow-quality fixed-sheet solver”.

The goal is not only to keep medium passing. The goal is to increase the actual search power and prove it on stronger LV8-derived workloads.

BBox may remain only as safe broad-phase/prereject. It must not be production collision truth, production search loss truth, final validity, or fallback validity.

## Required implementation A — Production search-position strength uplift

Find where `run_sparrow_pipeline` or its config sets the production `SearchPositionConfig`.

Q23R3 still used near-disabled production search settings. That is not acceptable for Sparrow parity.

Implement profile/config aware deterministic search budgets:

- smoke/tiny budget;
- medium budget;
- LV8 subset budget;
- optional quality budget.

Production `sparrow_cde` must use non-trivial search:

- `global_grid_n > 1`;
- `focused_sample_count > 0`;
- `coord_descent_max_steps > 0`;
- `coord_descent_top_k > 1`;
- rotation refinement where the rotation policy allows it.

Do not blindly set huge budgets that make tests unusable. Make the budget deterministic and measurable.

Add diagnostics that reach solver output:

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

Hard requirement: medium and LV8 hard-gate rows must prove non-trivial search activity. All-zero/disabled values are not PASS.

## Required implementation B — Exploration pool and deterministic disruption

Replace the minimal one-restart behavior with a stronger fixed-sheet adaptation of Sparrow exploration.

Implement at least:

- bounded infeasible solution pool;
- best feasible incumbent;
- best infeasible incumbent;
- pool insertion for local optima / failed separation attempts;
- deterministic selection from pool by raw loss, weighted loss, collision count, and compactness;
- deterministic disruption operators:
  - large-item swap or relocate;
  - sheet redistribution attempt;
  - clustered collision split / spread;
- repeated restart/restore attempts within a deterministic budget.

Add diagnostics:

- `sparrow_exploration_pool_size`
- `sparrow_exploration_pool_inserts`
- `sparrow_exploration_pool_restores`
- `sparrow_exploration_disruption_large_item_swaps`
- `sparrow_exploration_disruption_sheet_redistributions`
- `sparrow_exploration_disruption_cluster_splits`
- `sparrow_exploration_restore_attempts`
- `sparrow_exploration_restart_budget`
- `sparrow_exploration_restart_used`

Hard requirement: do not fake these as static zero fields. If a run converges before using the pool, diagnostics may show zero usage, but at least one dedicated smoke fixture must exercise pool/restore/disruption.

## Required implementation C — Fixed-sheet compression rewrite

Q23R3 compression is only a minimal local compaction. Replace or extend it with an actual fixed-sheet compression lifecycle.

Implement:

1. restore feasible incumbent;
2. propose compacted/shrunk objective target;
3. perturb/move one or more items toward compactness;
4. call separation to restore feasibility;
5. accept if CDE-valid and objective improves;
6. rollback otherwise;
7. repeat with deterministic budget.

Include multiple deterministic proposal types:

- left/down compaction;
- right/top extent reduction;
- centroid/cluster compaction;
- occupied bounding extent shrink;
- sheet-local compaction where applicable.

Add diagnostics:

- `sparrow_compression_outer_iterations`
- `sparrow_compression_proposals`
- `sparrow_compression_separation_calls`
- `sparrow_compression_accepts`
- `sparrow_compression_rollbacks`
- `sparrow_compression_objective_before`
- `sparrow_compression_objective_after`
- `sparrow_compression_best_delta`
- `sparrow_compression_invalid_rejects`

Hard requirement: compression must preserve CDE final validity. It must not emit invalid placements as `ok`.

## Required implementation D — Shape-aware / CDE-aware production loss

Production `sparrow_cde` must not use `LossModelKind::BboxArea` as the primary search loss.

Implement a production loss model such as:

```rust
LossModelKind::CdeSeparation
```

or:

```rust
LossModelKind::ShapeAwareCde
```

The exact name can differ, but the behavior must satisfy:

- CDE collision truth is mandatory;
- pair loss uses CDE/separation signal as primary value;
- boundary loss is geometry-aware where possible;
- bbox may only prereject, not define primary loss;
- selected loss model appears in diagnostics.

Add diagnostics:

- `loss_model_used`
- `loss_cde_separation_queries`
- `loss_bbox_proxy_queries`
- `loss_bbox_proxy_used_as_primary`
- `loss_shape_aware_pairs`
- `loss_boundary_shape_aware_queries`

Hard requirement for production `sparrow_cde`:

```text
loss_model_used != bbox_area
loss_bbox_proxy_used_as_primary == false
```

If a proxy path is unavoidable for a specific unsupported case, count it and make that run non-PASS unless it is a non-production benchmark-only row.

## Required implementation E — LV8 benchmark ladder

Use:

```text
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

Create deterministic subset generators:

1. `lv8_12types_x1`: one instance from each part type;
2. `lv8_24_instances`: deterministic quantity-aware 24-instance subset;
3. `lv8_50_instances`: benchmark row;
4. `lv8_100_instances`: benchmark row if runtime budget allows;
5. `lv8_full_276`: optional measured row, not hard gate in Q24.

Use consistent assumptions and write them into the report:

- sheet count and sheet size;
- gap/margin;
- rotation policy;
- seed;
- time budget;
- backend and pipeline.

Hard PASS gates:

- existing medium fixture remains `ok`, `12/12`;
- `lv8_12types_x1` is `ok`, `12/12`;
- `lv8_24_instances` is `ok`, `24/24`;
- all hard rows have final pairs `0`, boundary violations `0`, CDE backend, no fallback.

Benchmark-only rows:

- `lv8_50_instances`;
- `lv8_100_instances`;
- `lv8_full_276`.

These larger rows may be partial/unsupported in Q24, but they must be measured or explicitly accounted with a reason. Do not cherry-pick successful rows.

## Required smoke/benchmark scripts

Create:

```text
scripts/smoke_sgh_q24_sparrow_parity_quality_hardening.py
scripts/bench_sgh_q24_sparrow_parity_quality_hardening.py
```

The smoke script must hard-fail on:

- medium regression;
- LV8 12-types-x1 failure;
- LV8 24-instance failure;
- production `sparrow_cde` bbox/LBF/legacy fallback;
- `loss_model_used == bbox_area` in production rows;
- search budgets effectively disabled;
- missing exploration/compression diagnostics.

The benchmark script must write:

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

The report first line must be exactly:

```text
PASS
```

or:

```text
REVISE
```

A PASS is allowed only if all hard gates execute and pass.

## Verification commands

Run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24_sparrow_parity_quality_hardening.py
python3 scripts/bench_sgh_q24_sparrow_parity_quality_hardening.py --quick
./scripts/check.sh
```

If any command cannot run, document exact reason. Do not claim PASS if a hard smoke/benchmark gate did not execute.

## Expected evidence matrix

The final report must include a DoD evidence matrix with rows for:

- production search budget uplift;
- search diagnostics;
- exploration pool/disruption;
- compression lifecycle;
- production loss model;
- medium 12/12;
- LV8 12-types-x1;
- LV8 24-instance;
- larger LV8 denominator;
- no fallback;
- CDE backend;
- smoke/bench/check commands.

## Explicit REVISE conditions

Return `REVISE` if any of these occur:

- report-only or benchmark-only work;
- production search remains effectively disabled;
- medium hard gate regresses;
- LV8 12-types-x1 fails;
- LV8 24-instance fails;
- `sparrow_cde` still uses bbox-area as primary production loss;
- exploration remains one restart without pool/disruption;
- compression remains a single local left/down step without restore/separate/rollback lifecycle;
- fallback to bbox/LBF/legacy occurs in production `sparrow_cde`;
- larger LV8 rows are silently skipped;
- PASS is claimed without executed smoke/bench gates.
