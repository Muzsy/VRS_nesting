# Run prompt — SGH-Q25-R3 Upstream Sparrow core port closure, no benchmark focus

You are working in `/home/muszy/projects/VRS_nesting`.

This is a port-closure task. Do not treat it as benchmark tuning. Do not chase the LV8 191-piece first-sheet result. The goal is to finish the remaining non-compression upstream jagua_rs/Sparrow core semantics so the project can stop spending tasks on partial Sparrow-like rewrites.

Compression is out of scope and must remain disabled.

## 0. Hard rule

If a non-compression upstream behavior is not implemented by the end, do not write PASS. Mark:

```text
SGH-Q25-R3_STATUS: REVISE_SEMANTIC_GAP
```

If you need to modify files outside the allowed scope, stop and mark:

```text
SGH-Q25-R3_STATUS: REVISE_SCOPE_BLOCKED
```

Do not fake completion with “adapted”, “equivalent”, “perf-only skip”, “future work”, or “benchmark improved”.

## 1. Scope gate before editing

Run and save the output:

```bash
git status --porcelain=v1
git diff --name-only
git -C .cache/sparrow rev-parse HEAD
```

In the report create:

```text
UPSTREAM_COMMIT
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
```

Allowed implementation files:

```text
rust/vrs_solver/src/optimizer/sparrow/**
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/cde_session.rs
rust/vrs_solver/src/optimizer/cde_observability.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
```

CDE adapter files are allowed only for implementing upstream-style hazard collection hooks. Do not touch unrelated files.

## 2. Read upstream source before coding

Read these files from `.cache/sparrow` and keep them open while implementing:

```text
src/eval/specialized_jaguars_pipeline.rs
src/eval/sep_evaluator.rs
src/eval/lbf_evaluator.rs
src/eval/sample_eval.rs
src/quantify/mod.rs
src/quantify/tracker.rs
src/sample/search.rs
src/sample/uniform_sampler.rs
src/sample/coord_descent.rs
src/sample/best_samples.rs
src/optimizer/lbf.rs
src/optimizer/worker.rs
src/optimizer/separator.rs
src/optimizer/explore.rs
src/optimizer/mod.rs
```

The local implementation must follow those semantics. Fixed-sheet/multisheet differences may exist only where upstream infinite-strip behavior is impossible.

## 3. Implement specialized CDE pipeline closure

The local `specialized_cde_pipeline.rs` must implement the upstream shape of `collect_poly_collisions_in_detector_custom`:

1. Transform/build candidate shape.
2. Pole pre-pass:
   - iterate candidate surrogate/poles or local equivalent;
   - collect CDE hazards for poles;
   - stop pole pre-pass when accumulated pole area exceeds the upstream threshold equivalent (`shape.area * 0.5 / PI`);
   - early-terminate after each hazard if collector loss exceeds bound.
3. Bit-reversed edge traversal with early termination after each edge hazard collection.
4. Containment pass for hazards not detected by edges, again with early termination.
5. Collector accumulates weighted loss during traversal, not only after a completed `query` result.

If the current local `CdeCandidateSession` cannot expose pole/edge/containment collection, extend the allowed adapter layer. Do not leave a report row saying pole pre-pass is skipped.

## 4. Implement LBF closure

Fix local `lbf.rs` so LBF is a real upstream-style constructive builder, not a fixed-sheet recovery heuristic.

Required:

- Sort by upstream-equivalent convex-hull-area × diameter. Do not use simple `width * height * diagonal` as the default ordering.
- Place via `search_placement + LBFEvaluator` only.
- Accept only clear placements.
- If no clear placement exists on fixed sheets, record unresolved honestly.
- Any infeasible bootstrap needed for separator must be outside `LBFBuilder` and clearly named as fixed-sheet separator bootstrap, not LBF.
- Remove density-specific seed budget/shortcut logic. No `instances.len() >= 100` behavior change in LBF.
- Remove or keep absent all fake constructive shortcut names: `shelf_construct`, `fallback_anchor`, `fixed_sheet_recovery_candidate`, `candidate_penalty`, `overlap_score`, `least_infeasible`, “best bad”.

## 5. Implement search/sampler closure

Fix `sample/uniform_sampler.rs`, `sample/search.rs`, and coordinate-descent integration so local search follows upstream Algorithm 6.

Required:

- `UniformBBoxSampler` stores rotation entries with valid x/y ranges.
- It supports none/discrete/continuous rotations. Continuous rotation uses upstream-equivalent 16 rotation samples unless an explicit config maps the constant.
- It intersects sample bbox and container bbox after rotated-shape bbox compensation.
- It randomly samples from valid ranges; grid enumeration may be an optional deterministic smoke helper, not the primary algorithm.
- `search_placement` uses:
  - current/reference placement candidate where applicable;
  - focused sampler around the reference/current placement bbox;
  - container-wide sampler;
  - `BestSamples` with item-min-dim uniqueness threshold;
  - first coordinate descent over all best samples;
  - second/final coordinate descent over the best sample;
  - rotation wiggle where rotations allow.
- Multi-sheet adaptation may wrap the upstream search for each eligible fixed sheet, but must not replace the sampler/evaluator/refinement logic.

## 6. Preserve Q25-R2 semantic fixes

Do not regress:

- no `WorkingLayout` or `VrsCollisionTracker` in `optimizer/sparrow`;
- no compression;
- `SeparationEvaluator` uses specialized collector and upper/loss bound;
- quantification is overlap-proxy + shape penalty;
- tracker has pair/container losses, GLS weights, item/total weighted loss;
- worker accepts moves only when moved-item weighted loss does not increase;
- separator selects best worker by total weighted loss;
- exploration has pool/restore/disruption/contained relocation.

## 7. Write the report

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

The mapping table columns must be:

```text
Upstream file | Upstream behavior | Local file/function | Status | Allowed deviation | Evidence
```

Allowed PASS statuses:

```text
PORTED
ADAPTED_FIXED_SHEET_NO_SEMANTIC_LOSS
DEFERRED_COMPRESSION_ONLY
```

Forbidden for PASS:

```text
PARTIAL
TODO
STUB
PROXY
REVISE
PERF_ONLY_SKIP
ADAPTED_APPROXIMATION
future work
not implemented
```

Only compression may be deferred.

## 8. Verify

Run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.py
./scripts/check.sh
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r3_upstream_sparrow_port_closure_no_benchmark.md
```

Append build/test results to the report.

No LV8 dense quality gate belongs in this task. If you run one manually, mark it as non-acceptance diagnostic only.
