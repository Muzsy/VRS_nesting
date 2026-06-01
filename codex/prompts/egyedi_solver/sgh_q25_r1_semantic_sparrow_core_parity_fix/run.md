# SGH-Q25-R1 — Semantic upstream Sparrow core parity fix, compression excluded

## Read this first

Q25 split the native Sparrow implementation into upstream-mapped modules. That was necessary, but the audit found that several modules are still structural ports only. Your job is to finish the semantic port.

Do not tune dense LV8 numbers directly. Do not add a new heuristic. Do not keep proxy logic with a better name. Do not mark `PASS` if the collector/evaluator/LBF/quantification/exploration semantics are still not upstream-compatible.

Compression is explicitly out of scope.

## Absolute goal

The production `sparrow_cde` path must remain:

```text
SparrowProblem -> SparrowOptimizer::solve -> SparrowSolution
```

Inside that path, the Q25 module tree must now carry the real upstream Sparrow semantics, with only explicit fixed-sheet adaptations.

## Step 0 — source of truth

From repo root:

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
```

## Step 1 — fix `eval/specialized_cde_pipeline.rs`

It must not be a stub.

Replace the no-op collector with a real local equivalent of upstream `SpecializedHazardCollector`:

- fields for target item, tracker/weights or weighted-loss lookup, accumulated loss, loss bound, hazard list/counters, early-termination state;
- `reload(loss_bound)` resets state and stores the bound;
- pair/container accumulation calculates loss through the production quantification module and tracker weights;
- `is_empty`, `loss`, `early_terminate` behave meaningfully;
- `collect_poly_collisions_in_detector_custom(...)` performs real CDE/session collection for the moving candidate.

If the local CDE API differs from jagua's exact collector API, write an adapter, but do not skip collection.

## Step 2 — fix `eval/sep_evaluator.rs`

Rewrite candidate scoring to match upstream Algorithm 7 semantics:

1. prepare candidate shape;
2. reload collector with upper bound;
3. collect CDE hazards;
4. early-terminate dominated samples;
5. return clear/collision/invalid based on collector state and loss.

Remove production use of:

```text
hazard_extent_depth
aabb_penetration
ox.min(oy)
ix * iy
bbox/extent penetration as candidate loss
```

AABB may remain for fit-to-sheet clipping or safe broad phase only.

## Step 3 — fix `quantify/*`

Default quantification must port upstream Sparrow behavior:

- `quantify_collision_poly_poly`: `overlap_area_proxy + epsilon^2`, sqrt, shape penalty;
- `quantify_collision_poly_container`: container outside/intersection-area loss and shape penalty;
- tracker stores pair/container losses and GLS weights based on these functions.

If the Q24R9 resolution-distance probe is retained, make it explicitly experimental and non-default. The report must not call it exact upstream parity.

## Step 4 — fix `lbf.rs`

Remove production recovery shortcuts:

```text
fixed_sheet_recovery_candidate
shelf_construct
fallback_anchor
candidate_penalty
ix * iy overlap score
```

The LBF path must use:

```text
search_placement + LBFEvaluator
```

Fixed-sheet adaptation may search across sheets and rotations. If no clear placement exists, produce honest unresolved/partial diagnostics, not a proxy placement.

## Step 5 — fix worker/separator semantics

- Worker move acceptance: moved item weighted loss must not increase according to tracker semantics.
- Best worker load-back: minimum total weighted loss wins.
- Strike/no-improvement logic: upstream-style loss-based loop.
- Pair count may be diagnostic only, not primary selection.
- Sequential workers are acceptable for now only if documented as a non-semantic performance limitation.

## Step 6 — fix exploration disruption

Implement a fixed-sheet equivalent of upstream contained-item relocation:

- after large-item swap/relocation, detect items practically contained/covered by moved large items using CDE/geometric containment;
- transform contained items into the opened space;
- clamp/convert to closest feasible fixed-sheet placement;
- update tracker consistently.

A large-item swap plus random kick is not enough.

## Step 7 — verification

Run:

```bash
cargo build --manifest-path rust/vrs_solver/Cargo.toml --release
cargo test --manifest-path rust/vrs_solver/Cargo.toml --lib
python3 scripts/smoke_sgh_q25_r1_semantic_sparrow_core_parity_fix.py
./scripts/check.sh
```

Also run the existing Q25/Q24 regression smoke scripts if present and relevant.

## Required report

Write:

```text
codex/reports/egyedi_solver/sgh_q25_r1_semantic_sparrow_core_parity_fix.md
```

Start with one of:

```text
SGH-Q25-R1_STATUS: PASS
SGH-Q25-R1_STATUS: REVISE
```

Include:

- upstream commit;
- changed files;
- build/test/smoke results;
- semantic mapping table:

```text
Upstream file | Required behavior | Local file | Local implementation | Status | Fixed-sheet deviation | Evidence
```

Allowed statuses:

```text
PORTED
ADAPTED_FIXED_SHEET
DEFERRED_COMPRESSION_ONLY
NOT_APPLICABLE_IO_ONLY
REVISE
```

If any non-compression behavior is still stub/proxy/adapted-only without a concrete fixed-sheet reason, the final status must be `REVISE`.

## Do not overclaim

Do not write “exact upstream-style” unless the implementation actually matches the upstream semantics. If the code is a VRS-specific alternative, say so and mark it `REVISE` unless the fixed-sheet adaptation genuinely requires it.
