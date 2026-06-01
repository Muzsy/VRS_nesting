# SGH-Q25-R2 Complete upstream Sparrow core semantic port, compression excluded

## Why this task exists

The last tasks repeatedly said “full jagua_rs/Sparrow implementation”, but the implementation still took the smallest passing route: Sparrow-shaped names, local approximations, smoke-friendly progress, and fixed-sheet shortcuts. Q25 fixed structure. Q25-R1 fixed several obvious semantic stubs. Q25-R2 must finish the core port without benchmark distraction.

Do **not** tune the 191-piece LV8 first-sheet case. Do **not** optimize for dense benchmark progress. The quality of upstream jagua_rs/Sparrow is not under test here. The only target is whether our port actually carries the upstream core logic.

Compression remains out of scope and must stay disabled.

## Source of truth

Use the local upstream clone, not memory and not the current VRS implementation:

```text
.cache/sparrow
```

Record:

```bash
git -C .cache/sparrow rev-parse HEAD
```

Read and map these files before coding:

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

## Scope hygiene / dirty repo gate

Codex previously stopped because `git status` showed many modifications outside the task scope. This task must handle that explicitly.

### At task start

Run:

```bash
git status --porcelain=v1
git diff --name-only
```

Write the result into the report under:

```text
PRE_TASK_GIT_STATUS
PRE_TASK_DIRTY_FILES
PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES
```

If files outside the allowed Q25-R2 scope are already dirty before you start, record them as pre-existing. Do **not** revert them. Do **not** modify them. Do **not** use them as task evidence.

### Allowed Q25-R2 implementation scope

Primary allowed implementation files:

```text
rust/vrs_solver/src/optimizer/sparrow/**
```

Allowed supporting CDE adapter files **only if required to implement upstream-style hazard collection/early termination**:

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

If you need to modify anything else, stop and mark `SGH-Q25-R2_STATUS: REVISE_SCOPE_BLOCKED`, with the exact reason. Do not silently absorb broad changes into this task.

### At task end

Report:

```text
POST_TASK_GIT_STATUS
TASK_CHANGED_FILES
OUT_OF_SCOPE_NEW_CHANGES
```

`OUT_OF_SCOPE_NEW_CHANGES` must be `NONE` for PASS. Pre-existing dirty files are acceptable only if they are unchanged by this task and listed separately.

## Required semantic port completion

### 1. Real upstream-style CDE hazard collection pipeline

Q25-R1 still approximates the upstream collector because `collect_poly_collisions_in_detector_custom(...)` calls `session.query(candidate)` and accumulates loss after a batch result is returned.

Required:

- Implement a collector path that can accumulate weighted pair/container loss during CDE hazard collection, not only after a completed `CdeBatchResult`.
- Provide loss-bound/upper-bound early termination at collection time wherever the local CDE API allows it.
- If the current `CdeCandidateSession` API is insufficient, extend the allowed CDE adapter layer with a bounded/visitor-style collection method.
- The specialized collector must be the primary `SeparationEvaluator` path.

Reject if the specialized pipeline is still primarily:

```rust
let res = session.query(candidate);
for layout_idx in res.colliding_layout_idxs { ... }
```

That is a useful batch adapter, but not a complete upstream collector port.

### 2. `SeparationEvaluator` must mirror upstream semantics

Required:

- Use the specialized collector with upper-bound reload and early termination.
- Candidate ranking must be collector/tracker weighted loss based.
- `Clear` / `Collision { loss }` / invalid decisions must be derived from collector state.
- AABB/bbox/extent may appear only as safe broad-phase or sheet-fit clipping, never as separation loss/ranking.

### 3. Quantification/tracker must be cleaned to upstream semantics

Required:

- Pair and container loss default must use the upstream overlap-proxy + shape-penalty logic already started in Q25-R1.
- Remove or quarantine stale resolution-distance terminology and counters from production tracker diagnostics if they no longer represent the default loss.
- `SparrowCollisionTracker` should expose upstream-equivalent operations: pair/container loss lookup, item weighted loss, total weighted loss, GLS update, moved item update, and collision item extraction.
- If local keys differ from upstream `PItemKey`, document this as `ADAPTED_FIXED_SHEET_INDEXING`, not as a semantic gap.

### 4. LBFBuilder must stop using “least-infeasible” as a success substitute

The upstream LBFBuilder uses `search_placement + LBFEvaluator`; if needed, upstream expands strip width. In fixed-sheet multisheet, expansion is not allowed, but a fake placement is not an acceptable replacement.

Required:

- LBF placement path must be only `search_placement + LBFEvaluator`.
- Search all available fixed sheets/rotations where valid.
- If no clear placement exists, mark the item unresolved/partial for later handling; do not install a least-infeasible placement as if it were a constructed seed success.
- Remove language and code paths that turn “least-infeasible” into a normal constructive placement.
- If the separator intentionally starts from an infeasible layout for fixed-sheet reasons, document that as a separate fixed-sheet adaptation and do not label it upstream LBF parity.

### 5. Search/sampler/coordinate descent must match upstream behavior

Required:

- `BestSamples` ordering must be evaluator-score based with strict upper-bound behavior.
- Use focused sampler around current placement and uniform/container-wide sampler across eligible fixed sheets.
- Coordinate descent must port upstream axis/state semantics: random/deterministic axis choice, success/fail step-size updates, and rotation refinement where rotations are allowed.
- No dense benchmark throttling may change algorithm semantics. Budgets may be configurable, but not hard-coded as a shortcut to fake progress.

### 6. Worker/separator must be exact semantic port, not only weighted terminology

Required:

- Worker iterates colliding/problem items from tracker state, not arbitrary target shortcuts.
- Move acceptance is based on moved-item weighted loss not increasing.
- Worker result carries total weighted loss and enough state for best-worker load-back.
- Separator chooses the lowest total weighted loss worker state. Pair count/raw loss are diagnostics/tie-breakers only.
- Strike/no-improvement loop follows upstream separation semantics.
- Sequential workers are acceptable only as a performance limitation; the semantic worker competition must remain identical.

### 7. Exploration/disruption must port upstream intent

Required:

- Infeasible solution pool, biased restore, and disruption must be explicitly mapped to upstream.
- Large-item disruption must include the fixed-sheet equivalent of contained-item relocation.
- Containment must be geometry/CDE based enough to be meaningful, not only bbox-overlap.
- Update tracker consistently after disruption.

### 8. Benchmark discipline

Do not add dense LV8 acceptance as the driver of this task.

Allowed runtime checks are only regression/proof-of-not-broken:

```text
medium CDE smoke
LV8 12 type × 1 smoke if already cheap
existing unit/smoke tests
```

Do not optimize specifically for the 191-piece LV8 first-sheet subset in this task. The benchmark ladder comes after the full core port is semantically complete.

## Report requirements

Write:

```text
codex/reports/egyedi_solver/sgh_q25_r2_complete_upstream_sparrow_core_semantic_port.md
```

Start with exactly one:

```text
SGH-Q25-R2_STATUS: PASS
SGH-Q25-R2_STATUS: REVISE
SGH-Q25-R2_STATUS: REVISE_SCOPE_BLOCKED
```

Include these sections:

1. Upstream commit hash.
2. `PRE_TASK_GIT_STATUS` and `PRE_EXISTING_OUT_OF_SCOPE_DIRTY_FILES`.
3. Changed files and `TASK_CHANGED_FILES`.
4. `OUT_OF_SCOPE_NEW_CHANGES`.
5. Semantic mapping table:

```text
Upstream file | Upstream type/function | Required behavior | Local file | Local implementation | Status | Fixed-sheet deviation | Evidence
```

Allowed statuses:

```text
PORTED
ADAPTED_FIXED_SHEET
DEFERRED_COMPRESSION_ONLY
NOT_APPLICABLE_IO_ONLY
REVISE
```

Rules:

- `PORTED` means behavior, not name.
- `ADAPTED_FIXED_SHEET` requires a concrete fixed-sheet reason.
- Any non-compression `REVISE` row means final status is `REVISE`.
- “Sparrow-like”, “similar”, “progress”, “good enough”, “future work”, and benchmark improvement are not valid PASS evidence.

## PASS criteria

Q25-R2 can be PASS only if:

- no new out-of-scope changes are introduced;
- specialized collector is not post-query-only batch accumulation;
- separation evaluator uses the collector with upper-bound semantics;
- LBF no longer treats least-infeasible placement as constructive success;
- search/sampler/coord-descent behavior is upstream-mapped;
- worker/separator semantics are upstream-mapped;
- exploration/disruption includes contained-item relocation semantics;
- compression remains excluded;
- report honestly maps every upstream core function involved.

