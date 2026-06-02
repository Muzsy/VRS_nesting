# SGH-Q25-R4 Semantic parity audit/fix — coordinate convention + LBF Invalid semantics

## Why this task exists

Q25-R3 made the local `optimizer/sparrow` much closer to a real upstream jagua_rs/Sparrow core. However, a post-audit found concrete source-level semantic risks that can invalidate the claimed parity even if the report says PASS.

This task is a narrow semantic audit/fix, not another broad porting task and not a benchmark task.

The suspected failures are specific:

1. **Coordinate convention leak**  
   Local samplers and evaluators operate in rect-min coordinates (`rmx`, `rmy`). `SparrowPlacement` stores anchor coordinates produced by `placement_anchor_from_rect_min`. `sample/coord_descent.rs` currently appears to take `self.cur.placement.x/y` and feed deltas back into `evaluate_sample`, which means anchor coordinates can be treated as rect-min coordinates. That is mostly invisible at 0° but becomes a real semantic error at 45° / continuous rotation.

2. **BestSamples uniqueness may use the wrong coordinate space**  
   If `ScoredPlacement` stores only anchor output coordinates, `BestSamples` cannot reliably deduplicate in sampler/search-space. Deduplication should compare the sampled rect-min coordinates, or a clearly equivalent sample-space key, not anchor coordinates that shift with rotation.

3. **LBF report/source mismatch**  
   Q25-R3 report states upstream `LBFEvaluator` behavior as “collision → Invalid”, but the current local `lbf_evaluator.rs` can still return `Some(ScoredPlacement { is_clear: false, ... })` for collisions. That is not acceptable for LBF constructive placement. LBF may only accept clear placements; collision must be invalid/rejected.

4. **Fixed-sheet bootstrap must remain honest**  
   Fixed-sheet unresolved seeding is allowed only as `fixed_sheet_separator_bootstrap` outside `LBFBuilder`. It must never be described as LBF success or upstream-equivalent LBF construction. It is a fixed-sheet separator bootstrap because fixed sheets cannot widen like a strip.

Compression remains out of scope. Benchmarks remain out of scope. Build/test/smoke are guardrails only.

## Source of truth

Read before editing:

```text
AGENTS.md
docs/codex/yaml_schema.md
docs/codex/report_standard.md
codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
.cache/sparrow/src/eval/lbf_evaluator.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/sample/coord_descent.rs
.cache/sparrow/src/sample/best_samples.rs
.cache/sparrow/src/sample/uniform_sampler.rs
.cache/sparrow/src/optimizer/lbf.rs
```

Record:

```bash
git -C .cache/sparrow rev-parse HEAD
```

## Scope hygiene gate

At task start run:

```bash
git status --porcelain=v1
git diff --name-only
```

Report:

```text
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
```

Allowed implementation scope:

```text
rust/vrs_solver/src/optimizer/sparrow/eval/sample_eval.rs
rust/vrs_solver/src/optimizer/sparrow/eval/lbf_evaluator.rs
rust/vrs_solver/src/optimizer/sparrow/eval/sep_evaluator.rs
rust/vrs_solver/src/optimizer/sparrow/sample/coord_descent.rs
rust/vrs_solver/src/optimizer/sparrow/sample/search.rs
rust/vrs_solver/src/optimizer/sparrow/sample/best_samples.rs
rust/vrs_solver/src/optimizer/sparrow/sample/uniform_sampler.rs
rust/vrs_solver/src/optimizer/sparrow/fixed_sheet.rs
rust/vrs_solver/src/optimizer/sparrow/lbf.rs
rust/vrs_solver/src/optimizer/sparrow/model.rs
rust/vrs_solver/src/optimizer/sparrow/mod.rs
rust/vrs_solver/src/optimizer/sparrow/tests.rs
rust/vrs_solver/src/optimizer/cde_adapter.rs
```

`rust/vrs_solver/src/optimizer/cde_adapter.rs` may be changed only if a test or helper requires a coordinate-convention utility that cannot live cleanly under `optimizer/sparrow`.

Do not modify unrelated optimizer modules, API, frontend, samples, benchmark fixtures, old reports, or docs outside this task package.

At task end report:

```text
POST_TASK_GIT_STATUS
TASK_CHANGED_FILES
OUT_OF_SCOPE_NEW_CHANGES
```

`OUT_OF_SCOPE_NEW_CHANGES` must be `NONE` for PASS. If new out-of-scope changes are needed, stop and mark:

```text
SGH-Q25-R4_STATUS: REVISE_SCOPE_BLOCKED
```

## Required work

### 1. Establish one explicit sample coordinate convention

The local convention must be explicit in code comments and implementation:

```text
SampleEvaluator::evaluate_sample(x, y, rot) receives rect-min coordinates.
UniformBBoxSampler emits rect-min coordinates.
search_placement and coordinate descent refine rect-min coordinates.
ScoredPlacement stores the final SparrowPlacement as anchor coordinates for layout output.
```

Required implementation shape:

- `ScoredPlacement` must carry `rect_min_x` and `rect_min_y` fields, or an equivalently explicit sample-space coordinate key. Prefer the names `rect_min_x` and `rect_min_y` for auditability.
- `LBFEvaluator` and `SeparationEvaluator` must fill those fields from their input `rmx/rmy` before converting to anchor.
- `BestSamples` uniqueness/deduplication must compare sample-space rect-min coordinates, not `placement.x/y` anchor coordinates.
- `CoordinateDescent` must keep and mutate current rect-min coordinates. It must not use `self.cur.placement.x/y` as the translation state.
- Rotation wiggle must call the evaluator with a consistent rect-min coordinate for the new rotation. Do not convert anchor to rect-min using the wrong rotation.
- `native_search_placement` may convert current anchor placement to rect-min once at the search boundary using `rect_min_from_anchor`, as it already does conceptually.

Reject conditions:

- `coord_descent.rs` still contains direct translation state like `let tx = self.cur.placement.x; let ty = self.cur.placement.y;`.
- `BestSamples` still deduplicates with `s.placement.x - cand.placement.x` / `s.placement.y - cand.placement.y`.
- The task changes evaluators to accept anchor coordinates just to hide the mismatch, without updating samplers/search/report consistently.
- 45°/continuous rotation candidates are treated as if anchor and rect-min were interchangeable.

### 2. Fix LBF Invalid semantics

Local LBF must match the upstream semantic contract:

```text
Clear sample -> candidate accepted/scored for LBF.
Collision/boundary/unsupported sample -> Invalid/rejected.
```

Required behavior:

- `LBFEvaluator::evaluate_sample` must not return a colliding `ScoredPlacement`.
- `LBFEvaluator` must not emit `is_clear: false` candidates.
- Remove the artificial collision ordering branch from LBF (`1_000_000 + loss + lbf_quality`, `QUANT_FLOOR`, neighbour-count loss, etc.).
- `LBFBuilder` may only place candidates whose evaluator returned clear.
- If no clear placement exists on fixed sheets, record unresolved honestly.
- Fixed-sheet infeasible bootstrap stays outside LBF in `fixed_sheet_separator_bootstrap`.

Reject conditions:

- `lbf_evaluator.rs` contains `is_clear: false`.
- `lbf_evaluator.rs` returns `Some(ScoredPlacement)` after a collision verdict.
- LBF path contains “best bad candidate”, “least infeasible”, `candidate_penalty`, `overlap_score`, or artificial `1_000_000` collision ranking.
- The report claims LBF collision-invalid parity while the source can still emit a colliding LBF candidate.

### 3. Add targeted semantic tests

Add Rust tests that fail on the Q25-R3 risk patterns. Include at least these test names:

```text
coord_descent_uses_rect_min_for_rotated_anchor_candidates
best_samples_deduplicates_in_rect_min_sample_space
lbf_evaluator_rejects_colliding_candidates_as_invalid
fixed_sheet_bootstrap_is_outside_lbf_and_marked_infeasible
```

Test intent:

- A rotated 45° or non-90° placement must not be refined by treating anchor as rect-min.
- Two rotated candidates with equivalent/near-equivalent sample-space rect-min should deduplicate even when anchor differs due to rotation compensation.
- A colliding LBF candidate must be rejected/invalid, not returned as `is_clear=false`.
- Fixed-sheet unresolved items may be seeded by bootstrap, but this must be outside `LBFBuilder` and not counted as constructive clear LBF success.

Do not add LV8 dense benchmark acceptance here.

### 4. Correct the parity report claim

Do not rewrite the historical Q25-R3 report. Write a new Q25-R4 report that explicitly contains:

```text
Q25_R3_REPORT_CLAIM_CORRECTION
```

Required content:

- State whether the Q25-R3 LBF mapping claim was source-accurate or not.
- If it was not source-accurate, say that plainly and list the exact local file/function corrected.
- State whether the coordinate-convention audit found a real bug or a false alarm.
- Do not hide source mismatches behind “report PASS”.

### 5. Keep non-goals locked

Do not:

- add compression;
- add LV8 benchmark quality acceptance;
- reintroduce legacy `WorkingLayout` / `VrsCollisionTracker` into `optimizer/sparrow`;
- add bbox/AABB/proxy ranking to separation or LBF;
- touch unrelated files to make checks pass.

## Acceptance commands

Run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
```

If `cargo` is unavailable in the environment, mark the affected command as not run with reason and do not claim full PASS unless it is run elsewhere and the evidence is pasted into the report.

## Report requirements

Write:

```text
codex/reports/egyedi_solver/sgh_q25_r4_semantic_parity_audit_fix_no_benchmark.md
```

Required sections:

```text
SGH-Q25-R4_STATUS
UPSTREAM_COMMIT
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
TASK_CHANGED_FILES
OUT_OF_SCOPE_NEW_CHANGES
ANCHOR_RECT_MIN_CONVENTION_AUDIT
BEST_SAMPLES_SAMPLE_SPACE_AUDIT
LBF_INVALID_SEMANTICS_AUDIT
FIXED_SHEET_BOOTSTRAP_AUDIT
Q25_R3_REPORT_CLAIM_CORRECTION
LEGACY_CORE_REGRESSION_GATE
TESTS_ADDED_OR_UPDATED
BUILD_TEST_RESULTS
```

For PASS:

```text
OUT_OF_SCOPE_NEW_CHANGES: NONE
Q25_R3_LBF_REPORT_MISMATCH: CONFIRMED_AND_FIXED
ANCHOR_RECT_MIN_CONVENTION: EXPLICIT_AND_TESTED
LBF_COLLISION_SEMANTICS: INVALID_REJECTED
COMPRESSION_STATUS: DEFERRED_ONLY
LV8_BENCHMARK_STATUS: NOT_USED_AS_ACCEPTANCE
```
