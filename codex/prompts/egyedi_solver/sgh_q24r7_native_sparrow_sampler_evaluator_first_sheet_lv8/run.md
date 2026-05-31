# SGH-Q24R7 — Native Sparrow sampler/evaluator + LV8 first-sheet reference

You are working in the VRS_nesting repository.

Q24R5 completed the architectural native-model cutover. Q24R6 hardened native tracker/search/worker behavior. Q24R7 must now close the next concrete jagua_rs/Sparrow gap: the native sampler/evaluator and dense LV8 scaling.

This is a **coding-first algorithmic task**. It is not a compression task and not a new architecture task.

## Controlling objective

Production `sparrow_cde` must remain native:

```text
SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution / SparrowSolveResult
```

Now deepen the native search/evaluator so it resembles the original Sparrow logic more closely:

```text
native sample pool
  -> global/container-wide samples across eligible sheets
  -> focused samples from collision neighborhoods / high-loss items
  -> polygon/CDE-aware sample evaluator
  -> coordinate descent/refinement of top samples
  -> worker competition with stronger deterministic budgets
  -> CDE final validation
```

Compression is excluded. Do not enable it. Do not use it to pass any gate. For our fixed multisheet target, compression is a later last-sheet-only layer after the full solver core is complete.

## Forbidden regression

Do not reintroduce the old VRS core into production `sparrow_cde`:

```text
WorkingLayout
VrsCollisionTracker
SparrowSeparationKernel
search_position_for_target(&WorkingLayout, ...)
build_constructive_seed_layout(...)
PhaseOptimizer
MultiSheetManager
legacy / LBF fallback
crate::io::Placement as internal native layout state
```

The only allowed VRS boundary remains input/output conversion.

## Mandatory reading before coding

Read these current project files:

```text
codex/reports/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening.md
codex/reports/egyedi_solver/sgh_q24r6_native_sparrow_tracker_search_parity_hardening.verify.log
scripts/smoke_sgh_q24r6_native_sparrow_tracker_search_parity_hardening.py
rust/vrs_solver/src/adapter.rs
rust/vrs_solver/src/io.rs
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
rust/vrs_solver/src/optimizer/loss_model.rs
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf
```

Read the local Sparrow reference:

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

Skim `.cache/sparrow/src/optimizer/compress.rs` only to confirm compression is out of scope.

## Hard target 1 — Replace shallow infeasible sample ordering

Q24R6 still allowed AABB-style penetration magnitude to order infeasible candidates. That is not good enough for the next parity step.

Implement or harden a native candidate evaluator analogous to Sparrow's `SepEvaluator`:

- CDE decides collision truth.
- The infeasible magnitude used to rank candidates must be polygon/CDE-aware, not primarily AABB penetration.
- AABB may remain only as broad-phase/pruning, never as authoritative truth and not as the main infeasible ordering score.
- Candidate scoring must be deterministic.
- Search, worker decisions, and diagnostics must use this evaluator consistently.

## Hard target 2 — Multi-container candidate pool, not fallback-only

The search must consider all eligible sheets/containers as part of the candidate pool.

Reject a solution where the current sheet is searched first and other sheets are only tried as a last resort without being fairly evaluated as candidate containers. For multisheet nesting, this leads to bad early commitments.

Expected behavior:

- every eligible sheet gets global/container-wide candidates;
- focused candidates are generated around the current/high-loss/colliding neighborhood;
- all allowed rotations are evaluated;
- coordinate descent/refinement runs on the top candidates;
- best candidate can come from a different sheet even if the current sheet has a feasible but worse candidate.

## Hard target 3 — Stronger worker/search budget

Workers must compete with meaningfully different target orders and candidate choices.

- Worker count and sample budgets must be deterministic and configurable.
- Defaults must be strong enough for the LV8 first-sheet probe.
- Diagnostics must show worker count, candidate evaluations, commits, rollbacks, best loss, global/focused/refined samples, cross-sheet candidates, evaluator calls.

## Hard target 4 — Correct LV8 first-sheet reference probe

Do not use a synthetic `12 types x max 4` subset.

Generate the dense probe from:

```text
tests/fixtures/nesting_engine/ne2_input_lv8jav.json
```

with quantities from **Nesting layout 1 / 2** of:

```text
samples/real_work_dxf/0014-01H/lv8jav/Nested/project_2447207_report.pdf
```

Exact quantity vector:

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

Mapping notes:

- Report `LV8_00057-2_20db REV8` -> fixture id `LV8_00057_20db`.
- Report `Lv8 _10059_10db REV2` -> fixture id `Lv8_10059_10db`.
- The report sheet is `3000 x 1500`; fixture sheet is equivalent orientation `1500 x 3000`.
- The report used 5 mm gap and all rotations; fixture currently contains solver-ready geometry and allowed rotation lists. Do not silently pretend these are identical. Preserve fixture semantics unless you implement a documented conversion.

Primary first-sheet probe should use **one stock sheet**. Report exact result honestly:

```text
required = 191
placed = ?
unplaced = ?
final pairs = ?
boundary = ?
runtime = ?
no fallback/compression = ?
```

If 191/191 is not achieved, do not fake PASS for that result. Record exact blockers and next algorithmic gap.

## Acceptance / reject rules

PASS requires at minimum:

- native architecture preserved;
- sampler/evaluator materially improved in Rust code;
- AABB is not the main infeasible sample evaluator/orderer;
- multi-container candidate pool is not fallback-only;
- medium CDE gate passes;
- LV8 12 types x1 regression passes;
- LV8 reference sheet-1 191-instance probe is generated and run honestly with CDE, no bbox truth, no LBF, no legacy, no compression;
- full report and verify log written.

If the first-sheet probe is partial, mark the first-sheet runtime gate as `PARTIAL`, not fake `PASS`, unless 191/191 is actually placed with zero final pairs/boundary. The overall task can only be `PASS` with a partial first-sheet result if the sampler/evaluator implementation is materially complete and the report explains the remaining blocker precisely. Otherwise mark `REVISE`.

## Required commands

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.py
./scripts/check.sh
```

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q24r7_native_sparrow_sampler_evaluator_first_sheet_lv8.md
```

The report must include:

```text
SGH-Q24R7_STATUS: PASS|REVISE
STATIC_ARCHITECTURE_GATE: PASS|FAIL
STATIC_SAMPLER_EVALUATOR_GATE: PASS|FAIL
RUNTIME_MEDIUM_CDE_GATE: PASS|FAIL
RUNTIME_LV8_12TYPES_X1_GATE: PASS|FAIL
RUNTIME_LV8_REFERENCE_SHEET1_GATE: PASS|PARTIAL|FAIL
```

Include exact first-sheet probe table and output metrics. Do not omit the unplaced list if partial.
