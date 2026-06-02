# SGH-Q25-R3 Upstream Sparrow core port closure, no benchmark focus

## Why this task exists

The project has spent too many tasks on “Sparrow-like” fixes. Q25 finally split the monolith. Q25-R1 and Q25-R2 removed several proxy/stub paths. The remaining task is not to improve LV8 numbers. The remaining task is to close the source-level semantic gaps against upstream jagua_rs/Sparrow so the porting phase can end.

This task must not optimize for the 191-piece LV8 first-sheet benchmark. That benchmark may be useful later. It is not the development driver here.

Compression stays out of scope. Everything else in the upstream Sparrow core must be either ported or explicitly documented as an unavoidable fixed-sheet adaptation.

## Source of truth

Use the local upstream clone:

```text
.cache/sparrow
```

Record:

```bash
git -C .cache/sparrow rev-parse HEAD
```

Read these files before editing:

```text
.cache/sparrow/src/eval/specialized_jaguars_pipeline.rs
.cache/sparrow/src/eval/sep_evaluator.rs
.cache/sparrow/src/eval/lbf_evaluator.rs
.cache/sparrow/src/eval/sample_eval.rs
.cache/sparrow/src/quantify/mod.rs
.cache/sparrow/src/quantify/tracker.rs
.cache/sparrow/src/quantify/pair_matrix.rs
.cache/sparrow/src/quantify/overlap_proxy.rs
.cache/sparrow/src/sample/search.rs
.cache/sparrow/src/sample/uniform_sampler.rs
.cache/sparrow/src/sample/coord_descent.rs
.cache/sparrow/src/sample/best_samples.rs
.cache/sparrow/src/optimizer/lbf.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/optimizer/mod.rs
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
rust/vrs_solver/src/optimizer/sparrow/**
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/cde_session.rs
rust/vrs_solver/src/optimizer/cde_observability.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
```

The CDE adapter files may be changed only when required to implement upstream-like hazard collection semantics. Do not change `adapter.rs`, `sheet.rs`, `item.rs`, unrelated optimizer modules, API, frontend, samples, or unrelated docs.

At task end report:

```text
POST_TASK_GIT_STATUS
TASK_CHANGED_FILES
OUT_OF_SCOPE_NEW_CHANGES
```

`OUT_OF_SCOPE_NEW_CHANGES` must be `NONE` for PASS. If new out-of-scope changes are needed, stop and mark `SGH-Q25-R3_STATUS: REVISE_SCOPE_BLOCKED`.

## Required port closure work

### 1. Complete specialized CDE pipeline parity

Q25-R2 implemented visitor/bounded collection, but the report explicitly accepted that the upstream pole pre-pass was skipped. Q25-R3 must close that gap.

Required behavior:

- Before edge traversal, perform the upstream-style pole pre-pass for the candidate shape.
- Check poles until the accumulated pole area exceeds the upstream threshold equivalent: roughly `shape.area * 0.5 / PI`.
- After each pole hazard insertion, call early termination / loss-bound logic.
- Then run bit-reversed edge traversal.
- Then run containment pass for remaining partial hazards.
- The collector must still accumulate weighted loss during traversal and terminate as soon as the loss bound is exceeded.

Reject conditions:

- Report says pole pre-pass is omitted, “perf-only”, “not needed”, or “future work”.
- `specialized_cde_pipeline.rs` is a wrapper around `session.query(candidate)`.
- Loss is accumulated only after a finished batch result.
- Edge traversal exists but pole pre-pass and containment pass are not both implemented.

If the current CDE adapter cannot expose pole/edge/containment hooks, extend the allowed CDE adapter layer. Do not document the missing hook as an accepted semantic gap.

### 2. Close LBFBuilder parity

Q25-R2 still had local LBF adaptations: simple area/diameter ordering, density-based seed budget, limited sampling, and unresolved seeding mixed near LBF.

Required behavior:

- LBF ordering must be upstream-equivalent: convex-hull-area × diameter, descending, then expanded by demand/instance quantity as appropriate for VRS flattened instances.
- LBF placement must use `search_placement + LBFEvaluator` only.
- LBF may accept only `SampleEval::Clear` / clear local equivalent.
- If no clear placement exists on fixed sheets, the LBF result must record unresolved honestly.
- Fixed-sheet infeasible starting placement, if still needed so separator has every item present, must be outside LBFBuilder and clearly named as a fixed-sheet separator bootstrap, not LBF parity.
- Remove density-specific seed shortcuts such as `instances.len() >= 100`, special dense `seed_budget_s`, or one-sample LBF search paths.

Reject conditions:

- `shelf_construct`, `fallback_anchor`, `fixed_sheet_recovery_candidate`, `candidate_penalty`, `overlap_score`, `least_infeasible`, or “best bad candidate” appears in the LBF path.
- LBF accepts a colliding placement as a successful constructive placement.
- LBF uses hard-coded `samples_for(rot, 1, ...)` as its normal placement search.
- LBF ordering remains simple bbox/width-height area instead of upstream convex-hull-area × diameter.

### 3. Close search/sampler parity

Required behavior:

- `UniformBBoxSampler` must follow upstream semantics:
  - precompute rotation entries;
  - support none/discrete/continuous rotations;
  - use 16 evenly spaced continuous rotation samples unless config explicitly maps upstream constants;
  - compute valid x/y ranges by intersecting sample bbox and container bbox after rotated-shape bbox compensation;
  - sample randomly from valid ranges, not grid-only as the primary sampler.
- `search_placement` must follow upstream Algorithm 6:
  - add current/reference placement as a candidate where applicable;
  - focused sampler around the current/reference placement bbox;
  - container-wide sampler across eligible fixed sheets;
  - `BestSamples` with uniqueness threshold based on item min dimension;
  - first coordinate descent over all best samples;
  - second/final coordinate descent over the best sample;
  - rotation wiggle when rotations allow it.
- Multi-sheet adaptation may search multiple fixed containers, but it must not replace the upstream sampler/evaluator/refinement semantics.

Reject conditions:

- dense-specific throttles alter algorithm semantics.
- search is primarily grid enumeration with random jitter sprinkled in.
- focused and container-wide samplers are not separate concepts.
- coordinate descent is one-pass only.
- continuous rotation sampling/refinement is absent.

### 4. Keep Q25-R2 gains intact

Do not regress these Q25-R2 properties:

- `SeparationEvaluator` uses specialized collector + upper/loss bound, not bbox ranking.
- Quantification uses upstream overlap-proxy + shape penalty, not resolution-distance default.
- Tracker stores pair/container loss and GLS weights and exposes item/total weighted loss.
- Worker acceptance is moved-item weighted-loss based.
- Separator best-worker selection is total weighted-loss based.
- Exploration has infeasible pool/restore/disruption and contained-item relocation fixed-sheet equivalent.
- Production `sparrow_cde` does not use `WorkingLayout`, `VrsCollisionTracker`, or old VRS core.

### 5. Mapping table: no open non-compression gap

The report must contain:

```text
PORT_CLOSURE_MAPPING_TABLE
```

Columns:

```text
Upstream file | Upstream behavior | Local file/function | Status | Allowed deviation | Evidence
```

Allowed statuses:

```text
PORTED
ADAPTED_FIXED_SHEET_NO_SEMANTIC_LOSS
DEFERRED_COMPRESSION_ONLY
```

Forbidden statuses for PASS:

```text
PARTIAL
TODO
STUB
PROXY
REVISE
PERF_ONLY_SKIP
ADAPTED_APPROXIMATION
```

Only compression may be deferred. If any non-compression row is not closed, mark `SGH-Q25-R3_STATUS: REVISE_SEMANTIC_GAP`.

## Acceptance commands

Run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
```

Do not add LV8 dense quality acceptance. If you run LV8 manually, keep it in an appendix and do not use it to justify semantic PASS.

## Report requirements

Write:

```text
codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
```

Required sections:

```text
SGH-Q25-R3_STATUS
UPSTREAM_COMMIT
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
TASK_CHANGED_FILES
OUT_OF_SCOPE_NEW_CHANGES
PORT_CLOSURE_MAPPING_TABLE
FIXED_SHEET_DEVIATIONS_WITH_NO_SEMANTIC_LOSS
DEFERRED_COMPRESSION_ONLY
BUILD_TEST_RESULTS
```

PASS requires:

```text
SGH-Q25-R3_STATUS: PASS
OUT_OF_SCOPE_NEW_CHANGES: NONE
No non-compression semantic gap remains open.
```
