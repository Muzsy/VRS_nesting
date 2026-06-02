# SGH-Q25-R4 Semantic parity audit/fix

SGH-Q25-R4_STATUS: PASS

## Meta

- Task slug: `sgh_q25_r4_semantic_parity_audit_fix_no_benchmark`
- Canvas: `canvases/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md`
- Goal YAML: `codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.yaml`
- Run date: `2026-06-02`
- Branch / commit: `main` / `d8c7bd5faa2e151406399eb98ff5771b73c59f30`
- Focus area: `rust/vrs_solver/optimizer/sparrow`

## UPSTREAM_COMMIT

- `.cache/sparrow`: `c95454e390276231b278c879d25b39708398b7d3`

## PRE_TASK_GIT_STATUS

```text
?? README_SGH_Q25_R4_SEMANTIC_PARITY_AUDIT_FIX_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark/
?? scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py
```

## PRE_TASK_DIRTY_FILES

```text
README_SGH_Q25_R4_SEMANTIC_PARITY_AUDIT_FIX_PACKAGE.md
canvases/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
codex/codex_checklist/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.yaml
codex/prompts/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark/run.md
scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py
```

## PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES

```text
README_SGH_Q25_R4_SEMANTIC_PARITY_AUDIT_FIX_PACKAGE.md
canvases/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.yaml
codex/prompts/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark/run.md
```

These files were copied into place before implementation started. They are not implementation changes.

## POST_TASK_GIT_STATUS

```text
 M rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/sample_eval.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/best_samples.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
?? README_SGH_Q25_R4_SEMANTIC_PARITY_AUDIT_FIX_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark/
?? codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
?? codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.verify.log
?? scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py
```

## TASK_CHANGED_FILES

- `rust/vrs_solver/src/optimizer/sparrow/eval/sample_eval.rs`
- `rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs`
- `rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs`
- `rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs`
- `rust/vrs_solver/src/optimizer/sparrow/sample/best_samples.rs`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs`
- `codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md`
- `codex/codex_checklist/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md`
- `codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.verify.log`

## OUT_OF_SCOPE_NEW_CHANGES

OUT_OF_SCOPE_NEW_CHANGES: NONE

The only non-implementation untracked files are the pre-existing Q25-R4 task package files listed above.

## ANCHOR_RECT_MIN_CONVENTION_AUDIT

ANCHOR_RECT_MIN_CONVENTION: EXPLICIT_AND_TESTED

- `SampleEvaluator::evaluate_sample` now documents that `x`/`y` are rect-min sample-space coordinates.
- `ScoredPlacement` now carries `rect_min_x` and `rect_min_y` alongside the output anchor `SparrowPlacement`.
- `LBFEvaluator` and `SeparationEvaluator` fill `rect_min_x`/`rect_min_y` directly from their `rmx`/`rmy` inputs before anchor conversion.
- `CoordinateDescent` mutates `self.cur.rect_min_x` / `self.cur.rect_min_y`, not output anchor coordinates.
- `native_search_placement` already converts the current anchor placement to rect-min once at the search boundary via `rect_min_from_anchor`.

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/eval/sample_eval.rs:35`
- `rust/vrs_solver/src/optimizer/sparrow/eval/sample_eval.rs:52`
- `rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs:75`
- `rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs:95`
- `rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs:169`
- `rust/vrs_solver/src/optimizer/sparrow/sample/search.rs:239`

## BEST_SAMPLES_SAMPLE_SPACE_AUDIT

- `BestSamples` deduplicates by `rect_min_x` / `rect_min_y`, rotation, and sheet index.
- It no longer compares `placement.x` / `placement.y`, so anchor compensation for rotated placements cannot split equivalent sample-space candidates.

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/sample/best_samples.rs:20`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:458`

## LBF_INVALID_SEMANTICS_AUDIT

LBF_COLLISION_SEMANTICS: INVALID_REJECTED

- `LBFEvaluator::score_lbf_candidate` returns `None` for unsupported, boundary-colliding, or colliding samples.
- `lbf_evaluator.rs` no longer emits `ScoredPlacement { is_clear: false, ... }`.
- The artificial collision ranking branch (`1_000_000 + loss + lbf_quality`, neighbor-count loss, `QUANT_FLOOR` collision ordering) was removed from LBF.
- `LBFBuilder` continues to accept only clear placements and record no-clear fixed-sheet cases as unresolved.

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs:57`
- `rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs:62`
- `rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs:75`
- `rust/vrs_solver/src/optimizer/sparrow/lbf.rs:86`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:474`

## FIXED_SHEET_BOOTSTRAP_AUDIT

- Fixed-sheet unresolved seeding remains outside `LBFBuilder` in `fixed_sheet_separator_bootstrap`.
- The bootstrap is documented and tested as an infeasible fixed-sheet separator seed, not as upstream LBF construction success.

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs:34`
- `rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs:56`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:509`

## Q25_R3_REPORT_CLAIM_CORRECTION

Q25_R3_LBF_REPORT_MISMATCH: CONFIRMED_AND_FIXED

- The Q25-R3 report claim that local LBF matched upstream `collision -> Invalid` was not source-accurate.
- The mismatch was in `rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs`, function `LBFEvaluator::score_lbf_candidate`.
- Before Q25-R4, the local source could return a colliding `ScoredPlacement` with `is_clear=false` and an artificial collision score.
- Q25-R4 fixes this by rejecting collision/boundary/unsupported LBF samples with `None`, matching upstream invalid/rejected semantics.
- The coordinate-convention audit found a real bug: `CoordinateDescent` and `BestSamples` used output anchor coordinates where sampler/evaluator/search operate in rect-min sample space.

## LEGACY_CORE_REGRESSION_GATE

COMPRESSION_STATUS: DEFERRED_ONLY
LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE

- No compression phase was added.
- No LV8 benchmark quality acceptance was added.
- No `WorkingLayout` or `VrsCollisionTracker` was introduced under `optimizer/sparrow`.
- No bbox/AABB/proxy ranking was added to LBF or separation.

## TESTS_ADDED_OR_UPDATED

Added targeted Rust tests:

- `coord_descent_uses_rect_min_for_rotated_anchor_candidates`
- `best_samples_deduplicates_in_rect_min_sample_space`
- `lbf_evaluator_rejects_colliding_candidates_as_invalid`
- `fixed_sheet_bootstrap_is_outside_lbf_and_marked_infeasible`

Evidence:

- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:421`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:458`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:474`
- `rust/vrs_solver/src/optimizer/sparrow/tests.rs:509`

## BUILD_TEST_RESULTS

- `cargo build --manifest-path rust/vrs_solver/Cargo.toml --release` -> PASS (`Finished release profile`, 25 existing warnings).
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` -> first run: FAIL, `436 passed; 1 failed`; failing test `native_optimizer_solve_is_deterministic_for_same_seed`.
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib native_optimizer_solve_is_deterministic_for_same_seed` -> PASS (`1 passed`), proving the failed test was not reproducible in isolation.
- `cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib` -> second required full run: PASS (`437 passed; 0 failed`).
- `python3 scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py` -> PASS before report closure (`61 PASS; 0 WARN; 0 FAIL`); final run is part of the closing gate.
- `python3 scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py` -> final report run: PASS (`75 PASS; 0 WARN; 0 FAIL`).
- `./scripts/check.sh` -> PASS (`[DONE] smoketest OK`).
- `./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md` -> PASS; see AUTO_VERIFY block below.

<!-- AUTO_VERIFY_START -->
### Automatikus repo gate (verify.sh)

- eredmény: **PASS**
- check.sh exit kód: `0`
- futás: 2026-06-02T22:52:03+02:00 → 2026-06-02T22:55:03+02:00 (180s)
- parancs: `./scripts/check.sh`
- log: `/home/muszy/projects/VRS_nesting/codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.verify.log`
- git: `main@d8c7bd5`
- módosított fájlok (git status): 14

**git diff --stat**

```text
 .../src/optimizer/sparrow/eval/lbf_evaluator.rs    |  71 +-------
 .../src/optimizer/sparrow/eval/sample_eval.rs      |   4 +
 .../src/optimizer/sparrow/eval/sep_evaluator.rs    |   4 +
 .../src/optimizer/sparrow/sample/best_samples.rs   |   4 +-
 .../src/optimizer/sparrow/sample/coord_descent.rs  |  33 +++-
 rust/vrs_solver/src/optimizer/sparrow/tests.rs     | 184 +++++++++++++++++++++
 6 files changed, 227 insertions(+), 73 deletions(-)
```

**git status --porcelain (preview)**

```text
 M rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/sample_eval.rs
 M rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/best_samples.rs
 M rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs
 M rust/vrs_solver/src/optimizer/sparrow/tests.rs
?? README_SGH_Q25_R4_SEMANTIC_PARITY_AUDIT_FIX_PACKAGE.md
?? canvases/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
?? codex/codex_checklist/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
?? codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.yaml
?? codex/prompts/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark/
?? codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
?? codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.verify.log
?? scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py
```

<!-- AUTO_VERIFY_END -->
