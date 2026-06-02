# SGH-Q25-R5 Strict Sparrow parity profile

SGH-Q25-R5_STATUS: PASS

## Meta

- Task slug: `sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark`
- Canvas: `canvases/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.yaml`
- Run date: `2026-06-02`
- Branch / commit: `main` / `6ad8e89347d8839d1589824f0169997ff293a861`
- Focus area: `rust/vrs_solver/optimizer/sparrow`

## UPSTREAM_COMMIT

- `.cache/sparrow`: `c95454e390276231b278c879d25b39708398b7d3`

## PRE_TASK_GIT_STATUS

```text
?? README_SGH_Q25_R5_STRICT_SPARROW_PARITY_PROFILE_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark/
?? scripts/smoke_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.py
```

## PRE_TASK_DIRTY_FILES

```text
README_SGH_Q25_R5_STRICT_SPARROW_PARITY_PROFILE_PACKAGE.md
canvases/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
codex/codex_checklist/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.yaml
codex/prompts/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark/run.md
scripts/smoke_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.py
```

## PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES

```text
README_SGH_Q25_R5_STRICT_SPARROW_PARITY_PROFILE_PACKAGE.md
canvases/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.yaml
codex/prompts/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark/run.md
```

These files were copied into place before implementation started. They are not implementation changes.

## TASK_CHANGED_FILES

- `rust/vrs_solver/src/optimizer/cde_adapter.rs`
- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs`
- `rust/vrs_solver/src/optimizer/sparrow/explore.rs`
- `rust/vrs_solver/src/optimizer/sparrow/lbf.rs`
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs`
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs`
- `rust/vrs_solver/src/optimizer/sparrow/separator.rs`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs`
- `rust/vrs_solver/src/optimizer/sparrow/worker.rs`
- `codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md`
- `codex/codex_checklist/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md`

## OUT_OF_SCOPE_NEW_CHANGES

OUT_OF_SCOPE_NEW_CHANGES: NONE

Only YAML-declared outputs were modified for implementation/reporting.

## STRICT_PROFILE_CONFIG_AUDIT

STRICT_PROFILE_DEFAULT: SPARROW_STRICT_PARITY
INSTANCE_COUNT_DOWNSCALING: DISABLED_IN_STRICT_PROFILE

- `SparrowProfile::SparrowStrictParity` is the default profile for `SparrowConfig::from_solver_input`.
- Strict parity pins worker count and separator budgets to upstream constants.
- `scaled_for_instance_count` returns early for strict parity, so dense instance count cannot reduce budgets.
- `SparrowProfile::VrsFast` remains the explicit non-parity branch for retained local shortcuts.

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:69`
- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:94`
- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:117`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:726`

## TOUCHING_POLICY_AUDIT

TOUCHING_POLICY_STRICT: CDE_TOUCHING_IS_COLLISION
VRS_TOUCH_ALLOWED_POLICY: EXPLICIT_NON_PARITY_MODE

- `CdeTouchingPolicy::{SparrowStrict,VrsTouchAllowed}` makes touching semantics explicit.
- Generic CDE defaults preserve VRS touch-allowed behavior; Sparrow tracker/search/session paths request strict policy explicitly.
- Strict pair touching returns collision from raw CDE. Strict boundary handling allows truly interior placements but treats boundary-touch/outside as collision.

Evidence:

- `rust/vrs_solver/src/optimizer/cde_adapter.rs:41`
- `rust/vrs_solver/src/optimizer/cde_adapter.rs:131`
- `rust/vrs_solver/src/optimizer/cde_adapter.rs:276`
- `rust/vrs_solver/src/optimizer/cde_adapter.rs:290`
- `rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs:141`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:653`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:665`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:677`

## SAMPLE_BUDGET_AUDIT

SAMPLE_BUDGETS: UPSTREAM_PARITY

- Separator strict sample budget is `50` container, `25` focused, `3` coordinate descents.
- LBF strict sample budget is `1000` container, `0` focused, `3` coordinate descents.
- Local grid-derived strict sample count and LBF `128` shortcut were removed from strict path.

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:74`
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs:166`
- `rust/vrs_solver/src/optimizer/sparrow/lbf.rs:166`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:726`

## WORKER_ORDERING_AUDIT

WORKER_ORDERING: RNG_SHUFFLE_ONLY_IN_STRICT_PROFILE

- Strict worker pass collects colliding items and applies only deterministic RNG shuffle.
- Worker-index bias remains only in explicit `VrsFast`.
- Best worker load-back by weighted loss is unchanged.

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/worker.rs:100`
- `rust/vrs_solver/src/optimizer/sparrow/worker.rs:107`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:699`

## SEPARATOR_LOOP_AUDIT

SEPARATOR_LIMITS: UPSTREAM_PARITY_200_3

- Strict separator loop uses `SPARROW_PARITY_ITER_NO_IMPROVE_LIMIT = 200`.
- Strict separator loop uses `SPARROW_PARITY_STRIKE_LIMIT = 3`.

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:79`
- `rust/vrs_solver/src/optimizer/sparrow/separator.rs:96`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:726`

## EXPLORATION_DISRUPTION_AUDIT

EXPLORATION_RESTORE: NORMAL_BIASED_POOL_SELECTION
DISRUPTION_SWAP: RANDOM_LARGE_ITEM_PAIR

- Exploration restore samples an absolute normal-like value with stddev `0.25` and maps it into the sorted infeasible pool.
- Disruption selects a random pair from a large-item candidate pool and avoids fixed top-two selection.
- Strict max consecutive failed attempts is `10`; large-item cutoff percentile is `0.75`.

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs:82`
- `rust/vrs_solver/src/optimizer/sparrow/explore.rs:49`
- `rust/vrs_solver/src/optimizer/sparrow/explore.rs:175`
- `rust/vrs_solver/src/optimizer/sparrow/explore.rs:187`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:752`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:761`

## FIXED_SHEET_ADAPTATION_BOUNDARY

- Fixed-sheet search remains a local adaptation: current sheet first, then eligible alternate sheets.
- Fixed-sheet bootstrap remains outside LBF and is tested as an explicit infeasible separator seed.
- Strict boundary semantics mean exact sheet-boundary fit is not accepted as clear LBF success.

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs:204`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:510`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:808`

## LEGACY_CORE_REGRESSION_GATE

COMPRESSION_STATUS: DEFERRED_ONLY
LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE

- No compression phase was added to `optimizer/sparrow`.
- No LV8 benchmark quality acceptance was added.
- No `WorkingLayout` or `VrsCollisionTracker` appears in `optimizer/sparrow`.
- No bbox/AABB/proxy ranking was added to LBF or separation.

## TESTS_ADDED_OR_UPDATED

Added or updated Rust tests:

- `cde_sparrow_strict_reports_touching_rectangles_as_collision`
- `cde_vrs_touch_allowed_reports_touching_rectangles_as_no_collision`
- `sparrow_strict_boundary_touching_is_not_feasible`
- `strict_worker_orders_colliding_items_by_rng_shuffle_only`
- `strict_separator_uses_upstream_loop_limits`
- `strict_explore_uses_biased_pool_restore_not_seed_modulo`
- `strict_disruption_selects_random_large_item_pair_not_always_top_two`
- `fixed_sheet_extensions_are_documented_after_upstream_swap`
- `fixed_sheet_bootstrap_is_outside_lbf_and_marked_infeasible`

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:510`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:653`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:665`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:677`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:699`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:726`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:752`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:761`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:808`

## BUILD_TEST_RESULTS

- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` -> PASS (`Finished release profile`, 25 existing warnings).
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` -> PASS (`445 passed; 0 failed`; finished in 176.65s).
- Targeted new-test loop -> PASS for all Q25-R5 test names.
- `python3 scripts/smoke_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.py` -> PASS (`105 PASS; 0 WARN; 0 FAIL`).
- `./scripts/check.sh` -> PASS (`[DONE] smoketest OK`).
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md` -> PASS (`eredmény: PASS`).

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-03T00:22:30+02:00 → 2026-06-03T00:25:32+02:00 (182s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.verify.log`
- git: `main@6ad8e89`
- módosított fájlok (git status): 17

**git diff --stat**

```text
 rust/vrs_solver/src/optimizer/cde_adapter.rs       | 193 ++++++++++++++++-----
 .../src/optimizer/sparrow/diagnostics.rs           |  42 ++++-
 rust/vrs_solver/src/optimizer/sparrow/explore.rs   | 107 ++++++++++--
 rust/vrs_solver/src/optimizer/sparrow/lbf.rs       |  12 +-
 .../src/optimizer/sparrow/quantify/tracker.rs      |  14 +-
 .../src/optimizer/sparrow/sample/search.rs         |  25 ++-
 rust/vrs_solver/src/optimizer/sparrow/separator.rs |  10 +-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     | 192 +++++++++++++++++++-
 rust/vrs_solver/src/optimizer/sparrow/worker.rs    |  29 +++-
 9 files changed, 525 insertions(+), 99 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/cde_adapter.rs
 M rust/vrs_solver/src/optimizer/sparrow/diagnostics.rs
 M rust/vrs_solver/src/optimizer/sparrow/explore.rs
 M rust/vrs_solver/src/optimizer/sparrow/lbf.rs
 M rust/vrs_solver/src/optimizer/sparrow/quantify/tracker.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
 M rust/vrs_solver/src/optimizer/sparrow/separator.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
 M rust/vrs_solver/src/optimizer/sparrow/worker.rs
?? README_SGH_Q25_R5_STRICT_SPARROW_PARITY_PROFILE_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark/
?? codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.md
?? codex/reports/egyedi_solver/sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.verify.log
?? scripts/smoke_sgh_q25_r5_strict_sparrow_parity_profile_no_benchmark.py
```

<!-- AUTO_VERIFY_END -->
