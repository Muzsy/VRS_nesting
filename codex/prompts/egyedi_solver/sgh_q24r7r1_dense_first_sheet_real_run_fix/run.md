# SGH-Q24R7-R1 — Dense first-sheet real-run fix

You are working in the VRS_nesting repository.

This is a **repair task** for Q24R7. Do not start a new Q24R8 direction. Do not add compression. Do not reintroduce the old VRS solver core.

## The problem to fix

Q24R7 made useful sampler/evaluator changes, but the dense LV8 first-sheet 191-instance probe was not a real solve. The current native `SparrowOptimizer::solve` contains a production shortcut similar to:

```rust
if instances.len() >= 100 && sheets.len() == 1 {
    diag.initial_raw_loss = BIG_UNSUPPORTED_LOSS;
    diag.collision_graph_final_pairs = 1;
    diag.converged = false;
    return SparrowSolveResult { feasible: false, ... };
}
```

This means the first-sheet probe was reported as a guarded partial with `0.0s` runtime and marker diagnostics. That is not a valid dense-search proof.

## Controlling objective

Make the 191-instance LV8 first-sheet probe run a real, bounded native Sparrow CDE lifecycle:

```text
SparrowProblem
-> SparrowOptimizer::solve
-> build_native_constructive_seed
-> SparrowCollisionTracker::build
-> exploration/separation loop
-> move_items_multi / worker competition
-> native_search_placement / CandidateEvaluator
-> CDE final validation
-> honest SolverOutput diagnostics
```

The result may still be `partial`, but it must be a **real partial after search**, not an early return.

## Forbidden regressions

Do not reintroduce any of these into production `sparrow_cde`:

```text
WorkingLayout
VrsCollisionTracker
SparrowSeparationKernel
search_position_for_target(&WorkingLayout, ...)
build_constructive_seed_layout(...)
PhaseOptimizer
MultiSheetManager
legacy fallback
LBF fallback
bbox truth
compression
crate::io::Placement as internal native layout state
```

`crate::io::Placement` remains allowed only at the final output projection boundary.

## Mandatory reading before coding

Read:

```text
codex/reports/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md
codex/reports/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.verify.log
scripts/smoke_sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.py
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

Optional but recommended for algorithmic tuning:

```text
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/eval/sep_evaluator.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/quantify/tracker.rs
```

If `.cache/sparrow` is missing, run:

```bash
./scripts/ensure_sparrow.sh
```

Do not use `.cache/sparrow/src/optimizer/compress.rs` as an implementation target; compression remains out of scope.

## Hard target 1 — Remove the production dense shortcut

Remove or quarantine outside production the large single-sheet early return.

Rejectable patterns include:

```rust
if instances.len() >= 100 && sheets.len() == 1 { return SparrowSolveResult ... }
if large_single_sheet { return partial_seed_layout ... }
diag.collision_graph_final_pairs = 1; // marker instead of real final validation
```

A bounded solve may still stop due to `time_limit_s`, but only inside the real exploration/separation lifecycle after search work has occurred.

## Hard target 2 — Preserve runtime safety without skipping search

The previous guard probably existed to avoid timeouts. Replace it with bounded large-instance behavior, not a skip.

Acceptable strategies:

- scale budgets deterministically for `instance_count >= 100`, but keep non-trivial worker/search activity;
- cap per-target candidate pool size while still evaluating all relevant sheets/rotations fairly;
- use time-budget checks inside `separate`, `move_items_multi`, and candidate generation;
- preserve best infeasible state and final CDE validation when the deadline is hit;
- surface `partial_reason = time_budget_exhausted | unresolved_collisions | boundary_violations | no_candidate`.

Do not reduce dense search to `global_grid_n=1`, `focused_samples=1`, `coord_descent_steps=1` if that effectively avoids meaningful search.

## Hard target 3 — Honest dense diagnostics

The output must distinguish three things:

```text
attempted instances / seed placements
valid placements after CDE final validation
unresolved/colliding/boundary-blocked instances
```

If the existing schema cannot represent this clearly, extend diagnostics backward-compatibly with optional fields. Suggested fields:

```rust
sparrow_large_single_sheet_guard_used: Option<bool>      // must be false
sparrow_dense_real_run: Option<bool>                    // true for 191 probe
sparrow_dense_partial_reason: Option<String>
sparrow_dense_validated_placements: Option<usize>
sparrow_dense_unresolved_instances: Option<Vec<String>> // or compact string/list field if schema constraints require
sparrow_dense_final_validation_ran: Option<bool>
```

Use naming consistent with the repo style. The exact names may differ, but the smoke/report must be able to prove:

- no dense shortcut;
- real search activity;
- real CDE final validation;
- honest blocker list if partial.

## Hard target 4 — Correct LV8 first-sheet reference probe

Use the same exact Q24R7 first-sheet vector from `tests/fixtures/nesting_engine/ne2_input_lv8jav.json`:

```text
LV8_01170_10db      10
LV8_02048_20db       7
LV8_02049_50db      50
Lv8_07919_16db      13
Lv8_07920_50db      12
Lv8_07921_50db      33
Lv8_15435_10db      10
Lv8_11612_6db        3
Lv8_15348_6db        4
Lv8_10059_10db      10
LV8_00035_28db      28
LV8_00057_20db      11
TOTAL              191
```

Primary probe:

```text
stock sheets = 1
required = 191
optimizer_pipeline = sparrow_cde
collision_backend = cde
compression = disabled / zero
```

## Acceptance / reject rules

`PASS` requires:

- native architecture preserved;
- dense shortcut removed from production;
- medium CDE gate passes;
- LV8 12 types x1 gate passes;
- LV8 191 first-sheet probe actually runs search/separation;
- dense runtime is real and bounded, not `0.0s` marker return;
- diagnostics show non-zero search calls, candidate samples, worker candidates, and CDE queries;
- no bbox/LBF/legacy/compression;
- report written with exact metrics.

The 191 fit itself can be `PARTIAL` if not solved yet. In that case the overall task may still PASS only if `RUNTIME_LV8_REFERENCE_SHEET1_REAL_RUN_GATE=PASS` and the report gives concrete blockers.

`REVISE` is mandatory if:

- the dense shortcut still exists in production;
- the 191 probe returns without search activity;
- diagnostics use marker final pairs/boundary instead of real validation;
- `placed=191/191` is presented as success while `status=partial` and final pairs/boundary are non-zero;
- compression or legacy fallback is used.

## Required commands

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r7r1_dense_first_sheet_real_run_fix.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md
```

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q24r7r1_dense_first_sheet_real_run_fix.md
```

Status lines:

```text
SGH-Q24R7R1_STATUS: PASS|REVISE
STATIC_ARCHITECTURE_GATE: PASS|FAIL
STATIC_DENSE_GUARD_GATE: PASS|FAIL
RUNTIME_MEDIUM_CDE_GATE: PASS|FAIL
RUNTIME_LV8_12TYPES_X1_GATE: PASS|FAIL
RUNTIME_LV8_REFERENCE_SHEET1_REAL_RUN_GATE: PASS|FAIL
RUNTIME_LV8_REFERENCE_SHEET1_FIT_GATE: PASS|PARTIAL|FAIL
```

Dense probe table must include:

```text
required
status
valid/solved placements, not just seed placement count
unplaced count
final collision pairs
boundary violations
raw/weighted loss
runtime
iterations
search calls
samples
worker candidates
CDE queries
partial reason
top blocker / unresolved instance ids
compression/fallback counters
```
