# SGH-Q25-R2 — Complete upstream Sparrow core semantic port, compression excluded

## Read this first

The goal is not to improve LV8 benchmark numbers. The goal is to complete the upstream jagua_rs/Sparrow core port after Q25/Q25-R1.

Do not write a new heuristic. Do not tune the 191-piece first-sheet LV8 case. Do not mark PASS based on runtime progress. Compression remains out of scope.

## Absolute target

Production `sparrow_cde` remains:

```text
SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution
```

Inside that route, the core modules must now be upstream-semantics ports, not local approximations.

## Step 0 — repo hygiene / dirty state scope gate

From repo root, before coding:

```bash
git status --porcelain=v1 | tee /tmp/sgh_q25_r2_pre_status.txt
git diff --name-only | tee /tmp/sgh_q25_r2_pre_diff_names.txt
```

Create the report immediately:

```text
codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
```

Add sections:

```text
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
```

If files outside the allowed scope are already dirty, list them as pre-existing. Do not revert them. Do not edit them. Do not include them as Q25-R2 evidence.

Allowed implementation scope:

```text
rust/vrs_solver/src/optimizer/sparrow/**
```

Allowed supporting files only if required for the real bounded/visitor CDE hazard collector:

```text
rust/vrs_solver/src/optimizer/cde_adapter.rs
rust/vrs_solver/src/optimizer/cde_session.rs
rust/vrs_solver/src/optimizer/cde_observability.rs
rust/vrs_solver/src/optimizer/collision_severity.rs
```

Allowed task/report files:

```text
README_SGH_Q25_R2_COMPLETE_UPSTREAM_SPARROW_CORE_SEMANTIC_PORT_PACKAGE.md
canvases/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
codex/codex_checklist/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
codex/goals/canvases/egyedi_solver/fill_canvas_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.yaml
codex/prompts/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port/run.md
codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.verify.log
scripts/smoke_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.py
```

If any other file must be changed, stop and set:

```text
SGH-Q25-R2_STATUS: REVISE_SCOPE_BLOCKED
```

Then explain the required file and reason. Do not continue silently.

## Step 1 — upstream source of truth

Run:

```bash
test -d .cache/sparrow || ./scripts/ensure_sparrow.sh
git -C .cache/sparrow rev-parse HEAD
```

Record the commit in the report.

Read these upstream files before coding:

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
.cache/sparrow/src/sample/coord_descent.rs
.cache/sparrow/src/sample/best_samples.rs
.cache/sparrow/src/sample/uniform_sampler.rs
.cache/sparrow/src/optimizer/lbf.rs
.cache/sparrow/src/optimizer/worker.rs
.cache/sparrow/src/optimizer/separator.rs
.cache/sparrow/src/optimizer/explore.rs
.cache/sparrow/src/optimizer/mod.rs
```

Do not infer upstream behavior from current VRS code.

## Step 2 — complete the CDE hazard collector port

Q25-R1 still processes hazards after a finished `CdeCandidateSession::query(candidate)` batch. That is not full upstream semantics.

Implement a bounded/visitor-style collection path:

- candidate CDE collection must be able to call the specialized collector as hazards are found;
- collector must accumulate tracker-weighted pair/container loss;
- collector must support loss-bound / upper-bound early termination during collection where local CDE allows it;
- if `CdeCandidateSession` lacks the necessary API, extend the allowed CDE adapter layer instead of hiding post-query accumulation in `specialized_cde_pipeline.rs`.

Reject condition:

```rust
let res = session.query(candidate);
for layout_idx in res.colliding_layout_idxs { ... }
```

This can remain only as a legacy/simple helper outside the production `SeparationEvaluator` path. It is not the Q25-R2 semantic collector path.

## Step 3 — complete `SeparationEvaluator`

Make `SeparationEvaluator` mirror upstream semantics:

1. prepare candidate transform;
2. reload collector with current upper bound;
3. collect hazards through the bounded collector path;
4. early-terminate dominated samples;
5. score candidate only from collector/tracker weighted loss;
6. return clear/collision/invalid from collector state.

No bbox/AABB/extent collision loss is allowed. Broad-phase fit checks are allowed only as fit checks, not ranking.

## Step 4 — clean quantification and tracker

Q25-R1 started upstream overlap-proxy quantification. Finish it:

- default pair loss = upstream overlap-proxy + epsilon², sqrt, shape penalty;
- default container loss = upstream outside/intersection-area + shape penalty;
- tracker stores pair/container raw loss and GLS weights;
- tracker exposes item weighted loss, total weighted loss, collision/problem items, moved-item update;
- remove stale “resolution distance” production comments/counters unless explicitly non-default experimental.

Do not claim upstream parity if the default production tracker uses a different loss model.

## Step 5 — fix LBF semantics

The LBF builder must not use least-infeasible placement as constructive success.

Required:

- every LBF placement attempt goes through `search_placement + LBFEvaluator`;
- fixed-sheet adaptation may search across all available sheets and allowed rotations;
- if no clear placement exists, record unresolved/partial honestly;
- do not insert a colliding “best bad” placement and call it LBF success;
- if the later separator needs an infeasible seed, that must be a separately named fixed-sheet adaptation, not LBF parity.

Ban in production LBF path:

```text
shelf_construct
fallback_anchor
fixed_sheet_recovery_candidate
candidate_penalty
overlap_score
least-infeasible success
```

## Step 6 — complete search/sampler/coordinate descent semantics

Port upstream search behavior, not a benchmark shortcut:

- `BestSamples` ordered by evaluator score and upper bound;
- focused sampler around current placement;
- uniform/container-wide sampler across eligible fixed sheets;
- coordinate descent with upstream axis/state behavior, success/fail step updates, and rotation refinement where rotations are allowed;
- no dense-only budget hard-code that changes semantics to hide poor search.

Budgets can be configurable. They cannot be fake-progress shortcuts.

## Step 7 — complete worker/separator semantics

Port upstream worker/separator semantics:

- worker targets come from tracker collision/problem state;
- move acceptance: moved-item weighted loss must not increase;
- worker result carries full state and total weighted loss;
- separator loads back the minimum total weighted loss worker state;
- pair count/raw loss are diagnostics or tie-breakers only;
- strike/no-improvement loop follows upstream loss semantics;
- sequential execution is allowed only as a performance limitation, not a semantic change.

## Step 8 — complete exploration/disruption semantics

Port upstream exploration intent:

- infeasible solution pool;
- biased restore;
- large-item disruption;
- fixed-sheet equivalent of contained-item relocation;
- tracker-consistent update after disruption.

Contained relocation must be geometry/CDE meaningful. Bbox-only containment is not enough.

## Step 9 — verification

Run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.py
./scripts/check.sh
```

Do not add dense LV8 quality acceptance. Cheap existing smokes may run only as “not broken” checks.

Then run:

```bash
./scripts/verify.sh --report codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
```

## Required final report

Report path:

```text
codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
```

Start with exactly one:

```text
SGH-Q25-R2_STATUS: PASS
SGH-Q25-R2_STATUS: REVISE
SGH-Q25-R2_STATUS: REVISE_SCOPE_BLOCKED
```

Required sections:

```text
UPSTREAM_COMMIT
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
TASK_CHANGED_FILES
OUT_OF_SCOPE_NEW_CHANGES
BUILD_TEST_RESULTS
SEMANTIC_MAPPING_TABLE
DEFERRED_COMPRESSION_ONLY
```

Mapping table columns:

```text
Upstream file | Upstream type/function | Required behavior | Local file | Local implementation | Status | Fixed-sheet deviation | Evidence
```

Allowed mapping statuses:

```text
PORTED
ADAPTED_FIXED_SHEET
DEFERRED_COMPRESSION_ONLY
NOT_APPLICABLE_IO_ONLY
REVISE
```

Rules:

- Any non-compression `REVISE` row means final status must be `REVISE`.
- `ADAPTED_FIXED_SHEET` requires an actual fixed-sheet reason.
- “Sparrow-like”, “similar”, “future work”, “progress”, “benchmark improved”, or “good enough” cannot justify PASS.

